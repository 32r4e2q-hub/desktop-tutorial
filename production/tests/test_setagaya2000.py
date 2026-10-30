"""离线自检：世田谷一家四口的分镜、提示词拼装与旁白清单。

不联网、不调模型：只守「能离线判定的东西」——
29 镜 / 180 秒 / 4–9 秒网格 / 24fps、STYLE 与 NEGATIVE 自动拼接、角色设定逐字复用、
每镜都有真实运镜与真实运动的描述、抽象示意图用独立 STYLE、单角色镜头固定 seed、
旁白一镜一句且语速合理、参考图齐备。
配音文件齐了以后，``generate.py --validate`` 还会再验 SHA-256 与时长。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "setagaya2000"


def load_generate():
    """按路径加载本项目 generate.py，避免和仓库里别的同名模块串味。"""
    stashed = {name: sys.modules.pop(name) for name in ("generate", "throttle", "agnes_video")
               if name in sys.modules}
    path_snapshot = list(sys.path)
    sys.path.insert(0, str(ROOT / "production"))
    spec = importlib.util.spec_from_file_location("setagaya2000_generate", PROJECT / "generate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
        sys.modules.update(stashed)
        sys.path[:] = path_snapshot
    return module


def load_module(name: str, path: Path):
    """按路径加载单个模块（不执行它的副作用），用于纯函数单测。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SetagayaPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
        cls.gen = load_generate()

    def test_29_shots_cover_exactly_180_seconds(self):
        shots = self.story["shots"]
        self.assertEqual(len(shots), 29)
        self.assertEqual(sum(shot["duration"] for shot in shots), 180)
        self.assertEqual((self.story["width"], self.story["height"], self.story["fps"]), (1920, 1080, 24))
        self.assertEqual(self.story["model"], "agnes-video-2.5-flash")
        self.assertEqual(self.story["source_size"], "720P")
        cursor = 0
        for shot in shots:
            self.assertEqual(shot["start"], cursor)
            self.assertGreaterEqual(shot["duration"], 4)
            self.assertLessEqual(shot["duration"], 9)
            self.assertEqual(shot["kind"], "agnes")
            self.assertEqual(shot["seconds"], shot["duration"])
            self.assertEqual(shot["aspect"], "16:9")
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
                expected = (self.story["style_rumor_prefix"] if shot["style_variant"] == "diagram"
                            else self.story["style_prefix"]).strip()
                self.assertTrue(prompt.startswith(expected))

    def test_every_shot_demands_real_camera_motion(self):
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                text = shot["prompt"]
                self.assertIn("Camera:", text)
                self.assertRegex(text.lower(), r"real motion|rotates|drifting|draw themselves")
                self.assertGreater(len(text), 240)

    def test_diagram_shots_use_their_own_style_and_carry_no_lettering(self):
        diagram = [shot for shot in self.story["shots"] if shot["style_variant"] == "diagram"]
        self.assertEqual([shot["id"] for shot in diagram], ["S13", "S19", "S22", "S25"])
        for shot in diagram:
            style = self.gen.style_for(self.story, shot).lower()
            self.assertIn("information graphic", style)
            self.assertIn("no readable letters", shot["prompt"].lower())

    def test_sensitive_imagery_is_never_requested(self):
        banned = re.compile(r"\b(corpse|dead body|blood splatter|gore|murder the|stabbing|"
                            r"clear face of the suspect)\b", re.I)
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                self.assertIsNone(banned.search(shot["prompt"]))
        silhouette = next(shot for shot in self.story["shots"] if "silhouette" in shot["characters"])
        self.assertIn("no visible face", self.story["characters"]["silhouette"])

    def test_single_character_shots_reuse_the_character_seed(self):
        seen = {}
        for shot in self.story["shots"]:
            if len(shot["characters"]) == 1:
                role = shot["characters"][0]
                seed = self.gen.payload_seed(self.story, shot)
                self.assertEqual(seed, self.story["character_seeds"][role])
                seen.setdefault(role, set()).add(seed)
        for role, seeds in seen.items():
            self.assertEqual(len(seeds), 1, role)
        self.assertIn("silhouette", seen)
        self.assertIn("detective", seen)

    def test_narration_is_one_line_per_shot_at_a_human_pace(self):
        self.assertEqual(len(self.story["shots"]), len({shot["narration"] for shot in self.story["shots"]}))
        total = 0
        for shot in self.story["shots"]:
            characters = sum(1 for ch in shot["narration"] if ch.isalnum() or "\u3400" <= ch <= "\u9fff")
            total += characters
            with self.subTest(shot=shot["id"]):
                self.assertGreater(characters, 0)
                self.assertLessEqual(characters / shot["duration"], 4.8)
        self.assertGreater(total, 600)
        self.assertLess(total / 180.0, 4.2)

    def test_narration_length_matches_shot_length(self):
        """解说词跟片段等长：字数 ÷ 镜头秒数必须落在人类语速区间，且不靠加速凑。"""
        story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
        for shot in story["shots"]:
            chars = len(re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", shot["narration"]))
            cps = chars / shot["duration"]
            self.assertGreaterEqual(cps, 1.0, f"{shot['id']} 旁白太短，镜头会空着：{cps:.2f} 字/秒")
            self.assertLessEqual(cps, 4.45, f"{shot['id']} 旁白太密，必须加速才能塞进镜头：{cps:.2f} 字/秒")
        self.assertEqual(sum(1 for s in story["shots"] if s["duration"] in (4, 5, 6, 7, 8, 9)),
                         len(story["shots"]), "镜头时长必须落在 Agnes 2.5 Flash 的 4–9 秒档位")

    def test_narration_fit_verdicts(self):
        """narration_fit 的判定边界：只有超过 1.55× 上限才算不合格。"""
        fit = load_module("setagaya2000_narration_fit", PROJECT / "narration_fit.py")
        self.assertEqual(fit.classify(0.92, 1.00, 1.55), "fit")
        self.assertEqual(fit.classify(0.75, 1.00, 1.55), "ok")
        self.assertEqual(fit.classify(0.46, 1.00, 1.55), "short")
        self.assertEqual(fit.classify(1.12, 1.12, 1.55), "needs-speedup")
        self.assertEqual(fit.classify(1.60, 1.60, 1.55), "over")
        self.assertEqual(fit.classify(1.55, 1.55, 1.55), "needs-speedup")

    def test_chapters_are_nine_and_contiguous(self):
        chapters = self.story["chapters"]
        self.assertEqual(len(chapters), 9)
        cursor = 0
        covered = []
        for chapter in chapters:
            self.assertEqual(chapter["start"], cursor)
            self.assertEqual(chapter["duration"], sum(
                shot["duration"] for shot in self.story["shots"] if shot["id"] in chapter["shot_ids"]))
            self.assertTrue(chapter["text"].strip())
            covered += chapter["shot_ids"]
            cursor += chapter["duration"]
        self.assertEqual(cursor, 180)
        self.assertEqual(covered, [shot["id"] for shot in self.story["shots"]])

    def test_reference_images_exist(self):
        for ref in self.story["reference_images"]:
            path = PROJECT / ref["file"]
            self.assertTrue(path.is_file(), ref["file"])
            self.assertGreater(path.stat().st_size, 20_000, ref["file"])

    def test_fresh_runner_can_restore_footage_from_receipts(self):
        """出片任务跑在新 checkout 上：work/ 是空的，只能凭 results 里的收据重下并逐字节校验。"""
        import hashlib
        import tempfile

        story = {"shots": self.story["shots"][:3]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            originals, sources = root / "originals", root / "sources"
            originals.mkdir()
            sources.mkdir()
            doc = {"shots": {}}
            for index, shot in enumerate(story["shots"]):
                blob = (f"agnes-fake-{index:02d}-".encode() * 9000)
                original = originals / f"{shot['id']}.mp4"
                original.write_bytes(blob)
                doc["shots"][shot["id"]] = {
                    "status": "completed", "video_url": original.as_uri(),
                    "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
                }
            (sources / "S01.mp4").write_bytes(b"corrupt partial download")
            self.assertEqual(self.gen.restore_sources(story, doc, sources), ["S01", "S02", "S03"])
            self.assertEqual(self.gen.restore_sources(story, doc, sources), [])
            doc["shots"]["S02"]["sha256"] = "0" * 64
            with self.assertRaises(RuntimeError):
                self.gen.restore_sources(story, doc, sources)

    def test_finished_film_cover_and_named_deliverables_are_published(self):
        """成片不能只躺在被忽略的 work/ 里：四份指定文件 + 仓库命名的交付一起进 交付/。"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clips = root / "clips"
            (clips / "delivery").mkdir(parents=True)
            film = clips / "成片.mp4"
            film.write_bytes(b"film" * 1000)
            (clips / "世田谷一家四口杀人案_封面.jpg").write_bytes(b"cover" * 100)
            (clips / "世田谷一家四口杀人案_封面.png").write_bytes(b"cover" * 100)
            (clips / "成片_字幕.srt").write_text("1\n00:00:00,000 --> 00:00:04,000\n字幕\n", encoding="utf-8")
            (clips / "delivery" / "technical-report.json").write_text("{}", encoding="utf-8")
            audio = root / "work" / "setagaya2000" / "audio"
            audio.mkdir(parents=True)
            (audio / "voiceover.wav").write_bytes(b"RIFF" * 500)
            delivery = root / "交付"

            original_delivery = self.gen.DELIVERY_DIR
            original_root = self.gen.ROOT
            try:
                self.gen.DELIVERY_DIR = delivery
                self.gen.ROOT = root
                copied = self.gen.publish_delivery(film)
            finally:
                self.gen.DELIVERY_DIR = original_delivery
                self.gen.ROOT = original_root
            for name in ("Setagaya_Case_Final.mp4", "Setagaya_Cover.png",
                         "Setagaya_Subtitles.srt", "Setagaya_Narration.wav"):
                self.assertIn(name, copied)
                self.assertTrue((delivery / name).is_file(), name)

    def test_sources_and_fact_boundaries_are_recorded(self):
        self.assertGreaterEqual(len(self.story["sources"]), 5)
        self.assertTrue(all(source["url"].startswith("https://") for source in self.story["sources"]))
        self.assertTrue(any("警视庁" in source["title"] for source in self.story["sources"]))
        boundary = "\n".join(self.story["fact_boundary"])
        for keyword in ("2000年12月30日", "宫泽干男", "至今未侦破", "3D示意性复原"):
            self.assertIn(keyword, boundary)


if __name__ == "__main__":
    unittest.main()
