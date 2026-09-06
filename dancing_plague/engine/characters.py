"""Procedural 2D character rigs (forward kinematics) with parametric motion cycles.

Side rig: pelvis-rooted skeleton (torso, head, 2 arms, 2 legs) in metres, facing +x.
Front rig: seated/standing figure facing the camera (used for the council scene).
Horse + cart rig for the road scene.  All motions are pure functions of time."""
from __future__ import annotations

import math
import numpy as np
import cv2

from .common import AA, P, PTS, col, mix, clamp01, smooth, lerp, Noise1D

TAU = math.tau

# segment lengths (m)
THIGH, SHIN, FOOT = 0.44, 0.42, 0.19
TORSO, NECK, HEAD_R = 0.50, 0.06, 0.105
UARM, FARM, HAND = 0.29, 0.26, 0.07


# ----------------------------------------------------------------------------- palettes

PALETTES = [
    dict(tunic=(96, 74, 58), hose=(58, 50, 46), skin=(214, 178, 146), hair=(60, 42, 30), cover=None, skirt=None),
    dict(tunic=(70, 78, 92), hose=(40, 40, 46), skin=(208, 170, 140), hair=(38, 30, 26), cover=(150, 140, 120), skirt=None),
    dict(tunic=(120, 60, 50), hose=(52, 46, 44), skin=(220, 185, 150), hair=(90, 60, 35), cover=None, skirt=None),
    dict(tunic=(82, 96, 74), hose=(46, 44, 40), skin=(205, 168, 138), hair=(50, 38, 28), cover=(170, 160, 140), skirt=(74, 84, 66)),
    dict(tunic=(140, 118, 84), hose=(60, 52, 48), skin=(216, 180, 148), hair=(70, 50, 34), cover=None, skirt=(120, 100, 70)),
    dict(tunic=(96, 90, 110), hose=(44, 42, 50), skin=(210, 172, 142), hair=(40, 34, 30), cover=(190, 180, 165), skirt=(84, 78, 98)),
    dict(tunic=(150, 80, 60), hose=(50, 44, 42), skin=(218, 182, 150), hair=(88, 62, 40), cover=None, skirt=(130, 70, 52)),
    dict(tunic=(60, 66, 70), hose=(36, 36, 40), skin=(200, 165, 135), hair=(30, 26, 24), cover=(120, 110, 100), skirt=None),
]
TROFFEA = dict(tunic=(140, 46, 40), hose=(60, 40, 40), skin=(222, 186, 154), hair=(70, 48, 32), cover=(176, 168, 150), skirt=(126, 40, 36))
DOCTOR = dict(tunic=(28, 26, 30), hose=(30, 28, 30), skin=(214, 178, 146), hair=(80, 74, 70), cover=(40, 36, 40), skirt=None)


def palette(i, rng=None):
    p = dict(PALETTES[i % len(PALETTES)])
    if rng is not None:
        jit = rng.uniform(0.85, 1.15)
        p["tunic"] = tuple(min(255, c * jit) for c in p["tunic"])
        if p["skirt"]:
            p["skirt"] = tuple(min(255, c * jit) for c in p["skirt"])
    return p


def shade_palette(p, tint=(1, 1, 1), fog=0.0, fogc=(0, 0, 0)):
    out = {}
    for k, v in p.items():
        if v is None:
            out[k] = None
        else:
            c = tuple(x * t for x, t in zip(v, tint))
            out[k] = tuple(a * (1 - fog) + b * fog for a, b in zip(c, fogc))
    return out


# ----------------------------------------------------------------------------- poses

def pose(**kw):
    p = dict(lean=0.0, head=0.0, sL=0.0, eL=0.15, sR=0.0, eR=0.15, hL=0.0, kL=0.0, hR=0.0, kR=0.0,
             jump=0.0, twist=0.0, ground=None, fL=0.0, fR=0.0)
    p.update(kw)
    return p


def blend(a, b, u):
    u = clamp01(u)
    out = {}
    for k in a:
        va, vb = a[k], b[k]
        if va is None or vb is None:
            out[k] = vb if u > 0.5 else va
        else:
            out[k] = va + (vb - va) * u
    return out


def idle(t, ph=0.0, amp=1.0):
    b = math.sin(t * 1.4 + ph)
    return pose(lean=0.03 * b * amp, head=0.04 * math.sin(t * 0.9 + ph), sL=0.05 * b, sR=-0.05 * b,
                eL=0.2, eR=0.2, kL=0.05, kR=0.05)


def walk(t, freq=1.8, stride=0.55, ph=0.0, lean=0.06, armswing=1.0, kmax=1.1, tired=0.0):
    w = TAU * freq * t + ph
    hL, hR = stride * math.sin(w), stride * math.sin(w + math.pi)
    kL = kmax * max(0.0, math.sin(w + 0.9)) ** 1.6 + 0.1 * tired
    kR = kmax * max(0.0, math.sin(w + math.pi + 0.9)) ** 1.6 + 0.1 * tired
    return pose(lean=lean + 0.25 * tired + 0.02 * math.sin(2 * w), head=0.03 * math.sin(2 * w) + 0.3 * tired,
                sL=-0.45 * armswing * math.sin(w) * (1 - 0.6 * tired), eL=0.35 + 0.15 * math.sin(w),
                sR=0.45 * armswing * math.sin(w) * (1 - 0.6 * tired), eR=0.35 - 0.15 * math.sin(w),
                hL=hL, kL=kL, hR=hR, kR=kR, fL=0.2 * math.sin(w), fR=0.2 * math.sin(w + math.pi))


