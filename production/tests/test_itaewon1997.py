import hashlib, json, subprocess, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "itaewon1997"
sys.path.insert(0, str(ROOT / "production"))
sys.path.insert(0, str(PROJECT))
import importlib.util  # noqa: E402


def _load(name, filename):
    # 其他项目也有 generate_clips/render/throttle，同名模块会在同一个 pytest 进程里串台，所以用唯一名字加载。
    spec = importlib.util.spec_from_file_location(name, PROJECT / filename)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


from itaewon_throttle import BudgetExhausted, RequestGate  # noqa: E402
generate_clips = _load("itaewon_generate_clips", "generate_clips.py")

SLOTS = [5,5,7,7,6,5,7,7,6,5,7,7,6,5,6,6,6,5,6,6,5,5,7,7,6,6,6,6,6,6]


class ItaewonPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, str(PROJECT / "build_story.py")], check=True, capture_output=True, text=True)
        cls.data = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))

    def test_30_shots_exact_180_seconds_script_slots(self):
        self.assertTrue(generate_clips.validate(self.data))
        self.assertEqual([s["duration"] for s in self.data["shots"]], SLOTS)
        self.assertEqual(sum(SLOTS), 180)
        self.assertTrue(all(s["kind"] == "agnes" for s in self.data["shots"]))
        self.assertTrue(all("真实连续运动" in s["prompt"] for s in self.data["shots"]))

    def test_style_first_anchors_negative_last_and_safety(self):
        for s in self.data["shots"]:
            self.assertTrue(s["prompt"].startswith("【STYLE】"))
            self.assertTrue(s["prompt"].endswith(self.data["negative"]))
            self.assertIn("【参考图说明】", s["prompt"])
            for r in s["character_anchors"]:
                self.assertIn(f"【{r}锚点】", s["prompt"])
            for kw in s["highlight_keywords"]:
                self.assertIn(kw, s["subtitle"])
        # 镜头 11–14：只有背影/剪影，不暗示哪个为真
        for sid in ("S11", "S12"):
            p = next(s for s in self.data["shots"] if s["id"] == sid)["prompt"]
            self.assertIn("不出现任何行凶动作", p)

    def test_payload_schema_reference_mode(self):
        allowed = {"model","prompt","seconds","size","aspect_ratio","mode","n","seed","images"}
        rev = "a" * 40
        for s in self.data["shots"]:
            p = generate_clips.payload(s, rev)
            self.assertEqual(set(p), allowed)
            self.assertEqual(p["model"], "agnes-video-2.5-flash")
            self.assertEqual(p["mode"], "reference")
            self.assertEqual(p["seconds"], str(s["duration"]))
            self.assertTrue(1 <= len(p["images"]) <= 5)
            self.assertTrue(all(rev in u and u.endswith(f"/{rid}.png") for u, rid in zip(p["images"], s["reference_images"])))

    def test_visual_motif_p01_in_script_order(self):
        by = {s["id"]: s for s in self.data["shots"]}
        for sid in ("S02", "S05", "S14", "S30"):
            self.assertIn("P01", by[sid]["reference_images"])

    def test_references_ledger_and_revision(self):
        status = self.data["reference_status"]
        self.assertEqual(len(status["approved_generated"]), 29)
        rev = generate_clips.revision()
        self.assertRegex(rev, r"^[0-9a-f]{40}$")
        generate_clips.validate_bundle(self.data, rev)

    def test_narration_manifest_matches(self):
        mp = PROJECT / "audio" / "manifest.json"
        if not mp.exists():
            self.skipTest("narration not yet generated")
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        shots = {s["id"]: s for s in self.data["shots"]}
        for row in manifest["clips"]:
            path = PROJECT / row["file"]
            self.assertEqual(row["text"], shots[row["id"]]["narration"])
            self.assertEqual(row["tts_text"], shots[row["id"]]["tts_text"])
            self.assertEqual(row["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_gate(self):
        clock = [0.0]
        g = RequestGate(12.0, allow_fast_plan=True, clock=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
        g.acquire_creation(100); t1 = clock[0]; g.acquire_creation(100)
        self.assertGreaterEqual(clock[0] - t1, 12.0)
        with self.assertRaises(BudgetExhausted):
            g.acquire_creation(clock[0] + 1)

    def test_render_filters_and_ass(self):
        render = _load("itaewon_render", "render.py")
        for s in self.data["shots"]:
            f = render.segment_filter(s)
            self.assertIn(f"trim=duration={s['duration']}", f)
        self.assertIn("fade=t=out", render.segment_filter(next(s for s in self.data["shots"] if s["id"] == "S30")))
        self.assertEqual(render.highlight("a九刀b", ["九刀"]), "a{\\c&H003CC9FF\\fs60\\b1}九刀{\\r}b")

    def test_render_audio_synthesis(self):
        import tempfile, wave
        render = _load("itaewon_render", "render.py")
        with tempfile.TemporaryDirectory() as d:
            for name, fn in (("a.wav", lambda p: render.make_score(p)), ("b.wav", lambda p: render.make_sfx(p, self.data))):
                p = Path(d) / name; fn(p)
                with wave.open(str(p)) as w:
                    self.assertEqual(w.getnframes(), 48000 * 180)


if __name__ == "__main__":
    unittest.main()
