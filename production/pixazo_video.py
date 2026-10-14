"""PIXAZO free LTX endpoint only; no paid fallback or credentials in receipts.
Schema: https://www.pixazo.ai/models/ltx.md (ltx-v2-3-free variant).
Reusable download/error utilities below are transport-only, not Agnes calls.
"""
import hashlib
import http.client
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from agnes_video import (HttpResult, TransientError, parse_retry_after,
                         describe_error, download)

DEFAULT_BASE_URL = 'https://gateway.pixazo.ai'
MODEL = 'ltx-video-free'
CREATE_PATH = '/ltx-video/v1/text-to-video'


def full_payload(project, shot):
    if shot['aspect'] != '16:9' or shot['seconds'] != 6:
        raise ValueError('Only approved horizontal six-second source plan')
    prompt = project['style_prefix'] + shot['prompt']
    if not prompt.strip() or len(prompt) > 4000 or len(project['negative_prompt']) > 4000:
        raise ValueError('Invalid prompt length')
    # Both dimensions multiple of 32, true 16:9. 71,368,704 pixel-frames
    # stays below the documented 100M auto-truncation limit. 6.05s source.
    return {'prompt': prompt, 'negative': project['negative_prompt'],
            'width': 1024, 'height': 576, 'num_frames': 121,
            'frame_rate': 20, 'steps': 8, 'cfg': 3.0,
            'seed': 197500 + int(shot['id'][1:])}


def request_hash(project, shot):
    return hashlib.sha256(json.dumps({'endpoint': CREATE_PATH, 'payload': full_payload(project, shot)}, sort_keys=True).encode()).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # never forward subscription key to a redirect target


def http_json(method, url, key, payload=None, timeout=90):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc != 'gateway.pixazo.ai' or parsed.username:
        raise ValueError('Untrusted provider endpoint')
    if method == 'POST' and parsed.path != CREATE_PATH:
        raise ValueError('Only free LTX creation endpoint is authorized')
    if method == 'GET' and not parsed.path.startswith('/v2/requests/status/'):
        raise ValueError('Only universal task polling is authorized')
    if method not in ('POST', 'GET'):
        raise ValueError('Unsupported method')
    headers = {'Ocp-Apim-Subscription-Key': key, 'Accept': 'application/json',
               'Content-Type': 'application/json', 'User-Agent': 'kimdaedoo-pixazo/1.0'}
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as res:
            code, raw, rh = res.status, res.read(), res.headers
    except urllib.error.HTTPError as exc:
        code, raw, rh = exc.code, exc.read(), exc.headers
    except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, http.client.HTTPException) as exc:
        raise TransientError(type(exc).__name__) from exc
    text = raw.decode('utf-8', 'replace').replace(key, '[redacted]')
    try:
        body = json.loads(text)
    except ValueError:
        body = None
    delay = parse_retry_after(rh.get('Retry-After')) if rh else None
    return HttpResult(code, body, text, delay)


def find_video_url(body):
    if not isinstance(body, dict):
        return None
    out = body.get('output') or {}
    if not isinstance(out, dict):
        return None
    media = out.get('media_url')
    if isinstance(media, list):
        return next((x for x in media if isinstance(x, str) and x.startswith('https://')), None)
    if isinstance(media, str) and media.startswith('https://'):
        return media
    for k in ('video', 'preview_video'):
        item = out.get(k)
        if isinstance(item, dict) and str(item.get('url', '')).startswith('https://'):
            return item['url']
    return None
