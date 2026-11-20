#!/usr/bin/env python3
"""One paid Agnes S03 canary. Never issue duplicate create on an uncertain outcome."""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'production'))
import agnes_video as agnes

BRANCH = 'arena/aa4972d2-desktop-tutorial'
RESULT = HERE / 'qa' / 'S03_canary_v2.json'
OUT = ROOT / 'work' / 'baiyin_case' / 'canary' / 'S03_v2.mp4'
SHEET = HERE / 'qa' / 'S03_canary_v2.jpg'
MODEL = 'agnes-video-2.5-flash'
REF_REV = 'da3a0bf8c8d9a0ca174bfe934f51d7291ec129a2'


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, text=True, capture_output=True).stdout


def checkpoint(data, message, extra=()):
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    paths = [str(RESULT.relative_to(ROOT))] + [str(p.relative_to(ROOT)) for p in extra]
    git('add', '--', *paths)
    if subprocess.run(['git', 'diff', '--cached', '--quiet', '--', *paths], cwd=ROOT).returncode:
        git('commit', '-m', 'baiyin canary: ' + message, '--', *paths)
        # Stop rather than re-submit if another writer advanced the branch.
        git('push', 'origin', f'HEAD:refs/heads/{BRANCH}')
    print('CHECKPOINT', message, flush=True)


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REF') != f'refs/heads/{BRANCH}':
        raise SystemExit('Only run in the authorized current-branch Actions job')
    key = os.environ.get('AGNES_API_KEY', '').strip()
    if not key:
        raise SystemExit('AGNES_API_KEY missing')
    git('config', 'user.name', 'github-actions[bot]')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    shot = json.loads((HERE/'story.json').read_text(encoding='utf-8'))['shots'][2]
    if shot['id'] != 'S03':
        raise SystemExit('S03 missing from storyboard')
    prompt = ('电影级纪实情景演绎，冷峻克制的35mm胶片质感，1980年代中国西北工业小城。'
              '使用参考图的城市布局，蓝调时刻远景缓慢航拍下降，烟囱及街巷，微风轻轻推动薄雾，'
              '镜头连续稳定移动，真实动态视频，主体清晰，不出现人物与真实当事人肖像。'
              '画面不出现任何文字、标志、数字、字幕、水印、血腥、伤口、遗体或暴力。横版16:9。')
    payload = {'model': MODEL, 'prompt': prompt, 'seconds': str(max(4,min(12,shot['duration']))),
               'size': '720P', 'aspect_ratio': '16:9', 'mode': 'reference', 'n': 1,
               'seed': 19880527,
               'images': [f'https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/{REF_REV}/production/baiyin_case/reference/city_clean.png']}
    request_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    data = json.loads(RESULT.read_text()) if RESULT.is_file() else {}
    if data and data.get('request_hash') != request_hash:
        raise SystemExit('Existing task has different hash; refusing duplicate generation')
    if data.get('status') == 'completed':
        print('Already completed; no request issued')
        return
    if data and not data.get('video_id'):
        raise SystemExit('Prior submission unresolved: reconcile before another POST')
    base = os.environ.get('AGNES_BASE_URL', agnes.DEFAULT_BASE_URL).rstrip('/')
    if not data:
        data = {'shot': 'S03', 'status': 'submitting', 'request_hash': request_hash,
                'request': payload, 'reused_existing_asset': False, 'visual_review': 'pending'}
        checkpoint(data, 'submission prepared')
        try:
            # One attempt only. Even a timeout/429 is persisted as unknown, never auto-retried.
            created = agnes.create_task(base, key, payload, retries=1, retry_delay=1)
            video_id = created.get('video_id') or created.get('id') or created.get('task_id')
            if not video_id:
                raise RuntimeError('Provider response lacks task identifier')
            data.update(status='queued', video_id=str(video_id),
                        task_id=str(created.get('task_id') or created.get('id') or video_id))
            checkpoint(data, 'task accepted')
        except Exception as exc:
            data.update(status='create_unknown', error=str(exc).replace(key, '[redacted]')[:400])
            checkpoint(data, 'submission unresolved')
            raise
    try:
        time.sleep(13)
        final, url = agnes.poll_task(base, key, MODEL, data['video_id'], data.get('task_id'),
                                     interval=45, timeout=1800, max_failures=8)
        size = agnes.download(url, OUT, retries=3, retry_delay=5)
        probe = subprocess.run(['ffprobe', '-v','error','-show_format','-show_streams','-of','json', str(OUT)],
                               capture_output=True, text=True, check=True)
        info = json.loads(probe.stdout)
        streams = [s for s in info['streams'] if s['codec_type']=='video']
        if not streams or float(info['format']['duration']) < 4:
            raise RuntimeError('Canary failed technical decode/duration check')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel','error','-y','-i',str(OUT),
                        '-vf','fps=1/2,scale=480:-1,tile=3x1','-frames:v','1',str(SHEET)], check=True)
        data.update(status='completed', video_url=url, bytes=size,
                    sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),
                    codec=streams[0].get('codec_name'), width=streams[0].get('width'),
                    height=streams[0].get('height'), duration=float(info['format']['duration']),
                    visual_review='pending', provider_status=final.get('status'))
        checkpoint(data, 'completed; visual review pending', extra=(SHEET,))
    except Exception as exc:
        data.update(status='poll_or_download_failed', error=str(exc).replace(key, '[redacted]')[:400])
        checkpoint(data, 'poll or download failed')
        raise

if __name__ == '__main__':
    main()
