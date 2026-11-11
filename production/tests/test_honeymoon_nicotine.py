"""Offline validation for the reviewed reference package and reference-mode video payloads."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "production" / "honeymoon_nicotine"
sys.path.insert(0, str(HERE))
# Other production projects also import a top-level module named ``generate``.
# Load this project by file path to avoid whichever test happened to import first.
spec = importlib.util.spec_from_file_location("honeymoon_nicotine_generate", HERE / "generate.py")
assert spec is not None and spec.loader is not None
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class HoneymoonReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = json.loads((HERE / "story.json").read_text(encoding="utf-8"))

    def test_all_31_reviewed_images_are_present_and_pinned(self):
        approvals = json.loads((HERE / "reference" / "approvals.json").read_text(encoding="utf-8"))
        self.assertEqual(len(approvals["assets"]), 31)
        revision = (HERE / "reference" / "revision.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(revision, self.project["reference_revision"])
        for row in approvals["assets"].values():
            path = HERE / row["file"]
            self.assertEqual(row["status"], "approved")
            self.assertTrue(path.is_file())
            self.assertEqual(generator.digest(path), row["sha256"])

    def test_every_clip_uses_one_to_five_immutable_reference_urls(self):
        for shot in self.project["shots"]:
            with self.subTest(shot=shot["id"]):
                payload = generator.full_payload(self.project, shot)
                self.assertEqual(payload["mode"], "reference")
                self.assertIn("images", payload)
                self.assertGreaterEqual(len(payload["images"]), 1)
                self.assertLessEqual(len(payload["images"]), 5)
                self.assertTrue(all(url.startswith("https://raw.githubusercontent.com/") for url in payload["images"]))
                self.assertTrue(all(self.project["reference_revision"] in url for url in payload["images"]))

    def test_character_and_scene_anchors_are_attached(self):
        by_id = {shot["id"]: shot for shot in self.project["shots"]}
        # S21 is the densest reference shot: two characters, room, policy and diary.
        payload = generator.full_payload(self.project, by_id["S21"])
        self.assertEqual(len(payload["images"]), 5)
        names = [url.rsplit("/", 1)[-1] for url in payload["images"]]
        self.assertEqual(names, ["C01_A.png", "C05_POLICE.png", "S12_INTERROGATION.png",
                                "P02_POLICY_RED_CIRCLE.png", "P04_DIARY.png"])

    def test_status_only_check_persists_get_results_without_creating_tasks(self):
        with tempfile.TemporaryDirectory() as temporary:
            results_path = Path(temporary) / "results.json"
            results_path.write_text(json.dumps({"shots": {
                "S01": {"video_id": "task-existing", "task_id": "task-existing", "status": "queued"},
            }}), encoding="utf-8")
            original_results = generator.RESULTS
            generator.RESULTS = results_path
            try:
                with (
                    patch.dict(os.environ, {"AGNES_API_KEY": "test-key"}),
                    patch.object(generator.agnes, "http_json", return_value=(
                        200, {"status": "processing", "progress": 25}, "")) as request,
                ):
                    self.assertEqual(generator.check_outstanding_tasks(publish=False), 2)
                request.assert_called_once()
                self.assertEqual(request.call_args.args[0], "GET")
                saved = json.loads(results_path.read_text(encoding="utf-8"))
                report = saved["task_status_check"]
                self.assertEqual(report["create_requests"], 0)
                self.assertEqual(report["unresolved"], ["S01"])
                self.assertEqual(report["shots"]["S01"]["state"], "processing")
            finally:
                generator.RESULTS = original_results

    def test_retrieve_completed_downloads_only_existing_task_and_never_creates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            here = root / "production" / "honeymoon_nicotine"
            here.mkdir(parents=True)
            results_path = here / "results.json"
            results_path.write_text(json.dumps({"shots": {
                "S01": {"video_id": "task-existing", "task_id": "task-existing", "status": "queued"},
            }}), encoding="utf-8")
            original_root, original_here, original_results = generator.ROOT, generator.HERE, generator.RESULTS

            def fake_download(url, dest, retries, retry_delay):
                self.assertEqual(url, "https://video.example/S01.mp4")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b"video-bytes" * 200)
                return dest.stat().st_size

            try:
                generator.ROOT, generator.HERE, generator.RESULTS = root, here, results_path
                with (
                    patch.dict(os.environ, {"AGNES_API_KEY": "test-key"}),
                    patch.object(generator.agnes, "http_json", return_value=(200, {
                        "status": "completed", "progress": 100,
                        "video_url": "https://video.example/S01.mp4",
                    }, "")) as request,
                    patch.object(generator.agnes, "download", side_effect=fake_download),
                    patch.object(generator, "create_contact_sheet", return_value={
                        "decoded_ok": True, "visual_review": "pending",
                    }),
                ):
                    self.assertEqual(generator.retrieve_completed_tasks(publish=False), 0)
                request.assert_called_once()
                self.assertEqual(request.call_args.args[0], "GET")
                saved = json.loads(results_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["task_retrieval"]["create_requests"], 0)
                self.assertEqual(saved["task_retrieval"]["downloaded"], ["S01"])
                self.assertEqual(saved["shots"]["S01"]["status"], "completed")
                self.assertTrue((root / "work/honeymoon_nicotine/sources/S01.mp4").is_file())
            finally:
                generator.ROOT, generator.HERE, generator.RESULTS = original_root, original_here, original_results

    def test_plan_validates_offline_without_agnes_requests(self):
        generator.validate(self.project, require_audio=False)
        self.assertEqual(len(self.project["shots"]), 30)
        self.assertEqual(sum(shot["duration"] for shot in self.project["shots"]), 180)


if __name__ == "__main__":
    unittest.main()
