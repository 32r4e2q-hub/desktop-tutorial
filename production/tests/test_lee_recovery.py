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

    def simulate(self, states, rows=None, budget=35):
        client=Mock(); doc={'shots':rows or {}}; clock=[0]; submitted=[]; polled=[]; live=set(); peak=[0]
        def submit(**payload):
            task=payload['sid'];submitted.append(task);live.add(task);peak[0]=max(peak[0],len(live));return {'id':task}
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
            missing=g.run_queue(client,{},shots,doc,Path('/tmp'),Path('/tmp'),False,window=3,budget=budget)
        return doc,submitted,polled,peak[0],missing

    def test_slow_first_task_does_not_block_success_or_refill(self):
        doc,submitted,polled,peak,missing=self.simulate({'slow':'PROCESSING','fast':'SUCCESS','third':'SUCCESS','fourth':'SUCCESS'})
        self.assertEqual(missing,['slow'])
        self.assertEqual(doc['shots']['fourth']['status'],'completed')
        self.assertLessEqual(peak,3)
        self.assertIn('slow',polled)

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
        self.assertEqual(set(doc['shots']),{'S04','S07'})
        original=dict(doc['shots']['S04'])
        doc['shots']['S04']['marker']='keep'
        g.merge_recovered_receipts(project,doc)
        self.assertEqual(doc['shots']['S04']['marker'],'keep')
        bad={'source_branch':'other','shots':{'S04':dict(original,request_hash='changed')}}
        with patch.object(g,'read_json',return_value=bad):
            with self.assertRaises(ValueError):
                g.merge_recovered_receipts(project,{'shots':{}})

    def test_quota_is_not_retried(self):
        self.assertFalse(g.retryable(RuntimeError('1113 余额不足')))
        self.assertTrue(g.retryable(RuntimeError('1234 网络错误')))
        self.assertTrue(g.retryable(RuntimeError('1302 concurrency limit')))

if __name__ == '__main__':
    unittest.main()
