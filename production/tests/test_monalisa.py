"""蒙娜丽莎失窃案（production/monalisa）的离线自检：本片新增 / 改过的逻辑各有一条守着。

1. clause_times.align（分组 DP）：句内换气（一句跨两个语音块）和逗号处不停顿（两句挤一个语音块）
   两种情况同时出现时，分句起点仍然落在真实位置（spector 的分块 DP 会把前者推迟 1 秒多）。
2. render.CUTS：每个切点都在分句起点前的停顿窗里；EDL 正好 180 秒；每个 Agnes 镜头 ≤ 6.7 秒、不慢放。
3. 三处逐字一致：screenplay.md、story.json、audio/manifest.json；配音文件 sha256 与清单一致。
4. clip_qa：人为埋进去的硬切和冻结帧能在正确的帧号上被抓到（有没有 OpenCV 都要能跑）。
"""
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production/monalisa"


def load(name):
    """按路径加载本项目的模块（模块名加 monalisa_ 前缀）：别的测试会先 import 同名的
    render / media / clause_times（dahlia、脚手架），直接 `import render` 会拿到别人的。"""
    key = f"monalisa_{name}"
    if key in sys.modules:
        return sys.modules[key]
    shared = ("media", "build_audio", "clause_times", "clip_qa", "render")
    saved = {k: sys.modules.pop(k) for k in shared if k in sys.modules}
    sys.path.insert(0, str(PROJECT))
    try:
        spec = importlib.util.spec_from_file_location(key, PROJECT / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(PROJECT))
        for k in shared:
            sys.modules.pop(k, None)
        sys.modules.update(saved)
    return module


clause_times = load("clause_times")
render = clause_times.load_render()


def synth(blocks, rate=clause_times.RATE, tail=0.25):
    """blocks: [(start, end), ...] 秒；块内是噪声（「语音」），块外静音。"""
    total = blocks[-1][1] + tail
    x = np.zeros(int(total * rate), np.float32)
    rng = np.random.default_rng(7)
    for a, b in blocks:
        i, j = int(a * rate), int(b * rate)
        x[i:j] = rng.uniform(-0.3, 0.3, j - i).astype(np.float32)
    return x


class GroupDPTest(unittest.TestCase):
    def test_breath_inside_clause_and_unpaused_comma(self):
        # 分句（字数）：甲 5、乙 10（中间换气）、丙 6 + 丁 4（逗号处没停）、戊 8；语速 0.2 s/字
        text = "一二三四五，一二三四五六七八九十，一二三四五六，一二三四，一二三四五六七八。"
        blocks = [(0.15, 1.15),              # 甲 5 字
                  (1.50, 2.70), (3.00, 3.80),  # 乙：6 字 + 换气 0.3 s + 4 字
                  (4.15, 6.15),              # 丙 + 丁 挤在一个块里（10 字）
                  (6.50, 8.10)]              # 戊 8 字
        _, rows = clause_times.align(text, synth(blocks))
        starts = [r["start"] for r in rows]
        expected = [0.15, 1.50, 4.15, 5.35, 6.50]
        self.assertEqual(len(rows), 5)
        for got, want in zip(starts, expected):
            self.assertAlmostEqual(got, want, delta=0.08, msg=f"{starts} vs {expected}")
        self.assertEqual(rows[1]["group"], "2块/1句")
        self.assertEqual(rows[2]["group"], "1块/2句")

    def test_real_narration_rates_are_plausible(self):
        table = json.loads((PROJECT / "audio/clause-times.json").read_text())
        for cid, entry in table.items():
            for c in entry["clauses"]:
                self.assertTrue(3.6 <= c["chars_per_second"] <= 7.5, (cid, c))


class CutsTest(unittest.TestCase):
    def test_cuts_sit_in_pause_windows(self):
        self.assertEqual(clause_times.check_cuts(), [])

    def test_edl_is_180s_and_no_slow_motion(self):
        story = json.loads((PROJECT / "story.json").read_text())
        table = json.loads((PROJECT / "audio/clause-times.json").read_text())
        durations = [table[c["id"]]["duration"] for c in story["chapters"]]
        usable = render.DURATION - render.INTRO - render.OUTRO - render.GAP * 5
        tempo = sum(durations) / usable
        self.assertTrue(0.86 <= tempo <= 1.10, tempo)
        start, rows = render.INTRO, []
        for c, d in zip(story["chapters"], durations):
            rows.append({"id": c["id"], "start": start, "end": start + d / tempo, "raw_duration": d, "tempo": tempo})
            start += d / tempo + render.GAP
        edl = render.make_edl(story, rows)
        self.assertEqual(edl[-1]["end_frame"], render.TOTAL_FRAMES)
        for e in edl:
            seconds = (e["end_frame"] - e["start_frame"]) / render.FPS
            if e["kind"] == "agnes":
                self.assertLessEqual(seconds, 6.7, e["id"])
                self.assertGreaterEqual(seconds, 1.8, e["id"])


class VerbatimTest(unittest.TestCase):
    def test_three_copies_agree_and_audio_matches_receipts(self):
        story = json.loads((PROJECT / "story.json").read_text())
        manifest = json.loads((PROJECT / "audio/manifest.json").read_text())
        screenplay = (PROJECT / "screenplay.md").read_text()
        receipts = {c["id"]: c for c in manifest["clips"]}
        self.assertEqual(manifest["voice_id"], "voice-00")
        for ch in story["chapters"]:
            self.assertIn(ch["text"], screenplay)
            self.assertEqual(receipts[ch["id"]]["text"], ch["text"])
            digest = hashlib.sha256((PROJECT / "audio" / f"{ch['id']}.mp3").read_bytes()).hexdigest()
            self.assertEqual(receipts[ch["id"]]["sha256"], digest)


