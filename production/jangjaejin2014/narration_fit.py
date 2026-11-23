#!/usr/bin/env python3
"""Check each selected narration clip against its shot window without slowing speech."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def duration(path: Path) -> float:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ], text=True)
    return float(raw.strip())


def main() -> int:
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    manifest = json.loads((HERE / "audio" / "manifest.json").read_text(encoding="utf-8"))
    rows = {row["id"]: row for row in manifest.get("clips", [])}
    lines = ["# 逐镜旁白时长检查", "", "| 镜头 | 目标秒数 | 音频秒数 | 需要加速 | 结果 |", "|---|---:|---:|---:|---|"]
    failures = []
    for shot in story["shots"]:
        sid = shot["id"]
        row = rows.get(sid)
        if not row:
            failures.append(f"{sid}: manifest record missing")
            continue
        path = HERE / "audio" / row.get("file", "")
        if not path.is_file():
            failures.append(f"{sid}: audio file missing")
            continue
        raw = duration(path)
        target = float(shot["duration"])
        factor = max(1.0, raw / target)
        status = "PASS" if factor <= 1.55 + 1e-9 else "FAIL"
        lines.append(f"| {sid} | {target:.3f} | {raw:.3f} | {factor:.3f}x | {status} |")
        if factor > 1.55 + 1e-9:
            failures.append(f"{sid}: requires {factor:.3f}x (limit 1.55x)")
    out = HERE / "qa" / "narration-fit.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines += ["", f"旁白剪辑校验：{'FAIL' if failures else 'PASS'}。仅加速、不拉慢；超出上限即阻止出片。"]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(failures) if failures else "All 30 narration clips fit their shot windows.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
