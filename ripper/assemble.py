#!/usr/bin/env python3
"""Assemble the vertical (1080x1920) short from AI-generated clips + VO + subtitles + soundtrack.

    python assemble.py plan                 # timeline from shots.json + VO durations + available clips
    python assemble.py render [--workers 2] # → output/ripper_whitechapel_fog_1080x1920.mp4 (+ QC report)
    python assemble.py check                # QC only

Pipeline per frame (all numpy/OpenCV, deterministic):
  clip frame (time-remapped so every shot exactly fills its narration slot, with a slow settle when the
  clip is shorter) → 1080x1920 letter-free fit (cover) → uniform painterly post (gentle canvas grain,
  warm-cool split tone, vignette, rolling fog veil, film gate weave) → dissolve/dip-to-black between shots →
  titles (S02/S28) → Chinese subtitles (bottom safe zone for Douyin UI).
Audio: VO per narration block + synthesized bed (fog horn drone, wind, drips, hooves, heartbeat, piano motif).
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import glob
import json
import math
import multiprocessing as mp
import os
import shutil
import subprocess
import sys
import time

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
import imageio_ffmpeg  # noqa: E402

from engine.text import render_text  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 24
# Grade native 720p source pictures before upscaling; titles/subtitles stay native 1080p.
RW, RH = 720, 1280
cv2.setNumThreads(1)
CLIPS = os.path.join(HERE, "clips")
VO = os.path.join(HERE, "audio", "vo")
BUILD = os.path.join(HERE, "build")
OUT = os.path.join(HERE, "output")
FINAL = os.path.join(OUT, "ripper_whitechapel_fog_1080x1920.mp4")
SHOTS = json.load(open(os.path.join(HERE, "shots.json"), encoding="utf-8"))

# --------------------------------------------------------------------------- narration → subtitles
NARRATION = {
    "N01": ["1888年秋天，伦敦东区，白教堂。", "十一周之内，五个女人在夜里遇害。", "凶手写信嘲笑警察，还给自己起了个名字。", "一百多年过去了，没有人知道，他到底是谁。"],
    "N02": ["8月31日凌晨三点四十分。", "马车夫查尔斯·克罗斯走过巴克斯街，", "看见墙边躺着一个人。", "他以为是醉倒的女人，凑近才发现——", "她叫玛丽·安·尼科尔斯，四十三岁。", "这是第一个。"],
    "N03": ["八天后，汉伯里街29号的后院，第二个。", "警督弗雷德里克·阿伯莱恩赶到时，", "围观的人已经挤满了巷子。", "凶手下手极快，没有人听见任何声音。"],
    "N04": ["9月27日，中央新闻社收到一封红墨水写的信。", "信里嘲笑警察，预告下一次动手。", "落款是一个从未有人见过的名字：", "Jack the Ripper，开膛手杰克。", "这个名字，第二天登上了所有报纸。"],
    "N05": ["9月30日，一夜之间两起。", "伯纳街，一位小贩的马突然惊立不前；", "四十五分钟后，一英里外的主教广场，", "巡警的灯光照见了第四个。", "凶手在两地之间，穿过了整个警戒区。"],
    "N06": ["就在那晚，古尔斯顿街的门洞里出现一行粉笔字，", "旁边是一块染了血的围裙碎片。", "警察总监沃伦亲自下令：天亮之前，擦掉。", "这是全案唯一可能由凶手留下的文字，", "就这样消失了。"],
    "N07": ["11月9日，米勒庭院13号。", "房东的助手来收房租，敲门没人应，", "他从窗帘缝往里看了一眼。", "那一眼，成了整个案件最不可言说的部分。", "此后，杰克再没有出现。"],
    "N08": ["一百多年来，嫌疑人名单越拉越长：", "波兰理发师科斯明斯基、律师德鲁伊特、", "医生塔姆布蒂、画家西克特，甚至王室成员。", "每一个都有证据，每一个都不够。"],
    "N09": ["2014年，有人用一条据称来自现场的披肩", "做DNA检测，指向科斯明斯基。", "但披肩来历不明，检测方法也遭到质疑。", "答案似乎近在眼前，又再一次滑走。"],
    "N10": ["白教堂的雾早就散了。", "可只要那五个名字还被人提起，", "那个没有脸的男人，", "就还站在灯光照不到的地方。", "他是谁？评论区，说出你的推理。"],
}
TITLE_AT = "S02"      # main title card overlays this shot
END_AT = "S28"        # closing question overlays this shot
RENDER_VERSION = "v4.1-resumed-20260906"  # bump whenever the per-frame pixel pipeline changes (invalidates the segment cache)
PRE_ROLL = 0.7        # seconds of picture before the first narration word of a block
POST_ROLL = 0.5

# --------------------------------------------------------------------------- probing helpers

def probe_duration(path):
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", path, "-f", "null", "-"], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Cannot decode {path}: {r.stderr[-1200:]}")
    m = None
    for line in r.stderr.splitlines():
        if "time=" in line:
            m = line.rsplit("time=", 1)[1].split()[0]
    if not m:
        raise RuntimeError(f"No decoded duration for {path}")
    h, mi, s = m.split(":")
    return int(h) * 3600 + int(mi) * 60 + float(s)


def clip_frames(path):
    cap = cv2.VideoCapture(path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    cap.release()
    return n, fps


# --------------------------------------------------------------------------- timeline

def build_timeline():
    """Return list of shot dicts with start/dur, and total duration.

    Narration block k spans its shots; the block's duration = max(VO + rolls, sum of clip natural lengths).
    Inside the block, time is shared between shots proportionally to their planned seconds.
    """
    shots = [dict(s) for s in SHOTS["shots"]]
    available = {}
    for s in shots:
        p = os.path.join(CLIPS, f"{s['id']}.mp4")
        if os.path.exists(p) and os.path.getsize(p) > 1024:
            n, fps = clip_frames(p)
            available[s["id"]] = (p, n / fps if fps else 0.0, n, fps)
    missing = [s["id"] for s in shots if s["id"] not in available or available[s["id"]][1] <= 0]
    if missing:
        raise RuntimeError(f"Missing/invalid clips: {missing}; run recover_assets.py first")
    vo_dur = {k: probe_duration(os.path.join(VO, f"{k}.mp3")) for k in NARRATION}

    blocks = []
    for s in shots:
        if not blocks or blocks[-1]["vo"] != s["vo"]:
            blocks.append({"vo": s["vo"], "shots": []})
        blocks[-1]["shots"].append(s)

    t = 0.0
    timeline = []
    live_blocks = []
    for b in blocks:
        vo = b["vo"]
        live = [s for s in b["shots"] if s["id"] in available]
        if not live:
            continue
        live_blocks.append(b)
        planned = sum(s.get("seconds", 7) for s in live)
        block_dur = max(vo_dur[vo] + PRE_ROLL + POST_ROLL, planned * 0.8)
        b["start"] = t
        b["dur"] = block_dur
        b["vo_dur"] = vo_dur[vo]
        for s in live:
            share = s.get("seconds", 7) / planned
            d = block_dur * share
            p, nat, n, fps = available[s["id"]]
            off = 0
            if s.get("use"):
                u0, u1 = float(s["use"][0]), float(s["use"][1])
                u0 = max(0.0, min(u0, nat - 0.5))
                u1 = max(u0 + 0.5, min(u1, nat))
                off = int(round(u0 * fps))
                nat = u1 - u0
            timeline.append({"id": s["id"], "vo": vo, "path": p, "start": t, "dur": d, "natural": nat, "frames": n,
                             "fps": fps, "offset": off, "crop": s.get("crop"), "block_start": b["start"], "block_dur": block_dur})
            t += d
    return timeline, live_blocks, t, vo_dur


# --------------------------------------------------------------------------- per-frame rendering

class ClipReader:
    """Sequential-friendly random access reader with a small sliding cache (memory-bounded).

    Frames are decoded on demand; the cache keeps the most recent ~64 frames of the current clip,
    which covers the interpolation neighbour and the ping-pong reversal without holding the whole
    clip (a 9 s Agnes clip at 720 px would be ~600 MB per worker otherwise).
    """

    CACHE = 64

    def __init__(self):
        self.path = None
        self.cap = None
        self.n = 0
        self.pos = 0            # index of the next frame the capture will return
        self.cache = {}         # idx → frame
        self.order = []

    def _open(self, path):
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(path)
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.pos = 0
        self.cache, self.order = {}, []
        self.path = path

    def _decode_next(self):
        ok, f = self.cap.read()
        if not ok:
            return None
        if f.shape[1] > 720:
            f = cv2.resize(f, (720, int(round(f.shape[0] * 720 / f.shape[1]))), interpolation=cv2.INTER_AREA)
        idx = self.pos
        self.pos += 1
        self.cache[idx] = f
        self.order.append(idx)
        if len(self.order) > self.CACHE:
            old = self.order.pop(0)
            self.cache.pop(old, None)
        return f

    def get(self, path, idx):
        if path != self.path:
            self._open(path)
        if self.n <= 0:
            return np.zeros((H, W, 3), np.uint8)
        idx = int(max(0, min(self.n - 1, idx)))
        f = self.cache.get(idx)
        if f is not None:
            return f
        if idx < self.pos or idx > self.pos + self.CACHE:
            # backwards jump (ping-pong) or far seek: reposition a little before the target
            start = max(0, idx - 8)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, start)
            self.pos = start
        while self.pos <= idx:
            f = self._decode_next()
            if f is None:
                break
        f = self.cache.get(idx)
        if f is None:                       # decode failed at the tail: use the last frame we have
            if self.order:
                return self.cache[self.order[-1]]
            return np.zeros((H, W, 3), np.uint8)
        return f


def fit_cover(img, zoom=1.0, cx=0.5, cy=0.5):
    h, w = img.shape[:2]
    s = max(RW / w, RH / h) * zoom
    nw, nh = int(round(w * s)), int(round(h * s))
    r = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_CUBIC if s > 1 else cv2.INTER_AREA)
    x0 = int(round((nw - RW) * cx))
    y0 = int(round((nh - RH) * cy))
    x0 = max(0, min(max(0, nw - RW), x0))
    y0 = max(0, min(max(0, nh - RH), y0))
    out = r[y0:y0 + RH, x0:x0 + RW]
    if out.shape[0] != RH or out.shape[1] != RW:
        out = cv2.resize(out, (RW, RH), interpolation=cv2.INTER_LINEAR)
    return np.ascontiguousarray(out)


_canvas_tex = None
_vignette = None


def canvas_texture(rng):
    global _canvas_tex
    if _canvas_tex is None:
        n = rng.standard_normal((RH // 2, RW // 2)).astype(np.float32)
        n = cv2.GaussianBlur(n, (0, 0), 0.8)
        weave = (np.sin(np.arange(RH // 2)[:, None] * 1.7) * np.sin(np.arange(RW // 2)[None, :] * 1.7)).astype(np.float32)
        tex = cv2.resize(n * 0.8 + weave * 0.25, (RW, RH), interpolation=cv2.INTER_LINEAR)
        _canvas_tex = tex / (np.abs(tex).max() + 1e-6)
    return _canvas_tex


def vignette():
    global _vignette
    if _vignette is None:
        yy, xx = np.mgrid[0:RH, 0:RW].astype(np.float32)
        d = np.sqrt(((xx - RW / 2) / (RW / 2)) ** 2 + ((yy - RH / 2) / (RH / 2)) ** 2)
        _vignette = np.clip(1.0 - 0.45 * np.clip(d - 0.6, 0, 1) ** 1.8, 0, 1)[..., None]
    return _vignette


_veil_cache = {}


def fog_veil(t, seed):
    """Slow rolling low-frequency fog multiplier field (adds unity to clips from different generations)."""
    key = (round(t * 8) / 8, seed)
    if key in _veil_cache:
        return _veil_cache[key]
    rng = np.random.default_rng(seed)
    small = np.zeros((24, 14), np.float32)
    for o, amp in ((1, 1.0), (2, 0.5), (4, 0.25)):
        ph = rng.random((3, 2)) * 6.28
        y = np.linspace(0, o * 2.2, 24)[:, None]
        x = np.linspace(0, o * 1.3, 14)[None, :]
        small += amp * (np.sin(y + t * 0.07 * o + ph[0, 0]) * np.cos(x - t * 0.05 * o + ph[0, 1]))
    field = cv2.resize(small, (RW, RH), interpolation=cv2.INTER_CUBIC)
    out = (field - field.min()) / (field.max() - field.min() + 1e-6)
    if len(_veil_cache) > 8:
        _veil_cache.pop(next(iter(_veil_cache)))
    _veil_cache[key] = out
    return out


def painterly(frame_bgr):
    """Flatten photo-like micro detail into brush-like patches and darken edges (oil-sketch look)."""
    small = cv2.resize(frame_bgr, (RW // 3, RH // 3), interpolation=cv2.INTER_AREA)
    sm = cv2.bilateralFilter(small, 7, 45, 5)
    # keep some of the original mid-frequency detail so faces stay crisp (unsharp on the smoothed layer)
    up = cv2.resize(sm, (RW, RH), interpolation=cv2.INTER_LINEAR)
    mixed = cv2.addWeighted(up, 0.7, frame_bgr, 0.3, 0).astype(np.float32)
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Laplacian(g, cv2.CV_32F, ksize=3)
    edges = np.clip(np.abs(edges) / 48.0, 0, 1)
    edges = cv2.resize(edges, (RW, RH), interpolation=cv2.INTER_LINEAR)[..., None]
    return mixed * (1 - 0.28 * edges)


def post(frame_bgr, t, rng, fog_strength=0.10, grain_amt=0.035):
    f = painterly(frame_bgr) / 255.0
    # split tone: cool shadows (slate blue) / warm highlights (gaslight amber)
    lum = f.mean(axis=2, keepdims=True)
    shadow = np.array([0.10, 0.05, -0.03], np.float32)  # BGR: +blue, -red  (slate-blue shadows)
    high = np.array([-0.05, 0.02, 0.08], np.float32)    # gaslight-amber highlights
    f = f + shadow * (1 - lum) * 0.5 + high * lum * 0.5
    # global desaturation toward the umber/sepia palette
    grey = f.mean(axis=2, keepdims=True)
    f = grey + (f - grey) * 0.78
    f = f * np.array([0.93, 0.97, 1.03], np.float32)     # warm bias
    # exposure: lift very dark clips toward a common key, then a soft S-curve with lifted blacks
    f = np.clip(f, 0, 1)
    key = float(lum.mean())
    gain = float(np.clip(0.34 / max(key, 1e-3), 1.0, 2.2))
    f = 1.0 - (1.0 - f) ** gain              # screen-like lift: brightens shadows, keeps highlights
    f = 0.045 + 0.955 * ((f * f * (3 - 2 * f)) * 0.55 + f * 0.45)
    # rolling fog veil
    veil = fog_veil(t, 7)[..., None]
    fogcol = np.array([0.62, 0.66, 0.70], np.float32)
    f = f * (1 - fog_strength * veil) + fogcol * fog_strength * veil * 0.9
    # canvas grain (static weave + animated fine grain)
    tex = canvas_texture(rng)
    live = cv2.resize(np.random.default_rng(int(t * FPS) + 11).standard_normal((RH // 4, RW // 4)).astype(np.float32), (RW, RH), interpolation=cv2.INTER_LINEAR)
    f = f + (tex * 0.6 + live * 0.4)[..., None] * grain_amt * (0.6 + 0.4 * (1 - lum))
    # vignette
    f = f * (0.45 + 0.55 * vignette())
    return np.clip(f * 255.0 + 0.5, 0, 255).astype(np.uint8)


def gate_weave(t, seed):
    r = np.random.default_rng(seed)
    dx = 1.2 * math.sin(t * 0.9 + r.random() * 6) + 0.6 * math.sin(t * 3.1 + r.random() * 6)
    dy = 1.0 * math.sin(t * 0.7 + r.random() * 6)
    return dx, dy


def draw_text_center(canvas, text, cy, size, serif=True, color=(236, 226, 206), opacity=1.0, spacing=0, stroke=0,
                     stroke_color=(0, 0, 0), x=None):
    if opacity <= 0.002:
        return
    rgb, alpha = render_text(text, size, serif, color, stroke, stroke_color, spacing)
    h, w = alpha.shape
    cx = W / 2 if x is None else x
    x0 = int(round(cx - w / 2))
    y0 = int(round(cy - h / 2))
    xs, ys = max(0, x0), max(0, y0)
    xe, ye = min(W, x0 + w), min(H, y0 + h)
    if xe <= xs or ye <= ys:
        return
    a = alpha[ys - y0:ye - y0, xs - x0:xe - x0][..., None] * opacity
    src = rgb[ys - y0:ye - y0, xs - x0:xe - x0][..., ::-1]  # rgb→bgr
    # soft shadow
    sh = cv2.GaussianBlur(alpha, (0, 0), 4)[ys - y0:ye - y0, xs - x0:xe - x0][..., None] * opacity * 0.8
    reg = canvas[ys:ye, xs:xe].astype(np.float32)
    reg = reg * (1 - sh)
    reg = reg * (1 - a) + src.astype(np.float32) * a
    canvas[ys:ye, xs:xe] = reg.astype(np.uint8)


@lru_cache(maxsize=128)
def subtitle_size(line):
    for size in range(46, 29, -1):
        rgb, _ = render_text(line, size, False, (245, 240, 230), 3, (10, 8, 6))
        if rgb.shape[1] <= int(W * 0.84):
            return size
    raise ValueError(f"Subtitle too wide: {line}")


_SUB_BOUNDS = None


def _load_sub_bounds():
    """Subtitle line boundaries measured from the narration audio (build/subtitle_bounds.json);
    falls back to proportional character timing when the file is missing."""
    global _SUB_BOUNDS
    if _SUB_BOUNDS is None:
        fp = os.path.join(BUILD, "subtitle_bounds.json")
        try:
            _SUB_BOUNDS = json.load(open(fp, encoding="utf-8"))
        except Exception:
            _SUB_BOUNDS = {}
    return _SUB_BOUNDS


def subtitle_for(block, t_in_block):
    """Pick the subtitle line by measured pause timing inside the VO span."""
    lines = NARRATION[block["vo"]]
    vo_t = t_in_block - PRE_ROLL
    if vo_t < -0.15 or vo_t > block["vo_dur"] + 0.4:
        return None, 0.0
    b = _load_sub_bounds().get(block["vo"])
    if b and len(b) == len(lines) + 1:
        bounds = np.array(b, np.float32)
        bounds[0] = max(0.0, bounds[0] - 0.12)          # show a hair before the first word
        bounds[-1] = bounds[-1] + 0.35                   # keep the last line up briefly after the voice stops
    else:
        weights = np.array([max(2, len(l)) for l in lines], np.float32)
        bounds = np.concatenate([[0], np.cumsum(weights) / weights.sum()]) * block["vo_dur"]
    for i, l in enumerate(lines):
        if bounds[i] <= vo_t < bounds[i + 1]:
            a = min(1.0, (vo_t - bounds[i]) / 0.14)
            out = bounds[i + 1] - vo_t
            bq = min(1.0, out / 0.14)
            return l, max(0.0, min(a, bq))
    return None, 0.0


_flow_cache = {}
_dis = None


def flow_interp(a, b, t, key=None):
    """Motion-compensated in-between of frames a,b at fraction t (0..1) using DIS optical flow.

    Warps both neighbours toward the intermediate time and blends them, which removes the
    double-image ghosting of plain cross-fades when a clip is slowed down.
    """
    global _dis
    if _dis is None:
        _dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        _dis.setFinestScale(1)
    h, w = a.shape[:2]
    cached = _flow_cache.get(key) if key is not None else None
    if cached is None:
        # Coarse-to-fine flow at 360px wide, then scale displacement vectors to source pixels.
        fw, fh = min(360, w), max(8, int(round(h * min(360, w) / w)))
        ga = cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (fw, fh), interpolation=cv2.INTER_AREA)
        gb = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (fw, fh), interpolation=cv2.INTER_AREA)
        scale = np.array([w / fw, h / fh], dtype=np.float32)
        fab = cv2.resize(_dis.calc(ga, gb, None), (w, h)) * scale
        fba = cv2.resize(_dis.calc(gb, ga, None), (w, h)) * scale
        cached = (fab, fba)
        if key is not None:
            if len(_flow_cache) > 6:
                _flow_cache.clear()
            _flow_cache[key] = cached
    fab, fba = cached
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    # backward warping: sample a at (x - t*flow_ab) approximates the motion at time t
    map_a = (xs - fab[..., 0] * t, ys - fab[..., 1] * t)
    map_b = (xs - fba[..., 0] * (1 - t), ys - fba[..., 1] * (1 - t))
    wa = cv2.remap(a, map_a[0], map_a[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    wb = cv2.remap(b, map_b[0], map_b[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return cv2.addWeighted(wa, 1 - t, wb, t, 0)


def compose(gt, timeline, blocks, total, reader, rng):
    # find shot
    cur = None
    for s in timeline:
        if s["start"] <= gt < s["start"] + s["dur"] + 1e-6:
            cur = s
            break
    if cur is None:
        cur = timeline[-1]
    lt = gt - cur["start"]
    # time remap: strictly monotonic. The clip is stretched uniformly over its slot (never reversed,
    # never frozen). Slow-motion up to ~1.6x is smoothed with optical-flow interpolation below.
    nat = cur["natural"]
    slot = cur["dur"]
    ct = lt * (nat / slot) if slot > 0 else 0.0
    ct = max(0.0, min(nat - 1.0 / cur["fps"], ct))
    idx = ct * cur["fps"] + cur.get("offset", 0)
    f0 = reader.get(cur["path"], math.floor(idx))
    fr = idx - math.floor(idx)
    if fr > 0.02:
        f1 = reader.get(cur["path"], math.floor(idx) + 1)
        frame = flow_interp(f0, f1, fr, key=(cur["id"], math.floor(idx)))
    else:
        frame = f0
    # gentle push-in over the shot for extra life + gate weave
    crop = cur.get("crop") or {}
    zoom = crop.get("zoom", 1.0) * (1.0 + 0.04 * (lt / max(slot, 1e-6)))
    dx, dy = gate_weave(gt, 3)
    img = fit_cover(frame, zoom, crop.get("cx", 0.5) + dx / W, crop.get("cy", 0.5) + dy / H)
    block = next(b for b in blocks if b["vo"] == cur["vo"])
    fog_strength = 0.10 if cur["vo"] not in ("N08", "N09") else 0.06
    img = post(img, gt, rng, fog_strength=fog_strength)

    # transitions: dissolve 0.6 s between shots inside a block, dip-to-black 0.5 s between blocks
    fade = 1.0
    at_block_start = abs(gt - block["start"]) < 0.5
    at_block_end = (block["start"] + block["dur"] - gt) < 0.5
    if at_block_start and block["start"] > 0:
        fade = min(fade, (gt - block["start"]) / 0.5)
    if at_block_end:
        fade = min(fade, (block["start"] + block["dur"] - gt) / 0.5)
    if gt < 1.2:
        fade = min(fade, gt / 1.2)
    if total - gt < 1.5:
        fade = min(fade, (total - gt) / 1.5)
    # dissolve within block
    nxt = next((s for s in timeline if s["start"] > cur["start"]), None)
    if nxt and nxt["vo"] == cur["vo"] and (cur["start"] + cur["dur"] - gt) < 0.6:
        a = 1 - (cur["start"] + cur["dur"] - gt) / 0.6
        img1 = _dissolve_cache.get(nxt["id"])
        if img1 is None:
            # Respect retake trims/crop in the incoming dissolve as well as the main shot.
            f1 = reader_next.get(nxt["path"], nxt.get("offset", 0))
            nc = nxt.get("crop") or {}
            img1 = post(fit_cover(f1, nc.get("zoom", 1.0), nc.get("cx", 0.5), nc.get("cy", 0.5)),
                        nxt["start"], rng, fog_strength=fog_strength)
            _dissolve_cache.clear()
            _dissolve_cache[nxt["id"]] = img1
        img = cv2.addWeighted(img, 1 - a, img1, a, 0)
    if fade < 1:
        img = (img.astype(np.float32) * max(0.0, fade)).astype(np.uint8)

    # Upscale the native-resolution picture before crisp 1080p typography.
    img = cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC)

    # titles
    if cur["id"] == TITLE_AT:
        a = min(1.0, lt / 0.8) * min(1.0, (slot - lt) / 0.8)
        draw_text_center(img, "白教堂的雾", H * 0.36, 118, True, (232, 220, 196), a, spacing=10)
        draw_text_center(img, "1888 · 开膛手杰克", H * 0.36 + 120, 44, False, (200, 180, 150), a, spacing=6)
        draw_text_center(img, "JACK THE RIPPER", H * 0.36 + 175, 28, False, (150, 135, 115), a * 0.8, spacing=8)
    if cur["id"] == END_AT:
        a = min(1.0, max(0.0, (lt - slot * 0.35) / 1.0)) * min(1.0, (slot - lt) / 1.0 + 0.2)
        draw_text_center(img, "他是谁？", H * 0.40, 128, True, (232, 220, 196), a, spacing=14)
        draw_text_center(img, "评论区说出你的推理", H * 0.40 + 125, 42, False, (200, 180, 150), a, spacing=4)

    # subtitles (Douyin safe zone: keep above bottom 22%, inside horizontal 8% margins)
    line, sa = subtitle_for(block, gt - block["start"])
    if line:
        draw_text_center(img, line, H * 0.745, subtitle_size(line), False, (245, 240, 230), sa, stroke=3, stroke_color=(10, 8, 6))
    # small persistent watermark-free chapter tag top-left (date cards)
    return img


reader_next = ClipReader()
_dissolve_cache = {}


def render_range(args):
    f0, f1, path, timeline, blocks, total = args
    reader = ClipReader()
    rng = np.random.default_rng(99)
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-g", str(FPS * 2), "-threads", "1", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(f0, f1):
        gt = (i + 0.5) / FPS
        img = compose(gt, timeline, blocks, total, reader, rng)
        p.stdin.write(img.tobytes())
        if (i - f0) % 96 == 0:
            print(f"[seg {f0:5d}] {i - f0 + 1:4d}/{f1 - f0} {time.time() - t0:6.1f}s", flush=True)
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"Segment encoding failed: {path}")
    return path


# --------------------------------------------------------------------------- audio

def build_soundtrack(timeline, blocks, total, path):
    from engine import audio as au
    from scipy.io import wavfile
    sr = 48000
    n = int(total * sr) + sr
    rng = np.random.default_rng(5)
    mixL = np.zeros(n, np.float32)
    mixR = np.zeros(n, np.float32)

    def place(sig, t0, gain=1.0, pan=0.0):
        s0 = int(t0 * sr)
        seg = sig[: max(0, n - s0)]
        if len(seg) == 0:
            return
        l = math.sqrt(0.5 * (1 - pan))
        r = math.sqrt(0.5 * (1 + pan))
        mixL[s0:s0 + len(seg)] += seg * gain * l
        mixR[s0:s0 + len(seg)] += seg * gain * r

    # beds
    place(au.wind_bed(n, rng, base=180, howl=0.15), 0, 0.10)
    place(au.drone(n, 55.0, rng, amp=1.0, detune=0.4, dark=1.0), 0, 0.09)
    place(au.rain_bed(n, rng, intensity=0.25), 0, 0.05)
    # heartbeat under the opening and the ending
    hb = au.heartbeat(int(20 * sr), rate=1.05)
    place(hb, 0.0, 0.35)
    place(au.heartbeat(int(18 * sr), rate=1.2), max(0, total - 18), 0.30)
    # hooves/creaking cart in the street scenes
    for b in blocks:
        if b["vo"] in ("N02", "N05"):
            place(au.hooves(int(b["dur"] * sr), rng, rate=1.6, amp=1.0), b["start"], 0.08, pan=-0.3)
            place(au.creak_wheels(int(b["dur"] * sr), rng, rate=0.6, amp=1.0), b["start"], 0.05, pan=-0.2)
        if b["vo"] == "N04":
            place(au.quill(int(min(8, b["dur"]) * sr), rng, amp=1.0), b["start"] + PRE_ROLL, 0.18, pan=0.2)
            place(au.pulse_drum(int(b["dur"] * sr), 96, rng, amp=1.0, accent_every=4, start=b["dur"] * 0.45), b["start"], 0.10)
        if b["vo"] == "N06":
            place(au.whoosh(int(3 * sr), 0.0, 1.2, rng, amp=1.0, f0=300, f1=1200), b["start"] + b["dur"] * 0.45, 0.10)
        if b["vo"] == "N07":
            place(au.thud(int(2 * sr), 0.0, rng, amp=1.0), b["start"] + b["dur"] * 0.72, 0.35)
    # piano motif: one note per victim block (rising pitch)
    notes = {"N02": 220.0, "N03": 246.9, "N05": 277.2, "N07": 329.6}
    for b in blocks:
        if b["vo"] in notes:
            tone = au.bell(int(6 * sr), 0.0, f0=notes[b["vo"]], decay=2.5, amp=1.0)
            place(tone, b["start"] + 0.3, 0.16)
    # closing bell
    place(au.bell(int(8 * sr), 0.0, f0=110.0, decay=4.0, amp=1.0), max(0, total - 6.5), 0.22)
    # native ambience from the AI clips (rain / street tone), time-aligned to each shot's slot
    nat = np.zeros((n, 2), np.float32)
    for sh in timeline:
        wav = os.path.join(BUILD, f"nat_{sh['id']}.wav")
        info = subprocess.run([FFMPEG, "-hide_banner", "-i", sh["path"]], capture_output=True, text=True).stderr
        if "Audio:" not in info:
            continue
        r = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "quiet", "-y", "-ss", str(sh.get("offset", 0) / sh["fps"]), "-i", sh["path"], "-t", str(sh["natural"]), "-vn", "-ar", str(sr), "-ac", "2", wav])
        if r.returncode != 0 or not os.path.exists(wav):
            continue
        try:
            _, data = wavfile.read(wav)
        except Exception:
            continue
        data = data.astype(np.float32) / 32768.0 if data.dtype == np.int16 else data.astype(np.float32)
        if data.ndim == 1:
            data = np.stack([data, data], axis=1)
        slot = int(sh["dur"] * sr)
        seg = data[:slot]
        if len(seg) < slot:  # clip shorter than its slot → loop the tail with a crossfade-free repeat of ambience
            reps = int(np.ceil(slot / max(1, len(seg))))
            seg = np.concatenate([seg] * reps, axis=0)[:slot]
        fade = np.ones(slot, np.float32)
        k = min(slot // 2, int(0.6 * sr))
        if k > 0:
            fade[:k] = np.linspace(0, 1, k); fade[-k:] = np.linspace(1, 0, k)
        s0 = int(sh["start"] * sr)
        seg = seg[: max(0, n - s0)] * fade[: max(0, n - s0)][:, None]
        nat[s0:s0 + len(seg)] += seg
    # normalise native ambience to a steady bed level
    nrms = float(np.sqrt(np.mean(nat ** 2)) + 1e-9)
    nat *= min(4.0, 0.045 / nrms)
    bed = np.stack([mixL, mixR], axis=1) + nat

    # narration
    vo = np.zeros((n, 2), np.float32)
    for b in blocks:
        mp3 = os.path.join(VO, f"{b['vo']}.mp3")
        wav = os.path.join(BUILD, f"{b['vo']}.wav")
        subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", mp3, "-ar", str(sr), "-ac", "2", wav], check=True)
        _, data = wavfile.read(wav)
        data = data.astype(np.float32) / 32768.0 if data.dtype == np.int16 else data.astype(np.float32)
        # remove any DC / rumble, tame isolated peaks (soft knee above 0.45), micro fades at both ends
        data = data - data.mean(axis=0, keepdims=True)
        mag = np.abs(data)
        soft = np.where(mag > 0.45, 0.45 + (mag - 0.45) / (1 + (mag - 0.45) * 4.0), mag)
        data = np.sign(data) * soft
        k = int(0.02 * sr)
        if len(data) > 2 * k:
            data[:k] *= np.linspace(0, 1, k)[:, None]
            data[-k:] *= np.linspace(1, 0, k)[:, None]
        s0 = int((b["start"] + PRE_ROLL) * sr)
        seg = data[: max(0, n - s0)]
        vo[s0:s0 + len(seg)] += seg
    # duck the bed under narration
    env = np.abs(vo).max(axis=1)
    k = int(0.08 * sr)
    from scipy.ndimage import uniform_filter1d
    env = uniform_filter1d(env, size=k, mode="constant")
    # asymmetric smoothing: fast attack, slow release (done on a decimated envelope for speed)
    dec = 480
    e = env[::dec]
    out = np.zeros_like(e)
    a_att, a_rel = 0.55, 0.985
    v = 0.0
    for i, x in enumerate(e):
        v = x + (v - x) * (a_att if x > v else a_rel)
        out[i] = v
    env = np.interp(np.arange(len(env)), np.arange(len(out)) * dec, out)
    duck = np.clip(1.0 - 0.65 * np.clip(env / (env.max() + 1e-6) * 3.0, 0, 1), 0.35, 1.0)[:, None]
    mix = bed * duck * 0.9 + vo * 1.0
    mix = mix[: int(total * sr)]
    # loudness: bring the programme to ≈ -18 dBFS RMS (≈ -16 LUFS for speech-led content), then soft-limit at -1 dBFS
    rms = float(np.sqrt(np.mean(mix ** 2)) + 1e-9)
    mix *= min(2.5, (10 ** (-20 / 20)) / rms)
    lim = 10 ** (-1 / 20)
    mag = np.abs(mix)
    over = mag > lim * 0.8
    mix[over] = np.sign(mix[over]) * (lim * 0.8 + (mag[over] - lim * 0.8) * (lim * 0.2) / (lim * 0.2 + (mag[over] - lim * 0.8)))
    mix = np.clip(mix, -lim, lim)
    # master fades
    kf = int(0.8 * sr)
    mix[:kf] *= np.linspace(0, 1, kf)[:, None]
    kf = int(1.5 * sr)
    mix[-kf:] *= np.linspace(1, 0, kf)[:, None]
    wavfile.write(path, sr, (mix * 32767).astype(np.int16))
    return path


# --------------------------------------------------------------------------- QC

def qc(path, expected_total, blocks):
    report = {"file": path, "passed": True, "problems": []}
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    report["probe"] = "\n".join(l.strip() for l in r.splitlines() if "Duration" in l or "Stream" in l)
    report["duration"] = probe_duration(path)
    if abs(report["duration"] - expected_total) > 0.6:
        report["problems"].append(f"duration {report['duration']:.2f} vs expected {expected_total:.2f}")
    # black / frozen frame scan at 4 fps
    cap = cv2.VideoCapture(path)
    prev = None
    black, frozen, t = [], [], 0.0
    step = int(round((cap.get(cv2.CAP_PROP_FPS) or FPS) / 4))
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % step == 0:
            g = cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (90, 160))
            tt = i / (cap.get(cv2.CAP_PROP_FPS) or FPS)
            if g.mean() < 6 and 1.5 < tt < expected_total - 2.0:
                black.append(round(tt, 2))
            if prev is not None and np.abs(g.astype(np.int16) - prev).mean() < 0.15 and 1.5 < tt < expected_total - 2.0:
                frozen.append(round(tt, 2))
            prev = g
        i += 1
    cap.release()
    report["frames"] = i
    # allow dips between blocks: black is only a problem if it persists > 1.0 s
    runs = []
    for tb in black:
        if runs and tb - runs[-1][1] <= 0.3:
            runs[-1][1] = tb
        else:
            runs.append([tb, tb])
    long_black = [r for r in runs if r[1] - r[0] >= 1.0]
    if long_black:
        report["problems"].append(f"black segments: {long_black}")
    fr_runs = []
    for tb in frozen:
        if fr_runs and tb - fr_runs[-1][1] <= 0.3:
            fr_runs[-1][1] = tb
        else:
            fr_runs.append([tb, tb])
    long_frozen = [r for r in fr_runs if r[1] - r[0] >= 1.5]
    if long_frozen:
        report["problems"].append(f"frozen segments: {long_frozen}")
    report["black_samples"] = runs
    report["frozen_samples"] = fr_runs
    # audio presence
    wav = os.path.join(BUILD, "qc_audio.wav")
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "8000", wav], check=True)
    from scipy.io import wavfile
    sr, a = wavfile.read(wav)
    a = a.astype(np.float32) / 32768.0
    rms = float(np.sqrt(np.mean(a ** 2)) + 1e-9)
    report["audio_rms_db"] = round(20 * math.log10(rms), 1)
    report["audio_peak_db"] = round(20 * math.log10(float(np.abs(a).max()) + 1e-9), 2)
    if report["audio_rms_db"] < -30:
        report["problems"].append("audio too quiet")
    # VO onsets present at block starts
    onsets = []
    for b in blocks:
        s0 = int((b["start"] + PRE_ROLL) * sr)
        seg = a[s0:s0 + int(1.5 * sr)]
        onsets.append([b["vo"], round(float(np.abs(seg).max()), 3)])
    report["vo_onsets"] = onsets
    if any(o[1] < 0.02 for o in onsets):
        report["problems"].append("missing narration at block start: " + str([o for o in onsets if o[1] < 0.02]))
    report["passed"] = not report["problems"]
    return report


# --------------------------------------------------------------------------- CLI

def cmd_plan():
    timeline, blocks, total, vo_dur = build_timeline()
    print(f"{'shot':5s} {'vo':4s} {'start':>7s} {'dur':>6s} {'clip':>6s}")
    for s in timeline:
        print(f"{s['id']:5s} {s['vo']:4s} {s['start']:7.2f} {s['dur']:6.2f} {s['natural']:6.2f}")
    missing = [s["id"] for s in SHOTS["shots"] if s["id"] not in {t["id"] for t in timeline}]
    print(f"total {total:.2f}s  ({int(total * FPS)} frames)  clips used {len(timeline)}/{len(SHOTS['shots'])}  missing: {missing}")
    return timeline, blocks, total


def cmd_render(workers, only=None):
    timeline, blocks, total = cmd_plan()
    if not timeline:
        print("no clips available yet")
        return 1
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    nframes = int(round(total * FPS))
    seg = 600
    # Segment cache keyed by everything that influences its pixels: the shots overlapping the segment
    # (id, path, mtime, start, dur, offset, natural), the block boundaries, total length and the code version.
    import hashlib
    subtitle_fp = os.path.join(BUILD, "subtitle_bounds.json")
    if not os.path.exists(subtitle_fp):
        raise RuntimeError("Missing measured subtitle timings; run vo_align.py first")
    code_sig = RENDER_VERSION + hashlib.sha256(open(subtitle_fp, "rb").read()).hexdigest()
    code_sig += hashlib.sha256(open(__file__, "rb").read()).hexdigest()
    def seg_key(f0, f1):
        t0s, t1s = f0 / FPS, f1 / FPS
        parts = [code_sig, f"{total:.3f}", f"{f0}-{f1}"]
        for sh in timeline:
            if sh["start"] - 1.0 < t1s and sh["start"] + sh["dur"] + 1.0 > t0s:
                parts.append(f"{sh['id']}|{os.path.getmtime(sh['path']):.0f}|{sh['start']:.3f}|{sh['dur']:.3f}|{sh.get('offset',0)}|{sh['natural']:.3f}|{json.dumps(sh.get('crop') or {}, sort_keys=True)}")
        for b in blocks:
            if b["start"] - 1.0 < t1s and b["start"] + b["dur"] + 1.0 > t0s:
                parts.append(f"{b['vo']}|{b['start']:.3f}|{b['dur']:.3f}")
        return hashlib.md5("\n".join(parts).encode()).hexdigest()
    cache_fp = os.path.join(BUILD, "seg_cache.json")
    try:
        cache = json.load(open(cache_fp))
    except Exception:
        cache = {}
    if not only:
        for f in glob.glob(os.path.join(BUILD, "seg_*.mp4")):
            os.remove(f)
        cache = {}
    jobs, keep = [], []
    for f in glob.glob(os.path.join(BUILD, "seg_*.mp4")):
        if int(os.path.basename(f)[4:10]) >= nframes:
            os.remove(f)                                      # stale segment beyond the new end
    for f0 in range(0, nframes, seg):
        f1 = min(nframes, f0 + seg)
        path = os.path.join(BUILD, f"seg_{f0:06d}.mp4")
        key = seg_key(f0, f1)
        complete = False
        if only and os.path.exists(path) and cache.get(os.path.basename(path)) == key:
            c = cv2.VideoCapture(path)
            complete = int(c.get(cv2.CAP_PROP_FRAME_COUNT)) == (f1 - f0)
            c.release()
        if complete:
            keep.append(path)
        else:
            jobs.append((f0, f1, path, timeline, blocks, total))
            cache[os.path.basename(path)] = key
            if os.path.exists(path):
                os.remove(path)
    print(f"segments to render: {len(jobs)}, reused: {len(keep)}", flush=True)
    t0 = time.time()
    snd = build_soundtrack(timeline, blocks, total, os.path.join(BUILD, "soundtrack.wav"))
    print(f"soundtrack done ({time.time() - t0:.0f}s)", flush=True)
    if jobs:
        with mp.Pool(min(workers, len(jobs)), maxtasksperchild=1) as pool:
            for completed in pool.imap_unordered(render_range, jobs, chunksize=1):
                # Save each finished segment, so cancellation does not lose all cache metadata.
                with open(cache_fp + ".tmp", "w") as fh:
                    json.dump(cache, fh)
                os.replace(cache_fp + ".tmp", cache_fp)
                print(f"COMPLETED {os.path.basename(completed)}", flush=True)
    json.dump(cache, open(cache_fp, "w"))
    print(f"video segments done ({time.time() - t0:.0f}s)", flush=True)
    paths = sorted(glob.glob(os.path.join(BUILD, "seg_*.mp4")))
    lst = os.path.join(BUILD, "segments.txt")
    with open(lst, "w") as fh:
        for p in paths:
            fh.write(f"file '{p}'\n")
    video_only = os.path.join(BUILD, "video_only.mp4")
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video_only], check=True)
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", video_only, "-i", snd, "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", FINAL], check=True)
    print(f"muxed → {FINAL}")
    rep = qc(FINAL, total, blocks)
    with open(os.path.join(OUT, "qc_report.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=2)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    print("QC PASSED" if rep["passed"] else "QC FAILED")
    return 0 if rep["passed"] else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "render", "check"])
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--incremental", "--only", dest="only", action="store_true", help="reuse cached segments whose inputs are unchanged")
    a = ap.parse_args()
    if a.cmd == "plan":
        cmd_plan()
        return 0
    if a.cmd == "render":
        return cmd_render(a.workers, a.only)
    timeline, blocks, total = cmd_plan()
    rep = qc(FINAL, total, blocks)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