def dance(t, ph=0.0, intensity=1.0, style=0, exhaust=0.0):
    """Frantic, involuntary dancing. style: 0 hop, 1 flail/stomp, 2 spin, 3 stagger."""
    I = intensity * (1 - 0.5 * exhaust)
    if style == 0:
        f = 2.3
        w = TAU * f * t + ph
        return pose(lean=0.15 * math.sin(w * 0.7) * I + 0.35 * exhaust, head=0.35 * math.sin(w * 1.7) * I,
                    sL=2.4 + 0.5 * math.sin(w * 1.3) * I, eL=0.7 + 0.5 * math.sin(w * 2.1),
                    sR=2.2 + 0.6 * math.cos(w) * I, eR=0.8 + 0.5 * math.cos(w * 1.9),
                    hL=0.35 * math.sin(w) * I, kL=0.5 + 0.5 * math.sin(2 * w) * I,
                    hR=0.35 * math.sin(w + math.pi) * I, kR=0.5 - 0.5 * math.sin(2 * w) * I,
                    jump=max(0.0, math.sin(2 * w)) * 0.13 * I, fL=-0.3, fR=-0.3)
    if style == 1:
        f = 1.9
        w = TAU * f * t + ph
        sL = 1.2 + 1.3 * math.sin(w * 1.5) * I
        sR = 1.4 + 1.2 * math.sin(w * 1.5 + 2.0) * I
        return pose(lean=0.25 * math.sin(w) * I + 0.3 * exhaust, head=-0.3 * math.sin(w) * I,
                    sL=sL, eL=0.9 + 0.6 * math.sin(w * 3.1), sR=sR, eR=0.9 + 0.6 * math.cos(w * 2.7),
                    hL=0.7 * max(0.0, math.sin(w)) * I, kL=1.3 * max(0.0, math.sin(w)) * I + 0.1,
                    hR=0.7 * max(0.0, math.sin(w + math.pi)) * I, kR=1.3 * max(0.0, math.sin(w + math.pi)) * I + 0.1,
                    jump=0.02 * max(0.0, math.sin(2 * w)), fL=0.3, fR=0.3)
    if style == 2:
        f = 1.4
        w = TAU * f * t + ph
        return pose(lean=0.1 * math.sin(w * 0.5) * I + 0.3 * exhaust, head=0.15 * math.sin(w * 3),
                    sL=1.6 + 0.3 * math.sin(w * 2), eL=0.3, sR=1.6 + 0.3 * math.cos(w * 2), eR=0.3,
                    hL=0.3 * math.sin(2 * w), kL=0.4 + 0.3 * math.sin(4 * w), hR=-0.3 * math.sin(2 * w), kR=0.4 - 0.3 * math.sin(4 * w),
                    jump=0.05 * max(0.0, math.sin(4 * w)), twist=w * 0.8)
    f = 1.1
    w = TAU * f * t + ph
    return pose(lean=0.45 * math.sin(w * 0.8) * I + 0.5 * exhaust, head=0.5 * math.sin(w * 1.3) + 0.3,
                sL=0.6 + 0.7 * math.sin(w * 1.1), eL=0.5, sR=0.4 + 0.7 * math.sin(w * 1.1 + 1.5), eR=0.5,
                hL=0.5 * math.sin(w), kL=0.6 + 0.4 * math.sin(2 * w), hR=0.5 * math.sin(w + math.pi), kR=0.6 - 0.4 * math.sin(2 * w),
                jump=0.0, fL=0.2, fR=0.2)


def lying(t, ph=0.0, twitch=1.0):
    tw = max(0.0, math.sin(t * 5.0 + ph)) ** 8 * twitch * 0.25
    return pose(lean=1.42, head=0.4 + tw, sL=1.2 + tw, eL=1.4, sR=0.6 - tw, eR=1.6, hL=1.1 + tw * 0.5, kL=0.9,
                hR=1.35, kR=0.7, ground=0.17, fL=0.4, fR=0.4)


def collapse(u, t, dance_pose):
    """Blend from an active dance pose to lying on the ground; u in [0,1]."""
    mid = pose(lean=0.9, head=0.6, sL=1.6, eL=0.9, sR=1.2, eR=1.1, hL=0.9, kL=1.6, hR=0.7, kR=1.7, ground=0.28)
    end = lying(t, twitch=0.0)
    if u < 0.55:
        return blend(dance_pose, mid, smooth(u / 0.55))
    return blend(mid, end, smooth((u - 0.55) / 0.45))


def kneel_pray(t, ph=0.0):
    bow = 0.45 + 0.4 * (0.5 - 0.5 * math.cos(t * 0.9 + ph))
    return pose(lean=bow, head=0.35 + 0.2 * bow, sL=1.3 + 0.3 * bow, eL=1.6, sR=1.25 + 0.3 * bow, eR=1.65,
                hL=0.05, kL=1.62, hR=0.02, kR=1.6, fL=-1.2, fR=-1.2)


def sick_lying(t, ph=0.0):
    br = 0.5 + 0.5 * math.sin(t * 2.2 + ph)
    return pose(lean=1.5, head=0.2 + 0.05 * br, sL=1.4, eL=0.9 + 0.1 * br, sR=1.3, eR=1.2, hL=1.3, kL=0.5, hR=1.2, kR=0.6,
                ground=0.16, fL=0.5, fR=0.5)


