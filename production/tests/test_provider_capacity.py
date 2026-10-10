#!/usr/bin/env python3
"""供应商「模型没有可用通道」时的熔断策略测试（离线，不需要网络、ffmpeg 或额度）。

为什么要有这份测试：2026-10-10 华城连环杀人案（hwaseong1986）从 00:30Z 起连续 5 小时、
6 轮 Actions 运行全部 503「No available channel for model agnes-video-v2.0 under group
default (distributor)」，38 个镜头 0 个成功。旧策略把这种供应商侧容量问题当普通退避：
每镜试 8 次、每次冷却最长 300 秒，于是一整轮跑满 3 小时（run 38013901390）也一个素材都
没有——而且失败信息里挂着上一轮的旧错误，让人以为修好的 bug 又复发。

这段逻辑平时跑在 runner 上、要几十分钟才看得出结果，所以必须能离线跑一遍：

1. 认得出真实的 503 文案（也认得出它**不是**普通 502）；
2. 连续 N 轮通道不可用就整轮放弃，并且只发 N 次创建请求（不是 38×8 次）；
3. 有等待预算时按预算探，预算用尽才放弃；一次成功就清零计数；
4. 整条 ``generate.main()`` 在这种情况下落 ``phase=provider_capacity``、写出网关探针收据，
   并且不再把上一轮的 ``pipeline_error`` 留在 results.json 里。

Run:  python3 production/tests/test_provider_capacity.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock

PRODUCTION_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRODUCTION_DIR))
sys.path.insert(0, str(PRODUCTION_DIR / "hwaseong1986"))

import agnes_video  # noqa: E402

# 每个项目目录里都有一个 generate.py，而 test_dahlia*.py 会把 production/dahlia 插到
# sys.path 最前面 —— 直接 `import generate` 在整条测试跑起来时会拿到 dahlia 的那份
# （实测：单跑 8 passed，跑全套 5 failed）。所以按文件路径加载，并起个不会撞车的名字。
GENERATE_PATH = PRODUCTION_DIR / "hwaseong1986" / "generate.py"
_spec = importlib.util.spec_from_file_location("hwaseong1986_generate", GENERATE_PATH)
generate = importlib.util.module_from_spec(_spec)
sys.modules["hwaseong1986_generate"] = generate
_spec.loader.exec_module(generate)

# 2026-10-10 从 production/hwaseong1986/results.json 里原样抄下来的真实错误文案。
REAL_CHANNEL_ERROR = (
    "Could not create video task after 1 attempts; last problem: HTTP 503: No available "
    "channel for model agnes-video-v2.0 under group default (distributor) "
    "(request id: 20261010053223432997612R7RE8mwt)"
)


class FakeGate:
    """记录 defer / wait 调用，不真的睡。

    不能靠 patch time.sleep 来跳过 75 秒节流：RequestGate 的等待循环读的是真
    time.monotonic，睡 0 秒会让它原地空转到超时（这份测试第一次跑就是这么挂 10 分钟的）。
    所以整条 main() 的用例直接把 generate.RequestGate 换成它。
    """

    def __init__(self, minimum_interval=75.0, clock=None, sleep=None):
        self.deferred = []
        self.waits = 0
        self.creations = 0

    def defer(self, seconds):
        self.deferred.append(seconds)

    def wait_unblocked(self, deadline):
        self.waits += 1

    def acquire_creation(self, deadline):
        self.creations += 1


class FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class ChannelUnavailableRecognitionTests(unittest.TestCase):
    def test_recognises_the_real_production_error(self):
        self.assertTrue(generate.channel_unavailable(REAL_CHANNEL_ERROR))

    def test_recognises_it_whatever_the_model_name_is(self):
        """下线的是 agnes-video-v2.0，但换成 2.5 之后同样的文案也要认得出来。"""
        self.assertTrue(generate.channel_unavailable(
            "HTTP 503: No available channel for model agnes-video-2.5 under group default (distributor)"))

    def test_a_plain_502_is_not_channel_capacity(self):
        """普通 5xx 仍然走原来的退避重试，不能被误判成「等通道」。"""
        self.assertFalse(generate.channel_unavailable(
            "Could not create video task after 1 attempts; last problem: HTTP 502: Bad Gateway"))

    def test_provider_capacity_is_an_error(self):
        self.assertTrue(issubclass(generate.ProviderCapacity, Exception))


class CapacityRecognitionTests(unittest.TestCase):
    """「排队满」和「没通道」都是容量问题，要走同一套共享退避，不是每镜各自撞 8 次。"""

    def test_recognises_a_full_video_queue(self):
        self.assertEqual(generate.capacity_problem(
            "Could not create video task after 1 attempts; last problem: HTTP 503: "
            "video queue is full, please retry later (request id: 2026...)"),
            "供应商视频排队已满")

    def test_still_recognises_a_missing_channel(self):
        self.assertEqual(generate.capacity_problem(REAL_CHANNEL_ERROR), "该模型当前没有可用通道")

    def test_a_plain_502_is_not_a_capacity_problem(self):
        self.assertIsNone(generate.capacity_problem(
            "Could not create video task after 1 attempts; last problem: HTTP 502: Bad Gateway"))


class QuotaRecognitionTests(unittest.TestCase):
    def test_recognises_the_real_zero_balance_error(self):
        self.assertTrue(generate.quota_exhausted(
            "Authentication failed (HTTP 403): Insufficient user quota, remaining: ＄0.000000"))

    def test_channel_capacity_is_not_misread_as_quota(self):
        self.assertFalse(generate.quota_exhausted(REAL_CHANNEL_ERROR))
        self.assertTrue(generate.channel_unavailable(REAL_CHANNEL_ERROR))

    def test_a_generic_403_is_not_quota(self):
        """普通鉴权失败要照原样报出来（提示去查 key），不能被当成「去充值」。"""
        self.assertFalse(generate.quota_exhausted(
            "Authentication failed (HTTP 403): Invalid API key"))


class ChannelBreakerTests(unittest.TestCase):
    def test_gives_up_after_the_error_limit_and_defers_the_shared_gate(self):
        gate = FakeGate()
        records = []
        breaker = generate.ChannelBreaker(
            gate, deadline=10 ** 9, error_limit=3, wait_minutes=0,
            clock=FakeClock(), record=lambda **values: records.append(values))
        reason = generate.capacity_problem(REAL_CHANNEL_ERROR)
        for _ in range(2):
            self.assertTrue(breaker.observe("S01", REAL_CHANNEL_ERROR, reason=reason))
        self.assertEqual(len(gate.deferred), 2)
        self.assertTrue(all(seconds == generate.CHANNEL_COOLDOWN_SECONDS for seconds in gate.deferred))
        with self.assertRaises(generate.ProviderCapacity) as caught:
            breaker.observe("S01", REAL_CHANNEL_ERROR, reason=reason)
        # 放弃时必须说清楚是供应商侧容量问题，并带上供应商原文
        self.assertIn("没有可用通道", str(caught.exception))
        self.assertIn("No available channel", str(caught.exception))
        self.assertTrue(breaker.abort.is_set(), "放弃时必须置 ABORT，让另一个 worker 立刻停")
        self.assertEqual(len(records), 3)
        self.assertEqual([r["round_no"] for r in records], [1, 2, 3])
        self.assertEqual(records[-1]["outage"]["attempts"], 3)

    def test_wait_budget_keeps_probing_until_it_is_spent(self):
        gate = FakeGate()
        clock = FakeClock()
        breaker = generate.ChannelBreaker(
            gate, deadline=10 ** 9, error_limit=2, wait_minutes=10, clock=clock)
        clock.advance(60)
        self.assertTrue(breaker.observe("S01", REAL_CHANNEL_ERROR))   # 第 1 轮
        self.assertTrue(breaker.observe("S01", REAL_CHANNEL_ERROR))   # 第 2 轮 → 进入等待
        self.assertEqual(gate.waits, 1)
        self.assertEqual(breaker.state["consecutive"], 0, "等待后计数要清零，才能继续探")
        clock.advance(11 * 60)                                        # 预算（10 分钟）用尽
        self.assertTrue(breaker.observe("S01", REAL_CHANNEL_ERROR))
        with self.assertRaises(generate.ProviderCapacity):
            breaker.observe("S01", REAL_CHANNEL_ERROR)

    def test_a_successful_creation_resets_the_counter(self):
        """通道恢复过一次，就不该把后面的偶发波动数成第 4 轮而放弃整轮。"""
        breaker = generate.ChannelBreaker(FakeGate(), deadline=10 ** 9, error_limit=3, clock=FakeClock())
        breaker.observe("S01", REAL_CHANNEL_ERROR)
        breaker.observe("S01", REAL_CHANNEL_ERROR)
        breaker.note_success()
        self.assertEqual(breaker.state["consecutive"], 0)
        self.assertTrue(breaker.observe("S02", REAL_CHANNEL_ERROR))
        self.assertTrue(breaker.observe("S02", REAL_CHANNEL_ERROR))
        self.assertEqual(breaker.state["attempts"], 4, "累计尝试次数不清零，收据里才看得出总共烧了多少次")


class RunAbortsOnProviderCapacityTests(unittest.TestCase):
    """整条 main() 在供应商没通道时的行为（stub 掉网络，不消耗任何额度）。"""

    def setUp(self):
        self.tmp = Path(__file__).resolve().parents[2] / "work" / "test-provider-capacity"
        self.results = self.tmp / "production" / "hwaseong1986" / "results.json"
        self.probe = self.tmp / "production" / "hwaseong1986" / "delivery" / "provider-probe.json"
        self.results.parent.mkdir(parents=True, exist_ok=True)
        self.probe.parent.mkdir(parents=True, exist_ok=True)
        self.created = []

        def failing_create(base_url, api_key, payload, retries, retry_delay):
            self.created.append(payload["prompt"][:20])
            raise agnes_video.Fatal(REAL_CHANNEL_ERROR)

        # 网关的模型清单：默认列出本片要的模型（换模型时不用改这份测试）。
        self.gateway_models = [generate.MODEL]

        def fake_http_json(method, url, api_key, payload=None, timeout=60):
            if "/dashboard/billing/" in url:      # 余额端点：收据里要能看出 key 有没有钱
                body = {"hard_limit_usd": 25.0} if url.endswith("subscription") else {"total_usage": 0}
                return agnes_video.HttpResult(200, body, json.dumps(body))
            body = {"data": [{"id": name} for name in self.gateway_models]}
            return agnes_video.HttpResult(200, body, json.dumps(body))

        patches = [
            mock.patch.object(generate, "ROOT", self.tmp),
            mock.patch.object(generate, "RESULTS", self.results),
            mock.patch.object(generate, "PROBE", self.probe),
            mock.patch.object(generate, "ensure_tools", lambda *a, **k: None),
            mock.patch.object(generate, "RequestGate", FakeGate),
            mock.patch.object(generate.agnes, "create_task", failing_create),
            mock.patch.object(generate.agnes, "http_json", fake_http_json),
            mock.patch.object(generate.time, "sleep", lambda seconds: None),
            mock.patch.dict(os.environ, {"AGNES_API_KEY": "test-key"}),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        # ABORT 是模块级单例：跑之前必须复位，否则上一个用例的状态会漏进来
        generate.ABORT.clear()

    def run_main(self, payload):
        argv = ["generate.py", "--payload", json.dumps(payload)]
        with mock.patch.object(sys, "argv", argv):
            return generate.main()

    def test_run_stops_after_the_error_limit_instead_of_burning_the_budget(self):
        self.results.write_text(json.dumps(
            {"project": "x", "shots": {}, "pipeline_error": "stale from run 123"}), encoding="utf-8")
        with self.assertRaises(generate.ProviderCapacity):
            self.run_main({"workers": 1, "channel_error_limit": 3, "wait_channel_minutes": 0})
        # 核心：38 个镜头没有各自去撞 8 次——整轮只发了 error_limit 次创建请求
        self.assertEqual(len(self.created), 3)
        doc = json.loads(self.results.read_text(encoding="utf-8"))
        self.assertEqual(doc["phase"], "provider_capacity")
        self.assertIn("没有可用通道", doc["pipeline_error"])
        self.assertNotIn("stale from run 123", json.dumps(doc, ensure_ascii=False),
                         "上一轮的失败原因不属于这一轮，必须清掉")
        outage = doc["provider_outage"]
        self.assertEqual(outage["consecutive_rounds"], 3)
        self.assertIn("No available channel", outage["last_error"])
        self.assertTrue(self.probe.is_file(), "网关探针收据要落到分支上")
        probe = json.loads(self.probe.read_text(encoding="utf-8"))
        self.assertTrue(probe["target_model_listed"])
        self.assertEqual(probe["http_status"], 200)
        # 换过 key 之后，靠指纹和余额判断跑的是哪一把、有没有钱（key 本身不进仓库）
        self.assertEqual(probe["api_key_last4"], "-key")
        self.assertEqual(len(probe["api_key_sha256_12"]), 12)
        self.assertEqual([b["http_status"] for b in probe["billing"]], [200, 200])
        self.assertIn("hard_limit_usd", probe["billing"][0]["excerpt"])
        self.assertNotIn("test-key", json.dumps(probe), "收据里绝不能出现 key 原文")

    def test_probe_records_that_the_model_is_not_on_the_gateway(self):
        """2026-10-10 的真实故障：agnes-video-v2.0 被下线，网关只剩 2.5 系列。

        那时连报 5 小时 503「No available channel」，谁都以为通道在波动；
        收据里这一行 target_model_listed=false 才是真正的原因，必须一直留着。
        """
        # 清单里故意**不含**本片要用的模型 —— 这就是 v2.0 那天的处境
        self.gateway_models = ["agnes-3.0-flash", "agnes-image-2.5-flash", "agnes-2.5-pro"]
        with self.assertRaises(generate.ProviderCapacity):
            self.run_main({"workers": 1, "channel_error_limit": 1, "wait_channel_minutes": 0})
        probe = json.loads(self.probe.read_text(encoding="utf-8"))
        self.assertFalse(probe["target_model_listed"])
        self.assertEqual(probe["model"], generate.MODEL)
        self.assertEqual(probe["http_status"], 200)
        doc = json.loads(self.results.read_text(encoding="utf-8"))
        self.assertEqual(doc["model"], generate.MODEL,
                         "results.json 的 model 要跟着当前模型走，否则 render.py 的模型闸门会拒绝出片")

    def test_zero_balance_stops_the_whole_run_after_one_request(self):
        """2026-10-10T07:00Z 实测：payload 改对之后撞上的最后一道墙是余额 ＄0.000000。

        额度见底不是某一镜的问题，重试一万次也不会变好——所以一次请求就要停整轮，
        而不是 38 个镜头各撞一次 403、把一整轮 runner 时间烧光。
        """
        def no_quota(base_url, api_key, payload, retries, retry_delay):
            self.created.append(payload["prompt"][:20])
            raise agnes_video.Fatal(
                "Authentication failed (HTTP 403): Insufficient user quota, remaining: "
                "＄0.000000 (request id: 20261010065941375220354tcOnQaCa). Check AGNES_API_KEY.")

        with mock.patch.object(generate.agnes, "create_task", no_quota):
            with self.assertRaises(generate.QuotaExhausted):
                self.run_main({"workers": 1})
        self.assertEqual(len(self.created), 1, "额度见底应该一次请求就停整轮")
        doc = json.loads(self.results.read_text(encoding="utf-8"))
        self.assertEqual(doc["phase"], "quota_exhausted")
        self.assertIn("额度", doc["pipeline_error"])
        self.assertIn("Insufficient user quota", doc["pipeline_error"])

    def test_a_full_queue_uses_the_shared_breaker_not_per_shot_retries(self):
        """2026-10-10T07:37Z 实测：flash 档 720P 过了额度闸门，报的是
        「video queue is full, please retry later」。这种要整轮共享退避 + 等待预算，
        而不是让 38 个镜头各自撞 8 次。"""
        def queue_full(base_url, api_key, payload, retries, retry_delay):
            self.created.append(payload["prompt"][:20])
            raise agnes_video.Fatal(
                "Could not create video task after 1 attempts; last problem: HTTP 503: "
                "video queue is full, please retry later (request id: 202610100737537410334449NJkN7tr)")

        with mock.patch.object(generate.agnes, "create_task", queue_full):
            with self.assertRaises(generate.ProviderCapacity):
                self.run_main({"workers": 1, "channel_error_limit": 2, "wait_channel_minutes": 0})
        self.assertEqual(len(self.created), 2)
        doc = json.loads(self.results.read_text(encoding="utf-8"))
        self.assertEqual(doc["phase"], "provider_capacity")
        self.assertEqual(doc["provider_outage"]["reason"], "供应商视频排队已满")
        self.assertIn("排队已满", doc["pipeline_error"])

    def test_a_stale_pipeline_error_is_dropped_on_a_clean_run(self):
        """所有镜头都因请求本身失败时 phase=generation_incomplete，不写 pipeline_error；
        这时上一轮留下的旧错误必须已经被清掉，否则 results.json 会一直挂着它。"""
        self.results.write_text(json.dumps(
            {"project": "x", "shots": {}, "pipeline_error": "stale from run 123"}), encoding="utf-8")

        def rejected(base_url, api_key, payload, retries, retry_delay):
            raise agnes_video.Fatal("Request rejected (HTTP 400): prompt is empty")

        with mock.patch.object(generate.agnes, "create_task", rejected):
            self.assertEqual(self.run_main({"workers": 1}), 1)
        doc = json.loads(self.results.read_text(encoding="utf-8"))
        self.assertEqual(doc["phase"], "generation_incomplete")
        self.assertNotIn("pipeline_error", doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
