"""离线自检：《山姆之子：一张25美元的罚单》的分镜、提示词拼装、旁白与安全边界。

不联网、不调模型：只守「能离线判定的东西」——
30 镜 / 180 秒 / 5–7 秒网格 / 24fps、三色调 STYLE 与 NEGATIVE 自动拼接、角色锚点逐字复用、
每镜都有真实运镜与真实运动的描述、每镜引用已定稿的参考图且模式是 reference、
三色调只在脚本规定的段落切换、旁白一镜一句且语速落在 1.9–4.2 字/秒、
事实边界与「不出现遗体/开枪/受害者特写」的规则写在数据里。
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
PROJECT = ROOT / "production" / "sonofsam1977"
CHASE_SHOTS = {"S12", "S13", "S14", "S19", "S20", "S21", "S22", "S25"}
GOLD_SHOTS = {"S29", "S30"}


def load_generate():
    """按路径加载本项目 generate.py，避免和仓库里别的同名模块串味。"""
    stashed = {name: sys.modules.pop(name) for name in ("generate", "throttle", "agnes_video")
               if name in sys.modules}
    path_snapshot = list(sys.path)
    sys.path.insert(0, str(ROOT / "production"))
    spec = importlib.util.spec_from_file_location("sonofsam1977_generate", PROJECT / "generate.py")
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


class SonOfSamPlanTests(unittest.TestCase):
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
        self.assertEqual(self.story["branch"], "arena/e455e5b7-desktop-tutorial")
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
        self.assertEqual(declared, {"C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10",
                                    "SC01", "SC02", "SC03", "SC04", "SC05", "SC06", "SC07", "SC08",
                                    "SC09", "SC10"})
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
                self.assertIn("/production/sonofsam1977/reference/", url)
        finally:
            self.gen.REFERENCE_REVISION = original

    def test_every_shot_demands_real_camera_motion(self):
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                text = shot["prompt"]
                self.assertIn("Camera:", text)
                self.assertRegex(text.lower(), r"real motion|drifting|tumbling|pushing|rising")
                self.assertGreater(len(text), 300)

    def test_three_tone_palette_only_flips_where_scripted(self):
        for shot in self.story["shots"]:
            if shot["id"] in GOLD_SHOTS:
                expected = "gold"
            elif shot["id"] in CHASE_SHOTS:
                expected = "chase"
            else:
                expected = "night"
            self.assertEqual(shot["style_variant"], expected, shot["id"])
            style = self.gen.style_for(self.story, shot)
            if expected == "gold":
                self.assertIn("GOLD PALETTE", style)
            elif expected == "chase":
                self.assertIn("CHASE PALETTE", style)
            else:
                self.assertIn("NIGHT PALETTE", style)
        gold_chapters = {c["id"] for c in self.story["chapters"] if c["tone"] == "gold"}
        chase_chapters = {c["id"] for c in self.story["chapters"] if c["tone"] == "chase"}
        self.assertEqual(gold_chapters, {"N9"})
        self.assertEqual(chase_chapters, {"N4", "N6"})

    def test_sensitive_imagery_is_never_requested(self):
        banned = re.compile(r"\b(corpse|dead body|blood splatter|gore|bloody|shooting|gunshot|"
                            r"muzzle flash|firing|shot fired|clear face of the killer|"
                            r"victim close-up|victim in frame)\b", re.I)
        footage = " ".join(shot["prompt"] for shot in self.story["shots"])
        self.assertIsNone(banned.search(footage))
        # 枪支规则：提示词里不允许出现开枪/枪口火光；黑影设定里明确不举枪
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                lowered = shot["prompt"].lower()
                self.assertNotIn("muzzle flash", lowered)
                self.assertNotIn("gunshot", lowered)
                self.assertNotIn("shooting", lowered)
        self.assertIn("shooting", self.story["negative_prompt"].lower())
        self.assertIn("gunshot", self.story["negative_prompt"].lower())
        self.assertIn("victim close-up", self.story["negative_prompt"].lower())
        self.assertIn("never raised, never fired", self.story["characters"]["shadow"])
        self.assertIn("face completely hidden in shadow", self.story["characters"]["shadow"].lower())

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
        self.assertIn("shadow", seen)
        self.assertIn("berkowitz", seen)
        # 黑影在独镜里必须复用同一个 seed；双人镜头的 seed 由镜头序号决定（另一条一致性路径）
        shadow_solo = {self.gen.payload_seed(self.story, shot) for shot in self.story["shots"]
                       if shot["characters"] == ["shadow"]}
        self.assertEqual(shadow_solo, {self.story["character_seeds"]["shadow"]})

    def test_narration_is_one_line_per_shot_at_the_scripted_pace(self):
        self.assertEqual(len(self.story["shots"]),
                         len({shot["narration"] for shot in self.story["shots"]}))
        self.assertEqual(self.story["narration_spec"]["target_chars_per_second"], 3.7)
        total = sum(visible(shot["narration"]) for shot in self.story["shots"])
        self.assertGreater(total, 500)
        self.assertLess(total / 180.0, 3.9)
        for shot in self.story["shots"]:
            chars = visible(shot["narration"])
            cps = chars / shot["duration"]
            with self.subTest(shot=shot["id"]):
                self.assertGreater(cps, 1.9, "旁白太短，镜头会空着")
                self.assertLessEqual(cps, 4.2, "旁白太密，必须加速才能塞进镜头")

    def test_caption_lines_stay_within_the_two_line_limit(self):
        render = load_module("sonofsam1977_render", PROJECT / "render.py")
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                lines = render.split_caption(shot["narration"])
                self.assertLessEqual(len(lines), 2)
                self.assertTrue(all(len(line) <= 26 for line in lines))

    def test_narration_fit_verdicts(self):
        fit = load_module("sonofsam1977_narration_fit", PROJECT / "narration_fit.py")
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
        # 开头钩子：前两镜亮出罚单
        first_two = self.story["shots"][:2]
        self.assertTrue(all(shot["style_variant"] == "night" for shot in first_two))
        self.assertIn("罚单", "".join(shot["narration"] for shot in first_two))
        self.assertIn("一张罚单", self.story["presentation"]["cover"]["text"])
        # 结尾：最后一镜是暖金罚单特写，旁白收在「小罚单/大案子」，并抛互动提问
        self.assertEqual(self.story["shots"][-1]["style_variant"], "gold")
        self.assertIn("罚单", self.story["shots"][-1]["narration"])
        self.assertIn("大案子", self.story["shots"][-1]["narration"])
        self.assertTrue(self.story["presentation"]["end_question"].strip().endswith("？"))
        # 罚单视觉符号首尾呼应：S01/S02 亮相（罚单/黄车场景），S30 回到罚单桌面
        for sid in ("S01", "S02", "S30"):
            shot = next(s for s in self.story["shots"] if s["id"] == sid)
            self.assertTrue({"SC01", "SC03", "SC10"} & set(shot["references"]), sid)

    def test_sources_and_fact_boundaries_are_recorded(self):
        self.assertGreaterEqual(len(self.story["sources"]), 5)
        self.assertTrue(all(source["url"].startswith("https://") for source in self.story["sources"]))
        boundary = "\n".join(self.story["fact_boundary"])
        for keyword in ("1976年7月29日", "1977年7月31日", "1977年8月10日", "山姆之子",
                        "扬克斯", "不出现遗体"):
            self.assertIn(keyword, boundary)
        principles = "\n".join(self.story["principles"])
        for keyword in ("三色调", "黑影", "罚单", "一镜一句"):
            self.assertIn(keyword, principles)

    def test_publish_delivery_copies_the_named_four(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clips = root / "clips"
            (clips / "delivery").mkdir(parents=True)
            film = clips / "成片.mp4"
            film.write_bytes(b"film" * 1000)
            (clips / "山姆之子_封面.jpg").write_bytes(b"cover" * 100)
            (clips / "山姆之子_封面.png").write_bytes(b"cover" * 100)
            (clips / "成片_字幕.srt").write_text("1\n00:00:00,000 --> 00:00:04,000\n字幕\n", encoding="utf-8")
            (clips / "delivery" / "technical-report.json").write_text("{}", encoding="utf-8")
            audio = root / "work" / "sonofsam1977" / "audio"
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
            for name in ("SonOfSam1977_Final.mp4", "SonOfSam1977_Cover.png",
                         "SonOfSam1977_Subtitles.srt", "SonOfSam1977_Narration.wav"):
                self.assertIn(name, copied)
                self.assertTrue((delivery / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
