"""Shared primitives: frame geometry, easing, noise, camera projection, layers, compositing."""
from __future__ import annotations

import math
import numpy as np
import cv2

W, H, FPS = 1280, 720, 24
AH = 536                      # active (2.39:1) picture height
BAR = (H - AH) // 2           # letterbox bar height (92)
CX = W / 2.0
F_PX = 1100.0                 # focal length in pixels (~60 deg horizontal FOV)
SHIFT = 4
SH = float(1 << SHIFT)
AA = cv2.LINE_AA


# ----------------------------------------------------------------------------- math

def clamp(x, a, b):
    return a if x < a else b if x > b else x


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = clamp01(t)
    return t * t * (3 - 2 * t)


def smoothstep(e0, e1, x):
    if e1 == e0:
        return 1.0 if x >= e1 else 0.0
    return smooth((x - e0) / (e1 - e0))


def ease_in(t):
    t = clamp01(t)
    return t * t


def ease_out(t):
    t = clamp01(t)
    return 1 - (1 - t) * (1 - t)


def bump(t, width):
    """Smooth 0->1->0 pulse for t in [0, width]."""
    if t <= 0 or t >= width:
        return 0.0
    return math.sin(math.pi * t / width) ** 2


def mix(c0, c1, t):
    return tuple(a + (b - a) * t for a, b in zip(c0, c1))


def col(c):
    return tuple(int(clamp(round(v), 0, 255)) for v in c)


def kf(keys, t, linear=False):
    """Piecewise interpolation through (time, value) keys. Values may be scalars or tuples."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            if not linear:
                u = smooth(u)
            if isinstance(v0, (tuple, list)):
                return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return keys[-1][1]


def P(x, y):
    return (int(round(x * SH)), int(round(y * SH)))


def PTS(a):
    return np.round(np.asarray(a, np.float64) * SH).astype(np.int32).reshape(-1, 1, 2)


# ----------------------------------------------------------------------------- noise

class Noise1D:
    """Smooth 1-D value noise, deterministic per seed."""

    def __init__(self, seed, n=4096):
        self.v = np.random.default_rng(seed).random(n).astype(np.float32)
        self.n = n

    def __call__(self, x):
        i = int(math.floor(x))
        f = x - i
        f = f * f * (3 - 2 * f)
        a = self.v[i % self.n]
        b = self.v[(i + 1) % self.n]
        return float(a + (b - a) * f)

    def signed(self, x):
        return self(x) * 2 - 1


def fbm_tile(h, w, octaves=5, seed=0, base=4, persistence=0.55):
    """Seamlessly tileable fractal value noise in [0,1], float32 (h, w)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total, n = 1.0, 0.0, base
    for _ in range(octaves):
        g = rng.random((n, n)).astype(np.float32)
        g3 = np.tile(g, (3, 3))
        big = cv2.resize(g3, (3 * w, 3 * h), interpolation=cv2.INTER_CUBIC)
        out += amp * big[h:2 * h, w:2 * w]
        total += amp
        amp *= persistence
        n *= 2
    out /= total
    out -= out.min()
    out /= max(out.max(), 1e-6)
    return out


def scrolled(tile, dx, dy):
    """Return the tile scrolled by (dx, dy) pixels (wrapping)."""
    h, w = tile.shape[:2]
    return np.roll(tile, (int(dy) % h, int(dx) % w), axis=(0, 1))


# ----------------------------------------------------------------------------- sprites / glow

_glow_cache = {}
_GLOW_MAX_R = 260          # sprites above this are produced by resizing the largest cached one
_GLOW_CACHE_MAX = 48       # bounded cache (was unbounded → multi-GB leak over a long render)


def _make_glow(r):
    y, x = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    d = np.sqrt(x * x + y * y) / r
    return (np.clip(1 - d, 0, 1) ** 2.2).astype(np.float32)


def glow_sprite(r):
    """Radial falloff sprite of radius r (quantised so the cache stays small and bounded)."""
    r = int(max(2, r))
    if r > _GLOW_MAX_R:
        base = glow_sprite(_GLOW_MAX_R)
        return cv2.resize(base, (2 * r + 1, 2 * r + 1), interpolation=cv2.INTER_LINEAR)
    # quantise: exact below 16 px, then ~6 % steps
    if r > 16:
        r = int(round(16 * (1.06 ** round(math.log(r / 16.0) / math.log(1.06)))))
        r = min(r, _GLOW_MAX_R)
    sp = _glow_cache.get(r)
    if sp is None:
        if len(_glow_cache) >= _GLOW_CACHE_MAX:
            _glow_cache.pop(next(iter(_glow_cache)))
        sp = _make_glow(r)
        _glow_cache[r] = sp
    return sp


