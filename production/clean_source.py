#!/usr/bin/env python3
"""画面清理：把每个用到的片段裁到"干净带"（去掉源片顶部标题/底部字幕），
并用 cv2.inpaint 按 overlays.json 坐标平滑去除水印与红色人名条。
输出：<ROOT>/work/clean/clip_NNN.mp4（仅视频，1280x588@30fps，CRF12 近无损）。
"""
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "work" / "source.mkv"
OV = json.load(open(ROOT / "production" / "overlays.json", encoding="utf-8"))
NARR = json.load(open(ROOT / "work" / "production" / "narration_aligned.json", encoding="utf-8"))
FF = "/usr/local/bin/ffmpeg"
BAND_TOP, BAND_H, W = 68, 588, 1280


def collect_clips():
    clips, gi = [], 0
    for s in NARR:
        for c in s["cues"]:
            clips.append((float(c["clips"][0][0]), float(c["clips"][0][1]), gi))
            gi += 1
    return clips


def boxes_for(sin, sout):
    lo, hi = sin - 1.5, sout + 1.5
    bs = []
    for b in OV:
        if b["t0"] - 1.0 <= hi and b["t1"] + 1.0 >= lo:
            y, h = b["y"], b["h"]
            if y + h <= BAND_TOP + 1 or y >= BAND_TOP + BAND_H - 1:
                continue
            bs.append([b["x"], y, b["w"], h])
    return bs


def merge_boxes(bs, pad=4, maxgap=22):
    if not bs:
        return []
    rects = [[x - pad, y - pad, w + 2 * pad, h + 2 * pad] for x, y, w, h in bs]
    rects.sort(key=lambda r: (r[1], r[0]))
    merged = []
    for x, y, w, h in rects:
        x2, y2 = x + w, y + h
        placed = False
        for m in merged:
            mx, my, mw, mh = m
            mx2, my2 = mx + mw, my + mh
            if x < mx2 + maxgap and mx < x2 + maxgap and y < my2 + maxgap and my < y2 + maxgap:
                m[0], m[1] = min(mx, x), min(my, y)
                m[2], m[3] = max(mx2, x2) - m[0], max(my2, y2) - m[1]
                placed = True
                break
        if not placed:
            merged.append([x, y, w, h])
    out = []
    for x, y, w, h in merged:
        x = max(0, x)
        y = max(BAND_TOP, y)
        x2 = min(W, x + w)
        y2 = min(BAND_TOP + BAND_H, y + h)
        if x2 - x >= 6 and y2 - y >= 6:
            out.append((x, y, x2, y2))
    return out


def main():
    outdir = ROOT / "work" / "clean"
    outdir.mkdir(parents=True, exist_ok=True)
    for sin, sout, gi in collect_clips():
        out = outdir / f"clip_{gi:03d}.mp4"
        if out.exists() and out.stat().st_size > 2000:
            continue
        rects = merge_boxes(boxes_for(sin, sout))
        mask = np.zeros((BAND_H, W), np.uint8)
        for x, y, x2, y2 in rects:
            mask[y - BAND_TOP:y2 - BAND_TOP, x:x2] = 255
        has = mask.sum() > 0
        dec = subprocess.Popen(
            [FF, "-v", "error", "-ss", f"{sin:.3f}", "-to", f"{sout:.3f}", "-i", str(SRC),
             "-vf", f"crop={W}:{BAND_H}:0:{BAND_TOP}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
            stdout=subprocess.PIPE)
        enc = subprocess.Popen(
            [FF, "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
             "-s", f"{W}x{BAND_H}", "-r", "30", "-i", "-",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
             "-pix_fmt", "yuv420p", "-an", str(out)],
            stdin=subprocess.PIPE)
        n = 0
        while True:
            raw = dec.stdout.read(W * BAND_H * 3)
            if not raw:
                break
            frame = np.frombuffer(raw, np.uint8).reshape(BAND_H, W, 3).copy()
            if has:
                for x, y, x2, y2 in rects:
                    y0, y1 = y - BAND_TOP, y2 - BAND_TOP
                    m = 6
                    x0, x1 = max(0, x - m), min(W, x2 + m)
                    yy0, yy1 = max(0, y0 - m), min(BAND_H, y1 + m)
                    frame[yy0:yy1, x0:x1] = cv2.inpaint(
                        frame[yy0:yy1, x0:x1], mask[yy0:yy1, x0:x1], 3, cv2.INPAINT_TELEA)
            enc.stdin.write(frame.tobytes())
            n += 1
        enc.stdin.close()
        enc.wait()
        dec.wait()
        print(f"clip {gi:03d}: {sin:.2f}-{sout:.2f} frames={n} rects={len(rects)}", flush=True)
    print("ALL CLEAN CLIPS DONE")


if __name__ == "__main__":
    main()
