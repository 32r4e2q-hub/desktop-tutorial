"""离线自检：铅面具事件的分镜、提示词拼装与旁白清单。

不联网、不调模型：只守「能离线判定的东西」——
29 镜 / 180 秒 / 4–9 秒网格、STYLE 与 NEGATIVE 自动拼接、角色设定逐字复用、
传闻镜头用泛黄手绘 STYLE、单角色镜头固定 seed、旁白一镜一句且与清单一致。
配音文件齐了以后，``generate.py --validate`` 还会再验 SHA-256 与时长。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "leadmask1966"


def load_generate():
    """按路径加载本项目 generate.py，避免和仓库里别的同名模块串味。"""
    stashed = {name: sys.modules.pop(name) for name in ("generate", "throttle", "agnes_video")
               if name in sys.modules}
    path_snapshot = list(sys.path)
    sys.path.insert(0, str(ROOT / "production"))
    spec = importlib.util.spec_from_file_location("leadmask1966_generate", PROJECT / "generate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
        sys.modules.update(stashed)
        sys.path[:] = path_snapshot
    return module


class LeadMaskPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
        cls.gen = load_generate()

    def test_29_shots_cover_exactly_180_seconds(self):
        shots = self.story["shots"]
        self.assertEqual(len(shots), 29)
        self.assertEqual(sum(shot["duration"] for shot in shots), 180)
        self.assertEqual((self.story["width"], self.story["height"], self.story["fps"]), (1920, 1080, 30))
        cursor = 0
        for shot in shots:
            self.assertEqual(shot["start"], cursor)
            self.assertGreaterEqual(shot["duration"], 4)
            self.assertLessEqual(shot["duration"], 9)
            self.assertEqual(shot["kind"], "agnes")
            self.assertEqual(shot["aspect"], "16:9")
            self.assertEqual(shot["seconds"], shot["duration"])
            cursor += shot["duration"]
        self.assertEqual(cursor, 180)

    def test_every_prompt_gets_style_characters_and_negative(self):
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                prompt = self.gen.full_prompt(self.story, shot)
                self.assertTrue(prompt.startswith("【STYLE"), prompt[:40])
                self.assertTrue(prompt.endswith(self.story["negative_prompt"].strip()))
                self.assertIn(shot["prompt"], prompt)
                for role in shot["characters"]:
                    token = self.story["characters"][role].strip()
                    self.assertIn(token, prompt)
                    self.assertLess(prompt.index(token), prompt.index(shot["prompt"]))
                expected = (self.story["style_rumor_prefix"] if shot["style_variant"] == "rumor"
                            else self.story["style_prefix"]).strip()
                self.assertTrue(prompt.startswith(expected))

    def test_rumor_shots_are_hand_drawn_and_labelled(self):
        rumor = [shot for shot in self.story["shots"] if shot["style_variant"] == "rumor"]
        self.assertEqual([shot["id"] for shot in rumor], ["S20", "S22", "S23", "S24", "S25"])
        for shot in rumor:
            self.assertIn("hand-drawn", self.gen.style_for(self.story, shot).lower())

    def test_single_character_shots_reuse_the_character_seed(self):
        seen = {}
        for shot in self.story["shots"]:
            if len(shot["characters"]) == 1:
                role = shot["characters"][0]
                seed = self.gen.payload_seed(self.story, shot)
                self.assertEqual(seed, self.story["character_seeds"][role])
                seen.setdefault(role, set()).add(seed)
        self.assertIn("miguel", seen)
        self.assertIn("manuel", seen)
        for role, seeds in seen.items():
            self.assertEqual(len(seeds), 1, role)

    def test_validation_runs_without_voice_before_tts(self):
        self.gen.validate(self.story, require_audio=False)

    def test_shot_narration_matches_the_manifest_when_present(self):
        manifest_path = PROJECT / "audio" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        records = {row["id"]: row for row in manifest["clips"]}
        self.assertEqual(len(records), len(self.story["shots"]))
        for shot in self.story["shots"]:
            row = records[shot["id"]]
            self.assertEqual(row["text"], shot["narration"])
            self.assertEqual(row["narration_id"], shot["narration_id"])
            self.assertEqual(row["target_start"], shot["start"])
            self.assertEqual(row["target_duration"], shot["duration"])
            self.assertEqual(row["alignment"], "shot-locked")

    def test_narration_pace_stays_inside_the_speedup_budget(self):
        def visible(text: str) -> int:
            return sum(1 for ch in text if ch.isalnum() or "\u3400" <= ch <= "\u9fff")

        total = 0
        for shot in self.story["shots"]:
            chars = visible(shot["narration"])
            total += chars
            # 慢速 TTS 实测下限约 2.6 字/秒；1.55 倍上限意味着每镜不能超过 4.0 字/秒。
            self.assertLessEqual(chars / shot["duration"], 4.05,
                                 f"{shot['id']} 的旁白太长，会被迫超过 1.55 倍加速")
            self.assertGreater(chars, 8, f"{shot['id']} 的旁白太短")
        self.assertGreaterEqual(total, 500, "全片旁白少于 500 字，节奏会散")
        self.assertLessEqual(total / 180, 3.9, "全片语速超过每秒 3.9 字")

    def test_reference_images_and_post_overlays_are_defined(self):
        for reference in self.story["reference_images"]:
            self.assertTrue((PROJECT / reference["file"]).is_file(), reference["file"])
        presentation = self.story["presentation"]
        self.assertEqual(presentation["end_title"], "铅面具事件")
        self.assertEqual(presentation["cover"]["text"], "铅面具")
        self.assertIn("至今未解", presentation["end_subtitle"])
        self.assertIn("十六点三十", presentation["highlight_keywords"])
        self.assertEqual(self.story["narration_spec"]["max_speedup_factor"], 1.55)
        self.assertFalse(self.story["narration_spec"]["slowdown_allowed"])


if __name__ == "__main__":
    unittest.main()
