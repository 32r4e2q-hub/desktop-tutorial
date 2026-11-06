#!/usr/bin/env python3
"""Generate Hakamada shots with the verified Son of Sam Agnes reference-image schema."""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, os, re, sys, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'production'))
sys.path.insert(0,str(ROOT/'production'/'setagaya2000'))
import agnes_video as agnes
from throttle import RequestGate
PLAN=HERE/'story.json'; RESULTS=HERE/'results.json'; REF=HERE/'reference'
REVISION_FILE=REF/'revision.txt'; APPROVALS_FILE=REF/'approvals.json'
BRANCH='arena/74df59cd-desktop-tutorial'; REPOSITORY='32r4e2q-hub/desktop-tutorial'
MODEL='agnes-video-2.5-flash'; SIZE='720P'; REQUEST_INTERVAL=61
ALLOWED={'model','prompt','seconds','size','aspect_ratio','mode','n','seed','images'}
FORBIDDEN={'width','height','fps','num_frames','frame_rate','duration','resolution','negative_prompt','quality','num_inference_steps'}
LOCK=threading.RLock(); GATE=RequestGate(REQUEST_INTERVAL)

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def revision():
 if not REVISION_FILE.is_file(): raise RuntimeError('reference/revision.txt missing; publish immutable image bundle first')
 value=REVISION_FILE.read_text().strip()
 if not re.fullmatch(r'[0-9a-f]{40}',value): raise RuntimeError('reference revision must be a 40-character commit SHA')
 return value

def urls(shot, rev):
 if not re.fullmatch(r'[0-9a-f]{40}',rev or ''): raise ValueError('invalid immutable reference SHA')
 refs=shot.get('reference_images') or []
 if not 1<=len(refs)<=5: raise ValueError(f'{shot["id"]}: expected 1–5 reference images')
 return [f'https://raw.githubusercontent.com/{REPOSITORY}/{rev}/production/hakamada58/reference/{rid}.png' for rid in refs]

def payload(shot, rev=None):
 rev=rev or revision()
 return {'model':MODEL,'prompt':shot['prompt'],'seconds':str(shot['duration']),'size':SIZE,
         'aspect_ratio':'16:9','mode':'reference','n':1,'seed':int(shot['seed']),'images':urls(shot,rev)}

def validate_payload(p,shot,project):
 if set(p)!=ALLOWED: raise ValueError(f'{shot["id"]}: unexpected Agnes payload fields {sorted(p)}')
 if FORBIDDEN.intersection(p): raise ValueError(f'{shot["id"]}: forbidden Agnes fields {sorted(FORBIDDEN.intersection(p))}')
 if p['model']!=MODEL or p['size']!=SIZE or p['aspect_ratio']!='16:9' or p['mode']!='reference' or p['n']!=1:
  raise ValueError(f'{shot["id"]}: invalid model/size/aspect/reference mode')
 if p['seconds']!=str(shot['duration']) or p['prompt']!=shot['prompt']:
  raise ValueError(f'{shot["id"]}: prompt/duration payload mismatch')
 if not p['prompt'].startswith('【STYLE】') or not p['prompt'].endswith(project['negative']):
  raise ValueError(f'{shot["id"]}: STYLE must lead and NEGATIVE must end prompt')
 if len(p['images'])!=len(shot['reference_images']) or not 1<=len(p['images'])<=5:
  raise ValueError(f'{shot["id"]}: images list does not match storyboard references')
 if any(not u.startswith('https://raw.githubusercontent.com/') for u in p['images']):
  raise ValueError(f'{shot["id"]}: reference URL is not public raw GitHub HTTPS')

def validate(project):
 shots=project['shots']
 if len(shots)!=30 or project['target_duration']!=180: raise ValueError('expected 30 shots / 180 seconds')
 if project.get('model')!=MODEL or project.get('source_size')!=SIZE: raise ValueError('wrong Agnes model/source size')
 refs={r['id'] for r in project.get('reference_images',[])}
 if len(refs)!=34 or len(project.get('reference_status',{}).get('approved_generated',[]))!=34 or project.get('reference_status',{}).get('pending'):
  raise ValueError('all 34 approved references must be declared')
 cursor=0; test_revision='a'*40
 for s in shots:
  if s['start']!=cursor or s['duration']!=6: raise ValueError(f'invalid timeline {s["id"]}')
  if not 1<=len(s.get('reference_images',[]))<=5 or not set(s['reference_images'])<=refs: raise ValueError(f'invalid references {s["id"]}')
  p=payload(s,test_revision); validate_payload(p,s,project); cursor+=s['duration']
 if cursor!=180: raise ValueError('timeline does not sum to 180 seconds')
 return True

