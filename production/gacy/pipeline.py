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
FPS = 24
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


def post(resource, payload):
    key = os.environ.get('ZHIPUAI_API_KEY')
    if not key:
        raise RuntimeError('ZHIPUAI_API_KEY is not injected')
    for attempt in range(8):
        try:
            response = requests.post(API + resource, json=payload,
                headers={'Authorization': 'Bearer ' + key}, timeout=(30, 180))
        except requests.RequestException:
            if attempt == 7:
                raise RuntimeError('Zhipu connection failed after bounded retries') from None
            time.sleep(min(30 * (attempt + 1), 120))
            continue
        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(f'Zhipu returned non-JSON HTTP {response.status_code}') from None
        code = str(data.get('error', {}).get('code', ''))
        if response.status_code == 429 or code in ('1302', '1305') or response.status_code >= 500:
            print(f'Temporary Zhipu error {response.status_code}/{code}, retry {attempt+1}/8', flush=True)
            time.sleep(min(30 * (attempt + 1), 120))
            continue
        if not response.ok or 'error' in data:
            # Do not print request headers, keys, or opaque service responses.
            raise RuntimeError(f'Zhipu rejected {resource}: HTTP {response.status_code}, code={code}')
        return data
    raise RuntimeError('Zhipu retry budget exhausted')


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
}
REF_MAP = {1:'郊区住宅',2:'地下空间',3:'波戈',4:'波戈',5:'盖西',6:'盖西',7:'法官与陪审团',8:'盖西',9:'盖西',10:'少年',11:'郊区住宅',12:'母亲',13:'盖西',14:'雪夜药店',15:'少年',16:'母亲',17:'警探',18:'警探',19:'郊区住宅',20:'盖西',21:'地下空间',22:'地下空间',23:'郊区住宅',24:'地下空间',25:'法官与陪审团',26:'法庭与监狱',27:'法庭与监狱',28:'母亲'}


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


def await_video(task_id):
    key = os.environ['ZHIPUAI_API_KEY']
    deadline = time.monotonic() + 1800
    errors = 0
    while time.monotonic() < deadline:
        try:
            r = requests.get(API + '/async-result/' + task_id,
                             headers={'Authorization':'Bearer ' + key}, timeout=60)
            r.raise_for_status()
            data = r.json()
            errors = 0
        except (requests.RequestException, ValueError):
            errors += 1
            if errors >= 8:
                raise RuntimeError('Video polling failed; persisted task ID can be resumed') from None
            time.sleep(20)
            continue
        status = data.get('task_status')
        print(f'Video task {task_id}: {status}', flush=True)
        if status == 'SUCCESS':
            result = data.get('video_result', [])
            if not result or not result[0].get('url'):
                raise RuntimeError('Successful task has no video URL')
            return result[0]['url']
        if status in ('FAIL', 'FAILED'):
            raise RuntimeError('Video task failed; no substitute footage is allowed')
        time.sleep(15)
    raise RuntimeError('Video polling timed out; task ID retained for resume')


def generate_videos(state):
    receipts = state.setdefault('shots', {})
    for index, shot in enumerate(PLAN['shots'][:-1], 1):
        sid = shot['id']
        target = WORK / 'clips' / (sid + '.mp4')
        reference = HERE / 'references' / (REF_MAP[index] + '.jpg')
        image_url = 'data:image/jpeg;base64,' + base64.b64encode(reference.read_bytes()).decode()
        payload = {'model':'cogvideox-flash','quality':'speed',
                   'prompt':shot['prompt'],'image_url':image_url}
        wanted_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        receipt = receipts.get(sid, {})
        if receipt.get('payload_sha256') != wanted_hash:
            receipt = {'payload_sha256':wanted_hash,'model':'cogvideox-flash',
                       'reference':reference.name,'status':'pending'}
            receipts[sid] = receipt
        if target.exists() and receipt.get('status') == 'downloaded' and receipt.get('sha256') == hashlib.sha256(target.read_bytes()).hexdigest():
            continue
        if not receipt.get('task_id'):
            print('Submitting ' + sid + ' with reference image', flush=True)
            response = post('/videos/generations', payload)
            if not response.get('id'):
                raise RuntimeError('Video submit returned no task ID')
            receipt.update(task_id=response['id'], status='submitted')
            save(STATE, state)
        url = await_video(receipt['task_id'])
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


def render():
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
            vf+=f',fade=t=out:st={wanted-.3}:d=.15:color=black,drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable=gte(t\\,{wanted-.15})'
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
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['references','video','audio','render','all'],default='all');args=parser.parse_args()
    WORK.mkdir(parents=True,exist_ok=True);OUT.mkdir(exist_ok=True)
    state=json.loads(STATE.read_text()) if STATE.exists() else {}
    save(HERE/'run-status.json',{'status':'running','stage':args.stage,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
    try:
        if args.stage in ('references','all'): references(state)
        if args.stage in ('video','all'): generate_videos(state)
        if args.stage in ('audio','all'): make_audio()
        if args.stage in ('render','all'): render()
    except Exception as exc:
        save(HERE/'run-status.json',{'status':'failed','stage':args.stage,'error':str(exc),'no_static_fallback':True})
        raise
    save(HERE/'run-status.json',{'status':'stage_completed' if args.stage!='all' else 'draft_ready_requires_review','stage':args.stage})

if __name__=='__main__':
    main()
