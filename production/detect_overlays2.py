#!/usr/bin/env python3
"""Frame-accurate watermark + red name-tag tracker.

Emits motion-compensated delogo boxes per source clip (work/overlays2.json).
- Watermark: local-contrast template match at 5 fps inside each used clip.
- Name tags: saturated red banner blobs with white text at 2 fps, kept when
  position is stable for >=2 consecutive samples.
"""
import cv2
import json
import numpy as np
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "work" / "source.mkv"
FF = "ffmpeg"
W, H = 1280, 720
Y_MIN, Y_MAX = 54, 659
TMPL_PATH = Path("/tmp/wm_tmpl2.npy")


def build_template():
    if TMPL_PATH.exists():
        return np.load(TMPL_PATH)
    p = "/tmp/tmplsrc.png"
    subprocess.run([FF, "-v", "error", "-ss", "889.0", "-i", str(SRC),
                    "-frames:v", "1", "-vf", "format=gray", p], check=True)
    g = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    d = cv2.subtract(g, cv2.medianBlur(g, 21)).astype(np.float32)
    t = d[423:459, 1035:1190].copy()
    t -= t.mean()
    np.save(TMPL_PATH, t)
    return t


def grab_frames(t0, t1, fps, color=False):
    fmt = "yuv420p" if color else "gray"
    raw = subprocess.run(
        [FF, "-v", "error", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", str(SRC),
         "-vf", f"fps={fps},format={fmt}", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    step = 1.0 / fps
    fs = (W * H * 3 // 2) if color else (W * H)
    n = len(raw) // fs
    out = []
    for i in range(n):
        buf = np.frombuffer(raw[i * fs:(i + 1) * fs], np.uint8)
        out.append((t0 + i * step, buf))
    return out


def match_watermark(buf, tmpl, thr=0.42):
    g = buf.reshape(H, W)
    d = cv2.subtract(g, cv2.medianBlur(g, 21)).astype(np.float32)
    res = cv2.matchTemplate(d, tmpl, cv2.TM_CCOEFF_NORMED)
    res = np.nan_to_num(res)
    res[:Y_MIN, :] = 0
    if res.shape[0] > Y_MAX - tmpl.shape[0]:
        res[Y_MAX - tmpl.shape[0]:, :] = 0
    _, mx, _, loc = cv2.minMaxLoc(res)
    if mx < thr:
        return None
    return (int(loc[0]), int(loc[1]), tmpl.shape[1], tmpl.shape[0])


def red_blobs(buf):
    y = buf[:W * H].astype(np.int16).reshape(H, W)
    u = buf[W * H:W * H + W * H // 4].reshape(H // 2, W // 2).astype(np.int16)
    v = buf[W * H + W * H // 4:].reshape(H // 2, W // 2).astype(np.int16)
    u = cv2.resize(u, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.int16)
    v = cv2.resize(v, (W, H), interpolation=cv2.INTER_LINEAR).astype(np.int16)
    mask = ((v - 128 > 35) & (128 - u > 10) & (y > 50) & (y < 245)).astype(np.uint8)
    mask[:Y_MIN] = 0
    mask[Y_MAX:] = 0
    mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(mask)
    out = []
    for i in range(1, n):
        x, yy, w, h, ar = st[i]
        if 100 <= w <= 430 and 16 <= h <= 80 and ar / (w * h) > 0.40:
            sub_y = y[max(0, yy - 14):yy + h + 14, max(0, x - 14):x + w + 14]
            white_frac = float((sub_y > 190).mean())
            if white_frac > 0.04:  # banner region must carry white name text
                out.append((int(x), int(yy), int(w), int(h)))
    return out


def segments(samples, max_gap=26, pad=6):
    if not samples:
        return []
    segs, cur = [], [samples[0]]
    for s in samples[1:]:
        px, py = cur[-1][1][0], cur[-1][1][1]
        if abs(s[1][0] - px) > max_gap or abs(s[1][1] - py) > max_gap:
            segs.append(cur)
            cur = [s]
        else:
            cur.append(s)
    segs.append(cur)
    boxes = []
    for seg in segs:
        x0 = max(0, min(b[1][0] for b in seg) - pad)
        y0 = max(0, min(b[1][1] for b in seg) - pad)
        x1 = min(W, max(b[1][0] + b[1][2] for b in seg) + pad)
        y1 = min(H, max(b[1][1] + b[1][3] for b in seg) + pad)
        boxes.append((int(x0), int(y0), int(x1 - x0), int(y1 - y0),
                      seg[0][0] - 0.12, seg[-1][0] + 0.32))
    return boxes


def main():
    window = sys.argv[1] if len(sys.argv) > 1 else None
    narr = json.load(open(ROOT / "work/production/narration_aligned.json"))
    clips = sorted({(round(c["clips"][0][0], 2), round(c["clips"][0][1], 2))
                    for s in narr for c in s["cues"]})
    if window:
        lo, hi = map(float, window.split(":"))
        clips = [cb for cb in clips if cb[1] > lo and cb[0] < hi]
    tmpl = build_template()
    boxes, stats = [], {"wm_frames": 0, "wm_hits": 0, "tags": 0}
    for i, (a, b) in enumerate(clips):
        wm = []
        for t, buf in grab_frames(a, b, 5):
            stats["wm_frames"] += 1
            m = match_watermark(buf, tmpl)
            if m:
                stats["wm_hits"] += 1
                wm.append((t, m))
        for s in segments(wm):
            boxes.append(dict(x=s[0], y=s[1], w=s[2], h=s[3],
                              t0=round(s[4], 2), t1=round(s[5], 2)))
        tag_hits = {}
        for t, buf in grab_frames(a, b, 4, color=True):
            for bl in red_blobs(buf):
                tag_hits.setdefault((bl[0] // 50, bl[1] // 50), []).append((t, bl))
        for lst in tag_hits.values():
            if len(lst) < 2:
                continue
            stats["tags"] += 1
            for s in segments([(t, (b0 - 14, b1 - 12, b2 + 28, b3 + 24))
                               for t, (b0, b1, b2, b3) in lst], max_gap=16, pad=4):
                boxes.append(dict(x=s[0], y=s[1], w=s[2], h=s[3],
                                  t0=round(s[4], 2), t1=round(s[5], 2), tag=True))
        print(f"clip {i+1}/{len(clips)} [{a},{b}]: wm {len(wm)}/{stats['wm_frames']} tag "
              f"{len(tag_hits)}", flush=True)
    outp = ROOT / "work/overlays2.json" if not window else ROOT / f"work/overlays2_probe.json"
    json.dump(boxes, open(outp, "w"), ensure_ascii=False)
    print("boxes:", len(boxes), "stats:", stats, "->", outp)


if __name__ == "__main__":
    main()
