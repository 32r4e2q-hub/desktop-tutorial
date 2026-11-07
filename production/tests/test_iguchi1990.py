"""Offline safety and timeline tests for the 30-shot Iguchi Mariko production."""
from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from production.iguchi1990 import build_story, generate

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "production" / "iguchi1990"


class Iguchi1990PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = build_story.build()

    def test_exact_30_shots_and_180_second_contiguous_timeline(self):
        shots = self.project["shots"]
        self.assertEqual(len(shots), 30)
        self.assertEqual([shot["id"] for shot in shots], [f"S{i:02d}" for i in range(1, 31)])
        cursor = 0
        for shot in shots:
            self.assertEqual(shot["start"], cursor, shot["id"])
            self.assertGreaterEqual(shot["duration"], 4)
            self.assertLessEqual(shot["duration"], 12)
            cursor += shot["duration"]
        self.assertEqual(cursor, 180)
        self.assertEqual((self.project["width"], self.project["height"], self.project["fps"]),
                         (1920, 1080, 24))

    def test_narration_hanzi_rate_matches_target(self):
        stats = self.project["narration_stats"]
        self.assertEqual(stats["duration_seconds"], 180)
        counted = sum(
            len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", shot["narration"]))
            for shot in self.project["shots"]
        )
        self.assertEqual(stats["hanzi_count"], counted)
        self.assertAlmostEqual(stats["hanzi_per_second"], counted / 180, places=3)
        self.assertGreaterEqual(stats["hanzi_per_second"], 3.65)
        self.assertLessEqual(stats["hanzi_per_second"], 3.75)

    def test_offline_project_and_agnes_payload_validate(self):
        generate.validate_project(self.project, require_approved_refs=False)
        for shot in self.project["shots"]:
            payload = generate.full_payload(self.project, shot)
            self.assertEqual(payload["model"], "agnes-video-2.5-flash")
            self.assertEqual(payload["seconds"], str(shot["duration"]))
            self.assertEqual(payload["size"], "720P")
            self.assertEqual(payload["aspect_ratio"], "16:9")
            self.assertEqual(payload["mode"], "reference")
            self.assertEqual(payload["n"], 1)
            self.assertEqual(len(payload["images"]), len(shot["references"]))
            self.assertLessEqual(len(payload["images"]), 5)
            self.assertNotIn("negative_prompt", payload)
            self.assertFalse(generate.FORBIDDEN_FIELDS.intersection(payload))

    def test_prompt_order_is_style_references_role_scene_negative(self):
        shot = self.project["shots"][0]
        prompt = generate.full_prompt(self.project, shot)
        self.assertTrue(prompt.startswith("【STYLE】"))
        self.assertLess(prompt.index("<Picture 1>"), prompt.index("【C01锚点】"))
        self.assertLess(prompt.index("【C01锚点】"), prompt.index(shot["prompt"]))
        self.assertTrue(prompt.endswith(self.project["negative_prompt"]))
        self.assertIn("【NEGATIVE】", prompt)

    def test_reference_gate_fails_closed(self):
        from copy import deepcopy

        project_with_rejected_reference = deepcopy(self.project)
        target = project_with_rejected_reference["reference_images"][0]
        target["approved"] = False
        target["review_status"] = "rejected"
        errors = generate.reference_errors(project_with_rejected_reference)
        self.assertTrue(any(
            target["id"] in error and "story.json is not approved (rejected)" in error
            for error in errors
        ))
        with self.assertRaisesRegex(ValueError, "Reference gate blocked generation"):
            generate.validate_project(project_with_rejected_reference, require_approved_refs=True)

    def test_motion_probe_flags_frozen_frames(self):
        frame_size = 64 * 36
        frozen = bytes([90]) * frame_size
        still_report = generate.frame_motion_metrics([frozen] * 9, frame_size)
        self.assertTrue(still_report["suspected_static"])
        changed = bytearray(frozen)
        changed[:frame_size // 2] = bytes([150]) * (frame_size // 2)
        moving_report = generate.frame_motion_metrics([frozen, bytes(changed), frozen, bytes(changed)], frame_size)
        self.assertFalse(moving_report["suspected_static"])
        self.assertGreater(moving_report["moving_transitions"], 0)

    def test_airport_and_night_market_are_separate_reference_assets(self):
        refs = {row["id"]: row for row in self.project["reference_images"]}
        self.assertNotEqual(refs["S02"]["file"], refs["S02b"]["file"])
        self.assertIn("机场", refs["S02"]["description"])
        self.assertIn("夜市", refs["S02b"]["description"])

    def test_every_shot_has_its_own_caption_audio_slot_and_no_bgm(self):
        manifest = json.loads((HERE / "audio" / "manifest.json").read_text(encoding="utf-8"))
        clips = {row["id"]: row for row in manifest["clips"]}
        self.assertEqual(set(clips), {shot["id"] for shot in self.project["shots"]})
        for shot in self.project["shots"]:
            row = clips[shot["id"]]
            self.assertEqual(row["text"], shot["narration"])
            self.assertEqual(row["target_start"], shot["start"])
            self.assertEqual(row["target_duration"], shot["duration"])
        self.assertIn("无BGM", self.project["presentation"]["audio_style"])
        self.assertNotIn("栽赃", "".join(shot["narration"] for shot in self.project["shots"]))


if __name__ == "__main__":
    unittest.main()
