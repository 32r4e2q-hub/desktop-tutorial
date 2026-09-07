"""Offline tests for production/multi_video.py (no network)."""
import json, os, sys, types
from pathlib import Path
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import multi_video as mv  # noqa: E402
import agnes_video as agnes  # noqa: E402


class PayloadTests(unittest.TestCase):
    def test_pixazo_payload_vertical_free_limits(self):
        path, p = mv.pixazo_payload({"prompt": "x", "seconds": 8, "aspect": "9:16", "negative_prompt": "bad", "seed": 5})
        self.assertEqual(path, mv.PIXAZO_T2V)
        self.assertEqual((p["width"], p["height"]), (576, 1024))
        self.assertEqual(p["num_frames"], 121)                      # capped for the free endpoint
        self.assertEqual((p["num_frames"] - 1) % 8, 0)
        self.assertLessEqual(p["width"] * p["height"] * p["num_frames"], 100_000_000)
        self.assertEqual(p["negative"], "bad")                     # free endpoint wants `negative`
        self.assertNotIn("negative_prompt", p)
        self.assertEqual(p["seed"], 5)

    def test_pixazo_image_to_video(self):
        path, p = mv.pixazo_payload({"prompt": "x", "images": ["https://a/b.png"]})
        self.assertEqual(path, mv.PIXAZO_I2V)
        self.assertEqual(p["image_url"], "https://a/b.png")

    def test_pixazo_find_url_shapes(self):
        self.assertEqual(mv.pixazo_find_url({"output": {"media_url": ["https://x/o.mp4"]}}), "https://x/o.mp4")
        self.assertEqual(mv.pixazo_find_url({"output": {"video": {"url": "https://x/v.mp4"}}}), "https://x/v.mp4")
        self.assertIsNone(mv.pixazo_find_url({"status": "PROCESSING"}))

    def test_shot_list_prefix_and_negative(self):
        doc = {"style_prefix": "STYLE, ", "negative": "NEG", "defaults": {"seconds": 7, "aspect": "9:16"},
               "shots": [{"id": "S01", "prompt": "a"}, {"prompt": "b", "negative_prompt": "own", "no_prefix": True}]}
        tmp = Path(os.environ.get("TMPDIR", "/tmp")) / "shots_test.json"
        tmp.write_text(json.dumps(doc), encoding="utf-8")
        shots = mv.load_shots(tmp)
        self.assertEqual(shots[0]["prompt"], "STYLE, a")
        self.assertEqual(shots[0]["negative_prompt"], "NEG")
        self.assertEqual(shots[1]["id"], "S02")
        self.assertEqual(shots[1]["prompt"], "b")
        self.assertEqual(shots[1]["negative_prompt"], "own")
        self.assertEqual(shots[1]["seconds"], 7)

    def test_agnes_namespace_builds(self):
        shot = {"prompt": "p", "seconds": 8, "aspect": "9:16", "resolution": "720p"}
        with mock.patch.object(mv.agnes, "create_task", side_effect=agnes.Fatal("boom")):
            with self.assertRaises(mv.ProviderError):
                mv.agnes_generate(shot, Path("/tmp/never.mp4"), "k", 1, 1)


class FallbackTests(unittest.TestCase):
    def test_second_provider_used_and_becomes_sticky(self):
        calls = []
        def bad(shot, dest, key, poll, timeout):
            calls.append("bad"); raise mv.ProviderError("nope")
        def good(shot, dest, key, poll, timeout):
            calls.append("good"); return {"provider": "good", "size_bytes": 5}
        providers = [("bad", "K1", bad), ("good", "K2", good)]
        with mock.patch.dict(os.environ, {"K1": "a", "K2": "b"}):
            r = mv.generate_shot({"id": "S1", "prompt": "x"}, Path("/tmp/x.mp4"), providers, 1, 1)
            self.assertEqual(r["provider"], "good")
            self.assertEqual(r["errors_before_success"], ["bad: nope"])
            self.assertEqual(providers[0][0], "good")               # sticky reorder
            mv.generate_shot({"id": "S2", "prompt": "x"}, Path("/tmp/x.mp4"), providers, 1, 1)
        self.assertEqual(calls, ["bad", "good", "good"])

    def test_all_fail(self):
        def bad(shot, dest, key, poll, timeout):
            raise mv.ProviderError("nope")
        with mock.patch.dict(os.environ, {"K1": "a"}):
            with self.assertRaises(mv.ProviderError):
                mv.generate_shot({"id": "S1", "prompt": "x"}, Path("/tmp/x.mp4"), [("bad", "K1", bad)], 1, 1)


class PixazoFlowTests(unittest.TestCase):
    def test_create_poll_download(self):
        responses = iter([
            (202, {"request_id": "ltx-video_1", "status": "QUEUED", "polling_url": "https://gateway.pixazo.ai/v2/requests/status/ltx-video_1"}, ""),
            (200, {"status": "PROCESSING"}, ""),
            (200, {"status": "COMPLETED", "model_id": "ltx-video", "output": {"media_url": ["https://cdn/o.mp4"]}}, ""),
        ])
        seen = []
        def fake_http(method, url, key, payload=None, timeout=60):
            seen.append((method, url)); return next(responses)
        with mock.patch.object(mv, "pixazo_http", fake_http), \
             mock.patch.object(mv.agnes, "download", return_value=4096) as dl, \
             mock.patch.object(mv.time, "sleep"):
            r = mv.pixazo_generate({"id": "S1", "prompt": "p", "seconds": 5, "aspect": "9:16"}, Path("/tmp/o.mp4"), "key", 0, 60)
        self.assertEqual(r["provider"], "pixazo")
        self.assertEqual(r["video_url"], "https://cdn/o.mp4")
        self.assertEqual(seen[0], ("POST", mv.PIXAZO_T2V))
        self.assertEqual(seen[1][1], "https://gateway.pixazo.ai/v2/requests/status/ltx-video_1")
        dl.assert_called_once()

    def test_quota_exhausted_is_provider_error(self):
        with mock.patch.object(mv, "pixazo_http", return_value=(402, {"error": "Insufficient Balance"}, "")):
            with self.assertRaises(mv.ProviderError) as cm:
                mv.pixazo_generate({"id": "S1", "prompt": "p"}, Path("/tmp/o.mp4"), "key", 0, 60)
        self.assertIn("quota", str(cm.exception))

    def test_failed_status(self):
        responses = iter([(202, {"request_id": "r1", "status": "QUEUED"}, ""),
                          (200, {"status": "FAILED", "error": "nsfw"}, "")])
        with mock.patch.object(mv, "pixazo_http", lambda *a, **k: next(responses)), mock.patch.object(mv.time, "sleep"):
            with self.assertRaises(mv.ProviderError) as cm:
                mv.pixazo_generate({"id": "S1", "prompt": "p"}, Path("/tmp/o.mp4"), "key", 0, 60)
        self.assertIn("nsfw", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
