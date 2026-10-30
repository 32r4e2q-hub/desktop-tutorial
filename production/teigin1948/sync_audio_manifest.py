#!/usr/bin/env python3
"""Refresh shot-locked voice manifest from the current rendered audio/Sxx.mp3 files."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
voice_id = story["narration_spec"]["voice_id"]
clips = []
missing = []
for shot in story["shots"]:
    audio = HERE / "audio" / f"{shot['id']}.mp3"
    if not audio.is_file():
        missing.append(shot["id"])
        continue
    clips.append({
        "id": shot["id"],
        "file": audio.name,
        "voice_id": voice_id,
        "alignment": "shot-locked",
        "narration_id": shot["narration_id"],
        "target_start": shot["start"],
        "target_duration": shot["duration"],
        "text": shot["narration"],
        "sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
    })
manifest = {
    "voice": voice_id,
    "language": "zh-CN",
    "alignment": "one-clip-one-shot-one-caption",
    "slowdown_allowed": bool(story["narration_spec"].get("slowdown_allowed", False)),
    "min_tempo_factor": story["narration_spec"].get("min_tempo_factor", 1.0),
    "max_speedup_factor": story["narration_spec"].get("max_speedup_factor", 1.0),
    "clips": clips,
}
(HERE / "audio" / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"manifest clips={len(clips)}/29; missing={','.join(missing) if missing else 'none'}")
if missing:
    raise SystemExit(1)
