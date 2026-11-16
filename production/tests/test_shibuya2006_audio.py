"""第17期旁白链路的离线守门：转写解码、分支口径、依赖装配。

为什么要单独守这三条
--------------------
2026-11-16 的「旁白独立转写核验」跑了 1 分 14 秒就红：转写第一步就崩，

    TypeError: open() got an unexpected keyword argument 'metadata_errors'

原因是 runner 上的 Python 到了 3.14，pip 解析出的 PyAV 比 faster-whisper 要求的旧。
**这不是录音坏了**，而是解码路径依赖了 runner 碰巧装了哪个 av 轮子。所以：

1. 转写改成 ffmpeg 解码成 float32 数组再喂模型，PyAV 退出音频路径——这里用一段
   真造出来的正弦波验证解码长度与类型；
2. 工作流必须钉 Python 3.11 并装 ``production/requirements.txt``（av 在那边有版本
   区间），否则同样的坑会换个方式回来；
3. 工作流不能再写死某一条 ``arena/<id>`` 分支：Arena 每轮换分支，写死就等于下一轮
   这些作业永远跑不到当前分支上。
"""
from __future__ import annotations

import math
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "shibuya2006"
WORKFLOWS = ROOT / ".github" / "workflows"
sys.path.insert(0, str(PROJECT))

HAVE_FFMPEG = shutil.which("ffmpeg") is not None


