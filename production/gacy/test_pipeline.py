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


@pytest.fixture(autouse=True)
def isolate_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'DIAGNOSTICS', tmp_path/'api-diagnostics.json')
    monkeypatch.setattr(p, 'STATE', tmp_path/'receipts.json')


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


def test_dark_reference_has_correct_frame_and_is_nearly_black(tmp_path):
    from PIL import Image
    import numpy as np
    target=tmp_path/'dark.jpg'
    p.dark_reference(target)
    with Image.open(target) as im:
        assert im.size==(1344,756)
        assert np.asarray(im).mean()<10


def test_music_relative_level_and_last_second_silence(tmp_path,monkeypatch):
    import numpy as np
    monkeypatch.setattr(p,'OUT',tmp_path)
    monkeypatch.setattr(p,'SR',1000)
    p.score(np.ones(180000,dtype=np.float32)*.1)
    report=json.loads((tmp_path/'mix-report.json').read_text())
    assert abs(report['music_relative_rms_db']+18)<.05
    assert report['last_second_silent']
    assert report['peak']<1


def test_headline_ass_uses_single_backslashes(tmp_path,monkeypatch):
    monkeypatch.setattr(p,'OUT',tmp_path)
    p.write_subtitles([])
    text=(tmp_path/'captions.ass').read_text()
    assert r'\an8\pos(960,80)' in text
    assert r'\\an8' not in text


def test_reference_capacity_falls_back_to_same_prompt_free_video(monkeypatch):
    calls=[]
    def request(resource,payload,attempts=8):
        calls.append((resource,payload.copy(),attempts))
        if 'image_url' in payload:
            raise p.ProviderError(resource,429,'1305',exhausted=True)
        return {'id':'new-video-task'}
    monkeypatch.setattr(p,'post',request)
    state={}
    original={'model':'cogvideox-flash','prompt':'unchanged full scene/role prompt','quality':'speed','image_url':'data:image/jpeg;base64,TEST'}
    result,actual=p.submit_video(original,state)
    assert result['id']=='new-video-task'
    assert actual=={k:v for k,v in original.items() if k!='image_url'}
    assert state['video_policy']['effective_input']=='text'
    assert len(calls)==2 and calls[0][2]==2
    assert original['image_url']  # no mutation of original payload


@pytest.mark.parametrize('status,code',[(401,'1000'),(400,'1210'),(400,'1301'),(400,'1113')])
def test_auth_schema_moderation_balance_do_not_fallback(monkeypatch,status,code):
    request=Mock(side_effect=p.ProviderError('/videos/generations',status,code))
    monkeypatch.setattr(p,'post',request)
    with pytest.raises(p.ProviderError):
        p.submit_video({'model':'cogvideox-flash','image_url':'TEST'}, {})
    assert request.call_count==1


def test_transport_unknown_does_not_duplicate_post(monkeypatch):
    monkeypatch.setenv('ZHIPUAI_API_KEY','SECRET_NOT_FOR_REPORTS')
    request=Mock(side_effect=p.requests.Timeout('opaque error'))
    monkeypatch.setattr(p.requests,'post',request)
    with pytest.raises(RuntimeError,match='acceptance unknown'):
        p.post('/videos/generations',{'model':'cogvideox-flash','image_url':'PRIVATE_IMAGE_DATA'})
    assert request.call_count==1
    report=p.DIAGNOSTICS.read_text()
    assert 'SECRET_NOT_FOR_REPORTS' not in report
    assert 'PRIVATE_IMAGE_DATA' not in report
    assert 'transport_outcome_unknown' in report


def test_retry_failure_preserves_last_code(monkeypatch):
    monkeypatch.setenv('ZHIPUAI_API_KEY','TEST')
    response=Mock(status_code=429,ok=False)
    response.json.return_value={'error':{'code':'1305'}}
    monkeypatch.setattr(p.requests,'post',Mock(return_value=response))
    monkeypatch.setattr(p.time,'sleep',lambda _:None)
    with pytest.raises(p.ProviderError,match='HTTP 429, code=1305'):
        p.post('/videos/generations',{'model':'cogvideox-flash'},attempts=2)
    report=json.loads(p.DIAGNOSTICS.read_text())
    assert len(report)==2 and report[-1]['error_code']=='1305'
