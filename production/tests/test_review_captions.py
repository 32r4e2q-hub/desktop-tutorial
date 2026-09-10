"""字幕验证的口径：文字零漏字是硬门，能量筛查只筛边界。

能量包络用纯 numpy 数组测（不依赖音频编码器）；main() 的文字硬门
在解码之前就判，所以坏文本用纯视频小片就能测到非 0 退出。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
import review_captions  # noqa: E402

try:
    import av  # noqa: F401
    import numpy as np

    HAS_AV = True
except ImportError:
    HAS_AV = False

NARRATION = [{"id": "N01", "start": 1.0, "end": 11.0,
              "text": "一九四七年一月十五日，洛杉矶。"}]


class CompletenessTests(unittest.TestCase):
    def test_matching_text_passes(self):
        cues = [{"start": 1.0, "end": 6.0, "text": "一九四七年一月十五日，"},
                {"start": 6.0, "end": 11.0, "text": "洛杉矶。"}]
        rows = review_captions.completeness(NARRATION, cues)
        self.assertTrue(rows[0]["match"])

    def test_a_dropped_character_is_reported_with_position(self):
        cues = [{"start": 1.0, "end": 11.0, "text": "一九四七年一月十五日，洛杉。"}]
        rows = review_captions.completeness(NARRATION, cues)
        self.assertFalse(rows[0]["match"])
        self.assertIsNotNone(rows[0]["first_diff"])

    def test_cue_at_next_chapter_start_belongs_to_next(self):
        """下章起点的 cue 归下章（+2s 窗口归属曾误报"字幕多字"，见对轨记录）。"""
        narration = [{"id": "N01", "start": 0.0, "end": 10.0, "text": "甲"},
                     {"id": "N02", "start": 11.0, "end": 20.0, "text": "乙"}]
        self.assertEqual(review_captions.chapter_of(11.0, narration)["id"], "N02")
        self.assertEqual(review_captions.chapter_of(9.9, narration)["id"], "N01")


class ReviewTests(unittest.TestCase):
    def _db(self):
        """12 秒包络（50 窗/秒）：0-1s 前奏静音，1-2s 人声，2-2.5s 人声
        （给 gap 测试留的"间隙语音"），2.5-2.8s 静音，2.8-4s 人声，
        4-6s 静音，6-11s 人声，11-12s 尾静音。章内中位 -20dB，阈值 -32dB。"""
        if not HAS_AV:
            raise unittest.SkipTest("numpy 未安装，跳过能量筛查测试")
        db = np.full(600, -20.0)
        db[0:50] = -60.0
        db[125:140] = -60.0
        db[200:300] = -60.0
        db[550:600] = -60.0
        return db

    def test_clean_boundaries_have_no_flags(self):
        cues = [{"start": 1.0, "end": 4.0, "text": "甲"},
                {"start": 6.0, "end": 11.0, "text": "乙"}]
        rows = review_captions.review(cues, NARRATION, self._db())
        self.assertEqual(rows[0]["flags"], [])
        self.assertEqual(rows[1]["flags"], [])

    def test_a_cue_covering_silence_is_flagged(self):
        cues = [{"start": 3.5, "end": 6.5, "text": "甲"}]
        rows = review_captions.review(cues, NARRATION, self._db())
        self.assertTrue(any("语音占比" in flag for flag in rows[0]["flags"]))

    def test_a_boundary_inside_speech_is_flagged(self):
        """边界落在人声中间（前后 ±0.2s 无低谷）必须进短名单。"""
        cues = [{"start": 1.0, "end": 3.0, "text": "甲"},
                {"start": 3.0, "end": 11.0, "text": "乙"}]
        rows = review_captions.review(cues, NARRATION, self._db())
        joined = " ".join(rows[0]["flags"] + rows[1]["flags"])
        self.assertIn("切在语音中间", joined)

    def test_gap_voice_is_a_note_not_a_flag(self):
        """间隙语音只记 gap_note（设计 GAP/呼吸/混响尾），不进短名单。"""
        cues = [{"start": 1.0, "end": 2.0, "text": "甲"},
                {"start": 2.8, "end": 4.0, "text": "乙"}]
        rows = review_captions.review(cues, NARRATION, self._db())
        self.assertIsNotNone(rows[0]["gap_note"])
        for row in rows:
            self.assertFalse(any("间隙" in flag for flag in row["flags"]))


class MainTests(unittest.TestCase):
    def test_mismatched_text_fails_before_decoding(self):
        """文字硬门在解码前就判：纯视频小片足以测到非 0。"""
        if not HAS_AV:
            raise unittest.SkipTest("PyAV 未安装，跳过 main 测试")
        directory = Path(tempfile.mkdtemp(prefix="captions-"))
        film = directory / "film.mp4"
        container = av.open(str(film), "w")
        stream = container.add_stream("mpeg4", rate=30)
        stream.width, stream.height, stream.pix_fmt = 160, 90, "yuv420p"
        plane = np.zeros((90, 160, 3), dtype=np.uint8)
        for _ in range(5):
            for packet in stream.encode(av.VideoFrame.from_ndarray(plane, format="rgb24")):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
        container.close()
        project = directory / "project"
        (project / "delivery").mkdir(parents=True)
        (project / "delivery" / "narration-timing.json").write_text(
            json.dumps(NARRATION, ensure_ascii=False), encoding="utf-8")
        (project / "delivery" / "caption-timing.json").write_text(
            json.dumps([{"start": 0.0, "end": 10.0, "text": "缺字了"}], ensure_ascii=False),
            encoding="utf-8")
        exit_code = review_captions.main(
            ["--film", str(film), "--project", str(project),
             "--work", str(directory / "work")])
        self.assertEqual(exit_code, 1)
