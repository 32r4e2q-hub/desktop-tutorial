"""安城双尸案：离线闸门 + 调度器仿真（不触网、不消耗 Agnes 额度）。"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "anseong2007"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"anseong_{name}", PROJECT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PROJECT))
    spec.loader.exec_module(module)
    return module


class StoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))

    def test_thirty_shots_180_seconds_agnes_seconds(self):
        shots = self.story["shots"]
        self.assertEqual(len(shots), 30)
        self.assertEqual(sum(s["duration"] for s in shots), 180)
        for s in shots:
            self.assertTrue(4 <= s["duration"] <= 9, s["id"])

    def test_prompt_order_style_refs_anchors_negative(self):
        for s in self.story["shots"]:
            p = s["prompt"]
            self.assertTrue(p.startswith("【STYLE】"), s["id"])
            self.assertTrue(p.endswith(self.story["negative"]), s["id"])
            for c in s["character_anchors"]:
                self.assertIn(self.story["anchors"][c], p)
            self.assertLessEqual(len(s["reference_images"]), 5)

    def test_narration_fits_shot(self):
        """解说与片段等长：口播字数 ÷ 可用时长 ≤ 4.3 字/秒（加速上限内）。"""
        for s in self.story["shots"]:
            usable = s["duration"] - (1.0 if s["id"] == "S30" else 0.35)
            self.assertLessEqual(s["spoken_chars"] / usable, 4.3, s["id"])

    def test_no_violence_words_in_visual_prompts(self):
        for s in self.story["shots"]:
            for word in ("枪", "血迹斑斑", "尸体被", "开枪"):
                self.assertNotIn(word, s["visual_prompt"], s["id"])

    def test_validate_offline(self):
        gen = load("generate_clips")
        gen.validate(self.story, require_refs=False)


class FakeAgnes:
    """Minimal stand-in for production/agnes_video.py with rate limits, queue-full and a failed task."""

    def __init__(self, real):
        self.real = real
        self.created, self.status_calls, self.lock = [], 0, threading.Lock()
        self.first_429_done = self.queue_full_done = False
        self.failed_once = set()

    def create_task(self, base, key, payload, retries, retry_delay):
        with self.lock:
            if not self.first_429_done:
                self.first_429_done = True
                raise self.real.RateLimited("HTTP 429: slow down", 0.05)
            if len(self.created) == 3 and not self.queue_full_done:
                self.queue_full_done = True
                raise self.real.Fatal("Could not create video task; last problem: HTTP 503: video queue is full")
            tid = f"task_{len(self.created):02d}"
            self.created.append((tid, payload["seed"]))
            return {"id": tid, "task_id": tid, "status": "queued"}

    def http_json(self, method, url, key, payload=None, timeout=60):
        with self.lock:
            self.status_calls += 1
            if self.status_calls == 2:
                return self.real.HttpResult(429, {"error": {"message": "too many video status queries"}}, "", 0.05)
        tid = url.split("video_id=")[1].split("&")[0]
        if tid == "task_01" and tid not in self.failed_once:
            self.failed_once.add(tid)
            return self.real.HttpResult(200, {"status": "failed", "error": {"message": "upload timed out", "code": "upload_timeout"}}, "")
        return self.real.HttpResult(200, {"status": "completed", "url": f"https://cdn.example/{tid}.mp4", "progress": 100}, "")

    def download(self, url, dest, retries, retry_delay):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(url.encode() * 64)
        return dest.stat().st_size


class SchedulerSimulation(unittest.TestCase):
    def test_queue_all_then_poll_with_limits(self):
        gen = load("generate_clips")
        fake = FakeAgnes(gen.agnes)
        # agnes_video 是全仓共享模块：只在本用例内替换，结束自动还原，不能串到别的测试
        for name in ("create_task", "http_json", "download"):
            patcher = patch.object(gen.agnes, name, getattr(fake, name))
            patcher.start()
            self.addCleanup(patcher.stop)
        tmp = Path(tempfile.mkdtemp())
        gen.RESULTS, gen.QA, gen.WORK = tmp / "results.json", tmp / "qa", tmp / "clips"
        gen.CREATE_STOP_MARGIN = 0.0
        gen.RATE_LIMIT_MIN_WAIT, gen.QUEUE_FULL_WAIT, gen.CAPACITY_WAIT = 0.05, 0.1, 0.5
        gen.CREATE_INTERVAL, gen.POLL_SPACING, gen.POLL_429_BACKOFF, gen.PER_TASK_MIN_REPOLL = 0.05, 0.0, 0.05, 0.0
        gen.inspect_clip = lambda path, sid: {"duration_seconds": 6.0, "width": 1280, "height": 720,
                                              "motion_mean_difference": 0.1}
        original_gate = gen.RequestGate
        gen.RequestGate = lambda interval, allow_fast_plan=True: original_gate(0.05, allow_fast_plan=True)
        story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
        shots = story["shots"][:6]
        receipts = gen.Receipts({"shots": {}}, publish=False)
        # make every freshly created task immediately pollable
        orig_update = receipts.update

        def update(sid, push=False, **values):
            if values.get("status") == "queued":
                values["next_poll_epoch"] = 0
            orig_update(sid, push=push, **values)
        receipts.update = update
        producer = gen.Producer(story, shots, "KEY", "https://x", time.monotonic() + 60, receipts, "0" * 40, set())
        start = time.monotonic()
        code = producer.run()
        self.assertLess(time.monotonic() - start, 30)
        self.assertEqual(code, 1)  # only 6 of 30 shots selected → phase pending for the rest
        rows = receipts.doc["shots"]
        for s in shots:
            self.assertEqual(rows[s["id"]]["status"], "completed", rows[s["id"]])
        # six shots + one automatic re-create for the failed task
        self.assertEqual(len(fake.created), 7)
        self.assertEqual(rows["S02"]["auto_retries"], 1)


class RealInspection(unittest.TestCase):
    """真 inspect_clip（不打桩）：2026-11-08 首轮生成里 16 镜因关闭容器后读 stream 属性而卡在 download_pending。"""

    def test_inspect_clip_on_real_mp4(self):
        import av
        import numpy as np
        gen = load("generate_clips")
        tmp = Path(tempfile.mkdtemp())
        clip = tmp / "S99.mp4"
        with av.open(str(clip), "w") as out:
            st = out.add_stream("libx264", rate=24)
            st.width, st.height, st.pix_fmt = 1280, 720, "yuv420p"
            for i in range(24 * 4):
                img = np.zeros((720, 1280, 3), dtype=np.uint8)
                img[:, (i * 13) % 1280:(i * 13) % 1280 + 80] = 200
                for packet in st.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
                    out.mux(packet)
            for packet in st.encode():
                out.mux(packet)
        with patch.object(gen, "QA", tmp / "qa"):
            info = gen.inspect_clip(clip, "S99")
        self.assertEqual((info["width"], info["height"], info["fps"]), (1280, 720, "24"))
        self.assertGreater(info["motion_mean_difference"], 0)
        self.assertTrue((tmp / "qa" / "S99.jpg").is_file())


class RenderPlan(unittest.TestCase):
    """render.py 的离线部分：不需要 ffmpeg / 原片。"""

    @classmethod
    def setUpClass(cls):
        cls.render = load("render")
        cls.story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))

    def test_timeline_grades_and_sfx_cover_every_shot(self):
        self.render.validate_timeline(self.story)
        for shot in self.story["shots"]:
            self.assertIn(self.render.grade_for(self.story, shot["id"]), self.render.GRADES)
            bed, events = self.render.SFX_PLAN[shot["id"]]
            self.assertIn(bed, self.render.BEDS)
        self.assertIn(("dig", 0.66, 0.9), self.render.SFX_PLAN["S14"][1])   # 黑场之后才有铁锹声

    def test_sfx_events_synthesize_without_music_bed(self):
        import numpy as np
        rng = np.random.default_rng(1)
        kinds = {k for _, evs in self.render.SFX_PLAN.values() for k, _, _ in evs} - {"cut_to_silence"}
        for kind in sorted(kinds):
            audio = self.render.event_audio(kind, rng, 3.0)
            self.assertTrue(np.isfinite(audio).all(), kind)
            self.assertLessEqual(len(audio), int(3.0 * self.render.RATE) + self.render.RATE, kind)

    def test_timing_plan_trims_slows_and_jump_cuts(self):
        shots = {s["id"]: s for s in self.story["shots"]}
        long_src = {"duration": 7.6}
        plan = self.render.timing_plan(shots["S03"], long_src)   # 7s 镜头
        self.assertEqual((plan["stretch"], plan["cuts"], plan["target_frames"]), (1.0, [], 168))
        self.assertGreater(self.render.timing_plan(shots["S03"], {"duration": 6.5})["stretch"], 1.0)
        with self.assertRaises(RuntimeError):                     # 太短：不许大幅慢放/冻结
            self.render.timing_plan(shots["S03"], {"duration": 5.5})
        fast = self.render.timing_plan(shots["S16"], {"duration": 6.6})
        self.assertEqual(len(fast["cuts"]), 2)

    def test_subtitles_wrap_and_highlight_gold(self):
        lines = self.render.split_subtitle("他用死者手机发短信：暂时躲一躲警察。他以为，天衣无缝。")
        self.assertTrue(all(len(x) <= 22 for x in lines))
        self.assertIn("&H005FC9F4", self.render.highlight("一台发动机", ["发动机"]))

    @unittest.skipUnless(__import__("shutil").which("ffmpeg"), "ffmpeg not installed (render workflow runs --plan-only)")
    def test_plan_only_runs_on_repository_state(self):
        report = self.render.plan_only()
        self.assertEqual(report["voice_too_long"], [])


if __name__ == "__main__":
    unittest.main()
