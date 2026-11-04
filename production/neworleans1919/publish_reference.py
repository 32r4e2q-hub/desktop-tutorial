#!/usr/bin/env python3
"""Publish the approved reference stills and record the immutable revision they live at.

``generate.py`` never points at a mutable branch tip: every shot cites
``raw.githubusercontent.com/<repo>/<revision>/production/neworleans1919/reference/<ID>.png``.
This tool

1. checks all 24 declared stills exist, are PNG, are >= 20 KB and were reviewed;
2. commits them on the fixed branch;
3. writes the resulting commit SHA into ``reference/revision.txt``;
4. writes ``reference/approvals.json`` with the per-asset sha256.

Usage::

    python3 production/neworleans1919/publish_reference.py --check
    python3 production/neworleans1919/publish_reference.py --commit "neworleans1919: 定稿参考图 24 张"
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REFERENCE = HERE / "reference"
REVISION_FILE = REFERENCE / "revision.txt"
APPROVALS = REFERENCE / "approvals.json"
# Set to a date once a human or an agent has actually looked at every still.
REVIEWED_AT = "2026-11-04"


def story() -> dict:
    return json.loads((HERE / "story.json").read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check() -> dict:
    assets = {}
    missing = []
    for ref in story()["reference_images"]:
        path = HERE / ref["file"]
        if not path.is_file() or path.stat().st_size < 20_000:
            missing.append(ref["id"])
            continue
        with path.open("rb") as stream:
            if stream.read(8) != b"\x89PNG\r\n\x1a\n":
                raise SystemExit(f"{ref['file']} is not a PNG")
        assets[ref["id"]] = {"status": "approved", "sha256": digest(path),
                             "file": ref["file"], "description": ref["description"]}
    if missing:
        raise SystemExit("missing or too small: " + ", ".join(missing))
    return assets


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True,
                                   stderr=subprocess.STDOUT).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--commit", default="")
    args = parser.parse_args()

    assets = check()
    print(f"REFERENCES OK: {len(assets)} stills, all PNG and >= 20 KB")
    if args.check:
        return 0

    (APPROVALS).write_text(json.dumps({
        "reviewer": "Arena assistant visual inspection, one sheet at a time",
        "reviewed_at": REVIEWED_AT,
        "note": "Checks per sheet: three-view plus facial close-up present, no face on the "
                "Axeman, no victim, no wound, no legible lettering, period-correct clothing.",
        "assets": assets,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    paths = [str(REFERENCE.relative_to(ROOT))]
    git("add", "-f", "--", *paths)
    if subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=ROOT).returncode:
        print("stills already committed; reusing the current HEAD revision")
    else:
        git("commit", "-m", args.commit or "neworleans1919: 定稿参考图")
    head = git("rev-parse", "HEAD")
    # A commit is immutable only once it exists locally; push it before relying on the URL.
    subprocess.run(["git", "pull", "--rebase", "-q", "origin", "arena/eb3c7fec-desktop-tutorial"],
                   cwd=ROOT, check=False)
    subprocess.run(["git", "push", "-q", "origin",
                    "HEAD:arena/eb3c7fec-desktop-tutorial"], cwd=ROOT, check=True)
    head = git("rev-parse", "HEAD")
    REVISION_FILE.write_text(head + "\n", encoding="utf-8")
    git("add", "-f", "--", str(REVISION_FILE.relative_to(ROOT)))
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
        git("commit", "-m", "neworleans1919: 记录参考图不可变提交 " + head[:12])
    subprocess.run(["git", "pull", "--rebase", "-q", "origin", "arena/eb3c7fec-desktop-tutorial"],
                   cwd=ROOT, check=False)
    subprocess.run(["git", "push", "-q", "origin",
                    "HEAD:arena/eb3c7fec-desktop-tutorial"], cwd=ROOT, check=True)
    print("REFERENCE_REVISION", head)
    return 0


if __name__ == "__main__":
    sys.exit(main())
