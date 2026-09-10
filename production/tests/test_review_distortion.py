"""畸变采样器的口径：每段取到帧、密扫步长对、脚手架形状对。

采样位置用逐帧变色的合成片验证（第 N 帧是什么颜色是已知的），
结论脚手架只搭不填——verdict 永远是人写的，工具只许写 pending。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
import review_distortion  # noqa: E402

try:
    import av
    import numpy as np
    from PIL import Image

    HAS_AV = True
except ImportError:
    HAS_AV = False


def rainbow_film(path: Path, frames: int = 60, fps: int = 30) -> None:
    """每帧纯色、随帧号变红的合成片：看颜色就知道取到了第几帧。"""
    container = av.open(str(path), "w")
    stream = container.add_stream("mpeg4", rate=fps)
    stream.width, stream.height, stream.pix_fmt = 160, 90, "yuv420p"
    for i in range(frames):
        plane = np.zeros((90, 160, 3), dtype=np.uint8)
        plane[:, :, 0] = min(255, i * 4)
        frame = av.VideoFrame.from_ndarray(plane, format="rgb24")
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)
    container.close()


class SamplingTests(unittest.TestCase):
    def setUp(self):
        if not HAS_AV:
            raise unittest.SkipTest("PyAV 未安装，跳过畸变采样测试")
        self.directory = Path(tempfile.mkdtemp(prefix="distortion-"))
        self.film = self.directory / "film.mp4"
        rainbow_film(self.film, frames=70)
        self.project = self.directory / "project"
        (self.project / "delivery").mkdir(parents=True)
        edl = [{"id": "S01", "kind": "agnes", "start_frame": 0, "end_frame": 30,
                "narration_id": "N01"},
               {"id": "S02", "kind": "agnes", "start_frame": 30, "end_frame": 60,
                "narration_id": "N01"},
               {"id": "S03", "kind": "graphic", "start_frame": 60, "end_frame": 70,
                "narration_id": "N02"}]
        (self.project / "delivery" / "edit-decision-list.json").write_text(
            json.dumps(edl, ensure_ascii=False), encoding="utf-8")
        self.work = self.directory / "work"

    def _mean_red(self, name: str) -> float:
        image = Image.open(self.work / "frames" / name).convert("RGB")
        return float(np.asarray(image)[:, :, 0].mean())

    def test_two_frames_per_segment_at_thirds(self):
        """每段 1/3、2/3 处各一帧：S01(0-30)取第 10、20 帧，红通道≈40、80。"""
        exit_code = review_distortion.main(
            ["--film", str(self.film), "--project", str(self.project),
             "--work", str(self.work)])
        self.assertEqual(exit_code, 0)
        checklist = json.loads(
            (self.work / "distortion-checklist.json").read_text(encoding="utf-8"))
        self.assertEqual(len(checklist["segments"]), 3)
        first = checklist["segments"][0]
        self.assertEqual(len(first["frames"]), 2)
        self.assertTrue(all(row["verdict"] == "pending" for row in checklist["segments"]))
        self.assertAlmostEqual(self._mean_red(first["frames"][0]), 40, delta=12)
        self.assertAlmostEqual(self._mean_red(first["frames"][1]), 80, delta=12)

    def test_dense_scan_only_hits_listed_shots(self):
        """密扫只扫 --dense-shots 点名的镜头，步长 0.5s。"""
        exit_code = review_distortion.main(
            ["--film", str(self.film), "--project", str(self.project),
             "--work", str(self.work), "--dense-shots", "S02"])
        self.assertEqual(exit_code, 0)
        checklist = json.loads(
            (self.work / "distortion-checklist.json").read_text(encoding="utf-8"))
        rows = {row["id"]: row for row in checklist["segments"]}
        self.assertEqual(rows["S01"]["dense_frames"], [])
        self.assertEqual(rows["S03"]["dense_frames"], [])
        # S02 占 1.0-2.0s：0.5s 步长落在段内（尾端留 0.2s 裕量）的只有 t=1.5 一格
        self.assertEqual(len(rows["S02"]["dense_frames"]), 1)
        self.assertIn("t1.5s", rows["S02"]["dense_frames"][0])
        self.assertTrue(any(name.startswith("dense-sheet-")
                            for name in checklist["sheets"]))

    def test_sheets_group_by_chapter(self):
        review_distortion.main(
            ["--film", str(self.film), "--project", str(self.project),
             "--work", str(self.work)])
        self.assertTrue((self.work / "sheet-N01.jpg").is_file())
        self.assertTrue((self.work / "sheet-N02.jpg").is_file())
