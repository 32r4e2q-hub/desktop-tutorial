"""Generate distinct moving reenactments; retain explicit still fallback on service failure."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0,'production')
import agnes_video as a
P=Path(__file__).parent; OUT=Path('media');OUT.mkdir(exist_ok=True)
plan=json.loads((P/'edit_plan.json').read_text());shots={s['id']:s for s in json.loads((P/'story.json').read_text())['shots']}
key=os.environ.get('AGNES_API_KEY');base=a.DEFAULT_BASE_URL.rstrip('/');model='agnes-video-2.5-flash';jobs={}
if key:
 for sid,(ref,act) in plan['replacements'].items():
  payload={'model':model,'prompt':'纪实电影情景演绎。人物均为虚构成年演员。保持参考图人物造型和自然表情。'+act+' 不出现文字、水印、暴力。','seconds':str(shots[sid]['duration']),'size':'720P','aspect_ratio':'16:9','mode':'reference','n':1,'images':[f'https://raw.githubusercontent.com/{os.environ["GITHUB_REPOSITORY"]}/{os.environ["GITHUB_SHA"]}/production/baiyin_case/reference_v4/{ref}.jpg']}
  try:
   code,body,_=a.http_json('POST',base+'/v1/videos',key,payload,timeout=60);vid=body.get('video_id') or body.get('id') or body.get('task_id');assert code in (200,201,202) and vid
   jobs[sid]=(str(vid),str(body.get('task_id') or vid));print('accepted',sid,flush=True)
  except Exception: print('reference fallback',sid,flush=True)
  time.sleep(13)
 for sid,(vid,tid) in jobs.items():
  try:
   _,url=a.poll_task(base,key,model,vid,tid,interval=18,timeout=400,max_failures=3);a.download(url,OUT/(sid+'.mp4'));print('downloaded',sid,flush=True)
  except Exception: print('reference fallback',sid,flush=True)
