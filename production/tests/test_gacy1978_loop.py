"""Offline regression tests for safe capacity continuation; no cloud POSTs."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import tempfile
import types
from contextlib import ExitStack

PROJECT = Path(__file__).resolve().parents[1] / 'gacy1978'
sys.path.insert(0, str(PROJECT))
# Unique sibling loading prevents other production projects' modules leaking into this test.
spec = importlib.util.spec_from_file_location('gacy1978_loop_control', PROJECT/'loop_control.py')
control = importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
spec = importlib.util.spec_from_file_location('gacy1978_loop_engine', PROJECT/'generate_cogvideox.py')
engine = importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.story=json.loads((PROJECT/'story.json').read_text())
        self.options={'auto_resume':True,'ref_image':False,'round':1,'round_minutes':25}
        self.results={'phase':'provider_capacity','shots':{}}
        self.modules=patch.dict(sys.modules,{'generate_cogvideox':engine});self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_pending_schedule_does_not_drop_refs_or_starve_other_shots(self):
        shots=[s for s in self.story['shots'] if s['kind']!='graphic']
        with patch.object(engine,'REF_IMAGE_OK',True):
            first=engine.schedule_shots(shots,self.story,{'shots':{}},1)
            second=engine.schedule_shots(shots,self.story,{'shots':{}},2)
            self.assertEqual(len(first),38)
            self.assertEqual({s['id'] for s in first},{s['id'] for s in shots})
            self.assertFalse(first[0].get('reference_image'))
            self.assertNotEqual(first[0]['id'],second[0]['id'])
            ref=next(s for s in shots if s.get('reference_image'))
            result={'shots':{ref['id']:{'status':'queued','task_id':'accepted-not-reposted',
                'request_hash':engine.request_hash(self.story,ref)}}}
            self.assertEqual(engine.schedule_shots(shots,self.story,result,3)[0]['id'],ref['id'])

    def test_linear_retry_cadence_and_no_extra_relay_sleep(self):
        self.assertEqual([engine.retry_delay(n) for n in range(1,21)], list(range(20,116,5)))
        hint=types.SimpleNamespace(response=types.SimpleNamespace(headers={'Retry-After':'40'}))
        self.assertEqual(engine.retry_delay(1,hint),40)
        self.assertNotIn('sleep 120',(PROJECT/'workflows/gacy1978-cogvideox-gen.yml').read_text())

    def test_capacity_dispatches_next_round(self):
        action,opts,_=control.decide(self.story,self.results,self.options,42)
        self.assertEqual(action,'resume');self.assertEqual(opts['round'],2)
        self.assertNotIn('force',opts)

    def test_auth_bug_moderation_do_not_relay(self):
        for rc in (1,43,44):self.assertEqual(control.decide(self.story,self.results,self.options,rc)[0],'stop')
        for msg in ('Error code: 401 invalid api key','Error code: 403 Insufficient quota','1301 敏感内容'):
            self.assertFalse(engine.retryable(RuntimeError(msg)))
        self.assertTrue(engine.retryable(RuntimeError('Error code: 429 1305 访问量过大')))
        self.assertFalse(engine.transient_fail('1301 敏感内容 请稍后重试'))

    def test_stop_partial_force_and_budget(self):
        self.assertEqual(control.decide(self.story,self.results,self.options,42,True)[0],'stop')
        for opt in ({'round':40},{'force':True},{'only':'S08'},{'auto_resume':False}):
            self.assertEqual(control.decide(self.story,self.results,dict(self.options,**opt),42)[0],'stop')

    def test_pending_task_can_continue_not_duplicate(self):
        self.results['phase']='generation_incomplete'
        self.assertEqual(control.decide(self.story,self.results,self.options,42)[0],'resume')
        source=(PROJECT/'generate_cogvideox.py').read_text()
        self.assertIn("task_id = old['task_id']",source)
        self.assertIn('poll window ended; keep accepted task',source)

    def test_all_38_matching_receipts_required_before_render(self):
        for shot in self.story['shots']:
            if shot['kind']=='graphic':continue
            self.results['shots'][shot['id']]={'status':'completed','video_url':'https://example.invalid/video',
                'sha256':'a'*64,'bytes':123,'media':{'decoded_ok':True},'request_hash':engine.request_hash(self.story,shot)}
        self.assertEqual(control.decide(self.story,self.results,self.options,0)[0],'render')
        self.results['shots']['S01']['request_hash']='stale'
        self.assertNotEqual(control.decide(self.story,self.results,self.options,0)[0],'render')

    def test_changed_plan_after_success_resumes_but_corrupt_media_stops(self):
        self.results['phase']='sources_ready'
        for shot in self.story['shots']:
            if shot['kind']=='graphic':continue
            self.results['shots'][shot['id']]={'status':'completed','video_url':'https://example.invalid/video',
                'request_hash':engine.request_hash(self.story,shot),'sha256':'a'*64,'bytes':123,'media':{'decoded_ok':True}}
        self.results['shots']['S20']['request_hash']='valid-old-source-but-new-review-prompt'
        self.assertEqual(control.decide(self.story,self.results,self.options,0)[0],'resume')
        self.results['shots']['S20']['media']['decoded_ok']=False
        self.assertEqual(control.decide(self.story,self.results,self.options,0)[0],'stop')

    def test_image_mode_is_reconstructed_and_restored(self):
        self.story['shots'][0]['reference_image']='https://example.invalid/current-film-frame.jpg'
        saved=engine.REF_IMAGE_OK
        try:
            engine.REF_IMAGE_OK=True
            for shot in self.story['shots']:
                if shot['kind']=='graphic':continue
                self.results['shots'][shot['id']]={'status':'completed','video_url':'https://example.invalid/video',
                    'sha256':'a'*64,'bytes':123,'media':{'decoded_ok':True},
                    'request_hash':engine.request_hash(self.story,shot)}
            engine.REF_IMAGE_OK=None
            self.assertEqual(control.decide(self.story,self.results,dict(self.options,ref_image=True),0)[0],'render')
            self.assertIsNone(engine.REF_IMAGE_OK)
            self.assertEqual(control.decide(self.story,self.results,dict(self.options,ref_image=False),0)[0],'stop')
            self.assertEqual(control.decide(self.story,self.results,dict(self.options,ref_image=None),0)[0],'render')
            self.results['shots']['S01']['request_hash']='stale'
            self.assertEqual(control.decide(self.story,self.results,dict(self.options,ref_image=True),0)[0],'stop')
        finally:
            engine.REF_IMAGE_OK=saved

    def test_existing_six_receipts_are_reused(self):
        receipts=json.loads((PROJECT/'results.json').read_text())
        done=0
        for shot in self.story['shots']:
            row=receipts.get('shots',{}).get(shot['id'],{})
            if row.get('status')=='completed':
                # A deliberately revised prompt invalidates the old receipt until
                # its retake completes; unchanged completed clips still resume.
                done += bool(engine.usable_receipt(row,engine.request_hash(self.story,shot)))
        self.assertGreaterEqual(done,6)

    def exercise_offline_provider(self, pending):
        clock=[0.0];posts=[];polls=[]
        def create(**kwargs):
            posts.append(kwargs)
            raise RuntimeError('Error code: 429 1305 访问量过大')
        def retrieve(**kwargs):
            polls.append(kwargs)
            return {'task_status':'PROCESSING'}
        client=types.SimpleNamespace(videos=types.SimpleNamespace(generations=create,retrieve_videos_result=retrieve))
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root=Path(tmp);plan=root/'story.json';res=root/'results.json'
            plan.write_text(json.dumps(self.story))
            shot=next(s for s in self.story['shots'] if s['id']=='S08')
            row={'id':'S08','status':'queued','task_id':'accepted-task',
                 'request_hash':engine.request_hash(self.story,shot)} if pending else {}
            res.write_text(json.dumps({'shots':{'S08':row}}))
            for name,value in [('ROOT',root),('HERE',root),('PLAN',plan),('RESULTS',res),
                               ('REF_IMAGE_MODE',False),('REF_IMAGE_OK',False)]:
                stack.enter_context(patch.object(engine,name,value))
            stack.enter_context(patch.object(engine,'ensure_tools',lambda:None))
            stack.enter_context(patch.object(engine.time,'monotonic',lambda:clock[0]))
            stack.enter_context(patch.object(engine.time,'sleep',lambda seconds:clock.__setitem__(0,clock[0]+seconds)))
            stack.enter_context(patch.dict('os.environ',{'ZHIPUAI_API_KEY':'offline-test-placeholder'}))
            stack.enter_context(patch.dict(sys.modules,{'zhipuai':types.SimpleNamespace(ZhipuAI=lambda **kw:client)}))
            stack.enter_context(patch.object(sys,'argv',['generator','--payload',json.dumps({'only':'S08','ref_image':False,'round_minutes':1})]))
            rc=engine.main();doc=json.loads(res.read_text())
        return rc,doc,posts,polls

    def test_capacity_writes_real_retry_receipt_and_yields_42(self):
        rc,doc,posts,polls=self.exercise_offline_provider(False)
        self.assertEqual(rc,42);self.assertEqual(doc['phase'],'provider_capacity')
        self.assertEqual(doc['shots']['S08']['status'],'retry_wait')
        self.assertIn('1305',doc['shots']['S08']['error'])
        self.assertTrue(posts);self.assertFalse(polls)

    def test_resumed_accepted_task_never_posts_again(self):
        rc,doc,posts,polls=self.exercise_offline_provider(True)
        self.assertEqual(rc,42);self.assertFalse(posts);self.assertTrue(polls)
        self.assertEqual(doc['shots']['S08']['task_id'],'accepted-task')
        self.assertEqual(doc['shots']['S08']['status'],'queued')

    def test_official_dispatch_and_serial_queue(self):
        text=(PROJECT/'workflows/gacy1978-cogvideox-gen.yml').read_text()
        self.assertIn('actions: write',text);self.assertIn('cancel-in-progress: false',text)
        self.assertIn('gh workflow run gacy1978-cogvideox-gen.yml --ref arena/3c0c229a-desktop-tutorial',text)
        self.assertIn('gh workflow run gacy1978-render.yml',text)
        self.assertNotIn('production/gacy/REQUEST',text)


if __name__=='__main__':unittest.main()
