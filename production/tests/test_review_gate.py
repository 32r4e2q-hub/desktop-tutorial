"""交付门禁：五项缺一即拦，点名要具体到"谁没做、去跑什么"。

全用合成 JSON 测，不碰媒体——门禁本来也不碰媒体，它只验"东西在不在、
结论绿不绿"。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
import review_gate  # noqa: E402


def green_project(directory: Path) -> Path:
    project = directory / "project"
    (project / "review").mkdir(parents=True)
    (project / "delivery").mkdir(parents=True)
    (project / "review" / "film-review.json").write_text("{}", encoding="utf-8")
    (project / "review" / "transcode-check.json").write_text(
        json.dumps({"verdict": "pass"}), encoding="utf-8")
    (project / "review" / "distortion-check.json").write_text(
        json.dumps({"segments": [{"id": "S01", "verdict": "pass"},
                                 {"id": "S02", "verdict": "pass_with_note"}]}),
        encoding="utf-8")
    (project / "review" / "caption-energy-check.json").write_text(
        json.dumps({"shortlist_cues": [2, 3]}), encoding="utf-8")
    (project / "review" / "caption-listening.json").write_text(
        json.dumps({"shortlist_reviewed": True, "reviewer": "测试员",
                    "date": "2026-09-10"}), encoding="utf-8")
    (project / "delivery" / "verbatim-check.json").write_text(
        json.dumps({"film_pass": {"failing": []}}), encoding="utf-8")
    return project


class GateTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix="gate-"))

    def test_all_green_passes(self):
        project = green_project(self.directory)
        self.assertEqual(review_gate.main(["--project", str(project)]), 0)

    def test_missing_distortion_blocks_and_names_it(self):
        """畸变结论没落盘：拦住，且点名要跑 review_distortion.py。"""
        project = green_project(self.directory)
        (project / "review" / "distortion-check.json").unlink()
        self.assertEqual(review_gate.main(["--project", str(project)]), 1)
        _, failures = review_gate.check(project)
        self.assertEqual(len(failures), 1)
        self.assertIn("review_distortion.py", failures[0])

    def test_pending_distortion_blocks(self):
        """脚手架 verdict 全是 pending=没做：拦住。"""
        project = green_project(self.directory)
        (project / "review" / "distortion-check.json").write_text(
            json.dumps({"segments": [{"id": "S01", "verdict": "pending"}]}),
            encoding="utf-8")
        self.assertEqual(review_gate.main(["--project", str(project)]), 1)

    def test_shots_shaped_checklist_is_accepted(self):
        """dahlia 手工形状 {shots:{...}} 也认（兼容历史）。"""
        project = green_project(self.directory)
        (project / "review" / "distortion-check.json").write_text(
            json.dumps({"shots": {"S01": {"verdict": "pass"}}}), encoding="utf-8")
        self.assertEqual(review_gate.main(["--project", str(project)]), 0)

    def test_failed_distortion_blocks(self):
        project = green_project(self.directory)
        (project / "review" / "distortion-check.json").write_text(
            json.dumps({"segments": [{"id": "S07", "verdict": "fail"}]}), encoding="utf-8")
        _, failures = review_gate.check(project)
        self.assertTrue(any("S07" in f for f in failures))

    def test_unsigned_captions_block_then_signing_unlocks(self):
        project = green_project(self.directory)
        (project / "review" / "caption-listening.json").unlink()
        self.assertEqual(review_gate.main(["--project", str(project)]), 1)
        self.assertEqual(review_gate.main(
            ["--project", str(project), "--sign-captions", "测试员"]), 0)
        token = json.loads((project / "review" / "caption-listening.json")
                           .read_text(encoding="utf-8"))
        self.assertTrue(token["shortlist_reviewed"])
        self.assertEqual(token["reviewer"], "测试员")
        self.assertEqual(review_gate.main(["--project", str(project)]), 0)

    def test_failed_transcode_blocks(self):
        project = green_project(self.directory)
        (project / "review" / "transcode-check.json").write_text(
            json.dumps({"verdict": "fail"}), encoding="utf-8")
        self.assertEqual(review_gate.main(["--project", str(project)]), 1)

    def test_failing_verbatim_blocks(self):
        project = green_project(self.directory)
        (project / "delivery" / "verbatim-check.json").write_text(
            json.dumps({"film_pass": {"failing": ["N02"]}}), encoding="utf-8")
        _, failures = review_gate.check(project)
        self.assertTrue(any("N02" in f for f in failures))
