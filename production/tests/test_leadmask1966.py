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
            self.assertEqual(self.gen.restore_sources(story, doc, sources),
                             ["S01", "S02", "S03"])
            self.assertEqual(self.gen.restore_sources(story, doc, sources), [])
            doc["shots"]["S02"]["sha256"] = "0" * 64
            with self.assertRaises(RuntimeError):
                self.gen.restore_sources(story, doc, sources)

    def test_finished_film_cover_and_subtitles_reach_the_delivery_folder(self):
        """成片不能只躺在被忽略的 work/ 里：交付约定是 交付/ 下的 mp4 + 封面 + 字幕。"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clips = root / "clips"
            (clips / "delivery").mkdir(parents=True)
            film = clips / "成片.mp4"
            film.write_bytes(b"film" * 1000)
            (clips / "铅面具事件_封面.jpg").write_bytes(b"cover" * 100)
            (clips / "成片_字幕.srt").write_text(
                "1\n00:00:00,000 --> 00:00:04,000\n字幕\n", encoding="utf-8")
            (clips / "delivery" / "technical-report.json").write_text("{}", encoding="utf-8")
            original = self.gen.DELIVERY_DIR
            self.gen.DELIVERY_DIR = root / "交付"
            try:
                copied = self.gen.publish_delivery(film)
            finally:
                self.gen.DELIVERY_DIR = original
            self.assertIn(self.gen.DELIVERY_FILM, copied)
            self.assertIn("铅面具事件_封面.jpg", copied)
            self.assertIn("铅面具事件_字幕.srt", copied)
            self.assertEqual((root / "交付" / self.gen.DELIVERY_FILM).read_bytes(), film.read_bytes())

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

    def test_narration_fills_every_shot_without_rushing(self):
        """解说要跟片段等长：每镜的字数按该镜时长配比，既不留大段空白，也不靠加速硬塞。"""

        def visible(text: str) -> int:
            return sum(1 for ch in text if ch.isalnum() or "\u3400" <= ch <= "\u9fff")

        # voice-01 实测语速：短句约 3.38 字/秒，长句约 4.06 字/秒。
        slowest, fastest = 3.38, 4.06
        total = 0
        for shot in self.story["shots"]:
            chars = visible(shot["narration"])
            total += chars
            available = shot["duration"] - 0.08
            self.assertLessEqual(
                chars / fastest, available,
                f"{shot['id']} 按实测最快语速也超出镜头，只能靠加速硬塞")
            self.assertGreaterEqual(
                chars / slowest, available * 0.78,
                f"{shot['id']} 即使按最慢语速也填不满镜头，会留下大段空白")
        self.assertGreaterEqual(total, 580, "全片解说不足以填满镜头")
        self.assertGreaterEqual(total / 180, 3.2, "全片语速过慢，会出现大段空白")
        self.assertLessEqual(total / 180, 3.6, "全片语速过快，配音会被迫加速")

    def test_each_line_matches_its_own_shot(self):
        """一镜一句、句子互不重复，且镜头内出现的物件与人物要在这一句里有着落。"""
        lines = [shot["narration"] for shot in self.story["shots"]]
        self.assertEqual(len(lines), len(set(lines)), "有重复的旁白句子")
        expectations = {
            "S07": ["文廷山"], "S08": ["少年"], "S09": ["躺着"], "S13": ["眼罩"],
            "S14": ["十六点三十", "十八点三十"], "S16": ["枪伤"], "S17": ["放射性"],
            "S19": ["渔民"], "S20": ["外星人"], "S22": ["传闻"], "S23": ["胶囊"],
            "S24": ["飞碟", "上山"], "S25": ["一个也没有被证实"], "S27": ["妻子"],
            "S28": ["信号"], "S29": ["评论区"],
        }
        by_id = {shot["id"]: shot["narration"] for shot in self.story["shots"]}
        for sid, needles in expectations.items():
            for needle in needles:
                self.assertIn(needle, by_id[sid], f"{sid} 的解说没有说到画面里的内容：{needle}")

    def test_reference_images_and_post_overlays_are_defined(self):
        for reference in self.story["reference_images"]:
            self.assertTrue((PROJECT / reference["file"]).is_file(), reference["file"])
        presentation = self.story["presentation"]
        self.assertEqual(presentation["end_title"], "铅面具事件")
        self.assertEqual(presentation["cover"]["text"], "铅面具")
        self.assertIn("至今未解", presentation["end_subtitle"])
        self.assertIn("十六点三十", presentation["highlight_keywords"])
        narration = "".join(shot["narration"] for shot in self.story["shots"])
        for keyword in presentation["highlight_keywords"]:
            self.assertIn(keyword, narration, f"高亮词在台词里找不到：{keyword}")
        self.assertEqual(self.story["narration_spec"]["max_speedup_factor"], 1.55)
        self.assertFalse(self.story["narration_spec"]["slowdown_allowed"])


if __name__ == "__main__":
    unittest.main()
