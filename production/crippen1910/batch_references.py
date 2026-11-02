#!/usr/bin/env python3
"""Generate all remaining individual views in one cloud queue using existing character images.

No token is logged or stored. Synchronous image calls are not retried after an ambiguous
network timeout. A successful download is only a candidate, never a visual sign-off.
"""
from __future__ import annotations
import argparse
import base64
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageOps

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BRANCH='arena/f38dd103-desktop-tutorial'
MODEL='agnes-image-2.5-flash'
ENDPOINT='https://apihub.agnes-ai.com/v1/images/generations'
RESULTS=HERE/'reference/batch-results.json'
LOCK=threading.RLock()
GATE=threading.Lock()
LAST_START=0.0


def digest(data):
    return hashlib.sha256(data).hexdigest()


def plan(story):
    roles=[key for key in story['characters'] if key not in {'C07','C09'}]
    rows=[]
    instructions={
        'side':'STRICT ORTHOGRAPHIC LEFT PROFILE, exactly 90 degrees away from frontal view. Nose points to LEFT image edge. ONLY ONE EYE can be visible. One shoulder occludes the other. Head, torso, knees and both shoes all point LEFT. NOT frontal, NOT three-quarter. This is a technical character turnaround side elevation. Entire body with shoes and hair/required headwear inside frame.',
        'back':'EXACT straight BACK full-body view, facing directly away from the viewer. Back of head, jacket, trousers/skirt and shoes visible; absolutely NO face or eyes visible. Entire figure including hat if worn and shoes inside frame.',
        'face':'EXTREME CLOSE-UP FACE PORTRAIT, from clavicle to above head ONLY. Face fills most of the frame. NO waist, NO hands, NO legs, NO full body. Near-frontal face, eyes large and sharp; preserve face identity, hair, facial hair, spectacles and required headwear. Do not turn to side view.',
    }
    bare_heads={'C01','C03','C06','C08'}
    for role in roles:
        for view in ('side','back','face'):
            target=HERE/f'reference/{role}_{view}.png'
            if role=='C01' and view=='face':
                continue  # Dedicated face image already exists and was inspected.
            inputs=[f'reference/{role}.png']
            transforms=['head_crop'] if view=='face' else ['full']
            if view in {'side','back'}:
                inputs=[f'reference-guides/{view}.png',f'reference/{role}.png',f'reference/{role}.png']
                transforms=['full','head_crop','full']
            direction={
                'side':'严格左侧90度全身正交视图：鼻尖朝画面左边，只能见一只眼睛和一片眼镜。肩膀、腿和鞋前后重合，胸口不可朝向镜头。',
                'back':'严格180度背面全身正交视图：后脑勺和后背朝镜头，完全看不见脸和眼睛。',
                'face':'脸部大特写：只画头顶到锁骨，脸占画面大部分，不画腰部、手部和腿部。',
            }[view]
            prompt=direction+' '+instructions[view]+' '+story['characters'][role]
            if view in {'side','back'}:
                prompt+=' Image 1 controls the EXACT camera angle and full-body pose only. Image 2 is this character head identity; image 3 is this character costume, gender, body shape and colours. Match the pose of image 1, NEVER the pose of images 2 or 3. Replace the grey mannequin with this character.'
            else:
                prompt+=' Enlarge this supplied head crop into a face close-up, preserving its exact identity and headwear.'
            prompt+=' Fictional stylized cinematic 3D character, 1910, pale grey seamless studio, one figure only, no words, no panels. Preserve costume, hair, accessories and face identity.'
            if role in bare_heads:
                prompt+=' Bare head, no hat or cap.'
            rows.append(dict(id=f'{role}_{view}',role=role,view=view,file=str(target.relative_to(HERE)),
                             inputs=inputs,input_transforms=transforms,prompt=prompt,ratio='3:4'))
    rows.append(dict(id='P02',role=None,view='prop_revision',file='reference/P02.png',
        inputs=['reference/P02.png','reference/C01.png','reference/C03.png'],ratio='16:9',
        prompt='One single cinematic stylized 3D newspaper prop on black background. Preserve the first input newspaper layout, yellow paper, folds and abstract line columns. Correct ONLY its two illustrated portraits: the man must match the SECOND input character including round gold glasses and thick parted downward-sloping moustache; the woman must match the THIRD input including pinned black hair and beige blouse. All newspaper headings and columns must be abstract straight ink strokes, never readable words or letters. No readable title, no watermark, no other people, no panels or collage. The portraits are small ink drawings printed within one newspaper, not extra character figures.'))
    return rows


