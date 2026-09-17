"""Optional local-on-runner ASR-assisted timing; captions retain the reviewed script.

No audio is sent to an external transcription service. Model weights are downloaded
on the runner. Low-coverage matches explicitly fall back to pause-aware timing.
"""
import importlib.util
from difflib import SequenceMatcher
import os
from pathlib import Path
import re

def _load_simpfold():
    """加载上级目录的共享简繁折叠表（production/simpfold.py）。

    缺文件就立刻失败而不是静默退回停顿估算——v2 的教训：whisper 繁体转写
    把字符匹配率打到 0.03-0.75，四章字幕静默回落到停顿估算而失同步。
    """
    path=Path(__file__).resolve().parents[1]/'simpfold.py'
    if not path.is_file():
        raise RuntimeError(f'missing shared simpfold module: {path}')
    spec=importlib.util.spec_from_file_location('simpfold',path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_SIMPFOLD=_load_simpfold()

DIGITS = '零一二三四五六七八九'


def chinese_number(value):
    n=int(value)
    if n<10:return DIGITS[n]
    if n<100:
        tens,ones=divmod(n,10)
        return ('' if tens==1 else DIGITS[tens])+'十'+(DIGITS[ones] if ones else '')
    return ''.join(DIGITS[int(c)] for c in str(value))


def normalize(text):
    text=re.sub(r'(\d{4})(?=年)',lambda m:''.join(DIGITS[int(c)] for c in m.group(1)),text)
    text=re.sub(r'\d+',lambda m:chinese_number(m.group(0)),text)
    text=_SIMPFOLD.fold(text)
    return ''.join(re.findall(r'[\u3400-\u9fffA-Za-z]',text)).lower()


def aligned_cues(row, clauses, words):
    expected=normalize(row['text']);characters=[];times=[]
    for word in words:
        text=normalize(word['word'])
        if not text:continue
        a=max(0,float(word['start']));b=min(row['raw_duration'],float(word['end']))
        if b<=a:continue
        for i,c in enumerate(text):
            characters.append(c);times.append((a+(b-a)*i/len(text),a+(b-a)*(i+1)/len(text)))
    recognized=''.join(characters)
    mapping={}
    for block in SequenceMatcher(None,expected,recognized,autojunk=False).get_matching_blocks():
        for offset in range(block.size):mapping[block.a+offset]=times[block.b+offset]
    coverage=len(mapping)/max(1,len(expected))
    if coverage<.75:return None,coverage
    cues=[];cursor=0;last_end=row['start']
    for clause in clauses:
        count=len(normalize(clause));matches=[mapping[i] for i in range(cursor,cursor+count) if i in mapping]
        if not matches:return None,coverage
        a=min(t[0] for t in matches);b=max(t[1] for t in matches)
        start=max(last_end,row['start']+max(0,a-.09)/row['tempo'])
        end=row['start']+min(row['raw_duration'],b+.15)/row['tempo']
        if end<=start:return None,coverage
        cues.append({'start':start,'end':end,'text':clause})
        last_end=end;cursor+=count
    return cues,coverage


def transcribe_on_runner(narration, work):
    work=Path(work)
    os.environ.setdefault('HF_HOME',str(work/'model-cache'))
    os.environ.setdefault('HF_HUB_ETAG_TIMEOUT','15')
    os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT','90')
    try:
        from faster_whisper import WhisperModel
        model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=2,
                           download_root=str(work/'model-cache'))
        results={}
        for row in narration:
            segments,_=model.transcribe(row['path'],language='zh',beam_size=5,word_timestamps=True,
                                        vad_filter=True,initial_prompt=row['text'])
            words=[];text=[]
            for s in segments:
                text.append(s.text)
                for word in s.words or []:
                    words.append({'word':word.word,'start':word.start,'end':word.end})
            results[row['id']]={'words':words,'recognized_text':''.join(text)}
            print('ASR_TIMING_READY '+row['id'],flush=True)
        return results
    except Exception as exc:
        print(f'ASR_TIMING_UNAVAILABLE {type(exc).__name__}: {exc}; pause-aware fallback will be labeled',flush=True)
        return {}
