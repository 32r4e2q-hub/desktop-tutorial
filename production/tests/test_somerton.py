import hashlib
import json
import unittest
from pathlib import Path

from production.somerton.generate import (
    agnes,
    FORBIDDEN_PAYLOAD_FIELDS,
    MODEL,
    SOURCE_SIZE,
    REQUEST_INTERVAL_SECONDS,
    full_payload,
    full_prompt,
    prepare_prompt_changes,
    request_hash,
    retry_create_until_accepted,
    retryable_create_error,
    validate,
)
from production.somerton.throttle import RequestGate

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

    def test_transient_create_errors_retry_forever_at_61_second_intervals(self):
        self.assertEqual(REQUEST_INTERVAL_SECONDS, 61)
        self.assertEqual(RequestGate().interval, 61.0)
        for message, marker in (
            ("HTTP 503: video queue is full", "video queue is full"),
            ("get_channel_failed: no available channel", "no available channel"),
            ("HTTP 502: bad gateway", "provider 5xx"),
            ("network error: connection reset", "network error"),
        ):
            with self.subTest(message=message):
                self.assertEqual(retryable_create_error(message), marker)
        self.assertIsNone(retryable_create_error("HTTP 400: invalid aspect_ratio"))
        self.assertIsNone(retryable_create_error("HTTP 403: insufficient user quota"))

    def test_create_loop_exceeds_old_limit_until_provider_accepts(self):
        class FakeGate:
            def __init__(self):
                self.cooldowns = []

            def defer(self, seconds):
                self.cooldowns.append(seconds)

        gate = FakeGate()
        attempts = 0
        retries = []

        def create():
            nonlocal attempts
            attempts += 1
            if attempts <= 27:
                raise agnes.Fatal(
                    "Could not create video task; last problem: HTTP 503: video queue is full"
                )
            return {"video_id": "accepted-after-28-attempts"}

        result = retry_create_until_accepted(
            create, gate, REQUEST_INTERVAL_SECONDS, lambda *details: retries.append(details)
        )
        self.assertEqual(result["video_id"], "accepted-after-28-attempts")
        self.assertEqual(attempts, 28)
        self.assertEqual(len(retries), 27)
        self.assertEqual(gate.cooldowns, [61] * 27)

    def test_create_loop_does_not_retry_invalid_request(self):
        class FakeGate:
            def __init__(self):
                self.cooldowns = []

            def defer(self, seconds):
                self.cooldowns.append(seconds)

        gate = FakeGate()
        attempts = 0

        def create():
            nonlocal attempts
            attempts += 1
            raise agnes.Fatal("HTTP 400: invalid aspect_ratio")

        with self.assertRaises(agnes.Fatal):
            retry_create_until_accepted(create, gate, REQUEST_INTERVAL_SECONDS, lambda *_: None)
        self.assertEqual(attempts, 1)
        self.assertEqual(gate.cooldowns, [])

    def test_create_loop_honors_longer_server_retry_after(self):
        class FakeGate:
            def __init__(self):
                self.cooldowns = []

            def defer(self, seconds):
                self.cooldowns.append(seconds)

        gate = FakeGate()
        attempts = 0

        def create():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise agnes.RateLimited("HTTP 429", retry_after=90)
            return {"video_id": "after-retry-after"}

        self.assertEqual(
            retry_create_until_accepted(create, gate, REQUEST_INTERVAL_SECONDS, lambda *_: None)["video_id"],
            "after-retry-after",
        )
        self.assertEqual(gate.cooldowns, [90])

    def test_create_loop_honors_retry_after_on_5xx(self):
        class FakeGate:
            def __init__(self):
                self.cooldowns = []

            def defer(self, seconds):
                self.cooldowns.append(seconds)

        gate = FakeGate()
        attempts = 0

        def create():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise agnes.Fatal(
                    "Could not create video task; last problem: HTTP 503: overloaded",
                    retry_after=120,
                )
            return {"video_id": "after-5xx-retry-after"}

        self.assertEqual(
            retry_create_until_accepted(create, gate, REQUEST_INTERVAL_SECONDS, lambda *_: None)["video_id"],
            "after-5xx-retry-after",
        )
        self.assertEqual(gate.cooldowns, [120])

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

    def test_high_risk_props_have_explicit_strict_no_text_prompts(self):
        rows = {shot["id"]: shot for shot in self.story["shots"]}
        high_risk = {"S04", "S06", "S07", "S10", "S12", "S15", "S17", "S18", "S19", "S21", "S26", "S27"}
        markers = ("no text", "text-free", "no letters", "no lettering", "no writing", "no symbols", "no marks")
        for sid in high_risk:
            with self.subTest(shot=sid):
                prompt = rows[sid]["prompt"].lower()
                self.assertTrue(any(marker in prompt for marker in markers), prompt)

    def test_changed_prompt_rows_are_checkpointed_before_workers_start(self):
        shots = {shot["id"]: shot for shot in self.story["shots"]}
        old_s07 = {"id": "S07", "request_hash": "old-prompt", "status": "completed",
                   "reused_existing_asset": True, "video_url": "old-url"}
        matching_s08 = {"id": "S08", "request_hash": request_hash(self.story, shots["S08"]),
                        "status": "completed", "reused_existing_asset": True}
        results = {"shots": {"S07": old_s07.copy(), "S08": matching_s08.copy()}}

        changed = prepare_prompt_changes(self.story, results, [shots["S07"], shots["S08"]])

        self.assertEqual(changed, ["S07"])
        self.assertEqual(results["previous_results"]["S07"], [old_s07])
        self.assertEqual(results["shots"]["S07"]["request_hash"], request_hash(self.story, shots["S07"]))
        self.assertEqual(results["shots"]["S07"]["status"], "retrying_create")
        self.assertFalse(results["shots"]["S07"]["reused_existing_asset"])
        self.assertEqual(results["shots"]["S08"], matching_s08)

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
