"""字幕 ASR 对齐的分句内插与阈值：coldcase_dna v2/v3 的失同步教训。

v2：whisper 繁体转写把字符匹配率打到 0.03-0.75，四章字幕静默回落到停顿
估算而整体漂移；v3：折叠修好覆盖率后，"一个分句零锚点就整章放弃"又把
N01/N04 打回估算。这里守两件事：中间分句缺词时按锚点内插且时间有序；
映射率过低时才允许回落停顿估算。
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "coldcase_dna"))
import align_audio  # noqa: E402

ROW = {"id": "TX", "start": 30.0, "raw_duration": 28.0, "tempo": 1.0,
       "text": "第一句话讲完。第二句话紧跟。第三句话收尾。"}
CLAUSES = ["第一句话讲完。", "第二句话紧跟。", "第三句话收尾。"]


def synth(skip_middle=False):
    words = []
    t = 0.0
    for clause in ("第一句话讲完", "第二句话紧跟", "第三句话收尾"):
        if skip_middle and clause == "第二句话紧跟":
            t += len(clause) * 0.3 + 0.3
            continue
        for c in clause:
            words.append({"word": c, "start": t, "end": t + 0.3})
            t += 0.3
        t += 0.3
    return words


class AlignedCuesTests(unittest.TestCase):
    def test_missing_middle_clause_is_interpolated_in_order(self):
        cues, coverage = align_audio.aligned_cues(ROW, CLAUSES, synth(skip_middle=True))
        self.assertIsNotNone(cues)
        self.assertEqual(len(cues), 3)
        for a, b in zip(cues, cues[1:]):
            self.assertLessEqual(a["end"], b["start"] + 1e-9)
        for cue in cues:
            self.assertGreater(cue["end"], cue["start"])
            self.assertGreaterEqual(cue["start"], ROW["start"])
            self.assertLessEqual(cue["end"], ROW["start"] + ROW["raw_duration"] / ROW["tempo"] + 1e-6)

    def test_too_sparse_mapping_falls_back_to_estimate(self):
        cues, coverage = align_audio.aligned_cues(ROW, CLAUSES, synth()[:1])
        self.assertIsNone(cues)
        self.assertLess(coverage, 0.6)

    def test_full_anchor_coverage_is_one(self):
        cues, coverage = align_audio.aligned_cues(ROW, CLAUSES, synth())
        self.assertEqual(coverage, 1.0)
        for a, b in zip(cues, cues[1:]):
            self.assertLessEqual(a["start"], b["start"])
            self.assertGreater(b["end"], b["start"])

    def test_normalize_folds_traditional_asr_output(self):
        self.assertEqual(align_audio.normalize("刑事偵察學術討論"),
                         align_audio.normalize("刑事侦察学术讨论"))



class PickBestTests(unittest.TestCase):
    def test_stops_at_acceptable_variant(self):
        row = dict(ROW); row["text"] = "第一句话讲完。"
        clauses = ["第一句话讲完。"]
        sparse = [{"word": "第", "start": 0.0, "end": 0.3}]
        full = [{"word": c, "start": i * 0.3, "end": i * 0.3 + 0.3}
                for i, c in enumerate("第一句话讲完")]
        cues, coverage = align_audio.pick_best(row, clauses, [sparse, full])
        self.assertIsNotNone(cues)
        self.assertEqual(coverage, 1.0)

    def test_keeps_best_when_all_weak(self):
        row = dict(ROW); row["text"] = "第一句话讲完。"
        clauses = ["第一句话讲完。"]
        weak1 = [{"word": "第", "start": 0.0, "end": 0.3}]
        weak2 = [{"word": "第", "start": 0.0, "end": 0.3},
                 {"word": "一", "start": 0.3, "end": 0.6}]
        cues, coverage = align_audio.pick_best(row, clauses, [weak1, weak2])
        self.assertIsNone(cues)
        self.assertAlmostEqual(coverage, 2 / 6, places=3)


if __name__ == "__main__":
    unittest.main()
