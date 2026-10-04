"""参考风格实验室（``production/style_lab/``）的离线自检。

为什么要有这份测试：把「参考片长什么样」翻译成提示词这件事，最容易出的错是
**实测值和提示词各写各的**——量出来是冷调，提示词里却照抄上一部的暖调；
或者从 ``production/gilgo`` 复制 ``NEGATIVE_PROMPT`` 时把里面的
``3D render look, plastic CGI`` 一起带过来，等于自己把想要的 3D 画面否掉。

所以这里守五条，全部离线：

1. 数值 → 中文判定 → 英文提示词这条链是通的，且英文词**真的出现在** ``STYLE_PREFIX`` 里；
2. 三份候选共用同一套调色 / 光线 / 颗粒词，差别只在画面定位与人物政策；
3. ``NEGATIVE_PROMPT`` 里不许再出现反 3D 的词（上面那个坑）；
4. 档案里必须写明采样规模与已知误差，不许把推测写成结论；
5. 有 ffmpeg 时，用 2 秒合成片把 ``analyze.py`` 整条跑通；没 ffmpeg 就跳过
   ——离线 CI 不能因为环境缺 ffmpeg 就红。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STYLE_LAB = ROOT / "production" / "style_lab"
sys.path.insert(0, str(STYLE_LAB))

try:
    import style_profile  # type: ignore
except ImportError:  # pragma: no cover - 依赖没装时下面的用例会整体跳过
    style_profile = None

try:
    import numpy  # noqa: F401
    import PIL  # noqa: F401

    HAVE_IMAGING = True
except ImportError:  # pragma: no cover
    HAVE_IMAGING = False


def _ffmpeg() -> str:
    try:
        from ffmpeg_tool import find_ffmpeg  # type: ignore

        return find_ffmpeg()
    except Exception:  # pragma: no cover
        which = shutil.which("ffmpeg")
        return which or ""


FFMPEG = _ffmpeg()


def fake_metrics(**over):
    """一组捏造但形状正确的实测值。"""
    base = {
        "source": {"file": "demo.mp4", "mb": 1.0, "analyzed_at": "2026-10-04 00:00:00", "ffmpeg": "test"},
        "container": {"duration": 180.0, "fps": 30.0, "width": 1920, "height": 1080,
                      "orientation": "landscape", "video_codec": "h264", "has_audio": True},
        "sampling": {"sampled_frames": 12, "cut_detection_threshold": 0.24, "motion_pairs": 4},
        "color": {
            "mean_luma": 96.0, "luma_std": 21.0, "mean_contrast": 54.0,
            "mean_saturation": 81.0, "warmth_r_minus_b": -6.8,
            "tone_split": {"shadow": 0.17, "low_mid": 0.42, "high_mid": 0.41, "highlight": 0.0},
            "palette": [
                {"hex": "#121819", "rgb": [18, 24, 25], "share": 0.31},
                {"hex": "#354144", "rgb": [53, 65, 68], "share": 0.20},
                {"hex": "#d7d2bf", "rgb": [215, 210, 191], "share": 0.16},
            ],
        },
        "texture": {"mean_sharpness": 528.0, "mean_grain": 9.3, "dof_center_over_edge": 3.26,
                    "dof_frames_used": 12, "dof_total_frames": 12, "bottom_band_ratio": 0.96},
        "motion": {"mean_interframe_diff": 0.052, "max_interframe_diff": 0.127, "samples": [0.05]},
        "rhythm": {"estimated_cuts": 41, "estimated_median_shot_seconds": 3.65,
                   "estimated_mean_shot_seconds": 4.29, "cut_times": [1.0, 2.0], "partial": False},
    }
    base.update(over)
    return base


@unittest.skipIf(style_profile is None, "缺依赖（pillow/numpy），跳过")
class TestStyleProfile(unittest.TestCase):
    def test_bands_follow_the_numbers(self):
        words = style_profile.describe(fake_metrics())["zh"]
        self.assertIn("偏暗", words["影调"])
        self.assertIn("冷调", words["色温"])
        self.assertIn("低饱和", words["饱和"])
        self.assertIn("颗粒", words["颗粒"])

    def test_english_words_actually_reach_the_prefix(self):
        words = style_profile.describe(fake_metrics())
        for cand in style_profile.build_candidates(words):
            for key in ("palette", "tone", "temperature", "contrast", "sharpness", "grain", "dof", "motion"):
                self.assertIn(words["en"][key], cand["style_prefix"],
                              f"{cand['id']} 少了 {key}: {words['en'][key]}")

    def test_candidates_share_the_look_words(self):
        words = style_profile.describe(fake_metrics())
        cands = style_profile.build_candidates(words)
        self.assertEqual([c["id"] for c in cands],
                         ["photoreal_silhouette", "photoreal_faces", "cinematic_3d"])
        shared = [c for c in cands if "midnight blue" in c["style_prefix"] or "near-black" in c["style_prefix"]]
        self.assertEqual(len(shared), 3, "三份候选必须用同一套调色词")
        # 人物政策是三者的真正差别
        self.assertIn("never a clear frontal face", cands[0]["style_prefix"])
        self.assertIn("non-celebrity human faces are allowed", cands[1]["style_prefix"])

    def test_negative_prompt_drops_the_anti_3d_phrases(self):
        """production/gilgo 的 NEGATIVE_PROMPT 里有 '3D render look, plastic CGI'，
        照抄过来会把这次要的超写实 3D 画面自己否掉。"""
        for cand in style_profile.build_candidates(style_profile.describe(fake_metrics())):
            low = cand["negative_prompt"].lower()
            self.assertNotIn("3d render look", low)
            self.assertNotIn("plastic cgi", low)
            self.assertIn("flat 2d illustration", low, "反过来要把 2D 手绘挡住")

    def test_markdown_states_limits_and_setting_placeholder(self):
        metrics = fake_metrics()
        profile = style_profile.build_style_profile(metrics)
        md = profile["markdown"]
        self.assertIn("不是逐帧审查", md)
        self.assertIn("不把推测写成结论", md)
        self.assertIn(style_profile.SETTING_PLACEHOLDER, md)
        self.assertIn("45 镜 × 4 秒", md, "要提醒新片仍按手册的网格走")

    def test_dof_is_skipped_when_vignette_fools_it(self):
        metrics = fake_metrics()
        metrics["texture"] = dict(metrics["texture"], dof_center_over_edge=None,
                                  dof_frames_used=2, dof_total_frames=12)
        words = style_profile.describe(metrics)
        self.assertIn("判不了", words["zh"]["景深"])
        self.assertIsNone(words["numbers"]["dof"])

    def test_write_profile_drops_two_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            style_profile.write_profile(out, style_profile.build_style_profile(fake_metrics()))
            self.assertTrue((out / "风格档案.md").exists())
            payload = json.loads((out / "style-candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(len(payload["candidates"]), 3)
            self.assertIn("setting", payload["placeholders"])


@unittest.skipIf(style_profile is None or not HAVE_IMAGING or not FFMPEG,
                 "缺 ffmpeg 或成像依赖，跳过整条 analyze.py 的端到端用例")
class TestAnalyzeEndToEnd(unittest.TestCase):
    def test_two_second_clip_runs_the_whole_pipeline(self):
        import analyze  # type: ignore

        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "clip.mp4"
            subprocess.run(
                [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                 "-i", "testsrc2=size=320x180:rate=25:duration=2",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)],
                check=True, timeout=120,
            )
            out = Path(tmp) / "run"
            metrics = analyze.analyze_video(clip, out, samples=6, threshold=0.24, keep_reference=False)

            self.assertAlmostEqual(metrics["container"]["duration"], 2.0, delta=0.3)
            self.assertEqual(metrics["container"]["width"], 320)
            self.assertEqual(metrics["sampling"]["sampled_frames"], 6)
            self.assertTrue(metrics["color"]["palette"], "必须量出主色")
            self.assertTrue((out / "reference_metrics.json").exists())
            self.assertTrue((out / "contact-sheet.jpg").exists())

            profile = style_profile.build_style_profile(metrics)
            style_profile.write_profile(out, profile)
            self.assertIn("风格档案", profile["markdown"])
            self.assertEqual(len(profile["candidates"]), 3)


if __name__ == "__main__":
    unittest.main()
