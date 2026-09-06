"""Shots S1–S6: cold open, title, Troffea, time-lapse, cathedral square, council chamber."""
from __future__ import annotations

import math
import numpy as np
import cv2

from .common import (W, AH, CX, AA, P, PTS, Cam, Layer, Ground, sky_gradient, kf, lerp, mix, col, clamp, clamp01,
                     smooth, smoothstep, ease_in, ease_out, bump, draw_glow, blend_color, handheld, Noise1D, fbm_tile,
                     scrolled, overlay_alpha)
from . import fx
from . import world as wd
from . import characters as ch
from .text import draw_text


class Scene:
    """Base: subclasses implement build() (lazy, per process) and draw(t, ctx)."""
    name = "scene"
    grade = dict(lift=(0, 0, 0), gain=(1, 1, 1), gamma=1.0, sat=1.0, bloom=0.35, grain=0.035, vignette=0.55)

    def __init__(self, dur, seed=1):
        self.dur = float(dur)
        self.seed = seed
        self._built = False

    def ensure(self):
        if not self._built:
            self.build()
            self._built = True

    def build(self):
        pass

    def render(self, t):
        self.ensure()
        canvas = np.zeros((AH, W, 3), np.uint8)
        fbuf = np.zeros((AH, W, 3), np.float32)
        ctx = dict(canvas=canvas, fbuf=fbuf, captions=[])
        self.draw(t, ctx)
        return canvas, fbuf, ctx["captions"]

    def draw(self, t, ctx):
        raise NotImplementedError


def figure_shadow(canvas, px, py, k, light_dir=(0.6, 0.25), length=1.0, alpha=0.35, sq=1.0):
    """Soft contact shadow + cast shadow streak at the feet of a figure whose ground point is (px, py)."""
    tmp, merge = overlay_alpha(canvas, alpha)
    cv2.ellipse(tmp, P(px, py), (int(0.32 * k * 16 * sq), int(0.08 * k * 16)), 0, 0, 360, (8, 8, 10), -1, AA, 4)
    if length > 0:
        ex, ey = px + light_dir[0] * k * length, py + light_dir[1] * k * length * 0.25
        cv2.line(tmp, P(px, py), P(ex, ey), (8, 8, 10), max(2, int(0.16 * k)), AA, 4)
    merge()


def draw_window_lights(canvas, fbuf, cam, windows, t, warm=(255, 190, 110), gain=1.0, fog=None):
    for w in windows:
        if not w["lit"]:
            continue
        dz = 0.5 * (w["z0"] + w["z1"]) - cam.z
        if dz < 0.6:
            continue
        n = Noise1D(w["seed"])
        fl = 0.55 + 0.45 * (0.5 * n(t * 6) + 0.5 * n(t * 17 + 3))
        pts = [cam.proj(w["x"], w["y0"], w["z0"])[:2], cam.proj(w["x"], w["y0"], w["z1"])[:2],
               cam.proj(w["x"], w["y1"], w["z1"])[:2], cam.proj(w["x"], w["y1"], w["z0"])[:2]]
        c = tuple(v * fl * gain for v in warm)
        if fog is not None:
            f = 1 - math.exp(-fog[1] * dz)
            c = mix(c, fog[0], f * 0.8)
        cv2.fillPoly(canvas, [PTS(pts)], col(c), AA, 4)
        cx = sum(p[0] for p in pts) / 4
        cy = sum(p[1] for p in pts) / 4
        r = max(6, abs(pts[1][0] - pts[0][0]) * 2.2 + 8)
        draw_glow(fbuf, cx, cy, r, (1.0, 0.7, 0.35), 0.22 * fl * gain * (1 - (0.7 * (1 - math.exp(-fog[1] * dz)) if fog else 0)))


def lantern(canvas, fbuf, cam, X, Y, Z, t, seed, swing=1.0, lit=True, fog=None):
    """Hanging lantern on a short chain from (X, Y, Z); swings in the wind."""
    n = Noise1D(seed)
    ang = (0.18 * math.sin(t * 1.9 + seed) + 0.08 * n.signed(t * 0.7)) * swing
    L = 0.55
    bx, by, bz = X + math.sin(ang) * L, Y + math.cos(ang) * L, Z
    dz = Z - cam.z
    if dz < 0.7:
        return
    top = cam.proj(X, Y, Z)
    bot = cam.proj(bx, by, bz)
    k = bot[2]
    f = (1 - math.exp(-fog[1] * dz)) if fog else 0.0
    dark = col(mix((40, 34, 28), fog[0] if fog else (0, 0, 0), f))
    cv2.line(canvas, P(top[0], top[1]), P(bot[0], bot[1]), dark, max(1, int(0.02 * k)), AA, 4)
    w, h = 0.22 * k, 0.32 * k
    cv2.rectangle(canvas, P(bot[0] - w / 2, bot[1]), P(bot[0] + w / 2, bot[1] + h), dark, -1, AA, 4)
    if lit:
        fl = 0.7 + 0.3 * n(t * 9 + 20)
        glass = col(mix((255, 196, 120), fog[0] if fog else (0, 0, 0), f * 0.8))
        cv2.rectangle(canvas, P(bot[0] - w * 0.32, bot[1] + h * 0.15), P(bot[0] + w * 0.32, bot[1] + h * 0.85), tuple(int(v * fl) for v in glass), -1, AA, 4)
        draw_glow(fbuf, bot[0], bot[1] + h / 2, max(10, 1.6 * k), (1.0, 0.72, 0.38), 0.55 * fl * (1 - 0.7 * f))
        # reflection on wet ground
        gy = cam.proj(bx, 1.6, bz)[1]
        draw_glow(fbuf, bot[0], gy, max(8, 0.9 * k), (1.0, 0.7, 0.35), 0.16 * fl * (1 - 0.7 * f), aspect=2.2)
    cv2.rectangle(canvas, P(bot[0] - w * 0.6, bot[1] - 0.04 * k), P(bot[0] + w * 0.6, bot[1] + 0.03 * k), dark, -1, AA, 4)


