#!/usr/bin/env python3
"""Build cross-shot contact sheets for CogVideoX identity-reference review.

Every visible recurring character is supplied with the same image-to-video
reference in each shot. This script verifies reference SHA-256 provenance and
places the reference beside generated frames; it deliberately does not claim
that probabilistic video output is automatically identity-perfect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CELL = (320, 180)
PAD = 14
LABEL_H = 34


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def font(size: int):
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def midframe(video: Path, dest: Path, seconds: float) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(video),
        "-an", "-frames:v", "1", "-vf", f"scale={CELL[0]}:{CELL[1]}:force_original_aspect_ratio=decrease,pad={CELL[0]}:{CELL[1]}:(ow-iw)/2:(oh-ih)/2",
        "-q:v", "3", str(dest),
    ]
    subprocess.run(command, check=True, capture_output=True)
    if not dest.is_file():
        raise RuntimeError(f"ffmpeg did not extract a face-review frame from {video}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--project", type=Path, default=HERE / "story.json")
    parser.add_argument("--results", type=Path, default=HERE / "results.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    project = json.loads(args.project.read_text(encoding="utf-8"))
    results = json.loads(args.results.read_text(encoding="utf-8"))
    if results.get("model") != "cogvideox-flash":
        raise RuntimeError("Identity audit accepts only CogVideoX-Flash receipts")
    shots = {row["id"]: row for row in project["shots"] if row["kind"] == "cogvideo"}
    receipts = results.get("shots", {})
    args.out.mkdir(parents=True, exist_ok=True)

    all_ids = sorted({cid for shot in shots.values() for cid in shot.get("character_ids", [])})
    summary = {
        "provider": "Zhipu AI",
        "model": "cogvideox-flash",
        "identity_policy": "one stable reference image per recurring visible identity; base64 image-to-video input; distinct IDs use distinct reference designs",
        "human_visual_review": "required; contact sheets are evidence, not an automated guarantee",
        "characters": {},
    }
    review_font = font(18)
    for cid in all_ids:
        character = project["characters"][cid]
        ids = [sid for sid, shot in shots.items() if cid in shot.get("character_ids", [])]
        reference_rel = character.get("reference_image", "")
        reference = HERE / reference_rel if reference_rel else None
        reference_hash = sha256(reference) if reference and reference.is_file() else None
        rows = []
        mismatches = []
        for sid in ids:
            shot = shots[sid]
            receipt = receipts.get(sid, {})
            if receipt.get("status") != "completed":
                raise RuntimeError(f"{cid}/{sid}: no successful CogVideoX receipt")
            expected_ref = shot.get("reference_image", "")
            expected_sha = sha256(HERE / expected_ref) if expected_ref else None
            if receipt.get("reference_sha256") != expected_sha:
                mismatches.append({"shot": sid, "expected": expected_sha, "recorded": receipt.get("reference_sha256")})
            if shot.get("face_visible") and expected_sha != reference_hash:
                mismatches.append({"shot": sid, "expected_canonical": reference_hash, "used": expected_sha})
            video = args.sources / f"{sid}.mp4"
            if not video.is_file() or sha256(video) != receipt.get("sha256"):
                raise RuntimeError(f"{cid}/{sid}: missing or hash-mismatched generated video")
            duration = float(receipt.get("media", {}).get("duration", 6.0))
            frame = args.out / "frames" / f"{sid}.jpg"
            midframe(video, frame, min(duration / 2, 2.5))
            rows.append({"shot": sid, "frame": frame, "reference_sha256": expected_sha})

        tiles = []
        if reference and reference.is_file():
            tiles.append(("CANONICAL REF", reference))
        for row in rows:
            tiles.append((row["shot"], row["frame"]))
        columns = min(4, max(1, len(tiles)))
        tile_w, tile_h = CELL[0], CELL[1] + LABEL_H
        lines = (len(tiles) + columns - 1) // columns
        sheet = Image.new("RGB", (PAD + columns * (tile_w + PAD), PAD + lines * (tile_h + PAD)), "#101820")
        draw = ImageDraw.Draw(sheet)
        for index, (label, path) in enumerate(tiles):
            x = PAD + (index % columns) * (tile_w + PAD)
            y = PAD + (index // columns) * (tile_h + PAD)
            im = ImageOps.fit(Image.open(path).convert("RGB"), CELL, method=Image.Resampling.LANCZOS)
            sheet.paste(im, (x, y))
            draw.text((x + 2, y + CELL[1] + 6), label, fill="#f2eadb", font=review_font)
        contact = args.out / f"{cid}.jpg"
        sheet.save(contact, quality=88, optimize=True)
        summary["characters"][cid] = {
            "name": character.get("name"),
            "role": character.get("role"),
            "reference_image": reference_rel or None,
            "reference_sha256": reference_hash,
            "shots": ids,
            "reference_hash_consistent_for_visible_faces": not mismatches,
            "reference_mismatches": mismatches,
            "contact_sheet": contact.name,
            "visual_identity_review": "pending human review",
        }

    summary["status"] = "PASS_REFERENCE_PROVENANCE" if all(
        row["reference_hash_consistent_for_visible_faces"] for row in summary["characters"].values()
    ) else "FAIL_REFERENCE_PROVENANCE"
    out_path = args.out / "summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("CHARACTER_IDENTITY_AUDIT", json.dumps({
        cid: {"shots": row["shots"], "visible_face_reference_consistent": row["reference_hash_consistent_for_visible_faces"],
              "contact_sheet": row["contact_sheet"]}
        for cid, row in summary["characters"].items()
    }, ensure_ascii=False))
    if summary["status"] != "PASS_REFERENCE_PROVENANCE":
        raise RuntimeError("Character reference provenance mismatch; inspect summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
