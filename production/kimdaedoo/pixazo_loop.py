#!/usr/bin/env python3
"""Durable, serial Pixazo free LTX queue. API calls are paced, not busy-looped.
Only explicit queue/rate-limit rejections are retried on creation. Accepted IDs
survive rollover; ambiguous submission is a hard stop. No paid-model fallback.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.parse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'production'))
sys.path.insert(0, str(HERE))
import pixazo_video as api
from pixazo_video import full_payload, request_hash, MODEL
from generate import BRANCH

STATE = HERE/'pixazo-results.json'
CONTROL = HERE/'PIXAZO_REQUEST.json'
RELEASE = 'kimdaedoo-pixazo-source-clips'
INTERVAL = 75  # All create AND poll calls share this 1-per-75s gate.
TERMINAL_FAILED = {'failed','failure','error','cancelled','canceled','expired','rejected'}
TERMINAL_OK = {'completed','complete','succeeded','success','done','finished'}

class Pause(RuntimeError):
    pass


def classify(code, text, creating=False):
    s = text.lower()
    if 'insufficient balance' in s or 'insufficient_balance' in s or code == 402 or 'insufficient_user_quota' in s or 'insufficient user quota' in s or 'payment required' in s:
        return 'payment_or_quota'
    if code == 429:
        return 'rate_limit'
    if code in (401,403):
        return 'authentication_or_access'
    if 'model_not_found' in s or 'model not found' in s:
        return 'model_unavailable'
    if code == 503 and ('queue is full' in s or 'queue full' in s):
        return 'queue_full'
    if 200 <= code < 300:
        return 'ok'
    if code in (404,400) and not creating:
        return 'poll_endpoint_missing'
    if code >= 500:
        return 'submission_ambiguous' if creating else 'poll_transient'
    return 'request_rejected'


def cooldown(kind, streak, retry_after=0):
    if kind == 'queue_full':
        base = min(900, 120 * 2 ** min(max(streak-1,0), 3))
    elif kind == 'rate_limit':
        base = min(900, 150 * 2 ** min(max(streak-1,0), 3))
    else:
        base = min(900, INTERVAL * 2 ** min(max(streak-1,0), 4))
    return max(INTERVAL, base, retry_after or 0)


def nested(body):
    if not isinstance(body,dict):
        return {}
    for k in ('data','result'):
        if isinstance(body.get(k),dict):
            row = body[k]
            if any(x in row for x in ('status','video_id','task_id','id','url','video_url','metadata')):
                return row
    return body


def ids(body):
    row = nested(body)
    vid = row.get('request_id') or row.get('video_id') or row.get('id') or row.get('task_id')
    tid = row.get('task_id') or vid
    return (str(vid) if vid else None, str(tid) if tid else None)


def video_url(body):
    return api.find_video_url(nested(body)) or api.find_video_url(body)


def run(*args, capture=False):
    return subprocess.run(list(args),cwd=ROOT,check=True,text=True,capture_output=capture)


def git(*args):
    return run('git',*args,capture=True).stdout.strip()


def save(doc, publish=False):
    doc['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tmp = STATE.with_suffix('.tmp')
    tmp.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(STATE)
    if not publish:
        return
    if os.getenv('GITHUB_ACTIONS') != 'true' or git('branch','--show-current') != BRANCH:
        raise Pause('Checkpoint publishing allowed only on the fixed Actions branch')
    git('config','user.name','github-actions[bot]')
    git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    git('add',str(STATE.relative_to(ROOT)))
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
        git('commit','-m','kimdaedoo: save paced Pixazo generation queue')
        for attempt in range(3):
            try:
                git('push','origin',BRANCH)
                return
            except subprocess.CalledProcessError:
                git('fetch','origin',BRANCH)
                # A real conflict stops production rather than losing a task ID.
                git('rebase','FETCH_HEAD')
        raise Pause('Could not preserve task checkpoint remotely; no more API requests')


def safe(value, key):
    return json.loads(json.dumps(value,ensure_ascii=False).replace(key,'[redacted]')) if key else value


def record_request(doc, row, code, detail, kind):
    row['http'] = code
    row['detail'] = detail[:1500]
    row['attempt_count'] = row.get('attempt_count',0)+1
    history = row.setdefault('recent_responses',[])
    history.append({'at':time.time(),'http':code,'kind':kind,'detail':detail[:500]})
    del history[:-30]


def api_step(project, shot, doc, key, publish=False, now=None):
    """At most ONE provider HTTP request. Caller respects next_request_at."""
    now = time.time() if now is None else now
    if now < doc.get('next_request_at',0):
        return False
    sid = shot['id']
    wanted = request_hash(project,shot)
    row = doc['shots'].setdefault(sid,{'id':sid,'model':MODEL,'provider':'Pixazo','request_hash':wanted,'status':'pending'})
    if row.get('request_hash') != wanted:
        raise Pause('Prompt changed after production started: '+sid)
    if row['status'] in ('submitting','submission_ambiguous','manual_review_required','blocked'):
        raise Pause('Reconcile uncertain task before resubmission: '+sid)
    if row['status'] in ('completed','generated','download_retry'):
        return False
    creating = not row.get('video_id')
    doc['next_request_at'] = now + INTERVAL
    if creating:
        row['status'] = 'submitting'
        # Persist BEFORE POST; a killed process cannot silently duplicate a task.
        save(doc,publish)
        method,url,payload = 'POST',api.DEFAULT_BASE_URL+'/ltx-video/v1/text-to-video',full_payload(project,shot)
    else:
        method,payload = 'GET',None
        url = api.DEFAULT_BASE_URL+'/v2/requests/status/'+urllib.parse.quote(row['task_id'],safe='')
        save(doc,publish)
    try:
        response = api.http_json(method,url,key,payload,timeout=90)
        code,body,text = response
        if getattr(response,'retry_after',0):
            doc['next_request_at'] = max(doc['next_request_at'],time.time()+response.retry_after)
    except api.TransientError as e:
        if creating:
            row['status'] = 'submission_ambiguous'
            row['detail'] = str(e).replace(key,'[redacted]')[:1000]
            save(doc,publish)
            raise Pause('POST response lost; a task may exist. Never automatically POST again.')
        doc['retry_streak'] = doc.get('retry_streak',0)+1
        doc['next_request_at'] = time.time()+cooldown('poll_transient',doc['retry_streak'])
        row['status'] = 'poll_retry'
        save(doc,publish)
        return True
    kind = classify(code,text,creating)
    detail = api.describe_error(body,text,code).replace(key,'[redacted]')
    record_request(doc,row,code,detail,kind)
    # Pace from response completion, not from request start.
    doc['next_request_at'] = max(doc['next_request_at'],time.time()+INTERVAL)
    if kind in ('queue_full','rate_limit','poll_transient'):
        doc['retry_streak'] = doc.get('retry_streak',0)+1
        delay = cooldown(kind,doc['retry_streak'],getattr(response,'retry_after',None))
        doc['next_request_at'] = time.time()+delay
        row['status'] = 'retry_wait' if creating else 'poll_retry'
        doc['last_backoff_seconds'] = delay
        doc['phase'] = 'waiting_for_pixazo'
        save(doc,publish)
        print(f'{sid} {kind}: wait {delay:g}s; keep same task if already accepted',flush=True)
        return True
    if kind == 'poll_endpoint_missing':
        row['endpoint_misses'] = row.get('endpoint_misses',0)+1
        if row['endpoint_misses'] >= 8:
            row['status'] = 'manual_review_required'
            save(doc,publish)
            raise Pause('Accepted task missing on both poll endpoints; do not create replacement')
        row['poll_legacy'] = not row.get('poll_legacy',False)
        row['status'] = 'poll_retry'
        save(doc,publish)
        return True
    if kind != 'ok' or not isinstance(body,dict):
        row['status'] = 'blocked' if kind in ('payment_or_quota','authentication_or_access','model_unavailable','request_rejected') else 'submission_ambiguous'
        save(doc,publish)
        raise Pause(f'{sid}: {kind}; HTTP {code}. No other model/provider, no top-up.')
    doc['retry_streak'] = 0
    if creating:
        vid,tid = ids(body)
        row.update({'created':safe(body,key),'video_id':vid,'task_id':tid,
                    'status':'queued' if vid else 'submission_ambiguous'})
        if not vid:
            save(doc,publish)
            raise Pause('Accepted response without recognized task ID; reconcile, never resubmit')
        row['accepted_at'] = time.time()
        row['accepted_count'] = row.get('accepted_count',0)+1
        save(doc,publish)
        return True
    data = nested(body)
    state = str(data.get('status') or '').lower()
    row.update({'last_provider_state':state,'last_poll':safe(body,key)})
    url = video_url(body)
    if state in TERMINAL_OK or (not state and url):
        if url:
            row.update({'status':'generated','video_url':url})
        else:
            row['status'] = 'poll_retry'
    elif state in TERMINAL_FAILED:
        # Explicitly failed tasks are not in-flight. Retain IDs and permit at
        # most three fresh generations per shot, with a 15-minute cooldown.
        failures = row.setdefault('failed_tasks',[])
        failures.append({'video_id':row['video_id'],'task_id':row['task_id'],'response':safe(body,key)})
        row['failure_count'] = row.get('failure_count',0)+1
        if row['failure_count'] >= 3:
            row['status'] = 'manual_review_required'
            save(doc,publish)
            raise Pause('Three terminal task failures; inspect prompt/model rather than burn quota')
        for k in ('video_id','task_id','poll_legacy','endpoint_misses'):
            row.pop(k,None)
        row['status'] = 'retry_wait'
        doc['next_request_at'] = max(doc['next_request_at'],time.time()+900)
    else:
        row['status'] = 'poll_retry'
        if time.time()-row.get('accepted_at',time.time()) > 24*3600:
            save(doc,publish)
            raise Pause('Task pending for over 24h; inspect provider rather than submit another')
    save(doc,publish)
    return True


def archive_clip(shot, doc, key, publish=False):
    """Download, measure and archive immediately in a private GitHub Release.
    Provider CDN and 14-day artifacts are not treated as permanent storage.
    """
    row = doc['shots'][shot['id']]
    dest = ROOT/'work/kimdaedoo/sources'/(shot['id']+'.mp4')
    dest.parent.mkdir(parents=True,exist_ok=True)
    try:
        api.download(row['video_url'],dest,retries=2,retry_delay=15)
        from media import probe
        info = probe(dest)
        if info.get('duration',0) < shot['seconds']-.1 or info.get('width',0) < 640 or abs(info.get('width',0)/max(1,info.get('height',0))-16/9) > .03:
            raise Pause('Generated clip is too short/small: '+shot['id'])
        sha = hashlib.sha256(dest.read_bytes()).hexdigest()
        if row.get('sha256') and sha != row['sha256']:
            raise Pause('Provider bytes changed after verification: '+shot['id'])
        row.update({'sha256':sha,'bytes':dest.stat().st_size,'probe':info})
        if publish:
            repository = os.environ['GITHUB_REPOSITORY']
            asset_name = shot['id']+'-'+row['request_hash'][:12]+'-'+sha[:12]+'.mp4'
            upload = dest.with_name(asset_name)
            if not upload.exists():
                try:
                    upload.hardlink_to(dest)
                except OSError:
                    import shutil
                    shutil.copyfile(dest,upload)
            check = subprocess.run(['gh','release','view',RELEASE,'--repo',repository],cwd=ROOT,capture_output=True)
            if check.returncode:
                run('gh','release','create',RELEASE,'--repo',repository,'--target',BRANCH,
                    '--title','金大斗案 · Pixazo原始动画素材','--notes','仅素材归档，非已审成片；逐镜SHA和来源见production/kimdaedoo/pixazo-results.json','--prerelease')
            release = json.loads(run('gh','release','view',RELEASE,'--repo',repository,'--json','assets',capture=True).stdout)
            existing = next((a for a in release['assets'] if a['name']==asset_name),None)
            if not existing:
                run('gh','release','upload',RELEASE,str(upload),'--repo',repository)
                release = json.loads(run('gh','release','view',RELEASE,'--repo',repository,'--json','assets',capture=True).stdout)
                existing = next(a for a in release['assets'] if a['name']==asset_name)
            row['storage'] = {'release':RELEASE,'asset':asset_name,'url':existing['url'],'sha256':sha}
        row['status'] = 'completed'
        row.pop('download_error',None)
        row.pop('download_failures',None)
        doc['phase'] = 'generating'
        save(doc,publish)
        print('ARCHIVED',shot['id'],info.get('duration'),sha,flush=True)
    except Pause:
        raise
    except Exception as e:
        row['status'] = 'download_retry'
        row['download_failures'] = row.get('download_failures',0)+1
        row['download_error'] = str(e).replace(key,'[redacted]')[:1500]
        row['download_retry_at'] = time.time()+cooldown('download',row['download_failures'])
        save(doc,publish)
        if row['download_failures'] >= 8:
            raise Pause('Repeated download/archive failure; keep original URL/task, do not regenerate')


def control(publish=False):
    if publish:
        git('fetch','origin',BRANCH)
        return json.loads(git('show','FETCH_HEAD:production/kimdaedoo/PIXAZO_REQUEST.json'))
    return json.loads(CONTROL.read_text())


def output(name,value):
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:
            f.write(f'{name}={value}\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--budget-seconds',type=int,default=10800)
    p.add_argument('--publish',action='store_true')
    args = p.parse_args()
    project = json.loads((HERE/'story.json').read_text())
    cfg = control(args.publish)
    if not cfg.get('enabled') or not cfg.get('free_ltx_loop_authorized') or cfg.get('model') != MODEL:
        raise Pause('Queue not authorized/enabled for Pixazo free LTX')
    key = os.getenv('PIXAZO_API_KEY','').strip()
    if not key:
        raise Pause('Missing Actions PIXAZO_API_KEY secret; never paste credentials in chat')
    shots = [s for s in project['shots'] if s['kind']=='agnes']
    doc = json.loads(STATE.read_text()) if STATE.exists() else {'model':MODEL,'shots':{},'review':'pending'}
    if doc.get('model') != MODEL:
        raise Pause('Wrong model ledger')
    doc.update({'model':MODEL,'provider':'Pixazo','required_generated_shots':[s['id'] for s in shots],
                'billing_verified_free':False,'billing_note':'Model catalog tags free; account-level zero charge not measured','authorization':'User explicitly requested a paced free-LTX loop through GitHub until all shots finish',
                'rate_policy':{'all_provider_requests_min_interval_seconds':INTERVAL,'max_in_flight_tasks':1,
                               'queue_full_backoff_seconds':[120,240,480,900],
                               'honor_retry_after':True,'key_rotation':False,'paid_model_fallback':False},
                'phase':'generating','loop_status':'running'})
    # Do not open the older billing gate or pretend zero billing was measured.
    # Only free LTX is authorized here; any payment/quota response stops this loop.
    for s in shots:
        row = doc['shots'].get(s['id'])
        if row and row.get('request_hash') != request_hash(project,s):
            raise Pause('Plan changed; existing tasks must be reconciled')
    start = time.monotonic()
    next_control_check = 0
    output('continue','false')
    save(doc,args.publish)
    try:
        while time.monotonic()-start < args.budget_seconds:
            if time.monotonic() >= next_control_check:
                cfg = control(args.publish)
                if not cfg.get('enabled') or not cfg.get('free_ltx_loop_authorized') or cfg.get('model') != MODEL:
                    doc.update({'loop_status':'stopped_by_user','phase':'paused'})
                    save(doc,args.publish)
                    return 0
                next_control_check = time.monotonic()+120
            incomplete = [s for s in shots if doc['shots'].get(s['id'],{}).get('status')!='completed']
            doc['completed_count'] = len(shots)-len(incomplete)
            if not incomplete:
                doc.update({'loop_status':'completed','phase':'all_pixazo_sources_archived',
                            'review':'pending: full visual/audio QC still required; not a finished film'})
                save(doc,args.publish)
                output('all_complete','true')
                return 0
            # Only one active provider task; generated footage is archived before
            # any new task is created. No create/poll race or simultaneous workers.
            active = [s for s in incomplete if doc['shots'].get(s['id'],{}).get('video_id')]
            s = (active or incomplete)[0]
            row = doc['shots'].get(s['id'],{})
            if row.get('status') in ('generated','download_retry'):
                if time.time() >= row.get('download_retry_at',0):
                    archive_clip(s,doc,key,args.publish)
                else:
                    time.sleep(min(30,max(1,row['download_retry_at']-time.time())))
                continue
            delay = doc.get('next_request_at',0)-time.time()
            if delay > 0:
                remaining = args.budget_seconds-(time.monotonic()-start)
                time.sleep(max(0,min(30,delay,remaining)))
                continue
            api_step(project,s,doc,key,args.publish)
        doc.update({'loop_status':'rollover_required','phase':'waiting_for_next_actions_slice'})
        save(doc,args.publish)
        output('continue','true')
        return 0
    except Exception as e:
        doc.update({'loop_status':'paused_error','phase':'paused',
                    'pause_reason':str(e).replace(key,'[redacted]')[:2000]})
        save(doc,args.publish)
        output('continue','false')
        raise

if __name__ == '__main__':
    raise SystemExit(main())
