#!/usr/bin/env python3
"""Gacy production runner. Free Zhipu models only; no static-image video fallback.
Run on a network-enabled runner with ZHIPUAI_API_KEY and ffmpeg installed.
Outputs a REVIEW DRAFT, never an automatically approved publishable film.
"""
from __future__ import annotations
import argparse
import asyncio
import base64
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / 'work/gacy'
OUT = WORK / 'delivery'
STATE = HERE / 'receipts.json'
API = 'https://open.bigmodel.cn/api/paas/v4'
PLAN = json.loads((HERE / 'story.json').read_text())
VISUAL_PLAN = json.loads((HERE / 'visual-plan.json').read_text())
SDK_VIDEO_GENERATION = True
FPS = 30
SR = 48000


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def run(*args):
    subprocess.run([str(x) for x in args], check=True, stdout=subprocess.DEVNULL)


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)]))


def seconds(path):
    return float(probe(path)['format']['duration'])


DIAGNOSTICS = HERE / 'api-diagnostics.json'


class ProviderError(RuntimeError):
    def __init__(self, resource, status, code, exhausted=False):
        self.resource, self.status, self.code = resource, status, code
        self.transient = status == 429 or status >= 500 or code in ('1302', '1305')
        prefix = 'Zhipu retry budget exhausted' if exhausted else 'Zhipu rejected request'
        super().__init__(f'{prefix}: {resource}, HTTP {status}, code={code or "unknown"}')


class VideoPendingError(RuntimeError):
    def __init__(self, task_id, last_status, timeout_seconds):
        self.task_id, self.last_status = task_id, last_status
        super().__init__(f'Video still awaiting provider after {timeout_seconds}s: {last_status}; existing task ID retained for resume')


class VideoTaskFailedError(ProviderError):
    def __init__(self, details):
        super().__init__('/async-result', 200, details.get('code','unknown'))
        self.details = details
        # Repository evidence: 1234 is a terminal provider execution/network failure.
        # Only a definitively failed task may be replaced, never a pending task.
        self.transient = self.code == '1234'


def task_failure_details(data):
    error = data.get('error') or data.get('error_info') or {}
    if isinstance(error, str):
        try: error = json.loads(error)
        except ValueError: error = {'message':error}
    if not isinstance(error, dict): error = {}
    code = re.sub(r'[^A-Za-z0-9_-]','',str(error.get('code') or data.get('error_code') or data.get('code') or 'unknown'))[:32]
    message = str(error.get('message') or error.get('msg') or data.get('message') or data.get('fail_reason') or '')
    key = os.environ.get('ZHIPUAI_API_KEY','')
    if key: message = message.replace(key,'[REDACTED]')
    message = re.sub(r'https?://\S+|[A-Za-z0-9+/=]{100,}', '[REDACTED]',message)[:400]
    return {'code':code,'message':message,'response_fields':sorted(data.keys())}


def record_api_attempt(resource, payload, status, code, attempt):
    entries = json.loads(DIAGNOSTICS.read_text()) if DIAGNOSTICS.exists() else []
    entries.append({'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'resource': resource, 'model': payload.get('model'), 'http_status': status,
        'error_code': code, 'attempt': attempt,
        'video_input': 'reference_image' if 'image_url' in payload else 'text',
        'contains_no_headers_keys_or_image_data': True})
    save(DIAGNOSTICS, entries[-100:])


def video_payload(shot):
    return {'model':'cogvideox-flash', 'prompt':VISUAL_PLAN['shots'][shot['id']]['prompt'],
            'quality':'speed'}


def send_generation(resource, payload, key):
    if resource != '/videos/generations' or not SDK_VIDEO_GENERATION:
        return requests.post(API + resource, json=payload,
            headers={'Authorization':'Bearer ' + key}, timeout=(30,180))
    # Exactly the free-model SDK call used by the Mary Celeste production engine.
    client = make_video_client()
    response = requests.Response()
    try:
        result = client.videos.generations(model=payload['model'], prompt=payload['prompt'], quality=payload['quality'])
        data = result if isinstance(result,dict) else result.model_dump()
        response.status_code = 200
    except Exception as exc:
        original = getattr(exc,'response',None)
        if original is None:
            raise requests.RequestException('SDK submission outcome unknown') from None
        response.status_code = original.status_code
        try:
            data = original.json()
        except (ValueError,TypeError):
            data = {'error':{'code':'sdk_non_json'}}
    response._content = json.dumps(data).encode()
    return response


