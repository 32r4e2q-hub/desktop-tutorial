import hashlib
import json
import unittest
from pathlib import Path

from production.somerton.generate import (
    FORBIDDEN_PAYLOAD_FIELDS,
    MODEL,
    SOURCE_SIZE,
    capacity_failure_policy,
    full_payload,
    full_prompt,
    validate,
)

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "somerton"


class SomertonPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))

    def test_complete_fixed_180_second_agnes_plan(self):
        validate(self.story)
        self.assertEqual(len(self.story["shots"]), 29)
        self.assertEqual(sum(s["duration"] for s in self.story["shots"]), 180)
        self.assertEqual((self.story["width"], self.story["height"], self.story["fps"]), (1920, 1080, 30))
        self.assertTrue(all(s["kind"] == "agnes" for s in self.story["shots"]))
        self.assertTrue(all(4 <= s["duration"] <= 9 for s in self.story["shots"]))

    def test_25_flash_payload_uses_only_the_supported_720p_schema(self):
        expected_fields = {"model", "prompt", "seconds", "size", "aspect_ratio", "mode", "n", "seed"}
        self.assertEqual(self.story["model"], MODEL)
        self.assertEqual(self.story["source_size"], SOURCE_SIZE)
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                payload = full_payload(self.story, shot)
                self.assertEqual(set(payload), expected_fields)
                self.assertEqual(payload["model"], "agnes-video-2.5-flash")
                self.assertEqual(payload["seconds"], str(shot["duration"]))
                self.assertEqual(payload["size"], "720P")
                self.assertEqual(payload["aspect_ratio"], "16:9")
                self.assertEqual(payload["mode"], "text")
                self.assertEqual(payload["n"], 1)
                self.assertFalse(FORBIDDEN_PAYLOAD_FIELDS.intersection(payload))

    def test_provider_capacity_errors_get_bounded_shared_backoff(self):
        self.assertEqual(
            capacity_failure_policy("HTTP 500: video queue is full"),
            ("video queue is full", 90, 24),
        )
        self.assertEqual(
            capacity_failure_policy("get_channel_failed: no available channel"),
            ("no available channel", 300, 3),
        )
        self.assertEqual(capacity_failure_policy("HTTP 502: bad gateway"), ("provider 5xx", 120, 3))
        self.assertIsNone(capacity_failure_policy("HTTP 400: invalid aspect_ratio"))

    def test_every_prompt_gets_style_characters_and_negative(self):
        for shot in self.story["shots"]:
            with self.subTest(shot=shot["id"]):
                prompt = full_prompt(self.story, shot)
                self.assertTrue(prompt.startswith("【STYLE】"))
                self.assertTrue(prompt.endswith(self.story["negative_prompt"]))
                for role in shot["characters"]:
                    character = self.story["characters"][role]
                    normalized = character.strip()
                    self.assertIn(normalized, prompt)
                    self.assertLess(prompt.index(normalized), prompt.index(shot["prompt"]))
                self.assertIn(shot["prompt"], prompt)

    def test_audio_manifest_is_exact_and_hashed(self):
        manifest = json.loads((PROJECT / "audio" / "manifest.json").read_text(encoding="utf-8"))
        records = {row["id"]: row for row in manifest["clips"]}
        self.assertEqual(len(records), 9)
        for chapter in self.story["chapters"]:
            row = records[chapter["id"]]
            audio = PROJECT / "audio" / row["file"]
            self.assertEqual(row["text"], chapter["text"])
            self.assertEqual(row["sha256"], hashlib.sha256(audio.read_bytes()).hexdigest())
            self.assertEqual(row["voice_id"], "voice-00")

    def test_reference_images_and_post_overlays_are_defined(self):
        for reference in self.story["reference_images"]:
            self.assertTrue((PROJECT / reference["file"]).is_file())
        presentation = self.story["presentation"]
        self.assertEqual(presentation["end_title"], "塔玛姆·舒德")
        self.assertEqual(presentation["cover"]["text"], "他是谁?")
        self.assertIn("Tamam Shud", self.story["shots"][13]["prompt"])
        self.assertEqual(presentation["voice_pauses"]["N03"]["seconds"], 0.5)
        self.assertEqual(presentation["voice_pauses"]["N09"]["seconds"], 0.5)


if __name__ == "__main__":
    unittest.main()