def street_common_build(self, seed, snow=0.0, z_from=2.0, z_to=70.0, half_w=3.3):
    self.ground_y = 1.6
    self.half_w = half_w
    self.facades, self.windows, self.chimneys = wd.build_street(seed=seed, z_from=z_from, z_to=z_to, half_w=half_w, ground_y=self.ground_y, snow=snow)
    self.cathedral = wd.cathedral_layer(ppm=6, X=-12.0, Z=95.0, ground_y=self.ground_y, color=(40, 42, 56))
    self.clouds = fx.cloud_layer(seed + 3)


# =============================================================================== S1  cold open

class S1_ColdOpen(Scene):
    name = "S1"
    grade = dict(lift=(0.0, 0.01, 0.03), gain=(0.92, 0.98, 1.1), gamma=1.05, sat=0.85, bloom=0.5, grain=0.05, vignette=0.6)

    def build(self):
        street_common_build(self, seed=11)
        self.ground = Ground(wd.cobble_tile(seed=3, wet=0.9), ppm=128, camH=self.ground_y, fog=((22, 28, 42), 0.05))
        self.rain = fx.Rain(n=520, seed=4, wind=-140)
        self.fog = fx.Fog(seed=5, color=(70, 82, 110))
        self.smokes = [fx.Smoke((0, 0), rate=5, life=5, rise=26, wind=10, size0=5, growth=7, alpha0=0.22, color=(90, 96, 112), seed=i) for i in range(3)]
        self.walker_pal = dict(tunic=(28, 26, 30), hose=(22, 20, 24), skin=(40, 34, 30), hair=(20, 18, 16), cover=(30, 28, 30), skirt=None)
        self.sky = sky_gradient([(0, (8, 12, 24)), (0.45, (22, 30, 52)), (0.75, (40, 48, 70)), (1, (46, 52, 74))])
        self.dust = fx.Dust(n=40, seed=6, color=(150, 170, 200), rad=(0.6, 1.4))
        self.lanterns = []
        rng = np.random.default_rng(7)
        for f in self.facades:
            if f.z0 > 4 and f.z0 < 40 and rng.random() < 0.35:
                self.lanterns.append((f.x - f.meta["side"] * 0.9, self.ground_y - 3.4, f.z0 + f.meta["w"] * 0.5, int(rng.integers(0, 1000))))
        self.lanterns.sort(key=lambda l: -l[2])
        self.fogp = ((30, 38, 58), 0.045)

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        d = self.dur
        u = t / d
        # camera: slow dolly in, gentle handheld
        z = kf([(0, 0.0), (d, 5.5)], t, linear=True)
        zoom = kf([(0, 1.0), (d, 1.1)], t)
        dx, dy = handheld(t, 4.0, 1)
        cam = Cam(x=0.15 * math.sin(t * 0.2), y=0.0, z=z, zoom=zoom, hy=AH * 0.50, dx=dx, dy=dy)
        fog = self.fogp
        canvas[:] = self.sky
        # moon + clouds
        wd.moon(fbuf, W * 0.78 + dx * 0.2, AH * 0.16 + dy * 0.2, 16, brightness=0.9)
        fx.draw_clouds(canvas, self.clouds, t, cam.hy + 10, color=(30, 36, 54), speed=7, lo=0.45, hi=0.85, gain=0.8)
        # far cathedral silhouette
        self.cathedral.draw(canvas, cam, fog=((36, 44, 66), 0.02))
        # street
        self.ground.draw(canvas, cam)
        for f in self.facades:
            f.draw(canvas, cam, fog=fog, tint=(0.36, 0.40, 0.55))
        draw_window_lights(canvas, fbuf, cam, self.windows, t, gain=0.9, fog=fog)
        # chimney smoke (screen-space emitters)
        for i, (cx_, cy_, cz_) in enumerate(self.chimneys[:3]):
            if cz_ - cam.z < 8:
                continue
            sx, sy, k = cam.proj(cx_, cy_, cz_)
            self.smokes[i].origin = (sx, sy)
            self.smokes[i].draw(canvas, t, scale=clamp(k / 60, 0.3, 1.2), strength=0.8)
        # lanterns
        for (lx, ly, lz, sd) in self.lanterns:
            lantern(canvas, fbuf, cam, lx, ly, lz, t, sd, swing=1.0 - 0.4 * u, fog=fog)
        # distant walker with lantern, walking away and dissolving into fog
        wz = 14 + 1.1 * t
        wx = 0.6 + 0.3 * math.sin(t * 0.3)
        p = ch.walk(t, freq=1.5, stride=0.5, ph=0.3, lean=0.1, armswing=0.3)
        res = ch.place_figure(canvas, cam, wx, wz, p, ch.shade_palette(self.walker_pal, fog=1 - math.exp(-fog[1] * (wz - cam.z)), fogc=fog[0]),
                              self.ground_y, facing=1, hood=True, prop="lantern")
        if res:
            px, py, k = res
            fl = 0.75 + 0.25 * math.sin(t * 7)
            fa = math.exp(-fog[1] * (wz - cam.z))
            draw_glow(fbuf, px + 0.3 * k, py - 0.1 * k, max(8, 1.8 * k), (1.0, 0.7, 0.35), 0.5 * fl * fa)
        # rain fading out over the first 9 s, drips remain
        rain_d = kf([(0, 0.85), (6, 0.45), (9.5, 0.0)], t)
        if rain_d > 0:
            self.rain.draw(canvas, t, density=rain_d, weight=0.35)
        # ground mist
        vf = fx.vertical_fade(cam.hy - 10, cam.hy + 120)
        self.fog.draw(canvas, t, gain=0.42, vfade=vf, lo=0.3, hi=0.9)
        self.dust.draw(canvas, t, weight=0.35)
        ctx["captions"].append(("caption", "斯特拉斯堡 · 1518年7月", kf([(1.0, 0), (2.2, 1), (7.5, 1), (8.8, 0)], t)))


