"""Stateless particle & atmosphere effects. Everything is a pure function of time so frames can be
rendered out of order by several worker processes."""
from __future__ import annotations

import math
import numpy as np
import cv2

from .common import (W, AH, AA, P, PTS, Noise1D, col, clamp01, smooth, glow_sprite, draw_glow, blend_color,
                     fbm_tile, scrolled, overlay_alpha)


class Rain:
    def __init__(self, n=420, seed=1, speed=(900, 1500), length=(9, 22), wind=-120, color=(190, 205, 225)):
        r = np.random.default_rng(seed)
        self.x0 = r.random(n) * (W + 80) - 40
        self.y0 = r.random(n) * (AH + 60)
        self.v = r.uniform(*speed, n)
        self.len = r.uniform(*length, n)
        self.a = r.uniform(0.25, 0.8, n)
        self.wind = wind
        self.color = col(color)
        self.n = n

    def draw(self, canvas, t, density=1.0, weight=0.42):
        m = int(self.n * clamp01(density))
        if m <= 0:
            return
        tmp, merge = overlay_alpha(canvas, weight)
        y = (self.y0[:m] + self.v[:m] * t) % (AH + 60) - 30
        x = (self.x0[:m] + self.wind * t) % (W + 80) - 40
        dx = self.wind / self.v[:m] * self.len[:m]
        for i in range(m):
            cv2.line(tmp, P(x[i], y[i]), P(x[i] - dx[i], y[i] - self.len[i]), self.color, 1, AA, 4)
        merge()


class Snow:
    def __init__(self, n=380, seed=2, speed=(35, 110), wind=45, color=(235, 238, 245)):
        r = np.random.default_rng(seed)
        self.x0 = r.random(n) * (W + 120) - 60
        self.y0 = r.random(n) * (AH + 40)
        self.v = r.uniform(*speed, n)
        self.rad = r.uniform(0.8, 2.6, n)
        self.ph = r.random(n) * 6.283
        self.amp = r.uniform(8, 30, n)
        self.wind = wind
        self.color = col(color)
        self.n = n

    def draw(self, canvas, t, density=1.0, gust=0.0, weight=0.85):
        m = int(self.n * clamp01(density))
        tmp, merge = overlay_alpha(canvas, weight)
        y = (self.y0[:m] + self.v[:m] * t) % (AH + 40) - 20
        x = (self.x0[:m] + (self.wind + gust * 200) * t + np.sin(t * 1.3 + self.ph[:m]) * self.amp[:m]) % (W + 120) - 60
        for i in range(m):
            cv2.circle(tmp, P(x[i], y[i]), int(self.rad[i] * 16), self.color, -1, AA, 4)
        merge()


class Smoke:
    """Soft rising puffs from an emitter. origin: (x, y) screen px or callable(t)->(x, y)."""

    def __init__(self, origin, rate=6.0, life=4.0, rise=38.0, wind=14.0, size0=6.0, growth=9.0,
                 alpha0=0.28, color=(120, 120, 130), seed=3, turb=10.0):
        self.origin, self.rate, self.life, self.rise, self.wind = origin, rate, life, rise, wind
        self.size0, self.growth, self.alpha0, self.color, self.turb = size0, growth, alpha0, np.asarray(color, np.float32), turb
        self.n = int(rate * life) + 1
        r = np.random.default_rng(seed)
        self.jit = r.random((self.n, 3))
        self.noise = Noise1D(seed)

    def draw(self, fbuf_or_canvas, t, scale=1.0, strength=1.0):
        canvas = fbuf_or_canvas
        for i in range(self.n):
            b0 = i / self.rate
            if t < b0:
                continue
            age = (t - b0) % self.life
            birth = t - age
            ox, oy = self.origin(birth) if callable(self.origin) else self.origin
            u = age / self.life
            x = ox + (self.wind * age + math.sin(age * 1.7 + self.jit[i, 0] * 6.28) * self.turb * (0.3 + u)) * scale
            y = oy - self.rise * age * scale * (0.7 + 0.6 * self.jit[i, 1])
            r = (self.size0 + self.growth * age) * scale
            a = self.alpha0 * strength * (1 - u) ** 1.5 * min(1.0, age * 3) * (0.7 + 0.3 * self.jit[i, 2])
            if a < 0.01 or r < 1:
                continue
            s = glow_sprite(int(min(r, 400)))
            h, w = s.shape
            x0, y0 = int(x) - w // 2, int(y) - h // 2
            hh, ww = canvas.shape[:2]
            cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x0 + w, ww), min(y0 + h, hh)
            if cx1 <= cx0 or cy1 <= cy0:
                continue
            sub = s[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0][..., None] * a
            roi = canvas[cy0:cy1, cx0:cx1]
            if canvas.dtype == np.uint8:
                roi[:] = (roi * (1 - sub) + self.color * sub).astype(np.uint8)
            else:
                roi[:] = roi * (1 - sub) + (self.color / 255.0) * sub


