import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/'production'/'hakamada58'
spec=importlib.util.spec_from_file_location('hakamada58_render',PROJECT/'render.py')
render=importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)

class Hakamada58RenderTests(unittest.TestCase):
 def test_sentence_captions_fit_each_six_second_shot(self):
  story=json.loads((PROJECT/'story.json').read_text(encoding='utf-8'))
  manifest=json.loads((PROJECT/'audio'/'manifest.json').read_text(encoding='utf-8'))
  rows,ass,srt=render.speech_plan(story,manifest)
  self.assertEqual(len(rows),30)
  self.assertEqual(ass.count('Dialogue: 0,'),30)
  self.assertEqual(srt.count(' --> '),30)
  previous_end=0.0
  for row in rows:
   self.assertGreaterEqual(row['start'],(int(row['id'][1:])-1)*6)
   self.assertLessEqual(row['end'],(int(row['id'][1:])-1)*6+6.0)
   if int(row['id'][1:])>1:self.assertGreaterEqual(row['start'],previous_end+0.11)
   previous_end=row['end']
   self.assertLessEqual(row['tempo'],1.2)
  self.assertIn('他等了58年',ass)
  self.assertIn(r'\c&H0066D1FF&',ass)

 def test_timecode_and_chinese_wrap_are_stable(self):
  self.assertEqual(render.ass_time(65.43),'0:01:05.43')
  self.assertEqual(render.srt_time(65.432),'00:01:05,432')
  self.assertIn('\\N',render.wrap_cn('袴田巖等待了五十八年终于迎来无罪判决这一天。',18))

if __name__=='__main__':unittest.main()