def post(resource, payload, attempts=8):
    key = os.environ.get('ZHIPUAI_API_KEY')
    if not key:
        raise RuntimeError('ZHIPUAI_API_KEY is not injected')
    for attempt in range(attempts):
        try:
            response = send_generation(resource, payload, key)
        except requests.RequestException:
            # A timed-out POST may have been accepted: do not blindly create duplicates.
            record_api_attempt(resource, payload, 0, 'transport_outcome_unknown', attempt+1)
            raise RuntimeError('Zhipu POST transport failed; acceptance unknown, no blind resubmit') from None
        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(f'Zhipu returned non-JSON HTTP {response.status_code}') from None
        code = re.sub(r'[^a-zA-Z0-9_-]', '', str(data.get('error', {}).get('code', '')))[:32]
        record_api_attempt(resource, payload, response.status_code, code, attempt+1)
        if response.status_code == 429 or code in ('1302', '1305') or response.status_code >= 500:
            print(f'Temporary Zhipu error {response.status_code}/{code}, retry {attempt+1}/{attempts}', flush=True)
            if attempt + 1 == attempts:
                raise ProviderError(resource, response.status_code, code, exhausted=True)
            time.sleep(min(30 * (attempt + 1), 120))
            continue
        if not response.ok or 'error' in data:
            raise ProviderError(resource, response.status_code, code)
        return data
    raise RuntimeError('Invalid retry configuration')


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=(30, 240))
            r.raise_for_status()
            if not r.content:
                raise RuntimeError('Empty download')
            tmp = path.with_suffix(path.suffix + '.part')
            tmp.write_bytes(r.content)
            tmp.replace(path)
            return
        except requests.RequestException:
            if attempt == 3:
                raise RuntimeError('Media download failed') from None
            time.sleep(10 * (attempt + 1))


REFERENCE_SCENES = {
    '郊区住宅': '整齐白色小房子、草坪、秋冬树木、暖黄路灯，单一宽景，无人物。',
    '医院与派对': '1970年代儿童医院病房，暖光窗帘、床头气球，无人物。',
    '法庭与监狱': '1970年代冷灰法庭，木质座位与金属门，无人物。',
    '雪夜药店': '1970年代雪夜药店外景，无可读文字霓虹、暖光橱窗、雪花，无人物。',
    '地下空间': '漆黑狭窄地下空间，手电体积光与飘浮尘埃，无具体物体、无人体。',
    '封面底图': '单张完整电影封面画面，左三分线是一位穿彩色小丑服、白色脸部彩绘、圆形红鼻子的风格化中年男性，只见半张脸，半边脸在阴影；右三分线是木地板上一扇微开的活板门，只有光线与黑暗，不出现任何人体或具体物体。中央下方留排版空间，禁止文字。',
}
REF_MAP = {1:'郊区住宅',2:'地下空间',3:'波戈',4:'波戈',5:'盖西',6:'盖西',7:'法官与陪审团',8:'盖西',9:'盖西',10:'少年',11:'郊区住宅',12:'母亲',13:'盖西',14:'雪夜药店',15:'少年',16:'母亲',17:'警探',18:'警探',19:'郊区住宅',20:'盖西',21:'地下空间',22:'地下空间',23:'郊区住宅',24:'地下空间',25:'法官与陪审团',26:'法庭与监狱',27:'法庭与监狱',28:'母亲'}


def dark_reference(path):
    """Render a real 3D dust/light reference, with no invented room or furniture."""
    width, height = 1344, 756
    y, x = np.mgrid[0:height, 0:width]
    center = 280 + .22*x
    beam = np.exp(-((y-center)/(25+.12*x))**2)*np.clip(1-x/width,0,1)**1.4
    image = np.zeros((height,width,3),dtype=np.uint8)
    for channel, strength in enumerate((24,30,40)):
        image[:,:,channel] = (beam*strength).astype(np.uint8)
    im=Image.fromarray(image)
    draw=ImageDraw.Draw(im)
    rng=np.random.default_rng(19781221)
    # Project 3D dust particles, lit by an angular cone in world space.
    for _ in range(450):
        px,py,pz=rng.uniform(-3,3),rng.uniform(-2,2),rng.uniform(2,12)
        sx=width/2+700*px/pz;sy=height/2+700*py/pz
        ix,iy=int(sx),int(sy)
        if 0<=ix<width and 0<=iy<height and beam[iy,ix]>.15:
            value=int(40+130*beam[iy,ix]);r=.4+1.2/pz
            draw.ellipse((sx-r,sy-r,sx+r,sy+r),fill=(value,value,int(value*.9)))
    path.parent.mkdir(exist_ok=True)
    im.save(path, quality=94)