class Sparks:
    def __init__(self, origin, n=40, seed=4, life=(0.5, 1.4), speed=(40, 140), spread=0.9, wind=20.0,
                 gravity=60.0, colors=((255, 200, 90), (255, 140, 40), (255, 240, 180))):
        r = np.random.default_rng(seed)
        self.origin = origin
        self.n = n
        self.life = r.uniform(*life, n)
        self.off = r.random(n)
        ang = -math.pi / 2 + r.uniform(-spread, spread, n)
        sp = r.uniform(*speed, n)
        self.vx, self.vy = np.cos(ang) * sp, np.sin(ang) * sp
        self.wind, self.g = wind, gravity
        self.colors = [col(c) for c in colors]
        self.ci = r.integers(0, len(colors), n)
        self.size = r.uniform(0.7, 1.8, n)

    def draw(self, canvas, t, scale=1.0, intensity=1.0):
        ox, oy = self.origin(t) if callable(self.origin) else self.origin
        for i in range(self.n):
            ph = ((t + self.off[i] * self.life[i]) / self.life[i]) % 1.0
            age = ph * self.life[i]
            x = ox + (self.vx[i] * age + self.wind * age * age) * scale
            y = oy + (self.vy[i] * age + 0.5 * self.g * age * age) * scale
            br = (1 - ph) ** 1.3 * intensity * (0.6 + 0.4 * math.sin(age * 40 + i))
            if br < 0.08:
                continue
            c = tuple(int(v * br) for v in self.colors[self.ci[i]])
            cv2.circle(canvas, P(x, y), int(max(0.6, self.size[i] * scale) * 16), c, -1, AA, 4)


class Dust:
    """Slowly drifting motes that twinkle in light."""

    def __init__(self, n=90, seed=5, region=(0, 0, W, AH), color=(255, 225, 170), rad=(0.8, 2.0)):
        r = np.random.default_rng(seed)
        x0, y0, x1, y1 = region
        self.x = r.uniform(x0, x1, n)
        self.y = r.uniform(y0, y1, n)
        self.ph = r.random((n, 3)) * 6.283
        self.amp = r.uniform(6, 26, n)
        self.rad = r.uniform(*rad, n)
        self.drift = r.uniform(-8, 8, n)
        self.color = col(color)
        self.n = n
        self.region = region

    def draw(self, canvas, t, weight=0.7, drift_y=-6.0):
        tmp, merge = overlay_alpha(canvas, weight)
        x0, y0, x1, y1 = self.region
        for i in range(self.n):
            x = x0 + (self.x[i] - x0 + self.drift[i] * t + math.sin(t * 0.7 + self.ph[i, 0]) * self.amp[i]) % max(1, x1 - x0)
            y = y0 + (self.y[i] - y0 + drift_y * t + math.cos(t * 0.5 + self.ph[i, 1]) * self.amp[i] * 0.4) % max(1, y1 - y0)
            tw = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 2.3 + self.ph[i, 2]))
            c = tuple(int(v * tw) for v in self.color)
            cv2.circle(tmp, P(x, y), int(self.rad[i] * 16), c, -1, AA, 4)
        merge()


class Fog:
    """Two scrolling layers of tileable noise blended as a colored haze."""

    def __init__(self, seed=6, color=(150, 165, 185), scale=1.0):
        self.t1 = fbm_tile(AH, W, octaves=4, seed=seed, base=3)
        self.t2 = fbm_tile(AH, W, octaves=4, seed=seed + 1, base=5)
        self.color = color

    def alpha(self, t, speed=(18, -6), speed2=(-11, 4), lo=0.35, hi=0.9, gain=0.5):
        a = scrolled(self.t1, speed[0] * t, speed[1] * t) * 0.6 + scrolled(self.t2, speed2[0] * t, speed2[1] * t) * 0.4
        a = np.clip((a - lo) / (hi - lo), 0, 1)
        return (a * gain).astype(np.float32)

    def draw(self, canvas, t, gain=0.5, vfade=None, **kw):
        a = self.alpha(t, gain=gain, **kw)
        if vfade is not None:
            a *= vfade
        blend_color(canvas, self.color, a)


