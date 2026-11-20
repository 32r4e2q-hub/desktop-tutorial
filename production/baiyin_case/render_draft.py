#!/usr/bin/env python3
"""Build a non-release 180s draft from recorded Agnes receipts, with voice and subtitles.
No image is passed off as video; every source is hash-verified. Rendered draft
is not a visual or factual sign-off. Run verify_master separately.
"""
from __future__ import annotations
import hashlib,json,math,os,subprocess,sys,urllib.request,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
WORK=ROOT/'work'/'baiyin_case'/'draft';SOURCES=WORK/'sources';CLIPS=WORK/'normalized'
sys.path.insert(0,str(ROOT/'production'))
from gwangju_style import write_ass


def run(*cmd):subprocess.run(list(map(str,cmd)),cwd=ROOT,check=True)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def srt_time(s):
 ms=round(s*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
 return f'{h:02}:{m:02}:{s:02},{ms:03}'
def onset(path):
 with wave.open(str(path),'rb') as f:
  rate=f.getframerate();channels=f.getnchannels();samples=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
 mono=samples.reshape(-1,channels).mean(axis=1);hop=rate//100;blocks=mono[:len(mono)//hop*hop].reshape(-1,hop)
 rms=np.sqrt(np.mean(blocks**2,axis=1));threshold=max(.004,float(np.percentile(rms,95))*.10)
 active=np.flatnonzero(rms>threshold)
 if not len(active):raise RuntimeError(f'No voice activity in {path}')
 return float(active[0]/100),float((active[-1]+1)/100)
def heartbeat(path):
 rate=48000;n=rate*2;t=np.arange(n)/rate
 x=(.20*np.sin(2*np.pi*55*t)*np.exp(-np.maximum(t-.20,0)*22)*((t>=.20)&(t<.50)) +
    .14*np.sin(2*np.pi*48*t)*np.exp(-np.maximum(t-.48,0)*25)*((t>=.48)&(t<.72)))
 pcm=(np.clip(np.stack([x,x],axis=1),-1,1)*32767).astype('<i2')
 with wave.open(str(path),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(rate);f.writeframes(pcm.tobytes())

def main():
 for d in (WORK,SOURCES,CLIPS):d.mkdir(parents=True,exist_ok=True)
 story=json.loads((HERE/'story.json').read_text());results=json.loads((HERE/'results.json').read_text())['shots']
 # This is a review draft, not a release: insert completed redo candidates so
 # they can be reviewed in context. The report must keep visual_review=pending.
 redo_file=HERE/'qa'/'keyshots_redo.json'
 if redo_file.exists():
  redos=json.loads(redo_file.read_text())['shots']
  for sid,row in redos.items():
   if row.get('status')=='completed' and row.get('sha256') and row.get('video_url'):
    results[sid]=row
 run(sys.executable,HERE/'fit_audio.py')
 heart=WORK/'S01.wav';heartbeat(heart)
 audio_files=[heart]+[ROOT/'work'/'baiyin_case'/'audio'/f'{s["id"]}.wav' for s in story['shots'][1:]]
 audio_list=WORK/'audio_concat.txt';audio_list.write_text(''.join("file '"+str(x).replace("'", "'\\''")+"'\n" for x in audio_files))
 audio_m4a=WORK/'audio.m4a'
 run('ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',audio_list,'-ar','48000','-ac','2','-c:a','aac','-b:a','192k','-t','180',audio_m4a)
 cues=[]
 for shot in story['shots'][1:]:
  start,end=onset(ROOT/'work'/'baiyin_case'/'audio'/f'{shot["id"]}.wav')
  cues.append((shot['start']+start, min(shot['start']+end,shot['start']+shot['duration']-.03),shot['narration']))
 srt=WORK/'baiyin_subtitles.srt';srt.write_text('\n\n'.join(f'{i}\n{srt_time(a)} --> {srt_time(b)}\n{t}' for i,(a,b,t) in enumerate(cues,1))+'\n',encoding='utf-8')
 ass=WORK/'baiyin_subtitles.ass'
 hooks=[{'id':'H1','start':0,'end':2,'text':'28年'}, {'id':'H2','start':31,'end':33,'text':'11名遇害者'}, {'id':'H3','start':92,'end':94,'text':'2016年·转机'}]
 explainers=[{'start':9,'end':13,'text':'甘肃·白银｜真实案件'}, {'start':60,'end':64,'text':'警方累计采集指纹23万枚'}, {'start':99,'end':105,'text':'Y染色体提供父系线索，不能单独认定个人'}, {'start':133,'end':138,'text':'2016.8.26｜嫌疑人落网'}, {'start':160,'end':166,'text':'2019.1.3｜已执行死刑'}, {'start':178,'end':180,'text':'信源：新华社（2016）｜央视网（2019）'}]
 write_ass(ass,cues,['28年','11名','23万枚','死刑'],onscreen_label='AI情景演绎·非真实影像',hooks=hooks,explainers=explainers)
 sources_manifest=[]
 for shot in story['shots']:
  sid=shot['id'];r=results[sid]
  if r.get('status')!='completed' or not r.get('sha256') or not r.get('video_url'):raise RuntimeError(f'{sid} incomplete')
  source=SOURCES/f'{sid}.mp4'
  if not source.is_file() or digest(source)!=r['sha256']:
   request=urllib.request.Request(r['video_url'],headers={'User-Agent':'BaiyinDraft/1.0'})
   with urllib.request.urlopen(request,timeout=180) as stream, source.open('wb') as f:
    while True:
     block=stream.read(1024*1024)
     if not block:break
     f.write(block)
  if digest(source)!=r['sha256']:raise RuntimeError('Source hash mismatch: '+sid)
  sources_manifest.append({'id':sid,'sha256':r['sha256'],'video_id':r.get('video_id'),'duration':shot['duration']})
  dest=CLIPS/f'{sid}.mp4';duration=shot['duration']
  vf=f'scale=1920:1080:flags=lanczos,fps=24,trim=duration={duration},setpts=PTS-STARTPTS,setsar=1'
  if sid=='S25':vf+=f",drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='gte(t,{duration-1})'"
  vf+=',drawbox=x=0:y=0:w=iw:h=138:color=black:t=fill,drawbox=x=0:y=942:w=iw:h=138:color=black:t=fill,format=yuv420p'
  run('ffmpeg','-hide_banner','-loglevel','error','-y','-i',source,'-vf',vf,'-an','-c:v','libx264','-preset','veryfast','-crf','18','-r','24','-video_track_timescale','24000',dest)
  print('NORMALIZED',sid,flush=True)
 video_list=WORK/'video_concat.txt';video_list.write_text(''.join("file '"+str(CLIPS/(shot['id']+'.mp4'))+"'\n" for shot in story['shots']))
 concat=WORK/'video_concat.mp4';run('ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',video_list,'-c','copy',concat)
 film=WORK/'baiyin_firstcut_review.mp4'
 run('ffmpeg','-hide_banner','-loglevel','error','-y','-i',concat,'-i',audio_m4a,'-vf',f"ass={ass}",'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-c:a','copy','-t','180','-movflags','+faststart',film)
 (WORK/'source_manifest.json').write_text(json.dumps(sources_manifest,ensure_ascii=False,indent=2)+'\n')
 print('DRAFT',film,'visual review and verifier required',flush=True)
if __name__=='__main__':main()
