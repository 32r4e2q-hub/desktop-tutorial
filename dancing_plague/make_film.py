#!/usr/bin/env python3
"""End-to-end build: timeline → preview stills → parallel frame render → soundtrack → mux → QC.

  python make_film.py plan                 # print the timeline
  python make_film.py preview [t t t ...]  # render QA stills to build/preview
  python make_film.py audio                # soundtrack only
  python make_film.py render [--workers N] # full film → output/*.mp4 (+ QC report)
  python make_film.py check                # re-run QC on the existing output
"""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing as mp
import concurrent.futures as cf
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine import timeline as TL  # noqa: E402
from engine.render import FFMPEG, render_range, render_preview, BUILD  # noqa: E402
from engine.common import FPS  # noqa: E402
from engine import mix as MIX  # noqa: E402
from engine import check as CHECK  # noqa: E402

OUT_DIR = os.path.join(HERE, "output")
FINAL = os.path.join(OUT_DIR, "1518_dancing_plague_strasbourg.mp4")
FINAL_ASCII = FINAL


def plan():
    shots, total = TL.build_timeline(FFMPEG, FPS)
    print(TL.describe(shots, total))
    return shots, total


def do_preview(times):
    shots, total = TL.build_timeline(FFMPEG, FPS)
    if not times:
        times = []
        for s in shots:
            times += [s["start"] + 0.35 * s["dur"], s["start"] + 0.8 * s["dur"]]
    paths = render_preview(shots, total, times, os.path.join(BUILD, "preview"))
    for p in paths:
        print(p)


def do_audio():
    shots, total = TL.build_timeline(FFMPEG, FPS)
    os.makedirs(BUILD, exist_ok=True)
    wav = os.path.join(BUILD, "soundtrack.wav")
    t0 = time.time()
    MIX.build_soundtrack(shots, total, FFMPEG, wav)
    print(f"soundtrack: {wav}  ({time.time() - t0:.1f}s)")
    return wav, shots, total


def do_render(workers, chunk_seconds=None, reuse=False):
    shots, total = TL.build_timeline(FFMPEG, FPS)
    print(TL.describe(shots, total))
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    seg_dir = os.path.join(BUILD, "segments")
    if not reuse:
        shutil.rmtree(seg_dir, ignore_errors=True)
    os.makedirs(seg_dir, exist_ok=True)
    total_frames = int(round(total * FPS))
    # split at shot boundaries into ~equal work chunks (each chunk keeps whole GOPs; concat is lossless)
    n_chunks = max(workers * 3, 8)
    per = max(24, total_frames // n_chunks)
    ranges = []
    f = 0
    while f < total_frames:
        f1 = min(total_frames, f + per)
        ranges.append((f, f1, os.path.join(seg_dir, f"seg_{f:06d}.mp4"), shots, total))
        f = f1
    all_paths = [r[2] for r in ranges]
    if reuse:
        # keep segments that already exist and decode cleanly with the expected frame count
        keep = []
        for r in ranges:
            if os.path.exists(r[2]) and CHECK.count_frames(FFMPEG, r[2]) == r[1] - r[0]:
                keep.append(r[2])
        ranges = [r for r in ranges if r[2] not in keep]
        print(f"reusing {len(keep)} finished segments")
    print(f"rendering {sum(r[1] - r[0] for r in ranges)} frames in {len(ranges)} segments on {workers} workers")
    t0 = time.time()
    # audio in the main process while workers render frames
    wav = os.path.join(BUILD, "soundtrack.wav")
    # ProcessPoolExecutor raises BrokenProcessPool if a worker dies (e.g. OOM) instead of hanging forever
    with cf.ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as pool:
        futs = [pool.submit(render_range, r) for r in ranges]
        ta = time.time()
        if not (reuse and os.path.exists(wav)):
            MIX.build_soundtrack(shots, total, FFMPEG, wav)
            print(f"soundtrack done in {time.time() - ta:.1f}s", flush=True)
        for fu in futs:
            fu.result()
    seg_paths = all_paths
    print(f"frames rendered in {time.time() - t0:.1f}s")
    # concat + mux
    lst = os.path.join(seg_dir, "list.txt")
    with open(lst, "w") as fh:
        for p in sorted(seg_paths):
            fh.write(f"file '{p}'\n")
    video_only = os.path.join(BUILD, "video_only.mp4")
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video_only], check=True)
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", video_only, "-i", wav, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", FINAL], check=True)
    print(f"muxed → {FINAL}")
    return do_check(shots, total)


def do_check(shots=None, total=None):
    if shots is None:
        shots, total = TL.build_timeline(FFMPEG, FPS)
    rep = CHECK.main(FFMPEG, FINAL, shots, expect_dur=total, report_path=os.path.join(OUT_DIR, "qc_report.json"))
    print(json.dumps({k: v for k, v in rep.items() if k not in ("audio",)}, ensure_ascii=False, indent=2))
    print("QC PASSED" if rep["passed"] else "QC FAILED")
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "preview", "audio", "render", "check"])
    ap.add_argument("--reuse", action="store_true", help="keep already-rendered, complete segments")
    ap.add_argument("times", nargs="*", type=float)
    ap.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    a = ap.parse_args()
    if a.cmd == "plan":
        plan()
    elif a.cmd == "preview":
        do_preview(a.times)
    elif a.cmd == "audio":
        do_audio()
    elif a.cmd == "render":
        rep = do_render(a.workers, reuse=a.reuse)
        sys.exit(0 if rep["passed"] else 1)
    elif a.cmd == "check":
        rep = do_check()
        sys.exit(0 if rep["passed"] else 1)
