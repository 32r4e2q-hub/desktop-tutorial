"""锁住 CogVideoX-Flash 的请求形状与红线（离线，不发请求）。

2026-10-11 用户拍板 38 镜全走智谱免费档；这份测试守三件事：
payload 只有 model/prompt/quality 三个字段、模型名在出片闸门白名单里、
prompt 必须带上本片红线（PROMPT_GUARDRAILS，单一出处在 generate.py）。
"""
import importlib.util
import json
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
HW = HERE.parent / "hwaseong1986"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CogVideoXPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gen = load("hwaseong1986_generate_cogvideox", HW / "generate_cogvideox.py")
        cls.policy = load("hwaseong1986_model_policy", HW / "model_policy.py")
        cls.project = json.loads((HW / "story.json").read_text(encoding="utf-8"))
        cls.shot = next(s for s in cls.project["shots"] if s["id"] == "S01")

    def test_payload_is_the_stable_three_field_shape(self):
        body = self.gen.full_payload(self.project, self.shot)
        self.assertEqual(sorted(body), ["model", "prompt", "quality"])
        self.assertEqual(body["quality"], "speed")

    def test_model_is_on_the_render_gate_whitelist(self):
        self.assertEqual(self.gen.MODEL, "cogvideox-flash")
        self.assertIn(self.gen.MODEL, self.policy.ALLOWED_MODELS,
                      "智谱模型必须进 model_policy 白名单，否则 render 闸门拒出片")

    def test_prompt_carries_the_red_lines(self):
        body = self.gen.full_payload(self.project, self.shot)
        self.assertIn("readable text", body["prompt"],
                      "红线（画面不得出现可读文字等）必须随 prompt 下发")
        self.assertIn(self.shot["prompt"][:80], body["prompt"])
        self.assertLessEqual(len(body["prompt"]), 2600)

    def test_request_hash_is_reproducible(self):
        self.assertEqual(self.gen.request_hash(self.project, self.shot),
                         self.gen.request_hash(self.project, self.shot))

    def test_validate_accepts_the_real_story(self):
        self.gen.validate(self.project)  # 45 = 38 动态 + 7 信息卡


if __name__ == "__main__":
    unittest.main()