GLOW_MAX_RADIUS = 700  # hard cap: anything bigger than the frame is pointless and would allocate GBs


def draw_glow(fbuf, x, y, r, color, intensity=1.0, aspect=1.0):
    """Additive radial glow into float RGB buffer (values ~0..1). color in 0..1.
    Large radii are rendered analytically on the clipped ROI only (no giant sprite allocations)."""
    r = int(max(2, min(r, GLOW_MAX_RADIUS)))
    ry = max(1, int(min(r * aspect, GLOW_MAX_RADIUS)))
    if not (math.isfinite(x) and math.isfinite(y)):
        return
    x0, y0 = int(round(x)) - r, int(round(y)) - ry
    x1, y1 = x0 + 2 * r + 1, y0 + 2 * ry + 1
    hh, ww = fbuf.shape[:2]
    cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x1, ww), min(y1, hh)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    if r <= _GLOW_MAX_R and ry == r:
        s = glow_sprite(r)
        rr = s.shape[0] // 2
        if rr != r:  # quantised sprite → resize to the exact requested size (small arrays only)
            s = cv2.resize(s, (2 * r + 1, 2 * r + 1), interpolation=cv2.INTER_LINEAR)
        sub = s[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    else:
        # analytic falloff evaluated only inside the visible ROI
        yy = (np.arange(cy0, cy1, dtype=np.float32) - (y0 + ry)) / ry
        xx = (np.arange(cx0, cx1, dtype=np.float32) - (x0 + r)) / r
        d = np.sqrt(xx[None, :] ** 2 + yy[:, None] ** 2)
        sub = np.clip(1 - d, 0, 1) ** 2.2
    roi = fbuf[cy0:cy1, cx0:cx1]
    roi += sub[..., None] * (np.asarray(color, np.float32) * intensity)


def blit(canvas, rgb, alpha, x, y):
    """Alpha-blend rgb (uint8 h,w,3) with alpha (float32 h,w in 0..1) onto canvas (uint8) at int (x,y)."""
    h, w = alpha.shape[:2]
    hh, ww = canvas.shape[:2]
    x0, y0 = int(x), int(y)
    cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x0 + w, ww), min(y0 + h, hh)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    a = alpha[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0][..., None]
    src = rgb[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
    roi = canvas[cy0:cy1, cx0:cx1]
    roi[:] = (roi * (1 - a) + src * a).astype(np.uint8)


def blend_color(canvas, color, alpha):
    """Blend a flat color over canvas with a float32 alpha map (h,w)."""
    a = alpha[..., None]
    c = np.asarray(color, np.float32)
    canvas[:] = (canvas * (1 - a) + c * a).astype(np.uint8)


def overlay_alpha(canvas, weight):
    """Draw helper: returns a copy of canvas to draw semi-transparent things on, and a merge fn."""
    tmp = canvas.copy()

    def merge():
        cv2.addWeighted(tmp, weight, canvas, 1 - weight, 0, dst=canvas)

    return tmp, merge


# ----------------------------------------------------------------------------- camera

class Cam:
    """Pinhole camera. World units are metres; camera looks down +Z; Y grows downward.
    hy: screen row of the horizon (camera pitch); zoom multiplies the focal length."""

    def __init__(self, x=0.0, y=0.0, z=0.0, zoom=1.0, hy=AH * 0.5, dx=0.0, dy=0.0):
        self.x, self.y, self.z, self.zoom, self.hy = x, y, z, zoom, hy
        self.dx, self.dy = dx, dy  # handheld shake (screen px)

    @property
    def f(self):
        return F_PX * self.zoom

    def k(self, Z):
        return self.f / max(Z - self.z, 1e-3)

    def proj(self, X, Y, Z):
        k = self.k(Z)
        return CX + (X - self.x) * k + self.dx, self.hy + (Y - self.y) * k + self.dy, k

    def proj_pts(self, pts3):
        a = np.asarray(pts3, np.float64)
        dz = np.maximum(a[:, 2] - self.z, 1e-3)
        k = self.f / dz
        sx = CX + (a[:, 0] - self.x) * k + self.dx
        sy = self.hy + (a[:, 1] - self.y) * k + self.dy
        return np.stack([sx, sy], axis=1)

    def ground_y(self, Z, camH):
        return self.proj(0, camH, Z)[1]


def fog_amount(fog, dz):
    if fog is None:
        return 0.0
    return 1.0 - math.exp(-fog[1] * max(dz, 0.0))


def fog_color(fog):
    return np.asarray(fog[0], np.float32)


# ----------------------------------------------------------------------------- layers

class Layer:
    """A pre-rendered RGBA billboard standing in the world (top-left at X,Y, depth Z, width in metres)."""

    def __init__(self, rgb, alpha, X, Y, Z, width_m):
        self.rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
        a = alpha.astype(np.float32)
        if a.max() > 1.5:
            a = a / 255.0
        self.alpha = np.ascontiguousarray(a)
        self.X, self.Y, self.Z, self.width_m = float(X), float(Y), float(Z), float(width_m)
        self.ppm = self.rgb.shape[1] / self.width_m
        self.height_m = self.rgb.shape[0] / self.ppm
        self.mips = [(self.rgb, self.alpha)]
        r, al = self.rgb, self.alpha
        while min(r.shape[:2]) > 12:
            r = cv2.resize(r, (max(1, r.shape[1] // 2), max(1, r.shape[0] // 2)), interpolation=cv2.INTER_AREA)
            al = cv2.resize(al, (r.shape[1], r.shape[0]), interpolation=cv2.INTER_AREA)
            self.mips.append((r, al))

    def draw(self, canvas, cam, fog=None, tint=None, min_dz=0.35):
        dz = self.Z - cam.z
        if dz < min_dz:
            return
        k = cam.f / dz
        sx0 = CX + (self.X - cam.x) * k + cam.dx
        sy0 = cam.hy + (self.Y - cam.y) * k + cam.dy
        scale = k / self.ppm
        sw, sh = self.rgb.shape[1] * scale, self.rgb.shape[0] * scale
        x0, y0 = int(math.floor(sx0)), int(math.floor(sy0))
        x1, y1 = int(math.ceil(sx0 + sw)), int(math.ceil(sy0 + sh))
        hh, ww = canvas.shape[:2]
        cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x1, ww), min(y1, hh)
        if cx1 <= cx0 or cy1 <= cy0:
            return
        level = 0
        s = scale
        while s < 0.5 and level < len(self.mips) - 1:
            level += 1
            s *= 2
        rgb, alpha = self.mips[level]
        dw, dh = cx1 - cx0, cy1 - cy0
        M = np.array([[s, 0, sx0 - cx0], [0, s, sy0 - cy0]], np.float32)
        r = cv2.warpAffine(rgb, M, (dw, dh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        a = cv2.warpAffine(alpha, M, (dw, dh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        if fog is not None or tint is not None:
            rf = r.astype(np.float32)
            if tint is not None:
                rf *= np.asarray(tint, np.float32)
            if fog is not None:
                f = fog_amount(fog, dz)
                rf = rf * (1 - f) + fog_color(fog) * f
            r = np.clip(rf, 0, 255).astype(np.uint8)
        blit(canvas, r, a, cx0, cy0)


# ----------------------------------------------------------------------------- ground plane

class Ground:
    """Textured infinite ground plane at Y = camH below the camera, drawn with a perspective remap."""

    def __init__(self, tex, ppm, camH, fog=None, far_blur_from=14.0):
        self.tex = np.ascontiguousarray(tex, dtype=np.uint8)
        self.tex_blur = cv2.GaussianBlur(self.tex, (0, 0), 3)
        self.ppm = float(ppm)
        self.camH = float(camH)
        self.fog = fog
        self.far = far_blur_from
        self.th, self.tw = self.tex.shape[:2]
        self._xs = (np.arange(W, dtype=np.float32) - CX)

    def draw(self, canvas, cam, shade=None, u_off=0.0, v_off=0.0):
        hy = cam.hy + cam.dy
        y0 = int(max(0, math.floor(hy) + 2))
        if y0 >= AH:
            return
        ys = np.arange(y0, AH, dtype=np.float32)
        d = (self.camH - cam.y) * cam.f / (ys - hy)             # distance along Z for each row
        u = (self._xs[None, :] - cam.dx) * (d[:, None] / cam.f) + cam.x + u_off
        v = d[:, None] + cam.z + v_off + 0 * self._xs[None, :]
        map_x = ((u * self.ppm) % self.tw).astype(np.float32)
        map_y = ((-v * self.ppm) % self.th).astype(np.float32)
        far_rows = int(np.searchsorted(-d, -self.far))  # rows [0:far_rows) have d > far
        out = np.empty((len(ys), W, 3), np.uint8)
        if far_rows > 0:
            out[:far_rows] = cv2.remap(self.tex_blur, map_x[:far_rows], map_y[:far_rows], cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        if far_rows < len(ys):
            out[far_rows:] = cv2.remap(self.tex, map_x[far_rows:], map_y[far_rows:], cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        if self.fog is not None or shade is not None:
            of = out.astype(np.float32)
            if shade is not None:
                of *= shade[y0:AH][..., None] if shade.ndim == 2 else shade
            if self.fog is not None:
                f = (1 - np.exp(-self.fog[1] * np.maximum(d - 0, 0)))
                f = np.maximum(f, np.clip(1 - (ys - hy) / 14.0, 0, 1))[:, None, None]  # last rows before the horizon fully fogged
                of = of * (1 - f) + fog_color(self.fog) * f
            out = np.clip(of, 0, 255).astype(np.uint8)
        canvas[y0:AH] = out


# ----------------------------------------------------------------------------- sky

def sky_gradient(stops, cache=None):
    """Vertical gradient over the active area. stops: list of (row_fraction, color)."""
    ys = np.linspace(0, 1, AH, dtype=np.float32)
    outc = np.zeros((AH, 3), np.float32)
    fr = [s[0] for s in stops]
    for c in range(3):
        outc[:, c] = np.interp(ys, fr, [s[1][c] for s in stops])
    return np.repeat(outc[:, None, :], W, axis=1).astype(np.uint8)


# ----------------------------------------------------------------------------- post

_vig_cache = {}


def vignette_mask(strength=0.55, power=2.2):
    key = (strength, power)
    if key not in _vig_cache:
        y, x = np.mgrid[0:AH, 0:W].astype(np.float32)
        nx = (x - CX) / CX
        ny = (y - AH / 2) / (AH / 2)
        r = np.sqrt(nx * nx * 0.85 + ny * ny)
        m = 1 - strength * np.clip(r / 1.25, 0, 1) ** power
        _vig_cache[key] = m.astype(np.float32)[..., None]
    return _vig_cache[key]


def apply_grade(f, lift=(0, 0, 0), gain=(1, 1, 1), gamma=1.0, sat=1.0):
    f = f * np.asarray(gain, np.float32) + np.asarray(lift, np.float32)
    f = np.clip(f, 0, 1)
    if gamma != 1.0:
        f = np.power(f, 1.0 / gamma)
    if sat != 1.0:
        lum = f @ np.array([0.299, 0.587, 0.114], np.float32)
        f = lum[..., None] + (f - lum[..., None]) * sat
    return f


def bloom(f, threshold=0.62, amount=0.5, sigma=9):
    small = cv2.resize(f, (W // 4, AH // 4), interpolation=cv2.INTER_AREA)
    bright = np.clip(small - threshold, 0, None) * (1.0 / max(1e-3, 1 - threshold))
    bright = cv2.GaussianBlur(bright, (0, 0), sigma)
    up = cv2.resize(bright, (W, AH), interpolation=cv2.INTER_LINEAR)
    return f + up * amount


def grain(f, amount, rng):
    n = rng.standard_normal((AH // 2, W // 2), dtype=np.float32) * amount
    n = cv2.resize(n, (W, AH), interpolation=cv2.INTER_LINEAR)
    return f + n[..., None]


def handheld(t, amp, seed, freq=1.1):
    n1, n2 = Noise1D(seed), Noise1D(seed + 77)
    return (n1.signed(t * freq) * amp + n1.signed(t * 6.3 + 40) * amp * 0.15,
            n2.signed(t * freq * 0.9) * amp * 0.8 + n2.signed(t * 5.7 + 90) * amp * 0.12)
