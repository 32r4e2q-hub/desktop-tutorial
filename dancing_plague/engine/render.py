"""Frame renderer: per-shot scene → post (grade, bloom, grain, vignette) → letterbox → captions/subtitles → ffmpeg."""
from __future__ import annotations

import math
import os
import subprocess
import sys
import time
import numpy as np
import cv2
import imageio_ffmpeg

from .common import W, H, AH, BAR, FPS, CX, apply_grade, bloom, grain, vignette_mask, smoothstep, clamp01
from .text import draw_text, draw_subtitle
from . import timeline as TL

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = TL.ROOT
BUILD = os.path.join(ROOT, "build")
XFADE = 0.5  # seconds of dissolve between consecutive shots (hard cut for a few)
HARD_CUTS = {("S2", "S3"), ("S9", "S10")}


def post_process(canvas, fbuf, grade, rng, t_local, dur):
    f = canvas.astype(np.float32) / 255.0
    f += fbuf  # additive light
    f = bloom(f, threshold=0.62, amount=grade.get("bloom", 0.35))
    f = apply_grade(f, lift=grade.get("lift", (0, 0, 0)), gain=grade.get("gain", (1, 1, 1)), gamma=grade.get("gamma", 1.0), sat=grade.get("sat", 1.0))
    f *= vignette_mask(grade.get("vignette", 0.55))
    f = grain(f, grade.get("grain", 0.035), rng)
    return np.clip(f * 255.0, 0, 255).astype(np.uint8)


def compose_frame(shots, scene_objs, global_t, rng):
    """Return a full HxW frame for global time (handles cross-dissolves between shots)."""
    # find current shot
    idx = 0
    for i, s in enumerate(shots):
        if global_t >= s["start"]:
            idx = i
    s = shots[idx]
    t_local = global_t - s["start"]
    img, caps = render_shot(s, scene_objs, t_local, rng)
    # dissolve into the next shot near the end
    if idx + 1 < len(shots):
        nxt = shots[idx + 1]
        pair = (s["name"], nxt["name"])
        if pair not in HARD_CUTS:
            remain = s["dur"] - t_local
            if remain < XFADE:
                a = 1 - remain / XFADE
                img2, caps2 = render_shot(nxt, scene_objs, -remain, rng)  # negative local time = pre-roll (clamped inside)
                img = cv2.addWeighted(img, 1 - a, img2, a, 0)
                caps = [(k, txt, op * (1 - a)) for (k, txt, op) in caps] + [(k, txt, op * a) for (k, txt, op) in caps2]
    frame = np.zeros((H, W, 3), np.uint8)
    frame[BAR:BAR + AH] = img
    # captions (inside picture, lower-left) and counters (upper-right)
    for kind, txt, op in caps:
        if op <= 0.01:
            continue
        if kind == "caption":
            draw_text(frame, txt, 64, BAR + AH - 44, size=24, serif=True, color=(236, 228, 210), opacity=op, anchor="left", stroke=2, stroke_color=(20, 14, 12), spacing=2)
            # small rule
            x0, x1 = 64, 64 + int(140 * op)
            cv2.line(frame, (x0, BAR + AH - 26), (x1, BAR + AH - 26), (200, 190, 170), 1, cv2.LINE_AA)
        elif kind == "counter":
            draw_text(frame, txt, W - 64, BAR + 44, size=26, serif=False, color=(232, 222, 200), opacity=op, anchor="right", stroke=1, stroke_color=(0, 0, 0), spacing=3)
    # subtitle: narration text of the current shot (split into 2 parts by length)
    if s["vo"]:
        vo_t = t_local - s["lead"]
        if 0 <= vo_t <= s["vo_dur"] + 0.4:
            parts = split_subtitle(s["text"])
            total_chars = sum(len(p) for p in parts)
            acc = 0.0
            for p in parts:
                share = len(p) / total_chars * s["vo_dur"]
                if acc <= vo_t < acc + share + (0.4 if p is parts[-1] else 0.0):
                    draw_subtitle(frame, p, vo_t - acc, share + (0.4 if p is parts[-1] else 0.0), size=27)
                    break
                acc += share
    return frame


def split_subtitle(text, max_len=24):
    """Split at sentence punctuation so each subtitle is ≤ ~24 chars."""
    seps = "。！？；"
    soft = "，、：—"
    parts, cur = [], ""
    for ch in text:
        cur += ch
        if ch in seps and len(cur) >= 6:
            parts.append(cur)
            cur = ""
    if cur:
        parts.append(cur)
    # further split long parts at soft punctuation
    out = []
    for p in parts:
        while len(p) > max_len:
            cut = -1
            for i in range(min(len(p) - 1, max_len), 5, -1):
                if p[i] in soft:
                    cut = i
                    break
            if cut < 0:
                cut = max_len
            out.append(p[:cut + 1])
            p = p[cut + 1:]
        if p:
            out.append(p)
    return out


def render_shot(s, scene_objs, t_local, rng):
    scene = scene_objs[s["name"]]
    t = max(0.0, min(t_local, s["dur"] - 1.0 / FPS)) if t_local >= 0 else 0.0
    canvas, fbuf, caps = scene.render(t)
    img = post_process(canvas, fbuf, scene.grade, rng, t, s["dur"])
    # fade from black at very start / to black at very end of film handled by caller via timeline position
    return img, caps


def render_range(args):
    """Worker: render frames [f0, f1) into an h264 segment."""
    f0, f1, seg_path, shots, total = args
    scene_objs = {s["name"]: s["cls"](s["dur"], seed=i + 1) for i, s in enumerate(shots)}
    rng = np.random.default_rng(1000 + f0)
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-g", "48", "-an", seg_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t_start = time.time()
    for fi in range(f0, f1):
        gt = fi / FPS
        frame = compose_frame(shots, scene_objs, gt, rng)
        # global fade in / out
        fade = min(1.0, gt / 1.5) * min(1.0, max(0.0, (total - gt) / 1.5))
        if fade < 1.0:
            frame = (frame.astype(np.float32) * fade).astype(np.uint8)
        proc.stdin.write(np.ascontiguousarray(frame[:, :, ::-1]).tobytes())  # RGB → BGR for ffmpeg bgr24
        if (fi - f0) % 48 == 0:
            el = time.time() - t_start
            done = fi - f0 + 1
            print(f"[seg {f0:5d}] {done:4d}/{f1 - f0} frames  {el:6.1f}s  ({done / max(el, 1e-6):.2f} fps)", flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg segment failed: {seg_path}")
    return seg_path


def render_preview(shots, total, times, out_dir):
    """Render a handful of still frames for visual QA."""
    os.makedirs(out_dir, exist_ok=True)
    scene_objs = {s["name"]: s["cls"](s["dur"], seed=i + 1) for i, s in enumerate(shots)}
    rng = np.random.default_rng(7)
    paths = []
    for gt in times:
        frame = compose_frame(shots, scene_objs, gt, rng)
        p = os.path.join(out_dir, f"t{gt:07.2f}.jpg")
        cv2.imwrite(p, frame[:, :, ::-1], [cv2.IMWRITE_JPEG_QUALITY, 90])
        paths.append(p)
    return paths
