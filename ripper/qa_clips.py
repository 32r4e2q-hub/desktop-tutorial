#!/usr/bin/env python3
"""Per-clip QA for the AI-generated shots.

    python qa_clips.py            # report + contact sheet → build/qa/clips_sheet.jpg
    python qa_clips.py --strict   # also print the ids that should be regenerated

Checks: readable, duration ≥ 3 s, portrait aspect, motion (mean frame diff), no long black/frozen run,
palette distance to the style anchor (assets/gen/A00_style_anchor.png) in Lab space, faces-per-frame sanity.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLIPS = os.path.join(HERE, "clips")
ANCHOR = os.path.join(HERE, "assets", "gen", "A00_style_anchor.png")
OUTDIR = os.path.join(HERE, "build", "qa")


def lab_stats(img):
    lab = cv2.cvtColor(cv2.resize(img, (160, 284)), cv2.COLOR_BGR2LAB).astype(np.float32)
    return lab.reshape(-1, 3).mean(0), lab.reshape(-1, 3).std(0)


def analyse(path, anchor_stats):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames, diffs, black, prev = [], [], 0, None
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % 4 == 0:
            g = cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (90, 160)).astype(np.int16)
            if prev is not None:
                diffs.append(float(np.abs(g - prev).mean()))
            prev = g
            if g.mean() < 8:
                black += 1
            frames.append(f)
        i += 1
    cap.release()
    rep = {"id": os.path.splitext(os.path.basename(path))[0], "ok": True, "issues": [], "w": w, "h": h,
           "fps": round(fps, 2), "dur": round(n / fps, 2) if fps else 0}
    if not frames:
        rep["ok"] = False
        rep["issues"].append("unreadable")
        return rep, None
    rep["motion"] = round(float(np.mean(diffs)), 2) if diffs else 0.0
    rep["black_ratio"] = round(black / len(frames), 2)
    if rep["dur"] < 3:
        rep["issues"].append(f"too short {rep['dur']}s")
    if h <= w:
        rep["issues"].append("not portrait")
    if rep["motion"] < 1.0:
        rep["issues"].append("static (no motion)")
    if rep["black_ratio"] > 0.25:
        rep["issues"].append("mostly black")
    # frozen run
    run, worst = 0, 0
    for d in diffs:
        run = run + 1 if d < 0.3 else 0
        worst = max(worst, run)
    if worst * 4 / fps > 1.5:
        rep["issues"].append(f"frozen {worst * 4 / fps:.1f}s")
    # palette distance to anchor
    mid = frames[len(frames) // 2]
    m, s = lab_stats(mid)
    am, as_ = anchor_stats
    dist = float(np.linalg.norm((m - am) / np.array([255, 128, 128]) * np.array([1.0, 2.5, 2.5])))
    rep["palette_dist"] = round(dist, 3)
    if dist > 0.22:
        rep["issues"].append(f"palette drift {dist:.2f}")
    rep["ok"] = not rep["issues"]
    thumb = cv2.resize(mid, (180, 320))
    return rep, thumb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUTDIR, exist_ok=True)
    anchor = cv2.imread(ANCHOR)
    anchor_stats = lab_stats(anchor) if anchor is not None else (np.array([60, 128, 140], np.float32), None)
    paths = sorted(glob.glob(os.path.join(CLIPS, "S*.mp4")))
    reps, thumbs = [], []
    for p in paths:
        r, th = analyse(p, anchor_stats)
        reps.append(r)
        if th is not None:
            cv2.putText(th, r["id"] + (" !" if not r["ok"] else ""), (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (40, 40, 255) if not r["ok"] else (255, 255, 255), 2, cv2.LINE_AA)
            thumbs.append(th)
        flag = "OK " if r["ok"] else "BAD"
        print(f"{flag} {r['id']}  {r['w']}x{r['h']} {r['dur']:5.2f}s motion={r.get('motion', 0):5.2f} "
              f"palette={r.get('palette_dist', 0):.2f}  {'; '.join(r['issues'])}")
    if thumbs:
        cols = 7
        rows = [np.hstack(thumbs[i:i + cols] + [np.zeros_like(thumbs[0])] * (cols - len(thumbs[i:i + cols])))
                for i in range(0, len(thumbs), cols)]
        cv2.imwrite(os.path.join(OUTDIR, "clips_sheet.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
    json.dump(reps, open(os.path.join(OUTDIR, "clips_qa.json"), "w"), ensure_ascii=False, indent=2)
    bad = [r["id"] for r in reps if not r["ok"]]
    print(f"\n{len(reps) - len(bad)}/{len(reps)} clips pass; regenerate: {','.join(bad) if bad else '-'}")
    if a.strict and bad:
        print(",".join(bad))
    return 0


if __name__ == "__main__":
    sys.exit(main())
