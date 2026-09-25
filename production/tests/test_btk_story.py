from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "btk"
sys.path.insert(0, str(PROJECT))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_btk_content_source_and_narration_receipts_are_consistent():
    content = load_module("btk_story_test", PROJECT / "build_story.py")
    story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
    manifest = json.loads((PROJECT / "audio" / "manifest.json").read_text(encoding="utf-8"))
    assert len(content.CHAPTERS) == len(story["chapters"]) == len(manifest["clips"]) == 6
    for (chapter_id, _title, text), chapter, clip in zip(content.CHAPTERS, story["chapters"], manifest["clips"]):
        assert chapter_id == chapter["id"] == clip["id"]
        assert text == chapter["text"] == clip["text"]
        audio = PROJECT / "audio" / clip["file"]
        assert audio.is_file() and clip["sha256"]
        assert hashlib.sha256(audio.read_bytes()).hexdigest() == clip["sha256"]


def test_btk_plan_is_unique_animated_and_fact_checked():
    story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
    shots = story["shots"]
    assert len(shots) == 45
    assert sum(shot["kind"] == "agnes" for shot in shots) == 38
    assert sum(shot["kind"] == "graphic" for shot in shots) == 7
    assert len({shot["id"] for shot in shots}) == 45
    assert all("hold the final composition" in shot["prompt"].lower() for shot in shots if shot["kind"] == "agnes")
    assert {shot["id"] for shot in shots if shot["kind"] == "graphic"} == set(story["presentation"]["cards"])
    for source in story["sources"]:
        assert source["url"].startswith("https://") and source["usage"]
    text = "".join(chapter["text"] for chapter in story["chapters"])
    stripped = re.sub(r"[，。！？；：、—]", "", text)
    assert 700 <= len(stripped) <= 800
    assert "九天后的手铐" in text
    assert "完美匹配" in text  # explicitly negated in the script to avoid overstating familial DNA
    assert "老死狱中" not in text
    assert "二十多天后的手铐" not in text


def test_btk_cuts_use_every_shot_once_and_match_story_chapters():
    render = load_module("btk_render_test", PROJECT / "render.py")

    story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
    all_cuts = [(chapter, sid) for chapter, entries in render.CUTS.items() for _, sid, _ in entries]
    assert len(all_cuts) == len({sid for _, sid in all_cuts}) == 45
    assert {sid for _, sid in all_cuts} == {shot["id"] for shot in story["shots"]}
    assert set(render.CUTS) == {chapter["id"] for chapter in story["chapters"]}
    sys.modules["render"] = render
    table = load_module("btk_script_table_test", PROJECT / "script_table.py")
    rows, _tempo = table.segments()
    for chapter in story["chapters"]:
        spoken = "".join(row["text"] for row in rows if row["chapter"] == chapter["id"] and row["id"] != "END")
        assert spoken == chapter["text"]


def test_clause_alignment_falls_back_when_tts_has_too_few_pauses():
    clause_times = load_module("btk_clause_times_test", PROJECT / "clause_times.py")
    rate = clause_times.RATE
    # Continuous, non-silent signal has no qualifying punctuation pauses.
    x = np.full(rate * 4, 0.04, dtype=np.float32)
    duration, clauses = clause_times.align("第一句。第二句。第三句。", x)
    assert duration == 4.0
    assert len(clauses) == 3
    assert [row["text"] for row in clauses] == ["第一句", "第二句", "第三句"]
    assert clauses[0]["start"] < clauses[0]["end"] <= clauses[1]["start"] < clauses[1]["end"]
    assert clauses[-1]["end"] == 4.0
