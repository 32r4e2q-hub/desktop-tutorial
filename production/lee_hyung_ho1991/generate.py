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
BRANCH='arena/1f36798e-desktop-tutorial'
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
    prompt=(shot.get('style_prefix', project['style_prefix'])+shot['prompt']).strip()
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
    return any(x in text for x in ('1234','网络错误','network error','1302','1303','1305','429','访问量过大',
                                   'rate','timeout','timed out','temporar','connection','502','503','504'))

def resumable_task(row, wanted):
    """Never submit duplicate paid work after an interrupted polling run."""
    if row.get('request_hash') == wanted and row.get('status') in ('queued', 'processing'):
        return row.get('task_id')
    return None

def merge_recovered_receipts(project, doc):
    recovered = read_json(HERE/'recovered-receipts.json', {})
    shots = {s['id']: s for s in project['shots'] if s['kind'] == 'cogvideo'}
    for sid, row in recovered.get('shots', {}).items():
        shot = shots.get(sid)
        if not shot or not receipt_ready(row, request_hash(project, shot)):
            raise ValueError(f'{sid}: recovered receipt does not match current request')
        if row.get('reference_sha256') != reference_sha256(shot):
            raise ValueError(f'{sid}: recovered character reference mismatch')
        if receipt_ready(doc.get('shots', {}).get(sid, {}), request_hash(project, shot)):
            continue
        old = doc.setdefault('shots', {}).get(sid)
        if old:
            doc.setdefault('previous_results', {}).setdefault(sid, []).append(dict(old))
        doc['shots'][sid] = dict(row)
        doc['shots'][sid]['recovered_from_branch'] = recovered['source_branch']
        print(f'{sid}: recovered matching successful receipt; video bytes must pass SHA-256 on restore', flush=True)


def receipt_ready(row, wanted):
    return (row.get('request_hash') == wanted and row.get('status') == 'completed'
            and bool(row.get('video_url')) and bool(row.get('sha256')))


def collect_clip(doc, shot, sources, qa, publish):
    """Persist provider URL before IO; a download failure never regenerates video."""
    sid = shot['id']; row = doc['shots'][sid]
    dest = sources / f'{sid}.mp4'
    if not dest.exists() or (row.get('sha256') and digest(dest) != row['sha256']):
        download(row['video_url'], dest)
    checksum = digest(dest)
    if row.get('sha256') and row['sha256'] != checksum:
        raise RuntimeError(f'{sid}: downloaded bytes differ from saved SHA-256')
    info = inspect_clip(dest, qa, sid)
    checkpoint(doc, f'{sid} media and QA ready', sid,
               files=[qa / f'{sid}.jpg', qa / f'{sid}.json'], publish=publish,
               status='completed', sha256=checksum, bytes=dest.stat().st_size,
               media=info, error=None)


