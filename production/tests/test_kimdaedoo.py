#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金大斗案 · 离线闸门测试（不联网、不消耗 Agnes 额度）。

守的是“一次生成就要排队几小时，所以生成前必须确定提示词没错”这件事：
- 30 镜 × 6 秒 = 180 秒，章节相加 180
- 每个露脸镜头的 face token 逐字节存在，两个角色不撞脸
- 提示词里没有血/遗体/现代设备/多场景；旁白字数和关键事实齐全
- Agnes payload 形状（seconds 字符串、720P、mode、没有禁用字段）
- 工作流 shape：分支、61 秒节奏、自动接力、出片触发条件

跑法：
    python -m pytest production/tests/test_kimdaedoo.py -q
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "kimdaedoo"
STORY = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
CAST = json.loads((PROJECT / "cast.json").read_text(encoding="utf-8"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def clean_len(text: str) -> int:
    return len(re.sub(r"[，。、；：“”《》（）\s]", "", text))


# ------------------------------------------------------------------ 时间轴
def test_timeline_is_exactly_180_seconds():
    shots = STORY["shots"]
    assert len(shots) == 30
    assert [s["id"] for s in shots] == [f"S{i:02d}" for i in range(1, 31)]
    assert sum(s["duration"] for s in shots) == 180
    for index, shot in enumerate(shots):
        assert shot["start"] == index * 6
        assert shot["duration"] == 6
        assert shot["seconds"] == 6
        assert shot["aspect"] == "16:9"


def test_chapters_cover_the_whole_timeline():
    chapters = STORY["chapters"]
    assert sum(c["duration"] for c in chapters) == 180
    cursor = 0
    for chapter in chapters:
        assert chapter["start"] == cursor
        cursor += chapter["duration"]
    assert cursor == 180


def test_narration_fits_into_six_seconds_per_shot():
    total = 0
    for shot in STORY["shots"]:
        chars = clean_len(shot["narration"])
        assert 14 <= chars <= 34, f"{shot['id']} 旁白 {chars} 字"
        total += chars
    # 180 秒 × 3.3–4.0 字/秒
    assert 600 <= total <= 720, total


def test_key_facts_survive_condensing():
    joined = "".join(s["narration"] for s in STORY["shots"])
    for fact in ("55天", "17", "9起案件", "3人重伤", "1975", "1976", "27岁", "牛仔裤"):
        assert fact in joined, fact


def test_source_script_is_preserved_per_shot():
    """原稿 1438 字是内容唯一来源：压缩后的旁白之外，原文必须还在。"""
    raw = PROJECT / "source-script.txt"
    assert raw.is_file()
    text = raw.read_text(encoding="utf-8")
    assert text.count("### 镜头") == 30
    total = 0
    for shot in STORY["shots"]:
        assert shot["source_narration"], shot["id"]
        assert shot["source_prompt"], shot["id"]
        flat = re.sub(r"\s+", "", text)
        assert re.sub(r"\s+", "", shot["source_narration"]) in flat, shot["id"]
        total += clean_len(shot["source_narration"])
    assert total > 1300, total  # 原稿旁白约 1438 字


# ------------------------------------------------------------------ 角色与提示词
def test_face_tokens_are_byte_exact_per_shot():
    faces = {c["id"]: c["face"] for c in CAST["characters"]}
    assert len(set(faces.values())) == len(faces), "两个角色的 face token 不能相同"
    for sid, ids in CAST["shots"].items():
        prompt = next(s["prompt"] for s in STORY["shots"] if s["id"] == sid)
        for cid in ids:
            assert faces[cid] in prompt, f"{sid} 缺 {cid} 的 face token"


def test_face_tokens_do_not_leak_into_other_shots():
    faces = {c["id"]: c["face"] for c in CAST["characters"]}
    for shot in STORY["shots"]:
        declared = set(shot.get("cast") or [])
        for cid, face in faces.items():
            if cid not in declared:
                assert face not in shot["prompt"], f"{shot['id']} 夹带了 {cid} 的脸"


def test_prompts_are_single_scene_with_camera_and_year():
    camera = ("push-in", "pull-back", "tracking", "dolly", "crane", "pan", "drift",
              "tilt", "lateral", "orbit", "handheld", "zoom", "focus pull")
    for shot in STORY["shots"]:
        prompt = shot["prompt"]
        assert 200 <= len(prompt) <= 1000, (shot["id"], len(prompt))
        assert re.search(r"\b(1975|1976)\b", prompt), shot["id"]
        assert any(word in prompt.lower() for word in camera), shot["id"]
        for word in ("montage", "cut to", "jump cut", "meanwhile"):
            assert word not in prompt.lower(), (shot["id"], word)


def test_prompts_avoid_gore_text_and_modern_tech():
    """与 audit_prompts.py 用同一套否定句剥离规则，避免两套判据漂移。"""
    audit = load_module("kd_audit_rules", PROJECT / "audit_prompts.py")
    for shot in STORY["shots"]:
        stripped = audit.clean(shot["prompt"])
        for word in audit.BANNED_VIOLENCE:
            assert word not in stripped, (shot["id"], word)
        for word in audit.BANNED_MODERN:
            pattern = r"\b" + re.escape(word) + r"\b" if " " not in word else re.escape(word)
            assert not re.search(pattern, stripped), (shot["id"], word)
        for word in audit.BANNED_TEXT:
            assert word not in stripped, (shot["id"], word)
        for word in audit.BANNED_REAL_PERSON:
            assert word not in shot["prompt"].lower(), (shot["id"], word)


def test_prompt_audit_gate_passes():
    result = subprocess.run([sys.executable, str(PROJECT / "audit_prompts.py")],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((PROJECT / "delivery" / "prompt-audit.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["narration_chars"] == 666


def test_face_cast_static_gate_passes():
    # 用相对路径跑：face_cast 会把 project 原样写进报告，绝对路径会让仓库每次都变脏。
    result = subprocess.run([sys.executable, "production/face_cast.py",
                             "check-prompts", "--project", "production/kimdaedoo"],
                            capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_audit_gate_catches_a_planted_violation(tmp_path):
    """闸门本身也要被测试：故意把 S01 改成“血 + 跳切 + 没有运镜”，必须判红。"""
    story = json.loads(json.dumps(STORY))
    story["shots"][0]["prompt"] = ("1975 Korean laundry shop, blood on the counter, "
                                   "hard cut to a corpse, no camera movement")
    story_path = tmp_path / "story.json"
    story_path.write_text(json.dumps(story, ensure_ascii=False), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(PROJECT / "audit_prompts.py"),
         "--story", str(story_path), "--report", str(tmp_path / "audit.json")],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 1, result.stdout
    report = json.loads((tmp_path / "audit.json").read_text(encoding="utf-8"))
    joined = " | ".join(report["errors"])
    assert "S01" in joined
    assert "blood" in joined.lower() or "暴力" in joined
    assert "hard cut" in joined


# ------------------------------------------------------------------ payload
def test_agnes_payload_shape():
    gen = load_module("kd_generate", PROJECT / "generate.py")
    project = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
    gen.validate(project)  # 不抛异常就是过
    for shot in project["shots"]:
        payload = gen.full_payload(project, shot)
        assert payload["model"] == "agnes-video-2.5-flash"
        assert payload["size"] == "720P"
        assert payload["seconds"] == "6"
        assert payload["mode"] == "text"
        assert payload["n"] == 1
        assert isinstance(payload["seed"], int)
        for banned in ("width", "height", "fps", "num_frames", "duration",
                       "resolution", "negative_prompt"):
            assert banned not in payload
        assert "readable text" in payload["prompt"]  # 红线必须压进正文


def test_creation_interval_is_61_seconds():
    throttle = load_module("kd_throttle", PROJECT / "throttle.py")
    gate = throttle.RequestGate(minimum_interval=61, clock=lambda: 0.0, sleep=lambda _: None)
    assert gate.interval == 61
    with pytest.raises(ValueError):
        throttle.RequestGate(minimum_interval=59)


# ------------------------------------------------------------------ 工作流
def test_workflows_target_this_branch_and_pace_61s():
    gen = (ROOT / ".github" / "workflows" / "kimdaedoo-gen.yml").read_text(encoding="utf-8")
    final = (ROOT / ".github" / "workflows" / "kimdaedoo-final.yml").read_text(encoding="utf-8")
    assert "arena/b726ea5e-desktop-tutorial" in gen
    assert "arena/b726ea5e-desktop-tutorial" in final
    assert "queue-full lottery every 61s" in gen
    assert "gh workflow run kimdaedoo-final.yml" in gen
    assert "AGNES_API_KEY" in gen
    assert "gh release create" in final
    assert "finalize.py" in final


def test_generator_branch_constant_matches_workflow():
    text = (PROJECT / "generate.py").read_text(encoding="utf-8")
    assert "BRANCH='arena/b726ea5e-desktop-tutorial'" in text
    assert "QUEUE_COOLDOWN_SECONDS=61" in text
    assert "gate=RequestGate(minimum_interval=61)" in text


def test_finalize_refuses_stale_prompt_clips():
    """提示词改过之后，旧素材不能混进成片：finalize 必须比对 request_hash。"""
    text = (PROJECT / "finalize.py").read_text(encoding="utf-8")
    assert "def stale_shots()" in text
    assert "request_hash" in text
    assert "素材来自旧提示词" in text
    # 必须在下载之前拦下，否则会先花时间拉 30 条旧片
    assert text.index("stale_shots()") < text.index("下载 30 镜并校验")
