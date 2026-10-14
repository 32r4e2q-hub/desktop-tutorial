"""Rate policy, idempotency and hard-stop tests; never calls a live service."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import pytest

HERE=Path(__file__).resolve().parents[1]/'kimdaedoo'

@pytest.fixture
def engine(monkeypatch):
    snapshot=list(sys.path)
    old=sys.modules.pop('generate',None)
    try:
        spec=importlib.util.spec_from_file_location('kim_loop',HERE/'loop.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    finally:
        sys.path[:]=snapshot
        sys.modules.pop('generate',None)
        if old is not None:sys.modules['generate']=old
    saved=[]
    monkeypatch.setattr(m,'save',lambda doc,publish=False:saved.append(copy.deepcopy(doc)))
    monkeypatch.setattr(m.time,'time',lambda:1000)
    m.saved=saved
    return m

@pytest.fixture
def project():
    return json.loads((HERE/'story.json').read_text())

@pytest.mark.parametrize('code,text,creating,want',[
 (429,'rate limit for free users',True,'rate_limit'),
 (503,'video queue is full',True,'queue_full'),
 (503,'model_not_found no available channel',True,'model_unavailable'),
 (403,'insufficient_user_quota',True,'payment_or_quota'),
 (401,'invalid key',True,'authentication_or_access'),
 (402,'payment required',True,'payment_or_quota'),
 (500,'internal error',True,'submission_ambiguous'),
 (500,'internal error',False,'poll_transient'),
 (404,'not found',False,'poll_endpoint_missing'),
 (400,'unsupported seconds',True,'request_rejected'),
])
def test_response_classification(engine,code,text,creating,want):
    assert engine.classify(code,text,creating)==want


def test_cooldown_growth_cap_and_retry_after(engine):
    assert [engine.cooldown('queue_full',i) for i in range(1,6)]==[120,240,480,900,900]
    assert engine.cooldown('rate_limit',1,1800)==1800
    assert engine.cooldown('poll_transient',1)>=75


def test_no_calls_during_persisted_cooldown(engine,project,monkeypatch):
    monkeypatch.setattr(engine.api,'http_json',lambda *a,**kw:pytest.fail('Rate gate bypassed'))
    assert engine.api_step(project,project['shots'][0],{'shots':{},'next_request_at':1075},'fake',now=1000) is False


def test_queue_rejection_waits_without_task_creation(engine,project,monkeypatch):
    response=engine.api.HttpResult(503,{'message':'video queue is full'},'video queue is full',500)
    monkeypatch.setattr(engine.api,'http_json',lambda *a,**kw:response)
    doc={'shots':{}}
    engine.api_step(project,project['shots'][0],doc,'fake')
    row=doc['shots']['S01']
    assert row['status']=='retry_wait'
    assert not row.get('video_id')
    assert doc['next_request_at']==1500
    assert engine.saved[0]['shots']['S01']['status']=='submitting'


def test_accept_poll_and_completion_never_repost(engine,project,monkeypatch):
    calls=[]
    responses=iter([
      engine.api.HttpResult(200,{'data':{'video_id':'v','task_id':'t'}},'{}'),
      engine.api.HttpResult(200,{'status':'processing'},'{}'),
      engine.api.HttpResult(200,{'data':{'status':'completed','url':'https://example.com/video.mp4'}},'{}'),
    ])
    def http(method,*args,**kw):
        calls.append(method);return next(responses)
    monkeypatch.setattr(engine.api,'http_json',http)
    doc={'shots':{}}
    shot=project['shots'][0]
    for t in (1000,1075,1150):
        monkeypatch.setattr(engine.time,'time',lambda:t)
        engine.api_step(project,shot,doc,'fake',now=t)
    assert calls==['POST','GET','GET']
    assert doc['shots']['S01']['video_id']=='v'
    assert doc['shots']['S01']['status']=='generated'
    assert doc['shots']['S01']['accepted_count']==1
    assert not engine.api_step(project,shot,doc,'fake',now=1300)


def test_lost_post_response_stops_and_never_repeats(engine,project,monkeypatch):
    calls=[]
    def broken(*a,**kw):
        calls.append(1);raise engine.api.TransientError('socket timeout')
    monkeypatch.setattr(engine.api,'http_json',broken)
    doc={'shots':{}};shot=project['shots'][0]
    with pytest.raises(engine.Pause,match='response lost'):
        engine.api_step(project,shot,doc,'fake')
    with pytest.raises(engine.Pause,match='Reconcile'):
        engine.api_step(project,shot,doc,'fake',now=1200)
    assert len(calls)==1
    assert doc['shots']['S01']['status']=='submission_ambiguous'

@pytest.mark.parametrize('code,text',[(403,'insufficient_user_quota'),(401,'invalid key'),(400,'bad prompt')])
def test_fatal_response_does_not_get_retried(engine,project,monkeypatch,code,text):
    calls=[]
    def http(*a,**kw):
        calls.append(1);return engine.api.HttpResult(code,{'message':text},text)
    monkeypatch.setattr(engine.api,'http_json',http)
    doc={'shots':{}};shot=project['shots'][0]
    with pytest.raises(engine.Pause):engine.api_step(project,shot,doc,'fake')
    with pytest.raises(engine.Pause):engine.api_step(project,shot,doc,'fake',now=1200)
    assert len(calls)==1


def test_wrong_hash_stops_before_network(engine,project,monkeypatch):
    monkeypatch.setattr(engine.api,'http_json',lambda *a,**kw:pytest.fail('Should not call API'))
    doc={'shots':{'S01':{'status':'queued','request_hash':'changed','video_id':'old'}}}
    with pytest.raises(engine.Pause,match='Prompt changed'):
        engine.api_step(project,project['shots'][0],doc,'fake')


def test_only_explicit_terminal_failure_allows_replacement(engine,project,monkeypatch):
    shot=project['shots'][0]
    doc={'shots':{'S01':{'status':'queued','request_hash':engine.request_hash(project,shot),'video_id':'old','task_id':'old'}}}
    monkeypatch.setattr(engine.api,'http_json',lambda *a,**kw:engine.api.HttpResult(200,{'status':'failed'},'{}'))
    engine.api_step(project,shot,doc,'fake')
    row=doc['shots']['S01']
    assert row['status']=='retry_wait' and not row.get('video_id')
    assert row['failed_tasks'][0]['video_id']=='old'
    assert doc['next_request_at']==1900


def test_checkpoint_failure_blocks_post(engine,project,monkeypatch):
    monkeypatch.setattr(engine.api,'http_json',lambda *a,**kw:pytest.fail('Must save before POST'))
    def fail(*a,**kw):raise engine.Pause('Remote checkpoint unavailable')
    monkeypatch.setattr(engine,'save',fail)
    with pytest.raises(engine.Pause):engine.api_step(project,project['shots'][0],{'shots':{}},'fake',True)


def test_workflow_uses_dispatch_not_a_bot_push_for_rollover():
    source=(HERE.parents[1]/'.github/workflows/kimdaedoo-loop.yml').read_text()
    assert 'workflow_dispatch:' in source
    assert 'actions: write' in source
    assert '/dispatches' in source
    assert "steps.queue.outputs.continue == 'true'" in source
    assert 'concurrency:' in source
    assert 'group: kimdaedoo-agnes-api' in source

def test_explicit_money_error_not_confused_with_429(engine):
    assert engine.classify(429,'insufficient_user_quota',True)=='payment_or_quota'


def test_budget_rollover_preserves_cooldown_and_requests_continuation(engine,project,monkeypatch,tmp_path):
    state=tmp_path/'results.json'
    state.write_text(json.dumps({'model':engine.MODEL,'shots':{},'next_request_at':2000}))
    monkeypatch.setattr(engine,'STATE',state)
    monkeypatch.setenv('AGNES_API_KEY','fake')
    monkeypatch.setattr(engine,'control',lambda publish=False:{'enabled':True,'free_flash_loop_authorized':True,'model':engine.MODEL})
    monkeypatch.setattr(sys,'argv',['loop','--budget-seconds','0'])
    outputs=[]
    monkeypatch.setattr(engine,'output',lambda k,v:outputs.append((k,v)))
    assert engine.main()==0
    assert ('continue','true') in outputs
    assert engine.saved[-1]['next_request_at']==2000
    assert engine.saved[-1]['loop_status']=='rollover_required'


def test_all_complete_stops_continuation(engine,project,monkeypatch,tmp_path):
    state=tmp_path/'results.json'
    rows={s['id']:{'status':'completed','request_hash':engine.request_hash(project,s)} for s in project['shots'] if s['kind']=='agnes'}
    state.write_text(json.dumps({'model':engine.MODEL,'shots':rows}))
    monkeypatch.setattr(engine,'STATE',state)
    monkeypatch.setenv('AGNES_API_KEY','fake')
    monkeypatch.setattr(engine,'control',lambda publish=False:{'enabled':True,'free_flash_loop_authorized':True,'model':engine.MODEL})
    monkeypatch.setattr(sys,'argv',['loop','--budget-seconds','10'])
    outputs=[]
    monkeypatch.setattr(engine,'output',lambda k,v:outputs.append((k,v)))
    assert engine.main()==0
    assert ('continue','true') not in outputs
    assert ('all_complete','true') in outputs
    assert engine.saved[-1]['completed_count']==38
