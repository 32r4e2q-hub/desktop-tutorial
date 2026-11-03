"""Prepare shot-locked selected Arena narration from ten three-shot takes.

Actual local Chinese ASR word timestamps align the known script; mismatch fails closed.
No TTS provider substitution, guessed character-per-second captions, or syllable truncation.
Model/audio intermediates stay in ignored work/. The selected recordings remain auditable.
"""
import difflib,hashlib,json,re,subprocess,sys,wave,zipfile,urllib.request
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from build_audio import RATE,energy,trim_voice_edges,write_wave
from voice_policy import selected_voice_ready

DIGITS=dict(zip('零〇一二三四五六七八九两','001234567892'))

def normalize(text):
    def number(match):
        value=match.group()
        if not any(c in value for c in '十百千'):return ''.join(DIGITS[c] for c in value)
        total=current=0
        for c in value:
            if c in DIGITS:current=int(DIGITS[c])
            else:total+=(current or 1)*{'十':10,'百':100,'千':1000}[c];current=0
        return str(total+current)
    text=re.sub('[零〇一二三四五六七八九两十百千]+',number,text.lower())
    return ''.join(c for c in text if c.isalnum())


def align(script,words):
    expected=normalize(script);actual='';times=[]
    for word in words:
        chars=normalize(word['word'])
        for i,c in enumerate(chars):
            actual+=c
            times.append((word['start']+(word['end']-word['start'])*i/len(chars),word['start']+(word['end']-word['start'])*(i+1)/len(chars)))
    matcher=difflib.SequenceMatcher(None,expected,actual,autojunk=False)
    anchors={}
    for block in matcher.get_matching_blocks():
        for i in range(block.size):anchors[block.a+i]=times[block.b+i]
    coverage=len(anchors)/max(1,len(expected))
    if coverage<.68:raise RuntimeError(f'Selected-voice ASR alignment too weak: {coverage:.3f}')
    # Short ASR homophone substitutions still have real acoustic timestamps.
    # Keep exact-match coverage unchanged; do not map long/unrelated replacement spans.
    for tag,a,b,c,d in matcher.get_opcodes():
        if tag=='replace' and 0<b-a<=4 and 0<d-c<=4:
            start,end=times[c][0],times[d-1][1]
            for i in range(b-a):anchors[a+i]=(start+(end-start)*i/(b-a),start+(end-start)*(i+1)/(b-a))
    def position(offset,end=False):
        index=offset-1 if end else offset
        if index in anchors:return anchors[index][1 if end else 0]
        nearby=sorted(anchors,key=lambda p:(abs(p-index),p))
        if not nearby or abs(nearby[0]-index)>3:raise RuntimeError('Unanchored selected-voice script boundary')
        return anchors[nearby[0]][1 if end else 0]
    return position,coverage


def read_wave(path):
    with wave.open(str(path)) as f:
        assert f.getnchannels()==1 and f.getframerate()==RATE
        return np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768


def decode(source,target,rate=RATE,tempo=1):
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(source),'-af',f'atempo={tempo:.9f}','-ar',str(rate),'-ac','1','-c:a','pcm_s16le',str(target)],check=True)


def recognize(path,model):
    import vosk
    rec=vosk.KaldiRecognizer(model,16000);rec.SetWords(True);words=[]
    with wave.open(str(path)) as f:
        while data:=f.readframes(4000):
            if rec.AcceptWaveform(data):words.extend(json.loads(rec.Result()).get('result',[]))
    words.extend(json.loads(rec.FinalResult()).get('result',[]))
    if not words:raise RuntimeError('No actual ASR words in selected narration')
    return words


def model_path(work):
    target=work/'vosk-model-small-cn-0.22'
    if not (target/'am/final.mdl').is_file():
        archive=work/'vosk-cn.zip'
        with urllib.request.urlopen('https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip',timeout=180) as response,archive.open('wb') as output:
            import shutil
            shutil.copyfileobj(response,output)
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                if not (work/info.filename).resolve().is_relative_to(work.resolve()):raise RuntimeError('Unsafe ASR archive path')
            z.extractall(work)
    return target


