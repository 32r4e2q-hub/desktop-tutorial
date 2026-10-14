#!/usr/bin/env python3
"""Agnes 2.5-flash only. Default is dry-run; generation is blocked until zero-cost
eligibility is independently verified in billing-policy.json. No vendor fallback.
A successful validation or a queue-full response is NOT a billing proof.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'production'))
import agnes_video as api

MODEL = 'agnes-video-2.5-flash'
BRANCH = 'arena/09864331-desktop-tutorial'
BASE = 'https://apihub.agnes-ai.com'
RESULTS = HERE / 'results.json'


def full_payload(project, shot):
    if project.get('model') != MODEL or shot.get('aspect') != '16:9':
        raise ValueError('Only Agnes 2.5-flash / 16:9 is allowed')
    if shot['seconds'] not in (4, 6, 8):
        raise ValueError('Unsupported planned duration; confirm against current provider schema')
    # 2.5 uses seconds/mode/size/aspect_ratio, NOT the retired v2.0 frame payload.
    return {'model': MODEL, 'prompt': project['style_prefix'] + shot['prompt'] +
            ' Avoid: ' + project['negative_prompt'], 'seconds': str(shot['seconds']),
            'mode': 'text', 'size': '720P', 'aspect_ratio': '16:9'}


def request_hash(project, shot):
    return hashlib.sha256(json.dumps(full_payload(project, shot), sort_keys=True).encode()).hexdigest()


def validate(project, require_audio=False):
    if project['target_duration'] != 180 or len(project['shots']) != 45:
        raise ValueError('Expected 180 seconds and 45 shots')
    if (project['width'], project['height'], project['fps']) != (1920, 1080, 30):
        raise ValueError('Invalid output specification')
    if len({s['id'] for s in project['shots']}) != 45:
        raise ValueError('Duplicate shot ids')
    for i, s in enumerate(project['shots']):
        if s['start'] != i * 4 or s['duration'] != 4:
            raise ValueError('Invalid planning grid')
        if s['kind'] == 'agnes':
            if not s['prompt'].strip():
                raise ValueError('Empty prompt')
            full_payload(project, s)
        elif s['kind'] != 'graphic' or s['id'] not in project['presentation']['cards']:
            raise ValueError('Missing information card')
    manifest = json.loads((HERE / 'audio/manifest.json').read_text())
    by_id = {x['id']: x for x in manifest['clips']}
    if len(project['chapters']) != 6 or sum(c['duration'] for c in project['chapters']) != 180:
        raise ValueError('Invalid chapter plan')
    for c in project['chapters']:
        row = by_id[c['id']]
        if not c['text'] or c['text'] != row['text']:
            raise ValueError('Narration text mismatch')
        if require_audio:
            path = HERE / 'audio' / row['file']
            if not path.is_file() or digest(path) != row.get('sha256'):
                raise ValueError('Missing or changed narration: ' + c['id'])


def billing_gate(policy, now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if policy.get('model') != MODEL or policy.get('zero_cost_verified') is not True:
        raise RuntimeError('BLOCKED: no verified free-generation eligibility; no task submitted')
    if policy.get('max_charge') != 0 or not policy.get('evidence_url'):
        raise RuntimeError('BLOCKED: no zero-charge evidence')
    expiry = datetime.datetime.fromisoformat(policy['expires_at'].replace('Z', '+00:00'))
    if expiry <= now:
        raise RuntimeError('BLOCKED: free eligibility evidence expired')
    # This is a local guard, not a server-side spending cap. Never populate it from
    # model-list/validation results; only from account eligibility/pricing evidence.


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checkpoint(doc, publish=False):
    temp = RESULTS.with_suffix('.tmp')
    temp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
    temp.replace(RESULTS)
    if publish:
        branch = subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
        if os.getenv('GITHUB_ACTIONS') != 'true' or branch != BRANCH:
            raise RuntimeError('Checkpoint publishing is restricted to the fixed Actions branch')
        def git(*args):
            return subprocess.run(['git',*args],cwd=ROOT,check=True)
        git('config','user.name','github-actions[bot]')
        git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
        git('add', str(RESULTS.relative_to(ROOT)))
        changed = subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode
        if changed:
            git('commit','-m','kimdaedoo: save Agnes task checkpoint')
            # Do not hide push failures: stop before any more API submissions.
            git('push','origin',BRANCH)


def run_shot(project, shot, doc, key, publish=False):
    sid = shot['id']
    wanted = request_hash(project, shot)
    row = doc['shots'].get(sid)
    if row and row.get('request_hash') != wanted:
        raise RuntimeError('Changed prompt needs an explicit new generation/version: ' + sid)
    row = doc['shots'].setdefault(sid, {'id':sid,'request_hash':wanted,'model':MODEL,'provider':'Agnes'})
    if row.get('status') == 'completed':
        print('REUSE',sid)
        return
    if row.get('status') in ('submission_ambiguous','submitting','failed'):
        raise RuntimeError('Manual reconciliation required; never blindly resubmit: ' + sid)
    if not row.get('video_id'):
        for attempt in range(3):
            row['status'] = 'submitting'
            checkpoint(doc, publish)
            try:
                code, body, text = api.http_json('POST', BASE+'/v1/videos',key,
                                                full_payload(project,shot),timeout=120)
            except api.TransientError:
                row['status'] = 'submission_ambiguous'
                checkpoint(doc,publish)
                raise RuntimeError('Submission response lost; reconcile provider tasks before retrying')
            if 200 <= code < 300 and isinstance(body,dict):
                row.update({'created':body,'video_id':body.get('video_id') or body.get('id'),
                            'task_id':body.get('task_id'), 'status':'queued'})
                if not row['video_id']:
                    row['status'] = 'submission_ambiguous'
                    checkpoint(doc,publish)
                    raise RuntimeError('Accepted response has no known video id; do not submit again')
                checkpoint(doc,publish)
                break
            detail = api.describe_error(body,text,code).replace(key,'[redacted]')
            definitive_rejection = code < 500 or 'queue' in detail.lower() or 'model_not_found' in detail.lower()
            row.update({'http':code,'detail':detail,'status':'rejected' if definitive_rejection else 'submission_ambiguous'})
            checkpoint(doc,publish)
            if code == 429 or (code == 503 and 'queue' in detail.lower()):
                if attempt == 2:
                    raise RuntimeError('Queue/limit still blocked; stopped after 3 paced attempts')
                time.sleep(120*(attempt+1))
                continue
            raise RuntimeError(f'Provider refused request: HTTP {code}; no alternate model/provider')
    final, url = api.poll_task(BASE,key,MODEL,row['video_id'],row.get('task_id'),
                              interval=75,timeout=1800,max_failures=3)
    row.update({'status':'generated','final':final,'video_url':url})
    checkpoint(doc,publish)
    dest = ROOT/'work/kimdaedoo/sources'/f'{sid}.mp4'
    dest.parent.mkdir(parents=True,exist_ok=True)
    api.download(url,dest,retries=2,retry_delay=10)
    from media import probe
    info = probe(dest)
    if info.get('duration',0) < shot['seconds']-0.5 or info.get('width',0) < 640:
        raise RuntimeError('Generated clip is too short/small')
    row.update({'status':'completed','sha256':digest(dest),'bytes':dest.stat().st_size,'probe':info})
    checkpoint(doc,publish)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--validate',action='store_true')
    p.add_argument('--require-audio',action='store_true')
    p.add_argument('--execute',action='store_true')
    p.add_argument('--only',default='S01')
    p.add_argument('--publish',action='store_true')
    args=p.parse_args()
    project=json.loads((HERE/'story.json').read_text())
    validate(project,args.require_audio)
    if not args.execute:
        print('PLAN VALID: 180s grid / 38 Agnes + 7 cards; audio hashes checked' if args.require_audio else 'PLAN VALID: 180s grid / 38 Agnes + 7 cards; no audio check requested')
        print('This is not video generation, a billing confirmation or final QC approval')
        return
    policy=json.loads((HERE/'billing-policy.json').read_text())
    billing_gate(policy)
    chosen=set(args.only.split(','))
    eligible={s['id'] for s in project['shots'] if s['kind']=='agnes'}
    if not chosen or chosen-eligible:
        raise ValueError('Unknown/non-Agnes shot ID')
    if len(chosen)>1 and policy.get('canary_review_passed') is not True:
        raise RuntimeError('BLOCKED: single-clip visual review required before batch generation')
    key=os.environ.get('AGNES_API_KEY','').strip()
    if not key:
        raise RuntimeError('AGNES_API_KEY absent; use connected Actions secret, never paste it in chat')
    doc=json.loads(RESULTS.read_text()) if RESULTS.exists() else {'model':MODEL,'shots':{},'review':'pending'}
    for s in project['shots']:
        if s['id'] in chosen:
            run_shot(project,s,doc,key,args.publish)
            if len(chosen)>1:
                time.sleep(75)

if __name__ == '__main__':
    main()