def shiver_walk(t, ph=0.0):
    p = walk(t, freq=1.5, stride=0.42, ph=ph, lean=0.42, armswing=0.0, kmax=0.9)
    sh = 0.05 * math.sin(t * 25)
    p.update(sL=1.4 + sh, eL=2.2, sR=1.3 - sh, eR=2.3, head=0.45 + sh)
    return p


# ----------------------------------------------------------------------------- side rig geometry

def skeleton(p):
    """Return joints in local metres (x forward, y up), origin at the pelvis, plus pelvis height above ground."""
    L = p["lean"]
    neck = (TORSO * math.sin(L), TORSO * math.cos(L))
    hd = L + p["head"]
    headc = (neck[0] + (NECK + HEAD_R) * math.sin(hd), neck[1] + (NECK + HEAD_R) * math.cos(hd))
    sh = (neck[0] - 0.04 * math.sin(L), neck[1] - 0.04 * math.cos(L))

    def arm(s, e):
        a1 = L + s  # angle from straight down, positive forward: direction (sin a, -cos a)
        el = (sh[0] + UARM * math.sin(a1), sh[1] - UARM * math.cos(a1))
        a2 = a1 + e
        ha = (el[0] + FARM * math.sin(a2), el[1] - FARM * math.cos(a2))
        return el, ha

    def leg(h, k, f):
        kn = (THIGH * math.sin(h), -THIGH * math.cos(h))
        a2 = h - k
        an = (kn[0] + SHIN * math.sin(a2), kn[1] - SHIN * math.cos(a2))
        toe = (an[0] + FOOT * math.cos(f - 0.1), an[1] - FOOT * math.sin(f - 0.1))
        return kn, an, toe

    elL, haL = arm(p["sL"], p["eL"])
    elR, haR = arm(p["sR"], p["eR"])
    knL, anL, toeL = leg(p["hL"], p["kL"], p["fL"])
    knR, anR, toeR = leg(p["hR"], p["kR"], p["fR"])
    low = min(knL[1], anL[1], knR[1], anR[1], toeL[1] + 0.02, toeR[1] + 0.02)
    h = -low + p["jump"]
    if p.get("ground") is not None:
        h = p["ground"] + p["jump"]
    return dict(neck=neck, head=headc, sh=sh, elL=elL, haL=haL, elR=elR, haR=haR,
                knL=knL, anL=anL, toeL=toeL, knR=knR, anR=anR, toeR=toeR), h


