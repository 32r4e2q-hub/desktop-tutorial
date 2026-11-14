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
    "SANA": "C01", "MOTHER": "C02", "MOTHER_NEUTRAL": "C02N", "MOTHER_OLD": "C02B", "FATHER": "C03",
    "DETECTIVE": "C04", "EX": "C05", "FAMILIAR": "C06", "EXPERT": "C07",
    "TEAM_2024": "C08", "SHADOW": "C09",
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


def main() -> int:
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    approvals = json.loads((HERE / "reference" / "approvals.json").read_text(encoding="utf-8"))
    assets = approvals.get("assets", {})
    expected = set(story["reference_designs"]["characters"] +
                   story["reference_designs"]["scenes"] +
                   story["reference_designs"]["props"])
    errors: list[str] = []
    incomplete: list[str] = []

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
        if not 5 <= int(shot["duration"]) <= 7:
            errors.append(f"{shot.get('id')}: duration must be 5–7 seconds")
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
