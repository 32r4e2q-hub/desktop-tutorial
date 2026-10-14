#!/usr/bin/env python3
"""A single 4-second Agnes Flash canary through the existing Actions secret.

This is an availability trial, NOT a declaration that billing is free. The batch
billing gate remains closed. Never try another model/provider, never resubmit an
accepted or ambiguous task. Queue-full/429 refusals permit two paced retries.
"""
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
sys.path.insert(0, str(HERE))
import agnes_video as api
from generate import full_payload, MODEL, BRANCH

RECEIPT = HERE / 'canary-receipt.json'
DEST = ROOT / 'work/kimdaedoo/canary/S01-4s.mp4'


def extract_ids(body):
    for row in (body, body.get('data'), body.get('result')):
        if isinstance(row, dict):
            vid = row.get('video_id') or row.get('id')
            tid = row.get('task_id')
            if vid or tid:
                return str(vid or tid), str(tid or vid)
    return None, None


def safe(value, key):
    return json.loads(json.dumps(value, ensure_ascii=False).replace(key, '[redacted]')) if key else value


def checkpoint(doc, key):
    doc['updated_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    temp = RECEIPT.with_suffix('.tmp')
    temp.write_text(json.dumps(safe(doc, key), ensure_ascii=False, indent=2) + '\n')
    temp.replace(RECEIPT)
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        def git(*args):
            subprocess.run(['git', *args], cwd=ROOT, check=True)
        branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
        if branch != BRANCH:
            raise RuntimeError('Wrong production branch')
        git('config', 'user.name', 'github-actions[bot]')
        git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
        git('add', str(RECEIPT.relative_to(ROOT)))
        if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=ROOT).returncode:
            git('commit', '-m', 'kimdaedoo: checkpoint single Agnes Flash trial')
            git('push', 'origin', BRANCH)


def main():
    key = os.environ.get('AGNES_API_KEY', '').strip()
    project = json.loads((HERE / 'story.json').read_text())
    shot = dict(project['shots'][0], seconds=4)
    payload = full_payload(project, shot)
    assert payload['model'] == MODEL == 'agnes-video-2.5-flash'
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    doc = json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {
        'model': MODEL, 'provider': 'Agnes', 'shot': 'S01', 'seconds': 4,
        'request_hash': digest, 'request': payload, 'accepted_tasks': 0,
        'billing_verified_free': False, 'batch_started': False,
        'authorization': 'User asked to access Agnes through the API secret stored in GitHub; single Flash availability trial only',
        'review': 'pending', 'attempts': []}
    if doc.get('request_hash') != digest:
        raise RuntimeError('Changed canary request: reconcile old task before starting another')
    if doc.get('status') == 'completed':
        print('Canary already completed; no new task submitted')
        return 0
    if not key:
        doc['status'] = 'missing_actions_secret'
        checkpoint(doc, key)
        return 1
    if doc.get('status') in ('submitting', 'submission_ambiguous'):
        raise RuntimeError('Submission may already exist: manual reconciliation required, not resubmitting')
    try:
        if not doc.get('video_id'):
            for attempt in range(3):
                doc['status'] = 'submitting'
                checkpoint(doc, key)
                try:
                    response = api.http_json('POST', api.DEFAULT_BASE_URL + '/v1/videos', key, payload, timeout=120)
                except api.TransientError:
                    doc['status'] = 'submission_ambiguous'
                    checkpoint(doc, key)
                    raise RuntimeError('Response lost; no retry because a task may exist')
                code, body, text = response
                detail = api.describe_error(body, text, code).replace(key, '[redacted]')
                doc['attempts'].append({'http': code, 'detail': detail[:1500]})
                if 200 <= code < 300 and isinstance(body, dict):
                    vid, tid = extract_ids(body)
                    doc.update({'created': safe(body, key), 'video_id': vid, 'task_id': tid,
                                'status': 'queued' if vid else 'submission_ambiguous', 'accepted_tasks': 1})
                    checkpoint(doc, key)
                    if not vid:
                        raise RuntimeError('Accepted but no task ID recognized; never submit again')
                    break
                definitive = code < 500 or 'queue' in detail.lower() or 'model_not_found' in detail.lower()
                doc['status'] = 'rejected' if definitive else 'submission_ambiguous'
                checkpoint(doc, key)
                if code == 429 or (code == 503 and 'queue' in detail.lower()):
                    if attempt == 2:
                        doc['status'] = 'queue_or_rate_limit_blocked'
                        checkpoint(doc, key)
                        return 2
                    time.sleep(max(120 * (attempt + 1), getattr(response, 'retry_after', None) or 0))
                    continue
                # Payment/quota/auth/unavailable and all other errors stop immediately.
                print(f'Flash trial refused: HTTP {code}. No alternate model/provider.')
                return 1
        if not doc.get('video_url'):
            final, url = api.poll_task(api.DEFAULT_BASE_URL, key, MODEL, doc['video_id'], doc.get('task_id'),
                                      interval=75, timeout=1800, max_failures=3)
            doc.update({'status': 'generated', 'video_url': url, 'final': safe(final, key)})
            checkpoint(doc, key)
        api.download(doc['video_url'], DEST, retries=2, retry_delay=15)
        from media import probe
        info = probe(DEST)
        if info.get('width', 0) < 640 or info.get('duration', 0) < 3.5:
            raise RuntimeError('Downloaded canary is too short or small')
        doc.update({'status': 'completed', 'sha256': hashlib.sha256(DEST.read_bytes()).hexdigest(),
                    'bytes': DEST.stat().st_size, 'probe': info, 'review': 'pending',
                    'note': 'Successful generation is not proof of zero billing; no batch or paid fallback started.'})
        checkpoint(doc, key)
        print('Agnes canary downloaded and technically measured; visual review still pending')
        return 0
    except Exception as e:
        doc['last_error'] = str(e).replace(key, '[redacted]')[:2000]
        checkpoint(doc, key)
        raise


if __name__ == '__main__':
    raise SystemExit(main())