def draw_figure(canvas, px, py, k, p, pal, facing=1, silhouette=None, detail=True, alpha_hair=True,
                prop=None, hood=False):
    """Draw a side-view figure whose pelvis projects to (px, py); k = pixels per metre.
    Ground contact is handled by the caller through skeleton()'s height."""
    j, _ = skeleton(p)
    tw = p.get("twist", 0.0)
    xs = math.cos(tw)
    if abs(xs) < 0.15:
        xs = 0.15 if xs >= 0 else -0.15
    fx = facing * (1 if xs >= 0 else -1)
    sq = abs(xs)

    def S(pt):
        return (px + fx * pt[0] * k * sq + fx * 0.0, py - pt[1] * k)

    def th(m):
        return max(1, int(round(m * k)))

    if silhouette is not None:
        pal = dict(tunic=silhouette, hose=silhouette, skin=silhouette, hair=silhouette, cover=silhouette, skirt=silhouette if pal.get("skirt") else None)

    tunic, hose, skin, hair = col(pal["tunic"]), col(pal["hose"]), col(pal["skin"]), col(pal["hair"])
    dark_t = col(mix(pal["tunic"], (0, 0, 0), 0.35))
    far_h = col(mix(pal["hose"], (0, 0, 0), 0.3))
    far_s = col(mix(pal["skin"], (0, 0, 0), 0.3))
    pel = (px, py)

    def limb(a, b, c, w):
        cv2.line(canvas, P(*a), P(*b), c, w, AA, 4)

    # far leg
    limb(pel, S(j["knR"]), far_h, th(0.085))
    limb(S(j["knR"]), S(j["anR"]), far_h, th(0.07))
    limb(S(j["anR"]), S(j["toeR"]), far_h, th(0.06))
    # far arm
    limb(S(j["sh"]), S(j["elR"]), dark_t, th(0.075))
    limb(S(j["elR"]), S(j["haR"]), far_s if not hood else dark_t, th(0.06))
    # torso
    L = p["lean"]
    ux, uy = math.sin(L), math.cos(L)          # up along torso
    nx, ny = uy, -ux                           # forward normal
    hipw, shw = 0.13 * sq, 0.16 * sq
    poly = [(-nx * hipw, -ny * hipw - 0.06), (nx * hipw, ny * hipw - 0.06),
            (ux * TORSO + nx * shw, uy * TORSO + ny * shw), (ux * TORSO - nx * shw, uy * TORSO - ny * shw)]
    cv2.fillPoly(canvas, [PTS([S(q) for q in poly])], tunic, AA, 4)
    if pal.get("skirt"):
        sk = col(pal["skirt"])
        swing = 0.5 * (p["hL"] + p["hR"])
        bottom = -0.78
        poly = [(-0.14 * sq, -0.04), (0.14 * sq, -0.04), (0.30 * sq + swing * 0.25, bottom), (-0.26 * sq + swing * 0.25, bottom)]
        cv2.fillPoly(canvas, [PTS([S(q) for q in poly])], sk, AA, 4)
    # near leg
    limb(pel, S(j["knL"]), hose, th(0.09))
    limb(S(j["knL"]), S(j["anL"]), hose, th(0.075))
    limb(S(j["anL"]), S(j["toeL"]), col(mix(pal["hose"], (0, 0, 0), 0.4)) if silhouette is None else hose, th(0.065))
    # head
    hc = S(j["head"])
    r = max(2, int(round(HEAD_R * k)))
    cov = pal.get("cover")
    if hood:
        cv2.circle(canvas, P(hc[0] - fx * 0.02 * k, hc[1]), int(r * 1.3 * 16), col(cov or pal["tunic"]), -1, AA, 4)
        cv2.circle(canvas, P(hc[0] + fx * 0.02 * k, hc[1] + 0.01 * k), int(r * 0.78 * 16), col(mix(pal["skin"], (0, 0, 0), 0.35)), -1, AA, 4)
        # hood opening: cover the back 65 % of the head
        cv2.ellipse(canvas, P(hc[0], hc[1]), (int(r * 1.3 * 16), int(r * 1.3 * 16)), 0, 60 if fx > 0 else -120, 300 if fx > 0 else 120, col(cov or pal["tunic"]), -1, AA, 4)
    else:
        cv2.circle(canvas, P(*hc), r * 16, skin, -1, AA, 4)
        if cov:
            # kerchief: covers top and back of the head, drapes down the neck
            cv2.ellipse(canvas, P(hc[0], hc[1]), (int(r * 1.15 * 16), int(r * 1.15 * 16)), 0, 100 if fx > 0 else -80, 350 if fx > 0 else 170, col(cov), -1, AA, 4)
            cv2.fillPoly(canvas, [PTS([(hc[0] - fx * r * 0.85, hc[1] - r * 0.3), (hc[0] - fx * r * 1.25, hc[1] + r * 1.5), (hc[0] - fx * r * 0.15, hc[1] + r * 1.55), (hc[0] + fx * r * 0.2, hc[1] + r * 0.9)])], col(cov), AA, 4)
        else:
            # hair: cap over the top/back, small nape
            cv2.ellipse(canvas, P(hc[0] - fx * r * 0.08, hc[1] - r * 0.08), (int(r * 1.06 * 16), int(r * 1.02 * 16)), 0, 150 if fx > 0 else -30, 380 if fx > 0 else 200, hair, -1, AA, 4)
            cv2.fillPoly(canvas, [PTS([(hc[0] - fx * r * 0.95, hc[1] - r * 0.2), (hc[0] - fx * r * 0.9, hc[1] + r * 1.05), (hc[0] - fx * r * 0.35, hc[1] + r * 0.85)])], hair, AA, 4)
        # eye dot + brow hint when large enough
        if r >= 9 and silhouette is None:
            ex, ey = hc[0] + fx * r * 0.45, hc[1] - r * 0.12
            cv2.circle(canvas, P(ex, ey), max(1, int(r * 0.09 * 16)), (30, 22, 20), -1, AA, 4)
            cv2.line(canvas, P(ex - fx * r * 0.2, ey - r * 0.28), P(ex + fx * r * 0.18, ey - r * 0.3), col(mix(pal["skin"], (0, 0, 0), 0.6)), max(1, int(r * 0.06)), AA, 4)
    # near arm
    limb(S(j["sh"]), S(j["elL"]), tunic, th(0.08))
    limb(S(j["elL"]), S(j["haL"]), skin if not hood else tunic, th(0.065))
    if prop == "spear":
        hx, hy = S(j["haL"])
        cv2.line(canvas, P(hx, hy + 0.9 * k), P(hx + fx * 0.05 * k, hy - 1.4 * k), (70, 60, 50), max(1, int(0.03 * k)), AA, 4)
        cv2.fillPoly(canvas, [PTS([(hx + fx * 0.05 * k, hy - 1.4 * k), (hx + fx * 0.09 * k, hy - 1.15 * k), (hx + fx * 0.01 * k, hy - 1.15 * k)])], (170, 175, 185), AA, 4)
    if prop == "lantern":
        hx, hy = S(j["haL"])
        cv2.line(canvas, P(hx, hy), P(hx + fx * 0.08 * k, hy + 0.12 * k), (60, 50, 40), max(1, int(0.02 * k)), AA, 4)
        cv2.rectangle(canvas, P(hx + fx * 0.02 * k, hy + 0.12 * k), P(hx + fx * 0.16 * k, hy + 0.30 * k), (240, 190, 110), -1, AA, 4)


def place_figure(canvas, cam, X, Z, p, pal, camH, facing=1, **kw):
    """Project a standing figure at world (X, ground, Z). Returns (px, py, k) of the pelvis or None."""
    dz = Z - cam.z
    if dz < 0.6:
        return None
    _, h = skeleton(p)
    px, py, k = cam.proj(X, camH - h, Z)
    if px < -200 or px > canvas.shape[1] + 200 or py < -300 or py > canvas.shape[0] + 300:
        return None
    draw_figure(canvas, px, py, k, p, pal, facing=facing, **kw)
    return px, py, k


# ----------------------------------------------------------------------------- face (close-ups)

