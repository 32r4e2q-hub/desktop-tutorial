#!/usr/bin/env python3
"""Offline readiness check; never calls Agnes or creates a task."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ROLE_TO_ASSET = {
    "LIYINGPING": "C01", "LIYINGPING_SIDE": "C02", "LIYINGPING_BACK": "C03",
    "ZHUXIAODONG": "C04", "ZHUXIAODONG_BACK": "C05",
    "YANGMU": "C06", "YANGFU": "C07", "YANGFU_BACK": "C08",
    "EXTRA_BACK": "C09", "POLICE_BACK": "C10",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def asset_ids(shot: dict) -> list[str]:
    ids = [ROLE_TO_ASSET[role] for role in shot.get("characters", [])]
    for token in str(shot.get("reference_ids", "")).split("+"):
        token = token.strip().upper()
        if token:
            ids.append(token)
    return list(dict.fromkeys(ids))


def generated_sources_consistency() -> list[str]:
    """build_story.py is the only source of truth for story.json and the two script docs.

    2026-11-19 incident: story.json was hand-edited while build_story.py still emitted the
    old text; CI re-ran build_story.py, silently wiped the edit, and the Agnes run reused the
    stale request hashes (reused_existing_asset=true) — a no-op that burned CI minutes and
    kept publishing the non-compliant footage. Never hand-edit generated files; edit
    build_story.py and regenerate. Fail loudly here instead of burning Agnes quota.
    """
    generated = [
        "production/elisalam2013/story.json",
        "production/elisalam2013/screenplay.md",
        "production/elisalam2013/抖音脚本.md",
    ]
    problems: list[str] = []
    try:
        proc = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *generated],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return []  # no git binary or no checkout; skip the guard rather than block offline work
    if proc.returncode != 0:
        problems.append(
            "story.json / screenplay.md / 抖音脚本.md 与 build_story.py 的输出不一致："
            "请运行 `python3 production/elisalam2013/build_story.py` 后提交，"
            "不要手改这三个生成物（2026-11-19 事故：手改被 CI 重跑覆盖，六镜静默复用旧资产）")
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
            if role not in ROLE_TO_ASSET:
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
        ids = asset_ids(shot)
        if not 1 <= len(ids) <= 5:
            errors.append(f"{shot['id']}: reference mode requires 1–5 image references, has {len(ids)}")
        missing = [aid for aid in ids if assets.get(aid, {}).get("status") != "approved"]
        if missing:
            incomplete.append(f"{shot['id']}: pending references {','.join(missing)}")

    revision = (HERE / "reference" / "revision.txt").read_text(encoding="utf-8").strip()
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
        asset_path = f"production/elisalam2013/{row.get('file', '')}"
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

    role_set = set(ROLE_TO_ASSET)
    if set(story["characters"]) != role_set:
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
