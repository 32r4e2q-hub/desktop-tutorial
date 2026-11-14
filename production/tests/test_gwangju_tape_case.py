import json
import re
import struct
import sys
import wave
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = ROOT / "production" / "gwangju_tape_case"
sys.path.insert(0, str(PROJECT_DIR))


def load_project_module(name: str):
    """Avoid collisions with same-named modules from other production projects."""
    module_name = f"gwangju_tape_case_{name}"
    spec = spec_from_file_location(module_name, PROJECT_DIR / f"{name}.py")
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


build_sfx = load_project_module("build_sfx")
project_render = load_project_module("render")
project_generate = load_project_module("generate")
full_prompt = project_generate.full_prompt
write_ass = project_render.write_ass
write_cover_ass = project_render.write_cover_ass


@pytest.fixture(scope="module")
def story():
    return json.loads((PROJECT_DIR / "story.json").read_text(encoding="utf-8"))


def test_exact_30_shots_180_seconds_and_six_second_average(story):
    shots = story["shots"]
    assert len(shots) == 30
    cursor = 0
    for shot in shots:
        assert shot["start"] == cursor
        assert 5 <= shot["duration"] <= 7
        assert shot["seconds"] == shot["duration"]
        assert shot["aspect"] == "16:9"
        cursor += shot["duration"]
    assert cursor == 180
    assert cursor / len(shots) <= 6


def test_every_character_role_has_an_exact_anchor(story):
    assert set(story["characters"]) == {
        "SANA", "MOTHER", "MOTHER_OLD", "FATHER", "DETECTIVE",
        "EX", "FAMILIAR", "EXPERT", "TEAM_2024", "SHADOW",
    }
    for shot in story["shots"]:
        for role in shot["characters"]:
            assert story["characters"][role].startswith("【C")
            assert story["characters"][role] in story["characters"].values()


def test_hooks_and_explainers_are_complete_and_safely_timed(story):
    hooks = story["presentation"]["hooks"]
    hook_ids = {hook["id"] for hook in hooks}
    assert {f"H{i}" for i in range(1, 10)} <= hook_ids
    assert "CTA" in hook_ids
    for hook in hooks:
        assert hook["end"] - hook["start"] == pytest.approx(2.0)
    explainers = story["presentation"]["explainers"]
    assert len(explainers) == 9
    for hook in hooks:
        if hook["id"] == "CTA":
            continue
        next_exp = min(explainers, key=lambda item: abs(item["start"] - hook["end"]))
        assert next_exp["start"] >= hook["end"]


def test_final_picture_repairs_are_narrow_and_frame_locked():
    assert project_render.FLASH_REPAIR_FRAME == 464
    assert project_render.HOLD_REPAIR_FRAMES == (2533, 3450)
    assert project_render.DARK_REPAIR_START == pytest.approx(159.25)
    assert project_render.DARK_REPAIR_END == pytest.approx(160.0417)
    assert project_render.DARK_REPAIR_GAMMA == pytest.approx(1.5)


def test_visual_retake_safeguards_and_legal_qualifier(story):
    shots = {shot["id"]: shot for shot in story["shots"]}
    s04 = shots["S04"]["purpose"]
    assert "绝无其他人" in s04
    assert "不出现年轻女性" in s04
    assert "餐桌椅始终空无一人" in s04

    s08 = shots["S08"]["purpose"]
    assert "刀具" in s08 and "绝不出现" in s08
    assert "血迹" in s08 and "不展示地面" in s08
    assert "水果" not in s08

    s22 = shots["S22"]
    assert s22["characters"] == []
    assert "全程无人、无手" in s22["purpose"]
    assert "平铺在桌面上" in s22["purpose"]
    assert "胶带缠绕或束缚人体" in s22["purpose"]

    s26 = shots["S26"]["purpose"]
    assert "绝不出现纸张" in s26
    assert "绝不出现" in s26 and "任何文字、字母、数字" in s26
    assert "法槌" in shots["S26"]["sound_design"]
    assert build_sfx.CUES["S26"][1][0][0] == "gavel"
    assert "排除从犯" in next(
        cue["text"] for cue in story["presentation"]["explainers"] if cue["start"] == 162.1
    )


def test_reference_ids_and_sfx_cover_all_thirty_shots(story):
    expected = set(story["reference_designs"]["characters"] +
                   story["reference_designs"]["scenes"] + story["reference_designs"]["props"])
    role_to_asset = {
        "SANA": "C01", "MOTHER": "C02", "MOTHER_OLD": "C02B", "FATHER": "C03",
        "DETECTIVE": "C04", "EX": "C05", "FAMILIAR": "C06", "EXPERT": "C07",
        "TEAM_2024": "C08", "SHADOW": "C09",
    }
    for shot in story["shots"]:
        refs = [role_to_asset[role] for role in shot["characters"]]
        refs.extend(part.strip() for part in shot["reference_ids"].split("+") if part.strip())
        assert refs
        assert set(refs) <= expected
        assert len(set(refs)) <= 5
    assert set(build_sfx.CUES) == {shot["id"] for shot in story["shots"]}


