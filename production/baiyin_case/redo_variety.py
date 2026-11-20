#!/usr/bin/env python3
"""Regenerate repetitive shots; save new receipts without replacing original footage."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'production'));sys.path.insert(0,str(ROOT/'production'/'shanghai_freezer_case'))
import agnes_video as agnes
from throttle import RequestGate
BRANCH='arena/aa4972d2-desktop-tutorial';MODEL='agnes-video-2.5-flash'
RESULT=HERE/'qa'/'variety_redo.json'; QA=HERE/'qa'/'variety'; OUT=ROOT/'work'/'baiyin_case'/'variety'
BEATS={
'S14':('shopkeeper_back','虚构店主的背影近景，整理柜台上的无字纸箱，头部朝向柜台、不能露脸，镜头缓缓向右移。'),
'S20':('investigation','虚构调查人员背影坐在电脑前，屏幕始终纯黑无任何文字，翻阅空白资料，镜头微微推进。'),
'S22':('microscope','显微镜与透明载玻片局部，光线缓慢变化，镜头缓慢横移，不出现任何文字或人物。'),
'S23':('dossier','戴手套的手把完全无字的卡片轻轻摆放在桌面，镜头低角度缓慢推近。'),
'S26':('interview','空无一人的问询室，木桌上水杯微微反光，灯光柔和波动，镜头缓缓推进。')}

def git(*a): return subprocess.run(['git',*a],cwd=ROOT,check=True,capture_output=True,text=True).stdout

def checkpoint(doc,msg,files=()):
 RESULT.parent.mkdir(parents=True,exist_ok=True);RESULT.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 paths=[str(RESULT.relative_to(ROOT))]+[str(p.relative_to(ROOT)) for p in files];git('add','--',*paths)
 if subprocess.run(['git','diff','--cached','--quiet','--',*paths],cwd=ROOT).returncode:
  git('commit','-m','baiyin redo: '+msg,'--',*paths)
  for attempt in range(3):
   try: git('push','origin',f'HEAD:refs/heads/{BRANCH}');break
   except subprocess.CalledProcessError:
    if attempt==2:raise
    git('pull','--rebase','origin',BRANCH)
 print('CHECKPOINT',msg,flush=True)

def main():
 if os.getenv('GITHUB_ACTIONS')!='true' or os.getenv('GITHUB_REF')!=f'refs/heads/{BRANCH}':raise SystemExit('wrong branch')
 key=os.getenv('AGNES_API_KEY','').strip()
 if not key:raise SystemExit('missing key')
 base=(os.getenv('AGNES_BASE_URL') or agnes.DEFAULT_BASE_URL).rstrip('/');gate=RequestGate(minimum_interval=12.1)
 git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
 story=json.loads((HERE/'story.json').read_text()); shots={s['id']:s for s in story['shots']}
 doc=json.loads(RESULT.read_text()) if RESULT.exists() else {'reference_revision':os.environ['GITHUB_SHA'],'shots':{},'visual_review':'pending'}
 QA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 for sid,(reference,action) in BEATS.items():
  prompt=('纪实电影情景演绎，2016年西北中国，任何人物均为虚构演员背影，不还原真实长相。'
   +action+' 画面真实连续运动，16比9，克制的悬疑风，主体比例自然。禁止正脸、儿童、血腥、伤口、暴力、遗体、文字、数字、商标、招牌、水印。')
  payload={'model':MODEL,'prompt':prompt,'seconds':str(shots[sid]['duration']),'size':'720P','aspect_ratio':'16:9','mode':'reference','n':1,'seed':19900000+int(sid[1:]),'images':[f'https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/{doc["reference_revision"]}/production/baiyin_case/reference/{reference}.png']}
  wanted=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
  old=doc['shots'].get(sid)
  if old:
   if old['request_hash']!=wanted:raise SystemExit(f'{sid} changed request; stop')
   if old.get('video_id'):continue
   raise SystemExit(f'{sid} unresolved: no duplicate POST')
  row={'status':'submitting','request_hash':wanted,'request':payload,'reused_existing_asset':False,'visual_review':'pending'};doc['shots'][sid]=row;checkpoint(doc,sid+' submitting')
  for attempt in range(1,11):
   gate.acquire()
   try: reply=agnes.http_json('POST',base+'/v1/videos',key,payload,timeout=120);code,body,text=reply
   except Exception as e:
    row.update(status='create_unknown',error=str(e).replace(key,'[redacted]')[:300]);checkpoint(doc,sid+' unknown');raise
   if code==429:
    row.update(status='rate_limited',attempts=attempt);checkpoint(doc,sid+' rate limited')
    if attempt==10:raise SystemExit('capacity exhaustion')
    gate.defer(max(60,float(getattr(reply,'retry_after',None) or 0)));continue
   if not (200<=code<300 and isinstance(body,dict)):
    row.update(status='create_unknown' if code>=500 else 'rejected',http_status=code);checkpoint(doc,sid+' rejected');raise SystemExit('request failed')
   vid=body.get('video_id') or body.get('id') or body.get('task_id')
   if not vid:row.update(status='create_unknown');checkpoint(doc,sid+' missing id');raise SystemExit('missing id')
   row.update(status='queued',video_id=str(vid),task_id=str(body.get('task_id') or body.get('id') or vid),attempts=attempt);checkpoint(doc,sid+' accepted');break
 for sid in BEATS:
  row=doc['shots'][sid]
  if row.get('status')=='completed':continue
  try:
   final,url=agnes.poll_task(base,key,MODEL,row['video_id'],row.get('task_id'),interval=45,timeout=1800,max_failures=8,before_request=gate.acquire,rate_limit_callback=gate.defer)
   out=OUT/f'{sid}.mp4';size=agnes.download(url,out,retries=3,retry_delay=5)
   meta=json.loads(subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(out)],capture_output=True,text=True,check=True).stdout)
   video=next(x for x in meta['streams'] if x['codec_type']=='video');sheet=QA/f'{sid}.jpg'
   subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(out),'-vf','fps=1/2,scale=320:-1,tile=4x1','-frames:v','1',str(sheet)],check=True)
   row.update(status='completed',video_url=url,sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bytes=size,duration=float(meta['format']['duration']),width=video.get('width'),height=video.get('height'),provider_status=final.get('status'))
   checkpoint(doc,sid+' completed',files=(sheet,))
  except Exception as e:
   row.update(status='poll_failed',error=str(e).replace(key,'[redacted]')[:300]);checkpoint(doc,sid+' poll failed');raise
if __name__=='__main__':main()
