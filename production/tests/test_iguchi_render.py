"""Offline technical tests for the 1080p24 Iguchi edit pipeline."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

import yaml

from production.iguchi1990 import build_story, render

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "production" / "iguchi1990"


class IguchiRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story = build_story.build()

    def test_exact_timeline_and_one_vo_slot_per_shot(self):
        render.validate_timeline(self.story)
        manifest = json.loads((HERE / "audio" / "manifest.json").read_text(encoding="utf-8"))
        clips = {row["id"]: row for row in manifest["clips"]}
        self.assertEqual(set(clips), {shot["id"] for shot in self.story["shots"]})
        for shot in self.story["shots"]:
            self.assertEqual(clips[shot["id"]]["text"], shot["narration"])
            self.assertEqual(clips[shot["id"]]["target_start"], shot["start"])
            self.assertEqual(clips[shot["id"]]["target_duration"], shot["duration"])
            self.assertEqual(clips[shot["id"]]["alignment"], "shot-locked")

    def test_all_thirty_selected_voice_files_are_ready_and_hash_bound(self):
        manifest = json.loads((HERE / "audio" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["voice_id"], "voice-02")
        self.assertEqual(len(manifest["clips"]), 30)
        for row in manifest["clips"]:
            self.assertEqual(row["status"], "ready", row["id"])
            audio = HERE / "audio" / row["file"]
            self.assertTrue(audio.is_file(), row["id"])
            self.assertEqual(render.sha256(audio), row["sha256"], row["id"])

    def test_narration_integrity_and_date_qualified_parole_status(self):
        self.assertEqual(self.story["narration_stats"]["hanzi_count"], 658)
        self.assertAlmostEqual(self.story["narration_stats"]["hanzi_per_second"], 658 / 180, places=3)
        rows = {shot["id"]: shot for shot in self.story["shots"]}
        self.assertIn("媒体回顾", rows["S05"]["narration"])
        self.assertIn("媒体", rows["S06"]["narration"])
        self.assertIn("媒体", rows["S07"]["narration"])
        self.assertNotIn("失去踪影", rows["S19"]["narration"])
        self.assertIn("二〇二六年初", rows["S30"]["narration"])
        self.assertIn("官方现况待核", rows["S30"]["narration"])
        self.assertNotIn("近年报道", rows["S30"]["narration"])

    def test_three_visual_failures_have_narrow_safe_replacement_prompts(self):
        prompts = {shot["id"]: shot["prompt"].lower() for shot in self.story["shots"]}
        self.assertIn("no montage", prompts["S09"])
        s09 = next(shot for shot in self.story["shots"] if shot["id"] == "S09")
        self.assertEqual(s09["references"], ["C01"])
        self.assertIn("locked-off wide shot", prompts["S09"])
        self.assertIn("no taxi", prompts["S09"])
        self.assertIn("no storefront", prompts["S23"])
        self.assertIn("no blood", prompts["S27"])
        self.assertIn("no forensic tent", prompts["S27"])
        review = (HERE / "visual_review.md").read_text(encoding="utf-8")
        self.assertIn("仅 S09、S23、S27", review)

    def test_hash_bound_blur_masks_match_only_reviewed_sources(self):
        results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
        for sid, spec in render.BLUR_MASKS.items():
            self.assertEqual(results["shots"][sid]["sha256"], spec["sha256"], sid)
            boxes = render._blur_spec(sid, spec["sha256"])
            self.assertTrue(boxes)
            if sid == "S08":
                self.assertEqual([box[4:] for box in boxes], [(0.0, 3.5), (3.5, 7.0)])
            if sid == "S09":
                self.assertEqual(sorted({box[4:] for box in boxes}),
                                 [(0.0, 0.55), (0.55, 1.05), (1.05, 1.55), (1.3, 1.4),
                                  (1.4, 1.55), (1.55, 2.2), (2.2, 2.7), (2.7, 3.0), (3.0, 6.0)])
                micro_masks = {box[4:]: box[:4] for box in boxes if box[4:] in {(1.3, 1.4), (1.4, 1.55)}}
                self.assertEqual(micro_masks, {(1.3, 1.4): (520, 50, 260, 220),
                                               (1.4, 1.55): (520, 50, 280, 220)})
                graph, _ = render._normalized_graph({"id": "S09", "duration": 6},
                                                    {"width": 1280, "height": 720}, None, boxes)
                self.assertIn("crop=260:220:520:50,boxblur=42:8", graph)
                self.assertIn("crop=280:220:520:50,boxblur=42:8", graph)
        with self.assertRaisesRegex(RuntimeError, "source changed since blur mask review"):
            render._blur_spec("S06", "0" * 64)

    def test_matte_detector_tolerates_only_a_few_noisy_edge_rows(self):
        gray = render.np.full((360, 640), 100, dtype=render.np.uint8)
        gray[:31, :] = 0
        gray[:4, ::10] = 32  # a sparse compression/lighting artifact at the edge
        gray[-27:, :] = 0
        gray[-3:, ::10] = 32
        self.assertEqual(render._dark_edge_run(gray, False, axis=0, limit=79), 31)
        self.assertEqual(render._dark_edge_run(gray, True, axis=0, limit=79), 27)
        self.assertEqual(render._crop_values(
            {"width": 1280, "height": 720}, {"axis": "horizontal", "first": 64, "last": 56}
        ), (1280, 600, 0, 64))

    def test_source_gate_rejects_freeze_padding_and_frame_duplication(self):
        self.assertEqual(render.validate_source_motion("S01", {"duration": "5.0", "avg_frame_rate": "24/1"}, 120, 5), 120)
        with self.assertRaisesRegex(RuntimeError, "refusing frame padding"):
            render.validate_source_motion("S01", {"duration": "4.9", "avg_frame_rate": "24/1"}, 120, 5)
        with self.assertRaisesRegex(RuntimeError, "below 24 fps"):
            render.validate_source_motion("S01", {"duration": "5.0", "avg_frame_rate": "15/1"}, 120, 5)
        with self.assertRaisesRegex(RuntimeError, "refusing to freeze or pad"):
            render.validate_source_motion("S01", {"duration": "5.0", "avg_frame_rate": "24/1"}, 119, 5)

    def test_caption_wrapping_and_gold_keyword_style(self):
        parts = render.split_subtitle("二〇二六年初报道指，假释未获准；官方现况仍待核实。", limit=12)
        self.assertLessEqual(len(parts), 3)
        self.assertTrue(all(len(part) <= 12 for part in parts))
        line = render.highlight_line("媒体记载，刘学强被判无期。", ["刘学强"])
        self.assertIn(r"\c&H005FC9F4&", line)
        self.assertIn("刘学强", line)

    def test_audio_design_is_shot_specific_aperiodic_and_silent_at_the_end(self):
        self.assertEqual(set(render.SOUND_PROFILES), {shot["id"] for shot in self.story["shots"]})
        self.assertEqual(render.SILENT_TAIL_SECONDS, 1.0)
        self.assertEqual(render.RATE, 48_000)
        self.assertTrue(all(render.SOUND_PROFILES[sid][0] in render.PROFILE_CUTOFFS
                            for sid in render.SOUND_PROFILES))
        audio, report = render.synthesize_ambience(self.story, ROOT / "work" / "render-tests")
        self.assertEqual(audio.shape, (180 * render.RATE, 2))
        self.assertEqual(render.np.count_nonzero(audio[-render.RATE:, :]), 0)
        self.assertFalse(report["music"])
        self.assertFalse(report["melodic_bed"])
        self.assertEqual(len(report["shots"]), 30)
        self.assertTrue(all(row["music"] is False for row in report["shots"]))

    def test_render_workflow_downloads_both_runs_on_github_runner(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "iguchi1990-render.yml").read_text())
        steps = workflow["jobs"]["render"]["steps"]
        download_steps = [step for step in steps if step.get("uses", "").startswith("actions/download-artifact@")]
        self.assertEqual(len(download_steps), 3)
        self.assertEqual(download_steps[0]["with"]["run-id"], "${{ steps.params.outputs.base_run_id }}")
        self.assertEqual(download_steps[1]["with"]["run-id"], "${{ steps.params.outputs.repair_run_id }}")
        self.assertEqual(download_steps[2]["with"]["run-id"], "${{ steps.params.outputs.repair2_run_id }}")
        self.assertIn("repair2_run_id != ''", download_steps[2]["if"])
        self.assertTrue(any("render.py" in step.get("run", "") for step in steps))
        triggers = workflow.get("on", workflow.get(True, {}))
        self.assertEqual(triggers["push"]["paths"], ["production/iguchi1990/RENDER_REQUEST"])
        self.assertTrue(any(step.get("id") == "params" for step in steps))


if __name__ == "__main__":
    unittest.main()