class NarrationDecodeTests(unittest.TestCase):
    def test_normalize_drops_punctuation_and_keeps_spoken_characters(self):
        import transcribe_audio_candidates as transcribe

        self.assertEqual(transcribe.normalize("他说，她讲了句，你没有梦想。"),
                         "他说她讲了句你没有梦想")
        # 数字要按念出来的字对齐：2026-11-16 那一轮把 "12月31日" 当成不一致。
        self.assertEqual(transcribe.normalize("12月31日"),
                         transcribe.normalize("十二月三十一日"))
        self.assertEqual(transcribe.normalize("1月2日"),
                         transcribe.normalize("一月二日"))
        # whisper 会整段吐繁体，繁体/简体不能各记一个错字。
        self.assertEqual(transcribe.normalize("東京的家"),
                         transcribe.normalize("东京的家"))

    @unittest.skipUnless(HAVE_FFMPEG, "需要 ffmpeg 才能造测试音频")
    def test_decode_uses_ffmpeg_and_returns_16k_float32(self):
        """真造 0.5 秒正弦波：解码后长度必须是 16000 × 0.5，类型 float32。

        这条用例替掉的正是崩在 ``av.open(..., metadata_errors=...)`` 上的那条路：
        只要模块改回把文件路径直接交给模型，PyAV 版本再次漂移时这里会先红。
        """
        import tempfile

        import numpy as np

        import transcribe_audio_candidates as transcribe

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "tone.wav"
            subprocess.run([
                "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
                "-i", "sine=frequency=440:sample_rate=48000:duration=0.5",
                "-ac", "2", str(source),
            ], check=True)
            samples = transcribe.decode_float32(source)
        self.assertEqual(samples.dtype, np.float32)
        self.assertEqual(len(samples), 8000)
        self.assertGreater(float(np.max(np.abs(samples))), 0.1)

    def test_module_never_passes_a_path_to_the_model(self):
        """转写必须喂数组：源码里不能再出现 model.transcribe(<文件路径>)。"""
        text = (PROJECT / "transcribe_audio_candidates.py").read_text(encoding="utf-8")
        self.assertIn("decode_float32", text)
        self.assertNotIn("model.transcribe(str(path)", text)

    def test_boundaries_land_on_asr_word_onsets_not_on_silence(self):
        """句界取 ASR 词起点：静音切分会把 S23/S24 切在句子中间。"""
        from types import SimpleNamespace

        import align_group_audio as align

        texts = ["今天很冷。", "明天更冷。", "后天最冷。"]
        starts = [0.20, 2.10, 4.05]           # 每句首字真正开口的时间
        words = []
        for base, sentence in zip(starts, ("今天很冷", "明天更冷", "后天最冷")):
            for offset, character in enumerate(sentence):
                words.append(SimpleNamespace(word=character,
                                             start=base + offset * 0.2,
                                             end=base + offset * 0.2 + 0.18))
        heard, spans = align.char_spans(words)
        cuts, evidence, matched = align.boundaries_for(texts, heard, spans, 6.0)

        self.assertEqual(len(cuts), 4)
        self.assertAlmostEqual(cuts[1], starts[1] - align.PRE_ROLL, places=3)
        self.assertAlmostEqual(cuts[2], starts[2] - align.PRE_ROLL, places=3)
        self.assertEqual(matched, len(heard))
        self.assertEqual([row["time"] for row in evidence], starts[1:])

    def test_missing_word_still_yields_a_boundary(self):
        """ASR 吞字时，就近映射到能对上的字，而不是抛异常或乱切。"""
        from types import SimpleNamespace

        import align_group_audio as align

        texts = ["今天很冷。", "明天更冷。", "后天最冷。"]
        starts = [0.2, 3.0, 5.8]
        words = []
        for base, sentence in zip(starts, ("今天很冷", "明天更冷", "后天最冷")):
            for offset, character in enumerate(sentence):
                if sentence == "明天更冷" and character == "更":
                    continue          # whisper 吞掉一个字
                words.append(SimpleNamespace(word=character,
                                             start=base + offset * 0.5,
                                             end=base + offset * 0.5 + 0.45))
        heard, spans = align.char_spans(words)
        cuts, _evidence, _matched = align.boundaries_for(texts, heard, spans, 8.0)
        self.assertEqual(len(cuts), 4)
        self.assertAlmostEqual(cuts[1], starts[1] - align.PRE_ROLL, delta=0.6)
        self.assertAlmostEqual(cuts[2], starts[2] - align.PRE_ROLL, delta=0.6)

    @unittest.skipUnless(HAVE_FFMPEG, "需要 ffmpeg 才能造测试音频")
    def test_caption_lead_is_measured_from_the_first_audible_sample(self):
        """字幕不能凭空从镜头起点开始：先量出真实开口时间，只保留 0.10s 预读。

        2026-11-16 第一版母版就是栽在这里：30 条字幕全部从镜头起点起，语音却晚
        0.04–0.24 秒，verify_master 判「字幕领先语音 0.240s」。
        """
        import importlib.util
        import tempfile

        # 不能直接 ``import render``：production/tests/test_dahlia_edit.py 也会
        # 导入一个同名的 render（dahlia 项目），全量跑测试时后者会抢先注册。
        spec = importlib.util.spec_from_file_location(
            "shibuya2006_render", PROJECT / "render.py")
        render = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(render)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "late-voice.wav"
            # 0.6 秒静音 + 0.6 秒 220Hz：模拟 TTS 的前导静音（runner 上是旧版 ffmpeg，
            # 不用 anullsrc 的 d= 选项，改用 adelay 补前导静音）。
            subprocess.run([
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000:duration=0.6",
                "-af", "adelay=600", "-ac", "1", str(source),
            ], check=True)
            onset = render.speech_onset(source)
        self.assertAlmostEqual(onset, 0.6, delta=0.06)

    def test_transcript_approval_needs_a_written_reason(self):
        """相似度只是门槛：同音字偏差必须有写下来的理由，不能自动放行。"""
        import assemble_narration_review as assemble

        self.assertTrue(assemble.decision(0.95, None)[0])
        approved, _note = assemble.decision(0.70, None)
        self.assertFalse(approved)
        approved, note = assemble.decision(0.70, "whisper 把「涩谷」听成「社谷」")
        self.assertTrue(approved)
        self.assertIn("涩谷", note)

    def test_review_assembly_refuses_cut_candidates(self):
        """三句连读切出来的候选不能冒充逐镜录音。"""
        import assemble_narration_review as assemble

        story = {"shots": [{"id": "S01", "narration": "妹妹遇害第二天，他照常去集训。"}]}
        asr = {"shots": [{"id": "S01", "source_kind": "pause_cut_candidate",
                          "sha256": "0" * 64, "similarity": 1.0, "atempo_needed": 1.0}]}
        rows = assemble.build_rows(story, "voice-00", asr, {})
        self.assertEqual(rows[0]["status"], "pending")
        self.assertIn("different source", rows[0]["reason"])

    def test_worker_installs_pinned_python_and_shared_requirements(self):
        text = (WORKFLOWS / "shibuya2006-audio-review.yml").read_text(encoding="utf-8")
        self.assertIn("actions/setup-python@v5", text)
        self.assertIn('python-version: "3.11"', text)
        self.assertIn("production/requirements.txt", text)
        self.assertIn("faster-whisper", text)
        self.assertIn("WHISPER_CACHE_DIR", text)
        # 切分优先用 ASR 词时间戳，静音切分只做兜底。
        step = text[text.index("Cut candidates and independently transcribe"):]
        self.assertLess(step.index("align_group_audio.py"),
                        step.index("transcribe_audio_candidates.py"))
        self.assertIn("|| python production/shibuya2006/prepare_group_audio.py", step)

    def test_shibuya_workflows_follow_the_current_arena_branch(self):
        """三条第17期工作流都跑"触发它的那条分支"，不再写死某轮 arena/<id>。"""
        for name in ("shibuya2006.yml", "shibuya2006-audio-review.yml",
                     "shibuya2006-cover.yml"):
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text(encoding="utf-8")
                self.assertIn("${{ github.ref_name }}", text)
                self.assertIn("startsWith(github.ref, 'refs/heads/arena/')", text)
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    self.assertNotRegex(
                        stripped, r"arena/[0-9a-f]{8}-desktop-tutorial",
                        f"{name} 写死了分支名：{stripped}")

    def test_missing_narration_is_reported_not_filled(self):
        """缺 G04（S10–S12）时，转写报告只能写 missing_audio，不许造音频。"""
        import transcribe_audio_candidates as transcribe

        reasons = transcribe.blocked_reasons()
        for sid in ("S10", "S11", "S12"):
            self.assertEqual(reasons.get(sid), "moderation_blocked")
        text = (PROJECT / "transcribe_audio_candidates.py").read_text(encoding="utf-8")
        self.assertIn("missing_audio", text)
        # 不许在本脚本里生成音频：没有写文件、没有合成调用。
        for forbidden in ("write_wav", "soundfile", "generate_speech", "silenceremove"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
