import importlib.util
import json
from pathlib import Path

spec=importlib.util.spec_from_file_location('gacy_relay',Path(__file__).with_name('relay.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def setup(tmp_path,status='awaiting_provider',allowed=True):
    (tmp_path/'REQUEST').write_text('identity\nunique-request\n')
    (tmp_path/'run-status.json').write_text(json.dumps({'status':status,'automatic_retry_allowed':allowed}))


def test_pending_has_bounded_relay(tmp_path,monkeypatch):
    setup(tmp_path)
    monkeypatch.setenv('GITHUB_RUN_ID','1')
    first=r.decide(tmp_path,'identity',42,max_runs=2)
    assert first['resume'] and first['dispatch_status']=='planned_not_yet_dispatched'
    assert r.decide(tmp_path,'identity',42,max_runs=2)['finished_runs']==1  # idempotent same run
    monkeypatch.setenv('GITHUB_RUN_ID','2')
    assert not r.decide(tmp_path,'identity',42,max_runs=2)['resume']


def test_moderation_never_relayed_even_wrong_exit_42(tmp_path):
    setup(tmp_path,'blocked_by_provider_moderation',False)
    assert not r.decide(tmp_path,'identity',42)['resume']


def test_manual_new_marker_starts_separate_finite_chain(tmp_path,monkeypatch):
    setup(tmp_path);monkeypatch.setenv('GITHUB_RUN_ID','1')
    first=r.decide(tmp_path,'identity',42)
    (tmp_path/'REQUEST').write_text('identity\nnew-user-request\n')
    monkeypatch.setenv('GITHUB_RUN_ID','2')
    second=r.decide(tmp_path,'identity',42)
    assert second['chain']!=first['chain'] and second['finished_runs']==1
