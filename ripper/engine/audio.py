"""Procedural sound design + music bed, mixed with the narration into a single stereo WAV.
Pure numpy/scipy; every cue is a function of the timeline so it stays in sync with the picture."""
from __future__ import annotations

import math
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000


def sec(n):
    return int(n * SR)


def env_asr(n, a, r, s=1.0):
    e = np.ones(n, np.float32) * s
    na, nr = min(n, sec(a)), min(n, sec(r))
    if na > 0:
        e[:na] *= np.linspace(0, 1, na, dtype=np.float32)
    if nr > 0:
        e[-nr:] *= np.linspace(1, 0, nr, dtype=np.float32)
    return e


def noise(n, rng, color="white"):
    x = rng.standard_normal(n).astype(np.float32)
    if color == "pink":
        b, a = signal.butter(1, 400 / (SR / 2), "low")
        x = signal.lfilter(b, a, x).astype(np.float32) * 4 + x * 0.25
    elif color == "brown":
        x = np.cumsum(x) / 40
        x -= np.mean(x)
        x = signal.lfilter(*signal.butter(1, 20 / (SR / 2), "high"), x).astype(np.float32)
    return x / (np.abs(x).max() + 1e-6)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], "band")
    return signal.lfilter(b, a, x).astype(np.float32)


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, min(fc, SR / 2 - 100) / (SR / 2), "low")
    return signal.lfilter(b, a, x).astype(np.float32)


