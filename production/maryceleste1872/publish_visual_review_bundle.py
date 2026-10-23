#!/usr/bin/env python3
"""Publish compact final-cut visual evidence into the repository for review.

GitHub Actions artifacts expire and, in restricted environments, their Azure Blob
download URL may be unreachable. This copies only the compact review surfaces:
all-frame thumbnail sheets, dense hand contact sheets, and selected 960px review
candidates. It does not copy the film, per-frame metrics CSV, or arbitrary raw
intermediates.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


HAND_GLOB = "hands-*.jpg"


def _copy_files(source: Path, pattern: str, destination: Path) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for path in sorted(source.glob(pattern)):
        if path.is_file():
            target = destination / path.name
            shutil.copy2(path, target)
            copied.append(str(target))
    return copied


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--film", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--all-frames", type=Path, required=True)
    ap.add_argument("--contacts", type=Path, required=True)
    ap.add_argument("--candidates", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    if not args.film.is_file():
        raise SystemExit(f"Missing film: {args.film}")
    for source in (args.all_frames, args.contacts, args.candidates):
        if not source.is_dir():
            raise SystemExit(f"Missing visual evidence directory: {source}")

    temporary = args.out.with_name(args.out.name + ".tmp")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)

    all_frames = _copy_files(args.all_frames, "*-all-frames.jpg", temporary / "all-frames")
    manifests = _copy_files(args.all_frames, "manifest.json", temporary / "all-frames")
    hands = _copy_files(args.contacts, HAND_GLOB, temporary / "hands")
    midpoints = _copy_files(args.contacts, "shot-midpoints.jpg", temporary / "midpoints")
    candidates = _copy_files(args.candidates, "*.jpg", temporary / "candidates")
    candidate_manifests = _copy_files(args.candidates, "manifest.json", temporary / "candidates")

    # 每段一张全帧表，段数因项目而异（本片 31 镜+片尾卡）；模板里写死的 46
    # 是老项目的段数，2026-10-23 在本片视觉 QC 上把发布步卡死过一次。
    # 正确出处是 compose_all_frame_sheets 写的 manifest.json 的 sheets 清单。
    manifest_doc = {}
    manifest_path = args.all_frames / "manifest.json"
    if manifest_path.is_file():
        manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = len(manifest_doc.get("sheets") or [])
    if not all_frames:
        raise SystemExit("No final-cut all-frame sheets found")
    if expected and len(all_frames) != expected:
        raise SystemExit(
            f"Expected {expected} final-cut all-frame sheets per manifest, found {len(all_frames)}")
    if not hands:
        raise SystemExit("No final-cut hand contact sheets found")
    if not candidates:
        raise SystemExit("No selected review candidate frames found")

    receipt = {
        "film": args.film.name,
        "sha256": audit.get("sha256"),
        "decoded_frames": audit.get("video", {}).get("decoded_frames"),
        "source_audit": str(args.audit),
        "contents": {
            "all_frame_sheets": len(all_frames),
            "all_frame_manifests": len(manifests),
            "hand_contact_sheets": len(hands),
            "midpoint_contact_sheets": len(midpoints),
            "selected_candidate_frames": len(candidates),
            "candidate_manifests": len(candidate_manifests),
        },
        "scope": (
            "compact review evidence only; does not equal a human approval and does not "
            "replace the delivered MP4"
        ),
    }
    (temporary / "README.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if args.out.exists():
        shutil.rmtree(args.out)
    temporary.replace(args.out)
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
