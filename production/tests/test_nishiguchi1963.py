import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / 'nishiguchi1963'
spec = importlib.util.spec_from_file_location('nishiguchi_generator', HERE / 'generate.py')
# generate.py imports its local throttle module.
import sys
sys.path.insert(0, str(HERE))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

class NishiguchiPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = json.loads((HERE / 'story.json').read_text(encoding='utf-8'))

    def test_plan_and_exact_timeline(self):
        gen.validate(self.project, require_audio=False)
        shots = self.project['shots']
        self.assertEqual(len(shots), 30)
        self.assertEqual(sum(s['duration'] for s in shots), 180)
        self.assertTrue(all(5 <= s['duration'] <= 7 for s in shots))
        self.assertEqual(shots[-1]['start'] + shots[-1]['duration'], 180)

    def test_prompt_assembly_and_payload(self):
        for shot in self.project['shots']:
            prompt = gen.full_prompt(self.project, shot)
            self.assertTrue(prompt.startswith('【STYLE】'))
            self.assertTrue(prompt.endswith(self.project['negative_prompt']))
            for character in shot['characters']:
                self.assertIn(self.project['characters'][character], prompt)
            self.assertEqual(gen.full_payload(self.project, shot)['seconds'], str(shot['duration']))
            self.assertIn('continuous', prompt)

    def test_references_exist_and_audio_not_misrepresented(self):
        for reference in self.project['reference_images']:
            self.assertTrue((HERE / reference['file']).is_file())
        with self.assertRaises(ValueError):
            gen.validate(self.project, require_audio=True)

    def test_chapter_boundaries(self):
        cursor = 0
        for chapter in self.project['chapters']:
            self.assertEqual(chapter['start'], cursor)
            shots = [s for s in self.project['shots'] if s['narration_id'] == chapter['id']]
            self.assertEqual(chapter['shot_ids'], [s['id'] for s in shots])
            self.assertEqual(chapter['duration'], sum(s['duration'] for s in shots))
            cursor += chapter['duration']
        self.assertEqual(cursor, 180)

if __name__ == '__main__': unittest.main()
