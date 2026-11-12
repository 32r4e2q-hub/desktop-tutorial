#!/usr/bin/env python3
"""`production/verify_master.py` 的离线测试：只测纯函数，不需要 ffmpeg / 媒体文件。

真实的音画检测（音频流长度、字幕窗口、字幕-语音同步）在 runner 或本地有 ffmpeg 时，
直接跑 CLI：

    python3 production/verify_master.py --film <成片.mp4> --story <story.json>
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))

import verify_master  # noqa: E402


class SrtParsingTests(unittest.TestCase):
    def test_parses_cues_and_strips_index_lines(self):
        srt = (
            "1\n00:00:00,000 --> 00:00:04,289\n第一句。\n\n"
            "2\n00:00:05,000 --> 00:00:09,656\n第二句。\n"
        )
        tmp = ROOT / "work" / "verify-master-test.srt"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(srt, encoding="utf-8")
        cues = verify_master.parse_srt(tmp)
        self.assertEqual(len(cues), 2)
        self.assertAlmostEqual(cues[0][0], 0.0, places=3)
        self.assertAlmostEqual(cues[0][1], 4.289, places=3)
        self.assertEqual(cues[1][2], "第二句。")

    def test_missing_file_returns_empty(self):
        self.assertEqual(verify_master.parse_srt(ROOT / "work" / "not-here.srt"), [])


class CueWindowTests(unittest.TestCase):
    spans = [("S01", 0.0, 5.0), ("S02", 5.0, 10.0)]

    def test_exact_fit_passes(self):
        cues = [(0.0, 4.5, "a"), (5.0, 9.7, "b")]
        self.assertEqual(verify_master.cue_window_problems(cues, self.spans), [])

    def test_cue_count_mismatch_fails(self):
        problems = verify_master.cue_window_problems([(0.0, 4.5, "a")], self.spans)
        self.assertTrue(any("条数" in item for item in problems))

    def test_cue_leading_into_previous_shot_fails(self):
        # 实际踩过的坑：TTS 前导静音让 cue 比镜头早 0.3 秒，字幕串到上一镜。
        cues = [(0.0, 4.5, "a"), (4.7, 9.7, "b")]
        problems = verify_master.cue_window_problems(cues, self.spans)
        self.assertTrue(any("早于 S02" in item for item in problems))

    def test_cue_running_past_shot_end_fails(self):
        cues = [(0.0, 4.5, "a"), (5.0, 10.4, "b")]
        problems = verify_master.cue_window_problems(cues, self.spans)
        self.assertTrue(any("晚于 S02" in item for item in problems))

    def test_zero_length_cue_fails(self):
        cues = [(0.0, 0.0, "a"), (5.0, 9.7, "b")]
        problems = verify_master.cue_window_problems(cues, self.spans)
        self.assertTrue(any("时长非正" in item for item in problems))


class ShotSpanTests(unittest.TestCase):
    def test_spans_follow_start_and_duration(self):
        story = {"shots": [
            {"id": "S01", "start": 0, "duration": 5},
            {"id": "S02", "start": 5, "duration": 6},
        ]}
        self.assertEqual(verify_master.shot_spans(story),
                         [("S01", 0.0, 5.0), ("S02", 5.0, 11.0)])

    def test_rms_blocks_marks_silence_and_speech(self):
        numpy = __import__("numpy")
        rate = 48_000
        # 10ms 一格：每段正好一块，前两块静音、后两块有声。
        quiet = numpy.zeros(rate // 100, dtype=numpy.float32)
        loud = numpy.full(rate // 100, 0.5, dtype=numpy.float32)
        blocks = verify_master.rms_blocks(numpy.concatenate([quiet, quiet, loud, loud]), rate)
        self.assertEqual(len(blocks), 4)
        self.assertFalse(blocks[0])
        self.assertTrue(blocks[2])


if __name__ == "__main__":
    unittest.main()
