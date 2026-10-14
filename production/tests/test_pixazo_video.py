"""PIXAZO schema, serial pacing and durable submission safety; no network."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import pytest

PROD = Path(__file__).resolve().parents[1]
HERE = PROD/'kimdaedoo'

@pytest.fixture
def engine(monkeypatch):
    oldpath = list(sys.path)
    old = sys.modules.pop('generate', None)
    try:
        spec = importlib.util.spec_from_file_location('pixazo_queue', HERE/'pixazo_loop.py')
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    finally:
        sys.path[:] = oldpath
        sys.modules.pop('generate', None)
        if old is not None:
            sys.modules['generate'] = old
    m.saved = []
    monkeypatch.setattr(m, 'save', lambda d, publish=False: m.saved.append(copy.deepcopy(d)))
    monkeypatch.setattr(m.time, 'time', lambda: 1000)
    return m

@pytest.fixture
def project():
    return json.loads((HERE/'story.json').read_text())


def test_schema_prevents_pixel_budget_truncation(engine, project):
    for s in project['shots']:
        if s['kind'] != 'agnes':
            continue
        p = engine.full_payload(project, s)
        assert p['width'] % 32 == p['height'] % 32 == 0
        assert p['width']/p['height'] == 16/9
        assert p['width']*p['height']*p['num_frames'] <= 100_000_000
        assert p['num_frames']/p['frame_rate'] >= s['seconds']
        assert p['num_frames'] <= 121 and (p['num_frames']-1)%8 == 0
        assert 'negative' in p and 'negative_prompt' not in p and 'aspect' not in p


def test_accept_poll_archive_order_and_cooldown(engine, project, monkeypatch):
    calls = []
    responses = iter([
        engine.api.HttpResult(202, {'request_id': 'r1', 'status': 'QUEUED'}, '{}'),
        engine.api.HttpResult(200, {'request_id': 'r1', 'status': 'COMPLETED', 'output': {'media_url': ['https://example.com/clip.mp4']}}, '{}')])
    def http(method, url, *a, **kw):
        calls.append((method, url))
        return next(responses)
    monkeypatch.setattr(engine.api, 'http_json', http)
    doc = {'shots': {}}
    shot = project['shots'][0]
    engine.api_step(project, shot, doc, 'test-key', now=1000)
    assert engine.saved[0]['shots']['S01']['status'] == 'submitting'
    assert not engine.api_step(project, shot, doc, 'test-key', now=1050)
    monkeypatch.setattr(engine.time, 'time', lambda: 1075)
    engine.api_step(project, shot, doc, 'test-key', now=1075)
    assert calls == [('POST', engine.api.DEFAULT_BASE_URL+engine.api.CREATE_PATH),
                     ('GET', engine.api.DEFAULT_BASE_URL+'/v2/requests/status/r1')]
    assert doc['shots']['S01']['status'] == 'generated'
    assert not engine.api_step(project, shot, doc, 'test-key', now=2000)


def test_429_honors_longer_retry_after(engine, project, monkeypatch):
    monkeypatch.setattr(engine.api, 'http_json', lambda *a, **kw: engine.api.HttpResult(429, {}, 'rate limit', 3600))
    doc = {'shots': {}}
    engine.api_step(project, project['shots'][0], doc, 'fake')
    assert doc['next_request_at'] == 4600
    assert not doc['shots']['S01'].get('video_id')


def test_ambiguous_post_never_repeated(engine, project, monkeypatch):
    def timeout(*a, **kw):
        raise engine.api.TransientError('timeout')
    monkeypatch.setattr(engine.api, 'http_json', timeout)
    doc = {'shots': {}}
    with pytest.raises(engine.Pause):
        engine.api_step(project, project['shots'][0], doc, 'fake')
    monkeypatch.setattr(engine.api, 'http_json', lambda *a, **kw: pytest.fail('duplicate POST'))
    with pytest.raises(engine.Pause):
        engine.api_step(project, project['shots'][0], doc, 'fake', now=2000)


@pytest.mark.parametrize('code,text', [(402, 'Insufficient Balance'), (429, 'insufficient balance'), (401, 'bad key'), (200, 'insufficient_user_quota')])
def test_balance_auth_pause(engine, project, monkeypatch, code, text):
    monkeypatch.setattr(engine.api, 'http_json', lambda *a, **kw: engine.api.HttpResult(code, {'error': text}, text))
    doc = {'shots': {}}
    with pytest.raises(engine.Pause):
        engine.api_step(project, project['shots'][0], doc, 'fake')
    assert doc['shots']['S01']['status'] == 'blocked'


def test_only_free_endpoint_and_no_key_redirect(engine):
    with pytest.raises(ValueError):
        engine.api.http_json('POST', engine.api.DEFAULT_BASE_URL+'/ltx-2-5-pro/v1/text-to-video', 'secret', {})
    with pytest.raises(ValueError):
        engine.api.http_json('GET', 'https://other.example/status/r1', 'secret')
    assert engine.api.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example') is None
