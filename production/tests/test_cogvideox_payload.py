"""锁住 CogVideoX-Flash 的请求形状与红线（离线，不发请求）。

2026-10-11 用户拍板 38 镜全走智谱免费档；这份测试守四件事：
payload 默认只有 model/prompt/quality 三个字段、模型名在出片闸门白名单里、
prompt 必须带上本片红线（PROMPT_GUARDRAILS，单一出处在 model_policy.py）、
定妆照探测（image_url）只在探测通过时进 payload 且哈希随之改变。
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


class RefImageProbeTests(unittest.TestCase):
    """定妆照探测：露脸镜头要钉住 cast/C1–C5.png（2026-10-11 用户要求露脸）。"""

    @classmethod
    def setUpClass(cls):
        cls.gen = load("hwaseong1986_generate_cogvideox_probe", HW / "generate_cogvideox.py")
        cls.project = json.loads((HW / "story.json").read_text(encoding="utf-8"))
        cls.ref_shot = next(s for s in cls.project["shots"] if s.get("reference_image"))
        cls.plain_shot = next(s for s in cls.project["shots"]
                              if not s.get("reference_image") and s.get("kind") != "graphic")

    def setUp(self):
        self.gen.REF_IMAGE_OK = None
        self.gen.PROBE_TASKS.clear()

    tearDown = setUp

    def test_unprobed_payload_stays_plain_even_for_reference_shots(self):
        body = self.gen.full_payload(self.project, self.ref_shot)
        self.assertEqual(sorted(body), ["model", "prompt", "quality"],
                         "没探测过就默认纯文生视频，不许偷偷带 image_url")

    def test_probe_success_pins_portrait_and_reuses_the_submission(self):
        class Videos:
            def generations(self, **payload):
                assert payload["image_url"] == self.outer.ref_shot["reference_image"]
                return {"id": "task-123"}

            def __init__(self, outer):
                self.outer = outer

        class Client:
            def __init__(self, outer):
                self.videos = Videos(outer)

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            record = self.gen.probe_ref_image(Client(self), self.project,
                                              record_path=pathlib.Path(tmp) / "probe.json")
        self.assertTrue(record["supported"])
        self.assertTrue(self.gen.REF_IMAGE_OK)
        self.assertEqual(self.gen.PROBE_TASKS[self.ref_shot["id"]], "task-123")
        body = self.gen.full_payload(self.project, self.ref_shot)
        self.assertEqual(body["image_url"], self.ref_shot["reference_image"])
        plain = self.gen.full_payload(self.project, self.plain_shot)
        self.assertEqual(sorted(plain), ["model", "prompt", "quality"],
                         "没有定妆照的镜头永远纯文生视频")

    def test_probe_refusal_falls_back_to_text_to_video(self):
        class Client:
            class videos:
                @staticmethod
                def generations(**payload):
                    raise RuntimeError("400 invalid parameter image_url")

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "probe.json"
            record = self.gen.probe_ref_image(Client(), self.project, record_path=path)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(record["supported"])
        self.assertFalse(self.gen.REF_IMAGE_OK)
        self.assertFalse(self.gen.PROBE_TASKS)
        self.assertIn("image_url", saved["error"])
        body = self.gen.full_payload(self.project, self.ref_shot)
        self.assertEqual(sorted(body), ["model", "prompt", "quality"])

    def test_ref_image_changes_request_hash_only_for_reference_shots(self):
        before_ref = self.gen.request_hash(self.project, self.ref_shot)
        before_plain = self.gen.request_hash(self.project, self.plain_shot)
        self.gen.REF_IMAGE_OK = True
        self.assertNotEqual(before_ref, self.gen.request_hash(self.project, self.ref_shot),
                            "带定妆照后哈希必须变，收据机制才会只重跑这几镜")
        self.assertEqual(before_plain, self.gen.request_hash(self.project, self.plain_shot),
                            "其余 33 镜哈希不变，收据直接复用")

    def test_transient_fail_recognizes_the_real_1234_network_error(self):
        # 2026-10-11 S06 真实 FAIL 载荷（gen-diag-cogvideox.log）：供应商让重试，
        # 引擎必须重投而不是整轮暴毙。
        real = ("{'code': '1234', 'message': '网络错误，错误id："
                "202610111232513d85762cfe62472d，请稍后重试'}")
        self.assertTrue(self.gen.transient_fail(real))
        self.assertFalse(self.gen.transient_fail('content policy violation'),
                         "内容违规这类非瞬时 FAIL 必须仍然致命，不能空转重投")


class MediaWindowTests(unittest.TestCase):
    """2026-10-11 教训：CogVideoX-Flash 实测出片 5.108 s，被 6 秒质检下限整轮误杀。

    字典就是当天 results.json 失败行里的真实探测值；I/O 打桩（本地无 ffmpeg），
    但质检窗口判断走的是 media.inspect_clip 的真实代码路径。
    """

    REAL_COGVIDEOX_INFO = {'duration': 5.108108, 'bytes': 1355051, 'width': 1792,
                           'height': 1024, 'fps': 37.0, 'video_codec': 'h264',
                           'frames': 189}

    @classmethod
    def setUpClass(cls):
        cls.media = load("hwaseong1986_media_window", HW / "media.py")

    def inspect_with(self, info):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            clip = tmp / "S99.mp4"
            clip.write_bytes(b"x")

            def fake_run(cmd, *args, **kwargs):
                if '-q:v' in [str(c) for c in cmd]:  # 接触表那一条：副作用产出文件
                    pathlib.Path(cmd[-1]).write_bytes(b"jpg")

            orig = (self.media.ensure_tools, self.media.probe, self.media.run)
            self.media.ensure_tools = lambda: None
            self.media.probe = lambda path: dict(info)
            self.media.run = fake_run
            try:
                return self.media.inspect_clip(clip, tmp / "qa", "S99")
            finally:
                (self.media.ensure_tools, self.media.probe, self.media.run) = orig

    def test_real_cogvideox_clip_passes_inspection(self):
        info = self.inspect_with(self.REAL_COGVIDEOX_INFO)
        self.assertTrue(info["decoded_ok"])
        self.assertEqual(info["duration"], 5.108108)

    def test_sub_four_second_clip_still_rejected(self):
        bad = dict(self.REAL_COGVIDEOX_INFO, duration=3.9)
        with self.assertRaises(RuntimeError):
            self.inspect_with(bad)


if __name__ == "__main__":
    unittest.main()
