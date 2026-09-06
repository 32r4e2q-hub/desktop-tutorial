"""Procedural set construction: textures (cobbles, timber houses, cathedral, mountains, interiors)
and perspective-correct planar quads for the 2.5D camera."""
from __future__ import annotations

import math
import numpy as np
import cv2

from .common import (W, AH, CX, AA, P, PTS, col, mix, clamp, clamp01, fbm_tile, Layer, blit, fog_amount, fog_color, Noise1D)



def C(c):
    """OpenCV 5 wants plain python scalars for colours."""
    if isinstance(c, np.ndarray):
        c = c.tolist()
    if isinstance(c, (list, tuple)):
        return tuple(float(v) for v in c)
    return float(c)

# ----------------------------------------------------------------------------- generic quads

def warp_quad(canvas, rgb, alpha, quad, fog_f=0.0, fogc=None, tint=None, mips=None):
    """Draw texture (rgb uint8, alpha float32 0..1) onto screen quad [TL, TR, BR, BL] (float px)."""
    q = np.asarray(quad, np.float32)
    x0, y0 = int(math.floor(q[:, 0].min())), int(math.floor(q[:, 1].min()))
    x1, y1 = int(math.ceil(q[:, 0].max())), int(math.ceil(q[:, 1].max()))
    hh, ww = canvas.shape[:2]
    cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x1, ww), min(y1, hh)
    if cx1 - cx0 < 2 or cy1 - cy0 < 2:
        return
    th, tw = rgb.shape[:2]
    # choose mip level by on-screen width vs texture width
    level = 0
    if mips is not None:
        sw = max(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3]))
        s = sw / tw
        while s < 0.5 and level < len(mips) - 1:
            level += 1
            s *= 2
        rgb, alpha = mips[level]
        th, tw = rgb.shape[:2]
    src = np.array([[0, 0], [tw, 0], [tw, th], [0, th]], np.float32)
    dst = q - np.array([cx0, cy0], np.float32)
    Hm = cv2.getPerspectiveTransform(src, dst)
    dsize = (cx1 - cx0, cy1 - cy0)
    r = cv2.warpPerspective(rgb, Hm, dsize, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    a = cv2.warpPerspective(alpha, Hm, dsize, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if fog_f > 0.001 or tint is not None:
        rf = r.astype(np.float32)
        if tint is not None:
            rf *= np.asarray(tint, np.float32)
        if fog_f > 0.001:
            rf = rf * (1 - fog_f) + np.asarray(fogc, np.float32) * fog_f
        r = np.clip(rf, 0, 255).astype(np.uint8)
    blit(canvas, r, a, cx0, cy0)


def make_mips(rgb, alpha):
    mips = [(rgb, alpha)]
    r, a = rgb, alpha
    while min(r.shape[:2]) > 16:
        r = cv2.resize(r, (max(1, r.shape[1] // 2), max(1, r.shape[0] // 2)), interpolation=cv2.INTER_AREA)
        a = cv2.resize(a, (r.shape[1], r.shape[0]), interpolation=cv2.INTER_AREA)
        mips.append((r, a))
    return mips


class Facade:
    """Vertical wall plane at X = x, spanning Z0..Z1 and Y from ybot (ground) up to ytop (ybot - height)."""

    def __init__(self, rgb, alpha, x, z0, z1, ybot, height, meta=None):
        self.rgb = np.ascontiguousarray(rgb, np.uint8)
        a = alpha.astype(np.float32)
        if a.max() > 1.5:
            a /= 255.0
        self.alpha = np.ascontiguousarray(a)
        self.mips = make_mips(self.rgb, self.alpha)
        self.x, self.z0, self.z1, self.ybot, self.h = float(x), float(z0), float(z1), float(ybot), float(height)
        self.meta = meta or {}

    @property
    def zfar(self):
        return self.z1

    def draw(self, canvas, cam, fog=None, tint=None, zmin=0.45):
        z0, z1 = self.z0, self.z1
        u0 = 0.0
        if z1 - cam.z < zmin:
            return
        if z0 - cam.z < zmin:
            nz0 = cam.z + zmin
            u0 = (nz0 - z0) / (z1 - z0)
            z0 = nz0
        ytop = self.ybot - self.h
        tl = cam.proj(self.x, ytop, z0)[:2]
        tr = cam.proj(self.x, ytop, z1)[:2]
        br = cam.proj(self.x, self.ybot, z1)[:2]
        bl = cam.proj(self.x, self.ybot, z0)[:2]
        if max(tl[0], tr[0]) < -5 or min(tl[0], tr[0]) > W + 5:
            return
        rgb, alpha, mips = self.rgb, self.alpha, self.mips
        if u0 > 0:
            tw = rgb.shape[1]
            c0 = int(u0 * tw)
            if c0 >= tw - 2:
                return
            rgb, alpha = np.ascontiguousarray(rgb[:, c0:]), np.ascontiguousarray(alpha[:, c0:])
            mips = None
        f = fog_amount(fog, 0.5 * (z0 + z1) - cam.z) if fog else 0.0
        warp_quad(canvas, rgb, alpha, [tl, tr, br, bl], f, fog[0] if fog else None, tint, mips)


class Quad3D:
    """Arbitrary planar quad given by 4 world corners TL, TR, BR, BL (must be in front of the camera)."""

    def __init__(self, rgb, alpha, corners):
        self.rgb = np.ascontiguousarray(rgb, np.uint8)
        a = alpha.astype(np.float32)
        if a.max() > 1.5:
            a /= 255.0
        self.alpha = np.ascontiguousarray(a)
        self.mips = make_mips(self.rgb, self.alpha)
        self.c = np.asarray(corners, np.float64)

    def draw(self, canvas, cam, fog=None, tint=None, offset=(0, 0, 0)):
        c = self.c + np.asarray(offset, np.float64)
        if (c[:, 2] - cam.z).min() < 0.3:
            return
        q = cam.proj_pts(c)
        f = fog_amount(fog, float(c[:, 2].mean()) - cam.z) if fog else 0.0
        warp_quad(canvas, self.rgb, self.alpha, q, f, fog[0] if fog else None, tint, self.mips)


# ----------------------------------------------------------------------------- ground textures

def cobble_tile(seed=0, size=512, base=(84, 80, 76), wet=0.0, snow=0.0, warm=0.0):
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size, 3), np.float32)
    img[:] = np.asarray(mix(base, (0, 0, 0), 0.45), np.float32)
    sh, sw = 20, 26
    rows = size // sh + 2
    cols = size // sw + 2
    for r in range(rows):
        off = (sw // 2) if r % 2 else 0
        for c in range(cols):
            cx = (c * sw + off + rng.uniform(-2, 2)) % size
            cy = (r * sh + rng.uniform(-1.5, 1.5)) % size
            shade = rng.uniform(0.78, 1.18)
            cc = tuple(v * shade for v in base)
            cc = C(mix(cc, (150, 120, 90), warm * 0.25))
            ax, ay = int(sw * 0.46 + rng.uniform(-2, 1)), int(sh * 0.44 + rng.uniform(-1.5, 1))
            for dx in (-size, 0, size):
                for dy in (-size, 0, size):
                    cv2.ellipse(img, (int(cx + dx), int(cy + dy)), (ax, ay), rng.uniform(-8, 8), 0, 360, cc, -1, AA)
                    cv2.ellipse(img, (int(cx + dx - 2), int(cy + dy - 2)), (max(1, ax - 6), max(1, ay - 5)), 0, 0, 360, C(tuple(v * 1.09 for v in cc)), -1, AA)
    img = cv2.GaussianBlur(img, (0, 0), 0.7)
    dirt = fbm_tile(size, size, octaves=4, seed=seed + 5, base=3)
    img *= (0.82 + 0.36 * dirt)[..., None]
    if wet > 0:
        pud = fbm_tile(size, size, octaves=4, seed=seed + 9, base=2)
        m = np.clip((pud - (0.66 - 0.12 * wet)) / 0.1, 0, 1)[..., None]
        wetc = np.asarray((70, 82, 100), np.float32)
        img = img * (1 - m * 0.85) + wetc * m * 0.85
        img *= (1 - 0.18 * wet)
    if snow > 0:
        sn = fbm_tile(size, size, octaves=4, seed=seed + 13, base=3)
        m = np.clip((sn - (0.55 - 0.3 * snow)) / 0.15, 0, 1)[..., None]
        img = img * (1 - m) + np.asarray((222, 226, 236), np.float32) * m
    return np.clip(img, 0, 255).astype(np.uint8)


def flagstone_tile(seed=0, size=512, base=(120, 112, 100)):
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size, 3), np.float32)
    img[:] = np.asarray(mix(base, (0, 0, 0), 0.5), np.float32)
    sh, sw = 56, 84
    for r in range(size // sh + 2):
        off = (sw // 2) if r % 2 else 0
        for c in range(size // sw + 2):
            x = (c * sw + off) % size
            y = (r * sh) % size
            shade = rng.uniform(0.82, 1.15)
            cc = tuple(v * shade for v in base)
            for dx in (-size, 0, size):
                for dy in (-size, 0, size):
                    cv2.rectangle(img, (int(x + dx + 2), int(y + dy + 2)), (int(x + dx + sw - 3), int(y + dy + sh - 3)), cc, -1)
    img = cv2.GaussianBlur(img, (0, 0), 0.8)
    dirt = fbm_tile(size, size, octaves=4, seed=seed + 5, base=3)
    img *= (0.8 + 0.4 * dirt)[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


def dirt_tile(seed=0, size=512, base=(96, 84, 68), ruts=True):
    img = np.zeros((size, size, 3), np.float32)
    n = fbm_tile(size, size, octaves=5, seed=seed, base=3)
    img[:] = np.asarray(base, np.float32) * (0.7 + 0.6 * n)[..., None]
    if ruts:
        ys = np.arange(size)
        for cy in (size * 0.35, size * 0.65):
            d = np.exp(-((ys - cy) / 14.0) ** 2)
            img *= (1 - 0.35 * d)[:, None, None]
    # pebbles
    rng = np.random.default_rng(seed + 1)
    for _ in range(300):
        x, y = rng.integers(0, size, 2)
        cv2.circle(img, (int(x), int(y)), int(rng.integers(1, 3)), C(tuple(v * rng.uniform(0.6, 1.3) for v in base)), -1)
    return np.clip(img, 0, 255).astype(np.uint8)


def plank_tile(seed=0, size=512, base=(92, 70, 48), along_z=True):
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size, 3), np.float32)
    pw = 44
    n = size // pw + 1
    for i in range(n):
        shade = rng.uniform(0.8, 1.15)
        cc = tuple(v * shade for v in base)
        if along_z:
            cv2.rectangle(img, (i * pw, 0), (i * pw + pw - 2, size), cc, -1)
        else:
            cv2.rectangle(img, (0, i * pw), (size, i * pw + pw - 2), cc, -1)
    grainn = fbm_tile(size, size, octaves=5, seed=seed + 3, base=2)
    g = cv2.resize(grainn, (size, size))
    img *= (0.85 + 0.3 * g)[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


def rye_field_tile(seed=0, size=512, base=(150, 128, 70)):
    img = np.zeros((size, size, 3), np.float32)
    n = fbm_tile(size, size, octaves=5, seed=seed, base=4)
    img[:] = np.asarray(base, np.float32) * (0.6 + 0.7 * n)[..., None]
    return np.clip(img, 0, 255).astype(np.uint8)


# ----------------------------------------------------------------------------- houses

def house_texture(w_m, h_wall, h_gable, seed, ppm=40, stucco=None, timber=(54, 38, 26), snow=0.0):
    """Half-timbered gable-fronted house. Returns rgb, alpha, windows [(x, y, w, h) metres from top-left], door."""
    rng = np.random.default_rng(seed)
    wpx, hpx = int(w_m * ppm), int((h_wall + h_gable) * ppm)
    stucco = stucco or rng.choice([(196, 180, 150), (176, 160, 128), (188, 172, 146), (170, 150, 120), (160, 140, 118)], axis=0)
    stucco = tuple(float(v) for v in np.asarray(stucco))
    img = np.zeros((hpx, wpx, 3), np.float32)
    img[:] = np.asarray(stucco, np.float32)
    grime = fbm_tile(hpx, wpx, octaves=4, seed=seed + 2, base=3)
    img *= (0.78 + 0.32 * grime)[..., None]
    # darker lower wall
    ys = np.linspace(0, 1, hpx)[:, None, None]
    img *= (1 - 0.25 * np.clip((ys - 0.65) / 0.35, 0, 1))
    alpha = np.zeros((hpx, wpx), np.float32)
    gy = int(h_gable * ppm)
    cv2.rectangle(alpha, (0, gy), (wpx, hpx), 1.0, -1)
    cv2.fillPoly(alpha, [np.array([[0, gy], [wpx // 2, 0], [wpx, gy]], np.int32)], 1.0)
    tb = tuple(float(v) for v in timber)
    tw_ = max(2, int(0.14 * ppm))
    floors = max(1, int(round(h_wall / 2.9)))
    fh = h_wall / floors
    windows, door = [], None
    # horizontal beams
    for i in range(floors + 1):
        y = gy + int(i * fh * ppm)
        cv2.line(img, (0, y), (wpx, y), tb, tw_)
        if 0 < i < floors:
            # jetty shadow
            cv2.line(img, (0, y + tw_ + 2), (wpx, y + tw_ + 2), C(tuple(v * 0.75 for v in stucco)), max(1, tw_ // 2))
    # vertical posts
    nposts = max(2, int(w_m / 1.3))
    for i in range(nposts + 1):
        x = int(i * wpx / nposts)
        cv2.line(img, (x, gy), (x, hpx), tb, tw_)
    # gable framing
    cv2.line(img, (0, gy), (wpx // 2, 0), tb, tw_ + 2)
    cv2.line(img, (wpx, gy), (wpx // 2, 0), tb, tw_ + 2)
    cv2.line(img, (wpx // 2, 0), (wpx // 2, gy), tb, tw_)
    for k in range(1, 3):
        yy = int(gy * k / 3)
        xx = int(wpx / 2 * (1 - k / 3))
        cv2.line(img, (wpx // 2 - xx, yy), (wpx // 2 + xx, yy), tb, tw_)
    # diagonal braces
    for i in range(nposts):
        for fl in range(floors):
            if rng.random() < 0.45:
                x0, x1 = int(i * wpx / nposts), int((i + 1) * wpx / nposts)
                y0, y1 = gy + int(fl * fh * ppm), gy + int((fl + 1) * fh * ppm)
                if rng.random() < 0.5:
                    cv2.line(img, (x0, y1), (x1, y0), tb, max(1, tw_ - 1))
                else:
                    cv2.line(img, (x0, y0), (x1, y1), tb, max(1, tw_ - 1))
    # windows
    glass = (28, 30, 40)
    for fl in range(floors):
        y0 = gy + int(fl * fh * ppm)
        nwin = rng.integers(1, 3) if fl > 0 else rng.integers(0, 2)
        ww_, wh_ = int(0.7 * ppm), int(0.9 * ppm)
        for wi in range(nwin):
            x = int((wi + 1) * wpx / (nwin + 1)) - ww_ // 2 + int(rng.uniform(-4, 4))
            y = y0 + int(0.8 * ppm)
            cv2.rectangle(img, (x - 3, y - 3), (x + ww_ + 3, y + wh_ + 3), tb, -1)
            cv2.rectangle(img, (x, y), (x + ww_, y + wh_), glass, -1)
            cv2.line(img, (x + ww_ // 2, y), (x + ww_ // 2, y + wh_), tb, 2)
            cv2.line(img, (x, y + wh_ // 2), (x + ww_, y + wh_ // 2), tb, 2)
            windows.append((x / ppm, y / ppm, ww_ / ppm, wh_ / ppm))
    # gable window
    gx, gy2 = wpx // 2 - int(0.3 * ppm), int(gy * 0.55)
    cv2.rectangle(img, (gx - 3, gy2 - 3), (gx + int(0.6 * ppm) + 3, gy2 + int(0.7 * ppm) + 3), tb, -1)
    cv2.rectangle(img, (gx, gy2), (gx + int(0.6 * ppm), gy2 + int(0.7 * ppm)), glass, -1)
    windows.append((gx / ppm, gy2 / ppm, 0.6, 0.7))
    # door
    if rng.random() < 0.8:
        dw, dh = int(1.0 * ppm), int(2.0 * ppm)
        dx = int(rng.uniform(0.3, max(0.35, w_m - 1.4)) * ppm)
        dy = hpx - dh
        cv2.rectangle(img, (dx - 4, dy - 4), (dx + dw + 4, hpx), tb, -1)
        cv2.rectangle(img, (dx, dy), (dx + dw, hpx), (40, 30, 22), -1)
        cv2.ellipse(img, (dx + dw // 2, dy + 4), (dw // 2, dw // 3), 0, 180, 360, (40, 30, 22), -1)
        door = (dx / ppm, dw / ppm)
    if snow > 0:
        # snow on beams
        cv2.line(img, (0, gy + 1), (wpx, gy + 1), (225, 228, 238), max(1, tw_ // 2))
        cv2.line(img, (0, gy), (wpx // 2, 0), (225, 228, 238), max(2, tw_ // 2))
        cv2.line(img, (wpx, gy), (wpx // 2, 0), (225, 228, 238), max(2, tw_ // 2))
    return np.clip(img, 0, 255).astype(np.uint8), alpha, windows, door


def build_street(seed=1, z_from=2.0, z_to=70.0, half_w=3.5, ground_y=1.6, snow=0.0, ppm=40):
    """Rows of gable houses on both sides. Returns list of Facade (sorted far→near) and window list in world coords."""
    rng = np.random.default_rng(seed)
    facades, windows, chimneys = [], [], []
    for side in (-1, 1):
        z = z_from + rng.uniform(0, 1.5)
        i = 0
        while z < z_to:
            w = rng.uniform(4.8, 7.5)
            hw = rng.uniform(6.5, 9.5)
            hg = w * 0.55 * rng.uniform(0.9, 1.2)
            rgb, a, wins, door = house_texture(w, hw, hg, int(rng.integers(0, 1 << 30)), ppm=ppm, snow=snow)
            f = Facade(rgb, a, side * half_w, z, z + w, ground_y, hw + hg, meta=dict(side=side, door=door, w=w, hw=hw, hg=hg))
            facades.append(f)
            for (wx, wy, ww_, wh_) in wins:
                # texture u runs along Z from z (u=0) → z+w; y from top (ytop = ground_y - (hw+hg))
                ytop = ground_y - (hw + hg)
                windows.append(dict(x=side * half_w, z0=z + wx, z1=z + wx + ww_, y0=ytop + wy, y1=ytop + wy + wh_,
                                    lit=rng.random() < 0.28, seed=int(rng.integers(0, 10000)), side=side))
            if rng.random() < 0.5:
                chimneys.append((side * (half_w + 1.2), ground_y - (hw + hg * 0.75), z + w * 0.5))
            z += w + rng.uniform(0.0, 0.3)
            i += 1
    facades.sort(key=lambda f: -f.zfar)
    return facades, windows, chimneys


# ----------------------------------------------------------------------------- big set pieces

def cathedral_layer(ppm=10, X=-20.0, Z=45.0, ground_y=1.6, color=(72, 62, 60), detail=1.0):
    """Strasbourg-like facade with single north spire, as a front-facing Layer. Width 40 m, height 142 m."""
    wm, hm = 40.0, 142.0
    wpx, hpx = int(wm * ppm), int(hm * ppm)
    img = np.zeros((hpx, wpx, 3), np.float32)
    alpha = np.zeros((hpx, wpx), np.float32)
    c_arr = np.asarray(color, np.float32)
    c = C(c_arr)
    dark = C(c_arr * 0.55)
    light = C(c_arr * 1.25)

    def M(x, y):
        return int(x * ppm), int(hpx - y * ppm)

    # main facade block: 40 m wide, 66 m tall
    cv2.rectangle(alpha, M(0, 0), M(40, 66), 1.0, -1)
    cv2.rectangle(img, M(0, 0), M(40, 66), c, -1)
    # towers bases (both to 66) — north tower (left) continues
    cv2.rectangle(alpha, M(2, 66), M(15, 100), 1.0, -1)
    cv2.rectangle(img, M(2, 66), M(15, 100), c, -1)
    # octagon stage
    cv2.rectangle(alpha, M(4.5, 100), M(12.5, 118), 1.0, -1)
    cv2.rectangle(img, M(4.5, 100), M(12.5, 118), C(c_arr * 1.05), -1)
    # spire
    pts = np.array([M(3.5, 118), M(13.5, 118), M(8.5, 142)], np.int32)
    cv2.fillPoly(alpha, [pts], 1.0)
    cv2.fillPoly(img, [pts], C(c_arr * 0.95))
    # spire ribs / openwork
    for i in range(6):
        u = i / 5
        cv2.line(img, M(3.5 + 10 * u, 118), M(8.5, 142), light, 1)
    # pinnacles on stage corners
    for x in (4.5, 12.5):
        cv2.fillPoly(alpha, [np.array([M(x - 1, 118), M(x + 1, 118), M(x, 124)], np.int32)], 1.0)
        cv2.fillPoly(img, [np.array([M(x - 1, 118), M(x + 1, 118), M(x, 124)], np.int32)], c)
    # vertical buttress lines
    for x in (2, 8.5, 15, 25, 31.5, 38):
        cv2.line(img, M(x, 0), M(x, 66 if x > 15 else 100), dark, max(1, int(0.6 * ppm)))
    # horizontal galleries
    for y in (20, 40, 52, 66):
        cv2.line(img, M(0, y), M(40, y), dark, max(1, int(0.5 * ppm)))
        cv2.line(img, M(0, y + 0.7), M(40, y + 0.7), light, max(1, int(0.25 * ppm)))
    # rose window
    cx, cy = M(20, 44)
    r = int(7.5 * ppm)
    cv2.circle(img, (cx, cy), r, dark, -1)
    cv2.circle(img, (cx, cy), r, light, max(1, int(0.5 * ppm)))
    for i in range(16):
        a = i * math.pi / 8
        cv2.line(img, (cx, cy), (int(cx + math.cos(a) * r), int(cy + math.sin(a) * r)), light, max(1, int(0.25 * ppm)))
    cv2.circle(img, (cx, cy), int(r * 0.35), light, max(1, int(0.3 * ppm)))
    # portals (pointed arches)
    for x, w, h in ((20, 9, 16), (8.5, 5, 11), (31.5, 5, 11)):
        x0, y0 = M(x - w / 2, 0)
        x1, y1 = M(x + w / 2, h * 0.7)
        cv2.rectangle(img, (x0, y0), (x1, y1), C(c_arr * 0.55 * 0.6), -1)
        ptsA = np.array([M(x - w / 2, h * 0.7), M(x, h), M(x + w / 2, h * 0.7)], np.int32)
        cv2.fillPoly(img, [ptsA], C(c_arr * 0.55 * 0.6))
        for k in range(1, 4):
            s = 1 + k * 0.12
            ptsB = np.array([M(x - w * s / 2, 0), M(x - w * s / 2, h * 0.7), M(x, h * s), M(x + w * s / 2, h * 0.7), M(x + w * s / 2, 0)], np.int32)
            cv2.polylines(img, [ptsB], False, light if k % 2 else dark, max(1, int(0.25 * ppm)))
    # lancet windows on towers
    for x in (5.5, 11.5, 28, 34):
        for y in (72, 84):
            if x > 15 and y > 66:
                continue
            x0, y0 = M(x - 1, y)
            x1, y1 = M(x + 1, y + 8)
            cv2.rectangle(img, (x0, y0), (x1, y1), C(c_arr * 0.55 * 0.7), -1)
    # stone texture
    n = fbm_tile(hpx, wpx, octaves=4, seed=42, base=4)
    img *= (0.85 + 0.3 * n)[..., None]
    rgb = np.clip(img, 0, 255).astype(np.uint8)
    return Layer(rgb, alpha, X, ground_y - hm, Z, wm)


def mountain_layer(seed, width_m, height_m, Z, ground_y, color, ppm=2.0, jag=0.5):
    n = Noise1D(seed)
    wpx, hpx = int(width_m * ppm), int(height_m * ppm)
    img = np.zeros((hpx, wpx, 3), np.uint8)
    img[:] = col(color)
    alpha = np.zeros((hpx, wpx), np.float32)
    pts = [(0, hpx)]
    for i in range(0, wpx + 1, 4):
        u = i / wpx
        y = hpx * (0.25 + 0.55 * (0.5 * n(u * 6) + 0.35 * n(u * 17 + 30) * jag + 0.15 * n(u * 50 + 60) * jag))
        pts.append((i, y))
    pts.append((wpx, hpx))
    cv2.fillPoly(alpha, [np.array(pts, np.int32)], 1.0)
    return Layer(img, alpha, -width_m / 2, ground_y - height_m, Z, width_m)


def pine_layer(seed, X, Z, ground_y, height_m=9.0, color=(24, 34, 30), ppm=24):
    rng = np.random.default_rng(seed)
    wm = height_m * 0.45
    wpx, hpx = int(wm * ppm), int(height_m * ppm)
    img = np.zeros((hpx, wpx, 3), np.uint8)
    img[:] = col(color)
    alpha = np.zeros((hpx, wpx), np.float32)
    tiers = 6
    for i in range(tiers):
        u = i / (tiers - 1)
        y0 = int(hpx * (0.05 + 0.75 * u))
        y1 = int(hpx * (0.05 + 0.75 * u) + hpx * 0.28)
        half = int(wpx / 2 * (0.25 + 0.75 * u) * rng.uniform(0.85, 1.05))
        cv2.fillPoly(alpha, [np.array([[wpx // 2, y0], [wpx // 2 - half, y1], [wpx // 2 + half, y1]], np.int32)], 1.0)
    cv2.rectangle(alpha, (wpx // 2 - max(1, int(0.03 * hpx)), int(hpx * 0.8)), (wpx // 2 + max(1, int(0.03 * hpx)), hpx), 1.0, -1)
    return Layer(img, alpha, X - wm / 2, ground_y - height_m, Z, wm)


def stone_wall_texture(w_m, h_m, seed=3, ppm=30, base=(96, 88, 80), windows=()):
    rng = np.random.default_rng(seed)
    wpx, hpx = int(w_m * ppm), int(h_m * ppm)
    img = np.zeros((hpx, wpx, 3), np.float32)
    img[:] = np.asarray(base, np.float32) * 0.6
    bh, bw = int(0.45 * ppm), int(1.0 * ppm)
    for r in range(hpx // bh + 1):
        off = bw // 2 if r % 2 else 0
        for c_ in range(-1, wpx // bw + 1):
            x, y = c_ * bw + off, r * bh
            cc = tuple(v * rng.uniform(0.85, 1.12) for v in base)
            cv2.rectangle(img, (x + 2, y + 2), (x + bw - 2, y + bh - 2), cc, -1)
    n = fbm_tile(hpx, wpx, octaves=4, seed=seed + 1, base=3)
    img *= (0.75 + 0.4 * n)[..., None]
    ys = np.linspace(0, 1, hpx)[:, None, None]
    img *= (0.55 + 0.45 * (1 - ys))  # darker at the bottom
    wins = []
    for (wx, wy, ww_, wh_) in windows:
        x0, y0 = int(wx * ppm), int(wy * ppm)
        x1, y1 = int((wx + ww_) * ppm), int((wy + wh_) * ppm)
        cv2.rectangle(img, (x0, y0 + (x1 - x0) // 2), (x1, y1), (150, 165, 190), -1)
        cv2.ellipse(img, ((x0 + x1) // 2, y0 + (x1 - x0) // 2), ((x1 - x0) // 2, (x1 - x0) // 2), 0, 180, 360, (150, 165, 190), -1)
        cv2.line(img, ((x0 + x1) // 2, y0), ((x0 + x1) // 2, y1), (60, 55, 50), max(1, int(0.06 * ppm)))
        for k in range(1, 6):
            yy = y0 + (y1 - y0) * k // 6
            cv2.line(img, (x0, yy), (x1, yy), (60, 55, 50), max(1, int(0.04 * ppm)))
        wins.append((x0, y0, x1, y1))
    return np.clip(img, 0, 255).astype(np.uint8), np.ones((hpx, wpx), np.float32)


def wood_texture(w_m, h_m, seed=5, ppm=40, base=(110, 82, 52), planks_vertical=False, plank_w=0.3):
    rng = np.random.default_rng(seed)
    wpx, hpx = max(2, int(w_m * ppm)), max(2, int(h_m * ppm))
    img = np.zeros((hpx, wpx, 3), np.float32)
    pw = max(2, int(plank_w * ppm))
    n = (wpx if planks_vertical else hpx) // pw + 1
    for i in range(n):
        cc = tuple(v * rng.uniform(0.82, 1.15) for v in base)
        if planks_vertical:
            cv2.rectangle(img, (i * pw, 0), (i * pw + pw - 2, hpx), cc, -1)
        else:
            cv2.rectangle(img, (0, i * pw), (wpx, i * pw + pw - 2), cc, -1)
    g = fbm_tile(hpx, wpx, octaves=4, seed=seed + 2, base=2)
    img *= (0.85 + 0.3 * g)[..., None]
    return np.clip(img, 0, 255).astype(np.uint8), np.ones((hpx, wpx), np.float32)


def moon(canvas_f, x, y, r, brightness=1.0):
    """Additive moon disc + halo into float buffer."""
    from .common import draw_glow
    draw_glow(canvas_f, x, y, r * 6, (0.35, 0.42, 0.55), 0.35 * brightness)
    draw_glow(canvas_f, x, y, r * 1.6, (0.8, 0.85, 0.95), 0.9 * brightness)
    cv2.circle(canvas_f, (int(x), int(y)), int(r), (0.85 * brightness, 0.88 * brightness, 0.95 * brightness), -1, AA)