def references(state):
    refs = state.setdefault('references', {})
    folder = HERE / 'references'
    folder.mkdir(exist_ok=True)
    for name, description in {**PLAN['characters'], **REFERENCE_SCENES}.items():
        path = folder / (name + '.jpg')
        corrections = {
            '母亲': '唯一主体是一位40岁左右的女性母亲，明确女性面容，棕色卷发，深色女式外套，神情焦急而坚强。禁止男性、胡须、男性面容。',
            '少年': '画面中必须有且只有一位穿1970年代夹克、牛仔裤、运动鞋、背着书包的少年，完整背对镜头，绝不展示正脸；人物占画面高度一半，站在右三分线上。禁止空景。',
            '法官与陪审团': '唯一前景主体是穿黑色法袍坐在高处审判席的严肃法官，旁边陪审团穿1970年代正式服饰；法官不能是穿普通西装的站立男子。',
            '盖西': '唯一主体是体型明显偏胖、圆脸、浅棕色短发的中年白人男性，穿深色西装，亲切微笑，半边脸在阴影；不是瘦长脸，不留胡须。',
            '地下空间': '几乎全黑的抽象地下空间，唯一可见的是一束手电光和缓慢漂浮尘埃。绝不显示房间陈设、桌椅、窗户、门、家具或任何人体。',
        }
        prompt = (PLAN['style'] + '角色与场景参考图，单一完整画面，非拼贴，不要黑边。'
                  + '【参考对象：' + name + '】' + corrections.get(name, description)
                  + '所有人物为风格化3D虚构形象，非真实肖像。画面中不出现文字。'
                  + '【NEGATIVE】' + PLAN['negative'])
        digest = hashlib.sha256(prompt.encode()).hexdigest()
        if name == '地下空间':
            dark_reference(path)
            refs[name] = {'model':'procedural_3d_dust_reference_v1','prompt_sha256':digest,
                          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'status':'rendered_requires_visual_review','seed':19781221}
            save(STATE,state)
            continue
        if path.exists() and refs.get(name, {}).get('prompt_sha256') == digest:
            continue
        print('Generating free reference: ' + name, flush=True)
        data = post('/images/generations', {'model':'cogview-3-flash', 'prompt':prompt, 'size':'1344x768', 'watermark_enabled':False})
        item = data.get('data', [{}])[0]
        if item.get('url'):
            download(item['url'], path)
        elif item.get('b64_json'):
            path.write_bytes(base64.b64decode(item['b64_json']))
        else:
            raise RuntimeError('Reference generation returned no image')
        with Image.open(path) as im:
            im.convert('RGB').save(path, quality=90)
        refs[name] = {'model':'cogview-3-flash','prompt_sha256':digest,
                      'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                      'status':'generated_requires_visual_review'}
        save(STATE, state)
    # This is a generated design baseline, not a claim of human approval.
    state['reference_status'] = 'generated_baseline_not_human_approved'
    save(STATE, state)


def make_video_client():
    from zhipuai import ZhipuAI
    return ZhipuAI(api_key=os.environ['ZHIPUAI_API_KEY'], max_retries=0, timeout=60)


def await_video(task_id, timeout_seconds=1200, on_status=None):
    # Use the same SDK retrieval protocol as the user's successful connectivity test.
    client = make_video_client()
    deadline = time.monotonic() + timeout_seconds
    errors = 0
    attempts = 0
    last_status = 'UNQUERIED'
    while time.monotonic() < deadline:
        attempts += 1
        try:
            result = client.videos.retrieve_videos_result(id=task_id)
            data = result if isinstance(result, dict) else result.model_dump()
            errors = 0
        except Exception as exc:
            errors += 1
            status = getattr(exc, 'status_code', 0) or 0
            body = getattr(exc, 'body', {})
            response = getattr(exc, 'response', None)
            if response is not None:
                try:
                    body = response.json()
                except (ValueError, TypeError):
                    pass
            error = body.get('error', body) if isinstance(body, dict) else {}
            code = re.sub(r'[^a-zA-Z0-9_-]', '', str(error.get('code', 'sdk_query_error')))[:32]
            record_api_attempt('/async-result', {'model':'cogvideox-flash'}, status, code, attempts)
            message = str(error.get('message', ''))
            key = os.environ.get('ZHIPUAI_API_KEY', '')
            if key:
                message = message.replace(key, '[REDACTED]')
            message = re.sub(r'https?://\S+|[A-Za-z0-9+/=]{100,}', '[REDACTED]', message)[:300]
            if message:
                entries = json.loads(DIAGNOSTICS.read_text())
                entries[-1]['provider_message'] = message
                save(DIAGNOSTICS, entries)
            if code == '1301':
                raise ProviderError('/async-result', status, code) from None
            if status in (400,401,403,404) or errors >= 12:
                raise RuntimeError(f'Video polling failed: HTTP {status}, code={code}; existing task ID retained, no resubmission') from None
            print(f'Temporary video lookup error HTTP {status}, code={code}; retrying existing task only', flush=True)
            time.sleep(min(20 * errors, 60))
            continue
        status = str(data.get('task_status') or 'UNKNOWN').upper()
        last_status = status
        if on_status is not None:
            on_status({'provider_status':status,'poll_count':attempts,'checked_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
        print(f'Video task {task_id}: {status}', flush=True)
        if status == 'SUCCESS':
            result = data.get('video_result', [])
            if not result or not result[0].get('url'):
                raise RuntimeError('Successful task has no video URL')
            return result[0]['url']
        if status in ('FAIL', 'FAILED'):
            raise VideoTaskFailedError(task_failure_details(data))
        if status not in ('PROCESSING','PENDING','QUEUED','SUBMITTED'):
            raise RuntimeError('Unexpected video task status: '+status+'; inspect schema, not a normal queue timeout')
        time.sleep(15)
    raise VideoPendingError(task_id,last_status,timeout_seconds)


def shot_keyframe(shot, state):
    """Scene-specific first frame. Free CogView has no verified multi-reference identity lock."""
    folder = HERE / 'keyframes'
    folder.mkdir(exist_ok=True)
    path = folder / (shot['id'] + '.jpg')
    prompt = (PLAN['style'] + '生成此镜头的电影动画首帧，不是角色站立定妆照。'
              + shot['prompt'][len(PLAN['style']):])
    digest = hashlib.sha256(prompt.encode()).hexdigest()
    entries = state.setdefault('keyframes', {})
    entry = entries.get(shot['id'], {})
    if path.exists() and entry.get('prompt_sha256') == digest:
        return path
    if shot['id'] in ('S21','S22'):
        dark_reference(path)
        model = 'procedural_3d_dust_reference_v1'
    else:
        data=post('/images/generations',{'model':'cogview-3-flash','prompt':prompt,
                  'size':'1344x768','watermark_enabled':False})
        item=data.get('data',[{}])[0]
        if item.get('url'):
            download(item['url'],path)
        elif item.get('b64_json'):
            path.write_bytes(base64.b64decode(item['b64_json']))
        else:
            raise RuntimeError('Shot keyframe generation returned no image')
        with Image.open(path) as im:
            im.convert('RGB').save(path,quality=90)
        model='cogview-3-flash'
    entries[shot['id']]={'model':model,'prompt_sha256':digest,
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'status':'generated_requires_scene_and_character_review',
        'identity_conditioning':'text descriptions only; multi-reference identity lock not verified'}
    save(STATE,state)
    return path


def submit_video(payload, state):
    """Prefer reference animation; on explicit capacity rejection try the proven text-video route.
    No fallback on auth, balance, moderation, invalid fields, or unknown POST outcomes.
    """
    try:
        return post('/videos/generations', payload, attempts=2 if 'image_url' in payload else 8), payload
    except ProviderError as exc:
        if 'image_url' not in payload or not exc.transient:
            raise
        text_payload = {k:v for k,v in payload.items() if k != 'image_url'}
        state['video_policy'] = {'effective_input':'text',
            'reason':'reference input repeatedly rejected for capacity; using same full scene/character prompt',
            'reference_failure':{'http_status':exc.status,'code':exc.code},
            'identity_lock':False,'static_image_animation_fallback':False}
        save(STATE,state)
        print('Reference-video capacity rejection: trying free text-to-video with unchanged scene/character prompt; identity conditioning is not retained.',flush=True)
        return post('/videos/generations',text_payload),text_payload


def generate_one_video(shot, state):
    receipts = state.setdefault('shots', {})
    sid = shot['id']
    target = WORK / 'clips' / (sid + '.mp4')
    # Same proven three-field free text-video contract as Mary Celeste.
    payload = video_payload(shot)
    wanted_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    receipt = receipts.get(sid, {})
    if receipt.get('payload_sha256') != wanted_hash:
        if receipt:
            state.setdefault('previous_results', {}).setdefault(sid, []).append(dict(receipt))
        receipt = {'payload_sha256':wanted_hash,'model':'cogvideox-flash',
                   'visual_revision':VISUAL_PLAN['revision'],'status':'pending',
                   'reference_conditioning':False}
        receipts[sid] = receipt
        save(STATE,state)
    elif receipt.get('status') == 'blocked_by_provider_moderation':
        raise ProviderError('/async-result', 400, '1301')
    if receipt.get('status') == 'provider_failed_requires_review':
        error = VideoTaskFailedError(receipt.get('failure_details',{'code':'unknown'}))
        if not error.transient: raise error
        state.setdefault('previous_results',{}).setdefault(sid,[]).append(dict(receipt))
        receipt={'payload_sha256':wanted_hash,'model':'cogvideox-flash','status':'pending',
                 'visual_revision':VISUAL_PLAN['revision'],'reference_conditioning':False}
        receipts[sid]=receipt
        save(STATE,state)
    if target.exists() and receipt.get('status') == 'downloaded' and receipt.get('sha256') == hashlib.sha256(target.read_bytes()).hexdigest():
        return
    if not receipt.get('task_id'):
        receipt['input_mode'] = 'reference_image' if 'image_url' in payload else 'text'
        save(STATE,state)
        print('Submitting ' + sid + ' input=' + receipt['input_mode'], flush=True)
        try:
            response = post('/videos/generations', payload)
        except ProviderError as exc:
            if exc.code == '1301':
                receipt.update(status='blocked_by_provider_moderation',error_code='1301',
                    requires_review=True,no_automatic_resubmit=True)
                save(STATE,state)
            raise
        actual_payload = payload
        if not response.get('id'):
            raise RuntimeError('Video submit returned no task ID')
        receipt.update(task_id=response['id'], status='submitted',
            input_mode='reference_image' if 'image_url' in actual_payload else 'text',
            payload_sha256=hashlib.sha256(json.dumps(actual_payload,sort_keys=True).encode()).hexdigest())
        save(STATE, state)
    def progress(observation):
        receipt.update(last_provider_status=observation['provider_status'],last_polled_utc=observation['checked_utc'],poll_count=observation['poll_count'])
        save(STATE,state)
    try:
        url = await_video(receipt['task_id'],on_status=progress)
    except ProviderError as exc:
        if isinstance(exc,VideoTaskFailedError):
            receipt.update(status='provider_failed_requires_review',failure_details=exc.details)
            save(STATE,state)
        if exc.code == '1301':
            receipt.update(status='blocked_by_provider_moderation',error_code='1301',
                requires_review=True,no_automatic_resubmit=True)
            save(STATE,state)
        raise
    download(url, target)
    info = probe(target)
    if not any(s.get('codec_type') == 'video' for s in info['streams']):
        raise RuntimeError(sid + ': invalid downloaded video')
    receipt.update(status='downloaded',duration=seconds(target),
                   sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    save(STATE, state)
    qa = HERE / 'qa'
    qa.mkdir(exist_ok=True)
    for n, fraction in enumerate((0.15, 0.5, 0.85)):
        run('ffmpeg','-y','-ss',receipt['duration']*fraction,'-i',target,
            '-frames:v','1','-vf','scale=480:-1',qa/f'{sid}-{n}.jpg')


def generate_videos(state, limit=None):
    selected = PLAN['shots'][:-1] if limit is None else PLAN['shots'][:limit]
    blocked=[]
    for shot in selected:
        try:
            generate_one_video(shot,state)
        except ProviderError as exc:
            if exc.code != '1301' or limit == 1:
                raise
            blocked.append(shot['id'])
            print(shot['id'] + ': moderation rejected this revision; recording and moving to a different storyboard scene, not resubmitting this scene',flush=True)
    if blocked:
        raise RuntimeError('Visual review/redesign required for blocked scenes: '+','.join(blocked)+'; incomplete footage will not be rendered as a finished film')


def wav_write(path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((np.clip(samples, -.97, .97)*32767).astype('<i2').tobytes())


def ass_time(t):
    cs = round(t * 100)
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'


def clean_ass(text):
    return text.replace('\\', '').replace('{','').replace('}','').replace('\n',' ')


async def synthesize(text, path):
    import edge_tts
    if path.exists() and path.stat().st_size > 100:
        return
    for attempt in range(4):
        try:
            await edge_tts.Communicate(text, 'zh-CN-YunxiNeural', rate='-5%', pitch='-5Hz').save(str(path))
            return
        except Exception:
            path.unlink(missing_ok=True)
            if attempt == 3:
                raise RuntimeError('Chinese TTS unavailable; no silent voiceover fallback') from None
            await asyncio.sleep(10 * (attempt+1))


def make_audio():
    full = np.zeros(180 * SR, dtype=np.float32)
    cues = []
    voice_dir = WORK / 'voice'
    voice_dir.mkdir(exist_ok=True)
    report = []
    for ni, paragraph in enumerate(PLAN['narration']):
        # Split at punctuation AND after words requiring an explicit 500ms pause.
        parts = [p for p in re.split(r'(?<=[。！？：])|(?<=地板下)|(?<=马上回来)', paragraph['text']) if p]
        segments = []
        for j, text in enumerate(parts):
            token = hashlib.sha256(text.encode()).hexdigest()[:10]
            mp3 = voice_dir / f'{ni:02}-{j:02}-{token}.mp3'
            asyncio.run(synthesize(text, mp3))
            pcm = mp3.with_suffix('.wav')
            run('ffmpeg','-y','-i',mp3,'-ac','1','-ar',SR,pcm)
            with wave.open(str(pcm)) as f:
                samples = np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
            pause = .5 if text.endswith(('地板下','马上回来')) else .10
            segments.append((text, samples, pause))
        available = paragraph['end'] - paragraph['start']
        pauses = sum(p for _, _, p in segments)
        spoken = sum(len(s)/SR for _, s, _ in segments)
        speed = max(1., spoken / (available - pauses - .05))
        if speed > 1.35:
            raise RuntimeError(f'N{ni+1}: TTS needs {speed:.2f}x speed; refusing excessive acceleration or deleted words')
        cursor = paragraph['start']
        for j, (text, samples, pause) in enumerate(segments):
            if speed > 1.001:
                raw = voice_dir / f'{ni}-{j}-raw.wav'
                fitted = voice_dir / f'{ni}-{j}-fitted.wav'
                wav_write(raw, samples)
                run('ffmpeg','-y','-i',raw,'-af',f'atempo={speed:.6f}',fitted)
                with wave.open(str(fitted)) as f:
                    samples = np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
            start = round(cursor * SR)
            stop = start + len(samples)
            if stop > round(paragraph['end'] * SR):
                raise RuntimeError('TTS exceeds original paragraph timeline')
            full[start:stop] += samples
            duration = len(samples)/SR
            # Subdivide long lines while retaining exact synthesized sentence intervals.
            pieces = [text[k:k+24] for k in range(0,len(text),24)]
            used = 0
            for piece in pieces:
                a = cursor + duration * used / len(text)
                used += len(piece)
                b = cursor + duration * used / len(text)
                cues.append({'start':a,'end':b,'text':piece,'sync':'measured sentence audio; within-sentence split estimated'})
            cursor += duration + pause
        report.append({'paragraph':ni+1,'speed':speed,'end':cursor,'slot_end':paragraph['end']})
    rms = math.sqrt(float(np.mean(full**2)))
    if rms == 0:
        raise RuntimeError('Empty narration')
    full *= .15/rms
    wav_write(OUT/'narration.wav', full)
    save(OUT/'narration-timing.json', {'paragraphs':report,'cues':cues,'voice':'zh-CN-YunxiNeural','requires_listening_review':True})
    write_subtitles(cues)
    score(full)


def write_subtitles(cues):
    header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,50,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,100,100,80,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = []
    headlines = [
        (0, 5, '笑得最开心的小丑'), (10, 15, '1970年代 · 美国芝加哥郊区'),
        (35, 40, '1968年入狱 · 只服刑一年多'), (55, 60, '1972年起 · 少年陆续失踪'),
        (80, 85, '1978年12月11日 · 一句“马上回来”'), (105, 110, '12月13日 · 搜查令'),
        (130, 136, '33名受害者 · 大多是十几岁到二十出头'),
        (150, 156, '1980年审判 · 1994年5月10日执行'), (170, 176, '请记住他们，而不是他'),
    ]
    for start, end, text in headlines:
        lines.append(f'Dialogue: 1,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{{\\an8\\pos(960,80)\\fs44\\c&H0057C7F2&}}{text}')
    keywords = ('三十三','地板下','马上回来','二十九','请记住他们','而不是他','罗伯特·皮耶斯特','1968年','1978年','1994年')
    for cue in cues:
        text = clean_ass(cue['text'])
        for key in keywords:
            text = text.replace(key, '{\\c&H0057C7F2&\\fs60}' + key + '{\\r}')
        lines.append(f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},Default,,0,0,0,,{text}")
    (OUT/'captions.ass').write_text(header + '\n'.join(lines) + '\n')


def score(voice):
    """Original procedural underscore and effects; review required, not licensed recordings."""
    music = np.zeros(180*SR,dtype=np.float32)
    # Section-specific harmonic pulses: warm accordion-like reed harmonics → dark strings/piano.
    for section, paragraph in enumerate(PLAN['narration']):
        a,b = paragraph['start'],paragraph['end']
        t = np.arange(round((b-a)*SR),dtype=np.float32)/SR
        base = 130.81 if section in (0,1) else (65.41 if section<6 else 55.)
        if section == 1:
            tone = np.zeros_like(t)
            notes = (261.63,329.63,392.,329.63,293.66,349.23,392.,261.63)
            for k in range(math.ceil((b-a)/.65)):
                s=round(k*.65*SR); e=min(len(t),round((k+1)*.65*SR)); tt=np.arange(e-s)/SR
                freq=notes[k%len(notes)]
                tone[s:e] = sum(np.sin(2*np.pi*freq*h*tt)/h for h in (1,2,3,4))*np.sin(np.pi*np.arange(e-s)/(e-s))**.4
        else:
            tone = sum(np.sin(2*np.pi*base*h*t)/h**1.8 for h in (1,2,3,4))
            tone *= .5 + .15*np.sin(2*np.pi*.2*t)
            if section in (2,3,4,6):
                local = t % 2.5
                tone += np.sin(2*np.pi*220*t)*np.exp(-3*local)*.4
        if section == 0:
            tone += .15*np.sin(2*np.pi*(260*t-.7*t*t))
        fade = np.minimum(1,t/.3)*np.minimum(1,(b-a-t)/.3)
        music[round(a*SR):round(b*SR)] = tone*fade
    # Measured global RMS bed is 18 dB below measured narration; additional ducking when voice speaks.
    mrms = math.sqrt(float(np.mean(music**2)))
    vrms = math.sqrt(float(np.mean(voice**2)))
    music *= vrms*10**(-18/20)/mrms
    effects = np.zeros_like(music)
    rng = np.random.default_rng(1978)
    def effect(at, duration, kind):
        n=round(duration*SR); t=np.arange(n)/SR
        if kind=='bell':
            x=(np.sin(2*np.pi*880*t)+.4*np.sin(2*np.pi*1320*t))*np.exp(-5*t)
        elif kind=='gavel':
            x=rng.normal(0,1,n)*np.exp(-45*t)+.3*np.sin(2*np.pi*100*t)*np.exp(-20*t)
        else:
            noise=rng.normal(0,1,n)
            x=np.convolve(noise,np.ones(180)/180,mode='same')*np.sin(np.pi*t/duration)
        s=round(at*SR); effects[s:s+n]+=x.astype(np.float32)*.035
    effect(92.2,.8,'bell'); effect(40,.6,'gavel'); effect(159,.6,'gavel')
    effect(80,7,'wind'); effect(94,8,'wind')
    for at in np.arange(57,80,1.25):
        n=round(.25*SR);t=np.arange(n)/SR;s=round(at*SR)
        effects[s:s+n]+=(.025*np.sin(2*np.pi*48*t)*np.exp(-16*t)).astype(np.float32)
    mixed = voice+music+effects
    mixed[-SR:]=0
    mixed *= min(1.,.94/max(.0001,float(np.max(np.abs(mixed)))))
    wav_write(OUT/'mix.wav',mixed)
    wav_write(OUT/'music.wav',music)
    save(OUT/'mix-report.json',{'music_relative_rms_db':20*math.log10(math.sqrt(float(np.mean(music**2)))/vrms),'last_second_silent':bool(np.all(mixed[-SR:]==0)),'music':'original procedural underscore, requires music-direction review','peak':float(np.max(np.abs(mixed)))})


def font(size):
    return ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',size)


def make_ending():
    # True procedural particle animation; typography is composited, never hallucinated by model.
    enddir = WORK/'ending';enddir.mkdir(exist_ok=True)
    rng=np.random.default_rng(33)
    points = [(int(rng.uniform(110,1810)), int(rng.uniform(90,700))) for _ in range(33)]
    for frame in range(4*FPS):
        t=frame/FPS
        im=Image.new('RGB',(1920,1080));d=ImageDraw.Draw(im)
        for i,(x,y) in enumerate(points):
            alpha=max(0,min(1,(t-i*.055)*3))*min(1,(4-t)*2)
            if alpha>0:
                r=2+math.sin(t*2+i)*.7
                color=tuple(int(c*alpha) for c in (247,213,137))
                d.ellipse((x-r,y-r,x+r,y+r),fill=color)
        opacity=max(0,min(1,(t-.8)*1.2))*min(1,(4-t)*2)
        d.text((960,760),'三十三个年轻的生命',font=font(72),fill=tuple(int(c*opacity) for c in (242,199,87)),anchor='mm')
        d.text((960,866),'小丑杀手 · 约翰·韦恩·盖西',font=font(34),fill=(int(200*opacity),)*3,anchor='mm')
        im.save(enddir/f'{frame:04}.png')
    target=WORK/'clips/S29.mp4'
    run('ffmpeg','-y','-framerate',FPS,'-i',enddir/'%04d.png','-c:v','libx264','-pix_fmt','yuv420p','-crf','21',target)


def make_cover():
    from PIL import ImageOps
    source = HERE / 'references/封面底图.jpg'
    if not source.exists():
        raise RuntimeError('Cover reference missing; run references stage before render')
    with Image.open(source) as im:
        cover = ImageOps.fit(im.convert('RGB'), (1920, 1080))
    draw = ImageDraw.Draw(cover)
    draw.text((960, 850), '小丑的秘密', font=font(132), fill=(242,199,87),
              stroke_width=9, stroke_fill=(0,0,0), anchor='mm')
    cover.save(OUT/'封面_小丑的秘密.jpg', quality=94)


def render():
    from identity_gate import write_report
    identity_report = write_report(HERE)
    if not identity_report['publishable']:
        raise RuntimeError('Cross-shot identity has not passed the evidence-bound review gate; no finished film will be rendered')
    make_cover()
    make_ending()
    normalized=WORK/'normalized';normalized.mkdir(exist_ok=True)
    boundaries={10,35,55,80,105,130,150,170}
    for shot in PLAN['shots']:
        src=WORK/'clips'/(shot['id']+'.mp4')
        original=seconds(src);wanted=shot['duration']
        if original < 3:
            raise RuntimeError('Source clip too short; no freeze or looping fallback')
        # Constant speed fitting preserves continuous generated movement without looping/freeze.
        vf=f'setpts={wanted/original:.8f}*(PTS-STARTPTS),scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps={FPS}'
        if shot['end'] in boundaries:
            vf+=f',fade=t=out:st={wanted-.45}:d=.15:color=black,drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable=gte(t\\,{wanted-.3})'
        run('ffmpeg','-y','-i',src,'-an','-vf',vf,'-t',wanted,'-c:v','libx264','-preset','fast','-crf','24',normalized/(shot['id']+'.mp4'))
    concat=WORK/'concat.txt'
    concat.write_text(''.join(f"file '{(normalized/(s['id']+'.mp4')).as_posix()}'\n" for s in PLAN['shots']))
    joined=WORK/'joined.mp4'
    run('ffmpeg','-y','-f','concat','-safe','0','-i',concat,'-c','copy',joined)
    target=OUT/'小丑背后的真相_180秒_待审片.mp4'
    run('ffmpeg','-y','-i',joined,'-i',OUT/'mix.wav','-vf',f"ass={OUT/'captions.ass'}",'-map','0:v:0','-map','1:a:0','-t','180','-c:v','libx264','-preset','fast','-b:v','2200k','-maxrate','2800k','-bufsize','5600k','-c:a','aac','-b:a','160k','-movflags','+faststart',target)
    info=probe(target)
    video=next(s for s in info['streams'] if s.get('codec_type')=='video')
    assert (video['width'],video['height'])==(1920,1080)
    assert abs(float(info['format']['duration'])-180)<.1
    save(OUT/'technical-report.json',{'duration':float(info['format']['duration']),'width':1920,'height':1080,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'status':'technical_pass_manual_audiovisual_review_required','limitations':['within-sentence subtitle splits are estimated','reference designs generated without human signoff','motion, safety, character consistency and factual accuracy need manual review','procedural music is not yet music-direction approved']})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['references','video','audio','render','probe','identity','recover','all'],default='all');args=parser.parse_args()
    WORK.mkdir(parents=True,exist_ok=True);OUT.mkdir(exist_ok=True)
    state=json.loads(STATE.read_text()) if STATE.exists() else {}
    state['video_policy']={'effective_input':'text','reason':'Mary Celeste proven three-field SDK route; user-authorized non-graphic visual redesign','identity_lock':False,'visual_revision':VISUAL_PLAN['revision']}
    save(HERE/'run-status.json',{'status':'running','stage':args.stage,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    try:
        if args.stage in ('references','all'): references(state)
        if args.stage == 'recover':
            from recover_tasks import recover
            recover(sys.modules[__name__])
        if args.stage == 'identity':
            from identity_retry import run_with_cooldown
            run_with_cooldown(sys.modules[__name__])
        if args.stage == 'probe': generate_videos(state, limit=1)
        if args.stage in ('video','all'): generate_videos(state)
        if args.stage in ('audio','all'): make_audio()
        if args.stage in ('render','all'): render()
    except Exception as exc:
        pending = isinstance(exc,VideoPendingError)
        transient = isinstance(exc,ProviderError) and exc.transient
        blocked = isinstance(exc,ProviderError) and exc.code=='1301'
        phase = ('awaiting_provider' if pending else
                 'provider_transient' if transient else
                 'blocked_by_provider_moderation' if blocked else 'failed')
        report={'status':phase,'stage':args.stage,'error':str(exc),'no_static_fallback':True,
                'automatic_retry_allowed':pending or transient}
        if pending: report.update(task_id=exc.task_id,last_provider_status=exc.last_status,new_submission_allowed=False)
        save(HERE/'run-status.json',report)
        if pending or transient: return 42
        raise
    status = ('recovery_checked' if args.stage=='recover' else
              'identity_review_required' if args.stage=='identity' else
              'draft_ready_requires_review' if args.stage=='all' else 'stage_completed')
    save(HERE/'run-status.json',{'status':status,'stage':args.stage,'automatic_retry_allowed':False})
    return 0


if __name__=='__main__':
    sys.exit(main())
