"""CogVideoX-Flash 新项目脚手架的离线回归测试。"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
import new_cogvideox_topic  # noqa: E402

SLUG = "cogtest"
TITLE = "测试案件：工具链自检"
BRANCH = "arena/f5c619e4-desktop-tutorial"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class CogVideoXScaffoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="cogvideox-scaffold-test-"))
        cls.project = cls.tmp / SLUG
        new_cogvideox_topic.scaffold(SLUG, TITLE, BRANCH, cls.project)

    @classmethod
    def tearDownClass(cls):
        for name in list(sys.modules):
            if name.startswith("cog_scaffold_"):
                del sys.modules[name]
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_blank_plan_uses_cogvideox_without_reference_content(self):
        story = json.loads((self.project / "story.json").read_text())
        self.assertEqual(story["model"], "cogvideox-flash")
        self.assertEqual(story["_scaffold"]["reference"], "validated CogVideoX engine (content blank)")
        self.assertEqual(len(story["shots"]), 45)
        self.assertEqual(sum(shot["kind"] == "cogvideo" for shot in story["shots"]), 38)
        self.assertEqual({shot["id"] for shot in story["shots"] if shot["kind"] == "graphic"},
                         new_cogvideox_topic.GRAPHIC_IDS)
        self.assertTrue(all((shot["seconds"], shot["resolution"], shot["frame_rate"]) == (6, "1080p", 30)
                            for shot in story["shots"]))
        self.assertEqual(story["sources"], [])
        self.assertTrue(all(not chapter["text"] for chapter in story["chapters"]))

        copied = "\n".join(
            path.read_text(errors="ignore")
            for path in self.project.rglob("*")
            if path.is_file() and path.suffix != ".pyc"
        )
        for forbidden in ("jeong2000", "郑斗英", "十个月，九条人命"):
            self.assertNotIn(forbidden, copied)

    def test_engine_receipts_and_workflows_are_fresh(self):
        receipt = json.loads((self.project / "results.json").read_text())
        self.assertEqual(receipt["shots"], {})
        self.assertEqual(receipt["model"], "cogvideox-flash")
        self.assertEqual(receipt["provider"], "Zhipu AI")
        for old_output in ("qa", "delivery", "cast"):
            self.assertFalse((self.project / old_output).exists())
        for marker in ("GEN_REQUEST", "RENDER_REQUEST", "VERBATIM_REQUEST", "VISUAL_QC_REQUEST"):
            self.assertFalse((self.project / marker).exists())

        for kind in ("gen", "render", "verbatim", "visual-qc"):
            path = self.project / "workflows" / f"{SLUG}-{kind}.yml"
            text = path.read_text()
            self.assertIn(f"refs/heads/{BRANCH}", text)
            self.assertIn(f"production/{SLUG}", text)
        gen = (self.project / "workflows" / f"{SLUG}-gen.yml").read_text()
        self.assertIn("ZHIPUAI_API_KEY", gen)
        self.assertIn(f"python3 production/{SLUG}/generate.py --validate", gen)

    def test_authoring_template_matches_the_flash_plan(self):
        authoring = load_module("cog_scaffold_build_story", self.project / "build_story.py")
        self.assertEqual(sum(row[1] == "cogvideo" for row in authoring.SHOTS), 38)
        self.assertEqual({row[0] for row in authoring.SHOTS if row[1] == "graphic"},
                         new_cogvideox_topic.GRAPHIC_IDS)
        self.assertEqual(authoring.COGVIDEO_SECONDS, 6)
        self.assertIn("Realistic 3D animated documentary", authoring.STYLE_PREFIX)
        self.assertNotIn("3D render look", authoring.NEGATIVE_PROMPT)

    def test_empty_prompts_fail_before_generation(self):
        generator = load_module("cog_scaffold_generate", self.project / "generate.py")
        story = json.loads((self.project / "story.json").read_text())
        with self.assertRaisesRegex(ValueError, "missing prompt"):
            generator.validate(story)

    def test_filled_plan_builds_flash_payload(self):
        generator = load_module("cog_scaffold_generate_filled", self.project / "generate.py")
        story = json.loads((self.project / "story.json").read_text())
        story["style_prefix"] = "Realistic 3D animated documentary, 16:9."
        for shot in story["shots"]:
            if shot["kind"] == "cogvideo":
                shot["prompt"] = f"Wide establishing shot, safe empty environment, {shot['id']}"
            else:
                shot["graphic"] = f"Information card {shot['id']}"
        generator.validate(story)
        payload = generator.full_payload(story, story["shots"][0])
        self.assertEqual(payload["model"], "cogvideox-flash")
        self.assertEqual(payload["quality"], "speed")
        self.assertIn("Wide establishing shot", payload["prompt"])


if __name__ == "__main__":
    unittest.main()
