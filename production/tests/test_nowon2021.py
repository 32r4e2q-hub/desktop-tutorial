import importlib.util
import json
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'nowon2021'
def load(name):
    import sys
    if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
    spec=importlib.util.spec_from_file_location(name, ROOT / f'{name}.py')
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

class TestNowonPlan(unittest.TestCase):
    def test_plan_time_and_prompts(self):
        doc=load('build_story').build()
        self.assertEqual(len(doc['shots']),30)
        t=0
        for shot in doc['shots']:
            self.assertEqual(shot['start'],t)
            self.assertIn(shot['duration'],(5,6,7))
            t=shot['end']
            self.assertTrue(shot['prompt'].startswith('【STYLE】'+doc['style']))
            self.assertTrue(shot['prompt'].endswith('【NEGATIVE】'+doc['negative']))
            for role in shot['characters']:
                self.assertIn(doc['anchors'][role],shot['prompt'])
            for n,ref in enumerate(shot['reference_images'],1):
                self.assertIn(f'<Picture {n}>={ref}',shot['prompt'])
            self.assertLessEqual(len(shot['reference_images']),5)
        self.assertEqual(t,180)
        self.assertEqual(doc,json.loads((ROOT/'story.json').read_text(encoding='utf-8')))
    def test_missing_and_unapproved_refs_fail_closed(self):
        preflight=load('preflight')
        with TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'reference').mkdir()
            (root/'story.json').write_text((ROOT/'story.json').read_text(encoding='utf-8'),encoding='utf-8')
            (root/'reference'/'C01.png').write_bytes(b"\x89PNG\r\n\x1a\nnot-a-real-image")
            with patch.object(preflight,'ROOT',root):
                errors=preflight.check()
            self.assertTrue(any('P01：参考图缺失' in e for e in errors))
            self.assertTrue(any('C01：尚未完成定稿' in e for e in errors))

    def test_rate_gate_and_reference_payload(self):
        throttle=load('throttle')
        now=[0.0]
        def clock(): return now[0]
        def sleep(n): now[0] += n
        gate=throttle.RequestGate(12.1,allow_fast_plan=True,clock=clock,sleep=sleep)
        times=[]
        for _ in range(6):
            gate.acquire_creation(1000)
            times.append(clock())
        self.assertGreaterEqual(times[-1]-times[0],60)
        with self.assertRaises(ValueError): throttle.RequestGate(12.1)
        gen=load('generate_clips')
        shot=json.loads((ROOT/'story.json').read_text(encoding='utf-8'))['shots'][0]
        payload=gen.payload(shot,'a'*40)
        self.assertEqual(payload['mode'],'reference')
        self.assertEqual(payload['size'],'720P')
        self.assertEqual(payload['seconds'],'6')  # guard against short provider source; 5s edit
        self.assertEqual(payload['model'],'agnes-video-2.5-flash')
        self.assertEqual(len(payload['images']),4)
        self.assertEqual(set(payload),gen.ALLOWED)
        self.assertTrue(payload['prompt'].startswith('【STYLE】'))
        self.assertIn('<Picture 1>=P01',payload['prompt'])
        self.assertNotIn('negative_prompt',payload)

    def test_receipts_fail_closed_on_ambiguous_create(self):
        gen=load('generate_clips')
        shot=json.loads((ROOT/'story.json').read_text(encoding='utf-8'))['shots'][0]
        for status in ('creating','create_unknown','failed'):
            doc={'shots': {shot['id']:{'id':shot['id'],'status':status}}}
            r=gen.Receipts(doc,publish=False)
            producer=gen.Producer({'shots':[shot]},[shot],'test-key','https://unused.invalid',99999999,r,'a'*40,set())
            try:
                with self.assertRaises(RuntimeError): producer.plan()
            finally: producer.downloads.shutdown(wait=False)
        with TemporaryDirectory() as temp:
            corrupt=Path(temp)/'results.json'
            corrupt.write_text('{invalid',encoding='utf-8')
            with patch.object(gen,'RESULTS',corrupt):
                with self.assertRaises(RuntimeError): gen.read_results()

    def test_render_fails_closed_until_human_review_and_speech(self):
        render=load('render')
        doc=json.loads((ROOT/'story.json').read_text(encoding='utf-8'))
        with self.assertRaises(RuntimeError):
            render.verify_inputs(doc,{'phase':'clips_pending_resume'}, {'completed':0,'clips':[]})
        with self.assertRaises(RuntimeError):
            render.verify_inputs(doc,{'phase':'clips_ready','shots':{}}, {'completed':30,'clips':[{'id':s['id']} for s in doc['shots']]})

    def test_shot_locked_caption_windows_and_final_silence(self):
        render=load('render')
        doc=json.loads((ROOT/'story.json').read_text(encoding='utf-8'))
        clips={s['id']:{'file':'not-generated.mp3'} for s in doc['shots']}
        with patch.object(render,'duration_audio',return_value=4.0), patch.object(render,'voice_activity',return_value=(0.2,3.7)), patch.object(render,'speech_pause_points',return_value=[2.0]):
            rows=render.speech_plan(doc,clips)
        self.assertEqual(len(rows),30)
        for shot,row in zip(doc['shots'],rows):
            self.assertGreaterEqual(row['caption_start'],shot['start'])
            self.assertLessEqual(row['caption_end'],shot['end'])
            self.assertEqual(row['text'],shot['narration'])
        self.assertLessEqual(rows[-1]['end'],179)
        ass,srt=render.subtitles(rows)
        self.assertIn('AI动画情景重现 · 非新闻影像',ass)
        self.assertIn('芦原区三母女案',ass)
        self.assertIn(r'\c&H0066D1FF&',ass)
        self.assertGreaterEqual(srt.count(' --> '),30)
        self.assertIn('钟面时间为情景示意',ass)
        for row in rows:
            cues=render.subtitle_cues(row)
            self.assertEqual(''.join(t for _,_,t in cues),row['text'])
            self.assertTrue(all(row['caption_start']<=a<b<=row['caption_end'] for a,b,_ in cues))
            self.assertTrue(all(cues[j][1]<=cues[j+1][0]+1e-9 for j in range(len(cues)-1)))

    def test_render_rejects_overlong_voice(self):
        render=load('render')
        doc=json.loads((ROOT/'story.json').read_text(encoding='utf-8'))
        clips={s['id']:{'file':'not-generated.mp3'} for s in doc['shots']}
        with patch.object(render,'duration_audio',return_value=9.0), patch.object(render,'voice_activity',return_value=(0.0,8.9)):
            with self.assertRaises(RuntimeError): render.speech_plan(doc,clips)

    def test_render_provenance_and_voice_hash_gates(self):
        import hashlib
        render=load('render');gen=load('generate_clips');rev=gen.revision()
        doc=json.loads((ROOT/'story.json').read_text(encoding='utf-8'))
        with TemporaryDirectory() as temp:
            root=Path(temp); (root/'audio').mkdir()
            (root/'voice-selection.json').write_text('{"voice_id":"voice-00"}',encoding='utf-8')
            results={'phase':'clips_ready','reference_revision':rev,'shots':{}}
            clips=[]
            for shot in doc['shots']:
                sid=shot['id']; path=root/'audio'/f'{sid}.mp3'; path.write_bytes(('test-'+sid).encode())
                clips.append({'id':sid,'file':f'audio/{sid}.mp3','text':shot['narration'],'voice_id':'voice-00','sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
                results['shots'][sid]={'status':'completed','visual_review':'passed','video_id':'fixture','sha256':'fixture','bytes':1,'video_url':'https://fixture.invalid/a','request_hash':gen.request_hash(gen.payload(shot,rev))}
            manifest={'completed':30,'clips':clips}
            with patch.object(render,'HERE',root):
                self.assertEqual(len(render.verify_inputs(doc,results,manifest)),30)
                expected=results['shots']['SH01']['request_hash'];results['shots']['SH01']['request_hash']='stale'
                with self.assertRaises(RuntimeError): render.verify_inputs(doc,results,manifest,allow_unreviewed=True)
                results['shots']['SH01']['request_hash']=expected
                clips[0]['voice_id']='wrong-voice'
                with self.assertRaises(RuntimeError): render.verify_inputs(doc,results,manifest)
                clips[0]['voice_id']='voice-00'
                (root/'audio'/'SH01.mp3').write_bytes(b'corrupt')
                with self.assertRaises(RuntimeError): render.verify_inputs(doc,results,manifest)

    def test_provider_rejection_stops_further_submissions(self):
        import time
        gen=load('generate_clips')
        shots=json.loads((ROOT/'story.json').read_text(encoding='utf-8'))['shots'][:2]
        class FakeReceipts:
            def __init__(self): self.rows={}
            def row(self,sid): return self.rows.setdefault(sid,{})
            def update(self,sid,**kw): self.row(sid).update(kw)
            def push(self,**kw): pass
        class FakeGate:
            def acquire_creation(self,deadline): pass
        receipts=FakeReceipts()
        producer=gen.Producer({'shots':shots},shots,'test-key','https://unused.invalid',time.monotonic()+3600,receipts,'a'*40,set())
        producer.gate=FakeGate()
        try:
            with patch.object(gen.agnes,'create_task',side_effect=gen.agnes.Fatal('Authentication failed (HTTP 401)')) as call, patch.object(gen,'log'):
                producer.create_all(shots)
            self.assertEqual(call.call_count,1)
            self.assertEqual(receipts.row(shots[0]['id'])['status'],'create_failed')
            self.assertIn('rejected',producer.stop_reason)
        finally: producer.downloads.shutdown(wait=False)

    def test_artifact_restore_matches_receipt_not_artifact_order(self):
        import hashlib
        restore=load('restore_artifacts')
        with TemporaryDirectory() as temp:
            root=Path(temp); first=root/'original'; second=root/'retakes';out=root/'clips'
            first.mkdir();second.mkdir();(first/'SH05.mp4').write_bytes(b'old video')
            (second/'SH05.mp4').write_bytes(b'new video')
            data=b'new video';doc={'shots':{'SH05':{'status':'completed','sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)},'SH06':{'status':'completed','sha256':'b'*64,'bytes':2}}}
            done,missing=restore.restore(doc,[first,second],out)
            self.assertEqual(done,['SH05']);self.assertEqual(missing,['SH06'])
            self.assertEqual((out/'SH05.mp4').read_bytes(),data)

    @unittest.skipUnless(importlib.util.find_spec('numpy'), 'numpy not installed')
    def test_foley_is_timed_and_silent_at_end(self):
        import wave
        import numpy as np
        render=load('render')
        doc=json.loads((ROOT/'story.json').read_text(encoding='utf-8'))
        with TemporaryDirectory() as temp, patch.object(render,'RATE',8000):
            path=Path(temp)/'foley.wav';render.make_foley(path,doc)
            with wave.open(str(path)) as audio:
                self.assertEqual((audio.getframerate(),audio.getnchannels(),audio.getnframes()),(8000,2,8000*180))
                pcm=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2').reshape(-1,2)
            self.assertEqual(int(np.max(np.abs(pcm[-8000:]))),0)
            self.assertGreater(float(np.sqrt(np.mean(pcm[144*8000:146*8000].astype('float32')**2))),float(np.sqrt(np.mean(pcm[140*8000:142*8000].astype('float32')**2))))

    def test_caption_audit_requires_exact_text_and_shot_boundaries(self):
        audit=load('media_audit')
        doc={'shots':[{'id':'SH01','start':0,'end':5,'narration':'第一句，第二句。'},
                      {'id':'SH02','start':5,'end':10,'narration':'第三句。'}]}
        valid=('1\n00:00:00,100 --> 00:00:02,000\n第一句，\n\n'
               '2\n00:00:02,100 --> 00:00:04,900\n第二句。\n\n'
               '3\n00:00:05,100 --> 00:00:08,000\n第三句。\n')
        with TemporaryDirectory() as temp:
            srt=Path(temp)/'captions.srt';srt.write_text(valid,encoding='utf-8')
            self.assertEqual(audit.captions_audit(srt,doc)['cue_count'],3)
            srt.write_text(valid.replace('第一句','错一句',1),encoding='utf-8')
            with self.assertRaises(ValueError): audit.captions_audit(srt,doc)
            srt.write_text(valid.replace('00:00:04,900','00:00:05,020',1),encoding='utf-8')
            with self.assertRaises(ValueError): audit.captions_audit(srt,doc)

    def test_draft_is_watermarked_and_final_still_requires_review(self):
        import hashlib
        render=load('render');gen=load('generate_clips');rev=gen.revision();doc=json.loads((ROOT/'story.json').read_text(encoding='utf-8'))
        with TemporaryDirectory() as temp:
            root=Path(temp);(root/'audio').mkdir();(root/'voice-selection.json').write_text('{"voice_id":"voice-00"}',encoding='utf-8')
            results={'phase':'clips_ready','reference_revision':rev,'shots':{}};clips=[]
            for shot in doc['shots']:
                sid=shot['id'];data=sid.encode();(root/'audio'/f'{sid}.mp3').write_bytes(data)
                clips.append({'id':sid,'file':f'audio/{sid}.mp3','text':shot['narration'],'voice_id':'voice-00','sha256':hashlib.sha256(data).hexdigest()})
                results['shots'][sid]={'status':'completed','visual_review':'pending','video_id':'id','sha256':'x','bytes':1,'video_url':'https://example.invalid/v','request_hash':gen.request_hash(gen.payload(shot,rev))}
            manifest={'completed':30,'clips':clips}
            with patch.object(render,'HERE',root):
                with self.assertRaises(RuntimeError):render.verify_inputs(doc,results,manifest)
                self.assertEqual(len(render.verify_inputs(doc,results,manifest,allow_unreviewed=True)),30)
                results['shots']['SH01']['status']='failed'
                with self.assertRaises(RuntimeError):render.verify_inputs(doc,results,manifest,allow_unreviewed=True)
        sample=[{'caption_start':0.2,'caption_end':1.0,'text':'测试。','keywords':[]}]
        ass,_=render.subtitles(sample,draft=True);self.assertIn('未审片预览',ass)
        ass,_=render.subtitles(sample);self.assertNotIn('未审片预览',ass)

if __name__=='__main__': unittest.main()
