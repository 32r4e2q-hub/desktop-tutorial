#!/usr/bin/env python3
"""Assemble the user-uploaded commentary video from verified Git chunks."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PARTS_DIR = Path(__file__).resolve().parent / "source_parts"
EXPECTED_SIZE = 182_506_802
EXPECTED_SHA256 = "F2DAD2D76B01C5F648CCC7B6107BF50B76952237FA5EC18DB8B038C6958D54D8"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Retained for workflow compatibility")
    parser.add_argument("output")
    args = parser.parse_args()

    manifest_path = PARTS_DIR / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"Uploaded source manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    digest = hashlib.sha256()
    with output.open("wb") as destination:
        for part_name in manifest["parts"]:
            part = PARTS_DIR / part_name
            if not part.exists():
                raise RuntimeError(f"Uploaded source part is missing: {part}")
            print(f"Assembling {part.name} ({part.stat().st_size} bytes)...", flush=True)
            with part.open("rb") as source:
                for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
                    destination.write(block)
                    digest.update(block)

    actual_size = output.stat().st_size
    actual_sha256 = digest.hexdigest().upper()
    if actual_size != EXPECTED_SIZE:
        raise RuntimeError(f"Uploaded source size mismatch: {actual_size} != {EXPECTED_SIZE}")
    if actual_sha256 != EXPECTED_SHA256:
        raise RuntimeError(
            f"Uploaded source checksum mismatch: {actual_sha256} != {EXPECTED_SHA256}"
        )
    print(
        f"UPLOADED SOURCE VERIFIED: {actual_size} bytes / SHA256 {actual_sha256}",
        flush=True,
    )


if __name__ == "__main__":
    main()
