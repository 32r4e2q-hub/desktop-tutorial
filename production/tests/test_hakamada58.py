import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/'production'/'hakamada58'
sys.path.insert(0,str(PROJECT))
import generate_clips
from throttle import BudgetExhausted, RequestGate
from recover_tasks import find_records, as_time
class Hakamada58PlanTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  subprocess.run([sys.executable,str(PROJECT/'build_story.py')],check=True,capture_output=True,text=True)
  cls.data=json.loads((PROJECT/'story.json').read_text(encoding='utf-8'))
 def test_30_real_motion_shots_cover_exact_180_seconds(self):
  self.assertTrue(generate_clips.validate(self.data))
  self.assertEqual(len(self.data['shots']),30)
  self.assertEqual(sum(s['duration'] for s in self.data['shots']),180)
  self.assertTrue(all(s['kind']=='agnes' for s in self.data['shots']))
  self.assertTrue(all('真实连续运动' in s['prompt'] or '全程真实连续运动' in s['prompt'] for s in self.data['shots']))
 def test_style_references_and_negative_are_inline_in_order(self):
  for s in self.data['shots']:
   self.assertTrue(s['prompt'].startswith('【STYLE】'))
   self.assertIn('【参考图说明】',s['prompt'])
   self.assertTrue(s['prompt'].endswith(self.data['negative']))
   self.assertEqual(s['duration'],6)
   self.assertEqual(s['start'],(int(s['id'][1:])-1)*6)
   for keyword in s['highlight_keywords']:self.assertIn(keyword,s['subtitle'])
 def test_reference_payload_matches_son_of_sam_schema(self):
  allowed={'model','prompt','seconds','size','aspect_ratio','mode','n','seed','images'}
  rev='a'*40
  for shot in self.data['shots']:
   p=generate_clips.payload(shot,rev)
   self.assertEqual(set(p),allowed)
   self.assertEqual(p['model'],'agnes-video-2.5-flash')
   self.assertEqual(p['mode'],'reference')
   self.assertEqual(p['seconds'],'6')
   self.assertEqual(len(p['images']),len(shot['reference_images']))
   self.assertTrue(all(rev in url for url in p['images']))
   self.assertTrue(all('/'+rid+'.png' in url for rid,url in zip(shot['reference_images'],p['images'])))
 def test_all_approved_references_exist(self):
  status=self.data['reference_status']
  self.assertEqual(len(status['approved_generated']),38)
  self.assertEqual(status['pending'],[])
  for rid in status['approved_generated']:
   p=PROJECT/'reference'/f'{rid}.png'
   self.assertTrue(p.is_file(),rid)
   self.assertGreater(p.stat().st_size,20000,rid)
 def test_published_immutable_revision_and_sha_ledger_validate(self):
  rev=generate_clips.revision()
  self.assertRegex(rev,r'^[0-9a-f]{40}$')
  generate_clips.validate_bundle(self.data,rev)
  urls=generate_clips.payload(self.data['shots'][0],rev)['images']
  self.assertEqual(len(urls),len(self.data['shots'][0]['reference_images']))
 def test_cli_validate_is_offline(self):
  results=PROJECT/'results.json'
  before=results.read_bytes() if results.exists() else None
  result=subprocess.run([sys.executable,str(PROJECT/'generate_clips.py'),'--validate'],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertIn('mode=reference',result.stdout)
  after=results.read_bytes() if results.exists() else None
  self.assertEqual(before,after)
 def test_voiceover_manifest_matches_story_and_audio_hashes(self):
  manifest_path=PROJECT/'audio'/'manifest.json'
  if not manifest_path.exists():self.skipTest('narration not yet generated')
  manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
  self.assertEqual(manifest['completed'],len(manifest['clips']))
  self.assertLessEqual(manifest['completed'],manifest['planned'])
  shots={s['id']:s for s in self.data['shots']}
  for row in manifest['clips']:
   path=PROJECT/row['file']
   self.assertEqual(row['text'],shots[row['id']]['narration'])
   self.assertEqual(row['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
 def test_read_only_recovery_parser_handles_paginated_task_lists(self):
  body={'data':{'tasks':[{'id':'task_a','status':'completed'},{'id':'task_b','status':'running'}]}}
  self.assertEqual([x['id'] for x in find_records(body)],['task_a','task_b'])
  self.assertIsNotNone(as_time('2026-11-06T10:40:00Z'))
 def test_targeted_qc_revisions_remove_bloodlike_marks_and_calendar_artifact(self):
  shots={s['id']:s for s in self.data['shots']}
  self.assertIn('不得出现',shots['S11']['visual_prompt'])
  self.assertIn('干燥',shots['S11']['visual_prompt'])
  self.assertNotIn('P01',shots['S11']['reference_images'])
  self.assertIn('无任何斑点、污渍',shots['S12']['visual_prompt'])
  self.assertIn('NO FIRE, NO SMOKE, NO BLOOD',shots['S12']['visual_prompt'])
  self.assertIn('真90度正上方俯拍',shots['S12']['visual_prompt'])
  self.assertEqual(shots['S12']['reference_images'],['S12'])
  self.assertEqual(shots['S12']['character_anchors'],[])
  self.assertIn('不出现日历',shots['S17']['visual_prompt'])
  self.assertEqual(shots['S17']['character_anchors'],['C01C'])
 def test_second_pass_retake_prompts_resolve_continuity_failures(self):
  shots={s['id']:s for s in self.data['shots']}
  self.assertEqual(shots['S03']['reference_images'],['S03'])
  self.assertEqual(shots['S04']['reference_images'],['S03','S04'])
  self.assertIn('严格不出现消防车',shots['S03']['visual_prompt'])
  self.assertIn('仅出现三名',shots['S04']['visual_prompt'])
  self.assertIn('严禁红十字、黄十字',shots['S04']['visual_prompt'])
  self.assertIn('清楚看到水流喷向',shots['S04']['visual_prompt'])
  self.assertIn('不要出现村民群',shots['S04']['visual_prompt'])
  self.assertNotIn('C06',shots['S04']['reference_images'])
  self.assertEqual(shots['S20']['reference_images'],['S20','C02'])
  self.assertIn('晾衣绳',shots['S20']['visual_prompt'])
  self.assertIn('全身可见',shots['S20']['visual_prompt'])
  self.assertIn('NO CUT, NO CLOSE-UP',shots['S20']['visual_prompt'])
  self.assertEqual(shots['S22']['reference_images'],['S15','P29'])
  self.assertIn('始终并肩同框',shots['S22']['visual_prompt'])
  self.assertEqual(shots['S27']['reference_images'],['P27'])
  self.assertIn('不出现特写插入',shots['S27']['visual_prompt'])
  self.assertEqual(shots['S28']['reference_images'],['P28'])
  self.assertIn('不得出现人物、手、人体',shots['S28']['visual_prompt'])
  self.assertEqual(shots['S29']['reference_images'],['P29'])
  self.assertIn('左右分屏',shots['S29']['visual_prompt'])
 def test_paid_plan_creation_gate_requires_opt_in_and_spaces_requests(self):
  class Clock:
   now=0.0
   def __call__(self): return self.now
   def sleep(self,seconds): self.now+=seconds
  clock=Clock()
  with self.assertRaises(ValueError): RequestGate(12,clock=clock,sleep=clock.sleep)
  gate=RequestGate(12,allow_fast_plan=True,clock=clock,sleep=clock.sleep)
  gate.acquire_creation(100)
  first=clock.now
  gate.acquire_creation(100)
  self.assertGreaterEqual(clock.now-first,12)
  gate.defer(25)
  with self.assertRaises(BudgetExhausted): gate.wait_unblocked(24)
if __name__=='__main__':unittest.main()
