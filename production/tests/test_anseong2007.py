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


if __name__ == "__main__":
    unittest.main()