def highpass(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high")
    return signal.lfilter(b, a, x).astype(np.float32)


def slow_lfo(n, rng, rate=0.2, depth=0.5):
    """Smooth random modulation in [1-depth, 1+depth]."""
    k = max(4, int(n / SR * rate) + 2)
    pts = rng.standard_normal(k)
    t = np.linspace(0, 1, n, dtype=np.float32)
    lfo = np.interp(t, np.linspace(0, 1, k), pts)
    lfo = lowpass(lfo.astype(np.float32), 2.0)
    lfo /= (np.abs(lfo).max() + 1e-6)
    return 1 + depth * lfo


# ----------------------------------------------------------------------------- textures

def rain_bed(n, rng, intensity=1.0):
    x = noise(n, rng, "white")
    x = bandpass(x, 900, 9000) * 0.6 + lowpass(noise(n, rng, "white"), 500) * 0.4
    # droplets
    drops = np.zeros(n, np.float32)
    k = int(n / SR * 22 * intensity)
    idx = rng.integers(0, n - 400, k)
    for i in idx:
        L = rng.integers(80, 400)
        drops[i:i + L] += rng.uniform(0.2, 1.0) * np.exp(-np.arange(L) / (L / 4)) * rng.standard_normal(L)
    x = x + bandpass(drops, 1500, 7000) * 0.5
    return x * slow_lfo(n, rng, 0.3, 0.2)


def wind_bed(n, rng, base=250, howl=0.0):
    x = noise(n, rng, "pink")
    lfo = slow_lfo(n, rng, 0.15, 0.6)
    out = np.zeros(n, np.float32)
    chunk = SR // 4
    for i in range(0, n, chunk):
        fc = base * float(lfo[min(i, n - 1)]) * (1 + 0.5 * howl)
        seg = x[i:i + chunk]
        out[i:i + chunk] = bandpass(seg, max(40, fc * 0.5), fc * 2.5 + 100)
    out *= lfo ** 1.5
    if howl > 0:
        tone = np.sin(2 * math.pi * np.cumsum(lfo * 300 * howl) / SR).astype(np.float32) * 0.08 * howl
        out += tone * lfo
    return out / (np.abs(out).max() + 1e-6)


def crowd_bed(n, rng, size=1.0, distress=0.0):
    """Murmuring crowd: many short filtered noise bursts."""
    out = np.zeros(n, np.float32)
    k = int(n / SR * 40 * size)
    for _ in range(k):
        L = rng.integers(sec(0.08), sec(0.5))
        i = rng.integers(0, max(1, n - L))
        f = rng.uniform(150, 500) * (1 + 0.6 * distress * rng.random())
        seg = bandpass(rng.standard_normal(L).astype(np.float32), f, f * 3.2) * env_asr(L, 0.02, 0.06)
        vib = np.sin(np.linspace(0, rng.uniform(4, 14), L)) * 0.4 + 0.6
        out[i:i + L] += seg * rng.uniform(0.2, 1.0) * vib
    out = lowpass(out, 2500)
    return out / (np.abs(out).max() + 1e-6)


def footsteps(n, rng, rate=2.0, count=1.0, shuffle=0.0, surface="stone"):
    out = np.zeros(n, np.float32)
    k = int(n / SR * rate * count)
    for _ in range(k):
        i = rng.integers(0, n - sec(0.2))
        L = sec(rng.uniform(0.04, 0.12) * (1 + shuffle))
        burst = rng.standard_normal(L).astype(np.float32) * np.exp(-np.arange(L) / (L / 5))
        f = rng.uniform(120, 400) if surface == "stone" else rng.uniform(80, 200)
        out[i:i + L] += bandpass(burst, f, f * 6) * rng.uniform(0.3, 1.0)
    return out / (np.abs(out).max() + 1e-6)


def heartbeat(n, rate=1.0, start_rate=None):
    out = np.zeros(n, np.float32)
    t = 0.0
    dur = n / SR
    while t < dur:
        u = t / dur
        r = rate if start_rate is None else start_rate + (rate - start_rate) * u
        for off, amp in ((0.0, 1.0), (0.16, 0.7)):
            i = sec(t + off)
            L = sec(0.14)
            if i + L < n:
                tt = np.arange(L) / SR
                thump = np.sin(2 * math.pi * 52 * tt) * np.exp(-tt * 28) * amp
                out[i:i + L] += thump.astype(np.float32)
        t += 60.0 / (72 * r)
    return out


def bell(n, t0, f0=180.0, decay=6.0, amp=1.0):
    out = np.zeros(n, np.float32)
    i = sec(t0)
    L = min(n - i, sec(decay * 1.5))
    if L <= 0:
        return out
    tt = np.arange(L) / SR
    tone = np.zeros(L, np.float32)
    for r, a, d in ((0.5, 0.6, 1.0), (1.0, 1.0, 0.8), (1.2, 0.5, 0.7), (1.5, 0.35, 0.5), (2.0, 0.3, 0.4), (2.67, 0.25, 0.3), (3.0, 0.2, 0.25)):
        tone += a * np.sin(2 * math.pi * f0 * r * tt) * np.exp(-tt / (decay * d))
    tone *= np.minimum(1, tt * 400)
    out[i:i + L] += tone * amp * 0.12
    return out


def drone(n, freq, rng, amp=1.0, detune=0.5, dark=1.0):
    tt = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for k, a in ((1, 1.0), (2, 0.4), (3, 0.2), (1.5, 0.25)):
        for d in (-detune, 0, detune):
            x += a * np.sin(2 * math.pi * (freq * k + d * k) * tt + rng.random() * 6.28)
    x *= slow_lfo(n, rng, 0.12, 0.35)
    x = lowpass(x, 400 + 600 * (1 - dark))
    return x / (np.abs(x).max() + 1e-6) * amp


def pad_chord(n, freqs, rng, amp=1.0, attack=2.0, release=3.0):
    out = np.zeros(n, np.float32)
    for f in freqs:
        out += drone(n, f, rng, 1.0, detune=0.35, dark=0.6)
    out /= max(1, len(freqs))
    return out * env_asr(n, attack, release) * amp


def pulse_drum(n, bpm, rng, amp=1.0, accent_every=4, start=0.0):
    out = np.zeros(n, np.float32)
    period = 60.0 / bpm
    t = start
    k = 0
    while t < n / SR:
        i = sec(t)
        L = sec(0.25)
        if i + L < n:
            tt = np.arange(L) / SR
            f = 70 if k % accent_every == 0 else 95
            hit = np.sin(2 * math.pi * f * tt * np.exp(-tt * 6)) * np.exp(-tt * 18)
            hit += rng.standard_normal(L) * np.exp(-tt * 70) * 0.35
            out[i:i + L] += hit.astype(np.float32) * (1.0 if k % accent_every == 0 else 0.6)
        t += period
        k += 1
    return out * amp


def frame_drum_pattern(n, bpm, rng, amp=1.0):
    """Medieval tabor rhythm: DUM da-da DUM da."""
    pat = [(0, 1.0), (0.5, 0.5), (0.75, 0.5), (1.0, 1.0), (1.5, 0.6), (2.0, 1.0), (2.5, 0.5), (2.75, 0.5), (3.0, 1.0), (3.5, 0.6)]
    out = np.zeros(n, np.float32)
    beat = 60.0 / bpm
    t0 = 0.0
    while t0 < n / SR:
        for off, a in pat:
            i = sec(t0 + off * beat)
            L = sec(0.18)
            if i + L < n:
                tt = np.arange(L) / SR
                hit = np.sin(2 * math.pi * 110 * tt * np.exp(-tt * 9)) * np.exp(-tt * 24) * a
                hit += rng.standard_normal(L) * np.exp(-tt * 90) * 0.25 * a
                out[i:i + L] += hit.astype(np.float32)
        t0 += 4 * beat
    return out * amp


def pipe_melody(n, rng, amp=1.0, bpm=112, key=220.0):
    """Reedy shawm/bagpipe-like melody in dorian mode with a droning fifth."""
    scale = [0, 2, 3, 5, 7, 9, 10, 12, 14, 15]
    out = np.zeros(n, np.float32)
    beat = 60.0 / bpm
    t = 0.0
    deg = 4
    while t < n / SR:
        L_beats = rng.choice([0.5, 0.5, 1.0, 1.0, 1.5, 2.0])
        L = sec(L_beats * beat)
        i = sec(t)
        if i + L >= n:
            break
        deg = int(np.clip(deg + rng.choice([-2, -1, -1, 0, 1, 1, 2, 3]), 0, len(scale) - 1))
        f = key * 2 ** (scale[deg] / 12)
        tt = np.arange(L) / SR
        vib = 1 + 0.006 * np.sin(2 * math.pi * 5.5 * tt)
        tone = np.zeros(L, np.float32)
        for k, a in ((1, 1.0), (2, 0.7), (3, 0.6), (4, 0.4), (5, 0.35), (6, 0.25), (7, 0.2)):
            tone += a * np.sin(2 * math.pi * f * k * vib * tt)
        tone *= env_asr(L, 0.02, 0.05, 1.0)
        out[i:i + L] += tone
        t += L_beats * beat
    tt = np.arange(n) / SR
    dr = np.sin(2 * math.pi * key / 2 * tt) + 0.5 * np.sin(2 * math.pi * key / 2 * 3 * tt) + 0.5 * np.sin(2 * math.pi * key * 0.75 * tt)
    out = out / (np.abs(out).max() + 1e-6) * 0.8 + dr / 2 * 0.25
    out = bandpass(out, 150, 5000)
    return out / (np.abs(out).max() + 1e-6) * amp


def creak_wheels(n, rng, rate=0.7, amp=1.0):
    out = np.zeros(n, np.float32)
    t = 0.0
    while t < n / SR:
        L = sec(rng.uniform(0.3, 0.7))
        i = sec(t)
        if i + L >= n:
            break
        tt = np.arange(L) / SR
        f = rng.uniform(600, 1400)
        sweep = f * (1 + 0.3 * np.sin(2 * math.pi * 1.5 * tt))
        x = np.sin(2 * math.pi * np.cumsum(sweep) / SR) * env_asr(L, 0.05, 0.15)
        x += rng.standard_normal(L) * 0.1 * env_asr(L, 0.05, 0.15)
        out[i:i + L] += bandpass(x.astype(np.float32), 400, 3000) * rng.uniform(0.4, 1.0)
        t += 1.0 / rate * rng.uniform(0.7, 1.3)
    return out / (np.abs(out).max() + 1e-6) * amp


def hooves(n, rng, rate=1.8, amp=1.0):
    out = np.zeros(n, np.float32)
    t = 0.0
    while t < n / SR:
        for off in (0.0, 0.12, 0.27, 0.41):
            i = sec(t + off)
            L = sec(0.06)
            if i + L < n:
                tt = np.arange(L) / SR
                hit = np.sin(2 * math.pi * 200 * tt) * np.exp(-tt * 90) + rng.standard_normal(L) * np.exp(-tt * 200) * 0.6
                out[i:i + L] += hit.astype(np.float32) * rng.uniform(0.5, 1.0)
        t += 1.0 / rate
    return lowpass(out, 3000) / (np.abs(out).max() + 1e-6) * amp


def fire_bed(n, rng, amp=1.0):
    x = lowpass(noise(n, rng, "brown"), 900) * 0.5
    pops = np.zeros(n, np.float32)
    k = int(n / SR * 9)
    for i in rng.integers(0, n - 800, k):
        L = rng.integers(100, 700)
        pops[i:i + L] += rng.standard_normal(L) * np.exp(-np.arange(L) / (L / 3)) * rng.uniform(0.3, 1.0)
    x += bandpass(pops, 1500, 8000) * 0.6
    return x * slow_lfo(n, rng, 0.5, 0.3) / (np.abs(x).max() + 1e-6) * amp


def quill(n, rng, amp=1.0):
    x = noise(n, rng, "white")
    x = bandpass(x, 2500, 9000)
    lfo = (np.sin(2 * math.pi * 3.2 * np.arange(n) / SR) ** 6).astype(np.float32) * slow_lfo(n, rng, 0.5, 0.5)
    return x * lfo * amp


def candle_flicker(n, rng, amp=1.0):
    x = bandpass(noise(n, rng, "white"), 3000, 12000)
    lfo = slow_lfo(n, rng, 2.0, 0.9)
    lfo = np.clip(lfo - 0.9, 0, None) ** 2
    return x * lfo / (np.abs(x * lfo).max() + 1e-6) * amp


def whoosh(n, t0, dur, rng, amp=1.0, f0=200, f1=2000):
    out = np.zeros(n, np.float32)
    L = sec(dur)
    i = sec(t0)
    if i + L >= n:
        return out
    x = noise(L, rng, "white")
    tt = np.linspace(0, 1, L)
    seg = np.zeros(L, np.float32)
    chunk = SR // 20
    for j in range(0, L, chunk):
        u = j / L
        fc = f0 + (f1 - f0) * u
        seg[j:j + chunk] = bandpass(x[j:j + chunk], fc * 0.6, fc * 1.6)
    seg *= np.sin(np.pi * tt) ** 1.5
    out[i:i + L] += seg * amp
    return out


def boom(n, t0, rng, amp=1.0, f=45.0):
    out = np.zeros(n, np.float32)
    L = sec(3.0)
    i = sec(t0)
    if i + L >= n:
        L = n - i - 1
    tt = np.arange(L) / SR
    x = np.sin(2 * math.pi * f * tt * np.exp(-tt * 0.8)) * np.exp(-tt * 1.6)
    x += lowpass(rng.standard_normal(L).astype(np.float32), 200) * np.exp(-tt * 6) * 0.5
    out[i:i + L] += x.astype(np.float32) * amp
    return out


def thud(n, t0, rng, amp=1.0):
    out = np.zeros(n, np.float32)
    L = sec(0.35)
    i = sec(t0)
    if i + L >= n:
        return out
    tt = np.arange(L) / SR
    x = np.sin(2 * math.pi * 80 * tt * np.exp(-tt * 12)) * np.exp(-tt * 20) + lowpass(rng.standard_normal(L).astype(np.float32), 600) * np.exp(-tt * 30) * 0.6
    out[i:i + L] += x.astype(np.float32) * amp
    return out


def door_creak(n, t0, rng, amp=1.0):
    out = np.zeros(n, np.float32)
    L = sec(1.1)
    i = sec(t0)
    if i + L >= n:
        return out
    tt = np.arange(L) / SR
    f = 380 + 260 * np.sin(2 * math.pi * 0.7 * tt) + 40 * np.sin(2 * math.pi * 11 * tt)
    x = np.sign(np.sin(2 * math.pi * np.cumsum(f) / SR)) * 0.3 + np.sin(2 * math.pi * np.cumsum(f) / SR)
    x = bandpass(x.astype(np.float32), 200, 2500) * env_asr(L, 0.1, 0.3)
    out[i:i + L] += x * amp
    return out


def stereo_place(x, pan=0.0, width=0.0, rng=None):
    """Return (L, R) from mono with constant-power pan and optional decorrelated widening."""
    l = math.cos((pan + 1) * math.pi / 4)
    r = math.sin((pan + 1) * math.pi / 4)
    L, R = x * l, x * r
    if width > 0 and rng is not None:
        d = int(SR * 0.012)
        R = np.concatenate([np.zeros(d, np.float32), R[:-d]]) * (1 - width) + R * width
    return L, R
