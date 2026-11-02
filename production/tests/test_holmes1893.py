"""离线自检：H·H·霍姆斯《传说里的杀人城堡》的分镜、提示词拼装与旁白清单。

不联网、不调模型：只守「能离线判定的东西」——
30 镜 / 180 秒 / 5–7 秒为主 / 24fps、STYLE 与 NEGATIVE 自动拼接、角色设定逐字复用、
每镜都有真实运镜与真实运动、传说版画用独立 STYLE、双层标签与撕裂转场、单角色镜头固定 seed、
旁白一镜一句且语速合理、参考图齐备。
配音文件齐了以后，``generate.py --validate`` 还会再验 SHA-256 与时长。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "holmes1893"


def load_generate():
    """按路径加载本项目 generate.py，避免和仓库里别的同名模块串味。"""
    stashed = {name: sys.modules.pop(name) for name in ("generate", "throttle", "agnes_video")
               if name in sys.modules}
    path_snapshot = list(sys.path)
    sys.path.insert(0, str(ROOT / "production"))
    spec = importlib.util.spec_from_file_location("holmes1893_generate", PROJECT / "generate.py")
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


class HolmesPlanTests(unittest.TestCase):
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

    def test_brief_shot_lengths_are_five_to_seven_seconds(self):
        """附件脚本给的 30 个镜头全部是 5–7 秒；这里守住这条节奏。"""
        lengths = sorted({shot["duration"] for shot in self.story["shots"]})
        self.assertEqual(lengths, [5, 6, 7])

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
                expected = (self.story["style_rumor_prefix"] if shot["style_variant"] != "real"
                            else self.story["style_prefix"]).strip()
                self.assertTrue(prompt.startswith(expected))

    def test_every_shot_demands_real_camera_motion(self):
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                text = shot["prompt"]
                self.assertIn("Camera:", text)
                self.assertRegex(text.lower(), r"real motion|rotates|drifting|crawl|passing")
                self.assertGreater(len(text), 240)

    def test_legend_panels_use_the_print_style_and_carry_no_lettering(self):
        """双层画面规则：传说想象一律用泛黄旧报纸版画的独立 STYLE。"""
        legend = [shot for shot in self.story["shots"] if shot["style_variant"] != "real"]
        self.assertEqual([shot["id"] for shot in legend], ["S09", "S12", "S13"])
        for shot in legend:
            style = self.gen.style_for(self.story, shot).lower()
            self.assertIn("newspaper engraving", style)
            self.assertIn("no readable letters", shot["prompt"].lower())
        # S14 是撕裂转场：从传说画面撕开，露出写实画面，因此本身按写实镜头发单。
        tear = next(shot for shot in self.story["shots"] if shot["id"] == "S14")
        self.assertEqual(tear["style_variant"], "real")
        self.assertIn("tear", tear["prompt"].lower())

    def test_transitions_follow_the_two_layer_rule(self):
        render = load_module("holmes1893_render_transitions", PROJECT / "render.py")
        shots = self.story["shots"]
        plan = render.transition_plan(self.story)
        self.assertEqual(plan["S10"], ("fade", 0.12))        # 版画剖面 → 写实：极短叠化回到现实
        self.assertEqual(plan["S12"], ("fade", 0.30))        # 写实 → 传说：雾气叠化
        self.assertEqual(plan["S13"], ("smoothright", 0.35))  # 版画与版画之间：纸张翻页擦除
        self.assertEqual(plan["S14"], ("fade", 0.12))        # 进入撕裂镜头：极短叠化
        self.assertEqual(plan["S15"], ("fade", 0.30))        # 写实与写实之间：0.3 秒雾气叠化
        for index in range(1, len(shots)):
            self.assertIn(shots[index]["id"], plan)

    def test_sensitive_imagery_is_never_requested(self):
        banned = re.compile(r"\b(corpse|dead body|blood splatter|gore|murder the|stabbing|"
                            r"noose|gallows|hanging|exposed body|execution chamber)\b", re.I)
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                # 只查「场景描述」：句子里明确写出「no gallows / no gore」这类否定的不算违背。
                scene = shot["prompt"].split("Camera:")[0]
                for match in banned.finditer(scene):
                    context = scene[max(0, match.start() - 14):match.end() + 14].lower()
                    self.assertRegex(context, r"\bno\b|nothing|never|without",
                                     f"{shot['id']} 场景里出现了敏感词：{context!r}")
        # S28 只拍走廊灯灭与关门：画面提示词里必须写明「不出现任何刑场」。
        prison = next(shot for shot in self.story["shots"] if shot["id"] == "S28")
        self.assertIn("Nothing of any execution is shown", prison["prompt"])
        # 孩子只以剪影/背影出现。
        kids = self.story["characters"]["children"]
        self.assertIn("silhouette", kids.lower())
        self.assertIn("never shown", kids.lower())

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
        self.assertIn("holmes", seen)
        self.assertIn("geyer", seen)

    def test_narration_is_one_line_per_shot_at_a_human_pace(self):
        self.assertEqual(len(self.story["shots"]), len({shot["narration"] for shot in self.story["shots"]}))
        total = 0
        for shot in self.story["shots"]:
            characters = sum(1 for ch in shot["narration"] if ch.isalnum() or "\u3400" <= ch <= "\u9fff")
            total += characters
            with self.subTest(shot=shot["id"]):
                self.assertGreater(characters, 0)
                self.assertLessEqual(characters / shot["duration"], 4.8)
        self.assertGreater(total, 540)
        self.assertLess(total / 180.0, 4.2)

    def test_narration_length_matches_shot_length(self):
        """解说词跟片段等长：字数 ÷ 镜头秒数落在人类语速区间，且不靠加速凑。"""
        for shot in self.story["shots"]:
            chars = len(re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", shot["narration"]))
            cps = chars / shot["duration"]
            self.assertGreaterEqual(cps, 1.0, f"{shot['id']} 旁白太短，镜头会空着：{cps:.2f} 字/秒")
            self.assertLessEqual(cps, 4.45, f"{shot['id']} 旁白太密，必须加速才能塞进镜头：{cps:.2f} 字/秒")

    def test_narration_fit_verdicts(self):
        fit = load_module("holmes1893_narration_fit", PROJECT / "narration_fit.py")
        self.assertEqual(fit.classify(0.92, 1.00, 1.55), "fit")
        self.assertEqual(fit.classify(0.75, 1.00, 1.55), "ok")
        self.assertEqual(fit.classify(0.46, 1.00, 1.55), "short")
        self.assertEqual(fit.classify(1.12, 1.12, 1.55), "needs-speedup")
        self.assertEqual(fit.classify(1.60, 1.60, 1.55), "over")

    def test_children_are_identified_as_pitezels_not_his_own(self):
        """解说里必须说清三个孩子是皮泰泽尔的孩子，不能让人听成霍姆斯杀自己孩子。"""
        by_id = {shot["id"]: shot["narration"] for shot in self.story["shots"]}
        block = "".join(by_id[f"S{n:02d}"] for n in range(18, 23))
        self.assertIn("皮泰泽尔", block + by_id["S17"], "得先交代皮泰泽尔是谁")
        self.assertTrue("孩子母亲" in block or "的妻子" in block,
                        "要说清是从孩子的母亲身边带走")
        for shot in self.story["shots"]:
            for wrong in ("他的三个孩子", "自己的孩子", "虎毒不食子"):
                self.assertNotIn(wrong, shot["narration"], shot["id"])
        # 每个孩子的死要有落点，不能只用「没能等到回家」含糊带过。
        self.assertIn("地窖门", by_id["S21"])
        self.assertIn("艾丽斯", by_id["S22"])
        self.assertNotIn("没能等到回家", "".join(by_id.values()))

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

    def test_fact_boundaries_quote_the_real_record(self):
        boundary = "\n".join(self.story["fact_boundary"])
        for keyword in ("1861", "1884", "英格尔伍德", "一万美元", "艾丽斯", "1896 年 5 月 7 日",
                        "莫亚门辛", "水泥", "九人", "两百人"):
            self.assertIn(keyword, boundary, keyword)
        self.assertTrue(any("Pitezel" in source["title"] or "Pitezel" in source["supports"]
                            for source in self.story["sources"]))
        self.assertGreaterEqual(len(self.story["sources"]), 5)

    def test_sources_and_release_copy_are_recorded(self):
        self.assertTrue(all(source["url"].startswith("https://") for source in self.story["sources"]))
        pres = self.story["presentation"]
        # 封面改成系列模板后，标题是两行短句；仍要能看出「传说 / 真相」这组对照。
        self.assertIn("九个人", pres["cover"]["line2"])
        self.assertIn("失踪", pres["cover"]["line1"])
        self.assertEqual(pres["end_title"], "H·H·霍姆斯")
        self.assertIn("哪个更可怕", pres["end_question"])
        for tag in ("#真实事件", "#HH霍姆斯", "#杀人城堡", "#3D动画"):
            self.assertIn(tag, pres["hashtags"])

    def test_publish_delivery_uses_this_film_s_names(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clips = root / "clips"
            (clips / "delivery").mkdir(parents=True)
            film = clips / "成片.mp4"
            film.write_bytes(b"film" * 1000)
            (clips / "成片_封面.jpg").write_bytes(b"cover" * 100)
            (clips / "成片_封面.png").write_bytes(b"cover" * 100)
            (clips / "成片_字幕.srt").write_text("1\n00:00:00,000 --> 00:00:04,000\n字幕\n", encoding="utf-8")
            (clips / "delivery" / "technical-report.json").write_text("{}", encoding="utf-8")
            audio = root / "work" / "holmes1893" / "audio"
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
            for name in ("Holmes_Castle_Final.mp4", "Holmes_Castle_Cover.png",
                         "Holmes_Castle_Subtitles.srt", "Holmes_Castle_Narration.wav"):
                self.assertIn(name, copied)
                self.assertTrue((delivery / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()


class EndCardDimTests(unittest.TestCase):
    """片尾压暗必须走 ffmpeg 滤镜：ASS 里的 \\p1 整幅绘图在部分 libass 构建上会被整层丢弃。"""

    def setUp(self):
        self.render = load_module("holmes1893_render_dim", PROJECT / "render.py")
        self.story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))

    def test_ass_carries_no_full_frame_drawing(self):
        cues = [{"shot_id": shot["id"], "start": shot["start"] + 0.1,
                 "end": shot["start"] + max(0.6, shot["duration"] - 0.2),
                 "text": shot["narration"]} for shot in self.story["shots"]]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "check.ass"
            self.render.write_subtitles(path, cues, self.story, Path(tmp) / "check.srt")
            ass = path.read_text(encoding="utf-8")
        self.assertNotIn("Style: Plate", ass)
        self.assertNotIn("l 1920 1080", ass)
        self.assertIn("Dialogue: 2,", ass, "片尾字幕仍需保留")

    def test_cover_uses_the_single_series_template(self):
        source = (PROJECT / "render.py").read_text(encoding="utf-8")
        self.assertIn("series_cover.make(", source, "封面必须走 production/series_cover.py")
        self.assertNotIn("tear_path(", source, "旧的撕裂封面已废弃")
        self.assertIn("make_cover(", source)

        import qc

        self.assertEqual(tuple(qc.COVER_SIZE), (1080, 1440))
        cover = self.story["presentation"]["cover"]
        self.assertEqual(cover["series_episode"], 2)
        self.assertEqual((cover["line1"], cover["line2"]), ("传说里两百人失踪", "他只承认九个人"))
        for line in (cover["line1"], cover["line2"]):
            self.assertTrue(1 <= len(line) <= 18, line)
        # 窗口里必须是本片的一帧，且落在该镜时长之内（取没有字幕压住的时刻）。
        self.assertIn(cover["window_shot"], [shot["id"] for shot in self.story["shots"]])
        shot = next(s for s in self.story["shots"] if s["id"] == cover["window_shot"])
        self.assertGreaterEqual(cover["window_at"], 0)
        self.assertLess(cover["window_at"], shot["duration"])

    def test_closing_card_is_darkened_by_a_filter_not_by_ass(self):
        source = (PROJECT / "render.py").read_text(encoding="utf-8")
        # 时间门控（enable=）与 trim/concat 在 runner 上都实测不生效，压暗改到 S30 的逐镜调色里。
        self.assertIn("closing_shot_darkened", source)
        self.assertNotIn("enable=", source, "不要再用时间表达式压暗")
        self.assertIn("verify_end_card_dim", source, "渲染后必须校验片尾真的被压暗")

    def test_fade_lands_on_the_end_card_and_qc_accepts_the_tail_blackout(self):
        source = (PROJECT / "render.py").read_text(encoding="utf-8")
        card_at = float(re.search(r"^END_CARD_AT = ([0-9.]+)", source, re.M).group(1))
        fade_start = float(re.search(r"^END_CARD_FADE_START = ([0-9.]+)", source, re.M).group(1))
        fade_len = float(re.search(r"^END_CARD_FADE_SECONDS = ([0-9.]+)", source, re.M).group(1))
        story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
        last_start = float(story["shots"][-1]["start"])
        # 渐隐是 S30 内的相对时间：全黑的那一刻要正好落在片尾卡出现的位置，中间不留死黑。
        self.assertAlmostEqual(card_at, 176.40, places=2)
        self.assertLessEqual(abs((last_start + fade_start + fade_len) - card_at), 0.05)

        import qc

        fps = 10.0
        frames = np.full((1800, 4, 4), 90, dtype=np.uint8)   # 缩略图即可，只看亮度序列
        frames[1760:] = 0                      # 176.0 s 起是计划内的片尾收黑
        frames[905] = 0                        # 90.5 s 的孤立黑帧（不在切点上）才是缺陷
        shots = [{"start": i * 6.0} for i in range(30)]
        picture = qc.analyse_picture(frames, fps=fps, shots=shots)
        self.assertEqual(picture["unexpected_black_samples"], [90.5])
        self.assertTrue(picture["tail_black_samples"], "片尾收黑要被单独记录下来")
