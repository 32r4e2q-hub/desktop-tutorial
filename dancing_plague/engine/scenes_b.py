"""Shots S7–S12: torchlit stage, road to the shrine, ergot theory, mass hysteria montage, dawn, credits."""
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
from .scenes_a import Scene, figure_shadow, draw_window_lights, lantern, street_common_build


# =============================================================================== S7  torchlit stage

class S7_Stage(Scene):
    name = "S7"
    grade = dict(lift=(0.01, 0.0, 0.0), gain=(1.08, 0.95, 0.82), gamma=1.05, sat=1.0, bloom=0.6, grain=0.05, vignette=0.7)

    def build(self):
        self.ground_y = 1.6
        self.ground = Ground(wd.flagstone_tile(seed=71, base=(80, 72, 66)), ppm=96, camH=self.ground_y, fog=((14, 10, 12), 0.06))
        self.cathedral = wd.cathedral_layer(ppm=8, X=-20.0, Z=42.0, ground_y=self.ground_y, color=(30, 28, 36))
        self.facades, self.windows, _ = wd.build_street(seed=72, z_from=6.0, z_to=40.0, half_w=14.0, ground_y=self.ground_y)
        self.sky = sky_gradient([(0, (6, 8, 18)), (0.6, (16, 18, 34)), (1, (30, 26, 34))])
        # stage: platform 8 m wide, 6 m deep, 1 m high at Z 10..16
        self.sz0, self.sz1, self.sh = 10.0, 16.0, 1.0
        top_rgb, top_a = wd.wood_texture(8.0, 6.0, seed=73, ppm=40, base=(120, 90, 56), plank_w=0.3)
        fr_rgb, fr_a = wd.wood_texture(8.0, 1.0, seed=74, ppm=40, base=(90, 66, 40), plank_w=0.25)
        y_top = self.ground_y - self.sh
        self.stage_top = wd.Quad3D(top_rgb, top_a, [(-4, y_top, self.sz1), (4, y_top, self.sz1), (4, y_top, self.sz0), (-4, y_top, self.sz0)])
        self.stage_front = wd.Quad3D(fr_rgb, fr_a, [(-4, y_top, self.sz0), (4, y_top, self.sz0), (4, self.ground_y, self.sz0), (-4, self.ground_y, self.sz0)])
        self.y_stage = y_top
        rng = np.random.default_rng(75)
        self.stage_dancers = []
        for i in range(14):
            self.stage_dancers.append(dict(x=float(rng.uniform(-3.4, 3.4)), z=float(rng.uniform(10.8, 15.4)), style=int(rng.integers(0, 3)), ph=float(rng.random() * 6.28),
                                           pal=ch.palette(int(rng.integers(0, 8)), rng), facing=int(rng.choice([-1, 1])), speed=float(rng.uniform(0.9, 1.25)),
                                           collapse_at=float(rng.uniform(4.0, 10.5)) if rng.random() < 0.35 else None))
        self.ground_dancers = []
        for i in range(30):
            self.ground_dancers.append(dict(x=float(rng.choice([-1, 1]) * rng.uniform(4.8, 11.0)), z=float(rng.uniform(7.0, 24.0)), style=int(rng.integers(0, 4)), ph=float(rng.random() * 6.28),
                                            pal=ch.palette(int(rng.integers(0, 8)), rng), facing=int(rng.choice([-1, 1])), speed=float(rng.uniform(0.9, 1.2))))
        self.torches = [(-4.4, 9.8), (4.4, 9.8), (-4.4, 16.2), (4.4, 16.2), (-8.0, 7.5), (8.0, 7.5), (-11.0, 20.0), (11.0, 20.0)]
        self.sparks = [fx.Sparks((0, 0), n=26, seed=90 + i, spread=0.5, speed=(30, 110), gravity=40) for i in range(len(self.torches))]
        self.smokes = [fx.Smoke((0, 0), rate=5, life=2.2, rise=40, wind=10, size0=4, growth=10, alpha0=0.18, color=(60, 52, 50), seed=100 + i) for i in range(len(self.torches))]
        self.fogp = ((16, 12, 14), 0.05)
        self.strongman = ch.palette(0)

    def torch(self, canvas, fbuf, cam, X, Z, t, i):
        dz = Z - cam.z
        if dz < 1.0:
            return
        base = cam.proj(X, self.ground_y, Z)
        top = cam.proj(X, self.ground_y - 2.6, Z)
        k = top[2]
        cv2.line(canvas, P(base[0], base[1]), P(top[0], top[1]), (40, 32, 26), max(1, int(0.08 * k)), AA, 4)
        cv2.rectangle(canvas, P(top[0] - 0.09 * k, top[1]), P(top[0] + 0.09 * k, top[1] + 0.3 * k), (60, 48, 36), -1, AA, 4)
        fl = fx.torch_light(t, 120 + i)
        fx.flame(canvas, top[0], top[1], 0.55 * k * (0.9 + 0.2 * fl), t, seed=130 + i, sway=1.3)
        f = 1 - math.exp(-self.fogp[1] * dz)
        draw_glow(fbuf, top[0], top[1] - 0.25 * k, max(12, 3.2 * k), (1.0, 0.62, 0.25), 0.75 * fl * (1 - 0.6 * f))
        # ground pool of light
        draw_glow(fbuf, base[0], base[1], max(10, 2.6 * k), (1.0, 0.6, 0.25), 0.22 * fl * (1 - 0.6 * f), aspect=0.35)
        self.sparks[i].origin = (top[0], top[1] - 0.3 * k)
        self.sparks[i].draw(canvas, t, scale=clamp(k / 60, 0.3, 1.6), intensity=0.9)
        self.smokes[i].origin = (top[0], top[1] - 0.5 * k)
        self.smokes[i].draw(canvas, t, scale=clamp(k / 90, 0.3, 1.4), strength=0.9)

    def musician(self, canvas, cam, X, Z, t, kind, pal, facing=1):
        """Drummer / piper standing on the stage."""
        if kind == "drum":
            p = ch.idle(t, amp=0.6)
            beat = TAU_ = 2 * math.pi
            w = t * 2 * math.pi * 1.9
            p["sL"] = 0.9 + 0.5 * max(0.0, math.sin(w)) ** 2
            p["eL"] = 1.6 - 0.9 * max(0.0, math.sin(w)) ** 2
            p["sR"] = 0.9 + 0.5 * max(0.0, math.sin(w + math.pi)) ** 2
            p["eR"] = 1.6 - 0.9 * max(0.0, math.sin(w + math.pi)) ** 2
            p["lean"] = 0.12
        else:
            p = ch.idle(t, amp=0.5)
            p["sL"], p["eL"] = 1.35 + 0.05 * math.sin(t * 3), 2.1
            p["sR"], p["eR"] = 1.2, 2.2
            p["head"] = -0.2 + 0.05 * math.sin(t * 2)
            p["lean"] = -0.05 + 0.03 * math.sin(t * 1.2)
        _, h = ch.skeleton(p)
        px, py, k = cam.proj(X, self.y_stage - h, Z)
        ch.draw_figure(canvas, px, py, k, p, pal, facing=facing)
        if kind == "drum":
            # drum in front
            cv2.ellipse(canvas, P(px + facing * 0.32 * k, py - 0.05 * k), (int(0.26 * k * 16), int(0.1 * k * 16)), 0, 0, 360, (150, 130, 100), -1, AA, 4)
            cv2.rectangle(canvas, P(px + facing * 0.06 * k, py - 0.05 * k), P(px + facing * 0.58 * k, py + 0.25 * k), (110, 70, 45), -1, AA, 4)
        else:
            # pipe
            hx, hy = px + facing * 0.32 * k, py - 1.15 * k
            cv2.line(canvas, P(hx, hy), P(hx + facing * 0.45 * k, hy + 0.35 * k), (60, 44, 30), max(2, int(0.05 * k)), AA, 4)
        return px, py, k

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        d = self.dur
        fog = self.fogp
        # camera: push in from far, then low angle (hy rises → looking up) toward the end
        dx, dy = handheld(t, 4.5, 7)
        cam = Cam(x=kf([(0, 2.0), (d, -0.5)], t), y=kf([(0, -0.6), (d * 0.7, -0.2), (d, 0.5)], t), z=kf([(0, -6.0), (d * 0.7, 3.5), (d, 5.0)], t),
                  zoom=kf([(0, 0.95), (d, 1.1)], t), hy=kf([(0, AH * 0.46), (d * 0.7, AH * 0.5), (d, AH * 0.62)], t), dx=dx, dy=dy)
        canvas[:] = self.sky
        self.cathedral.draw(canvas, cam, fog=((14, 12, 18), 0.03))
        for f in self.facades:
            f.draw(canvas, cam, fog=fog, tint=(0.35, 0.28, 0.26))
        draw_window_lights(canvas, fbuf, cam, self.windows, t, gain=0.7, fog=fog)
        self.ground.draw(canvas, cam)
        # ground dancers behind the stage first (far), then stage, then near ground dancers
        allg = sorted(self.ground_dancers, key=lambda f: -f["z"])
        far = [f for f in allg if f["z"] > self.sz1]
        near = [f for f in allg if f["z"] <= self.sz1]

        def draw_ground(fs):
            for f in fs:
                x = f["x"] + 0.5 * math.sin(t * 0.6 * f["speed"] + f["ph"])
                z = f["z"] + 0.4 * math.cos(t * 0.5 + f["ph"])
                p = ch.dance(t * f["speed"], ph=f["ph"], style=f["style"], exhaust=0.3)
                fz = 1 - math.exp(-fog[1] * (z - cam.z))
                warm = self.torch_warmth(x, z, t)
                ch.place_figure(canvas, cam, x, z, p, ch.shade_palette(f["pal"], tint=warm, fog=fz, fogc=fog[0]), self.ground_y, facing=f["facing"])

        draw_ground(far)
        # back torches
        for i, (tx, tz) in enumerate(self.torches):
            if tz > self.sz1:
                self.torch(canvas, fbuf, cam, tx, tz, t, i)
        self.stage_top.draw(canvas, cam, fog=fog, tint=(1.0, 0.85, 0.7))
        # musicians at the back of the stage
        self.musician(canvas, cam, -2.8, 15.2, t, "drum", ch.palette(2), facing=1)
        self.musician(canvas, cam, 2.6, 15.3, t, "pipe", ch.palette(5), facing=-1)
        self.musician(canvas, cam, 0.0, 15.6, t, "pipe", ch.palette(7), facing=1)
        # stage dancers (sorted)
        sd = sorted(self.stage_dancers, key=lambda f: -f["z"])
        for f in sd:
            x = f["x"] + 0.4 * math.sin(t * 0.7 * f["speed"] + f["ph"])
            z = f["z"] + 0.3 * math.cos(t * 0.6 + f["ph"])
            dp = ch.dance(t * f["speed"], ph=f["ph"], style=f["style"], exhaust=clamp01(t / d) * 0.5)
            if f["collapse_at"] is not None and t > f["collapse_at"]:
                u = (t - f["collapse_at"]) / 1.0
                p = ch.collapse(u, t, dp) if u < 1 else ch.lying(t, ph=f["ph"], twitch=0.6)
                x, z = f["x"], f["z"]
            else:
                p = dp
            _, h = ch.skeleton(p)
            px, py, k = cam.proj(x, self.y_stage - h, z)
            warm = self.torch_warmth(x, z, t)
            fz = 1 - math.exp(-fog[1] * (z - cam.z))
            figure_shadow(canvas, *cam.proj(x, self.y_stage, z), light_dir=(-0.3 * math.copysign(1, x), 0.3), length=0.6, alpha=0.35)
            ch.draw_figure(canvas, px, py, k, p, ch.shade_palette(f["pal"], tint=warm, fog=fz, fogc=fog[0]), facing=f["facing"])
        # strong companion holding up a dancer (front of the stage)
        xs_, zs_ = -1.2, 10.9
        ps = ch.walk(t, freq=0.9, stride=0.25, lean=0.2, armswing=0.0)
        ps["sL"], ps["eL"], ps["sR"], ps["eR"] = 1.3, 1.2, 1.1, 1.3
        _, h = ch.skeleton(ps)
        px, py, k = cam.proj(xs_, self.y_stage - h, zs_)
        ch.draw_figure(canvas, px, py, k, ps, ch.shade_palette(self.strongman, tint=self.torch_warmth(xs_, zs_, t)), facing=1)
        pd = ch.dance(t, ph=2.0, style=3, exhaust=0.8)
        pd["lean"] = 0.5 + 0.1 * math.sin(t * 3)
        _, h2 = ch.skeleton(pd)
        px2, py2, k2 = cam.proj(xs_ + 0.55, self.y_stage - h2 + 0.05, zs_ + 0.05)
        ch.draw_figure(canvas, px2, py2, k2, pd, ch.shade_palette(ch.palette(4), tint=self.torch_warmth(xs_, zs_, t)), facing=1)
        self.stage_front.draw(canvas, cam, fog=fog, tint=(1.0, 0.8, 0.65))
        # front torches
        for i, (tx, tz) in enumerate(self.torches):
            if tz <= self.sz1:
                self.torch(canvas, fbuf, cam, tx, tz, t, i)
        draw_ground(near)
        # embers drifting across frame + smoke haze
        vf = fx.vertical_fade(cam.hy - 40, cam.hy + 160)
        haze = fbm_tile  # noqa (kept for parity)
        ctx["captions"].append(("caption", "市政厅的处方：让他们跳", smoothstep(1.0, 1.8, t) * (1 - smoothstep(d - 3.2, d - 2.4, t))))

    def torch_warmth(self, x, z, t):
        acc = 0.0
        for i, (tx, tz) in enumerate(self.torches):
            dd = math.hypot(x - tx, z - tz)
            acc += fx.torch_light(t, 120 + i) / (1 + dd * dd * 0.12)
        w = clamp(acc, 0.15, 1.6)
        return (0.35 + 0.75 * w, 0.3 + 0.55 * w, 0.28 + 0.35 * w)


