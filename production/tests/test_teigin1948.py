import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'production' / 'teigin1948'

class TeiginPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story = json.loads((PROJECT / 'story.json').read_text(encoding='utf-8'))

    def test_format_duration_and_contiguous_29_shots(self):
        shots = self.story['shots']
        self.assertEqual(len(shots), 29)
        self.assertEqual(self.story['target_duration'], 180)
        self.assertEqual((self.story['width'], self.story['height']), (1920, 1080))
        self.assertEqual(self.story['fps'], 24)
        cursor = 0
        for shot in shots:
            self.assertEqual(shot['start'], cursor)
            self.assertGreaterEqual(shot['duration'], 4)
            self.assertLessEqual(shot['duration'], 9)
            cursor += shot['duration']
        self.assertEqual(cursor, 180)

    def test_prompt_contract_and_character_roles(self):
        for shot in self.story['shots']:
            self.assertTrue(shot['prompt'].strip())
            self.assertTrue(shot['characters'] or shot['id'] in {'S01','S11','S13','S14','S15','S17','S19','S26','S27','S28','S29'})
            self.assertIn(shot['kind'], {'agnes'})
        self.assertTrue(self.story['style_prefix'].startswith('【STYLE】'))
        self.assertTrue(self.story['negative_prompt'].startswith('【NEGATIVE】'))

    def test_assets_and_narration_plan(self):
        for ref in self.story['reference_images']:
            self.assertTrue((PROJECT / ref['file']).is_file(), ref['file'])
        self.assertEqual(len(self.story['chapters']), 9)
        self.assertEqual(len({s['narration'] for s in self.story['shots']}), 29)
        self.assertEqual(self.story['shots'][27]['style_variant'], 'diagram')

if __name__ == '__main__':
    unittest.main()