def vertical_fade(y_top, y_full, y_end=None, y_zero=None):
    """Alpha profile (AH, W): 0 above y_top, 1 between y_full..y_end, back to 0 at y_zero."""
    ys = np.arange(AH, dtype=np.float32)
    a = np.clip((ys - y_top) / max(1, y_full - y_top), 0, 1)
    if y_end is not None and y_zero is not None:
        a *= 1 - np.clip((ys - y_end) / max(1, y_zero - y_end), 0, 1)
    return np.repeat(a[:, None], W, axis=1)


def god_rays(source=(W + 200, -300), n=7, seed=7, width=(30, 90), length=1900, blur=41):
    """Pre-rendered light shafts mask (float32 AH x W in 0..1)."""
    r = np.random.default_rng(seed)
    m = np.zeros((AH, W), np.float32)
    sx, sy = source
    for i in range(n):
        ang = math.atan2(AH * 0.7 - sy, W * 0.25 - sx) + r.uniform(-0.28, 0.28)
        w = r.uniform(*width)
        ex, ey = sx + math.cos(ang) * length, sy + math.sin(ang) * length
        nx, ny = -math.sin(ang) * w / 2, math.cos(ang) * w / 2
        poly = np.array([[sx + nx * 0.2, sy + ny * 0.2], [sx - nx * 0.2, sy - ny * 0.2], [ex - nx, ey - ny], [ex + nx, ey + ny]])
        cv2.fillPoly(m, [PTS(poly)], float(r.uniform(0.5, 1.0)), AA, 4)
    m = cv2.GaussianBlur(m, (0, 0), blur)
    return m / max(m.max(), 1e-6)


def flame(canvas, x, y, h, t, seed=0, sway=1.0, colors=((255, 110, 20), (255, 185, 60), (255, 245, 200))):
    """Flickering teardrop flame with base at (x, y), height h px."""
    n = Noise1D(seed)
    tip_dx = n.signed(t * 7.0) * 0.28 * h * sway
    hh = h * (0.85 + 0.3 * n(t * 11.0 + 5))
    rx = 0.30 * h * (0.85 + 0.3 * n(t * 9.0 + 9))
    for k, c in zip((1.0, 0.62, 0.32), colors):
        pts_r, pts_l = [], []
        for i in range(9):
            u = i / 8
            wdt = rx * k * math.sin(math.pi * u) ** 0.55 * (1 - 0.35 * u)
            cxp = x + tip_dx * u * u
            yy = y - hh * k * u - (h * (1 - k) * 0.08)
            pts_r.append((cxp + wdt, yy))
            pts_l.append((cxp - wdt, yy))
        poly = pts_r + pts_l[::-1]
        cv2.fillPoly(canvas, [PTS(poly)], col(c), AA, 4)


def torch_light(t, seed):
    n = Noise1D(seed)
    return 0.72 + 0.28 * (0.5 * n(t * 9.0) + 0.5 * n(t * 23.0 + 3))


def birds(canvas, t, origin, n=7, seed=8, speed=(90, 30), size=7, color=(30, 28, 32)):
    r = np.random.default_rng(seed)
    offs = r.uniform(-60, 60, (n, 2))
    flap = r.random(n) * 6.28
    ox, oy = origin
    for i in range(n):
        x = ox + speed[0] * t + offs[i, 0] + math.sin(t * 0.8 + i) * 6
        y = oy + speed[1] * t + offs[i, 1] * 0.5 + math.sin(t * 1.1 + i) * 4
        if x < -40 or x > W + 40 or y < -40 or y > AH + 40:
            continue
        w = math.sin(t * 9 + flap[i]) * size * 0.7
        pts = [(x - size, y - w), (x, y + w * 0.3), (x + size, y - w)]
        cv2.polylines(canvas, [PTS(pts)], False, col(color), 2, AA, 4)


def cloud_layer(seed=9):
    return fbm_tile(AH // 2, W, octaves=5, seed=seed, base=3)


def draw_clouds(canvas, tile, t, hy, color=(170, 178, 195), speed=9.0, lo=0.5, hi=0.85, gain=0.55):
    """Blend drifting clouds over the sky region above the horizon row hy."""
    h = tile.shape[0]
    a = scrolled(tile, speed * t, 0)
    a = np.clip((a - lo) / (hi - lo), 0, 1) * gain
    rows = int(min(AH, max(0, hy)))
    if rows <= 0:
        return
    a = cv2.resize(a, (W, rows), interpolation=cv2.INTER_LINEAR)
    fade = np.linspace(1, 0.15, rows, dtype=np.float32)[:, None]
    a = (a * fade).astype(np.float32)
    region = canvas[:rows]
    blend_color(region, color, a)