# =============================================================================== S8  road to Saverne

class S8_Road(Scene):
    name = "S8"
    grade = dict(lift=(0.0, 0.01, 0.03), gain=(0.9, 0.95, 1.05), gamma=1.05, sat=0.72, bloom=0.45, grain=0.05, vignette=0.6)

    def build(self):
        self.ground_y = 1.7
        self.ground = Ground(wd.dirt_tile(seed=81, base=(84, 74, 60)), ppm=96, camH=self.ground_y, fog=((132, 142, 156), 0.05), far_blur_from=10)
        self.sky = sky_gradient([(0, (96, 104, 122)), (0.5, (150, 156, 168)), (1, (170, 170, 172))])
        self.mountains = [wd.mountain_layer(82, 400, 70, 160, self.ground_y, (86, 96, 112), jag=0.6),
                          wd.mountain_layer(83, 300, 45, 110, self.ground_y, (70, 80, 96), jag=0.8),
                          wd.mountain_layer(84, 220, 26, 70, self.ground_y, (52, 62, 74), jag=1.0)]
        rng = np.random.default_rng(85)
        self.pines = []
        for i in range(70):
            side = rng.choice([-1, 1])
            X = float(side * rng.uniform(4.5, 22.0))
            Z = float(rng.uniform(6.0, 80.0))
            self.pines.append(wd.pine_layer(int(rng.integers(0, 1000)), X, Z, self.ground_y, height_m=float(rng.uniform(7, 13)), color=(22 + int(Z * 0.25), 30 + int(Z * 0.3), 30 + int(Z * 0.35))))
        self.pines.sort(key=lambda l: -l.Z)
        self.fog = fx.Fog(seed=86, color=(150, 160, 175))
        self.rain = fx.Rain(n=180, seed=87, wind=-60, speed=(600, 900), length=(6, 12), color=(170, 180, 195))
        self.fogp = ((132, 142, 156), 0.05)
        self.patients = [dict(ph=float(rng.random() * 6.28), pal=ch.palette(int(rng.integers(0, 8)), rng), off=float(i * 1.5 + rng.uniform(0, 0.5)), lat=float(rng.uniform(-0.9, 0.9))) for i in range(6)]
        for p in self.patients:
            p["pal"]["hose"] = (140, 40, 40)  # red shoes/hose
        self.guard_pal = dict(tunic=(70, 72, 80), hose=(40, 40, 44), skin=(210, 175, 145), hair=(40, 34, 30), cover=(120, 122, 130), skirt=None)
        self.chapel = None

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        d = self.dur
        fog = self.fogp
        # convoy moves along +Z at 1.1 m/s; camera: wide establishing then tracks alongside
        speed = 1.1
        conv_z = 8.0 + speed * t
        dx, dy = handheld(t, 3.0, 8)
        cam = Cam(x=kf([(0, -1.0), (5.0, -1.8), (d, -2.4)], t), y=kf([(0, -0.6), (d, 0.1)], t), z=kf([(0, 0.0), (5.0, conv_z - 8.0), (d, conv_z - 6.2)], t) if t > 5.0 else kf([(0, 0.0), (5.0, 8.0 + speed * 5.0 - 8.0)], t),
                  zoom=kf([(0, 0.95), (d, 1.15)], t), hy=AH * 0.47, dx=dx, dy=dy)
        canvas[:] = self.sky
        for m in self.mountains:
            m.draw(canvas, cam, fog=((150, 158, 172), 0.012))
        # chapel light far on the mountain
        cp = cam.proj(6.0, self.ground_y - 22.0, 118.0)
        draw_glow(fbuf, cp[0], cp[1], 26, (1.0, 0.75, 0.4), 0.55 * (0.8 + 0.2 * math.sin(t * 3)))
        cv2.rectangle(canvas, P(cp[0] - 4, cp[1] - 8), P(cp[0] + 4, cp[1] + 4), (60, 58, 62), -1, AA, 4)
        cv2.fillPoly(canvas, [PTS([(cp[0] - 5, cp[1] - 8), (cp[0], cp[1] - 16), (cp[0] + 5, cp[1] - 8)])], (50, 48, 52), AA, 4)
        self.ground.draw(canvas, cam)
        # pines & convoy, depth sorted
        items = [("pine", l.Z, l) for l in self.pines]
        items.append(("convoy", conv_z, None))
        items.sort(key=lambda it: -it[1])
        for kind, Z, obj in items:
            if kind == "pine":
                sway = 0.05 * math.sin(t * 1.1 + obj.Z)
                obj.draw(canvas, cam, fog=fog, tint=(1 + sway, 1 + sway, 1 + sway))
            else:
                self.draw_convoy(canvas, fbuf, cam, t, conv_z, fog)
        # fog banks
        vf = fx.vertical_fade(cam.hy - 60, cam.hy + 90, cam.hy + 200, AH)
        self.fog.draw(canvas, t, gain=0.5, vfade=vf, lo=0.3, hi=0.9, speed=(22, -3), speed2=(-14, 5))
        self.rain.draw(canvas, t, density=0.7, weight=0.3)
        ctx["captions"].append(("caption", "萨韦讷 · 圣维特圣坛", smoothstep(8.0, 8.8, t) * (1 - smoothstep(d - 1.5, d - 0.8, t))))

    def draw_convoy(self, canvas, fbuf, cam, t, cz, fog):
        gy = self.ground_y
        X = 0.0
        fz = lambda z: 1 - math.exp(-fog[1] * (z - cam.z))
        # horse ahead of cart
        hz = cz + 3.2
        hp = cam.proj(X, gy, hz)
        # side-view rigs are drawn in screen space; for a convoy moving away along Z we present it in 3/4 by drawing
        # along X (screen-right = +Z). Camera is beside the road, so use facing=1 with world X→Z remap.
        # Simpler: render convoy as if the road runs left→right across frame at depth (cz - cam.z).
        dz = cz - cam.z
        if dz < 1.0:
            return
        k = cam.f / dz
        gyp = cam.hy + (gy - cam.y) * k + cam.dy
        # base screen x for convoy centre (moves right as it advances relative to camera)
        base_x = CX + (X - cam.x) * k + cam.dx
        f = fz(cz)
        fc = fog[0]
        dist = 1.1 * t
        # patients walking behind (left)
        for i, p in enumerate(self.patients):
            px = base_x - (5.2 + p["off"]) * k
            pl = p["lat"]
            kk = k * (1 + 0.02 * pl)
            pose = ch.shiver_walk(t, ph=p["ph"]) if i % 2 else ch.walk(t, freq=1.5, stride=0.45, ph=p["ph"], lean=0.3, armswing=0.3, tired=0.7)
            _, h = ch.skeleton(pose)
            figure_shadow(canvas, px, gyp + pl * 0.15 * k, kk, light_dir=(0.0, 0.0), length=0, alpha=0.25)
            ch.draw_figure(canvas, px, gyp + pl * 0.15 * k - h * kk, kk, pose, ch.shade_palette(p["pal"], fog=f, fogc=fc), facing=1)
        # guards
        for gx_, ph_ in ((-4.6, 0.0), (2.6, 1.5)):
            px = base_x + gx_ * k
            pose = ch.walk(t, freq=1.5, stride=0.5, ph=ph_, lean=0.05, armswing=0.2)
            _, h = ch.skeleton(pose)
            ch.draw_figure(canvas, px, gyp - h * k, k, pose, ch.shade_palette(self.guard_pal, fog=f, fogc=fc), facing=1, prop="spear", hood=True)
        # cart + horse
        ch.draw_cart(canvas, base_x - 1.0 * k, gyp, k, dist, facing=1, color=tuple(a * (1 - f) + b * f for a, b in zip((88, 70, 52), fc)))
        # people sitting in the cart
        for i, (ox, ph_) in enumerate(((-1.9, 0.3), (-1.1, 1.1), (-0.3, 2.2))):
            pose = ch.idle(t, ph=ph_, amp=2.5)
            pose["lean"] = 0.35 + 0.1 * math.sin(t * 2 + ph_)
            pose["hL"], pose["kL"], pose["hR"], pose["kR"] = 1.5, 1.4, 1.5, 1.4
            pose["ground"] = 0.0
            pal = ch.palette(i + 2)
            pal["hose"] = (140, 40, 40)
            ch.draw_figure(canvas, base_x + ox * k, gyp - (0.55 + 0.8) * k, k * 0.95, pose, ch.shade_palette(pal, fog=f, fogc=fc), facing=1)
        ch.draw_horse(canvas, base_x + 2.4 * k, gyp, k, t, facing=1, color=tuple(a * (1 - f) + b * f for a, b in zip((72, 58, 48), fc)))
        # cart lantern
        lx, ly = base_x + 0.35 * k, gyp - 1.9 * k
        cv2.line(canvas, P(base_x + 0.3 * k, gyp - 1.55 * k), P(lx, ly), (40, 34, 30), max(1, int(0.03 * k)), AA, 4)
        cv2.rectangle(canvas, P(lx - 0.1 * k, ly), P(lx + 0.1 * k, ly + 0.25 * k), (230, 180, 100), -1, AA, 4)
        draw_glow(fbuf, lx, ly + 0.12 * k, max(10, 1.6 * k), (1.0, 0.72, 0.4), 0.5 * (1 - 0.6 * f) * fx.torch_light(t, 140))