@unittest.skipUnless(shutil.which("ffmpeg"), "needs ffmpeg")
class ClipQATest(unittest.TestCase):
    def test_planted_cut_and_freeze_are_found(self):
        clip_qa = load("clip_qa")
        with tempfile.TemporaryDirectory() as tmp:
            clip = Path(tmp) / "planted.mp4"
            # 0–1.5 s 慢速缩放的分形 → 1.5 s 硬切到彩条测试图；分形段第 12–20 帧冻结
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y",
                 "-f", "lavfi", "-i", "mandelbrot=size=640x360:rate=24",
                 "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24",
                 "-filter_complex",
                 "[0:v]trim=duration=1.5,setpts=PTS-STARTPTS,split[m1][m2];"
                 "[m1][m2]freezeframes=first=12:last=20:replace=12[a];"
                 "[1:v]trim=duration=1.0,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1[v]",
                 "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(clip)],
                check=True)
            summary, full = clip_qa.analyze(clip, tmp, "T01", fps=24.0)
            kinds = {e["type"]: e for e in summary["events"]}
            self.assertIn("hard_cut", kinds)
            # 1.5 s × 24 fps = 36 帧；trim+freezeframes+concat 这条链在 ffmpeg 7 上实测多出 1 帧（换场在第 37 帧），
            # 所以容差 ±1 帧——要抓的是「标在换场那一帧上」，不是 ffmpeg 的滤镜细节
            self.assertLessEqual(abs(kinds["hard_cut"]["peak_frame"] - 36), 1)
            self.assertIn("freeze", kinds)
            self.assertLessEqual(abs(kinds["freeze"]["start_frame"] - 12), 1)
            self.assertLessEqual(abs(kinds["freeze"]["end_frame"] - 20), 1)
            self.assertEqual(summary["auto_verdict"], "review")
            self.assertEqual(len(full["per_frame"]["mad"]), summary["frames_analyzed"])
            for name in ("T01-dense.jpg", "T01-flags.jpg"):
                self.assertTrue((Path(tmp) / name).stat().st_size > 1000)


class OscillationTest(unittest.TestCase):
    """clip_qa v2：S20 首版开门后那种「一帧一颤」要被抓到；平滑运镜、起止缓入定格、单帧起步不能误报。"""

    def series(self, osc_from=None, amp=0.6):
        n = 169
        t = np.arange(n)
        mad = np.clip(3.0 * np.sin(np.pi * t / (n - 1)), 0.05, None)      # 缓入 → 匀速 → 缓出
        mad[:12] = 0.05                                                    # 开头 0.5 s 定格（HOLD）
        mad[9] = 2.4                                                       # 单帧突然起步（S02 那种）
        flow = mad / 7.0
        if osc_from is not None:
            saw = np.array([(-1) ** k for k in range(n - osc_from)], float)
            mad[osc_from:] += amp * saw
            flow[osc_from:] += amp / 7.0 * saw
        zeros = np.zeros(n)
        return {"mad": mad, "tv": zeros + 0.01, "luma": zeros + 60.0, "flow": flow,
                "morph": zeros + 8.0, "sharp": zeros + 900.0}

    def test_sawtooth_is_flagged_where_it_starts(self):
        clip_qa = load("clip_qa")
        ev = [e for e in clip_qa.find_events(self.series(osc_from=120), 24.0) if e["type"] == "oscillation"]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["severity"], "high")
        self.assertLessEqual(abs(ev[0]["start_frame"] - 120), 8)

    def test_smooth_motion_and_holds_are_not(self):
        clip_qa = load("clip_qa")
        kinds = {e["type"] for e in clip_qa.find_events(self.series(), 24.0)}
        self.assertNotIn("oscillation", kinds)

    def test_real_clips_never_flag_an_approved_shot(self):
        """真实素材校准：逐帧数组重算事件，**人工复审判「通过」的镜头一个都不许报颤帧**（误报）。
        判了重生成的（S20、S33 首版）报出来是对的；重生成后 qa/Sxx.json 换成新素材，复审行也跟着改，
        这条不变式始终成立。结论从 qa-review.md 的表里读，不在测试里写死镜头号。"""
        clip_qa = load("clip_qa")
        verdicts = {}
        for line in (PROJECT / "qa-review.md").read_text().splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and re.fullmatch(r"S\d\d", cells[0]):
                verdicts[cells[0]] = cells[1]
        approved = {sid for sid, v in verdicts.items() if "通过" in v and "重生成" not in v}
        self.assertGreaterEqual(len(approved), 10)
        flagged = []
        for path in sorted((PROJECT / "qa").glob("S*.json")):
            qa = json.loads(path.read_text())
            if "frame_qa" not in qa or path.stem not in approved:
                continue
            m = {k: np.asarray(v, float) for k, v in qa["frame_qa"]["per_frame"].items()}
            if any(e["type"] == "oscillation" for e in clip_qa.find_events(m, 24.0)):
                flagged.append(path.stem)
        self.assertEqual(flagged, [], "颤帧检测误报了人工判通过的镜头")

if __name__ == "__main__":
    unittest.main()
