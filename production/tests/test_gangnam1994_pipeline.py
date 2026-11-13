from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
EP14 = ROOT / "production" / "gangnam1994"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestGangnam1994Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(EP14) not in sys.path:
            sys.path.insert(0, str(EP14))
        if str(ROOT / "production") not in sys.path:
            sys.path.insert(0, str(ROOT / "production"))
        cls.gen = load_module("gangnam1994_generate", EP14 / "generate.py")
        cls.story = json.loads((EP14 / "story.json").read_text(encoding="utf-8"))

    def test_thirty_shots_exact_180_seconds_and_rate_gate(self):
        self.assertEqual(self.gen.MODEL, "agnes-video-2.5-flash")
        self.assertEqual(self.gen.SOURCE_SIZE, "720P")
        self.assertGreaterEqual(self.gen.REQUEST_INTERVAL_SECONDS, 12.0)
        self.gen.validate(self.story, require_audio=False)
        self.assertEqual(len(self.story["shots"]), 30)
        self.assertEqual(sum(s["duration"] for s in self.story["shots"]), 180)

    def test_all_thirty_one_references_approved_and_pinned(self):
        approvals = json.loads((EP14 / "reference" / "approvals.json").read_text(encoding="utf-8"))
        assets = approvals.get("assets", {})
        self.assertEqual(len(assets), 31)
        rev = (EP14 / "reference" / "revision.txt").read_text(encoding="utf-8").strip()
        self.assertEqual(len(rev), 40)
        used = set()
        for shot in self.story["shots"]:
            payload = self.gen.full_payload(self.story, shot)
            self.assertEqual(set(payload.keys()), self.gen.ALLOWED_PAYLOAD_FIELDS)
            self.assertEqual(payload["mode"], "reference")
            self.assertTrue(1 <= len(payload["images"]) <= 5)
            for url in payload["images"]:
                self.assertIn(f"/{rev}/production/gangnam1994/reference/", url)
            used.update(self.gen.reference_asset_ids(shot))
        self.assertEqual(len(used), 31)

    def test_nine_retention_hooks_and_clean_s30_prompt(self):
        hooks = self.story["presentation"]["retention_hooks"]
        self.assertEqual(len(hooks), 9)
        self.assertEqual([h["id"] for h in hooks], [f"H{i}" for i in range(1, 10)])
        s30 = self.story["shots"][-1]
        self.assertEqual(s30["id"], "S30")
        self.assertIn("绝对没有任何文字", s30["purpose"])


if __name__ == "__main__":
    unittest.main()