# =============================================================================== S9  ergot

class S9_Ergot(Scene):
    name = "S9"
    grade = dict(lift=(0.02, 0.01, 0.0), gain=(1.05, 0.98, 0.82), gamma=1.0, sat=0.9, bloom=0.5, grain=0.04, vignette=0.6)

    def build(self):
        rng = np.random.default_rng(91)
        self.stalks = []
        for i in range(150):
            depth = rng.uniform(0.0, 1.0)  # 0 = far, 1 = near
            self.stalks.append(dict(x=float(rng.uniform(-0.1, 1.1)), depth=float(depth), ph=float(rng.random() * 6.28), h=float(rng.uniform(0.45, 0.7)),
                                    ergot=bool(rng.random() < 0.18 and depth > 0.4), lean=float(rng.uniform(-0.15, 0.15)), seed=int(rng.integers(0, 1000))))
        self.stalks.sort(key=lambda s: s["depth"])
        self.sky = sky_gradient([(0, (206, 176, 120)), (0.6, (226, 200, 150)), (1, (200, 170, 110))])
        self.dust = fx.Dust(n=160, seed=92, color=(255, 230, 170), rad=(0.5, 1.8))
        self.wind = Noise1D(93)
        self.fog = fx.Fog(seed=94, color=(230, 205, 150))

    def draw_stalk(self, canvas, s, t, cam_shift, gust, focus_near):
        depth = s["depth"]
        scale = 0.35 + 1.15 * depth ** 1.6
        x = (s["x"] - 0.5) * W * (1 + 0.6 * depth) + CX + cam_shift * (0.3 + depth)
        base_y = AH * (0.62 + 0.55 * depth ** 1.5)
        h = s["h"] * AH * scale
        sway = (gust * 0.9 + 0.35 * math.sin(t * 1.9 + s["ph"]) + 0.15 * math.sin(t * 4.3 + s["ph"] * 2)) * (0.16 + 0.1 * depth) + s["lean"] * 0.3
        # stalk as a quadratic curve
        pts = []
        for i in range(9):
            u = i / 8
            pts.append((x + sway * h * u * u, base_y - h * u))
        tip = pts[-1]
        c_stalk = mix((150, 130, 70), (60, 52, 36), 0.3 * (1 - depth))
        c_stalk = mix(c_stalk, (226, 200, 150), (1 - depth) ** 2 * 0.6)
        tw = max(1, int(0.006 * h))
        cv2.polylines(canvas, [PTS(pts)], False, col(c_stalk), tw, AA, 4)
        # ear of rye: spikelets along the top 25 %
        n_sp = 10
        ear_len = h * 0.26
        ang = math.atan2(-(pts[-1][1] - pts[-3][1]), pts[-1][0] - pts[-3][0])
        for i in range(n_sp):
            u = i / (n_sp - 1)
            ex = tip[0] - math.cos(ang) * ear_len * (1 - u) * 0 + math.cos(ang) * (ear_len * (u - 0.9))
            ey = tip[1] - math.sin(ang) * (ear_len * (u - 0.9))
            cxp = tip[0] + math.cos(ang) * ear_len * (u - 0.9)
            cyp = tip[1] - math.sin(ang) * ear_len * (u - 0.9)
            for side in (-1, 1):
                gx = cxp + side * math.sin(ang) * 0.012 * h
                gy = cyp + side * math.cos(ang) * 0.012 * h
                cv2.ellipse(canvas, P(gx, gy), (max(1, int(0.014 * h * 16)), max(1, int(0.006 * h * 16))), -math.degrees(ang) + side * 25, 0, 360, col(mix((190, 160, 90), (226, 200, 150), (1 - depth) ** 2 * 0.5)), -1, AA, 4)
            # awn
            cv2.line(canvas, P(cxp, cyp), P(cxp + math.cos(ang + 0.15) * 0.05 * h, cyp - math.sin(ang + 0.15) * 0.05 * h), col(c_stalk), 1, AA, 4)
        if s["ergot"]:
            # dark purple sclerotia replacing 2-3 grains
            for j in (2, 5, 7):
                u = j / (n_sp - 1)
                cxp = tip[0] + math.cos(ang) * ear_len * (u - 0.9)
                cyp = tip[1] - math.sin(ang) * ear_len * (u - 0.9)
                cv2.ellipse(canvas, P(cxp + math.sin(ang) * 0.014 * h, cyp + math.cos(ang) * 0.014 * h), (max(1, int(0.026 * h * 16)), max(1, int(0.009 * h * 16))), -math.degrees(ang) + 20, 0, 360, (36, 18, 40), -1, AA, 4)
            return (cxp, cyp)
        return None

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        d = self.dur
        canvas[:] = self.sky
        # sun low right → backlight
        draw_glow(fbuf, W * 0.8, AH * 0.22, 520, (1.0, 0.82, 0.55), 0.30)
        draw_glow(fbuf, W * 0.8, AH * 0.22, 120, (1.0, 0.92, 0.75), 0.45)
        gust = self.wind.signed(t * 0.35) * 0.8 + 0.5 * self.wind.signed(t * 1.4 + 20)
        cam_shift = kf([(0, 160), (d, -160)], t, linear=True)
        # far field: blurred band
        far = np.zeros((AH, W, 3), np.uint8)
        far[:] = self.sky
        for s in self.stalks:
            if s["depth"] < 0.45:
                self.draw_stalk(far, s, t, cam_shift, gust, False)
        far = cv2.GaussianBlur(far, (0, 0), 6 - 3 * smoothstep(3, 6, t) if t < 6 else 3)
        canvas[:] = far
        ergot_pts = []
        for s in self.stalks:
            if s["depth"] >= 0.45:
                r = self.draw_stalk(canvas, s, t, cam_shift, gust, True)
                if r:
                    ergot_pts.append(r)
        # focus racks to the nearest ergot at ~4 s: draw callout
        if ergot_pts and t > 4.2:
            # pick the ergot ear closest to frame centre
            ex, ey = min(ergot_pts, key=lambda p: abs(p[0] - CX * 1.15) + abs(p[1] - AH * 0.45))
            a = smoothstep(4.2, 5.0, t) * (1 - smoothstep(d - 5.5, d - 4.8, t))
            grow = smoothstep(4.2, 5.4, t)
            tmp, merge = overlay_alpha(canvas, a)
            cv2.circle(tmp, P(ex, ey), int(34 * grow * 16), (60, 30, 24), 2, AA, 4)
            lx = ex + 70 * grow
            ly = ey - 60 * grow
            cv2.line(tmp, P(ex + 24, ey - 24), P(lx, ly), (60, 30, 24), 2, AA, 4)
            cv2.line(tmp, P(lx, ly), P(lx + 150 * grow, ly), (60, 30, 24), 2, AA, 4)
            merge()
            draw_text(canvas, "麦角菌  Claviceps purpurea", lx + 8, ly - 22, size=24, serif=False, color=(40, 24, 20), opacity=a * grow, anchor="left", stroke=2, stroke_color=(240, 228, 200), shadow=False)
            draw_text(canvas, "幻觉 · 痉挛 · 肢体缺血", lx + 8, ly + 20, size=20, serif=False, color=(60, 30, 24), opacity=a * smoothstep(5.2, 5.8, t), anchor="left", stroke=2, stroke_color=(240, 228, 200), shadow=False)
        # final part: a silhouette dancer convulses then stiffens and falls (why ergot can't explain days of dancing)
        if t > d - 5.4:
            tt = t - (d - 5.4)
            px, py, k = W * 0.30, AH * 0.98, 300
            if tt < 1.8:
                p = ch.dance(tt, ph=1.0, style=1)
            elif tt < 3.0:
                u = (tt - 1.8) / 1.2
                stiff = ch.pose(lean=0.05, head=-0.2, sL=0.4, eL=0.1, sR=0.4, eR=0.1, hL=0.0, kL=0.0, hR=0.0, kR=0.0)
                stiff["sL"] += 0.15 * math.sin(tt * 30)
                p = ch.blend(ch.dance(1.8, ph=1.0, style=1), stiff, smooth(u))
            else:
                u = (tt - 3.0) / 1.2
                stiff = ch.pose(lean=0.05, head=-0.2, sL=0.4, eL=0.1, sR=0.4, eR=0.1)
                fallen = ch.pose(lean=1.5, head=-0.1, sL=0.5, eL=0.1, sR=0.5, eR=0.1, ground=0.15)
                p = ch.blend(stiff, fallen, ease_in(min(1, u)))
            _, h = ch.skeleton(p)
            a = smoothstep(0, 0.6, tt)
            tmp, merge = overlay_alpha(canvas, a)
            ch.draw_figure(tmp, px, py - h * k, k, p, ch.TROFFEA, facing=1, silhouette=(30, 20, 18))
            merge()
        self.dust.draw(canvas, t, weight=0.55, drift_y=-10)
        vf = fx.vertical_fade(AH * 0.3, AH * 0.8)
        self.fog.draw(canvas, t, gain=0.16, vfade=vf, lo=0.4, hi=0.95)
        ctx["captions"].append(("caption", "假说一：麦角中毒", smoothstep(1.0, 1.8, t) * (1 - smoothstep(6.5, 7.2, t))))


