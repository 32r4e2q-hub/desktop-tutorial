"""转制核查的口径：期望间距公式、重复帧检测、EDL 拼接。

核心断言只有一句：24fps nearest 抽成 30fps，重复帧主间距必须是 5；
dahlia 实测 24 个 agnes 段全过，新片子也一样。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
import review_transcode  # noqa: E402

try:
    import av  # noqa: F401
    import numpy as np

    HAS_AV = True
except ImportError:
    HAS_AV = False


def make_film(path: Path, colors: list[tuple[int, int, int]], fps: int = 30) -> None:
    """按给定逐帧颜色合成测试片（mpeg4，无需系统 ffmpeg）。"""
    container = av.open(str(path), "w")
    stream = container.add_stream("mpeg4", rate=fps)
    stream.width, stream.height, stream.pix_fmt = 160, 90, "yuv420p"
    for color in colors:
        plane = np.zeros((90, 160, 3), dtype=np.uint8)
        plane[:, :] = color
        frame = av.VideoFrame.from_ndarray(plane, format="rgb24")
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)
    container.close()


def nearest_24_to_30_frames(source_colors: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """模拟 nearest 24->30：每 4 个源帧出 5 个输出帧（第 2 帧重复一次）。"""
    out = []
    for i in range(0, len(source_colors), 4):
        group = source_colors[i:i + 4]
        if len(group) < 4:
            break
        out.extend([group[0], group[1], group[1], group[2], group[3]])
    return out


class IntervalTests(unittest.TestCase):
    def test_unity_stretch_gives_five(self):
        self.assertEqual(review_transcode.expected_interval(1.0), 5)

    def test_slow_motion_matches_dahlia_measurements(self):
        """dahlia 实测：1.25x 主间距 3，1.063x 主间距 4，1.176x 主间距 3。"""
        self.assertEqual(review_transcode.expected_interval(1.25), 3)
        self.assertEqual(review_transcode.expected_interval(1.063), 4)
        self.assertEqual(review_transcode.expected_interval(1.176), 3)

    def test_absurd_stretch_is_rejected(self):
        with self.assertRaises(ValueError):
            review_transcode.expected_interval(0.5)


class SpliceTests(unittest.TestCase):
    def test_a_gap_is_found(self):
        edl = [{"id": "S01", "start_frame": 0, "end_frame": 100},
               {"id": "S02", "start_frame": 105, "end_frame": 200}]
        result = review_transcode.check_splice(edl, 200)
        self.assertFalse(result["seamless"])
        self.assertEqual(len(result["gaps"]), 1)

    def test_seamless_edl_passes(self):
        edl = [{"id": "S01", "start_frame": 0, "end_frame": 100},
               {"id": "S02", "start_frame": 100, "end_frame": 200}]
        result = review_transcode.check_splice(edl, 200)
        self.assertTrue(result["seamless"])
        self.assertTrue(result["frames_match"])


class EndToEndTests(unittest.TestCase):
    def setUp(self):
        if not HAS_AV:
            raise unittest.SkipTest("PyAV 未安装，跳过转制端到端测试")
        self.directory = Path(tempfile.mkdtemp(prefix="transcode-"))

    def _project(self, kinds_and_stretch):
        project = self.directory / "project"
        (project / "delivery").mkdir(parents=True)
        edl, frame = [], 0
        for i, (kind, stretch) in enumerate(kinds_and_stretch):
            row = {"id": f"S{i + 1:02d}", "kind": kind, "start_frame": frame,
                   "end_frame": frame + 50, "narration_id": "N01"}
            if kind == "agnes":
                row["time_stretch"] = stretch
            edl.append(row)
            frame += 50
        (project / "delivery" / "edit-decision-list.json").write_text(
            json.dumps(edl, ensure_ascii=False), encoding="utf-8")
        return project

    def test_nearest_24_to_30_passes(self):
        """nearest 24->30 合成片：dup 20%，主间距 5，verdict ok，退出 0。"""
        palette = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        colors = nearest_24_to_30_frames(palette * 10)[:50]
        film = self.directory / "film.mp4"
        make_film(film, colors)
        project = self._project([("agnes", 1.0)])
        work = self.directory / "work"
        exit_code = review_transcode.main(
            ["--film", str(film), "--project", str(project), "--work", str(work)])
        self.assertEqual(exit_code, 0)
        report = json.loads((work / "transcode-check.json").read_text(encoding="utf-8"))
        self.assertEqual(report["verdict"], "pass")
        shot = report["shots"][0]
        self.assertEqual(shot["verdict"], "ok")
        self.assertEqual(shot["expected_interval"], 5)
        self.assertIn(5, [v for v, _ in shot["spacing_top3"]])
        self.assertTrue(report["geometry"]["sar_is_square"])

    def test_every_frame_different_is_flagged(self):
        """每一帧都不同（没有重复帧）：期望间距不在 Top3，非 0 退出。"""
        colors = [(i * 5 % 256, i * 11 % 256, i * 17 % 256) for i in range(50)]
        film = self.directory / "film.mp4"
        make_film(film, colors)
        project = self._project([("agnes", 1.0)])
        work = self.directory / "work"
        exit_code = review_transcode.main(
            ["--film", str(film), "--project", str(project), "--work", str(work)])
        self.assertEqual(exit_code, 1)
        report = json.loads((work / "transcode-check.json").read_text(encoding="utf-8"))
        self.assertEqual(report["shots"][0]["verdict"], "needs_review")

    def test_graphic_segments_are_not_measured(self):
        """信息卡（zoompan 缓推）不适用重复帧口径：直接跳过不断言。"""
        film = self.directory / "film.mp4"
        make_film(film, [(10, 10, 10)] * 50)
        project = self._project([("graphic", 1.0)])
        work = self.directory / "work"
        exit_code = review_transcode.main(
            ["--film", str(film), "--project", str(project), "--work", str(work)])
        self.assertEqual(exit_code, 0)
        report = json.loads((work / "transcode-check.json").read_text(encoding="utf-8"))
        self.assertEqual(report["shots"], [])
