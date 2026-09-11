"""固定音色闸门测试：分析器准不准、闸门拦不拦、工具链焊没焊死。

全部用合成信号做，不依赖 ffmpeg（wav 直读），CI 无 ffmpeg 也能跑。
真实音频的正反例（dahlia / 重配音后的 zodiac1969 应过、被否掉的第一版应挂）
在 2026-09-11 的重配音现场已经人工验证过，数字记录在 voice_reference/spec.json。
"""
from __future__ import annotations

import json
import math
import sys
import unittest
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
import check_voice  # noqa: E402

SPEC = ROOT / "production" / "voice_reference" / "spec.json"


def synth_voice(path: Path, f0_center: float, f0_span: float = 18.0,
                seconds: float = 3.0, rate: int = 16000) -> None:
    """合成一段"像人声"的谐波信号：基频带缓慢起伏与整体下降，有声幅值 0.3。"""
    n = int(seconds * rate)
    t = np.arange(n) / rate
    f0 = f0_center + f0_span * np.sin(2 * math.pi * 0.4 * t) - (f0_span / 2) * (t / seconds)
    phase = 2 * math.pi * np.cumsum(f0) / rate
    signal = (0.30 * np.sin(phase) + 0.15 * np.sin(2 * phase) + 0.08 * np.sin(3 * phase))
    envelope = np.minimum(1.0, np.minimum(t / 0.05, (seconds - t) / 0.05))  # 去掉边界毛刺
    samples = np.int16(np.clip(signal * envelope, -1, 1) * 32767)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(rate)
        writer.writeframes(samples.tobytes())


def make_project(directory: Path, files: list[str], f0_center: float) -> Path:
    audio = directory / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    clips = []
    for name in files:
        synth_voice(audio / name, f0_center)
        clips.append({"id": name.split(".")[0], "file": name, "sha256": "x" * 64, "text": "测试"})
    (audio / "manifest.json").write_text(
        json.dumps({"voice_id": "test", "language": "zh-CN", "clips": clips}, ensure_ascii=False),
        encoding="utf-8")
    return directory


class AnalyzerTests(unittest.TestCase):
    def test_male_range_signal_measures_near_its_f0(self):
        path = Path("/tmp") is None and None or None  # placeholder to keep linters calm
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "male.wav"
            synth_voice(wav, f0_center=120.0)
            row = check_voice.profile(wav)
            self.assertGreater(row["voiced_frames"], 40)
            self.assertAlmostEqual(row["median_f0_hz"], 120.0, delta=6.0)
            self.assertLessEqual(row["p10_f0_hz"], 110.0)


class GateTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp(prefix="voice-gate-test-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_male_voice_passes(self):
        project = make_project(self.tmp / "male", ["N01.wav", "N02.wav"], f0_center=120.0)
        report = check_voice.check(project, SPEC)
        self.assertEqual(report["problems"], [], report["problems"])
        self.assertTrue(report["passed"])

    def test_high_pitched_voice_is_rejected(self):
        project = make_project(self.tmp / "high", ["N01.wav", "N02.wav"], f0_center=200.0)
        report = check_voice.check(project, SPEC)
        self.assertFalse(report["passed"])
        self.assertTrue(any("男音区间" in problem for problem in report["problems"]),
                        report["problems"])
        self.assertTrue(any("低十分位" in problem for problem in report["problems"]),
                        report["problems"])
        self.assertIn("voice_reference", report["remedy"])

    def test_too_short_clip_is_rejected(self):
        project = make_project(self.tmp / "short", ["N01.wav"], f0_center=120.0)
        clip = project / "audio" / "N01.wav"
        clip.unlink()
        synth_voice(clip, f0_center=120.0, seconds=0.4)  # 约 20 个有声帧，低于 40
        report = check_voice.check(project, SPEC)
        self.assertFalse(report["passed"])
        self.assertTrue(any("有声帧" in problem for problem in report["problems"]))


class WeldTests(unittest.TestCase):
    """"焊死"不许被悄悄拆掉：规格、样本、出片脚本、脚手架四处都得在。"""

    def test_spec_and_reference_samples_exist(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.assertEqual(spec["language"], "zh-CN")
        self.assertEqual(spec["gender"], "masculine")
        low, high = spec["gate"]["median_f0_hz"]
        self.assertLessEqual(low, min(spec["measured_reference"]["dahlia_median_f0_hz_per_chapter"]))
        self.assertGreaterEqual(high, max(spec["measured_reference"]["dahlia_median_f0_hz_per_chapter"]))
        for sample in spec["reference_samples"]:
            self.assertTrue((ROOT / sample).is_file(), sample)
        rejected = spec["measured_reference"]["rejected_take_median_f0_hz_per_chapter"]
        self.assertTrue(all(value > high for value in rejected), rejected)

    def test_run_project_runs_the_gate_and_fails_closed(self):
        script = (ROOT / "production" / "run_project.sh").read_text(encoding="utf-8")
        self.assertIn("python3 production/check_voice.py --project", script)
        # 失败必须中断出片（fail closed），不是打条日志继续跑
        self.assertRegex(script, r"check_voice\.py[^\n]*\|\|\s*\{[^}]*exit 1")

    def test_new_topic_scaffold_pins_the_voice(self):
        project = self.tmp_project()
        manifest = json.loads((project / "audio" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["voice_spec"], "production/voice_reference/spec.json")
        self.assertIn("男音", manifest["selection"])
        readme = (project / "README.md").read_text(encoding="utf-8")
        self.assertIn("check_voice.py", readme)
        self.assertIn("voice_reference", readme)

    def test_manual_pins_the_voice(self):
        manual = (ROOT / "新题目开工手册.md").read_text(encoding="utf-8")
        self.assertIn("check_voice.py", manual)
        self.assertIn("voice_reference", manual)
        self.assertIn("音色已钉死", manual)

    @staticmethod
    def tmp_project():
        import importlib
        import shutil
        import tempfile
        new_topic = importlib.import_module("new_topic")
        tmp = Path(tempfile.mkdtemp(prefix="voice-scaffold-"))
        production = tmp / "production"
        production.mkdir(parents=True)
        shutil.copy2(ROOT / "production" / "agnes_video.py", production / "agnes_video.py")
        project = production / "voicetest"
        new_topic.scaffold("voicetest", "音色钉死自检", "arena/voice-test",
                           project, ROOT / "production" / "dahlia")
        return project


if __name__ == "__main__":
    unittest.main()
