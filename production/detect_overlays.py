#!/usr/bin/env python3
"""Detect the drifting burned-in watermark on the source video.

Method: inside each burst we sample 4 frames spaced ~2.6s apart (the source
cuts on average every ~3.1s, so at least one shot boundary is crossed). For
every frame we compute max(tophat, blackhat) with a 9x9 kernel: translucent
overlay glyphs produce a strong thin-stroke response on ANY background. The
median of the four responses keeps only pixels that respond in every frame
(the static overlay) and drops changing film content. Connected components
become delogo boxes.
"""
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import cv2

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "work/source.mkv")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "work/overlays.json")
Y_MIN, Y_MAX = 54, 660
BURST_STEP = 12.0
BURST_FRAME_COUNT = 4
BURST_GAP = 2.6
DURATION = 2351.0


def frames_at(times: list[float]) -> list[np.ndarray]:
    out = []
    for t in times:
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            r = subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-ss", f"{t:.2f}", "-i", str(SRC), "-frames:v", "1",
                 "-vf", "format=gray", tmp.name],
                capture_output=True)
            if r.returncode:
                continue
            g = cv2.imread(tmp.name, cv2.IMREAD_GRAYSCALE)
            if g is not None and g.shape[:2] == (720, 1280):
                out.append(g)
    return out


def detect_burst(t0: float) -> list[dict]:
    frames = frames_at([t0 + i * BURST_GAP for i in range(BURST_FRAME_COUNT)])
    if len(frames) < 3:
        return []
    kern = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    resp = []
    for g in frames:
        gf = g.astype(np.float32)
        top = gf - cv2.morphologyEx(gf, cv2.MORPH_OPEN, kern)
        bot = cv2.morphologyEx(gf, cv2.MORPH_CLOSE, kern) - gf
        resp.append(np.maximum(top, bot))
    med = np.median(np.stack(resp), axis=0)
    mask = (med > 11).astype(np.uint8) * 255
    mask[:Y_MIN, :] = 0
    mask[Y_MAX:, :] = 0
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 5)))
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    boxes = []
    for k in range(1, n):
        x, y, w, h, area = stats[k]
        if not (60 <= w <= 360 and 16 <= h <= 64 and area >= 180):
            continue
        if area < w * h * 0.10:
            continue
        boxes.append({"x": int(x), "y": int(y), "w": int(w), "h": int(h), "area": int(area)})
    # merge overlapping/adjacent parts of the same watermark (text + companion icon)
    boxes.sort(key=lambda b: -b["area"])
    merged: list[dict] = []
    for b in boxes:
        hit = None
        for m in merged:
            if abs(b["x"] - m["x"]) < 170 and abs(b["y"] - m["y"]) < 70:
                hit = m; break
        if hit is None:
            merged.append(dict(b))
        else:
            x2 = max(hit["x"] + hit["w"], b["x"] + b["w"]); y2 = max(hit["y"] + hit["h"], b["y"] + b["h"])
            hit["x"] = min(hit["x"], b["x"]); hit["y"] = min(hit["y"], b["y"])
            hit["w"] = x2 - hit["x"]; hit["h"] = y2 - hit["y"]; hit["area"] += b["area"]
    return merged[:3]


def main():
    result = []
    t, idx = 6.0, 0
    while t < DURATION - BURST_GAP * BURST_FRAME_COUNT:
        for b in detect_burst(t):
            b["t0"] = round(t, 1)
            b["t1"] = round(t + BURST_GAP * (BURST_FRAME_COUNT - 1) + 1.2, 1)
            result.append(b)
        idx += 1
        if idx % 20 == 0:
            print(f"burst {idx} t={t:.0f}s total={len(result)}", flush=True)
        t += BURST_STEP
    Path(OUT).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print("WROTE", OUT, len(result), "boxes")

if __name__ == "__main__":
    main()