def prepare():
    from narrate import enforce_video_gate
    import vosk
    story=json.loads((HERE/'story.json').read_text());enforce_video_gate(story)
    selection=json.loads((HERE/'audio/voice-selection.json').read_text())
    assert selection['provider']=='Arena speech'
    manifest=json.loads((HERE/'audio/voice-groups.json').read_text())
    assert manifest['voice_id']==selection['voice_id']
    groups=manifest['groups'];assert [sid for g in groups for sid in g['shot_ids']]==[s['id'] for s in story['shots']]
    by_id={s['id']:s for s in story['shots']};work=ROOT/'work/crippen1910/selected-voice';work.mkdir(parents=True,exist_ok=True)
    vosk.SetLogLevel(-1);model=vosk.Model(str(model_path(work)));timings={};evidence={};oversized=[]
    for group in groups:
        gid=group['id'];source=HERE/'audio/groups'/f'{gid}.mp3'
        assert hashlib.sha256(source.read_bytes()).hexdigest()==group['sha256']
        shots=[by_id[sid] for sid in group['shot_ids']]
        script='\n'.join(s['narration'] for s in shots)
        assert script==group['text']
        wav16=work/f'{gid}-16.wav';wav48=work/f'{gid}-48.wav'
        decode(source,wav16,16000);decode(source,wav48);samples=read_wave(wav48)
        words=recognize(wav16,model);position,coverage=align(script,words)
        evidence[gid]={'sha256':group['sha256'],'asr_words':words,'normalized_script_coverage':coverage}
        (HERE/'qa/selected-voice-alignment.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
        offsets=[0]
        for shot in shots:offsets.append(offsets[-1]+len(normalize(shot['narration'])))
        cuts=[0.0]
        for offset in offsets[1:-1]:
            a=position(offset,end=True);b=position(offset)
            if b<a-.12:raise RuntimeError('ASR boundary order conflict')
            cuts.append((a+b)/2)
        cuts.append(len(samples)/RATE)
        for i,shot in enumerate(shots):
            sid=shot['id'];start=cuts[i];end=cuts[i+1];raw=samples[round(start*RATE):round(end*RATE)]
            levels=energy(raw);active=np.flatnonzero(levels>max(.0002,float(levels.max())*.003))
            trimmed,onset,offset=trim_voice_edges(raw);removed=max(0,int(active[0])*.01-onset)
            local=lambda index,last=False: max(0.0,min(len(trimmed)/RATE,position(offsets[i]+index,end=last)-start-removed))
            captions=[];char_cursor=0
            for sentence in re.findall(r'.+?[。！？]|.+$',shot['narration']):
                n=len(normalize(sentence));last=char_cursor+n==offsets[i+1]-offsets[i]
                captions.append({'text':sentence,'start':onset if char_cursor==0 else local(char_cursor),'end':offset if last else local(char_cursor+n,True)});char_cursor+=n
            pauses=[]
            for match in re.finditer(r'一道电波[，,]?|科拉[，,](?=究竟)',shot['narration']):
                at=len(normalize(shot['narration'][:match.end()]));a=local(at,True);b=local(at)
                pauses.append((a,max(a,b)))
            available=min(shot['duration']-.08,179-shot['start'])-(.5 if sid=='S25' else 0)
            fixed=.5*len(pauses);gap=sum(b-a for a,b in pauses)
            tempo=max(1.0,(len(trimmed)/RATE-gap)/(available-fixed-.04))
            if tempo>story['narration_spec']['max_speedup_factor']:
                oversized.append({'shot':sid,'required_tempo':tempo,'natural_seconds':len(trimmed)/RATE,'available_seconds':available})
                (HERE/'qa/selected-voice-duration-issues.json').write_text(json.dumps(oversized,ensure_ascii=False,indent=2)+'\n')
                continue
            raw_path=work/f'{sid}-natural.wav';write_wave(raw_path,trimmed)
            fitted=work/f'{sid}-fitted.wav';decode(raw_path,fitted,tempo=tempo);data=read_wave(fitted)
            ratio=len(data)/len(trimmed)
            for caption in captions:caption['start']*=ratio;caption['end']*=ratio
            inserted=[]
            for a,b in reversed(pauses):
                a*=ratio;b*=ratio;begin=round(a*RATE);finish=round(b*RATE)
                data=np.concatenate([data[:begin],np.zeros(RATE//2,dtype=np.float32),data[finish:]])
                delta=.5-(finish-begin)/RATE
                for caption in captions:
                    for k in ['start','end']:
                        if caption[k]>=b-.001:caption[k]+=delta
                inserted.append({'at':begin/RATE,'duration':.5})
            if len(data)/RATE>available+.025:raise RuntimeError(sid+': selected narration exceeds shot after measured fitting')
            for caption in captions:
                caption['start']=max(0,min(caption['start'],len(data)/RATE-.01));caption['end']=min(len(data)/RATE,max(caption['end'],caption['start']+.01))
            joined=work/f'{sid}-joined.wav';write_wave(joined,data);output=HERE/'audio'/f'{sid}.mp3'
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(joined),'-c:a','libmp3lame','-b:a','96k',str(output)],check=True)
            timings[sid]={'captions':captions,'inserted_pauses':inserted,'natural_seconds':len(data)/RATE,'tempo_factor':tempo,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'alignment':'Vosk actual word timestamps matched to known script','group_id':gid}
            print('SELECTED_VOICE',sid,'seconds',round(len(data)/RATE,3),'tempo',round(tempo,3),flush=True)
    if oversized:raise RuntimeError('Selected narration exceeds natural delivery limits; see qa/selected-voice-duration-issues.json; no truncation allowed')
    (HERE/'audio/timing.json').write_text(json.dumps(timings,ensure_ascii=False,indent=2)+'\n')
    (HERE/'audio/voice.json').write_text(json.dumps({'provider':'Arena speech','voice_id':selection['voice_id'],'language':'zh-CN','gender':'masculine','selection':'user selected audition, no Edge substitution'},ensure_ascii=False,indent=2)+'\n')
    (HERE/'qa/selected-voice-alignment.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    assert selected_voice_ready(HERE,story['shots'])
    subprocess.run([sys.executable,str(HERE/'build_story.py')],check=True)

if __name__=='__main__':prepare()
