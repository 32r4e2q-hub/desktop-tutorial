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


class RoundEndClassificationTests(unittest.TestCase):
    """一轮跑完还有镜头没成：「免费池没开闸」必须判成容量（rc=42 接力），不能伪装成真 bug。

    2026-10-17 run 39037939402 实测：57 次抽签只中 S01，预算用尽后其余 29 镜的失败文案是
    ``Provider cooldown would exceed the generation budget; saved tasks can be resumed``。
    旧代码把它当普通失败 → rc=1、phase=generation_incomplete → auto_resume 按契约停摆，
    自动接力链就此断裂。这组用例就是钉住「冷却顶穿预算 = 容量，不是 bug」。
    """

    def test_cooldown_overrun_counts_as_capacity(self):
        self.assertTrue(generate.capacity_related_error(
            "Provider cooldown would exceed the generation budget; saved tasks can be resumed"))

    def test_queue_full_counts_as_capacity(self):
        self.assertTrue(generate.capacity_related_error(
            "Could not create video task after 1 attempts; last problem: HTTP 503: "
            "video queue is full, please retry later"))

    def test_channel_unavailable_counts_as_capacity(self):
        self.assertTrue(generate.capacity_related_error(
            "No available channel for model agnes-video-2.5-flash under group default"))

    def test_saved_task_budget_note_counts_as_capacity(self):
        self.assertTrue(generate.capacity_related_error(
            "Generation budget reached; task ID was saved for resumption"))

    def test_real_bugs_are_not_capacity(self):
        self.assertFalse(generate.capacity_related_error("HTTP 400: size must be one of 720P"))
        self.assertFalse(generate.capacity_related_error("Downloaded file does not match its receipt: S07"))
        self.assertFalse(generate.capacity_related_error("AGNES_API_KEY is unavailable to this workflow"))
        self.assertFalse(generate.capacity_related_error(None))
        self.assertFalse(generate.capacity_related_error(""))

    def test_run_39037939402_replay_is_provider_capacity(self):
        """按 run 39037939402 的真实收尾数据复现：S01 成、其余 29 镜全是
        「冷却顶穿预算」，breaker 记了 57 次容量事件 → 必须判 42/provider_capacity。"""
        overrun = "Provider cooldown would exceed the generation budget; saved tasks can be resumed"
        shots = {"S01": {"id": "S01", "status": "completed", "error": None}}
        for i in range(2, 31):
            shots["S%02d" % i] = {"id": "S%02d" % i, "status": "failed", "error": overrun}
        required = ["S%02d" % i for i in range(1, 31)]
        code, phase, bugs = generate.classify_incomplete_round(shots, required, 57)
        self.assertEqual(code, 42)
        self.assertEqual(phase, "provider_capacity")
        self.assertEqual(bugs, [])

    def test_one_real_bug_still_stops_the_round(self):
        """混进一个 400 参数错误就必须按真 bug 停，不能拿容量当遮羞布。"""
        overrun = "Provider cooldown would exceed the generation budget; saved tasks can be resumed"
        shots = {"S01": {"id": "S01", "status": "completed", "error": None},
                 "S02": {"id": "S02", "status": "failed", "error": overrun},
                 "S03": {"id": "S03", "status": "failed", "error": "HTTP 400: size must be one of 720P"}}
        code, phase, bugs = generate.classify_incomplete_round(shots, ["S01", "S02", "S03"], 12)
        self.assertEqual(code, 1)
        self.assertEqual(phase, "generation_incomplete")
        self.assertEqual(bugs, ["S03"])

    def test_no_capacity_pressure_is_not_capacity(self):
        """一轮里一次容量事件都没有，却还有镜头没成 → 不是供应商的问题。"""
        shots = {"S01": {"id": "S01", "status": "failed", "error": "Downloaded file does not match its receipt: S01"}}
        code, phase, bugs = generate.classify_incomplete_round(shots, ["S01"], 0)
        self.assertEqual(code, 1)
        self.assertEqual(bugs, ["S01"])


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


class AutoResumeTests(unittest.TestCase):
    """排队满要能自动接力，但连续零产出必须停。"""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.req = self.dir / "GEN_REQUEST"
        self.res = self.dir / "results.json"
        self.req.write_text('{"round":1}\n', encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write_results(self, phase, completed):
        shots = {f"S{i:02d}": {"status": "completed" if i < completed else "provider_unavailable"}
                 for i in range(1, 31)}
        self.res.write_text(json.dumps({"phase": phase, "shots": shots}), encoding="utf-8")

    def test_queue_full_resumes(self):
        auto_resume = load("auto_resume")
        self.write_results("provider_capacity", 0)
        verdict, msg = auto_resume.decide(self.req, self.res, rc=42)
        self.assertEqual(verdict, "resume")
        self.assertEqual(json.loads(self.req.read_text())["round"], 2)

    def test_quota_exhausted_does_not_resume(self):
        auto_resume = load("auto_resume")
        self.write_results("quota_exhausted", 0)
        self.assertEqual(auto_resume.decide(self.req, self.res, rc=43)[0], "skip")

    def test_bug_does_not_resume(self):
        auto_resume = load("auto_resume")
        self.write_results("pipeline_failed", 0)
        self.assertEqual(auto_resume.decide(self.req, self.res, rc=1)[0], "skip")

    def test_three_stale_rounds_stop(self):
        auto_resume = load("auto_resume")
        self.write_results("provider_capacity", 0)
        self.req.write_text(json.dumps({"round": 4, "round_started_completed": 0, "stale_rounds": 2}),
                            encoding="utf-8")
        verdict, msg = auto_resume.decide(self.req, self.res, rc=42)
        self.assertEqual(verdict, "stop")
        self.assertIn("零进展", msg)

    def test_progress_resets_the_stale_counter(self):
        auto_resume = load("auto_resume")
        self.write_results("provider_capacity", 5)   # 这轮多了 5 镜
        self.req.write_text(json.dumps({"round": 4, "round_started_completed": 0, "stale_rounds": 2}),
                            encoding="utf-8")
        verdict, _ = auto_resume.decide(self.req, self.res, rc=42)
        self.assertEqual(verdict, "resume")
        self.assertEqual(json.loads(self.req.read_text())["stale_rounds"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