def draw_face(canvas, cx, cy, r, t, expr="neutral", skin=(222, 186, 154), look=(0.0, 0.0), blink_seed=0, talk=0.0,
              gaze_dart=0.0):
    """Frontal face inside a head of radius r at (cx, cy). expr: neutral | blank | fear | frown | tired."""
    n = Noise1D(blink_seed + 11)
    # blink: periodic quick closes
    per = 3.1 + 1.3 * n(t * 0.1)
    ph = (t % per) / per
    blink = max(0.0, 1 - abs(ph - 0.5) * 2 * 9) if 0.44 < ph < 0.56 else 0.0
    lid = {"neutral": 0.0, "blank": 0.18, "fear": -0.25, "frown": 0.12, "tired": 0.55}[expr]
    brow = {"neutral": 0.0, "blank": 0.05, "fear": -0.35, "frown": 0.3, "tired": 0.1}[expr]
    browtilt = {"neutral": 0.0, "blank": 0.0, "fear": 0.35, "frown": -0.3, "tired": 0.2}[expr]
    mouth_open = {"neutral": 0.05, "blank": 0.12, "fear": 0.5, "frown": 0.02, "tired": 0.25}[expr]
    mouth_curve = {"neutral": 0.05, "blank": -0.05, "fear": -0.25, "frown": -0.3, "tired": -0.15}[expr]
    if talk > 0:
        mouth_open = 0.1 + 0.4 * talk * max(0.0, math.sin(t * 14) * 0.6 + math.sin(t * 23) * 0.4)
    gx = look[0] + gaze_dart * n.signed(t * 3.0) * 0.6
    gy = look[1] + gaze_dart * n.signed(t * 2.3 + 50) * 0.3
    eye_y = cy - r * 0.08
    ex_off = r * 0.36
    ew, eh = r * 0.19, r * 0.11 * (1 - 0.85 * blink) * (1 - lid * 0.6 if lid > 0 else 1 + abs(lid))
    dark = col(mix(skin, (0, 0, 0), 0.55))
    for s in (-1, 1):
        ex = cx + s * ex_off
        # eye white
        cv2.ellipse(canvas, P(ex, eye_y), (int(ew * 16), max(1, int(eh * 16))), 0, 0, 360, (236, 228, 220), -1, AA, 4)
        # iris/pupil
        ir = r * 0.075
        ix, iy = ex + gx * ew * 0.5, eye_y + gy * eh * 0.5
        if eh > r * 0.02:
            cv2.circle(canvas, P(ix, iy), int(ir * 16), (70, 52, 40), -1, AA, 4)
            cv2.circle(canvas, P(ix, iy), int(ir * 0.5 * 16), (15, 12, 12), -1, AA, 4)
            cv2.circle(canvas, P(ix - ir * 0.3, iy - ir * 0.3), max(1, int(ir * 0.18 * 16)), (250, 250, 250), -1, AA, 4)
        # upper lid line
        cv2.ellipse(canvas, P(ex, eye_y), (int(ew * 16), max(1, int(eh * 16))), 0, 180, 360, dark, max(1, int(r * 0.03)), AA, 4)
        # brow
        by = eye_y - r * 0.28 + brow * r * 0.12
        b0 = (ex - ew * 1.2, by + s * browtilt * r * 0.08)
        b1 = (ex + ew * 1.2, by - s * browtilt * r * 0.08)
        cv2.line(canvas, P(*b0), P(*b1), col(mix(skin, (0, 0, 0), 0.7)), max(1, int(r * 0.05)), AA, 4)
    # nose
    cv2.line(canvas, P(cx, cy - r * 0.02), P(cx - r * 0.07, cy + r * 0.3), col(mix(skin, (0, 0, 0), 0.25)), max(1, int(r * 0.035)), AA, 4)
    # mouth
    my = cy + r * 0.55
    mw = r * 0.28
    mo = mouth_open * r * 0.22
    pts_top = [(cx - mw, my), (cx, my - mouth_curve * r * 0.15 * -1 * -1), (cx + mw, my)]
    if mo > r * 0.02:
        poly = [(cx - mw, my), (cx, my - r * 0.03), (cx + mw, my), (cx, my + mo)]
        cv2.fillPoly(canvas, [PTS(poly)], (60, 28, 30), AA, 4)
    else:
        cv2.polylines(canvas, [PTS([(cx - mw, my - mouth_curve * r * 0.2), (cx, my), (cx + mw, my - mouth_curve * r * 0.2)])], False, dark, max(1, int(r * 0.035)), AA, 4)