def test_approved_reference_records_match_file_hashes_and_aspect(story):
    approvals = json.loads((PROJECT_DIR / "reference" / "approvals.json").read_text(encoding="utf-8"))
    for aid, row in approvals["assets"].items():
        if row.get("status") != "approved":
            continue
        path = PROJECT_DIR / row["file"]
        raw = path.read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        width, height = struct.unpack(">II", raw[16:24])
        assert row["dimensions"] == [width, height]
        assert build_sfx.digest(path) == row["sha256"]
        if row.get("type") in {"scene", "prop"}:
            assert width / height == pytest.approx(16 / 9, abs=0.015)


def test_sfx_generation_has_exact_timing_hashes_and_non_silent_pcm(story, tmp_path):
    output = tmp_path / "sfx"
    manifest = build_sfx.build(output)
    assert len(manifest["clips"]) == 30
    assert "no BGM" in manifest["policy"]
    shots = {shot["id"]: shot for shot in story["shots"]}
    for row in manifest["clips"]:
        path = output / row["file"]
        assert build_sfx.digest(path) == row["sha256"]
        assert row["script_note"] == shots[row["id"]]["sound_design"]
        with wave.open(str(path), "rb") as audio:
            assert audio.getnchannels() == 2
            assert audio.getframerate() == 48_000
            assert audio.getnframes() == round(row["seconds"] * 48_000)
            assert any(audio.readframes(audio.getnframes()))


def test_full_narration_manifest_is_shot_locked_and_hash_verified(story):
    manifest = json.loads((PROJECT_DIR / "audio" / "manifest.json").read_text(encoding="utf-8"))
    rows = {row["id"]: row for row in manifest["clips"]}
    assert len(rows) == 30
    assert manifest["voice"] == story["narration_spec"]["voice_id"]
    assert manifest["alignment"] == "one-clip-one-shot-one-caption"
    assert manifest["slowdown_allowed"] is False
    for shot in story["shots"]:
        row = rows[shot["id"]]
        audio = PROJECT_DIR / "audio" / row["file"]
        assert row["text"] == shot["narration"]
        assert row["voice_id"] == manifest["voice"]
        assert row["target_start"] == shot["start"]
        assert row["target_duration"] == shot["duration"]
        assert build_sfx.digest(audio) == row["sha256"]


def test_prompt_prefix_and_negative_policy(story):
    assert story["style_prefix"].startswith("【STYLE】")
    assert story["negative_prompt"].startswith("【NEGATIVE】")
    assert story["source_size"] == "720P"
    assert story["model"] == "agnes-video-2.5-flash"
    assert story["sfx_only"] is True
    for shot in story["shots"]:
        prompt = full_prompt(story, shot)
        assert prompt.startswith(story["style_prefix"])
        assert prompt.endswith(story["negative_prompt"])
        for role in shot["characters"]:
            assert story["characters"][role] in prompt


def test_ass_output_includes_big_hooks_and_gold_explainers(story, tmp_path):
    path = tmp_path / "captions.ass"
    presentation = story["presentation"]
    write_ass(path, [], presentation["highlight_phrases"],
              (presentation["end_title"], presentation["end_subtitle"],
               presentation["title_start"], presentation["title_end"]),
              presentation["onscreen_label"], presentation["hooks"], presentation["explainers"])
    ass = path.read_text(encoding="utf-8")
    plain_ass = re.sub(r"\{[^}]*\}", "", ass).replace(r"\N", "")
    assert "Style: Hook," in ass
    assert "Style: Explainer," in ass
    assert r"{\q2\fad" in ass
    assert r"\\q2" not in ass
    assert r"\\N" not in ass
    for hook in presentation["hooks"]:
        assert hook["text"] in plain_ass
    for explainer in presentation["explainers"]:
        assert explainer["text"] in plain_ass
    assert "AI动画情景重现 · 非真实影像" in ass
    assert "\\c&H0000C8FF&" in ass
    cover = tmp_path / "cover.ass"
    write_cover_ass(cover, presentation["cover_text"], presentation["end_title"])
    cover_ass = cover.read_text(encoding="utf-8")
    assert "Style: CoverTitle," in cover_ass
    assert presentation["cover_text"] in cover_ass
    assert presentation["end_title"] in cover_ass
    assert "22米胶带" in presentation["cover_concept"]
