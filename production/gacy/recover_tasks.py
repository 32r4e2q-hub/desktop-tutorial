"""Read-only provider recovery: query known task IDs, never submit a generation.
A verified completed identity clip is downloaded and exposed as an experimental fragment,
not a finished film. The historical squirrel control is explicitly not Gacy footage.
"""
import hashlib
import json
import re
import time
from pathlib import Path

CONTROL_TASK = '20261024101554a7aa2599cbe04555'  # Existing success, GitHub issue #44.


def safe_error(exc):
    status=getattr(exc,'status_code',0) or 0
    response=getattr(exc,'response',None)
    data={}
    if response is not None:
        try:data=response.json()
        except (ValueError,TypeError):pass
    error=data.get('error',data) if isinstance(data,dict) else {}
    code=re.sub(r'[^A-Za-z0-9_-]','',str(error.get('code','query_error')))[:32]
    return {'http_status':status,'error_code':code}


def recover(engine):
    file=engine.HERE/'identity-probe/receipts.json'
    identity=json.loads(file.read_text()) if file.exists() else {'shots':{}}
    report={'status':'checking','checked_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'new_generation_requests':0,'tasks':[]}
    dest=engine.HERE/'recovery-report.json'
    client=engine.make_video_client()
    tasks=[('historical-control',CONTROL_TASK,None)]
    for sid,shot in identity.get('shots',{}).items():
        if shot.get('task_id') and shot.get('status')!='blocked_by_provider_moderation':
            tasks.append((sid,shot['task_id'],shot))
    for sid,task_id,receipt in tasks:
        row={'id':sid,'task_id':task_id,'is_film_footage':False if receipt is None else 'experimental_identity_clip_only'}
        report['tasks'].append(row)
        try:
            response=client.videos.retrieve_videos_result(id=task_id)
            data=response if isinstance(response,dict) else response.model_dump()
            status=str(data.get('task_status','UNKNOWN')).upper()
            row['provider_status']=status
            if receipt is not None:
                receipt.update(last_provider_status=status,last_polled_utc=report['checked_utc'])
            if status=='SUCCESS':
                results=data.get('video_result',[])
                if not results or not results[0].get('url'):
                    raise RuntimeError('SUCCESS without a video URL')
                row['download_url_returned']=True
                target=engine.WORK/'recovered'/(sid+'.mp4')
                if receipt is not None:
                    target=engine.WORK/'identity-probe'/(sid+'.mp4')
                engine.download(results[0]['url'],target)
                info=engine.probe(target)
                video=next(s for s in info['streams'] if s.get('codec_type')=='video')
                sha=hashlib.sha256(target.read_bytes()).hexdigest()
                row.update(downloaded=True,sha256=sha,bytes=target.stat().st_size,
                           duration=engine.seconds(target),width=video['width'],height=video['height'])
                if receipt is not None:
                    receipt.update(status='downloaded',sha256=sha,duration=row['duration'])
                    folder=engine.HERE/'identity-probe';folder.mkdir(exist_ok=True)
                    for n,fraction in enumerate((.15,.5,.85)):
                        engine.run('ffmpeg','-y','-ss',row['duration']*fraction,'-i',target,
                                   '-frames:v','1','-vf','scale=960:-1',folder/f'{sid}-{n}.jpg')
                    # Expose this small experimental fragment honestly, not as the final movie.
                    if target.stat().st_size<50000000:
                        import shutil
                        delivery=engine.ROOT/'交付';delivery.mkdir(exist_ok=True)
                        shutil.copyfile(target,delivery/f'盖西_同脸实验_{sid}_原始片段.mp4')
            elif status in ('FAIL','FAILED'):
                row['terminal']=True
                row['failure_details']=engine.task_failure_details(data)
                if receipt is not None:
                    receipt.update(status='provider_failed_requires_review',failure_details=row['failure_details'])
            elif status in ('PROCESSING','PENDING','QUEUED','SUBMITTED'):
                row['awaiting_existing_task']=True
            else:
                row['requires_schema_review']=True
        except Exception as exc:
            row.update(safe_error(exc))
            row['downloaded']=False
            row['failure_phase']='download_or_validation' if row.get('provider_status')=='SUCCESS' else 'provider_query'
            row['exception_type']=type(exc).__name__
            if row['error_code']=='1301' and receipt is not None:
                receipt.update(status='blocked_by_provider_moderation',no_automatic_resubmit=True)
        engine.save(dest,report)
        if receipt is not None:engine.save(file,identity)
    report.update(status='checked',verified_downloads=sum(x.get('downloaded',False) for x in report['tasks']))
    engine.save(dest,report)
    states=[s.get('status') for s in identity.get('shots',{}).values()]
    if 'provider_failed_requires_review' in states:
        identity['status']='provider_terminal_failure'
    elif 'blocked_by_provider_moderation' in states:
        identity['status']='blocked_by_provider_moderation'
    elif any(t.get('awaiting_existing_task') for t in report['tasks'] if t['id']!='historical-control'):
        identity['status']='awaiting_provider'
    elif all(identity.get('shots',{}).get(sid,{}).get('status')=='downloaded' for sid in ('C1-A','C1-B')):
        identity['status']='clips_downloaded_identity_review_required'
    elif 'downloaded' in states:
        identity['status']='partial_identity_clips_downloaded'
    engine.save(file,identity)
    retry_file=engine.HERE/'identity-probe/retry-status.json'
    if retry_file.exists():
        retry=json.loads(retry_file.read_text())
        retry.update(status=identity.get('status','checked'),reconciled_utc=report['checked_utc'],same_actor_verified=False)
        engine.save(retry_file,retry)
    return report