def draw_head_closeup(canvas, cx, cy, r, t, pal, expr, cover=True, talk=0.0, look=(0, 0), gaze_dart=0.0, seed=0,
                      turn=0.0, tremble=0.0):
    """Big frontal head with headscarf/hair. turn: -1..1 shifts features (fake yaw)."""
    tx = cx + turn * r * 0.25 + tremble * r * 0.02 * math.sin(t * 31)
    skin = col(pal["skin"])
    cov = pal.get("cover")
    if cover and cov:
        dark_c = col(mix(cov, (0, 0, 0), 0.3))
        # kerchief: rounded hood hugging the head, tied under the chin, tails falling behind the shoulders
        cv2.ellipse(canvas, P(cx, cy + r * 0.05), (int(r * 1.28 * 16), int(r * 1.35 * 16)), 0, 0, 360, col(cov), -1, AA, 4)
        cv2.fillPoly(canvas, [PTS([(cx - r * 1.2, cy + r * 0.3), (cx + r * 1.2, cy + r * 0.3), (cx + r * 1.45, cy + r * 2.9), (cx - r * 1.45, cy + r * 2.9)])], col(cov), AA, 4)
        # a few soft fold lines
        for sgn in (-1, 1):
            cv2.line(canvas, P(cx + sgn * r * 1.05, cy + r * 0.9), P(cx + sgn * r * 1.25, cy + r * 2.9), dark_c, max(1, int(r * 0.035)), AA, 4)
            cv2.line(canvas, P(cx + sgn * r * 0.75, cy + r * 1.4), P(cx + sgn * r * 0.85, cy + r * 2.9), dark_c, max(1, int(r * 0.025)), AA, 4)
    else:
        cv2.circle(canvas, P(cx, cy - r * 0.1), int(r * 1.12 * 16), col(pal["hair"]), -1, AA, 4)
    # neck
    cv2.rectangle(canvas, P(cx - r * 0.36, cy + r * 0.7), P(cx + r * 0.36, cy + r * 1.9), col(mix(pal["skin"], (0, 0, 0), 0.3)), -1, AA, 4)
    # face
    cv2.ellipse(canvas, P(cx, cy), (int(r * 0.86 * 16), int(r * 1.0 * 16)), 0, 0, 360, skin, -1, AA, 4)
    # soft shading on the shadow side (blurred mask blended with a darker skin tone)
    x0, y0 = int(cx - r * 1.4), int(cy - r * 1.4)
    x1, y1 = int(cx + r * 1.4), int(cy + r * 1.4)
    hh, ww = canvas.shape[:2]
    x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(ww, x1), min(hh, y1)
    if x1c > x0c and y1c > y0c:
        m = np.zeros((y1c - y0c, x1c - x0c), np.float32)
        cv2.ellipse(m, (int(cx - x0c + r * (0.55 + turn * 0.4)), int(cy - y0c + r * 0.15)), (int(r * 0.75), int(r * 1.0)), 0, 0, 360, 1.0, -1, AA)
        face_m = np.zeros_like(m)
        cv2.ellipse(face_m, (int(cx - x0c), int(cy - y0c)), (int(r * 0.86), int(r * 1.0)), 0, 0, 360, 1.0, -1, AA)
        m = cv2.GaussianBlur(m, (0, 0), r * 0.22) * face_m * 0.32
        roi = canvas[y0c:y1c, x0c:x1c]
        shade_c = np.asarray(mix(pal["skin"], (60, 30, 40), 0.55), np.float32)
        roi[:] = (roi * (1 - m[..., None]) + shade_c * m[..., None]).astype(np.uint8)
    if cover and cov:
        # inner edge of the hood casting a shadow onto the forehead / temples
        tmp = canvas.copy()
        cv2.ellipse(tmp, P(cx, cy - r * 0.02), (int(r * 0.98 * 16), int(r * 1.1 * 16)), 0, 195, 345, (20, 14, 14), max(2, int(r * 0.1)), AA, 4)
        cv2.addWeighted(tmp, 0.28, canvas, 0.72, 0, dst=canvas)
        cv2.ellipse(canvas, P(cx, cy - r * 0.02), (int(r * 1.0 * 16), int(r * 1.12 * 16)), 0, 190, 350, col(mix(cov, (0, 0, 0), 0.22)), max(2, int(r * 0.06)), AA, 4)
    else:
        cv2.ellipse(canvas, P(cx, cy - r * 0.55), (int(r * 0.9 * 16), int(r * 0.5 * 16)), 0, 180, 360, col(pal["hair"]), -1, AA, 4)
    draw_face(canvas, tx, cy, r * 0.9, t, expr, skin=pal["skin"], look=look, blink_seed=seed, talk=talk, gaze_dart=gaze_dart)


# ----------------------------------------------------------------------------- front rig (seated council)

