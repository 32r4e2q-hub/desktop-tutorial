#!/usr/bin/env python3
"""Offline readiness check; never calls Agnes or creates a task.

仓库出厂的 preflight 曾死字面量绑定单一参考项目的角色代号（ROLE_TO_ASSET），
复制到新题目后永远报“unknown character role”，形同闸门失灵。现在改为从
story.json 的 character_reference_ids 现算映射：任何按 story 结构生成的新项目
都能直接通过本闸门，参考项目一字不动。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REL = HERE.relative_to(ROOT).as_posix()   # e.g. production/<slug>


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def asset_ids(shot: dict, story: dict) -> list[str]:
    """镜头 → 参考图资产编号。

    - ``characters[]`` 里的角色代号按 story.json 顶层的 ``character_reference_ids`` 现算；
    - ``reference_ids``（如 "C01+P02"、"S14"）按 approvals.json 的键原样解析；
    - 未登记的角色/ID 在这里或 approvals 校验里明确报错，绝不静默猜测。
    """
    role_map = story.get("character_reference_ids") or {}
    ids: list[str] = []
    for role in shot.get("characters", []):
        asset = role_map.get(role)
        if asset:
            ids.append(asset)
    for token in str(shot.get("reference_ids", "")).split("+"):
        token = token.strip().upper()
        if token:
            ids.append(token)
    return list(dict.fromkeys(ids))


def generated_sources_consistency() -> list[str]:
    """build_story.py 是 story.json 与两份脚本的唯一内容源。

    2026-11-19 事故：story.json 被手改而 build_story.py 仍在输出旧文案，CI 重跑
    build_story.py 静默覆盖、Agnes 按旧 request_hash 复用资产——零进度且误导发布。
    这里直接失败，不等烧掉额度再发现。
    """
    generated = [f"{REL}/story.json", f"{REL}/screenplay.md", f"{REL}/抖音脚本.md"]
    problems: list[str] = []
    try:
        proc = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *generated],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return []  # no git binary or no checkout; skip the guard rather than block offline work
    if proc.returncode != 0:
        problems.append(
            "story.json / screenplay.md / 抖音脚本.md 与 build_story.py 的输出不一致："
            "请运行 `python3 <本项目>/build_story.py` 后提交，"
            "不要手改这三个生成物（2026-11-19 事故：手改被 CI 重跑覆盖，镜头静默复用旧资产）")
    return problems


def main() -> int:
    consistency = generated_sources_consistency()
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    approvals = json.loads((HERE / "reference" / "approvals.json").read_text(encoding="utf-8"))
    assets = approvals.get("assets", {})
    expected = set(story["reference_designs"]["characters"] +
                   story["reference_designs"]["scenes"] +
                   story["reference_designs"]["props"])
    errors: list[str] = []
    incomplete: list[str] = []
    errors.extend(consistency)

    if len(story.get("shots", [])) != 30 or story.get("target_duration") != 180:
        errors.append("Storyboard must contain 30 shots and target 180 seconds")
    durations = [int(shot["duration"]) for shot in story.get("shots", [])]
    if not durations or sum(durations) != 180 or sum(durations) / len(durations) > 6.0:
        errors.append("Timeline must total 180 seconds and average no more than six seconds per shot")
    cursor = 0
    for shot in story.get("shots", []):
        if shot.get("start") != cursor:
            errors.append(f"{shot.get('id')}: non-contiguous start {shot.get('start')} (expected {cursor})")
        cursor += int(shot["duration"])
        if not 2 <= int(shot["duration"]) <= 14:
            errors.append(f"{shot.get('id')}: duration must be 2–14 seconds（时间码以 story.json 与定稿配音实测为准）")
        for role in shot.get("characters", []):
            if role not in story.get("character_reference_ids", {}):
                errors.append(f"{shot.get('id')}: unknown character role {role}")

    for aid in sorted(expected):
        row = assets.get(aid)
        if not row:
            incomplete.append(f"{aid}: no approval record")
            continue
        if row.get("status") != "approved":
            incomplete.append(f"{aid}: {row.get('status', 'not approved')}")
            continue
        path = HERE / row.get("file", "")
        if not path.is_file():
            errors.append(f"{aid}: approved PNG missing")
            continue
        raw = path.read_bytes()
        if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
            errors.append(f"{aid}: approved PNG invalid")
            continue
        width, height = struct.unpack(">II", raw[16:24])
        if row.get("dimensions") != [width, height]:
            errors.append(f"{aid}: recorded PNG dimensions do not match file")
        if row.get("type") in {"scene", "prop"} and abs(width / height - 16 / 9) > 0.015:
            errors.append(f"{aid}: scene/prop reference is not 16:9 ({width}x{height})")
        if sha256(path) != row.get("sha256"):
            errors.append(f"{aid}: approved PNG SHA-256 mismatch")

    for shot in story.get("shots", []):
        ids = asset_ids(shot, story)
        if not 1 <= len(ids) <= 5:
            errors.append(f"{shot.get('id')}: reference mode requires 1–5 image references, has {len(ids)}")
        missing = [aid for aid in ids if assets.get(aid, {}).get("status") != "approved"]
        if missing:
            incomplete.append(f"{shot['id']}: pending references {','.join(missing)}")

    try:
        revision = (HERE / "reference" / "revision.txt").read_text(encoding="utf-8").strip()
    except OSError:
        revision = ""
        incomplete.append("reference/revision.txt: missing (未钉住参考图快照 commit)")

    if revision:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", revision):
            incomplete.append("reference/revision.txt: immutable 40-character commit is not pinned")
        else:
            try:
                subprocess.run(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=ROOT,
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                incomplete.append("reference/revision.txt: commit is not available in this checkout")

    for aid, row in assets.items():
        asset_revision = row.get("revision")
        if not asset_revision:
            continue
        if not re.fullmatch(r"[0-9a-fA-F]{40}", str(asset_revision)):
            incomplete.append(f"{aid}: immutable asset revision is not pinned")
            continue
        asset_path = f"{REL}/{row.get('file', '')}"
        try:
            subprocess.run(["git", "cat-file", "-e", f"{asset_revision}:{asset_path}"], cwd=ROOT,
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            incomplete.append(f"{aid}: pinned commit does not contain the approved image")

    hooks = story["presentation"].get("hooks", [])
    required_hooks = {f"H{i}" for i in range(1, 10)}
    if not required_hooks.issubset({hook.get("id") for hook in hooks}):
        errors.append("All hooks H1–H9 must be present")
    for hook in hooks:
        if abs((float(hook["end"]) - float(hook["start"])) - 2.0) > 1e-6:
            errors.append(f"{hook.get('id')}: hook must be exactly 2 seconds")

    role_map = story.get("character_reference_ids", {})
    if set(story["characters"]) != set(role_map):
        errors.append("Character anchors and reference mapping do not match")
    if not story.get("negative_prompt", "").startswith("【NEGATIVE】"):
        errors.append("NEGATIVE block must remain the last prompt component")
    if not story.get("style_prefix", "").startswith("【STYLE】"):
        errors.append("STYLE block must be the first prompt component")
    if story.get("sfx_only") is not True:
        errors.append("Audio policy must be SFX-only, with no BGM")

    print(f"Story: {len(story['shots'])} shots / {sum(durations)} sec / average {sum(durations)/len(durations):.2f} sec")
    print(f"References: {len(expected)} expected; {sum(1 for aid in expected if assets.get(aid, {}).get('status') == 'approved')} approved")
    if errors:
        print("\nHARD ERRORS:")
        print("\n".join("- " + item for item in errors))
    if incomplete:
        print("\nNOT READY (no Agnes requests permitted):")
        print("\n".join("- " + item for item in sorted(set(incomplete))))
    if errors or incomplete:
        print("\nPREFLIGHT: BLOCKED")
        return 1
    print("\nPREFLIGHT: READY (offline only; API has not been called)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