# =============================================================================== S2  title

class S2_Title(Scene):
    name = "S2"
    grade = dict(lift=(0, 0, 0), gain=(1, 1, 1), gamma=1.0, sat=1.0, bloom=0.6, grain=0.06, vignette=0.7)

    def build(self):
        self.fog = fx.Fog(seed=21, color=(120, 110, 100))
        self.dust = fx.Dust(n=120, seed=22, color=(255, 220, 170), rad=(0.6, 2.2))

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        canvas[:] = (6, 5, 6)
        self.fog.draw(canvas, t, gain=0.22, lo=0.35, hi=0.95, speed=(25, -4), speed2=(-16, 8))
        draw_glow(fbuf, CX, AH * 0.45, 420, (0.45, 0.32, 0.2), 0.16 * smoothstep(0, 1.2, t))
        self.dust.draw(canvas, t, weight=0.55)
        a1 = smoothstep(0.2, 1.4, t) * (1 - smoothstep(self.dur - 0.9, self.dur - 0.2, t))
        a2 = smoothstep(0.9, 2.0, t) * (1 - smoothstep(self.dur - 0.8, self.dur - 0.15, t))
        sp = int(10 + 14 * smoothstep(0, 3.5, t))
        draw_text(canvas, "1518", CX, AH * 0.36, size=150, serif=True, color=(214, 196, 168), opacity=a1, spacing=sp)
        draw_text(canvas, "没有音乐的舞蹈", CX, AH * 0.62, size=52, serif=True, color=(226, 214, 196), opacity=a2, spacing=8)
        draw_text(canvas, "斯特拉斯堡跳舞瘟疫", CX, AH * 0.76, size=26, serif=False, color=(150, 140, 128), opacity=a2, spacing=6)


# =============================================================================== S3  Troffea

