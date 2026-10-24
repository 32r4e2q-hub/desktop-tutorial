"""Bounded free CogVideoX reference-identity experiment, not an identity guarantee.
Two independently animated camera/action clips share one canonical fictional face image.
A capacity rejection or moderation block is never replaced by text-only generation.
"""
from pathlib import Path
import base64
import hashlib
import json
import time

PROMPTS = [
    ('C1-A', 'A fictional stocky middle-aged adult man with a round clean-shaven face and short light-brown hair, matching the supplied reference. In a softly lit period room, he gently turns his head a little to the left and lifts a plain ceramic cup. Eyes blink naturally, fingers and shoulders move continuously. One slow medium camera arc, face clearly visible throughout. Cinematic stylized 3D animation, warm amber and cool blue light, 16:9, plain unlettered props.'),
    ('C1-B', 'A fictional stocky middle-aged adult man with a round clean-shaven face and short light-brown hair, matching the supplied reference. In a softly lit period room, he gently turns his head a little to the right and folds one plain sheet of paper. Eyes blink naturally, fingers and shoulders move continuously. One slow medium camera approach, face clearly visible throughout. Cinematic stylized 3D animation, warm amber and cool blue light, 16:9, plain unlettered props.'),
]


def submit(engine, payload):
    for attempt in range(2):
        try:
            result = engine.make_video_client().videos.generations(**payload)
            data = result if isinstance(result, dict) else result.model_dump()
            engine.record_api_attempt('/videos/generations', payload, 200, '', attempt+1)
            return data
        except engine.ProviderError:
            raise
        except Exception as exc:
            response = getattr(exc, 'response', None)
            if response is None:
                raise RuntimeError('Identity probe POST outcome unknown; no blind resubmission') from None
            status = response.status_code
            try:
                body = response.json()
                code = str(body.get('error', {}).get('code', 'unknown'))
            except (ValueError, TypeError, AttributeError):
                code = 'non_json'
            engine.record_api_attempt('/videos/generations', payload, status, code, attempt+1)
            error = engine.ProviderError('/videos/generations', status, code)
            if not error.transient or attempt == 1:
                raise error from None
            time.sleep(30)
    raise RuntimeError('Identity probe retry budget exhausted')


def run_probe(engine):
    folder = engine.HERE / 'identity-probe'
    folder.mkdir(exist_ok=True)
    record = folder / 'receipts.json'
    state = json.loads(record.read_text()) if record.exists() else {'shots': {}}
    reference = engine.HERE / 'references/盖西.jpg'
    ref_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
    state.update(reference_sha256=ref_hash, reference_path='references/盖西.jpg',
        status='running', same_actor_verified=False,
        experiment='one canonical reference image, two independent animated clips',
        limitations='Successful generation is not proof of stable identity; inspect beginning/middle/end and compare across clips.')
    engine.save(record, state)
    for sid, prompt in PROMPTS:
        payload = {'model':'cogvideox-flash', 'quality':'speed', 'prompt':prompt,
                   'image_url':'data:image/jpeg;base64,'+base64.b64encode(reference.read_bytes()).decode()}
        digest = hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        shot = state['shots'].get(sid, {})
        if shot.get('payload_sha256') != digest:
            if shot:
                state.setdefault('previous_results', {}).setdefault(sid, []).append(dict(shot))
            shot = {'payload_sha256':digest, 'reference_sha256':ref_hash, 'status':'pending',
                    'model':'cogvideox-flash', 'input_mode':'reference_image'}
            state['shots'][sid] = shot
            engine.save(record,state)
        elif shot.get('status') == 'blocked_by_provider_moderation':
            raise engine.ProviderError('/videos/generations',400,'1301')
        target = engine.WORK / 'identity-probe' / (sid+'.mp4')
        try:
            if shot.get('status') == 'provider_failed_requires_review':
                details = shot.get('failure_details',{'code':'unknown'})
                error = engine.VideoTaskFailedError(details)
                if not error.transient:
                    raise error
                state.setdefault('previous_results',{}).setdefault(sid,[]).append(dict(shot))
                shot = {'payload_sha256':digest,'reference_sha256':ref_hash,'status':'pending',
                        'model':'cogvideox-flash','input_mode':'reference_image'}
                state['shots'][sid] = shot
                engine.save(record,state)
            if shot.get('status') == 'downloaded' and target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == shot.get('sha256'):
                continue
            if not shot.get('task_id'):
                data = submit(engine,payload)
                if not data.get('id'):
                    raise RuntimeError('Identity probe returned no task ID')
                shot.update(task_id=data['id'],status='submitted')
                engine.save(record,state)
            def progress(observation):
                shot.update(last_provider_status=observation['provider_status'],last_polled_utc=observation['checked_utc'],poll_count=observation['poll_count'])
                engine.save(record,state)
            url = engine.await_video(shot['task_id'], timeout_seconds=1200,on_status=progress)
            shot['status']='provider_succeeded'
            engine.save(record,state)
            engine.download(url,target)
            duration = engine.seconds(target)
            shot.update(status='downloaded',sha256=hashlib.sha256(target.read_bytes()).hexdigest(),duration=duration)
            for n,fraction in enumerate((.15,.5,.85)):
                engine.run('ffmpeg','-y','-ss',duration*fraction,'-i',target,'-frames:v','1',
                           '-vf','scale=960:-1',folder/f'{sid}-{n}.jpg')
            engine.save(record,state)
        except Exception as exc:
            code = getattr(exc,'code',None)
            if isinstance(exc,engine.VideoPendingError):
                shot['status']='awaiting_provider'
                state['status']='awaiting_provider'
            elif isinstance(exc,engine.VideoTaskFailedError):
                shot.update(status='provider_failed_requires_review',failure_details=exc.details)
                state['status']='provider_transient_failure' if exc.transient else 'provider_terminal_failure'
                if code == '1301':
                    shot.update(status='blocked_by_provider_moderation',no_automatic_resubmit=True)
                    state['status']='blocked_by_provider_moderation'
            elif code == '1301':
                shot.update(status='blocked_by_provider_moderation',no_automatic_resubmit=True)
                state['status']='blocked_by_provider_moderation'
            elif getattr(exc,'transient',False):
                state['status']='capacity_unavailable'
            else:
                state['status']='download_or_validation_failed' if shot.get('status')=='provider_succeeded' else 'incomplete_requires_diagnosis'
            state['error']=str(exc)
            engine.save(record,state)
            raise
    contact_sheet(folder,reference)
    state.update(status='clips_downloaded_identity_review_required',same_actor_verified=False)
    engine.save(record,state)


def contact_sheet(folder, reference):
    from PIL import Image, ImageDraw, ImageOps
    sheet = Image.new('RGB',(1600,650),'#171b22')
    draw = ImageDraw.Draw(sheet)
    for row,(sid,_) in enumerate(PROMPTS):
        for col,path in enumerate([reference]+[folder/f'{sid}-{n}.jpg' for n in range(3)]):
            if not path.exists():
                continue
            with Image.open(path) as image:
                thumb = ImageOps.contain(image.convert('RGB'),(390,280))
            x=col*400;y=row*325
            sheet.paste(thumb,(x,y+25))
            draw.text((x+5,y+5),'Canonical reference' if col==0 else f'{sid} sample {col}',fill='white')
    sheet.save(folder/'identity-comparison.jpg',quality=94)


if __name__ == '__main__':
    import pipeline
    run_probe(pipeline)
