import json
import subprocess
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/'production'/'hakamada58'
sys.path.insert(0,str(PROJECT))
import generate_clips
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
 def test_all_34_approved_references_exist(self):
  status=self.data['reference_status']
  self.assertEqual(len(status['approved_generated']),34)
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
  result=subprocess.run([sys.executable,str(PROJECT/'generate_clips.py'),'--validate'],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertIn('mode=reference',result.stdout)
  self.assertFalse((PROJECT/'results.json').exists())
if __name__=='__main__':unittest.main()