# =============================================================================== S10  mass psychogenic illness

class S10_Hysteria(Scene):
    name = "S10"
    grade = dict(lift=(0.0, 0.0, 0.01), gain=(0.95, 0.97, 1.02), gamma=1.0, sat=0.7, bloom=0.45, grain=0.05, vignette=0.7)

    def build(self):
        # segment A: snowy street (winter famine)
        street_common_build(self, seed=11, snow=1.0)
        self.groundA = Ground(wd.cobble_tile(seed=3, snow=1.0), ppm=128, camH=self.ground_y, fog=((150, 156, 170), 0.06))
        self.snow = fx.Snow(n=520, seed=101, wind=140)
        self.fogA = fx.Fog(seed=102, color=(170, 176, 190))
        # segment B: sickbed interior
        rgb, a = wd.stone_wall_texture(6.0, 3.5, seed=103, ppm=50, base=(70, 62, 56), windows=[(4.2, 0.4, 0.7, 1.6)])
        self.wallB = wd.Quad3D(rgb, a, [(-3, 1.5 - 3.5, 4.0), (3, 1.5 - 3.5, 4.0), (3, 1.5, 4.0), (-3, 1.5, 4.0)])
        self.floorB = Ground(wd.plank_tile(seed=104, base=(60, 46, 34)), ppm=90, camH=1.5, fog=((20, 16, 14), 0.1), far_blur_from=6)
        # segment C: shrine — St Vitus statue niche with candles
        rgb2, a2 = wd.stone_wall_texture(8.0, 6.0, seed=105, ppm=40, base=(78, 72, 68))
        self.wallC = wd.Quad3D(rgb2, a2, [(-4, 1.5 - 6, 5.0), (4, 1.5 - 6, 5.0), (4, 1.5, 5.0), (-4, 1.5, 5.0)])
        self.floorC = Ground(wd.flagstone_tile(seed=106, base=(90, 84, 78)), ppm=96, camH=1.5, fog=((20, 16, 14), 0.08), far_blur_from=6)
        self.dust = fx.Dust(n=90, seed=107, color=(255, 220, 170))
        # segment D: contagion grid
        rng = np.random.default_rng(108)
        self.grid = []
        cols, rows = 12, 5
        for r in range(rows):
            for c in range(cols):
                self.grid.append(dict(c=c, r=r, jit=float(rng.uniform(-0.15, 0.15)), ph=float(rng.random() * 6.28), style=int(rng.integers(0, 4)), delay=float(rng.uniform(0, 0.5))))
        self.fogD = fx.Fog(seed=109, color=(60, 20, 22))

    # segment boundaries (seconds within the shot)
    A_END, B_END, C_END = 5.2, 9.2, 13.4

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        d = self.dur
        if t < self.A_END:
            self.draw_snow(t, canvas, fbuf, ctx)
        elif t < self.B_END:
            self.draw_sickbed(t - self.A_END, canvas, fbuf, ctx)
        elif t < self.C_END:
            self.draw_shrine(t - self.B_END, canvas, fbuf, ctx)
        else:
            self.draw_grid(t - self.C_END, d - self.C_END, canvas, fbuf, ctx)

    def draw_snow(self, t, canvas, fbuf, ctx):
        fog = ((150, 156, 170), 0.06)
        dx, dy = handheld(t, 5.0, 10)
        cam = Cam(x=0.2, y=-0.2, z=kf([(0, 0.0), (self.A_END, 2.2)], t), zoom=1.05, hy=AH * 0.48, dx=dx, dy=dy)
        canvas[:] = (118, 124, 140)
        self.groundA.draw(canvas, cam)
        for f in self.facades:
            f.draw(canvas, cam, fog=fog, tint=(0.62, 0.64, 0.72))
        draw_window_lights(canvas, fbuf, cam, self.windows, t, gain=0.5, fog=fog)
        # three figures leaning into the wind, walking toward camera (-Z)
        for i, (x, z0, ph) in enumerate(((-1.2, 16.0, 0.0), (0.9, 19.0, 1.4), (-0.2, 24.0, 2.9))):
            z = z0 - 0.9 * t
            p = ch.walk(t, freq=1.4, stride=0.4, ph=ph, lean=0.45, armswing=0.0, kmax=0.9)
            p["sL"], p["eL"], p["sR"], p["eR"] = 1.3, 2.2, 1.1, 2.3  # arms hugging the body
            p["head"] = 0.4
            fz = 1 - math.exp(-fog[1] * (z - cam.z))
            ch.place_figure(canvas, cam, x, z, p, ch.shade_palette(ch.palette(i + 1), tint=(0.7, 0.7, 0.78), fog=fz, fogc=fog[0]), self.ground_y, facing=-1, hood=True)
        gust = 0.5 + 0.5 * math.sin(t * 0.9)
        self.snow.draw(canvas, t, density=1.0, gust=gust, weight=0.85)
        vf = fx.vertical_fade(cam.hy - 30, cam.hy + 120)
        self.fogA.draw(canvas, t, gain=0.45, vfade=vf, lo=0.3, hi=0.9, speed=(60, 0), speed2=(-30, 4))
        ctx["captions"].append(("caption", "饥荒 · 严冬", smoothstep(0.6, 1.2, t) * (1 - smoothstep(self.A_END - 0.8, self.A_END - 0.3, t))))

    def draw_sickbed(self, t, canvas, fbuf, ctx):
        fog = ((20, 16, 14), 0.08)
        gy = 1.5
        dx, dy = handheld(t, 2.0, 11)
        cam = Cam(x=kf([(0, 0.6), (4.0, 0.1)], t), y=-0.2, z=kf([(0, -3.6), (4.0, -2.6)], t), zoom=1.05, hy=AH * 0.46, dx=dx, dy=dy)
        canvas[:] = (14, 11, 10)
        self.wallB.draw(canvas, cam, fog=fog)
        # window light (window in texture at x 4.2..4.9 m of a 6 m wall → world X 1.2..1.9, y 0.4..2.0 from wall top)
        wp = cam.proj(1.55, gy - 3.5 + 1.2, 4.0)
        draw_glow(fbuf, wp[0], wp[1], max(20, 1.0 * wp[2]), (0.55, 0.62, 0.8), 0.5, aspect=1.6)
        self.floorB.draw(canvas, cam)
        # bed: low platform Z 2.2..3.6, X -1.9..0.9, top at gy-0.45
        yb = gy - 0.45
        q = [cam.proj(-1.9, yb, 3.6)[:2], cam.proj(0.9, yb, 3.6)[:2], cam.proj(0.9, yb, 2.2)[:2], cam.proj(-1.9, yb, 2.2)[:2]]
        cv2.fillPoly(canvas, [PTS(q)], (150, 142, 128), AA, 4)
        qf = [cam.proj(-1.9, yb, 2.2)[:2], cam.proj(0.9, yb, 2.2)[:2], cam.proj(0.9, gy, 2.2)[:2], cam.proj(-1.9, gy, 2.2)[:2]]
        cv2.fillPoly(canvas, [PTS(qf)], (70, 52, 38), AA, 4)
        # pillow
        pq = [cam.proj(0.15, yb - 0.12, 3.5)[:2], cam.proj(0.85, yb - 0.12, 3.5)[:2], cam.proj(0.85, yb - 0.02, 2.4)[:2], cam.proj(0.15, yb - 0.02, 2.4)[:2]]
        cv2.fillPoly(canvas, [PTS(pq)], (190, 182, 168), AA, 4)
        # patient lying, head to the right (facing -1 so the head is at +x)
        p = ch.sick_lying(t, ph=0.5)
        px, py, k = cam.proj(-0.35, yb - 0.17, 2.9)
        ch.draw_figure(canvas, px, py, k, p, ch.palette(3), facing=-1)
        # blanket over legs/torso, breathing
        br = 0.012 * math.sin(t * 2.2 + 0.5)
        bq = [cam.proj(-1.85, yb - 0.24 - br, 3.5)[:2], cam.proj(0.05, yb - 0.26 - br, 3.5)[:2], cam.proj(0.05, yb - 0.2, 2.3)[:2], cam.proj(-1.85, yb - 0.18, 2.3)[:2]]
        cv2.fillPoly(canvas, [PTS(bq)], (98, 72, 62), AA, 4)
        # carer sitting on a stool at the foot/left of the bed, facing the camera, dabbing the brow
        kk = cam.proj(0, gy, 1.9)[2]
        by = cam.proj(0, gy - 0.5, 1.9)[1]
        sx = cam.proj(1.35, gy, 1.9)[0]
        ch.draw_front_figure(canvas, sx, by, kk, t, ch.palette(5), gesture="point" if (t % 3) < 1.6 else "rest", ph=0.7, expr="tired", seed=3, nod=0.6)
        # candle on a stool (left)
        cp = cam.proj(-2.4, gy - 0.6, 2.6)
        cv2.rectangle(canvas, P(cp[0] - 0.14 * cp[2], cp[1]), P(cp[0] + 0.14 * cp[2], cp[1] + 0.6 * cp[2]), (60, 46, 34), -1, AA, 4)
        cv2.rectangle(canvas, P(cp[0] - 0.02 * cp[2], cp[1] - 0.22 * cp[2]), P(cp[0] + 0.02 * cp[2], cp[1]), (222, 210, 180), -1, AA, 4)
        fx.flame(canvas, cp[0], cp[1] - 0.22 * cp[2], 0.12 * cp[2], t, seed=111)
        draw_glow(fbuf, cp[0], cp[1] - 0.3 * cp[2], max(10, 1.8 * cp[2]), (1.0, 0.7, 0.35), 0.6 * fx.torch_light(t, 112))
        self.dust.draw(canvas, t, weight=0.35, drift_y=-3)
        ctx["captions"].append(("caption", "瘟疫", smoothstep(0.5, 1.0, t) * (1 - smoothstep(3.2, 3.7, t))))

    def draw_shrine(self, t, canvas, fbuf, ctx):
        fog = ((20, 16, 14), 0.06)
        gy = 1.5
        dur = self.C_END - self.B_END
        dx, dy = handheld(t, 2.0, 12)
        cam = Cam(x=0.0, y=kf([(0, -0.6), (dur, -0.2)], t), z=kf([(0, -4.4), (dur, -2.4)], t), zoom=1.0, hy=kf([(0, AH * 0.5), (dur, AH * 0.56)], t), dx=dx, dy=dy)
        canvas[:] = (12, 10, 10)
        self.wallC.draw(canvas, cam, fog=fog)
        nz = 4.95
        # niche (dark arch) from y = gy-3.9 to gy-1.0
        nq = [cam.proj(-0.8, gy - 3.4, nz)[:2], cam.proj(0.8, gy - 3.4, nz)[:2], cam.proj(0.8, gy - 1.0, nz)[:2], cam.proj(-0.8, gy - 1.0, nz)[:2]]
        cv2.fillPoly(canvas, [PTS(nq)], (30, 26, 26), AA, 4)
        top = cam.proj(0, gy - 3.4, nz)
        cv2.ellipse(canvas, P(top[0], top[1]), (int(0.8 * top[2] * 16), int(0.6 * top[2] * 16)), 0, 180, 360, (30, 26, 26), -1, AA, 4)
        # plinth
        pq = [cam.proj(-0.6, gy - 1.0, nz - 0.01)[:2], cam.proj(0.6, gy - 1.0, nz - 0.01)[:2], cam.proj(0.6, gy - 0.55, nz - 0.01)[:2], cam.proj(-0.6, gy - 0.55, nz - 0.01)[:2]]
        cv2.fillPoly(canvas, [PTS(pq)], (64, 58, 54), AA, 4)
        # statue on the plinth: stone saint with a raised hand
        sp = ch.pose(lean=0.0, head=-0.05, sL=1.9, eL=0.9, sR=0.3, eR=0.4)
        _, h = ch.skeleton(sp)
        px, py, k = cam.proj(0.0, gy - 1.0 - h, nz - 0.03)
        stone = dict(tunic=(150, 140, 128), hose=(140, 130, 120), skin=(160, 150, 140), hair=(150, 140, 130), cover=None, skirt=(140, 130, 118))
        ch.draw_figure(canvas, px, py, k, sp, stone, facing=-1)
        hc = cam.proj(0.0, gy - 1.0 - 1.72, nz)
        cv2.circle(canvas, P(hc[0], hc[1]), int(0.24 * hc[2] * 16), (200, 170, 90), max(1, int(0.03 * hc[2])), AA, 4)
        # warm glow from the candles lighting the niche
        draw_glow(fbuf, px, py - 0.6 * k, max(20, 1.4 * k), (1.0, 0.72, 0.4), 0.28 * fx.torch_light(t, 133))
        self.floorC.draw(canvas, cam)
        # candles row on a step in front of the plinth
        for i, cx_ in enumerate(np.linspace(-1.5, 1.5, 9)):
            cp = cam.proj(cx_, gy - 0.3, 4.4)
            hgt = 0.14 + 0.06 * math.sin(i * 1.7)
            cv2.rectangle(canvas, P(cp[0] - 0.015 * cp[2], cp[1] - hgt * cp[2]), P(cp[0] + 0.015 * cp[2], cp[1]), (226, 214, 184), -1, AA, 4)
            fx.flame(canvas, cp[0], cp[1] - hgt * cp[2], 0.09 * cp[2], t, seed=120 + i)
            draw_glow(fbuf, cp[0], cp[1] - (hgt + 0.06) * cp[2], max(8, 1.1 * cp[2]), (1.0, 0.7, 0.35), 0.4 * fx.torch_light(t, 130 + i))
        # kneeling worshippers (side view toward the statue), bowing
        for i, (x, z, ph, pi) in enumerate(((-1.3, 3.0, 0.0, 1), (1.1, 3.2, 1.3, 3), (-0.1, 2.2, 2.4, 6))):
            p = ch.kneel_pray(t, ph=ph)
            _, h = ch.skeleton(p)
            px, py, k = cam.proj(x, gy - h, z)
            figure_shadow(canvas, px, cam.proj(x, gy, z)[1], k, light_dir=(0, 0), length=0, alpha=0.3)
            ch.draw_figure(canvas, px, py, k, p, ch.palette(pi), facing=1, hood=(i == 2))
        self.dust.draw(canvas, t, weight=0.4, drift_y=-4)
        ctx["captions"].append(("caption", "圣维特的诅咒", smoothstep(0.8, 1.4, t) * (1 - smoothstep(dur - 0.8, dur - 0.3, t))))

    def draw_grid(self, t, dur, canvas, fbuf, ctx):
        canvas[:] = (10, 6, 7)
        self.fogD.draw(canvas, t, gain=0.5, lo=0.3, hi=0.95, speed=(14, -5), speed2=(-8, 3))
        cols, rows = 12, 5
        cw, rh = W / (cols + 1), (AH * 0.78) / rows
        # infection spreads from the centre cell outward: radius grows with time
        c0, r0 = 5.5, 2.0
        radius = kf([(0.6, 0.0), (dur - 1.0, 8.5)], t)
        s = 1.0 + 0.12 * (t / dur)
        for g in self.grid:
            gx = (g["c"] + 1) * cw + g["jit"] * cw
            gy = AH * 0.14 + (g["r"] + 0.85) * rh
            gx = CX + (gx - CX) * s
            gy = AH * 0.5 + (gy - AH * 0.5) * s
            dist = math.hypot(g["c"] - c0, (g["r"] - r0) * 1.6)
            infected = dist + g["delay"] < radius
            k = rh * 0.42 * s
            if infected:
                since = t - kf([(0.0, 0.6), (8.5, dur - 1.0)], dist + g["delay"], linear=True)
                inten = smoothstep(0, 0.8, since)
                p = ch.blend(ch.idle(t, ph=g["ph"], amp=0.6), ch.dance(t, ph=g["ph"], style=g["style"]), inten)
                colr = mix((150, 140, 140), (210, 40, 40), inten)
                draw_glow(fbuf, gx, gy - 0.9 * k, k * 2.4, (0.9, 0.15, 0.12), 0.25 * inten)
            else:
                p = ch.idle(t, ph=g["ph"], amp=0.6)
                colr = (120, 116, 120)
            _, h = ch.skeleton(p)
            ch.draw_figure(canvas, gx, gy - h * k, k, p, ch.TROFFEA, facing=1 if g["c"] % 2 else -1, silhouette=col(colr))
        # pulse rings from the centre
        for i in range(3):
            ph = (t * 0.45 + i / 3) % 1.0
            if t > 0.6:
                rr = ph * W * 0.7
                tmp, merge = overlay_alpha(canvas, 0.25 * (1 - ph))
                cv2.circle(tmp, P(CX, AH * 0.5), int(rr * 16), (200, 60, 60), 2, AA, 4)
                merge()
        ctx["captions"].append(("caption", "假说二：集体心因性疾病", smoothstep(0.4, 1.0, t) * (1 - smoothstep(dur - 0.6, dur - 0.2, t))))


