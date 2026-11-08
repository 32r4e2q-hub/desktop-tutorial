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
        self.assertGreaterEqual(stats["hanzi_per_second"], 3.60)
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

    def test_monthly_rate_gate_and_saved_provider_window(self):
        self.assertAlmostEqual(generate.MIN_CREATE_INTERVAL, 12.1)
        member_gate = generate.RequestGate(
            minimum_interval=generate.MIN_CREATE_INTERVAL,
            minimum_allowed_interval=generate.MIN_CREATE_INTERVAL,
        )
        self.assertAlmostEqual(member_gate.interval, 12.1)
        # Other projects retain the shared conservative 60-second floor unless they opt in.
        with self.assertRaises(ValueError):
            generate.RequestGate(minimum_interval=generate.MIN_CREATE_INTERVAL)

        self.assertEqual(
            generate.provider_interval_from_message(
                "You have used up today's video generation quota and are now limited to 1 request every 5 minutes."
            ),
            300.0,
        )
        old_receipt = {"shots": {"S02": {"applied_cooldown_seconds": 239.0}}}
        self.assertEqual(generate.provider_interval_from_results(old_receipt), 300.0)
        current_receipt = {
            "provider_minimum_create_interval_seconds": 300.0,
            "shots": {"S06": {"applied_cooldown_seconds": 300.0,
                               "provider_minimum_create_interval_seconds": 300.0}},
        }
        self.assertEqual(generate.provider_interval_from_results(current_receipt), 300.0)

    def test_retry_after_extends_provider_interval_and_persists_cooldown(self):
        from unittest.mock import patch

        gate = generate.RequestGate(
            minimum_interval=generate.MIN_CREATE_INTERVAL,
            minimum_allowed_interval=generate.MIN_CREATE_INTERVAL,
        )
        doc = {"last_successful_create_epoch": 100.0}
        with patch("production.iguchi1990.generate.time.time", return_value=112.1):
            cooldown = generate.apply_rate_limit(gate, doc, "HTTP 429", 288.0)
        self.assertAlmostEqual(gate.interval, 300.1)
        self.assertEqual(cooldown, 300.0)
        self.assertAlmostEqual(doc["provider_minimum_create_interval_seconds"], 300.1)
        self.assertAlmostEqual(doc["provider_blocked_until_epoch"], 412.1)

        bare_gate = generate.RequestGate(
            minimum_interval=generate.MIN_CREATE_INTERVAL,
            minimum_allowed_interval=generate.MIN_CREATE_INTERVAL,
        )
        bare_doc = {}
        with patch("production.iguchi1990.generate.time.time", return_value=200.0):
            bare_cooldown = generate.apply_rate_limit(bare_gate, bare_doc, "HTTP 429", None)
        self.assertEqual(bare_cooldown, 300.0)
        self.assertEqual(bare_gate.interval, 300.0)
        self.assertEqual(bare_doc["provider_blocked_until_epoch"], 500.0)

        stricter_gate = generate.RequestGate(
            minimum_interval=generate.MIN_CREATE_INTERVAL,
            minimum_allowed_interval=generate.MIN_CREATE_INTERVAL,
        )
        stricter_doc = {"rate_policy": {}}
        with patch("production.iguchi1990.generate.time.time", return_value=200.0):
            stricter_cooldown = generate.apply_rate_limit(
                stricter_gate,
                stricter_doc,
                "1 request every 5 minutes",
                600.0,
            )
        self.assertEqual(stricter_gate.interval, 600.0)
        self.assertEqual(stricter_cooldown, 600.0)
        self.assertEqual(stricter_doc["rate_policy"]["effective_creation_interval_seconds"], 600.0)

    def test_forced_retry_archives_terminal_failure_and_clears_provider_task_id(self):
        shot = next(row for row in self.project["shots"] if row["id"] == "S09")
        wanted_hash = generate.request_hash(self.project, shot)
        old = {"id": "S09", "request_hash": wanted_hash, "status": "failed",
               "video_id": "task_upload_timeout", "generation_attempts": 1,
               "create_attempts": 1, "error": "upload timed out"}
        doc = {"shots": {"S09": old}}
        row = generate._new_task_row(doc, shot, wanted_hash)
        retried = generate.prepare_forced_retry(doc, shot, row, wanted_hash)
        self.assertEqual(retried["status"], "waiting_create_slot")
        self.assertNotIn("video_id", retried)
        self.assertEqual(retried["generation_attempts"], 1)
        self.assertEqual(retried["create_attempts"], 1)
        self.assertEqual(doc["previous_results"]["S09"], [old])
        self.assertEqual(doc["shots"]["S09"], retried)

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