def make_payload(row):
    images=[]
    for index,name in enumerate(row['inputs']):
        data=(HERE/name).read_bytes()
        transforms=row.get('input_transforms',[])
        if index<len(transforms) and transforms[index]=='head_crop':
            with Image.open(io.BytesIO(data)) as original:
                w,h=original.size
                crop=original.crop((int(w*.32),0,int(w*.68),int(h*.48)))
                output=io.BytesIO();crop.save(output,format='PNG');data=output.getvalue()
        images.append('data:image/png;base64,'+base64.b64encode(data).decode('ascii'))
    return dict(model=MODEL,prompt=row['prompt'],size='1K',ratio=row['ratio'],
                extra_body={'image':images,'response_format':'url'})


def wait_gate():
    global LAST_START
    with GATE:
        delay=max(0,12-(time.monotonic()-LAST_START))
        if delay:time.sleep(delay)
        LAST_START=time.monotonic()


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True,stderr=subprocess.STDOUT,timeout=120)


def save(doc):
    with LOCK:
        tmp=RESULTS.with_suffix('.tmp')
        tmp.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
        tmp.replace(RESULTS)
        archive=HERE/'reference/batch-runs'
        archive.mkdir(exist_ok=True)
        (archive/(str(doc.get('run_id') or 'local')+'.json')).write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')


def publish():
    with LOCK:
        git('add','--','production/crippen1910/reference','production/crippen1910/story.json','production/crippen1910/screenplay.md','production/crippen1910/audio/manifest.json')
        if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode==0:return
        git('commit','-m','crippen1910: cloud reference candidates checkpoint [skip-crippen-batch]')
        for attempt in range(3):
            try:
                git('push','origin',BRANCH)
                return
            except subprocess.CalledProcessError:
                if attempt==2:raise
                git('pull','--rebase','--autostash','origin',BRANCH)