class S3_Troffea(Scene):
    name = "S3"
    grade = dict(lift=(0.02, 0.01, 0.0), gain=(1.08, 1.0, 0.9), gamma=1.0, sat=0.9, bloom=0.4, grain=0.035, vignette=0.5)

    def build(self):
        street_common_build(self, seed=11)
        self.ground = Ground(wd.cobble_tile(seed=3, wet=0.15, warm=0.6), ppm=128, camH=self.ground_y, fog=((190, 176, 150), 0.02))
        self.sky = sky_gradient([(0, (130, 150, 175)), (0.5, (200, 190, 170)), (1, (225, 205, 175))])
        self.rays = fx.god_rays(source=(W * 0.15, -200), n=6, seed=31, width=(40, 120), length=1700)
        self.dust = fx.Dust(n=110, seed=32, color=(255, 232, 190), rad=(0.6, 1.8))
        self.fogp = ((196, 182, 156), 0.02)
        self.bg_cache = None
        # neighbours
        self.n_pal1 = ch.palette(1)
        self.n_pal2 = ch.palette(3)
        self.n_pal3 = ch.palette(6)
        self.door_z = 6.2

    # Troffea's trajectory (world X, Z, facing, pose)
    def troffea(self, t):
        # 0-2.2 s: walks out from the right facade to the street centre; 2.2-3.4 stands; 3.4-5 twitches; then full dance
        if t < 2.2:
            u = t / 2.2
            x = lerp(2.5, 0.9, u)
            z = lerp(self.door_z, self.door_z + 1.2, u)
            p = ch.walk(t, freq=1.7, stride=0.5, ph=0.2, lean=0.08)
            return x, z, -1, p
        x, z = 0.9, self.door_z + 1.2
        if t < 3.4:
            u = (t - 2.2) / 1.2
            p = ch.blend(ch.walk(2.2, freq=1.7, stride=0.5, ph=0.2, lean=0.08), ch.idle(t, amp=1.5), smooth(u * 2))
            return x, z, -1, p
        if t < 5.2:
            u = (t - 3.4) / 1.8
            tw = ch.idle(t, amp=1.5)
            tw["sL"] += 0.9 * u * max(0.0, math.sin(t * 13)) ** 2
            tw["head"] += 0.25 * u * math.sin(t * 9)
            tw["lean"] += 0.15 * u * math.sin(t * 7)
            dp = ch.dance(t, ph=0.4, intensity=0.9, style=0)
            return x, z, -1, ch.blend(tw, dp, ease_in(u))
        wob = 0.35 * math.sin(t * 0.9)
        return x + wob, z + 0.2 * math.sin(t * 0.6), -1 if math.cos(t * 0.45) > -0.3 else 1, ch.dance(t, ph=0.4, intensity=1.0, style=0 if (t % 6) < 4 else 2)

    def draw_wide(self, t, canvas, fbuf, cam):
        fog = self.fogp
        canvas[:] = self.sky
        fx.draw_clouds(canvas, self.clouds, t, cam.hy, color=(235, 228, 215), speed=10, lo=0.5, hi=0.9, gain=0.6)
        self.cathedral.draw(canvas, cam, fog=((200, 190, 170), 0.02))
        self.ground.draw(canvas, cam)
        for f in self.facades:
            f.draw(canvas, cam, fog=fog, tint=(1.0, 0.94, 0.86))
        # laundry line between facades at Z = 9.5
        zl = 9.5
        if zl - cam.z > 1.0:
            a = cam.proj(-self.half_w + 0.1, self.ground_y - 4.2, zl)
            b = cam.proj(self.half_w - 0.1, self.ground_y - 4.0, zl)
            k = a[2]
            cv2.line(canvas, P(a[0], a[1] + 6 * math.sin(t)), P(b[0], b[1]), (60, 50, 42), max(1, int(0.015 * k)), AA, 4)
            for i, (u0, wdt, cc) in enumerate(((0.18, 0.11, (214, 208, 196)), (0.42, 0.14, (150, 120, 100)), (0.68, 0.10, (200, 190, 170)))):
                x0 = a[0] + (b[0] - a[0]) * u0
                x1 = a[0] + (b[0] - a[0]) * (u0 + wdt)
                y0 = a[1] + (b[1] - a[1]) * u0
                h = 0.75 * k
                sway = 0.25 * k * math.sin(t * 2.1 + i * 1.7) + 0.1 * k * math.sin(t * 5.3 + i)
                poly = [(x0, y0), (x1, y0), (x1 + sway, y0 + h), (x0 + sway * 1.2, y0 + h * 0.97)]
                cv2.fillPoly(canvas, [PTS(poly)], cc, AA, 4)
        # figures sorted far → near
        tx, tz, tf, tp = self.troffea(t)
        figs = [(tz, tx, tp, ch.TROFFEA, tf, {})]
        # neighbour 1: standing at a door, turns to look after 3 s
        f1 = 1 if t < 3.0 else -1
        p1 = ch.idle(t, ph=1.0)
        if 2.6 < t < 3.6:
            p1["head"] += 0.3 * bump(t - 2.6, 1.0)
        if t > 5.5:
            p1["sL"] = 1.0 + 0.2 * math.sin(t * 2)
            p1["eL"] = 1.3
        figs.append((11.5, -2.6, p1, self.n_pal1, f1, {}))
        # neighbour 2: walking towards camera, stops and stares
        if t < 6.0:
            z2 = 20 - 1.2 * t
            p2 = ch.walk(t, freq=1.6, stride=0.5, ph=1.0)
        else:
            z2 = 20 - 1.2 * 6.0
            p2 = ch.blend(ch.walk(6.0, freq=1.6, stride=0.5, ph=1.0), ch.idle(t, ph=2.0), smooth((t - 6.0) / 0.8))
            p2["head"] += 0.15
        figs.append((z2, 2.2, p2, self.n_pal2, -1, {}))
        # neighbour 3 (child) far, running across at t 6-9
        if 6 < t < 9.5:
            x3 = lerp(-3.0, 3.0, (t - 6) / 3.5)
            p3 = ch.walk(t, freq=2.6, stride=0.7, lean=0.15)
            figs.append((16.0, x3, p3, self.n_pal3, 1, {}))
        figs.sort(key=lambda f: -f[0])
        light_dir = (0.7, 0.3)
        for (z_, x_, p_, pal_, fc_, kw) in figs:
            gp = cam.proj(x_, self.ground_y, z_)
            figure_shadow(canvas, gp[0], gp[1], gp[2], light_dir=light_dir, length=1.3, alpha=0.3)
            fz = 1 - math.exp(-fog[1] * (z_ - cam.z))
            ch.place_figure(canvas, cam, x_, z_, p_, ch.shade_palette(pal_, fog=fz, fogc=fog[0]), self.ground_y, facing=fc_, **kw)
        # birds startled when she starts dancing
        if 4.6 < t < 9:
            fx.birds(canvas, t - 4.6, (W * 0.62, AH * 0.42), n=6, seed=33, speed=(120, -70), size=4, color=(70, 62, 60))
        # light shafts + dust
        ray = (self.rays * (0.10 + 0.03 * math.sin(t * 0.7)))[..., None]
        fbuf += ray * np.array([1.0, 0.85, 0.6], np.float32)
        self.dust.draw(canvas, t, weight=0.5)

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        cut = 8.2
        if t < cut:
            tx, tz, _, _ = self.troffea(t)
            z = kf([(0, 0.0), (2.2, 0.6), (cut, 2.4)], t)
            zoom = kf([(0, 1.05), (5.0, 1.15), (cut, 1.32)], t)
            dx, dy = handheld(t, 3.0, 3)
            cam = Cam(x=kf([(0, 0.4), (2.2, 0.25), (cut, 0.05)], t) + tx * 0.35, y=-0.1, z=z, zoom=zoom, hy=AH * 0.47, dx=dx, dy=dy)
            self.draw_wide(t, canvas, fbuf, cam)
            return
        # ---- close-up on Troffea's face (shallow focus, background = blurred street, slow push in)
        if self.bg_cache is None:
            bg = np.zeros((AH, W, 3), np.uint8)
            bgf = np.zeros((AH, W, 3), np.float32)
            cam = Cam(x=0.3, y=-0.1, z=3.0, zoom=1.6, hy=AH * 0.47)
            self.draw_wide(cut, bg, bgf, cam)
            small = cv2.resize(bg, (W // 4, AH // 4), interpolation=cv2.INTER_AREA)
            small = cv2.GaussianBlur(small, (0, 0), 5)
            self.bg_cache = cv2.resize(small, (W, AH), interpolation=cv2.INTER_LINEAR)
        u = (t - cut) / max(0.1, self.dur - cut)
        s = 1.0 + 0.08 * u
        M = np.array([[s, 0, CX * (1 - s)], [0, s, AH * 0.45 * (1 - s)]], np.float32)
        canvas[:] = cv2.warpAffine(self.bg_cache, M, (W, AH), borderMode=cv2.BORDER_REFLECT)
        # face
        tt = t - cut
        expr = "blank" if tt < 2.2 else "fear"
        turn = 0.25 * math.sin(tt * 0.8)
        cx = CX + 40 + 18 * math.sin(tt * 2.3) + 4 * math.sin(tt * 17)
        cy = AH * 0.50 + 12 * math.sin(tt * 3.1) + 3 * math.sin(tt * 23)
        r = 118 * (1 + 0.05 * u)
        # shoulders
        cv2.ellipse(canvas, P(cx, cy + r * 2.4), (int(r * 1.9 * 16), int(r * 0.9 * 16)), 0, 180, 360, col(ch.TROFFEA["tunic"]), -1, AA, 4)
        ch.draw_head_closeup(canvas, cx, cy, r, tt, ch.TROFFEA, expr, cover=True, look=(0.25 * math.sin(tt * 1.7), -0.1),
                             gaze_dart=1.0 if tt > 1.5 else 0.3, seed=5, turn=turn, tremble=0.6 + 0.4 * u)
        # warm key light from the left + dust
        draw_glow(fbuf, cx - r * 1.4, cy - r * 0.8, r * 3.2, (1.0, 0.85, 0.6), 0.10)
        self.dust.draw(canvas, t, weight=0.45)


# =============================================================================== S4  time-lapse

class S4_TimeLapse(Scene):
    name = "S4"
    grade = dict(lift=(0.0, 0.0, 0.0), gain=(1.0, 0.98, 0.94), gamma=1.0, sat=0.85, bloom=0.35, grain=0.04, vignette=0.6)

    def build(self):
        self.ground_y = 1.6
        self.facades, self.windows, self.chimneys = wd.build_street(seed=11, z_from=8.0, z_to=40.0, half_w=3.3, ground_y=self.ground_y)
        self.ground = Ground(wd.cobble_tile(seed=3, wet=0.0, warm=0.4), ppm=128, camH=self.ground_y, fog=None, far_blur_from=60)
        self.cloud_shadow = fbm_tile(AH, W, octaves=4, seed=41, base=2)
        rng = np.random.default_rng(42)
        # dancers appear over time inside the visible patch X ∈ [-3, 3], Z ∈ [11, 20]
        self.dancers = []
        n = 44
        for i in range(n):
            x = float(rng.uniform(-2.9, 2.9))
            z = float(rng.uniform(11.5, 20.5))
            self.dancers.append(dict(x=x, z=z, style=int(rng.integers(0, 4)), ph=float(rng.random() * 6.28), pal=ch.palette(int(rng.integers(0, 8)), rng),
                                     facing=int(rng.choice([-1, 1])), speed=float(rng.uniform(0.85, 1.15)), wander=float(rng.uniform(0.2, 0.7))))

    @staticmethod
    def daycycle(u):
        """u in [0,1) → (sky tint rgb 0..1 multipliers, light dir, shadow len, ambient)."""
        # 0=dawn, .25=noon, .5=dusk, .75=midnight
        ang = u * 2 * math.pi
        sun_h = math.sin(ang)  # -1..1 (>0 day)
        day = clamp01(sun_h * 1.6 + 0.2)
        warm = clamp01(1 - abs(sun_h) * 2.2)  # golden at dawn/dusk
        tint = mix(mix((0.16, 0.20, 0.34), (1.0, 0.98, 0.94), day), (1.05, 0.82, 0.62), warm * day * 0.7)
        ld = (math.cos(ang) * 1.6, 0.35)
        sl = clamp(0.35 / max(0.15, sun_h), 0.4, 3.0) if sun_h > 0 else 0.0
        return tint, ld, sl, day

    def count_at(self, t):
        # 1 → 5 → 12 → 34 → 44 over the shot
        return int(kf([(0, 1), (2.8, 1), (3.0, 5), (5.4, 5), (5.6, 12), (8.0, 12), (8.2, 34), (10.5, 34), (10.7, 44)], t, linear=True))

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        d = self.dur
        cycles = 3.0
        u = (t / d) * cycles + 0.1
        tint, ld, sl, day = self.daycycle(u % 1.0)
        # high, steep camera; slow crane up + pull back
        cam = Cam(x=0.3 * math.sin(t * 0.15), y=kf([(0, -11.0), (d, -14.5)], t), z=0.0, zoom=kf([(0, 1.25), (d, 0.95)], t), hy=kf([(0, -760), (d, -640)], t))
        canvas[:] = col(tuple(v * 150 for v in tint))
        shade = np.ones((AH,), np.float32)
        self.ground.draw(canvas, cam, shade=None)
        # tint ground + drifting cloud shadows
        cs = scrolled(self.cloud_shadow, 30 * t, 8 * t)
        cs = 1 - 0.35 * day * np.clip((cs - 0.5) / 0.3, 0, 1)
        gf = canvas.astype(np.float32) * np.asarray(tint, np.float32) * cs[..., None]
        canvas[:] = np.clip(gf, 0, 255).astype(np.uint8)
        # facades along the edges (steep perspective)
        for f in self.facades:
            f.draw(canvas, cam, fog=None, tint=tuple(v * 0.9 for v in tint), zmin=7.5)
        # lit windows at night
        night = 1 - day
        if night > 0.05:
            draw_window_lights(canvas, fbuf, cam, self.windows, t, gain=night)
        n = self.count_at(t)
        figs = self.dancers[:n]
        figs = sorted(figs, key=lambda f: -f["z"])
        for i, f in enumerate(figs):
            ph = f["ph"]
            wob = f["wander"]
            x = f["x"] + wob * math.sin(t * 0.7 * f["speed"] + ph)
            z = f["z"] + wob * 0.6 * math.cos(t * 0.5 * f["speed"] + ph)
            exhaust = clamp01((t - 6) / 12) * 0.6 if i % 3 == 0 else 0.0
            p = ch.dance(t * f["speed"], ph=ph, intensity=1.0, style=f["style"], exhaust=exhaust) if i > 0 else ch.dance(t, ph=0.4, style=0)
            pal = ch.TROFFEA if i == n - 1 and i == 0 else f["pal"]
            if i == 0 and n == 1:
                pal = ch.TROFFEA
            gp = cam.proj(x, self.ground_y, z)
            if sl > 0:
                figure_shadow(canvas, gp[0], gp[1], gp[2], light_dir=ld, length=sl * 0.8, alpha=0.32 * day, sq=1.0)
            ch.place_figure(canvas, cam, x, z, p, ch.shade_palette(pal, tint=tuple(0.35 + 0.65 * v for v in tint)), self.ground_y, facing=f["facing"])
        # day/night ambient glow
        if night > 0.2:
            draw_glow(fbuf, CX, AH * 0.5, 600, (0.05, 0.08, 0.16), 0.5 * night)
        # documentary counter
        day_n = int(kf([(0, 1), (3.0, 4), (5.6, 5), (8.2, 7), (10.7, 30)], t, linear=True))
        label = f"第{day_n}天 · {['1', '1', '5', '12', '34', '约400'][[0, 1, 5, 12, 34, 44].index(n) if n in (0, 1, 5, 12, 34, 44) else 1]}人"
        ctx["captions"].append(("counter", label, smoothstep(0.6, 1.4, t)))


# =============================================================================== S5  cathedral square

class S5_Square(Scene):
    name = "S5"
    grade = dict(lift=(0.0, 0.0, 0.01), gain=(0.98, 0.98, 1.0), gamma=1.0, sat=0.78, bloom=0.3, grain=0.04, vignette=0.6)

    def build(self):
        self.ground_y = 1.6
        self.ground = Ground(wd.flagstone_tile(seed=51), ppm=96, camH=self.ground_y, fog=((176, 178, 184), 0.03), far_blur_from=22)
        self.cathedral = wd.cathedral_layer(ppm=10, X=-20.0, Z=105.0, ground_y=self.ground_y, color=(98, 90, 88))
        rng = np.random.default_rng(52)
        # side buildings: rows of houses at X = ±16 from Z 6..46
        self.facL, winL, _ = wd.build_street(seed=53, z_from=6.0, z_to=103.0, half_w=17.0, ground_y=self.ground_y)
        self.windows = winL
        self.sky = sky_gradient([(0, (150, 158, 170)), (0.5, (188, 190, 194)), (1, (205, 200, 195))])
        self.clouds = fx.cloud_layer(54)
        self.fogp = ((176, 178, 184), 0.02)
        self.dancers = []
        for i in range(64):
            x = float(rng.uniform(-9.5, 9.5))
            z = float(rng.uniform(6.5, 30.0))
            self.dancers.append(dict(x=x, z=z, style=int(rng.integers(0, 4)), ph=float(rng.random() * 6.28), pal=ch.palette(int(rng.integers(0, 8)), rng),
                                     facing=int(rng.choice([-1, 1])), speed=float(rng.uniform(0.85, 1.2)), wander=float(rng.uniform(0.2, 0.9)),
                                     collapse_at=float(rng.uniform(2.0, 11.0)) if rng.random() < 0.22 else None, exhaust=float(rng.uniform(0, 0.6))))
        self.dust_emit = [fx.Smoke((0, 0), rate=4, life=1.6, rise=8, wind=6, size0=4, growth=14, alpha0=0.16, color=(160, 150, 130), seed=60 + i, turb=4) for i in range(6)]
        self.banner_seed = 3

    def banner(self, canvas, cam, X, Z, t, color, seed):
        # pole + waving cloth
        top = cam.proj(X, self.ground_y - 5.5, Z)
        base = cam.proj(X, self.ground_y, Z)
        k = top[2]
        if Z - cam.z < 1:
            return
        cv2.line(canvas, P(base[0], base[1]), P(top[0], top[1]), (50, 42, 36), max(1, int(0.06 * k)), AA, 4)
        n = Noise1D(seed)
        pts_top, pts_bot = [], []
        for i in range(8):
            u = i / 7
            wave = math.sin(t * 4 + u * 5 + seed) * 0.25 * u + n.signed(t * 1.5 + u * 3) * 0.2 * u
            xx = top[0] + (1.6 * u) * k * (1 - 0.1 * u)
            yy = top[1] + wave * k
            pts_top.append((xx, yy + 0.1 * k))
            pts_bot.append((xx, yy + (1.1 - 0.15 * u) * k))
        poly = pts_top + pts_bot[::-1]
        cv2.fillPoly(canvas, [PTS(poly)], col(color), AA, 4)

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        d = self.dur
        # lateral dolly with slow push-in; light dims as clouds roll over
        dx, dy = handheld(t, 3.5, 5)
        cam = Cam(x=kf([(0, -4.5), (d, 4.0)], t, linear=True), y=-1.1, z=kf([(0, 0.0), (d, 3.0)], t), zoom=kf([(0, 0.92), (d, 1.08)], t), hy=AH * 0.44, dx=dx, dy=dy)
        dim = kf([(0, 1.0), (d * 0.5, 1.0), (d, 0.82)], t)
        fog = self.fogp
        canvas[:] = self.sky
        fx.draw_clouds(canvas, self.clouds, t, cam.hy, color=(120, 124, 132), speed=14, lo=0.42, hi=0.85, gain=0.7 * (1.3 - dim))
        self.cathedral.draw(canvas, cam, fog=((178, 180, 186), 0.012), tint=(dim, dim, dim * 1.02))
        for f in self.facL:
            f.draw(canvas, cam, fog=fog, tint=(dim * 0.95, dim * 0.93, dim * 0.9))
        self.ground.draw(canvas, cam)
        if dim < 0.98:
            canvas[:] = (canvas.astype(np.float32) * (0.85 + 0.15 * dim)).astype(np.uint8)
        # banners
        self.banner(canvas, cam, -6.0, 14.0, t, (130, 40, 40), 1)
        self.banner(canvas, cam, 7.0, 18.0, t, (170, 140, 60), 2)
        figs = sorted(self.dancers, key=lambda f: -f["z"])
        light_dir = (0.4, 0.3)
        emit_i = 0
        for f in figs:
            ph, wob = f["ph"], f["wander"]
            x = f["x"] + wob * math.sin(t * 0.6 * f["speed"] + ph)
            z = f["z"] + wob * 0.5 * math.cos(t * 0.45 * f["speed"] + ph)
            ex = clamp01(f["exhaust"] + t / d * 0.4)
            dp = ch.dance(t * f["speed"], ph=ph, style=f["style"], exhaust=ex)
            if f["collapse_at"] is not None and t > f["collapse_at"]:
                u = (t - f["collapse_at"]) / 1.1
                if u < 1:
                    p = ch.collapse(u, t, dp)
                    x, z = f["x"], f["z"]
                    if 0.2 < u < 0.9 and emit_i < len(self.dust_emit):
                        gp = cam.proj(x, self.ground_y, z)
                        self.dust_emit[emit_i].origin = (gp[0], gp[1])
                        self.dust_emit[emit_i].draw(canvas, (u - 0.2) * 1.1, scale=clamp(gp[2] / 80, 0.3, 1.5))
                        emit_i += 1
                else:
                    p = ch.lying(t, ph=ph, twitch=1.0 if u < 4 else 0.3)
                    x, z = f["x"], f["z"]
            else:
                p = dp
            gp = cam.proj(x, self.ground_y, z)
            if gp[2] > 12:
                figure_shadow(canvas, gp[0], gp[1], gp[2], light_dir=light_dir, length=0.5 * dim, alpha=0.28 * dim)
            fz = 1 - math.exp(-fog[1] * (z - cam.z))
            ch.place_figure(canvas, cam, x, z, p, ch.shade_palette(f["pal"], tint=(dim, dim, dim), fog=fz, fogc=fog[0]), self.ground_y, facing=f["facing"])
        fx.birds(canvas, t, (W * 0.1, AH * 0.22), n=9, seed=55, speed=(70, 12), size=5, color=(60, 60, 66))
        # dust haze near the ground
        vf = fx.vertical_fade(cam.hy + 20, cam.hy + 200)
        haze = np.repeat(np.clip((np.arange(AH) - cam.hy - 20) / 220, 0, 1)[:, None], W, axis=1).astype(np.float32) * 0.18
        blend_color(canvas, (180, 172, 160), haze)


# =============================================================================== S6  council chamber

class S6_Council(Scene):
    name = "S6"
    grade = dict(lift=(0.01, 0.0, 0.0), gain=(1.05, 0.96, 0.85), gamma=1.05, sat=0.92, bloom=0.55, grain=0.045, vignette=0.7)

    def build(self):
        self.ground_y = 1.5
        wall_w, wall_h = 12.0, 7.0
        rgb, a = wd.stone_wall_texture(wall_w, wall_h, seed=61, ppm=40, base=(86, 78, 72), windows=[(2.2, 0.8, 1.4, 4.2), (8.4, 0.8, 1.4, 4.2)])
        self.wall = wd.Quad3D(rgb, a, [(-wall_w / 2, self.ground_y - wall_h, 7.0), (wall_w / 2, self.ground_y - wall_h, 7.0), (wall_w / 2, self.ground_y, 7.0), (-wall_w / 2, self.ground_y, 7.0)])
        self.floor = Ground(wd.plank_tile(seed=62, base=(70, 54, 40)), ppm=90, camH=self.ground_y, fog=((40, 30, 24), 0.05), far_blur_from=8)
        # table: top + front
        tw, tdz, th_ = 6.0, 1.3, 0.78
        z0 = 3.4
        top_rgb, top_a = wd.wood_texture(tw, tdz, seed=63, ppm=60, base=(96, 70, 44), plank_w=0.35)
        fr_rgb, fr_a = wd.wood_texture(tw, th_, seed=64, ppm=60, base=(70, 50, 32), plank_w=0.25)
        y_top = self.ground_y - th_
        self.table_top = wd.Quad3D(top_rgb, top_a, [(-tw / 2, y_top, z0 + tdz), (tw / 2, y_top, z0 + tdz), (tw / 2, y_top, z0), (-tw / 2, y_top, z0)])
        self.table_front = wd.Quad3D(fr_rgb, fr_a, [(-tw / 2, y_top, z0), (tw / 2, y_top, z0), (tw / 2, self.ground_y, z0), (-tw / 2, self.ground_y, z0)])
        self.z_table, self.y_table, self.table_dz = z0, y_top, tdz
        self.rays = fx.god_rays(source=(W * 0.72, -500), n=5, seed=65, width=(30, 80), length=1600, blur=35)
        self.dust = fx.Dust(n=140, seed=66, color=(200, 215, 240), rad=(0.5, 1.5))
        self.smoke = [fx.Smoke((0, 0), rate=6, life=2.5, rise=30, wind=3, size0=2, growth=6, alpha0=0.12, color=(120, 110, 100), seed=70 + i, turb=6) for i in range(4)]
        self.pals = [ch.DOCTOR, dict(ch.DOCTOR, tunic=(60, 40, 44), cover=(90, 30, 30)), dict(ch.DOCTOR, tunic=(40, 44, 58), cover=None, hair=(150, 140, 130)), dict(ch.DOCTOR, tunic=(48, 40, 34), cover=(60, 50, 40))]
        self.fogp = ((30, 24, 20), 0.06)

    def candle(self, canvas, fbuf, cam, X, Z, t, seed, h=0.28):
        base = cam.proj(X, self.y_table, Z)
        k = base[2]
        cv2.rectangle(canvas, P(base[0] - 0.02 * k, base[1] - h * k), P(base[0] + 0.02 * k, base[1]), (222, 210, 180), -1, AA, 4)
        fx.flame(canvas, base[0], base[1] - h * k, 0.14 * k, t, seed=seed)
        fl = fx.torch_light(t, seed)
        draw_glow(fbuf, base[0], base[1] - (h + 0.08) * k, max(10, 1.4 * k), (1.0, 0.7, 0.35), 0.5 * fl)
        return base, k

    def draw_wide(self, t, canvas, fbuf, cam):
        fog = self.fogp
        canvas[:] = (18, 14, 12)
        self.wall.draw(canvas, cam, fog=fog)
        # window light glow on the wall (cool)
        for wx in (-3.1, 3.1):
            wp = cam.proj(wx, self.ground_y - 4.1, 7.0)
            draw_glow(fbuf, wp[0], wp[1], max(20, 1.4 * wp[2]), (0.5, 0.62, 0.85), 0.42, aspect=1.7)
        self.floor.draw(canvas, cam)
        # people behind the table (front rigs) — far → near
        k_p = cam.proj(0, self.ground_y, 4.6)[2]
        base_y = cam.proj(0, self.ground_y - 0.45, 4.6)[1]  # seated pelvis height
        table_y = cam.proj(0, self.y_table, 4.4)[1]
        gestures = ["book", "write", "point", "slam"]
        xs = [-2.1, -0.7, 0.75, 2.2]
        talking = 0.75 + 0.25 * math.sin(t * 1.3)
        for i, (x, g) in enumerate(zip(xs, gestures)):
            sx = cam.proj(x, self.ground_y, 4.6)[0]
            talk = talking if g == "point" else (0.4 if g == "slam" and (t % 4) < 1.5 else 0.0)
            ch.draw_front_figure(canvas, sx, base_y, k_p, t, self.pals[i], gesture=g, ph=i * 1.7, talk=talk,
                                 expr=["frown", "neutral", "frown", "frown"][i], seed=i, head_shake=1.0 if g == "slam" else 0.0, nod=0.5 if g == "book" else 0.0, table_y=table_y)
        # table
        self.table_top.draw(canvas, cam, fog=fog)
        self.table_front.draw(canvas, cam, fog=fog)
        # papers, books, inkpot on the table
        for (px_, pz_, w_, h_, cc) in ((-1.4, 3.7, 0.5, 0.35, (214, 200, 168)), (-0.6, 3.9, 0.45, 0.32, (222, 210, 180)), (0.9, 3.8, 0.5, 0.36, (208, 196, 160)), (1.9, 4.1, 0.6, 0.4, (90, 60, 40))):
            q = [cam.proj(px_ - w_ / 2, self.y_table - 0.01, pz_ + h_)[:2], cam.proj(px_ + w_ / 2, self.y_table - 0.01, pz_ + h_)[:2], cam.proj(px_ + w_ / 2, self.y_table - 0.01, pz_)[:2], cam.proj(px_ - w_ / 2, self.y_table - 0.01, pz_)[:2]]
            cv2.fillPoly(canvas, [PTS(q)], cc, AA, 4)
        # candles
        for i, (cx_, cz_) in enumerate(((-2.6, 3.6), (-0.1, 3.55), (1.5, 3.65), (2.7, 3.7))):
            base, k = self.candle(canvas, fbuf, cam, cx_, cz_, t, seed=80 + i)
            self.smoke[i].origin = (base[0], base[1] - 0.45 * k)
            self.smoke[i].draw(canvas, t, scale=clamp(k / 180, 0.4, 1.4), strength=0.7)
        # window shafts + dust
        ray = (self.rays * 0.16)[..., None]
        fbuf += ray * np.array([0.55, 0.68, 0.95], np.float32)
        self.dust.draw(canvas, t, weight=0.5, drift_y=-4)

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        cut = 7.6
        if t < cut:
            dx, dy = handheld(t, 2.5, 6)
            cam = Cam(x=kf([(0, -1.4), (cut, 1.3)], t, linear=True), y=0.25, z=kf([(0, 0.0), (cut, 0.9)], t), zoom=kf([(0, 1.0), (cut, 1.12)], t), hy=AH * 0.40, dx=dx, dy=dy)
            self.draw_wide(t, canvas, fbuf, cam)
            # foreground out-of-focus candle flame (bokeh)
            fl = fx.torch_light(t, 99)
            draw_glow(fbuf, W * 0.12 + 15 * math.sin(t * 0.5), AH * 0.78, 130, (1.0, 0.6, 0.25), 0.55 * fl, aspect=1.4)
            if t > 5.4:
                ctx["captions"].append(("caption", "诊断：热血过盛", smoothstep(5.4, 6.2, t)))
            return
        # close-up of the physician: candle-lit, talking, frowning
        tt = t - cut
        canvas[:] = (16, 12, 10)
        # blurred backdrop: wall glow
        draw_glow(fbuf, W * 0.7, AH * 0.3, 380, (0.35, 0.45, 0.7), 0.25, aspect=1.4)
        cx = CX - 60 + 10 * math.sin(tt * 1.1)
        cy = AH * 0.5 + 5 * math.sin(tt * 1.9)
        r = 115 + 6 * tt
        pal = self.pals[2]
        cv2.ellipse(canvas, P(cx, cy + r * 2.4), (int(r * 2.0 * 16), int(r * 0.95 * 16)), 0, 180, 360, col(pal["tunic"]), -1, AA, 4)
        talk = 0.0
        # speaks in bursts: 0.4-2.6 s, 3.4-4.6 s
        if 0.3 < tt < 2.7 or 3.3 < tt < 4.8:
            talk = 1.0
        ch.draw_head_closeup(canvas, cx, cy, r, tt, pal, "frown", cover=False, talk=talk, look=(-0.35 + 0.2 * math.sin(tt * 0.8), 0.05), gaze_dart=0.2, seed=9, turn=-0.3 + 0.15 * math.sin(tt * 0.7))
        # candle key light from the right, flickering
        fl = fx.torch_light(t, 101)
        draw_glow(fbuf, cx + r * 1.8, cy + r * 0.6, r * 3.0, (1.0, 0.72, 0.4), 0.22 * fl)
        # candle flame in frame (right foreground)
        fx.flame(canvas, W * 0.83, AH * 0.86, 46, t, seed=102)
        draw_glow(fbuf, W * 0.83, AH * 0.78, 150, (1.0, 0.68, 0.3), 0.7 * fl)
        self.dust.draw(canvas, t, weight=0.4, drift_y=-3)
        ctx["captions"].append(("caption", "诊断：热血过盛", 1.0 - smoothstep(1.8, 2.6, tt)))
