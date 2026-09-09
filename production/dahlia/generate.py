#!/usr/bin/env python3
"""Generate only Agnes V2.0 shots; checkpoint small metadata, never commit video bytes."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'production'))
import agnes_video as agnes

BRANCH = 'arena/01a083bb-desktop-tutorial'
PLAN = Path(__file__).with_name('story.json')
RESULTS = Path(__file__).with_name('results.json')
LOCK = threading.RLock()


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def full_payload(project, shot):
    return agnes.build_payload(argparse.Namespace(
        prompt=project['style_prefix'] + shot['prompt'], negative_prompt=project['negative_prompt'],
        image=None, mode=None, seed=shot['seed'], steps=None, seconds=shot['seconds'],
        num_frames=None, frame_rate=shot['frame_rate'], aspect=shot['aspect'],
        resolution=shot['resolution'], width=None, height=None, model=agnes.DEFAULT_MODEL))


def validate(project):
    assert project['target_duration'] == 180
    assert len(project['shots']) == 30
    assert len({shot['id'] for shot in project['shots']}) == 30
    for i, shot in enumerate(project['shots']):
        assert shot['start'] == i * 6 and shot['duration'] == 6
        assert shot['kind'] in ('agnes', 'graphic')
        if shot['kind'] == 'agnes':
            assert shot['prompt'].strip()
            payload = full_payload(project, shot)
            assert payload['model'] == 'agnes-video-v2.0'
            assert (payload['num_frames'] - 1) % 8 == 0
        else:
            assert shot['graphic'].strip()
    assert sum(c['duration'] for c in project['chapters']) == 180


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True,
                                   stderr=subprocess.STDOUT, timeout=90)


def review_matches(review, first_result):
    """A visual approval applies only to the exact first-shot request and bytes."""
    return (
        isinstance(review, dict)
        and review.get('decision') == 'approved'
        and review.get('first_shot_id') == first_result.get('id')
        and bool(first_result.get('sha256'))
        and review.get('video_sha256') == first_result.get('sha256')
        and bool(first_result.get('request_hash'))
        and review.get('request_hash') == first_result.get('request_hash')
    )


def wait_for_review(first_result, timeout=1800):
    """The already-running job waits for a reviewed JSON file on this same branch.

    No new Actions dispatch or secret access is needed to approve the first clip.
    The remaining generation requests are not submitted until this gate passes.
    """
    deadline = time.monotonic() + timeout
    print('WAITING_FOR_VISUAL_REVIEW: ' + first_result['id'], flush=True)
    while time.monotonic() < deadline:
        try:
            git('fetch', '--no-tags', 'origin', BRANCH)
            raw = git('show', 'FETCH_HEAD:production/dahlia/review.json')
            review = json.loads(raw)
            if review_matches(review, first_result):
                return review
            if (isinstance(review, dict) and review.get('decision') == 'rejected'
                    and review.get('video_sha256') == first_result.get('sha256')):
                raise RuntimeError('First shot was rejected during visual review; batch not submitted')
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
            # Missing approval is expected while the reviewer is inspecting the clip.
            pass
        time.sleep(min(20, max(0, deadline - time.monotonic())))
    raise RuntimeError('First-shot review timed out; no remaining clips were submitted')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--payload', default='{}')
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    project = read_json(PLAN, {})
    validate(project)
    if args.validate:
        print('VALID: 180 seconds, 30 shots, 24 Agnes clips and 6 graphics.'); return 0
    options = json.loads(args.payload or '{}')
    requested = options.get('only', '')
    if not isinstance(requested, str): raise ValueError('only must be comma-separated IDs')
    only = {s.strip() for s in requested.split(',') if s.strip()}
    shots = [s for s in project['shots'] if s['kind'] == 'agnes']
    if only - {s['id'] for s in shots}: raise ValueError('Unknown or non-Agnes shot ID')
    if only: shots = [s for s in shots if s['id'] in only]
    workers = min(2, max(1, int(options.get('workers', 2))))
    publish = args.publish
    if publish:
        if os.getenv('GITHUB_ACTIONS') != 'true' or git('branch', '--show-current').strip() != BRANCH:
            raise RuntimeError('Publishing is allowed only from the fixed Arena branch in Actions')
        git('config', 'user.name', 'github-actions[bot]')
        git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    doc = read_json(RESULTS, {'project': project['title'], 'model': agnes.DEFAULT_MODEL, 'shots': {}})
    out = ROOT / 'work' / 'dahlia' / 'clips'; out.mkdir(parents=True, exist_ok=True)
    key = os.environ.get('AGNES_API_KEY', '').strip()
    base = os.environ.get('AGNES_BASE_URL', agnes.DEFAULT_BASE_URL).rstrip('/')

    def checkpoint(sid, **values):
        with LOCK:
            row = doc['shots'].setdefault(sid, {'id': sid})
            row.update(values)
            row['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            doc['updated_at'] = row['updated_at']
            doc['run_id'] = os.getenv('GITHUB_RUN_ID')
            RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n')
            if publish:
                rel = str(RESULTS.relative_to(ROOT))
                git('add', '--', rel)
                changed = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', rel], cwd=ROOT).returncode
                if changed:
                    git('commit', '-m', f'dahlia: {sid} {row.get("status", "checkpoint")}', '--', rel)
                    for attempt in range(3):
                        try:
                            git('push', 'origin', BRANCH)
                            break
                        except subprocess.CalledProcessError:
                            if attempt == 2:
                                raise
                            # A visual-review approval may have advanced this same
                            # branch. Rebase only this job's metadata commit; never
                            # force-push or modify the approval file.
                            git('pull', '--rebase', 'origin', BRANCH)
            print('SHOT_STATUS ' + sid + ' ' + str(row.get('status')), flush=True)

    def generate(shot):
        sid = shot['id']
        payload = full_payload(project, shot)
        request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with LOCK: old = dict(doc['shots'].get(sid, {}))
        if old.get('request_hash') != request_hash:
            old = {}
        if old.get('status') == 'completed' and old.get('video_url'):
            print(f'{sid}: existing matching result retained', flush=True); return True
        if not key:
            checkpoint(sid, status='blocked', error='AGNES_API_KEY is not available to this workflow', request_hash=request_hash)
            return False
        try:
            video_id, task_id = old.get('video_id'), old.get('task_id')
            if video_id:
                print(f'{sid}: resuming recorded task (no new create request)', flush=True)
            else:
                checkpoint(sid, status='submitting', request_hash=request_hash, error=None)
                created = agnes.create_task(base, key, payload, retries=2, retry_delay=10)
                video_id = created.get('video_id') or created.get('id') or created.get('task_id')
                task_id = created.get('task_id') or created.get('id')
                if not video_id: raise agnes.Fatal('No video/task identifier returned')
                checkpoint(sid, status='queued', request_hash=request_hash,
                           video_id=str(video_id), task_id=str(task_id or ''),
                           requested_seconds=payload['num_frames']/payload['frame_rate'])
            final, url = agnes.poll_task(base, key, agnes.DEFAULT_MODEL, str(video_id), str(task_id) if task_id else None,
                                        interval=8, timeout=1500, max_failures=12)
            target = out / (sid + '.mp4')
            size = agnes.download(url, target, retries=3, retry_delay=5)
            # Store provenance separately from the large clip.
            checksum = hashlib.sha256(target.read_bytes()).hexdigest()
            receipt = {'id': sid, 'provider': 'agnes', 'model': agnes.DEFAULT_MODEL,
                       'request_hash': request_hash, 'request': payload, 'video_id': str(video_id),
                       'video_url': url, 'bytes': size, 'sha256': checksum,
                       'reported_size': final.get('size'), 'reported_seconds': final.get('seconds')}
            target.with_suffix('.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
            checkpoint(sid, status='completed', video_url=url, bytes=size, sha256=checksum,
                       reported_size=final.get('size'), reported_seconds=final.get('seconds'), error=None)
            return True
        except Exception as exc:
            error = str(exc).replace(key, '[redacted]') if key else str(exc)
            # A receipt prevents automatic recreation of an already-submitted task.
            checkpoint(sid, status='failed', error=error[:600])
            print(f'{sid}: failed: {error[:600]}', flush=True)
            return False

    requested_count = len(shots)
    outcomes = []
    if publish and not only and requested_count > 1:
        # One manual workflow start is sufficient: generate a canary, wait for
        # human visual review recorded on this branch, then continue the batch.
        first = shots[0]
        if not generate(first):
            print('FIRST_SHOT_FAILED: remaining clips were not submitted', flush=True)
            return 1
        outcomes.append(True)
        first_result = dict(doc['shots'][first['id']])
        doc['review'] = {'status': 'awaiting_visual_review', 'first_shot_id': first['id']}
        checkpoint(first['id'])
        try:
            approval = wait_for_review(first_result)
        except RuntimeError as exc:
            doc['review'] = {'status': 'stopped', 'reason': str(exc), 'first_shot_id': first['id']}
            checkpoint(first['id'])
            print(str(exc), flush=True)
            return 1
        doc['review'] = {'status': 'approved', 'first_shot_id': first['id'],
                         'video_sha256': approval['video_sha256']}
        checkpoint(first['id'])
        shots = shots[1:]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes.extend(pool.map(generate, shots))
    print(f'COMPLETE: {sum(outcomes)}/{requested_count} requested clips available', flush=True)
    summary = os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as handle:
            handle.write(f'## 黑色大丽花 · Agnes V2.0\n\n{sum(outcomes)}/{requested_count} requested clips completed.\n\n')
            handle.write('Videos are artifacts, not Git objects. Task provenance is in `production/dahlia/results.json`.\n')
    return 0 if all(outcomes) else 1


if __name__ == '__main__':
    raise SystemExit(main())
