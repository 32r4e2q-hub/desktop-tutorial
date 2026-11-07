#!/usr/bin/env python3
"""从已核验的原始片段（无字幕、无角标）里导出封面候选帧到 qa_final/cover_frames/。"""
import json, subprocess, sys
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("itaewon_render", HERE / "render.py")
render = importlib.util.module_from_spec(spec); sys.modules["itaewon_render"] = render; spec.loader.exec_module(render)

PICKS = {"S08": (1.0, 2.5, 4.0), "S10": (1.5, 3.0), "S27": (1.5, 3.0), "S09": (1.5, 3.0), "S12": (1.5, 3.0), "S26": (2.0, 3.5)}


def main():
    results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    out = HERE / "qa_final" / "cover_frames"; out.mkdir(parents=True, exist_ok=True)
    raw = ROOT / "work/itaewon1997/cover_raw"
    for sid, times in PICKS.items():
        row = results["shots"][sid]; dest = raw / f"{sid}.mp4"
        render.download(row["video_url"], dest, row["sha256"], int(row["bytes"]))
        for t in times:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(dest), "-frames:v", "1", "-q:v", "2",
                            str(out / f"{sid}_{t:.1f}.jpg")], check=True)
    print("frames:", sorted(p.name for p in out.glob("*.jpg")))


if __name__ == "__main__":
    sys.exit(main())