# =============================================================================== S11  dawn

class S11_Dawn(Scene):
    name = "S11"
    grade = dict(lift=(0.01, 0.01, 0.02), gain=(1.0, 0.98, 1.0), gamma=1.05, sat=0.82, bloom=0.5, grain=0.045, vignette=0.6)

    def build(self):
        street_common_build(self, seed=11)
        self.ground = Ground(wd.cobble_tile(seed=3, wet=0.5, warm=0.3), ppm=128, camH=self.ground_y, fog=((150, 150, 160), 0.035))
        self.fog = fx.Fog(seed=112, color=(190, 188, 190))
        self.dust = fx.Dust(n=50, seed=113, color=(255, 235, 200), rad=(0.6, 1.4))
        self.lanterns = []
        rng = np.random.default_rng(7)
        for f in self.facades:
            if f.z0 > 4 and f.z0 < 40 and rng.random() < 0.35:
                self.lanterns.append((f.x - f.meta["side"] * 0.9, self.ground_y - 3.4, f.z0 + f.meta["w"] * 0.5, int(rng.integers(0, 1000))))
        self.lanterns.sort(key=lambda l: -l[2])
        self.smokes = [fx.Smoke((0, 0), rate=4, life=5, rise=22, wind=8, size0=5, growth=7, alpha0=0.18, color=(150, 150, 160), seed=i) for i in range(3)]

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        d = self.dur
        u = t / d
        # colour warms from blue-grey to pale gold over the shot
        warm = smoothstep(0.1, 0.9, u)
        sky = sky_gradient([(0, mix((60, 70, 96), (120, 120, 140), warm)), (0.5, mix((120, 128, 150), (210, 180, 150), warm)), (1, mix((150, 150, 158), (236, 210, 170), warm))])
        fog = (mix((140, 144, 158), (210, 196, 176), warm), 0.035)
        dx, dy = handheld(t, 2.0, 13)
        cam = Cam(x=0.1, y=-0.1, z=kf([(0, 6.0), (d, 3.6)], t), zoom=kf([(0, 1.25), (d, 1.02)], t), hy=AH * 0.5, dx=dx, dy=dy)
        canvas[:] = sky
        fx.draw_clouds(canvas, self.clouds, t, cam.hy, color=col(mix((170, 176, 190), (240, 220, 190), warm)), speed=6, lo=0.45, hi=0.9, gain=0.5)
        self.cathedral.draw(canvas, cam, fog=(mix((130, 136, 156), (215, 200, 180), warm), 0.02))
        self.ground.fog = fog
        self.ground.draw(canvas, cam)
        tint = mix((0.62, 0.66, 0.78), (1.0, 0.92, 0.82), warm)
        for f in self.facades:
            f.draw(canvas, cam, fog=fog, tint=tint)
        for i, (cx_, cy_, cz_) in enumerate(self.chimneys[:3]):
            if cz_ - cam.z < 8:
                continue
            sx, sy, k = cam.proj(cx_, cy_, cz_)
            self.smokes[i].origin = (sx, sy)
            self.smokes[i].draw(canvas, t, scale=clamp(k / 60, 0.3, 1.2), strength=0.7)
        for (lx, ly, lz, sd) in self.lanterns:
            lantern(canvas, fbuf, cam, lx, ly, lz, t, sd, swing=0.5, lit=(warm < 0.6), fog=fog)
        # a pair of red shoes left on the cobbles at Z ≈ 8.5
        for i, (sx_, sz_) in enumerate(((0.25, 8.4), (0.55, 8.55))):
            gp = cam.proj(sx_, self.ground_y - 0.03, sz_)
            k = gp[2]
            ang = -15 + 25 * i
            cv2.ellipse(canvas, P(gp[0], gp[1]), (int(0.14 * k * 16), int(0.05 * k * 16)), ang, 0, 360, (110, 30, 30), -1, AA, 4)
            cv2.ellipse(canvas, P(gp[0] - 0.05 * k, gp[1] - 0.03 * k), (int(0.07 * k * 16), int(0.06 * k * 16)), ang, 0, 360, (130, 36, 34), -1, AA, 4)
        fx.birds(canvas, t, (W * 0.2, AH * 0.2), n=5, seed=114, speed=(50, -8), size=4, color=(70, 72, 80))
        # sunrise glow low on the right
        draw_glow(fbuf, W * 0.62, cam.hy - 40, 420, (1.0, 0.75, 0.45), 0.35 * warm, aspect=0.6)
        vf = fx.vertical_fade(cam.hy - 20, cam.hy + 120)
        self.fog.draw(canvas, t, gain=0.4 * (1 - 0.4 * warm), vfade=vf, lo=0.3, hi=0.9)
        self.dust.draw(canvas, t, weight=0.35)


