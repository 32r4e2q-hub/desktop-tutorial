#!/usr/bin/env python3
"""Generate Lee Hyung-ho case reenactment clips with Zhipu CogVideoX-Flash only.

No Agnes or other video-generation provider is called. Provider receipts and
SHA-256 hashes are checkpointed to the fixed Arena branch; footage bytes remain
outside Git and are restored from their verified Zhipu CDN receipts for rendering.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PLAN=HERE/'story.json'; RESULTS=HERE/'results.json'
BRANCH='arena/04ec3850-desktop-tutorial'
MODEL='cogvideox-flash'; GRID_SECONDS=4
sys.path.insert(0,str(HERE))
from media import ensure_tools, inspect_clip


def read_json(path,default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def full_payload(project,shot):
    # CogVideoX-Flash receives the deterministic character reference as an
    # image-to-video start frame, not as a different video-generation provider.
    prompt=(project['style_prefix']+shot['prompt']).strip()
    if len(prompt)>2600: prompt=prompt[:2600]
    payload={'model':MODEL,'prompt':prompt,'quality':'quality','with_audio':False}
    reference=shot.get('reference_image')
    if reference:
        path=HERE/reference
        if not path.is_file(): raise FileNotFoundError(f"Missing identity reference for {shot['id']}: {path}")
        mime='image/jpeg' if path.suffix.lower() in ('.jpg','.jpeg') else 'image/png'
        encoded=base64.b64encode(path.read_bytes()).decode('ascii')
        payload['image_url']=f'data:{mime};base64,{encoded}'
    return payload

def request_hash(project,shot):
    payload=full_payload(project,shot)
    if 'image_url' in payload:
        payload['reference_image_sha256']=hashlib.sha256(payload.pop('image_url').encode('ascii')).hexdigest()
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def reference_sha256(shot):
    reference=shot.get('reference_image')
    return digest(HERE/reference) if reference else None

def validate(project):
    shots=project.get('shots') or []
    if project.get('target_duration')!=180 or len(shots)!=45 or len(shots)*GRID_SECONDS!=180:
        raise ValueError('Expected 45-shot, 180-second plan')
    if project.get('model')!=MODEL: raise ValueError(f'Project model must be {MODEL}')
    if len({x['id'] for x in shots})!=45: raise ValueError('Duplicate shot IDs')
    characters=project.get('characters') or {}
    for i,shot in enumerate(shots):
        if shot['id']!=f'S{i+1:02d}' or shot['start']!=i*4 or shot['duration']!=4:
            raise ValueError(f'Invalid timeline at {shot.get("id")}')
        if shot['kind']=='cogvideo':
            if not shot.get('prompt','').strip() or 'TODO' in shot['prompt']:
                raise ValueError(f'{shot["id"]}: missing prompt')
            unknown=set(shot.get('character_ids',[]))-set(characters)
            if unknown: raise ValueError(f'{shot["id"]}: unknown character IDs {sorted(unknown)}')
            reference=shot.get('reference_image','')
            if reference and not (HERE/reference).is_file():
                raise ValueError(f'{shot["id"]}: missing identity reference image {reference}')
            expected={characters[cid].get('reference_image','') for cid in shot.get('character_ids',[])}
            expected.discard('')
            if reference and expected and expected!={reference}:
                raise ValueError(f'{shot["id"]}: reference image differs from the canonical character bible')
            if shot.get('face_visible') and shot.get('character_ids') and not reference:
                raise ValueError(f'{shot["id"]}: face-visible recurring identity lacks its canonical reference')
            if len(shot.get('character_ids',[]))>1 and not reference:
                raise ValueError(f'{shot["id"]}: multi-person shot requires a shared identity reference')
            payload=full_payload(project,shot)
            if payload['model']!=MODEL or payload.get('with_audio') is not False:
                raise ValueError('Wrong CogVideoX provider/audio policy')
        elif shot['kind']=='graphic':
            if not shot.get('graphic','').strip(): raise ValueError(f'{shot["id"]}: empty graphic')
        else: raise ValueError(f'{shot["id"]}: unsupported kind {shot["kind"]}')
    if sum(x['kind']=='cogvideo' for x in shots)!=38 or sum(x['kind']=='graphic' for x in shots)!=7:
        raise ValueError('Expected 38 CogVideoX clips + 7 graphics')
    if any('TODO' in json.dumps(x,ensure_ascii=False) for x in (project.get('presentation'),project.get('chapters'))):
        raise ValueError('Content TODO remains')

def validate_audio(project):
    manifest=read_json(HERE/'audio/manifest.json',{})
    clips={x['id']:x for x in manifest.get('clips',[])}
    for chapter in project['chapters']:
        row=clips.get(chapter['id'],{}); path=HERE/'audio'/row.get('file','missing')
        if row.get('text')!=chapter['text'] or not path.is_file() or digest(path)!=row.get('sha256'):
            raise ValueError('Narration text/audio mismatch: '+chapter['id'])

def obj_get(value,name,default=None):
    if isinstance(value,dict): return value.get(name,default)
    return getattr(value,name,default)

def git(*args,check=True):
    result=subprocess.run(['git',*args],cwd=ROOT,text=True,capture_output=True,timeout=120)
    if check and result.returncode: raise RuntimeError(result.stdout+result.stderr)
    return result.stdout.strip()

def checkpoint(doc,label,sid=None,files=(),publish=False,**values):
    if sid:
        row=doc.setdefault('shots',{}).setdefault(sid,{'id':sid}); row.update(values)
        row['updated_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    doc['updated_at']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    doc['run_id']=os.getenv('GITHUB_RUN_ID')
    RESULTS.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if not publish:return
    paths=[str(RESULTS.relative_to(ROOT))]+[str(Path(p).relative_to(ROOT)) for p in files if Path(p).exists()]
    git('add','--',*paths)
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
        git('commit','-m',f'lee_hyung_ho1991: {label}','--',*paths)
        for attempt in range(5):
            if subprocess.run(['git','push','origin',BRANCH],cwd=ROOT).returncode==0: break
            git('fetch','origin',BRANCH); git('rebase','FETCH_HEAD')
            time.sleep(2+attempt*2)
        else: raise RuntimeError('checkpoint push failed')

def download(url,dest):
    dest.parent.mkdir(parents=True,exist_ok=True); temp=dest.with_suffix('.part')
    request=urllib.request.Request(url,headers={'User-Agent':'arena-lee-hyung-ho1991-cogvideo/1.0'})
    with urllib.request.urlopen(request,timeout=240) as r,temp.open('wb') as f:
        while True:
            b=r.read(1024*1024)
            if not b:break
            f.write(b)
    temp.replace(dest)

def retryable(exc):
    text=str(exc).lower()
    if any(x in text for x in ('1113','余额不足','无可用资源包')):
        return False
    return any(x in text for x in ('1234','网络错误','network error','1305','429','访问量过大',
                                   'rate','timeout','timed out','temporar','connection','502','503','504'))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--payload',default='{}'); ap.add_argument('--validate',action='store_true'); ap.add_argument('--require-audio',action='store_true'); ap.add_argument('--publish',action='store_true'); ap.add_argument('--prune-failed',action='store_true'); args=ap.parse_args()
    project=read_json(PLAN,{}); validate(project)
    if args.require_audio: validate_audio(project)
    if args.validate:
        audio_note='; narration hashes match' if args.require_audio else '; narration is a separate workflow stage'
        print('VALID: 180-second plan; 45 shots; 38 CogVideoX-Flash sources; 7 graphics; identity references ready'+audio_note); return 0
    doc=read_json(RESULTS,{'project':project['title'],'model':MODEL,'provider':'Zhipu AI','shots':{}})
    doc.update(model=MODEL,provider='Zhipu AI',workflow_policy='lee-hyung-ho-cogvideox-reference-v2',
               identity_policy='image-to-video input is pinned by per-shot reference SHA-256; same visible role reuses the same reference asset; visual continuity still requires contact-sheet review')
    if args.prune_failed:
        stale=[sid for sid,row in doc.get('shots',{}).items() if row.get('status')=='failed' and not row.get('video_url')]
        for sid in stale:doc['shots'].pop(sid,None)
        checkpoint(doc,'pruned failed tasks',publish=args.publish); print('PRUNED',stale); return 0
    if args.publish:
        if os.getenv('GITHUB_ACTIONS')!='true' or git('branch','--show-current')!=BRANCH:
            raise RuntimeError('Publish only from the fixed Arena branch in Actions')
        git('config','user.name','github-actions[bot]')
        git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    options=json.loads(args.payload or '{}'); only={x.strip() for x in str(options.get('only','')).split(',') if x.strip()}
    shots=[x for x in project['shots'] if x['kind']=='cogvideo']
    if only-{x['id'] for x in shots}: raise ValueError('Unknown/non-CogVideo shot: '+','.join(sorted(only)))
    if only:shots=[x for x in shots if x['id'] in only]
    key=os.getenv('ZHIPUAI_API_KEY','').strip()
    if not key: raise RuntimeError('ZHIPUAI_API_KEY is unavailable')
    from zhipuai import ZhipuAI
    client=ZhipuAI(api_key=key)
    sources=ROOT/'work/lee_hyung_ho1991/sources'; qa=HERE/'qa'; sources.mkdir(parents=True,exist_ok=True); qa.mkdir(parents=True,exist_ok=True)
    ensure_tools(); started=time.monotonic(); deadline=started+330*60
    doc['phase']='generating_sources'; doc['required_generated_shots']=[x['id'] for x in project['shots'] if x['kind']=='cogvideo']
    checkpoint(doc,'CogVideoX cloud generation started',publish=args.publish)
    failures=[]
    for index,shot in enumerate(shots,1):
        sid=shot['id']; wanted=request_hash(project,shot); old=doc.get('shots',{}).get(sid,{})
        if old.get('status')=='completed' and old.get('request_hash')==wanted and old.get('video_url') and old.get('sha256'):
            print(f'{sid}: verified receipt already exists; no new generation',flush=True); continue
        if old and old.get('request_hash')!=wanted:
            doc.setdefault('previous_results',{}).setdefault(sid,[]).append(old); doc['shots'][sid]={'id':sid}
        if time.monotonic()>deadline: raise RuntimeError('Generation deadline reached; rerun resumes from receipts')
        payload=full_payload(project,shot); task_id=None
        identity_meta={'character_ids':shot.get('character_ids',[]),'face_visible':shot.get('face_visible',False),
                       'reference_image':shot.get('reference_image') or None,
                       'reference_sha256':reference_sha256(shot)}
        failure_history=list(doc.get('shots',{}).get(sid,{}).get('task_failures',[]))
        attempt_offset=len(failure_history)
        task_id=None; result=None; completed_task=False; max_task_attempts=3
        for attempt_index in range(1,max_task_attempts+1):
            task_attempt=attempt_offset+attempt_index
            checkpoint(doc,f'{sid} submitting attempt {task_attempt}',sid,publish=args.publish,
                       status='submitting',request_hash=wanted,error=None,task_attempt=task_attempt,
                       task_failures=failure_history,**identity_meta)
            for submit_attempt in range(1,21):
                try:
                    response=client.videos.generations(**payload); task_id=obj_get(response,'id')
                    if not task_id: raise RuntimeError(f'No task id: {response}')
                    break
                except Exception as exc:
                    if not retryable(exc) or submit_attempt==20: raise
                    wait=min(120,15+submit_attempt*5)
                    print(f'{sid}: submit throttled attempt {submit_attempt}, wait {wait}s: {str(exc)[:180]}',flush=True)
                    time.sleep(wait)
            checkpoint(doc,f'{sid} queued attempt {task_attempt}',sid,publish=args.publish,
                       status='queued',task_id=str(task_id),request_hash=wanted,task_attempt=task_attempt,
                       task_failures=failure_history,**identity_meta)
            status=''
            for poll in range(1,241):
                try:
                    result=client.videos.retrieve_videos_result(id=task_id)
                    status=str(obj_get(result,'task_status','')).upper()
                    print(f'{sid} [{index}/{len(shots)}] attempt {task_attempt} poll {poll}: {status}',flush=True)
                    if status=='SUCCESS':
                        completed_task=True
                        break
                    if status=='FAIL':
                        error_value=obj_get(result,'error',None)
                        raw_error=repr(error_value if error_value is not None else result)[:1600]
                        error=error_value or {}
                        code=str(obj_get(error,'code',''))
                        message=str(obj_get(error,'message',''))
                        failure_text=code+' '+message+' '+raw_error
                        quota_failure=any(token in failure_text for token in ('1113','余额不足','无可用资源包'))
                        transient_failure=not quota_failure and (not code and not message or retryable(RuntimeError(failure_text)))
                        detail=f'Provider task failed with code {code or "unknown"}: {message or raw_error}'
                        failure_history.append({'task_id':str(task_id),'code':code,'message':message,
                                                'raw_error':raw_error,'attempt':task_attempt})
                        if transient_failure and attempt_index<max_task_attempts:
                            print(f'{sid}: transient CogVideoX task failure; submitting a fresh task',flush=True)
                            checkpoint(doc,f'{sid} transient provider failure; retrying',sid,publish=args.publish,
                                       status='retrying',task_id=str(task_id),request_hash=wanted,
                                       task_attempt=task_attempt,task_failures=failure_history,error=detail,
                                       **identity_meta)
                            time.sleep(15*task_attempt)
                            break
                        checkpoint(doc,f'{sid} provider task failed',sid,publish=args.publish,status='failed',
                                   task_id=str(task_id),request_hash=wanted,task_attempt=task_attempt,
                                   task_failures=failure_history,error=detail,**identity_meta)
                        raise RuntimeError('Provider task failed; see the checkpointed error details')
                    time.sleep(10)
                except Exception as exc:
                    if retryable(exc) and poll<240:
                        time.sleep(min(60,10+poll//10)); continue
                    raise
            else:
                raise RuntimeError(f'{sid}: polling timeout for task {task_id}')
            if completed_task:
                break
            if status=='FAIL' and attempt_index<max_task_attempts and retryable(
                    RuntimeError(str(failure_history[-1].get('code',''))+' '+str(failure_history[-1].get('message','')))):
                continue
        if not completed_task:
            raise RuntimeError(f'{sid}: no CogVideoX task succeeded after {max_task_attempts} attempts')
        video_result=obj_get(result,'video_result') or []; first=video_result[0] if video_result else None; url=obj_get(first,'url') if first else None
        if not url: raise RuntimeError(f'{sid}: SUCCESS without video URL: {result}')
        dest=sources/f'{sid}.mp4'; download(url,dest); checksum=digest(dest)
        try:
            info=inspect_clip(dest,qa,sid)
        except Exception as exc:
            checkpoint(doc,f'{sid} failed inspection',sid,publish=args.publish,status='failed',request_hash=wanted,task_id=str(task_id),video_url=url,error=str(exc)[:600],**identity_meta); failures.append(sid); continue
        files=[qa/f'{sid}.jpg',qa/f'{sid}.json']
        checkpoint(doc,f'{sid} media and QA ready',sid,files=files,publish=args.publish,status='completed',request_hash=wanted,task_id=str(task_id),video_url=url,sha256=checksum,bytes=dest.stat().st_size,media=info,error=None,**identity_meta)
    complete=[sid for sid,row in doc.get('shots',{}).items() if row.get('status')=='completed']
    missing=sorted(set(doc['required_generated_shots'])-set(complete))
    doc['phase']='selected_sources_ready' if only and not failures else 'sources_ready' if not missing else 'generation_incomplete'
    checkpoint(doc,doc['phase'],publish=args.publish)
    if failures or (not only and missing):
        raise RuntimeError('CogVideoX generation incomplete: '+','.join(failures or missing))
    print(f'COMPLETE {len(shots)} requested clips; model={MODEL}',flush=True); return 0

if __name__=='__main__': raise SystemExit(main())
