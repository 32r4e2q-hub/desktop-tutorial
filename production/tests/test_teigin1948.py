import json
import tempfile

import numpy as np
import unittest
from pathlib import Path

from production.teigin1948.qc import analyse_picture, check_subtitles
from production.teigin1948.build_audio import voice_tempo_factor

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

    def test_narration_copy_is_length_matched_to_each_video_shot(self):
        spec = self.story['narration_spec']
        self.assertEqual(spec['voice_id'], 'voice-01')
        self.assertEqual(spec['target_characters_per_second'], 3.7)
        self.assertTrue(spec['slowdown_allowed'])
        for shot in self.story['shots']:
            visible = sum(ch.isalnum() for ch in shot['narration'])
            rate = visible / shot['duration']
            self.assertGreaterEqual(rate, 2.9, shot['id'])
            self.assertLessEqual(rate, 4.7, shot['id'])
        self.assertAlmostEqual(voice_tempo_factor(4.6, 4.92), 4.6 / 4.92, places=6)
        with self.assertRaises(RuntimeError):
            voice_tempo_factor(3.0, 5.0)

    def test_teigin_specific_endcard_and_cup_cover(self):
        render = (PROJECT / 'render.py').read_text(encoding='utf-8')
        self.assertIn('东京 · 1948 · 至今存疑', render)
        self.assertIn('帝银事件', render)
        self.assertIn('S07.mp4', render)
        self.assertIn('(1868, 643, 1902, 677)', render)
        self.assertIn('Teigin_Cover.png', (PROJECT / 'generate.py').read_text(encoding='utf-8'))

    def test_end_question_in_last_narration_caption_is_not_a_missing_card(self):
        def clock(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            whole = int(seconds % 60)
            millis = round((seconds - int(seconds)) * 1000)
            if millis == 1000:
                whole += 1
                millis = 0
            return f'{hours:02}:{minutes:02}:{whole:02},{millis:03}'

        blocks = []
        for index, shot in enumerate(self.story['shots'], 1):
            text = shot['narration']
            lines = [text[:26], text[26:]] if len(text) > 26 else [text]
            lines = [line for line in lines if line]
            start = shot['start'] + 0.03
            end = shot['start'] + shot['duration'] - 0.05
            blocks.append(f"{index}\n{clock(start)} --> {clock(end)}\n" + "\n".join(lines))

        with tempfile.TemporaryDirectory() as directory:
            srt = Path(directory) / 'captions.srt'
            srt.write_text('\n\n'.join(blocks), encoding='utf-8')
            result = check_subtitles(srt, self.story)

        self.assertEqual(result['cues'], 29)
        self.assertEqual(result['end_card_cues'], 1)
        self.assertTrue(result['covers_all_lines'])
        self.assertEqual(result['problems'], [])

    def test_flash_detector_does_not_call_a_persistent_cut_a_flash(self):
        cut = np.full((20, 8, 8), 20, dtype=np.uint8)
        cut[8:] = 100
        flash = np.full((20, 8, 8), 20, dtype=np.uint8)
        flash[8] = 100
        cut_result = analyse_picture(cut, fps=4.0, shots=[])
        flash_result = analyse_picture(flash, fps=4.0, shots=[])
        self.assertEqual(cut_result['flash_samples'], [])
        self.assertEqual(flash_result['flash_samples'], [1.75])

if __name__ == '__main__':
    unittest.main()
