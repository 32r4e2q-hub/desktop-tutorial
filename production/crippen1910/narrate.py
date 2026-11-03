"""Shot-locked Chinese narration after all thirty motion clips pass visual review.

Autonomous voice selection: Microsoft zh-CN-YunjianNeural, masculine Mandarin,
low pitch. No actor/person imitation. Uses public Edge TTS, not an Arena voice_id.
"""
import asyncio,hashlib,json,re,subprocess,sys,time
from pathlib import Path
import numpy as np
import edge_tts
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from build_audio import RATE,trim_voice_edges,write_wave
VOICE='zh-CN-YunjianNeural'
PITCH='-8Hz'

def enforce_video_gate(story):
    result=json.loads((HERE/'results.json').read_text())['shots']
    review=json.loads((HERE/'qa/batch-reviews.json').read_text())
    for shot in story['shots']:
        sid=shot['id'];r=result.get(sid,{});q=review.get(sid,{})
        if r.get('status')!='completed' or q.get('status')!='approved' or q.get('sha256')!=r.get('sha256'):
            raise RuntimeError('No narration until every motion clip is reviewed: '+sid)

def split_sentence(text):
    return re.findall(r'.+?[。！？]|.+$',text)

async def generate(story):
    import wave
    audio=HERE/'audio';work=HERE.parents[1]/'work/crippen1910/tts';work.mkdir(parents=True,exist_ok=True)
    timing={};semaphore=asyncio.Semaphore(2)
    async def one(shot):
        async with semaphore:
            sid=shot['id'];available=min(shot['start']+shot['duration']-.08,179)-shot['start']
            if sid=='S25':available-=.5  # A dramatic narration pause after '终于结束了'.
            # Fits at natural playback: atempo remains 1, keeping inserted pauses exactly .5s.
            for rate in [0,6,12,18,24,30]:
                joined=[];cursor=0;captions=[];gaps=[]
                for sentence_index,sentence in enumerate(split_sentence(shot['narration'])):
                    caption_start=None;caption_end=None
                    parts=[];position=0
                    for marker in re.finditer(r'一道电波[，,]?|科拉[，,](?=究竟)',sentence):
                        parts.append((sentence[position:marker.end()],True));position=marker.end()
                    if position<len(sentence):parts.append((sentence[position:],False))
                    for part_index,(part,pause_after) in enumerate(parts):
                        if not part:continue
                        text=part.rstrip('，,') if pause_after else part
                        raw=work/f'{sid}-{sentence_index}-{part_index}.mp3';wav=raw.with_suffix('.wav')
                        for attempt in range(3):
                            try:
                                await edge_tts.Communicate(text,VOICE,rate=f'+{rate}%',pitch=PITCH).save(str(raw));break
                            except Exception:
                                if attempt==2:raise
                                await asyncio.sleep(5*(attempt+1))
                        subprocess.run(['ffmpeg','-y','-v','error','-i',str(raw),'-ar',str(RATE),'-ac','1','-c:a','pcm_s16le',str(wav)],check=True)
                        with wave.open(str(wav)) as f:samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
                        samples,onset,offset=trim_voice_edges(samples)
                        if caption_start is None:caption_start=cursor/RATE+onset
                        caption_end=cursor/RATE+offset
                        joined.append(samples);cursor+=len(samples)
                        if pause_after:
                            gaps.append(dict(at=cursor/RATE,duration=.5))
                            silence=np.zeros(RATE//2,dtype=np.float32);joined.append(silence);cursor+=len(silence)
                    captions.append(dict(text=sentence,start=caption_start,end=caption_end))
                    if sentence_index<len(split_sentence(shot['narration']))-1:
                        gap=np.zeros(round(.15*RATE),dtype=np.float32);joined.append(gap);cursor+=len(gap)
                samples=np.concatenate(joined)
                if len(samples)/RATE<=available-.04:break
            else:raise RuntimeError(f'{sid}: rewrite narration, cannot fit without clipping')
            merged=work/f'{sid}-joined.wav';write_wave(merged,samples)
            target=audio/f'{sid}.mp3'
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(merged),'-c:a','libmp3lame','-b:a','96k',str(target)],check=True)
            timing[sid]=dict(captions=captions,inserted_pauses=gaps,rate_percent=rate,natural_seconds=len(samples)/RATE,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
            print('VOICE',sid,round(len(samples)/RATE,3),'seconds; rate',rate,flush=True)
    await asyncio.gather(*(one(s) for s in story['shots']))
    (audio/'voice.json').write_text(json.dumps(dict(voice_id=VOICE,provider='Microsoft Edge TTS',language='zh-CN',gender='masculine',pitch=PITCH,selection='autonomous under user brief; not an Arena audition'),ensure_ascii=False,indent=2)+'\n')
    (audio/'timing.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2)+'\n')
    subprocess.run([sys.executable,str(HERE/'build_story.py')],check=True)

if __name__=='__main__':
    story=json.loads((HERE/'story.json').read_text());enforce_video_gate(story);asyncio.run(generate(story))
