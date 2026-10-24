"""Offline tests: no provider calls, no key needed, no generated media committed."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('gacy_pipeline', HERE/'pipeline.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def test_plan_integrity():
    spec = importlib.util.spec_from_file_location('gacy_validate', HERE/'validate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    warnings = module.validate(p.PLAN)
    assert len(warnings) == 1


def test_only_free_zhipu_models():
    source = (HERE/'pipeline.py').read_text()
    assert "'model':'cogvideox-flash'" in source
    assert "'model':'cogview-3-flash'" in source
    assert 'cogvideox-3' not in source
    assert 'zoompan' not in source
    assert 'tpad' not in source


def test_every_generated_shot_has_reference():
    assert set(p.REF_MAP) == set(range(1,29))
    assert set(p.REF_MAP.values()) <= set(p.REFERENCE_SCENES) | set(p.PLAN['characters'])


def test_missing_key_fails_without_network(monkeypatch):
    monkeypatch.delenv('ZHIPUAI_API_KEY', raising=False)
    request = Mock()
    monkeypatch.setattr(p.requests,'post',request)
    with pytest.raises(RuntimeError,match='not injected'):
        p.post('/images/generations',{})
    request.assert_not_called()


def test_permanent_error_is_not_retried_or_secret_logged(monkeypatch):
    monkeypatch.setenv('ZHIPUAI_API_KEY','TEST_SECRET_DO_NOT_LOG')
    response=Mock(status_code=400,ok=False)
    response.json.return_value={'error':{'code':'1210','message':'opaque'}}
    request=Mock(return_value=response)
    monkeypatch.setattr(p.requests,'post',request)
    with pytest.raises(RuntimeError) as exc:
        p.post('/videos/generations',{})
    assert 'TEST_SECRET' not in str(exc.value)
    assert request.call_count == 1


def test_rate_limit_has_bounded_retry(monkeypatch):
    monkeypatch.setenv('ZHIPUAI_API_KEY','TEST')
    response=Mock(status_code=429,ok=False)
    response.json.return_value={'error':{'code':'1305'}}
    request=Mock(return_value=response)
    monkeypatch.setattr(p.requests,'post',request)
    monkeypatch.setattr(p.time,'sleep',lambda _:None)
    with pytest.raises(RuntimeError,match='budget exhausted'):
        p.post('/videos/generations',{})
    assert request.call_count==8


def test_subtitle_highlight_and_timestamp(tmp_path,monkeypatch):
    monkeypatch.setattr(p,'OUT',tmp_path)
    p.write_subtitles([{'start':1.25,'end':2.75,'text':'请记住他们，而不是他。'}])
    text=(tmp_path/'captions.ass').read_text()
    assert '0:00:01.25,0:00:02.75' in text
    assert r'\c&H0057C7F2&\fs60' in text
    assert 'MarginV' in text


def test_receipt_save_is_atomic(tmp_path):
    path=tmp_path/'nested/state.json'
    p.save(path,{'status':'submitted','task_id':'example'})
    assert json.loads(path.read_text())['status']=='submitted'
    assert not path.with_suffix('.json.tmp').exists()


def test_does_not_skip_references_in_all_stage():
    source=(HERE/'pipeline.py').read_text()
    assert source.index("if args.stage in ('references','all')") < source.index("if args.stage in ('video','all')")
    assert 'requires_visual_review' in source
