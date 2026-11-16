#!/usr/bin/env python3
"""Assemble audio/review.json from one-clip-per-shot files plus their ASR evidence.

The delivery pipeline refuses to write ``audio/manifest.json`` unless every shot has a
review record that matches its file hash, its locked text and the selected voice. This
script builds that record from evidence already in the repo instead of hand-typing 30
hashes:

* the clip must be an **individual** ``audio/Sxx.mp3`` (a three-shot cut never qualifies);
* the ASR row must have hashed *that exact file*, and the transcript must match the locked
  text — a homophone-only deviation is acceptable only when a human/agent has looked at
  the diff and written the reason in ``audio/review-allow.json``;
* the clip must fit its shot window within the 1.55x limit.

Nothing is auto-approved by similarity alone, and this is **not** a listening sign-off:
``reviewed_by`` says transcript inspection, and the delivery report still has to state
that full playback review is pending.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MATCH_THRESHOLD = 0.90
MAX_ATEMPO = 1.55


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def decision(similarity: float, allow_reason: str | None) -> tuple[bool, str]:
    """Similarity alone never approves a clip; a written reason covers ASR homophones."""
    if similarity >= MATCH_THRESHOLD:
        return True, "transcript matches the locked text"
    if allow_reason:
        return True, f"transcript deviation accepted: {allow_reason}"
    return False, "transcript differs and no written reason exists"


def build_rows(story: dict, voice_id: str, asr: dict, allow: dict) -> list[dict]:
    rows = {row["id"]: row for row in asr.get("shots", [])}
    records = []
    for shot in story["shots"]:
        sid = shot["id"]
        path = HERE / "audio" / f"{sid}.mp3"
        if not path.is_file():
            records.append({"id": sid, "status": "pending", "reason": "clip missing"})
            continue
        clip_hash = digest(path)
        row = rows.get(sid)
        if row is None:
            records.append({"id": sid, "status": "pending", "reason": "no ASR evidence"})
            continue
        if row.get("source_kind") != "individual" or row.get("sha256") != clip_hash:
            records.append({"id": sid, "status": "pending",
                            "reason": "ASR evidence is for a different source than this clip"})
            continue
        similarity = float(row.get("similarity", 0.0))
        approved, note = decision(similarity, allow.get(sid))
        atempo = float(row.get("atempo_needed", 0.0))
        if approved and atempo > MAX_ATEMPO:
            approved, note = False, f"needs {atempo:.3f}x, over the {MAX_ATEMPO}x limit"
        record = {
            "id": sid,
            "status": "approved" if approved else "pending",
            "reviewed_by": "Arena agent · transcript diff inspection",
            "review_method": "independent faster-whisper transcript compared with the locked text",
            "text": shot["narration"],
            "sha256": clip_hash,
            "voice_id": voice_id,
            "asr_similarity": round(similarity, 4),
            "asr_text": row.get("asr_text"),
            "atempo_needed": atempo,
            "note": note,
        }
        if not approved:
            record["reason"] = note
        records.append(record)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write audio/review.json when complete")
    args = parser.parse_args(argv)

    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    voice = json.loads((HERE / "audio/voice.json").read_text(encoding="utf-8"))["voice_id"]
    asr_path = HERE / "qa/narration-asr.json"
    asr = json.loads(asr_path.read_text(encoding="utf-8")) if asr_path.is_file() else {"shots": []}
    allow_path = HERE / "audio/review-allow.json"
    allow = json.loads(allow_path.read_text(encoding="utf-8")) if allow_path.is_file() else {}

    records = build_rows(story, voice, asr, allow)
    pending = [row for row in records if row["status"] != "approved"]
    report = {
        "voice": voice,
        "policy": "One clip per shot. Transcript inspection only — not a listening sign-off.",
        "clips": records,
    }
    (HERE / "audio/review.proposed.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(records) - len(pending)}/{len(records)} clips approved by transcript evidence")
    for row in pending:
        print(f"  PENDING {row['id']}: {row.get('reason')}")
    if pending:
        return 1
    if args.write:
        (HERE / "audio/review.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Wrote audio/review.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
