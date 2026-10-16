"""Offline scheduler tests, no provider access or paid task submission."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

PATH = Path(__file__).resolve().parents[1] / 'lee_hyung_ho1991/generate.py'
spec = importlib.util.spec_from_file_location('lee_generate', PATH)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

class RecoveryTests(unittest.TestCase):
    def test_resume_requires_same_payload_and_live_task(self):
        row = dict(status='queued', task_id='existing', request_hash='abc')
        self.assertEqual(g.resumable_task(row, 'abc'), 'existing')
        self.assertIsNone(g.resumable_task(row, 'changed'))
        self.assertIsNone(g.resumable_task(dict(row, status='failed'), 'abc'))

    def simulate(self, states, rows=None, budget=35, submit_errors=None, **policy):
        client=Mock(); doc={'shots':rows or {}}; clock=[0]; submitted=[]; polled=[]; live=set(); peak=[0]
        def submit(**payload):
            task=payload['sid'];submitted.append(task)
            if task in (submit_errors or {}):raise RuntimeError(submit_errors[task])
            live.add(task);peak[0]=max(peak[0],len(live));return {'id':task}
        def poll(id):
            polled.append(id)
            status=states[id]
            if status in ('SUCCESS','FAIL'):live.discard(id)
            return {'task_status':status,'error':{'code':'1234','message':'network error'},'video_result':[{'url':'https://test/'+id}]}
        def checkpoint(doc,label,sid=None,**values):
            values.pop('publish',None);values.pop('files',None)
            if sid:doc['shots'].setdefault(sid,{}).update(values)
        def collect(doc,shot,*args):
            doc['shots'][shot['id']].update(status='completed',sha256='verified')
        client.videos.generations.side_effect=submit;client.videos.retrieve_videos_result.side_effect=poll
        shots=[{'id':k} for k in states]
        with patch.object(g,'request_hash',return_value='hash'),patch.object(g,'full_payload',side_effect=lambda p,s:{'sid':s['id']}),patch.object(g,'reference_sha256',return_value=None),patch.object(g,'checkpoint',side_effect=checkpoint),patch.object(g,'collect_clip',side_effect=collect),patch.object(g.time,'monotonic',side_effect=lambda:clock[0]),patch.object(g.time,'sleep',side_effect=lambda sec:clock.__setitem__(0,clock[0]+sec)):
            missing=g.run_queue(client,{},shots,doc,Path('/tmp'),Path('/tmp'),False,budget=budget,**dict({'window':3,'cooldown_seconds':0},**policy))
        return doc,submitted,polled,peak[0],missing

    def test_slow_first_task_does_not_block_success_or_refill(self):
        doc,submitted,polled,peak,missing=self.simulate({'slow':'PROCESSING','fast':'SUCCESS','third':'SUCCESS','fourth':'SUCCESS'})
        self.assertEqual(missing,['slow'])
        self.assertEqual(doc['shots']['fourth']['status'],'completed')
        self.assertLessEqual(peak,3)
        self.assertIn('slow',polled)

    def test_synchronous_1305_does_not_starve_other_prompts(self):
        doc,submitted,_,_,missing=self.simulate({'bad':'SUCCESS','good':'SUCCESS'},budget=65,
                                               submit_errors={'bad':'429 1305 model busy'},window=1)
        self.assertEqual(missing,['bad'])
        self.assertEqual(doc['shots']['good']['status'],'completed')
        self.assertEqual(submitted[:2],['bad','good'])
        self.assertEqual(doc['submission_backoffs'][0]['shot'],'bad')

    def test_resume_does_not_submit_duplicate(self):
        row={'status':'queued','task_id':'existing','request_hash':'hash'}
        doc,submitted,_,_,missing=self.simulate({'existing':'SUCCESS'}, {'existing':row})
        self.assertEqual(submitted,[]);self.assertEqual(missing,[])

    def test_failed_task_retries_only_once_without_blocking_good_task(self):
        doc,submitted,_,_,missing=self.simulate({'bad':'FAIL','good':'SUCCESS'})
        self.assertEqual(submitted.count('bad'),2)
        self.assertEqual(submitted.count('good'),1)
        self.assertEqual(missing,['bad'])

    def test_successful_url_is_reused_without_new_generation(self):
        row={'status':'generated','request_hash':'hash','video_url':'https://test/saved'}
        _,submitted,polled,_,missing=self.simulate({'saved':'SUCCESS'},{'saved':row})
        self.assertEqual(submitted,[]);self.assertEqual(polled,[]);self.assertEqual(missing,[])

    def test_recovered_receipts_match_current_payload_and_do_not_replace_success(self):
        project=g.read_json(g.PLAN,{})
        doc={'shots':{}}
        g.merge_recovered_receipts(project,doc)
        self.assertEqual(set(doc['shots']),{'S04'})
        self.assertNotIn('S07',doc['shots'])  # retired payload must not override the replacement
        original=dict(doc['shots']['S04'])
        doc['shots']['S04']['marker']='keep'
        g.merge_recovered_receipts(project,doc)
        self.assertEqual(doc['shots']['S04']['marker'],'keep')
        bad={'source_branch':'other','shots':{'S04':dict(original,request_hash='changed')}}
        with patch.object(g,'read_json',return_value=bad):
            with self.assertRaises(ValueError):
                g.merge_recovered_receipts(project,{'shots':{}})

    def test_residual_policy_caps_retries_and_concurrency(self):
        _,submitted,_,peak,missing=self.simulate({'bad':'FAIL','good':'SUCCESS'},window=2,max_task_attempts=3)
        self.assertEqual(submitted.count('bad'),3)
        self.assertLessEqual(peak,2)
        self.assertEqual(missing,['bad'])

    def test_cooldown_prevents_immediate_resubmission(self):
        _,submitted,_,_,_=self.simulate({'bad':'FAIL'},cooldown_seconds=90)
        self.assertEqual(submitted.count('bad'),1)

    def test_invalid_queue_policy_is_rejected(self):
        for policy in ({'window':100},{'max_task_attempts':0},{'budget_minutes':999},{'window':True}):
            with self.assertRaises(ValueError):
                g.queue_policy(policy)
        self.assertEqual(g.queue_policy({'budget_minutes':210})['budget'],12600)

    def test_partial_restore_allows_missing_receipts_but_final_restore_does_not(self):
        import json, tempfile
        spec=importlib.util.spec_from_file_location('lee_fetch', PATH.with_name('fetch_sources.py'))
        fetch=importlib.util.module_from_spec(spec);spec.loader.exec_module(fetch)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'plan.json').write_text(json.dumps({'shots':[{'id':'S01','kind':'cogvideo'}]}))
            (root/'results.json').write_text('{"shots":{}}')
            argv=['fetch','--project',str(root/'plan.json'),'--results',str(root/'results.json'),'--dest',str(root/'sources')]
            with patch.dict('sys.modules',{'generate':g}), patch.object(g,'request_hash',return_value='hash'), patch('sys.argv',argv+['--allow-incomplete']):
                self.assertEqual(fetch.main(),0)
            with patch.dict('sys.modules',{'generate':g}), patch.object(g,'request_hash',return_value='hash'), patch('sys.argv',argv):
                with self.assertRaises(RuntimeError):
                    fetch.main()

    def test_tts_negative_rate_is_one_cli_argument(self):
        import tempfile, subprocess
        spec=importlib.util.spec_from_file_location('lee_tts',PATH.with_name('prepare_tts.py'))
        tts=importlib.util.module_from_spec(spec);spec.loader.exec_module(tts)
        with tempfile.TemporaryDirectory() as tmp:
            destination=Path(tmp)/'N01.mp3'
            def fake_run(command,**kwargs):
                self.assertIn('--rate=-12%',command)
                self.assertNotIn('--rate',command)
                destination.write_bytes(b'x'*2048)
                return subprocess.CompletedProcess(command,0,'','')
            with patch.object(tts.subprocess,'run',side_effect=fake_run):
                tts.synthesize('测试',0.88,destination)

    def test_quota_is_not_retried(self):
        self.assertFalse(g.retryable(RuntimeError('1113 余额不足')))
        self.assertTrue(g.retryable(RuntimeError('1234 网络错误')))
        self.assertTrue(g.retryable(RuntimeError('1302 concurrency limit')))

if __name__ == '__main__':
    unittest.main()
