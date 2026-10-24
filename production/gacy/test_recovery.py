import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('gacy_recovery',HERE/'recover_tasks.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def setup_engine(tmp_path):
    from test_pipeline import p
    record=tmp_path/'identity-probe/receipts.json';record.parent.mkdir()
    record.write_text(json.dumps({'shots':{'C1-A':{'task_id':'existing-accepted-task','status':'submitted'}}}))
    client=Mock()
    engine=SimpleNamespace(HERE=tmp_path,WORK=tmp_path/'work',ROOT=tmp_path,
        make_video_client=lambda:client,save=p.save,download=Mock(),probe=Mock(),seconds=Mock(),run=Mock())
    return engine,client


def test_recovery_queries_existing_ids_and_never_submits(tmp_path):
    engine,client=setup_engine(tmp_path)
    client.videos.retrieve_videos_result.return_value={'task_status':'PROCESSING'}
    report=r.recover(engine)
    assert report['new_generation_requests']==0
    assert report['tasks'][1]['awaiting_existing_task']
    client.videos.generations.assert_not_called()
    client.videos.retrieve_videos_result.assert_any_call(id='existing-accepted-task')


def test_recovery_downloads_and_probes_completed_clip(tmp_path):
    engine,client=setup_engine(tmp_path)
    client.videos.retrieve_videos_result.return_value={'task_status':'SUCCESS','video_result':[{'url':'https://example.invalid/clip.mp4'}]}
    def download(url,path):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'unit-test-only')
    engine.download=download
    engine.probe.return_value={'streams':[{'codec_type':'video','width':1792,'height':1024}]}
    engine.seconds.return_value=5.1
    report=r.recover(engine)
    assert report['verified_downloads']==2
    assert (tmp_path/'交付/盖西_同脸实验_C1-A_原始片段.mp4').exists()
    receipt=json.loads((tmp_path/'identity-probe/receipts.json').read_text())
    assert receipt['shots']['C1-A']['status']=='downloaded'
    client.videos.generations.assert_not_called()


def test_recovery_does_not_requery_moderated_task(tmp_path):
    engine,client=setup_engine(tmp_path)
    record=tmp_path/'identity-probe/receipts.json'
    record.write_text(json.dumps({'shots':{'C1-A':{'task_id':'blocked-task','status':'blocked_by_provider_moderation'}}}))
    client.videos.retrieve_videos_result.return_value={'task_status':'PROCESSING'}
    report=r.recover(engine)
    assert len(report['tasks'])==1  # control only
    client.videos.generations.assert_not_called()
