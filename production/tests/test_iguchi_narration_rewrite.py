"""Text-only pacing checks for the versioned Iguchi narration rewrite."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from production.iguchi1990 import build_story


class IguchiNarrationRewriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = build_story.narration_rewrite_v2_rows()

    def test_active_v2_covers_existing_30_shot_timeline_and_fits_speech_window(self):
        self.assertEqual([row["id"] for row in self.rows], [f"S{i:02d}" for i in range(1, 31)])
        self.assertEqual(sum(row["duration"] for row in self.rows), 180)
        self.assertEqual(sum(row["hanzi_count"] for row in self.rows), 649)
        self.assertAlmostEqual(649 / 180, 3.6055555556, places=3)
        self.assertLessEqual(max(row["hanzi_per_second"] for row in self.rows), 3.7 * 1.15)

        active = {shot["id"]: shot for shot in build_story.SHOTS}
        for row in self.rows:
            self.assertEqual(row["start"], active[row["id"]]["start"])
            self.assertEqual(row["duration"], active[row["id"]]["duration"])
            self.assertEqual(row["narration"], active[row["id"]]["narration"])

    def test_removes_repetitive_media_attribution_but_keeps_claims_attributed(self):
        narration = "".join(row["narration"] for row in self.rows)
        for phrase in ("媒体报道", "媒体记载", "据报道", "报道指"):
            self.assertNotIn(phrase, narration)
        rows = {row["id"]: row["narration"] for row in self.rows}
        self.assertIn("供称", rows["S16"])
        self.assertIn("说", rows["S17"])
        self.assertIn("回忆", rows["S25"])
        self.assertIn("供称", rows["S28"])
        self.assertNotIn("二〇二六年初", rows["S30"])
        self.assertEqual(rows["S30"], "旅程结束，留下的疑问仍未解开。")
        self.assertNotIn("骨灰", rows["S30"])

    def test_draft_writer_does_not_need_to_rebuild_active_story_or_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = build_story.write_narration_rewrite_v2(Path(directory) / "draft.md")
            text = path.read_text(encoding="utf-8")
        self.assertIn("649 个 CJK 汉字", text)
        self.assertIn("| S30 | 02:54.000–03:00.000 |", text)
        for row in self.rows:
            self.assertIn(row["narration"], text)


if __name__ == "__main__":
    unittest.main()