def draw_front_figure(canvas, cx, base_y, k, t, pal, gesture="rest", ph=0.0, talk=0.0, expr="frown", seed=0,
                      head_shake=0.0, nod=0.0, table_y=None):
    """Seated figure facing the camera. base_y: pelvis/bench height in px; k px per metre."""
    tunic, skin = col(pal["tunic"]), col(pal["skin"])
    dark = col(mix(pal["tunic"], (0, 0, 0), 0.35))
    shw = 0.24 * k
    torso_h = 0.55 * k
    sway = 0.01 * k * math.sin(t * 0.7 + ph)
    top = base_y - torso_h
    poly = [(cx - 0.17 * k + sway, base_y), (cx + 0.17 * k + sway, base_y), (cx + shw + sway * 0.5, top), (cx - shw + sway * 0.5, top)]
    cv2.fillPoly(canvas, [PTS(poly)], tunic, AA, 4)
    # collar
    cv2.fillPoly(canvas, [PTS([(cx - 0.1 * k, top), (cx + 0.1 * k, top), (cx, top + 0.16 * k)])], col(mix(pal["tunic"], (255, 255, 255), 0.35)), AA, 4)
    # head
    hr = 0.115 * k
    hx = cx + sway * 0.5 + head_shake * hr * 0.35 * math.sin(t * 5.0 + ph)
    hy = top - 0.06 * k - hr + nod * hr * 0.2 * math.sin(t * 2.4 + ph)
    cv2.rectangle(canvas, P(hx - hr * 0.35, hy + hr * 0.7), P(hx + hr * 0.35, top + 2), col(mix(pal["skin"], (0, 0, 0), 0.2)), -1, AA, 4)
    if pal.get("cover"):
        cv2.ellipse(canvas, P(hx, hy - hr * 0.35), (int(hr * 1.15 * 16), int(hr * 0.9 * 16)), 0, 180, 360, col(pal["cover"]), -1, AA, 4)
        cv2.rectangle(canvas, P(hx - hr * 1.15, hy - hr * 0.35), P(hx + hr * 1.15, hy - hr * 0.1), col(pal["cover"]), -1, AA, 4)
    cv2.ellipse(canvas, P(hx, hy), (int(hr * 0.85 * 16), int(hr * 16)), 0, 0, 360, skin, -1, AA, 4)
    if not pal.get("cover"):
        cv2.ellipse(canvas, P(hx, hy - hr * 0.45), (int(hr * 0.9 * 16), int(hr * 0.55 * 16)), 0, 180, 360, col(pal["hair"]), -1, AA, 4)
    if hr > 9:
        turn = head_shake * 0.5 * math.sin(t * 5.0 + ph)
        draw_face(canvas, hx + turn * hr * 0.2, hy, hr * 0.92, t, expr, skin=pal["skin"], blink_seed=seed, talk=talk)
    # arms
    shL = (cx - shw * 0.85 + sway * 0.5, top + 0.05 * k)
    shR = (cx + shw * 0.85 + sway * 0.5, top + 0.05 * k)
    ty = table_y if table_y is not None else base_y - 0.05 * k
    w_arm = max(2, int(0.075 * k))
    w_fore = max(2, int(0.065 * k))

    def arm(sh, elbow, hand, hand_r=0.05):
        cv2.line(canvas, P(*sh), P(*elbow), dark, w_arm, AA, 4)
        cv2.line(canvas, P(*elbow), P(*hand), tunic, w_fore, AA, 4)
        cv2.circle(canvas, P(*hand), max(2, int(hand_r * k * 16)), skin, -1, AA, 4)

    if gesture == "rest":
        arm(shL, (shL[0] - 0.12 * k, ty - 0.02 * k), (cx - 0.12 * k, ty))
        arm(shR, (shR[0] + 0.12 * k, ty - 0.02 * k), (cx + 0.12 * k, ty))
    elif gesture == "write":
        wx = cx + 0.22 * k + 0.03 * k * math.sin(t * 9 + ph) + 0.06 * k * ((t * 0.35 + ph) % 1.0)
        wy = ty - 0.01 * k + 0.012 * k * math.sin(t * 17 + ph)
        arm(shL, (shL[0] - 0.14 * k, ty - 0.02 * k), (cx - 0.16 * k, ty))
        arm(shR, (shR[0] + 0.16 * k, ty - 0.06 * k), (wx, wy))
        # quill
        cv2.line(canvas, P(wx, wy), P(wx + 0.06 * k, wy - 0.3 * k), (230, 225, 210), max(1, int(0.02 * k)), AA, 4)
    elif gesture == "book":
        bx0, bx1, by = cx - 0.22 * k, cx + 0.22 * k, ty - 0.02 * k
        arm(shL, (shL[0] - 0.1 * k, ty - 0.05 * k), (bx0 + 0.02 * k, by - 0.05 * k))
        arm(shR, (shR[0] + 0.1 * k, ty - 0.05 * k), (bx1 - 0.02 * k, by - 0.05 * k))
        cv2.rectangle(canvas, P(bx0, by - 0.16 * k), P(bx1, by + 0.02 * k), (214, 198, 160), -1, AA, 4)
        cv2.line(canvas, P(cx, by - 0.16 * k), P(cx, by + 0.02 * k), (120, 100, 70), max(1, int(0.01 * k)), AA, 4)
        # turning page every ~3 s
        u = (t * 0.33 + ph) % 1.0
        if u < 0.25:
            a = u / 0.25
            px_ = cx + (bx1 - cx) * math.cos(a * math.pi)
            cv2.fillPoly(canvas, [PTS([(cx, by - 0.16 * k), (px_, by - 0.16 * k - 0.05 * k * math.sin(a * math.pi)), (px_, by + 0.02 * k - 0.05 * k * math.sin(a * math.pi)), (cx, by + 0.02 * k)])], (232, 220, 190), AA, 4)
    elif gesture == "point":
        raise_ = 0.5 + 0.5 * math.sin(t * 1.6 + ph)
        hx_, hy_ = cx + 0.45 * k, ty - 0.35 * k - 0.15 * k * raise_
        arm(shL, (shL[0] - 0.12 * k, ty - 0.02 * k), (cx - 0.14 * k, ty))
        arm(shR, (shR[0] + 0.2 * k, ty - 0.2 * k - 0.05 * k * raise_), (hx_, hy_), hand_r=0.045)
        cv2.line(canvas, P(hx_, hy_), P(hx_ + 0.09 * k, hy_ - 0.04 * k), skin, max(2, int(0.03 * k)), AA, 4)
    elif gesture == "slam":
        u = (t * 0.5 + ph) % 1.0
        lift = max(0.0, math.sin(u * math.pi * 2)) * 0.15 * k if u < 0.5 else 0.0
        arm(shL, (shL[0] - 0.12 * k, ty - 0.02 * k), (cx - 0.14 * k, ty))
        arm(shR, (shR[0] + 0.15 * k, ty - 0.1 * k - lift), (cx + 0.18 * k, ty - lift))