def contact_sheets(doc):
    rows=[row for row in doc['items'] if row.get('status')=='candidate_generated']
    qa=HERE/'reference/batch-review';qa.mkdir(exist_ok=True)
    for start in range(0,len(rows),9):
        selected=rows[start:start+9]
        sheet=Image.new('RGB',(1350,1590),'#d8d8d8');draw=ImageDraw.Draw(sheet)
        for index,row in enumerate(selected):
            x=(index%3)*450;y=(index//3)*530
            with Image.open(HERE/row['file']) as im:
                thumbnail=ImageOps.contain(im.convert('RGB'),(440,495))
                sheet.paste(thumbnail,(x+(450-thumbnail.width)//2,y+28))
            draw.text((x+10,y+8),row['id'],fill='black')
        sheet.save(qa/f'sheet-{start//9+1:02d}.jpg',quality=92)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--validate',action='store_true')
    parser.add_argument('--publish',action='store_true')
    parser.add_argument('--only',default='')
    parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args()
    story=json.loads((HERE/'story.json').read_text())
    rows=plan(story)
    assert len(rows)==30 and len({row['id'] for row in rows})==30
    for row in rows:
        for source in row['inputs']:
            assert (HERE/source).is_file(),source
    if args.only:
        wanted=set(args.only.split(','))
        if wanted-{row['id'] for row in rows}:raise ValueError('Unknown batch item')
        rows=[row for row in rows if row['id'] in wanted]
    if args.validate:
        print(f'VALID: {len(rows)} image-to-image requests, independent files, existing identity inputs, no video call')
        return 0
    key=os.environ.get('AGNES_API_KEY','')
    if not key:raise RuntimeError('Cloud AGNES_API_KEY is unavailable')
    if args.publish:
        if os.environ.get('GITHUB_ACTIONS')!='true' or git('branch','--show-current').strip()!=BRANCH:
            raise RuntimeError('Publishing allowed only in the fixed cloud branch')
        git('config','user.name','arena-autopilot')
        git('config','user.email','arena-autopilot@users.noreply.github.com')
    previous=json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    old={row['id']:row for row in previous.get('items',[])}
    doc=dict(model=MODEL,endpoint=ENDPOINT,planned_count=30,selected_count=len(rows),run_id=os.environ.get('GITHUB_RUN_ID'),
             source_revision=os.environ.get('GITHUB_SHA'),phase='generating_candidates',
             visual_review='pending',automatic_video_submission=False,items=[])
    for row in rows:
        record=dict(row,status='pending',input_sha256={name:digest((HERE/name).read_bytes()) for name in row['inputs']})
        # P02 uses its previous bytes as an editing source. Do not regenerate a completed
        # revision just because its own successful output replaced the original input.
        completed=old.get(row['id'],{})
        if completed.get('status')=='candidate_generated' and (HERE/row['file']).is_file() and digest((HERE/row['file']).read_bytes())==completed.get('sha256') and row['prompt']==completed.get('prompt') and all(name==row['file'] or completed.get('input_sha256',{}).get(name)==digest((HERE/name).read_bytes()) for name in row['inputs']):
            record=completed
        doc['items'].append(record)
    save(doc)
    def set_record(record, **values):
        with LOCK:
            record.update(values)
            save(doc)
    def generate(record):
        if record['status']=='candidate_generated':return True
        try:
            payload=make_payload(record)
            request_body=json.dumps(payload,ensure_ascii=False).encode('utf-8')
            set_record(record,status='submitting',request_sha256=digest(request_body))
            save(doc)
            for attempt in range(1,7):
                wait_gate()
                request=urllib.request.Request(ENDPOINT,data=request_body,method='POST',headers={
                    'Authorization':'Bearer '+key,'Content-Type':'application/json',
                    'User-Agent':'crippen-reference-batch/1.0',
                    'Idempotency-Key':record['request_sha256']})
                try:
                    with urllib.request.urlopen(request,timeout=360) as response:
                        result=json.loads(response.read())
                    break
                except urllib.error.HTTPError as exc:
                    set_record(record,last_http_status=exc.code)
                    # Record status only: server bodies may echo Data URIs. Never store them.
                    if exc.code==429 and attempt<6:
                        set_record(record,status='rate_limited')
                        time.sleep(max(61,min(180,int(exc.headers.get('Retry-After','61')) if str(exc.headers.get('Retry-After','61')).isdigit() else 61)))
                        continue
                    raise
            item=result.get('data',[{}])[0]
            set_record(record,response_created=result.get('created'))
            if item.get('b64_json'):
                image_data=base64.b64decode(item['b64_json'])
            elif item.get('url'):
                set_record(record,image_url=item['url'])
                with urllib.request.urlopen(item['url'],timeout=120) as response:
                    image_data=response.read(15*1024*1024+1)
            else:raise ValueError('No image URL or Base64 returned')
            if len(image_data)>15*1024*1024:raise ValueError('Output exceeds image size limit')
            with Image.open(io.BytesIO(image_data)) as im:
                im.load()
                if min(im.size)<256:raise ValueError('Output too small')
                output=io.BytesIO();im.convert('RGB').save(output,format='PNG',optimize=True)
                image_data=output.getvalue();dimensions=list(im.size)
            target=HERE/record['file']
            with LOCK:
                temporary=target.with_suffix('.download')
                temporary.write_bytes(image_data)
                temporary.replace(target)
                set_record(record,status='candidate_generated',sha256=digest(image_data),bytes=len(image_data),dimensions=dimensions,visual_review='pending')
            print('CANDIDATE',record['id'],dimensions,flush=True)
            save(doc)
            return True
        except Exception as exc:
            ambiguous=isinstance(exc,(TimeoutError,urllib.error.URLError)) and not isinstance(exc,urllib.error.HTTPError)
            set_record(record,status='submission_outcome_unknown' if ambiguous else 'failed',error_type=type(exc).__name__)
            print('FAILED',record['id'],type(exc).__name__,flush=True)
            save(doc)
            return False
    pending=[record for record in doc['items'] if record['status']!='candidate_generated']
    if pending:
        # One schema/quality canary before queueing the rest, in this same job.
        if not generate(pending[0]):
            doc['phase']='canary_failed';save(doc)
            if args.publish:publish()
            return 1
        if args.publish:publish()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(args.workers,2))) as pool:
            futures=[pool.submit(generate,row) for row in pending[1:]]
            completed=0
            for future in concurrent.futures.as_completed(futures):
                future.result();completed+=1
                if args.publish and completed%5==0:publish()
    doc['phase']='candidates_ready_for_review' if all(row['status']=='candidate_generated' for row in doc['items']) else 'incomplete'
    save(doc)
    contact_sheets(doc)
    # Regenerate content and the per-view missing-file inventory without approving anything.
    subprocess.run(['python3',str(HERE/'build_story.py')],cwd=ROOT,check=True)
    if args.publish:publish()
    return 0 if doc['phase']=='candidates_ready_for_review' else 1


if __name__=='__main__':
    raise SystemExit(main())