def validate_bundle(project,rev):
 ledger=json.loads(APPROVALS_FILE.read_text(encoding='utf-8'))
 assets=ledger.get('assets',{}); expected={r['id']:r for r in project['reference_images']}
 if set(assets)!=set(expected): raise RuntimeError('approval ledger must cover exactly all 34 refs')
 for rid,item in expected.items():
  path=HERE/item['file']
  if not path.is_file() or path.stat().st_size<20000 or path.read_bytes()[:8]!=b'\x89PNG\r\n\x1a\n':
   raise RuntimeError(f'{rid}: missing/invalid PNG')
  if assets[rid].get('sha256')!=sha(path) or assets[rid].get('file')!=item['file']:
   raise RuntimeError(f'{rid}: image has changed since approval')
 if not rev: raise RuntimeError('missing immutable reference revision')

def inspect_clip(path,sid):
 import av
 from PIL import Image, ImageOps, ImageDraw
 container=av.open(str(path)); stream=next((s for s in container.streams if s.type=='video'),None)
 if stream is None: raise RuntimeError(f'{sid}: no video stream')
 duration=float(container.duration/av.time_base) if container.duration else float(stream.duration*stream.time_base)
 width,height=int(stream.width),int(stream.height)
 if not 4.5<=duration<=9.5 or width<640 or height<360: raise RuntimeError(f'{sid}: unsuitable returned video {duration:.2f}s {width}x{height}')
 sample_times=[duration*(i+.5)/9 for i in range(9)]; thumbs=[]; ix=0; last=None
 for frame in container.decode(stream):
  last=frame
  t=float(frame.pts*stream.time_base) if frame.pts is not None else 0
  while ix<len(sample_times) and t>=sample_times[ix]:
   im=frame.to_image().convert('RGB'); im=ImageOps.pad(im,(426,240),color=(12,12,12)); thumbs.append(im); ix+=1
  if ix==9: break
 if last is None: raise RuntimeError(f'{sid}: no decodable frames')
 while len(thumbs)<9:
  thumbs.append(ImageOps.pad(last.to_image().convert('RGB'),(426,240),color=(12,12,12)))
 sheet=Image.new('RGB',(1278,720),(12,12,12))
 for i,im in enumerate(thumbs[:9]): sheet.paste(im,((i%3)*426,(i//3)*240))
 qa=HERE/'qa'; qa.mkdir(parents=True,exist_ok=True); contact=qa/f'{sid}.jpg'; sheet.save(contact,quality=88)
 result={'duration_seconds':round(duration,3),'width':width,'height':height,'fps':str(stream.average_rate) if stream.average_rate else None,'bytes':path.stat().st_size,'decoded_ok':True,'contact_sheet':str(contact.relative_to(ROOT)),'visual_review':'pending'}
 (qa/f'{sid}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 container.close(); return result

def read_results():
 if RESULTS.is_file():
  try:return json.loads(RESULTS.read_text(encoding='utf-8'))
  except ValueError:pass
 return {'project':'袴田事件：58年','model':MODEL,'mode':'reference','phase':'prepared','shots':{}}

def save(doc):
 with LOCK: RESULTS.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def one(shot,doc,key,base,outdir,deadline,rev,project):
 sid=shot['id']; p=payload(shot,rev); validate_payload(p,shot,project); ph=hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True).encode()).hexdigest(); dest=outdir/f'{sid}.mp4'
 with LOCK: old=dict(doc.setdefault('shots',{}).get(sid,{}))
 if old.get('request_hash')!=ph and old:
  doc.setdefault('previous_results',{}).setdefault(sid,[]).append(old); old={}; doc['shots'][sid]={'id':sid}
 if old.get('request_hash')==ph and old.get('status')=='completed' and dest.exists() and sha(dest)==old.get('sha256'):
  print(sid+': verified completed result reused',flush=True); return True
 if not key:
  with LOCK: doc['shots'][sid]={'id':sid,'status':'blocked','request_hash':ph,'error':'AGNES_API_KEY is unavailable'};save(doc)
  return False
 try:
  video_id=old.get('video_id'); task_id=old.get('task_id')
  if not video_id:
   for attempt in range(8):
    with LOCK: doc['shots'][sid]={'id':sid,'status':'waiting_create_slot','request_hash':ph,'request_payload':p,'create_attempt':attempt+1};save(doc)
    GATE.acquire_creation(deadline)
    try: created=agnes.create_task(base,key,p,retries=1,retry_delay=75); break
    except agnes.RateLimited as exc:
     delay=max(REQUEST_INTERVAL_SECONDS,exc.retry_after or 0);GATE.defer(delay)
     with LOCK: doc['shots'][sid].update(status='rate_limited',cooldown_seconds=delay,error=str(exc)[:600]);save(doc)
   else: raise RuntimeError('Agnes create retry limit reached')
   video_id=created.get('video_id') or created.get('id') or created.get('task_id');task_id=created.get('task_id') or created.get('id')
   if not video_id: raise RuntimeError('Agnes returned no task ID')
   with LOCK: doc['shots'][sid].update(status='queued',video_id=str(video_id),task_id=str(task_id or ''),requested_seconds=int(p['seconds']));save(doc)
  final,url=agnes.poll_task(base,key,MODEL,str(video_id),str(task_id or '') or None,interval=25,timeout=max(30,deadline-time.monotonic()),max_failures=12,before_request=lambda:GATE.wait_unblocked(deadline),rate_limit_callback=GATE.defer)
  size=agnes.download(url,dest,retries=3,retry_delay=5); digest=sha(dest); qa=inspect_clip(dest,sid)
  with LOCK: doc['shots'][sid].update(status='completed',video_url=url,bytes=size,sha256=digest,final_response=final,inspection=qa,visual_reference_attached=True,visual_review='pending',updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()));save(doc)
  print(f'{sid}: completed, decoded and contact sheet ready',flush=True);return True
 except Exception as exc:
  msg=str(exc).replace(key,'[REDACTED]') if key else str(exc)
  with LOCK: doc.setdefault('shots',{}).setdefault(sid,{'id':sid}).update(status='failed',error=msg[:700],updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()));save(doc)
  print(f'{sid}: failed: {msg[:300]}',file=sys.stderr,flush=True);return False

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--validate',action='store_true');ap.add_argument('--only',default='');ap.add_argument('--workers',type=int,default=2);ap.add_argument('--out',default='work/hakamada58/clips');ap.add_argument('--budget-hours',type=float,default=4.5)
 args=ap.parse_args(); project=json.loads(PLAN.read_text(encoding='utf-8'));validate(project)
 if args.validate: print('VALID: 30 shots / 180s; Agnes 2.5 Flash mode=reference; 34 refs; 1–5 immutable image URLs per shot');return 0
 rev=revision();validate_bundle(project,rev)
 ids={x.strip() for x in args.only.split(',') if x.strip()}; unknown=ids-{s['id'] for s in project['shots']}
 if unknown: raise ValueError('unknown shot IDs: '+','.join(sorted(unknown)))
 shots=[s for s in project['shots'] if not ids or s['id'] in ids]
 outdir=ROOT/args.out;outdir.mkdir(parents=True,exist_ok=True);doc=read_results();doc.update(phase='generating',reference_revision=rev,mode='reference',model=MODEL);save(doc)
 key=os.getenv('AGNES_API_KEY','').strip();base=(os.getenv('AGNES_BASE_URL','').strip() or agnes.DEFAULT_BASE_URL).rstrip('/');deadline=time.monotonic()+args.budget_hours*3600
 with concurrent.futures.ThreadPoolExecutor(max_workers=min(2,max(1,args.workers))) as pool: outcomes=list(pool.map(lambda s:one(s,doc,key,base,outdir,deadline,rev,project),shots))
 count=sum(row.get('status')=='completed' for row in doc['shots'].values())
 doc['phase']='clips_ready' if count==30 else 'batch_ready' if all(outcomes) else 'clips_incomplete';save(doc)
 print(f'COMPLETE: {count}/30 clips recorded; selected={len(shots)}',flush=True);return 0 if all(outcomes) else 1
if __name__=='__main__': raise SystemExit(main())
