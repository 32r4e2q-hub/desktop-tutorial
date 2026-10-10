#!/usr/bin/env python3
"""锁住 agnes-video-2.5 的请求形状（离线，不发请求）。

为什么要这份测试：2026-10-10 供应商把 `agnes-video-v2.0` 下线、换上 `agnes-video-2.5`，
请求体字段整套变了。旧实现把 `width/height/num_frames/frame_rate/negative_prompt` 全填上，
新模型一律 400；而 `seconds` 必须是**字符串**、`size` 必须是档位名、`mode` 必填——
这些都不是猜出来的，是从 https://agnes-ai.com/en/docs/agnes-video-25 抄来的
（原文摘录留在 `production/hwaseong1986/delivery/payload-schema-probe.json` 的 docs 段）。

这份测试守的就是「照着文档拼」这件事：谁把某个被拒字段加回来，离线自检立刻红，
不用再烧一轮 Actions 才发现。

Run:  python3 production/tests/test_payload_shape.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

PRODUCTION_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = PRODUCTION_DIR / "hwaseong1986"
sys.path.insert(0, str(PRODUCTION_DIR))
sys.path.insert(0, str(PROJECT_DIR))

# 每个项目目录都有一个 generate.py，按文件路径加载，避免撞上别的项目那份。
_spec = importlib.util.spec_from_file_location("hwaseong1986_generate", PROJECT_DIR / "generate.py")
generate = importlib.util.module_from_spec(_spec)
sys.modules["hwaseong1986_generate"] = generate
_spec.loader.exec_module(generate)

_policy_spec = importlib.util.spec_from_file_location(
    "hwaseong1986_model_policy", PROJECT_DIR / "model_policy.py")
model_policy = importlib.util.module_from_spec(_policy_spec)
sys.modules["hwaseong1986_model_policy"] = model_policy
_policy_spec.loader.exec_module(model_policy)

PROJECT = json.loads((PROJECT_DIR / "story.json").read_text(encoding="utf-8"))
SHOTS = {s["id"]: s for s in PROJECT["shots"]}

# 文档《Parameter Restrictions》：传了就 400 的字段
BANNED = ("width", "height", "fps", "num_frames", "frame_rate", "duration",
          "resolution", "negative_prompt", "quality", "num_inference_steps")


def payload_of(shot_id: str) -> dict:
    return generate.full_payload(PROJECT, SHOTS[shot_id])


class DocumentedRequestShapeTests(unittest.TestCase):
    def test_text_shot_uses_the_documented_fields(self):
        payload = payload_of("S01")
        # 免费方案定型：flash 档（主档要余额，实测两把 key 都是 ＄0.000000）
        self.assertEqual(payload["model"], "agnes-video-2.5-flash")
        self.assertEqual(payload["mode"], "text")
        self.assertIsInstance(payload["seconds"], str, "seconds 必须是字符串，传数字网关会 invalid_json")
        self.assertTrue(4 <= int(payload["seconds"]) <= 12, "文档只接受 4–12 秒")
        self.assertIn(payload["size"], ("720P", "1080P", "1K", "2K"), "size 是档位名，不是像素")
        self.assertEqual(payload["size"], "720P", "flash 档只认 720P")
        self.assertEqual(payload["aspect_ratio"], "16:9")
        self.assertEqual(payload["n"], 1)
        self.assertTrue(payload["prompt"].strip())

    def test_no_field_the_provider_rejects(self):
        for shot_id in ("S01", "S06"):
            with self.subTest(shot=shot_id):
                payload = payload_of(shot_id)
                for field in BANNED:
                    self.assertNotIn(field, payload, f"{field} 已被 agnes-video-2.5 拒绝")

    def test_face_shot_pins_the_portrait_as_first_frame(self):
        """露脸镜头靠 keyframe 模式把定妆照钉成真正的第一帧（跨镜同一张脸的一半靠它）。"""
        payload = payload_of("S06")
        self.assertEqual(payload["mode"], "keyframe")
        self.assertEqual(payload["first_frame"], SHOTS["S06"]["reference_image"])
        self.assertTrue(payload["first_frame"].startswith("https://"),
                        "Agnes 只在服务器侧取图，必须是公开 https 地址")

    def test_guardrails_moved_into_the_prompt(self):
        """negative_prompt 不再是独立字段：红线不出现在提示词里就等于没有了。"""
        prompt = payload_of("S01")["prompt"]
        for keyword in ("readable text", "corpse", "real person", "cartoon"):
            self.assertIn(keyword, prompt.lower())
        self.assertTrue(prompt.startswith(PROJECT["style_prefix"].strip()[:30]))


def load_render():
    """按文件路径加载本片的 render.py。

    不能 `import render`：仓库里多个项目都有 render.py / generate.py，测试跑起来
    sys.path 上先出现的是别的项目那份（实测会 import 到 production/dahlia/generate.py）。
    """
    spec = importlib.util.spec_from_file_location("hwaseong1986_render", PROJECT_DIR / "render.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["hwaseong1986_render"] = module
    sys.path.insert(0, str(PROJECT_DIR))
    spec.loader.exec_module(module)
    return module


class RenderGateAgreementTests(unittest.TestCase):
    def test_render_gate_accepts_what_generate_produces(self):
        """生成写进 results.json 的模型，必须过得了 render.py 的出片闸门。

        两边都从 model_policy 读；不一致的话素材全生成完了才发现整片被拒
        （旧代码写死 agnes-video-v2.0，报的还是看不懂的
        「Only the requested Agnes model is allowed」）。
        """
        render = load_render()
        self.assertEqual(render.ALLOWED_MODELS, model_policy.ALLOWED_MODELS)
        self.assertIn(payload_of("S01")["model"], render.ALLOWED_MODELS)
        self.assertIn(payload_of("S06")["model"], render.ALLOWED_MODELS)

    def test_free_plan_is_the_default(self):
        """用户定的方案：走免费档（主档要余额，两把 key 实测都是 ＄0.000000）。"""
        self.assertEqual(model_policy.MODEL, "agnes-video-2.5-flash")
        self.assertEqual(model_policy.SIZE_TIER, "720P")


class ValidationGateTests(unittest.TestCase):
    def test_validate_passes_on_the_real_plan(self):
        generate.validate(PROJECT)   # 不抛就是过

    def test_validate_rejects_a_banned_field(self):
        original = generate.full_payload

        def poisoned(project, shot):
            payload = original(project, shot)
            payload["width"] = 1920      # 就是这次踩的坑
            return payload

        generate.full_payload = poisoned
        try:
            with self.assertRaises(ValueError):
                generate.validate(PROJECT)
        finally:
            generate.full_payload = original

    def test_validate_rejects_seconds_outside_the_range(self):
        original = generate.full_payload

        def too_long(project, shot):
            return {**original(project, shot), "seconds": "30"}

        generate.full_payload = too_long
        try:
            with self.assertRaises(ValueError):
                generate.validate(PROJECT)
        finally:
            generate.full_payload = original


if __name__ == "__main__":
    unittest.main(verbosity=2)
