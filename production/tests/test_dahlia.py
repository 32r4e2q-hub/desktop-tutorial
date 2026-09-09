"""Offline tests; no API credentials, paid requests, or GitHub mutations."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('dahlia_generate', ROOT / 'production/dahlia/generate.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class PlanAndReviewTests(unittest.TestCase):
    def setUp(self):
        self.result = {'id': 'S01', 'request_hash': 'request-a', 'sha256': 'video-a'}
        self.approval = {'first_shot_id': 'S01', 'decision': 'approved',
                         'request_hash': 'request-a', 'video_sha256': 'video-a'}

    def test_complete_timeline_and_provider(self):
        project = json.loads((ROOT / 'production/dahlia/story.json').read_text())
        generator.validate(project)
        self.assertEqual(sum(s['kind'] == 'agnes' for s in project['shots']), 24)
        self.assertEqual(sum(s['kind'] == 'graphic' for s in project['shots']), 6)
        for shot in project['shots']:
            if shot['kind'] == 'agnes':
                self.assertEqual(generator.full_payload(project, shot)['model'], 'agnes-video-v2.0')

    def test_approval_requires_matching_material_and_prompt(self):
        self.assertTrue(generator.review_matches(self.approval, self.result))
        for changes in [{'decision': 'pending'}, {'first_shot_id': 'S02'},
                        {'request_hash': 'old-request'}, {'video_sha256': 'old-video'}]:
            with self.subTest(changes=changes):
                self.assertFalse(generator.review_matches({**self.approval, **changes}, self.result))
        for invalid in [None, [], {}, 'approved']:
            self.assertFalse(generator.review_matches(invalid, self.result))
        self.assertFalse(generator.review_matches(self.approval, {'id': 'S01'}))

    def test_review_gate_reads_only_current_branch(self):
        calls = []
        def fake_git(*args):
            calls.append(args)
            return json.dumps(self.approval) if args[0] == 'show' else ''
        with patch.object(generator, 'git', side_effect=fake_git):
            self.assertEqual(generator.wait_for_review(self.result), self.approval)
        self.assertEqual(calls[0], ('fetch', '--no-tags', 'origin', generator.BRANCH))
        self.assertEqual(calls[1], ('show', 'FETCH_HEAD:production/dahlia/review.json'))

    def test_rejected_first_shot_stops_batch(self):
        rejected = {**self.approval, 'decision': 'rejected'}
        with patch.object(generator, 'git', side_effect=['', json.dumps(rejected)]):
            with self.assertRaisesRegex(RuntimeError, 'rejected'):
                generator.wait_for_review(self.result)

    def test_timeout_does_not_approve(self):
        with self.assertRaisesRegex(RuntimeError, 'timed out'):
            generator.wait_for_review(self.result, timeout=0)

    def test_visual_prompt_has_no_closed_open_folder_conflict(self):
        project = json.loads((ROOT / 'production/dahlia/story.json').read_text())
        prompt = next(s['prompt'] for s in project['shots'] if s['id'] == 'S26').lower()
        self.assertIn('open', prompt)
        self.assertNotIn('closed case folder', prompt)


if __name__ == '__main__':
    unittest.main()