def run_queue(client, project, shots, doc, sources, qa, publish,
              window=3, budget=240*60, max_task_attempts=2, cooldown_seconds=60):
    """One writer, bounded cloud concurrency, fair polling and capped retries.

    PROCESSING never frees a slot or triggers duplicate work. All existing task
    IDs are polled, even if they exceed the window during recovery. Time budget
    expiry preserves those IDs for the next run. Download retries reuse URLs.
    """
    deadline = time.monotonic() + budget
    attempts = {}; download_attempts = {}; next_poll = {}; retry_at = {}; pending = []
    active = {}; hashes = {s['id']: request_hash(project, s) for s in shots}
    for shot in shots:
        sid = shot['id']; row = doc.get('shots', {}).get(sid, {})
        if row and row.get('request_hash') != hashes[sid]:
            doc.setdefault('previous_results', {}).setdefault(sid, []).append(dict(row))
            doc['shots'][sid] = {'id': sid}
            row = doc['shots'][sid]
        if receipt_ready(row, hashes[sid]):
            continue
        if resumable_task(row, hashes[sid]) or (row.get('status') == 'generated' and row.get('video_url')):
            active[sid] = shot
            attempts[sid] = 1
        else:
            pending.append(shot)
    # Untouched work before previously failed shots.
    pending.sort(key=lambda s: len(doc.get('shots', {}).get(s['id'], {}).get('task_failures', [])))
    submit_after = 0
    while (pending or active) and time.monotonic() < deadline:
        # Poll EVERY live task before filling slots; no 30-minute per-shot loop.
        for sid, shot in list(active.items()):
            if time.monotonic() >= deadline:
                break
            if time.monotonic() < next_poll.get(sid, 0):
                continue
            row = doc['shots'][sid]
            if row.get('status') != 'generated':
                try:
                    result = client.videos.retrieve_videos_result(id=row['task_id'])
                except Exception as exc:
                    if not retryable(exc):
                        raise
                    print(f'{sid}: polling transport error; keeping task ID: {str(exc)[:160]}', flush=True)
                    next_poll[sid] = time.monotonic() + 30
                    continue
                status = str(obj_get(result, 'task_status', '')).upper()
                print(f'{sid}: {status}; live={len(active)} pending={len(pending)}', flush=True)
                if status == 'FAIL':
                    error = obj_get(result, 'error') or {}
                    code = str(obj_get(error, 'code', ''))
                    message = str(obj_get(error, 'message', ''))
                    detail = f'{code} {message}'
                    history = list(row.get('task_failures', []))
                    history.append({'task_id': row['task_id'], 'code': code, 'message': message,
                                    'raw_error': repr(result)[:1600]})
                    checkpoint(doc, f'{sid} provider failed', sid, publish=publish,
                               status='failed', task_failures=history, error=detail)
                    active.pop(sid)
                    if any(token in detail for token in ('1113', '余额不足', '无可用资源包')):
                        raise RuntimeError('Provider quota exhausted; stopped without retrying')
                    if attempts.get(sid, 1) < max_task_attempts and (not code and not message or retryable(RuntimeError(detail))):
                        retry_at[sid] = time.monotonic() + cooldown_seconds
                        pending.append(shot)  # one retry, after untouched work
                    continue
                if status != 'SUCCESS':
                    next_poll[sid] = time.monotonic() + 10
                    continue
                videos = obj_get(result, 'video_result') or []
                url = obj_get(videos[0], 'url') if videos else None
                if not url:
                    raise RuntimeError(f'{sid}: provider SUCCESS without a URL')
                checkpoint(doc, f'{sid} provider succeeded; download pending', sid,
                           publish=publish, status='generated', video_url=url, error=None)
            try:
                collect_clip(doc, shot, sources, qa, publish)
            except Exception as exc:
                download_attempts[sid] = download_attempts.get(sid, 0) + 1
                checkpoint(doc, f'{sid} download or inspection deferred', sid, publish=publish,
                           status='generated', error=str(exc)[:600])
                # Do not repeatedly block the queue on broken CDN/inspection.
                if download_attempts[sid] >= 3:
                    active.pop(sid)
                else:
                    next_poll[sid] = time.monotonic() + 30
                continue
            active.pop(sid)
        while pending and len(active) < window and time.monotonic() >= submit_after and time.monotonic() < deadline:
            eligible = [s for s in pending if time.monotonic() >= retry_at.get(s['id'], 0)]
            if not eligible:
                break
            shot = eligible[0]; sid = shot['id']
            try:
                response = client.videos.generations(**full_payload(project, shot))
            except Exception as exc:
                if not retryable(exc):
                    raise
                # Back off submissions, but keep collecting other active tasks.
                detail=str(exc)[:180]
                print(f'Submission paused 30s ({sid}): {detail}', flush=True)
                history=doc.setdefault('submission_backoffs',[])
                history.append({'shot':sid,'error':detail,'at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
                # A synchronous provider rejection must not pin the entire queue to one prompt.
                pending.remove(shot);pending.append(shot)
                if len(history)==1 or len(history)%5==0:
                    checkpoint(doc,'provider submission backoff; task IDs retained',publish=publish)
                submit_after = time.monotonic() + 30
                break
            task_id = obj_get(response, 'id')
            if not task_id:
                raise RuntimeError(f'{sid}: provider did not return a task ID')
            pending.remove(shot); attempts[sid] = attempts.get(sid, 0) + 1
            checkpoint(doc, f'{sid} queued', sid, publish=publish,
                       status='queued', task_id=str(task_id), request_hash=hashes[sid], error=None,
                       task_attempt=attempts[sid], character_ids=shot.get('character_ids', []),
                       face_visible=shot.get('face_visible', False),
                       reference_image=shot.get('reference_image') or None,
                       reference_sha256=reference_sha256(shot))
            active[sid] = shot
        if pending or active:
            time.sleep(min(2, max(0, deadline-time.monotonic())))
    return [s['id'] for s in shots if not receipt_ready(doc.get('shots', {}).get(s['id'], {}), hashes[s['id']])]


def queue_policy(options):
    bounds = {'window': (1, 3, 3), 'max_task_attempts': (1, 3, 2),
              'budget_minutes': (1, 240, 240), 'cooldown_seconds': (0, 300, 60)}
    policy = {}
    for key, (low, high, default) in bounds.items():
        value = options.get(key, default)
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f'{key} must be an integer between {low} and {high}')
        policy[key] = value
    policy['budget'] = policy.pop('budget_minutes') * 60
    return policy


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
    policy=queue_policy(options)
    shots=[x for x in project['shots'] if x['kind']=='cogvideo']
    if only-{x['id'] for x in shots}: raise ValueError('Unknown/non-CogVideo shot: '+','.join(sorted(only)))
    if only:shots=[x for x in shots if x['id'] in only]
    # A repeatedly failing shot must not starve every unattempted shot.
    shots.sort(key=lambda shot: len(doc.get('shots',{}).get(shot['id'],{}).get('task_failures',[])))
    key=os.getenv('ZHIPUAI_API_KEY','').strip()
    if not key: raise RuntimeError('ZHIPUAI_API_KEY is unavailable')
    from zhipuai import ZhipuAI
    client=ZhipuAI(api_key=key, timeout=60.0, max_retries=0)
    sources=ROOT/'work/lee_hyung_ho1991/sources'; qa=HERE/'qa'; sources.mkdir(parents=True,exist_ok=True); qa.mkdir(parents=True,exist_ok=True)
    ensure_tools()
    merge_recovered_receipts(project,doc)
    doc['phase']='generating_sources'
    doc['required_generated_shots']=[x['id'] for x in project['shots'] if x['kind']=='cogvideo']
    checkpoint(doc,'fair queue generation started',publish=args.publish)
    doc['queue_policy']=policy
    print('QUEUE_POLICY',json.dumps(policy),flush=True)
    failures=run_queue(client,project,shots,doc,sources,qa,args.publish,**policy)
    complete=[sid for sid,row in doc.get('shots',{}).items() if row.get('status')=='completed']
    missing=sorted(set(doc['required_generated_shots'])-set(complete))
    doc['phase']='selected_sources_ready' if only and not failures else 'sources_ready' if not missing else 'generation_incomplete'
    checkpoint(doc,doc['phase'],publish=args.publish)
    if failures or (not only and missing):
        raise RuntimeError('CogVideoX generation incomplete: '+','.join(failures or missing))
    print(f'COMPLETE {len(shots)} requested clips; model={MODEL}',flush=True); return 0

if __name__=='__main__': raise SystemExit(main())