# ----------------------------------------------------------------------------- horse & cart

def draw_horse(canvas, px, py, k, t, ph=0.0, facing=1, color=(70, 56, 46), speed=1.0):
    """Walking horse; (px, py) = ground point below the chest; k px/m."""
    body_c = col(color)
    dark = col(mix(color, (0, 0, 0), 0.35))
    w = TAU * 1.05 * speed * t + ph
    bob = 0.02 * k * math.sin(2 * w)
    bx, by = px, py - 1.25 * k + bob   # body centre
    # legs: 4, phases for a walk gait
    for i, (dx, phs, cc) in enumerate(((0.55, 0.0, dark), (-0.55, math.pi, dark), (0.5, math.pi * 0.5, body_c), (-0.6, math.pi * 1.5, body_c))):
        a = 0.45 * math.sin(w + phs)
        kn = 0.6 * max(0.0, math.sin(w + phs + 0.8))
        hip = (bx + facing * dx * k, by + 0.25 * k)
        knee = (hip[0] + facing * math.sin(a) * 0.45 * k, hip[1] + math.cos(a) * 0.45 * k)
        a2 = a - kn * (1 if dx > 0 else -1) * 0.8
        hoof = (knee[0] + facing * math.sin(a2) * 0.5 * k, knee[1] + math.cos(a2) * 0.5 * k)
        hoof = (hoof[0], min(hoof[1], py))
        cv2.line(canvas, P(*hip), P(*knee), cc, max(2, int(0.11 * k)), AA, 4)
        cv2.line(canvas, P(*knee), P(*hoof), cc, max(2, int(0.08 * k)), AA, 4)
    cv2.ellipse(canvas, P(bx, by), (int(0.85 * k * 16), int(0.38 * k * 16)), 0, 0, 360, body_c, -1, AA, 4)
    # neck + head
    nb = (bx + facing * 0.7 * k, by - 0.15 * k)
    nod = 0.06 * k * math.sin(w)
    nt = (bx + facing * 1.2 * k, by - 0.75 * k + nod)
    cv2.line(canvas, P(*nb), P(*nt), body_c, max(3, int(0.3 * k)), AA, 4)
    cv2.ellipse(canvas, P(nt[0] + facing * 0.22 * k, nt[1] + 0.05 * k), (int(0.3 * k * 16), int(0.14 * k * 16)), 0, 0, 360, body_c, -1, AA, 4)
    cv2.line(canvas, P(nt[0] - facing * 0.05 * k, nt[1] - 0.05 * k), P(nt[0] - facing * 0.02 * k, nt[1] - 0.2 * k), dark, max(1, int(0.05 * k)), AA, 4)
    # mane & tail
    for i in range(4):
        u = i / 3
        mx, my = nb[0] + (nt[0] - nb[0]) * u, nb[1] + (nt[1] - nb[1]) * u
        cv2.line(canvas, P(mx, my), P(mx - facing * 0.12 * k, my - 0.12 * k + 0.02 * k * math.sin(t * 6 + i)), dark, max(1, int(0.05 * k)), AA, 4)
    tail = [(bx - facing * 0.8 * k, by - 0.05 * k)]
    for i in range(1, 5):
        tail.append((bx - facing * (0.8 + 0.08 * i) * k + facing * 0.05 * k * math.sin(t * 3 + i), by - 0.05 * k + 0.16 * i * k))
    cv2.polylines(canvas, [PTS(tail)], False, dark, max(1, int(0.07 * k)), AA, 4)


def draw_cart(canvas, px, py, k, dist, facing=1, color=(88, 70, 52), wheel_r=0.55):
    """Cart with base centre at ground point (px, py). dist = distance travelled (m) for wheel rotation."""
    body = col(color)
    dark = col(mix(color, (0, 0, 0), 0.4))
    ang = dist / wheel_r
    # bed
    y0 = py - (wheel_r + 0.25) * k
    cv2.rectangle(canvas, P(px - 1.3 * k, y0 - 0.9 * k), P(px + 1.3 * k, y0), body, -1, AA, 4)
    for i in range(-2, 3):
        cv2.line(canvas, P(px + i * 0.5 * k, y0 - 0.9 * k), P(px + i * 0.5 * k, y0), dark, max(1, int(0.03 * k)), AA, 4)
    cv2.line(canvas, P(px - 1.3 * k, y0 - 0.9 * k), P(px + 1.3 * k, y0 - 0.9 * k), dark, max(1, int(0.04 * k)), AA, 4)
    # shaft to the horse
    cv2.line(canvas, P(px + facing * 1.3 * k, y0), P(px + facing * 2.6 * k, y0 + 0.05 * k), dark, max(1, int(0.05 * k)), AA, 4)
    # wheels
    for wx in (px - 0.75 * k, px + 0.75 * k):
        wc = (wx, py - wheel_r * k)
        cv2.circle(canvas, P(*wc), int(wheel_r * k * 16), dark, max(2, int(0.07 * k)), AA, 4)
        for s in range(8):
            a = ang + s * math.pi / 4
            cv2.line(canvas, P(*wc), P(wc[0] + math.cos(a) * wheel_r * k, wc[1] + math.sin(a) * wheel_r * k), dark, max(1, int(0.035 * k)), AA, 4)
        cv2.circle(canvas, P(*wc), max(2, int(0.07 * k * 16)), (40, 34, 30), -1, AA, 4)
