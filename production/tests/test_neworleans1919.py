"""离线自检：《新奥尔良斧头杀手》的分镜、提示词拼装、旁白与安全边界。

不联网、不调模型：只守「能离线判定的东西」——
30 镜 / 180 秒 / 5–7 秒网格 / 24fps、STYLE 与 NEGATIVE 自动拼接、角色锚点逐字复用、
每镜都有真实运镜与真实运动的描述、每镜引用已定稿的参考图且模式是 reference、
双色调只在允许的段落里切换、旁白一镜一句且语速落在 3.6–3.9 字/秒附近、
事实边界与「不出现遗体/孩子/面容」的规则写在数据里。
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
PROJECT = ROOT / "production" / "neworleans1919"
JAZZ_SHOTS = {"S01", "S02", "S19", "S20", "S21", "S22", "S30"}


def load_generate():
    """按路径加载本项目 generate.py，避免和仓库里别的同名模块串味。"""
    stashed = {name: sys.modules.pop(name) for name in ("generate", "throttle", "agnes_video")
               if name in sys.modules}
    path_snapshot = list(sys.path)
    sys.path.insert(0, str(ROOT / "production"))
    spec = importlib.util.spec_from_file_location("neworleans1919_generate", PROJECT / "generate.py")
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
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def visible(text: str) -> int:
    return len(re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", text))


class NewOrleansPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
        cls.gen = load_generate()

    def test_30_shots_cover_exactly_180_seconds(self):
        shots = self.story["shots"]
        self.assertEqual(len(shots), 30)
        self.assertEqual(sum(shot["duration"] for shot in shots), 180)
        self.assertEqual((self.story["width"], self.story["height"], self.story["fps"]), (1920, 1080, 24))
        self.assertEqual(self.story["model"], "agnes-video-2.5-flash")
        self.assertEqual(self.story["source_size"], "720P")
        self.assertEqual(self.story["branch"], "arena/eb3c7fec-desktop-tutorial")
        cursor = 0
        for shot in shots:
            self.assertEqual(shot["start"], cursor)
            self.assertGreaterEqual(shot["duration"], 5)
            self.assertLessEqual(shot["duration"], 7)
            self.assertEqual(shot["kind"], "agnes")
            self.assertEqual(shot["seconds"], shot["duration"])
            self.assertEqual(shot["aspect"], "16:9")
            cursor += shot["duration"]
        self.assertEqual(cursor, 180)

    def test_every_prompt_gets_style_characters_references_and_negative(self):
        # 参考图指向不可变提交：给测试一个合法的 revision，不去碰真实接口
        original = self.gen.REFERENCE_REVISION
        self.gen.REFERENCE_REVISION = "0" * 40
        try:
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
                    for index in range(1, len(shot["references"]) + 1):
                        self.assertIn(f"<Picture {index}>", prompt)
        finally:
            self.gen.REFERENCE_REVISION = original

    def test_reference_images_are_declared_and_published(self):
        declared = {ref["id"] for ref in self.story["reference_images"]}
        self.assertEqual(declared, {"C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09",
                                    "SC01", "SC02", "SC03", "SC04", "SC05", "SC06", "SC07", "SC08",
                                    "SC09", "SC10", "P01", "P02", "P03", "P04", "P05"})
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                self.assertTrue(1 <= len(shot["references"]) <= 5)
                self.assertTrue(set(shot["references"]).issubset(declared))
                self.assertEqual(len(set(shot["references"])), len(shot["references"]))
        # 定稿图必须真实入库（>20 KB），否则 reference 模式会把空图喂给模型
        for ref in self.story["reference_images"]:
            path = PROJECT / ref["file"]
            self.assertTrue(path.is_file(), ref["file"])
            self.assertGreater(path.stat().st_size, 20_000, ref["file"])

    def test_reference_revision_is_an_immutable_commit_when_recorded(self):
        revision_file = PROJECT / "reference" / "revision.txt"
        if not revision_file.is_file():
            self.skipTest("参考图尚未发布：先提交定稿图并写入 reference/revision.txt")
        self.assertRegex(revision_file.read_text(encoding="utf-8").strip(), r"^[0-9a-f]{40}$")

    def test_payload_uses_reference_mode_with_approved_images(self):
        original = self.gen.REFERENCE_REVISION
        self.gen.REFERENCE_REVISION = "a" * 40
        try:
            shot = self.story["shots"][0]
            payload = self.gen.full_payload(self.story, shot)
            self.assertEqual(set(payload), self.gen.ALLOWED_PAYLOAD_FIELDS)
            self.assertEqual(payload["mode"], "reference")
            self.assertEqual(payload["n"], 1)
            self.assertEqual(payload["size"], "720P")
            self.assertEqual(payload["aspect_ratio"], "16:9")
            self.assertIsInstance(payload["seconds"], str)
            self.assertEqual(len(payload["images"]), len(shot["references"]))
            for url in payload["images"]:
                self.assertTrue(url.startswith(
                    "https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/" + "a" * 40))
                self.assertIn("/production/neworleans1919/reference/", url)
        finally:
            self.gen.REFERENCE_REVISION = original

    def test_every_shot_demands_real_camera_motion(self):
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                text = shot["prompt"]
                self.assertIn("Camera:", text)
                self.assertRegex(text.lower(), r"real motion|rotates|drifting|turning")
                self.assertGreater(len(text), 300)

    def test_two_tone_palette_only_flips_where_scripted(self):
        for shot in self.story["shots"]:
            expected = "jazz" if shot["id"] in JAZZ_SHOTS else "fear"
            self.assertEqual(shot["style_variant"], expected, shot["id"])
            style = self.gen.style_for(self.story, shot)
            if expected == "jazz":
                self.assertIn("爵士之夜", style)
                self.assertIn("warm gold", style.lower())
            else:
                self.assertIn("FEAR PALETTE", style)
        jazz_chapters = {c["id"] for c in self.story["chapters"] if c["tone"] == "jazz"}
        self.assertEqual(jazz_chapters, {"N1", "N6", "N9"})

    def test_sensitive_imagery_is_never_requested(self):
        banned = re.compile(r"\b(corpse|dead body|blood splatter|gore|bloody|stabbing|"
                            r"swinging the axe|axe strike|clear face of the killer)\b", re.I)
        footage = " ".join(shot["prompt"] for shot in self.story["shots"])
        self.assertIsNone(banned.search(footage))
        # 受害者与孩子不入画：只有物件和空镜的暗示
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                lowered = shot["prompt"].lower()
                self.assertNotIn("child", lowered)
                self.assertNotIn("children", lowered)
                self.assertNotIn("infant", lowered)
                self.assertNotIn("baby", lowered)
        self.assertIn("victim", self.story["negative_prompt"].lower())
        self.assertIn("child in distress", self.story["negative_prompt"])
        self.assertIn("no face", self.story["characters"]["axeman"].lower())
        # 斧头只能是影子、剪影或静物
        self.assertIn("never swung", self.story["characters"]["axeman"])

    def test_single_character_shots_use_a_fixed_per_character_seed(self):
        seen = {}
        for shot in self.story["shots"]:
            if len(shot["characters"]) == 1:
                role = shot["characters"][0]
                seed = self.gen.payload_seed(self.story, shot)
                self.assertEqual(seed, self.story["character_seeds"][role])
                seen.setdefault(role, set()).add(seed)
        for role, seeds in seen.items():
            self.assertEqual(len(seeds), 1, role)
        self.assertIn("axeman", seen)
        self.assertIn("detective", seen)
        # 黑影在独镜里必须复用同一个 seed；双人镜头的 seed 由镜头序号决定（另一条一致性路径）
        axeman_solo = {self.gen.payload_seed(self.story, shot) for shot in self.story["shots"]
                       if shot["characters"] == ["axeman"]}
        self.assertEqual(axeman_solo, {self.story["character_seeds"]["axeman"]})

    def test_narration_is_one_line_per_shot_at_the_scripted_pace(self):
        self.assertEqual(len(self.story["shots"]),
                         len({shot["narration"] for shot in self.story["shots"]}))
        self.assertEqual(self.story["narration_spec"]["target_chars_per_second"], 3.7)
        total = sum(visible(shot["narration"]) for shot in self.story["shots"])
        self.assertGreater(total, 540)
        self.assertLess(total / 180.0, 3.9)
        for shot in self.story["shots"]:
            chars = visible(shot["narration"])
            cps = chars / shot["duration"]
            with self.subTest(shot=shot["id"]):
                self.assertGreater(cps, 1.9, "旁白太短，镜头会空着")
                self.assertLessEqual(cps, 4.2, "旁白太密，必须加速才能塞进镜头")

    def test_caption_lines_stay_within_the_two_line_limit(self):
        render = load_module("neworleans1919_render", PROJECT / "render.py")
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                lines = render.split_caption(shot["narration"])
                self.assertLessEqual(len(lines), 2)
                self.assertTrue(all(len(line) <= 26 for line in lines))

    def test_narration_fit_verdicts(self):
        fit = load_module("neworleans1919_narration_fit", PROJECT / "narration_fit.py")
        self.assertEqual(fit.classify(0.92, 1.00, 1.55), "fit")
        self.assertEqual(fit.classify(0.75, 1.00, 1.55), "ok")
        self.assertEqual(fit.classify(0.46, 1.00, 1.55), "short")
        self.assertEqual(fit.classify(1.12, 1.12, 1.55), "needs-speedup")
        self.assertEqual(fit.classify(1.60, 1.60, 1.55), "over")

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

    def test_hook_and_ending_are_built_in(self):
        first_two = self.story["shots"][:2]
        self.assertTrue(all(shot["style_variant"] == "jazz" for shot in first_two))
        self.assertIn("爵士乐", "".join(shot["narration"] for shot in first_two))
        self.assertIn("斧头不会落下", self.story["presentation"]["cover"]["text"])
        self.assertTrue(self.story["shots"][-1]["narration"].strip().endswith("？"))
        self.assertIn("斧头不会落下", self.story["shots"][1]["narration"])
        # 字幕大字（开头钩子的那句）必须真的出现在旁白里
        self.assertIn("放爵士的家，斧头不会落下", self.story["shots"][1]["narration"])

    def test_sources_and_fact_boundaries_are_recorded(self):
        self.assertGreaterEqual(len(self.story["sources"]), 5)
        self.assertTrue(all(source["url"].startswith("https://") for source in self.story["sources"]))
        boundary = "\n".join(self.story["fact_boundary"])
        for keyword in ("1918年5月", "1919年3月10日", "1919年3月13日", "1919年10月27日",
                        "至今未破", "传闻", "不出现遗体"):
            self.assertIn(keyword, boundary)
        principles = "\n".join(self.story["principles"])
        for keyword in ("双色调", "黑影", "不入画", "一镜一句"):
            self.assertIn(keyword, principles)

    def test_publish_delivery_copies_the_named_four(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clips = root / "clips"
            (clips / "delivery").mkdir(parents=True)
            film = clips / "成片.mp4"
            film.write_bytes(b"film" * 1000)
            (clips / "新奥尔良斧头杀手_封面.jpg").write_bytes(b"cover" * 100)
            (clips / "新奥尔良斧头杀手_封面.png").write_bytes(b"cover" * 100)
            (clips / "成片_字幕.srt").write_text("1\n00:00:00,000 --> 00:00:04,000\n字幕\n", encoding="utf-8")
            (clips / "delivery" / "technical-report.json").write_text("{}", encoding="utf-8")
            audio = root / "work" / "neworleans1919" / "audio"
            audio.mkdir(parents=True)
            (audio / "voiceover.wav").write_bytes(b"RIFF" * 500)
            delivery = root / "交付"
            original_delivery, original_root = self.gen.DELIVERY_DIR, self.gen.ROOT
            try:
                self.gen.DELIVERY_DIR = delivery
                self.gen.ROOT = root
                copied = self.gen.publish_delivery(film)
            finally:
                self.gen.DELIVERY_DIR = original_delivery
                self.gen.ROOT = original_root
            for name in ("NewOrleans1919_Final.mp4", "NewOrleans1919_Cover.png",
                         "NewOrleans1919_Subtitles.srt", "NewOrleans1919_Narration.wav"):
                self.assertIn(name, copied)
                self.assertTrue((delivery / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
