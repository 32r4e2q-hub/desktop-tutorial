"""Offline integrity tests. Test images are fixtures, not verified real identity evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from PIL import Image

HERE=Path(__file__).resolve().parent

def load(name):
    spec=importlib.util.spec_from_file_location('gacy_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

gate=load('identity_gate')
probe=load('identity_probe')
engine=load('pipeline')


def test_empty_review_never_passes(tmp_path):
    result=gate.evaluate(tmp_path,{}, {})
    assert not result['publishable'] and result['status']=='NEEDS_IDENTITY_REVIEW'


def test_identity_probe_forwards_reference_to_sdk(tmp_path,monkeypatch):
    monkeypatch.setattr(engine,'DIAGNOSTICS',tmp_path/'diag.json')
    client=Mock();client.videos.generations.return_value={'id':'reference-task'}
    monkeypatch.setattr(engine,'make_video_client',lambda:client)
    payload={'model':'cogvideox-flash','quality':'speed','prompt':'fictional adult turns his head','image_url':'data:image/jpeg;base64,TEST'}
    assert probe.submit(engine,payload)['id']=='reference-task'
    client.videos.generations.assert_called_once_with(**payload)


def test_identity_probe_does_not_replace_capacity_error_with_text(tmp_path,monkeypatch):
    class Error(Exception):
        response=Mock(status_code=429)
    Error.response.json.return_value={'error':{'code':'1305'}}
    client=Mock();client.videos.generations.side_effect=Error()
    monkeypatch.setattr(engine,'DIAGNOSTICS',tmp_path/'diag.json')
    monkeypatch.setattr(engine,'make_video_client',lambda:client)
    monkeypatch.setattr(probe.time,'sleep',lambda _:None)
    payload={'model':'cogvideox-flash','prompt':'safe adult portrait','quality':'speed','image_url':'TEST'}
    with pytest.raises(engine.ProviderError):probe.submit(engine,payload)
    assert client.videos.generations.call_count==2
    assert all(c.kwargs['image_url']=='TEST' for c in client.videos.generations.call_args_list)


def test_moderation_is_terminal_for_identity_probe(tmp_path,monkeypatch):
    class Error(Exception):
        response=Mock(status_code=400)
    Error.response.json.return_value={'error':{'code':'1301'}}
    client=Mock();client.videos.generations.side_effect=Error()
    monkeypatch.setattr(engine,'DIAGNOSTICS',tmp_path/'diag.json')
    monkeypatch.setattr(engine,'make_video_client',lambda:client)
    with pytest.raises(engine.ProviderError):probe.submit(engine,{'model':'cogvideox-flash','image_url':'TEST'})
    assert client.videos.generations.call_count==1


def test_probe_retains_task_id_after_poll_timeout(tmp_path,monkeypatch):
    (tmp_path/'references').mkdir();Image.new('RGB',(320,180)).save(tmp_path/'references/盖西.jpg')
    monkeypatch.setattr(engine,'HERE',tmp_path)
    monkeypatch.setattr(engine,'WORK',tmp_path/'media')
    monkeypatch.setattr(probe,'PROMPTS',probe.PROMPTS[:1])
    submit=Mock(return_value={'id':'accepted-reference-task'})
    monkeypatch.setattr(probe,'submit',submit)
    lookup=Mock(side_effect=RuntimeError('poll timeout'))
    monkeypatch.setattr(engine,'await_video',lookup)
    with pytest.raises(RuntimeError,match='poll timeout'):probe.run_probe(engine)
    with pytest.raises(RuntimeError,match='poll timeout'):probe.run_probe(engine)
    assert submit.call_count==1
    record=json.loads((tmp_path/'identity-probe/receipts.json').read_text())
    assert record['shots']['C1-A']['task_id']=='accepted-reference-task'
    assert not record['same_actor_verified']


def accepted_fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(gate,'APPEARANCES',{'C1':{'name':'test actor','reference':'actor.jpg','shots':['S01','S02']},'C1-makeup':{'name':'test costume','reference':'costume.jpg','shots':['S03','S04']}})
    for file,color in [('actor.jpg','red'),('costume.jpg','green')]:Image.new('RGB',(160,160),color).save(tmp_path/file)
    receipts={'shots':{}}
    review={'appearances':{},'makeup_identity_link':{'main_reference_sha256':gate.digest(tmp_path/'actor.jpg'),'makeup_reference_sha256':gate.digest(tmp_path/'costume.jpg'),'decision':'same_underlying_character','reviewer':'fixture reviewer'}}
    for cid,appearance in gate.APPEARANCES.items():
        review['appearances'][cid]={}
        for sid in appearance['shots']:
            sha=hashlib.sha256(sid.encode()).hexdigest();receipts['shots'][sid]={'status':'downloaded','sha256':sha}
            evidence=[]
            for n in range(3):
                name=f'{sid}-{n}.jpg';Image.new('RGB',(160,160),(20+n*70,50,70)).save(tmp_path/name)
                evidence.append({'path':name,'sha256':gate.digest(tmp_path/name)})
            review['appearances'][cid][sid]={'source_sha256':sha,'reference_sha256':gate.digest(tmp_path/appearance['reference']),'decision':'same_identity','face_visibility':'clear','reviewer':'fixture reviewer','reviewer_type':'agent_visual_review','evidence':evidence}
    return receipts,review


def test_changed_clip_invalidates_identity_review(tmp_path,monkeypatch):
    receipts,review=accepted_fixture(tmp_path,monkeypatch)
    assert gate.evaluate(tmp_path,receipts,review)['publishable']
    receipts['shots']['S01']['sha256']='new-source'
    assert not gate.evaluate(tmp_path,receipts,review)['publishable']


def test_duplicate_source_does_not_prove_cross_shot_identity(tmp_path,monkeypatch):
    receipts,review=accepted_fixture(tmp_path,monkeypatch)
    sha=receipts['shots']['S01']['sha256'];receipts['shots']['S02']['sha256']=sha
    review['appearances']['C1']['S02']['source_sha256']=sha
    result=gate.evaluate(tmp_path,receipts,review)
    assert not result['publishable']
    assert any('two distinct' in x for x in result['issues'])
