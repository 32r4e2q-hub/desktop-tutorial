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
    """词级时间戳 -> 分句字幕时间。

    映射率 ≥0.6 才算可用；个别分句完全没命中锚点时，在最近的左右锚点之间
    按字符位置线性内插，而不是像旧版那样整章放弃回落到停顿估算
    （v2/v3 实证：估算在 N04/N06 错到字幕整体漂移几秒）。
    """
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
    if coverage<.6:return None,coverage
    matched=sorted(mapping)
    def film_time(raw):
        return row['start']+min(row['raw_duration'],max(0.0,raw))/row['tempo']
    cues=[];cursor=0;last_end=row['start']
    for clause in clauses:
        count=len(normalize(clause));lo,hi=cursor,cursor+count
        idx=[i for i in range(lo,hi) if i in mapping]
        if idx:
            a_raw=min(mapping[i][0] for i in idx);b_raw=max(mapping[i][1] for i in idx)
        else:
            prev_i=max((i for i in matched if i<lo),default=None)
            next_i=min((i for i in matched if i>=hi),default=None)
            left_raw=mapping[prev_i][1] if prev_i is not None else 0.0
            right_raw=mapping[next_i][0] if next_i is not None else row['raw_duration']
            span=max(1,len(matched))
            left_i=prev_i if prev_i is not None else (matched[0]-1 if matched else 0)
            right_i=next_i if next_i is not None else (matched[-1]+1 if matched else span)
            frac_a=(lo-left_i)/max(1,right_i-left_i);frac_b=(hi-left_i)/max(1,right_i-left_i)
            a_raw=left_raw+(right_raw-left_raw)*min(1.0,max(0.0,frac_a))
            b_raw=left_raw+(right_raw-left_raw)*min(1.0,max(0.0,frac_b))
            if b_raw<=a_raw:b_raw=min(row['raw_duration'],a_raw+0.6)
        start=max(last_end,film_time(a_raw-.09))
        end=max(start+.4,film_time(b_raw+.15))
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
        # small 而不是 base：v3 实证 base 对 N05 的干净配音几乎转写不出可用文本
        # （字符匹配率 0.03，small 同段 0.9+）；condition off 防提示词复述式幻觉。
        model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=2,
                           download_root=str(work/'model-cache'))
        results={}
        for row in narration:
            segments,_=model.transcribe(row['path'],language='zh',beam_size=5,word_timestamps=True,
                                        vad_filter=True,condition_on_previous_text=False,
                                        initial_prompt=row['text'])
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
