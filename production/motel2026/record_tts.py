#!/usr/bin/env python3
"""Register Arena TTS clips only after they were generated for the current V2 narration.

``build_story.py`` deliberately invalidates every audio checksum whenever narration text or
voice changes.  Once a batch has successfully returned from Arena ``generate_speech``, run:

    python3 production/motel2026/record_tts.py --voice voice-03 --ids S01,S02

The command records the exact clip SHA-256 together with the current text hash.  Rendering
and narration fitting reject rows that have not been registered this way, preventing stale
old-cut MP3s from silently entering the revised edit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", required=True, help="Arena voice ID used by generate_speech")
    parser.add_argument("--ids", required=True, help="comma-separated shot IDs generated in this batch")
    args = parser.parse_args()

    ids = [piece.strip() for piece in args.ids.split(",") if piece.strip()]
    if not ids or len(set(ids)) != len(ids):
        raise SystemExit("--ids must contain one or more distinct shot IDs")

    story_path = HERE / "story.json"
    manifest_path = HERE / "audio" / "manifest.json"
    story = json.loads(story_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_voice = story.get("narration_spec", {}).get("voice_id")
    if args.voice != expected_voice or manifest.get("voice") != expected_voice:
        raise SystemExit(f"Selected voice mismatch: expected {expected_voice!r}, got {args.voice!r}")

    shots = {shot["id"]: shot for shot in story["shots"]}
    rows = {row["id"]: row for row in manifest.get("clips", [])}
    missing = [sid for sid in ids if sid not in shots or sid not in rows]
    if missing:
        raise SystemExit("Unknown storyboard/manifest IDs: " + ", ".join(missing))

    for sid in ids:
        shot, row = shots[sid], rows[sid]
        text_sha = hashlib.sha256(shot["narration"].encode("utf-8")).hexdigest()
        clip = HERE / "audio" / row["file"]
        if not clip.is_file() or clip.stat().st_size < 100:
            raise SystemExit(f"Missing or implausibly small TTS clip: {clip}")
        if (row.get("text") != shot["narration"] or row.get("text_sha256") != text_sha
                or row.get("voice_id") != expected_voice):
            raise SystemExit(f"Storyboard / manifest mismatch: {sid}")
        row["audio_text_sha256"] = text_sha
        row["sha256"] = sha256(clip)
        row["generation_source"] = "Arena generate_speech confirmed"

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("REGISTERED " + ",".join(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
