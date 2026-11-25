#!/usr/bin/env python3
"""Fail when a recorded clip does not match the current script.

`build_audio_manifest.py` copies narration text from story.json, so its `text`
field can never reveal a stale recording. This checker compares against
`audio/spoken.json`, which records what was actually sent to TTS, and also
verifies the file hash has not drifted since the manifest was written.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STALE = "（旧版解说，已被 2026-11-24 重写取代，需重录）"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    spoken = json.loads((HERE / "audio" / "spoken.json").read_text(encoding="utf-8"))["spoken"]
    manifest = json.loads((HERE / "audio" / "manifest.json").read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in manifest.get("clips", [])}
    pending, problems = [], []
    for shot in story["shots"]:
        sid, want = shot["id"], shot["narration"]
        got = spoken.get(sid, "")
        audio = HERE / "audio" / f"{sid}.mp3"
        if got != want:
            pending.append(sid)
            continue
        if not audio.is_file():
            problems.append(f"{sid}: 音频文件缺失")
            continue
        row = rows.get(sid)
        if not row:
            problems.append(f"{sid}: manifest 缺少记录")
        elif row.get("sha256") != digest(audio):
            problems.append(f"{sid}: 音频哈希与 manifest 不符（重录后未重建 manifest）")
    if pending:
        print(f"待重录 {len(pending)} 条: {', '.join(pending)}")
    for p in problems:
        print("错误:", p)
    if not pending and not problems:
        print("全部 30 条配音与当前脚本一致。")
    return 1 if pending or problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
