#!/usr/bin/env python3
"""Validation only: no valid generation request, no paid-model fallback."""
import datetime
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

BASE = 'https://apihub.agnes-ai.com'
HERE = Path(__file__).resolve().parent
MODELS = ('agnes-video-v2.0', 'agnes-video-2.5', 'agnes-video-2.5-flash')


def classify(code, text):
    s = text.lower()
    if code == 429:
        return 'rate_limited'
    if code == 402 or 'insufficient_user_quota' in s or 'insufficient user quota' in s:
        return 'quota_or_payment_required'
    if code in (401, 403):
        return 'auth_or_access_denied'
    if 'model_not_found' in s or 'model not found' in s:
        return 'model_unavailable'
    if 'queue is full' in s or 'queue full' in s:
        return 'queue_full_not_proof_of_free_generation'
    if 200 <= code < 300:
        return 'unexpected_acceptance_stop'
    if code in (400, 422) and any(x in s for x in ('prompt', 'seconds', 'frames')):
        return 'validation_rejected_free_generation_unverified'
    return 'unknown'


def request(path, key, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
        'User-Agent': 'kimdaedoo-validation/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            code, raw = r.status, r.read(65536)
    except urllib.error.HTTPError as e:
        code, raw = e.code, e.read(65536)
    except (OSError, TimeoutError) as e:
        return {'http': None, 'verdict': 'network_error', 'detail': str(e).replace(key, '[redacted]')[:1000]}
    text = raw.decode('utf-8', 'replace').replace(key, '[redacted]')
    return {'http': code, 'verdict': classify(code, text), 'detail': text[:5000]}


def main():
    out = HERE / 'probe'
    out.mkdir(exist_ok=True)
    report = {'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'mode': 'invalid-prompt validation only; never submits usable video',
              'billing_verified_free': False, 'generation_started': False, 'models': []}
    key = os.environ.get('AGNES_API_KEY', '').strip()
    def save():
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    if not key:
        report['blocked'] = 'AGNES_API_KEY missing in Actions'
        save()
        return 1
    report['model_list'] = request('/v1/models', key)
    save()
    for i, model in enumerate(MODELS):
        if i:
            time.sleep(75)
        payload = ({'model': model, 'prompt': '', 'width': 832, 'height': 448,
                    'num_frames': 0, 'frame_rate': 24} if model.endswith('v2.0') else
                   {'model': model, 'prompt': '', 'seconds': '0', 'mode': 'text',
                    'size': '720P', 'aspect_ratio': '16:9'})
        result = request('/v1/videos', key, payload)
        report['models'].append({'model': model, **result})
        save()
        print(model, result['verdict'], flush=True)
        if result['verdict'] == 'unexpected_acceptance_stop':
            report['blocked'] = 'Provider accepted an invalid request; do not retry or poll automatically'
            save()
            return 1
    report['blocked'] = 'Validation cannot establish zero-cost generation; no actual clips requested'
    save()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