# =============================================================================== S12  credits

class S12_Credits(Scene):
    name = "S12"
    grade = dict(lift=(0, 0, 0), gain=(1, 1, 1), gamma=1.0, sat=1.0, bloom=0.3, grain=0.05, vignette=0.6)

    def build(self):
        self.dust = fx.Dust(n=80, seed=121, color=(200, 190, 170), rad=(0.5, 1.6))

    def draw(self, t, ctx):
        canvas, fbuf = ctx["canvas"], ctx["fbuf"]
        canvas[:] = (6, 5, 6)
        self.dust.draw(canvas, t, weight=0.4)
        a = smoothstep(0.3, 1.2, t) * (1 - smoothstep(self.dur - 1.0, self.dur - 0.3, t))
        draw_text(canvas, "1518 · 斯特拉斯堡", CX, AH * 0.36, size=40, serif=True, color=(200, 186, 160), opacity=a, spacing=6)
        draw_text(canvas, "史料：Waller, J. (2008) A Time to Dance, a Time to Die", CX, AH * 0.52, size=20, serif=False, color=(140, 132, 122), opacity=a * smoothstep(0.9, 1.6, t))
        draw_text(canvas, "本片为程序化生成的动画纪录片 · 人物与场景为艺术再现", CX, AH * 0.62, size=18, serif=False, color=(110, 104, 98), opacity=a * smoothstep(1.2, 1.9, t))
