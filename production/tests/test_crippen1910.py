"""Offline content/payload tests. Passing these never approves missing media or references."""
import importlib.util
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'production/crippen1910'
spec = importlib.util.spec_from_file_location('crippen_generator', HERE/'generate.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


class CrippenPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story = json.loads((HERE/'story.json').read_text())

    def test_timeline_matches_user(self):
        cursor=0
        for shot in self.story['shots']:
            self.assertEqual(shot['start'], cursor)
            self.assertTrue(5 <= shot['duration'] <= 7)
            cursor += shot['duration']
        self.assertEqual(cursor, 180)
        self.assertEqual(len(self.story['shots']),30)

    def test_chapters(self):
        self.assertEqual([x['start'] for x in self.story['chapters']], [0,10,35,60,85,108,130,150,168])
        self.assertEqual(sum(x['duration'] for x in self.story['chapters']),180)

    def test_every_prompt_has_exact_anchors(self):
        for shot in self.story['shots']:
            prompt=gen.full_prompt(self.story,shot)
            self.assertTrue(prompt.startswith('【STYLE】'))
            self.assertTrue(prompt.endswith(gen.negative_for(self.story,shot)))
            for role in shot['characters']:
                self.assertIn(self.story['characters'][role],prompt)
            for n in range(1,len(shot['references'])+1):
                self.assertIn(f'<Picture {n}>',prompt)

    def test_reference_payload_not_text_generation(self):
        with patch.object(gen,'reference_urls',side_effect=lambda shot:['https://example.com/'+r+'.png' for r in shot['references']]):
            for shot in self.story['shots']:
                payload=gen.full_payload(self.story,shot)
                self.assertEqual(payload['mode'],'reference')
                self.assertEqual(len(payload['images']),len(shot['references']))
                self.assertEqual(set(payload),gen.ALLOWED_PAYLOAD_FIELDS)
                self.assertFalse(gen.FORBIDDEN_PAYLOAD_FIELDS.intersection(payload))

    def test_reference_gate_fails_closed(self):
        with patch.object(gen, 'read_json', return_value={}):
            with self.assertRaisesRegex(ValueError,'Reference missing/unreviewed/changed'):
                gen.validate_reference_gate(self.story)

    def test_primary_files_alone_cannot_bypass_character_package(self):
        approved={ref['id']:{'status':'approved','sha256':gen.digest(HERE/ref['file'])} for ref in self.story['reference_images']}
        original=gen.read_json
        def fake_read(path,default):
            if path.name=='approvals.json':
                return {'assets':approved}
            return original(path,default)
        with patch.object(gen,'read_json',side_effect=fake_read):
            with self.assertRaisesRegex(ValueError,'Character view missing'):
                gen.validate_reference_gate(self.story)

    def test_mutable_reference_revision_rejected(self):
        with patch.object(gen,'read_json',return_value={'revision':'main'}):
            with self.assertRaisesRegex(ValueError,'immutable commit'):
                gen.reference_urls(self.story['shots'][0])

    def test_only_modern_lab_allows_modern_equipment(self):
        self.assertNotIn('现代物体',gen.negative_for(self.story,self.story['shots'][28]))
        self.assertIn('2007年现代生物实验室',gen.style_for(self.story,self.story['shots'][28]))
        self.assertIn('现代物体',gen.negative_for(self.story,self.story['shots'][27]))

    def test_one_line_one_shot_budget(self):
        manifest=json.loads((HERE/'audio/manifest.json').read_text())
        for shot,record in zip(self.story['shots'],manifest['clips']):
            self.assertEqual(record['text'],shot['narration'])
            self.assertEqual(record['target_duration'],shot['duration'])
            count=len(re.sub(r'[^\u3400-\u9fffA-Za-z0-9]','',shot['narration']))
            self.assertLessEqual(count/shot['duration'],4.2)

    def test_revision_and_episode(self):
        self.assertEqual(self.story['episode'],3)
        self.assertEqual(self.story['branch'],'arena/f38dd103-desktop-tutorial')
        self.assertEqual(sum(r['asset_role']=='primary' for r in self.story['reference_images']),31)
        self.assertEqual(len(self.story['reference_images']),35)

    def test_montrose_sub_locations(self):
        shots={s['id']:s for s in self.story['shots']}
        self.assertIn('S06_deck',shots['S16']['references'])
        self.assertIn('S06_dining',shots['S17']['references'])
        self.assertIn('S06_cabin',shots['S18']['references'])
        self.assertIn('C01_face',shots['S04']['references'])
        for shot in shots.values():
            self.assertLessEqual(len(shot['references']),8)

    def test_twist_not_exoneration(self):
        tail=''.join(s['narration'] for s in self.story['shots'][-2:])
        self.assertIn('可能',tail)
        self.assertIn('争议',tail)
        self.assertNotIn('已经平反',tail)

if __name__=='__main__':
    unittest.main()
