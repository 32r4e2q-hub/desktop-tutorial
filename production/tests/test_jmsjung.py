#!/usr/bin/env python3
"""jmsjung 的离线闸门：把 2026-10-16 探针那次的真实时间线写成测试。

为什么专门测这一段：熔断逻辑跑在 runner 上，要几十分钟才看得出结果，
而它一旦判错，整轮 30 镜会在「明明还能成功」的时候被掐死——
2026-10-17 11:36Z 就真的这么死过一次（run 39028605641，11 分 33 秒，0 镜）。

跑：python3 production/tests/test_jmsjung.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "jmsjung"


def load(name):
    """按文件路径加载，避免 production/ 下六个同名 generate.py 互相串味。"""
    spec = importlib.util.spec_from_file_location(f"jmsjung_{name}", PROJECT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generate = load("generate")


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class FakeGate:
    """只记账，不真睡：冷却与创建间隔都由 clock 推进模拟。"""

    def __init__(self, clock):
        self.clock = clock
        self.deferred = []

    def defer(self, seconds):
        self.deferred.append(seconds)

    def wait_unblocked(self, deadline):
        return None


class QueueLotteryTests(unittest.TestCase):
    """排队满 = 抽签，不是断线。"""

    def setUp(self):
        self.clock = FakeClock()
        self.gate = FakeGate(self.clock)
        self.records = []

    def breaker(self, **kwargs):
        return generate.ChannelBreaker(
            self.gate, deadline=10 ** 9, clock=self.clock,
            record=lambda **kw: self.records.append(kw), **kwargs)

    def test_real_2026_10_16_timeline_reaches_the_fifth_attempt(self):
        """10-16 实测：07:36/07:39/07:42/07:45 全满，07:48 受理。

        旧实现 error_limit=3、wait_budget=0 → 第 3 次就抛 ProviderCapacity，
        把一次**本来会成功**的运行判死。这个用例就是钉住那次真实的成功。
        """
        breaker = self.breaker(error_limit=3, wait_minutes=0)
        message = "HTTP 503: video queue is full, please retry later"
        for _ in range(4):
            self.assertTrue(breaker.observe("S01", message, reason="供应商视频排队已满",
                                            cooldown=180, kind="queue"))
            self.clock.advance(180)
        # 第 5 次：不抛，交给调用方发请求
        self.assertTrue(breaker.observe("S01", message, cooldown=180, kind="queue"))
        # 成功后计数清零
        breaker.note_success()
        self.assertEqual(breaker.state["queue_attempts"], 0)
        self.assertIsNone(breaker.queue_started)

    def test_queue_full_never_counts_as_a_missing_channel(self):
        breaker = self.breaker(error_limit=3, wait_minutes=0)
        for _ in range(30):
            breaker.observe("S01", "video queue is full", cooldown=180, kind="queue")
            self.clock.advance(180)
        self.assertEqual(breaker.state["consecutive"], 0)  # 通道连击计数没被污染

    def test_queue_full_stops_after_the_wall_clock_budget(self):
        """抽了 110 分钟还没开闸就诚实停，不无限空烧 runner。"""
        breaker = self.breaker(error_limit=3, queue_wait_minutes=110)
        message = "video queue is full"
        with self.assertRaises(generate.ProviderCapacity) as ctx:
            for _ in range(200):
                breaker.observe("S01", message, cooldown=180, kind="queue")
                self.clock.advance(180)
        self.assertIn("排队", str(ctx.exception))
        self.assertTrue(breaker.abort.is_set())

    def test_no_available_channel_still_breaks_after_three_rounds(self):
        """真·下线（no available channel）必须照旧快速放弃，别白等。"""
        breaker = self.breaker(error_limit=3, wait_minutes=0)
        with self.assertRaises(generate.ProviderCapacity) as ctx:
            for _ in range(3):
                breaker.observe("S01", "No available channel for model agnes-video-v2.0",
                                reason="该模型当前没有可用通道", cooldown=300, kind="channel")
                self.clock.advance(300)
        self.assertIn("没有可用通道", str(ctx.exception))


class CapacityClassificationTests(unittest.TestCase):
    def test_two_kinds_are_told_apart(self):
        self.assertEqual(generate.capacity_problem("HTTP 503: video queue is full")[2], "queue")
        self.assertEqual(
            generate.capacity_problem("No available channel for model agnes-video-2.5-flash")[2], "channel")
        self.assertIsNone(generate.capacity_problem("HTTP 400: prompt is required"))

    def test_queue_cooldown_is_180_seconds(self):
        """用户指定的「180 秒试探一次」。"""
        self.assertEqual(generate.QUEUE_COOLDOWN_SECONDS, 180)
        self.assertEqual(generate.capacity_problem("video queue is full")[1], 180)


class StoryTests(unittest.TestCase):
    """story.json 必须和上传的脚本对得上：30 镜 × 6 秒 = 180 秒。"""

    def setUp(self):
        self.story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))

    def test_thirty_shots_of_six_seconds(self):
        shots = self.story["shots"]
        self.assertEqual(len(shots), 30)
        self.assertEqual(sum(s["duration"] for s in shots), 180)
        for index, shot in enumerate(shots):
            self.assertEqual(shot["start"], index * 6, shot["id"])
            self.assertEqual(shot["duration"], 6, shot["id"])
            self.assertEqual(shot["id"], f"S{index + 1:02d}")

    def test_six_chapters_cover_the_timeline(self):
        chapters = self.story["chapters"]
        self.assertEqual(len(chapters), 6)
        self.assertEqual(sum(c["duration"] for c in chapters), 180)

    def test_every_shot_has_a_prompt_and_narration(self):
        for shot in self.story["shots"]:
            self.assertTrue(shot["prompt"].strip(), shot["id"])
            self.assertTrue(shot["narration"].strip(), shot["id"])

    def test_payload_stays_inside_the_2_5_flash_contract(self):
        """2.5-flash 只认 720P / mode / seconds 字符串，传 width、num_frames 就是 400。"""
        project = self.story
        shot = project["shots"][0]
        payload = generate.full_payload(project, shot)
        self.assertEqual(payload["model"], "agnes-video-2.5-flash")
        self.assertEqual(payload["size"], "720P")
        self.assertEqual(payload["mode"], "text")
        self.assertIsInstance(payload["seconds"], str)
        for banned in ("width", "height", "num_frames", "frame_rate", "negative_prompt", "resolution"):
            self.assertNotIn(banned, payload)

    def test_validate_passes(self):
        generate.validate(self.story)


if __name__ == "__main__":
    unittest.main(verbosity=2)
