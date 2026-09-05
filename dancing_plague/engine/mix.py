"""Build the full soundtrack: narration + per-shot ambience/SFX + music bed, with ducking. Writes a 48 kHz stereo WAV."""
from __future__ import annotations

import math
import os
import subprocess
import numpy as np
from scipy import signal
from scipy.io import wavfile

from . import audio as au
from .audio import SR, sec

FFMPEG = None


def decode_mp3(path, ffmpeg_bin):
    """Decode any audio file to float32 mono @ SR with ffmpeg."""
    out = subprocess.run([ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode())
    return np.frombuffer(out.stdout, np.float32).copy()


def trim_silence(x, thresh=0.01, pad=0.08):
    a = np.abs(x)
    idx = np.where(a > thresh)[0]
    if len(idx) == 0:
        return x
    i0 = max(0, idx[0] - sec(pad))
    i1 = min(len(x), idx[-1] + sec(pad))
    return x[i0:i1]


def place(track, x, t0, gain=1.0, fade_in=0.0, fade_out=0.0, pan=0.0):
    i = sec(t0)
    if i >= track.shape[0] or i + len(x) <= 0:
        return
    x = x.astype(np.float32) * gain
    if fade_in > 0:
        n = min(len(x), sec(fade_in))
        x[:n] *= np.linspace(0, 1, n, dtype=np.float32)
    if fade_out > 0:
        n = min(len(x), sec(fade_out))
        x[-n:] *= np.linspace(1, 0, n, dtype=np.float32)
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), track.shape[0] - i)
    l = math.cos((pan + 1) * math.pi / 4)
    r = math.sin((pan + 1) * math.pi / 4)
    track[i:i + n, 0] += x[:n] * l * 1.4142
    track[i:i + n, 1] += x[:n] * r * 1.4142


def norm(x, peak=1.0):
    m = np.abs(x).max()
    return x / m * peak if m > 0 else x


def build_soundtrack(shots, total, ffmpeg_bin, out_wav):
    rng = np.random.default_rng(2024)
    N = sec(total) + 1
    vo = np.zeros((N, 2), np.float32)
    amb = np.zeros((N, 2), np.float32)
    mus = np.zeros((N, 2), np.float32)
    sfx = np.zeros((N, 2), np.float32)
    by = {s["name"]: s for s in shots}

    # ------------------------------------------------------------------ narration
    vo_mono = np.zeros(N, np.float32)
    for s in shots:
        if not s["vo"]:
            continue
        x = decode_mp3(s["vo_path"], ffmpeg_bin)
        # light processing: high-pass, gentle compression
        x = au.highpass(x, 80)
        x = np.tanh(x * 1.6) / math.tanh(1.6)
        x = norm(x, 0.9)
        t0 = s["start"] + s["lead"]
        place(vo, x, t0, gain=1.0, fade_in=0.01, fade_out=0.05)
        i = sec(t0)
        n = min(len(x), N - i)
        vo_mono[i:i + n] += x[:n]

    # ------------------------------------------------------------------ helper to time segments
    def seg(name):
        s = by[name]
        return s["start"], s["dur"], sec(s["dur"]) + sec(0.6)

    # ------------------------------------------------------------------ S1 cold open: rain fading, drips, bell, low drone
    t0, d, n = seg("S1")
    rain = au.rain_bed(n, rng) * np.interp(np.arange(n), [0, sec(6), sec(9.5), n], [1.0, 0.55, 0.12, 0.08]).astype(np.float32)
    place(amb, rain, t0, gain=0.55, fade_in=1.0, fade_out=1.0)
    place(amb, au.wind_bed(n, rng, base=180), t0, gain=0.18, fade_in=2.0, fade_out=1.0)
    place(sfx, au.bell(n, 2.6, f0=164, decay=7, amp=1.0), t0, gain=0.9)
    place(sfx, au.bell(n, 8.9, f0=164, decay=7, amp=0.8), t0, gain=0.9)
    place(sfx, au.footsteps(n, rng, rate=1.6, count=1.0) * np.linspace(0.8, 0.0, n, dtype=np.float32), t0, gain=0.10)
    place(mus, au.pad_chord(n, [55.0, 82.4, 110.0], rng, amp=1.0, attack=3.0, release=2.0), t0, gain=0.34)
    # ------------------------------------------------------------------ S2 title: boom + heartbeat + swell
    t0, d, n = seg("S2")
    place(sfx, au.boom(n, 0.25, rng, amp=1.0), t0, gain=0.9)
    place(mus, au.pad_chord(n, [55.0, 65.4, 82.4, 98.0], rng, amp=1.0, attack=0.5, release=1.5), t0, gain=0.4)
    place(sfx, au.heartbeat(n, rate=0.9), t0, gain=0.5, fade_out=0.8)
    # ------------------------------------------------------------------ S3 Troffea: morning street, door, steps, birds; music enters uneasy
    t0, d, n = seg("S3")
    place(amb, au.wind_bed(n, rng, base=350), t0, gain=0.10, fade_in=0.5, fade_out=0.5)
    place(amb, au.crowd_bed(n, rng, size=0.3), t0, gain=0.10, fade_in=0.5, fade_out=0.5)
    place(sfx, au.door_creak(n, 0.05, rng, amp=1.0), t0, gain=0.2, pan=0.4)
    steps = au.footsteps(n, rng, rate=2.0, count=1.0)
    envs = np.interp(np.arange(n), [0, sec(2.2), sec(3.4), sec(5.2), n], [0.8, 0.8, 0.0, 1.2, 1.2]).astype(np.float32)
    place(sfx, steps * envs, t0, gain=0.22)
    place(sfx, au.whoosh(n, 4.6, 1.2, rng, amp=0.8, f0=800, f1=3000), t0, gain=0.25)  # birds startle
    place(mus, au.pad_chord(n, [58.3, 87.3, 116.5], rng, amp=1.0, attack=3.0, release=2.0), t0, gain=0.28)
    place(sfx, au.heartbeat(n, rate=1.0, start_rate=0.8) * np.interp(np.arange(n), [0, sec(8.0), n], [0.0, 0.0, 1.0]).astype(np.float32), t0, gain=0.45)
    # ------------------------------------------------------------------ S4 time-lapse: rising crowd, steps density, pulse
    t0, d, n = seg("S4")
    grow = np.interp(np.arange(n), [0, sec(3), sec(5.6), sec(8.2), n], [0.1, 0.25, 0.5, 0.85, 1.0]).astype(np.float32)
    place(amb, au.footsteps(n, rng, rate=6.0, count=3.0, shuffle=0.5) * grow, t0, gain=0.35, fade_in=0.3, fade_out=0.5)
    place(amb, au.crowd_bed(n, rng, size=1.0, distress=0.5) * grow, t0, gain=0.30, fade_in=0.3, fade_out=0.5)
    place(amb, au.wind_bed(n, rng, base=300), t0, gain=0.08, fade_in=0.5, fade_out=0.5)
    place(mus, au.pulse_drum(n, 66, rng, amp=1.0), t0, gain=0.42, fade_in=0.5, fade_out=0.5)
    place(mus, au.pad_chord(n, [55.0, 82.4, 98.0], rng, amp=1.0, attack=1.0, release=1.5), t0, gain=0.3)
    # ------------------------------------------------------------------ S5 square: big crowd, thuds when people fall
    t0, d, n = seg("S5")
    place(amb, au.crowd_bed(n, rng, size=1.6, distress=0.8), t0, gain=0.42, fade_in=0.6, fade_out=0.8)
    place(amb, au.footsteps(n, rng, rate=9.0, count=3.0, shuffle=0.7), t0, gain=0.28, fade_in=0.6, fade_out=0.8)
    place(amb, au.wind_bed(n, rng, base=260), t0, gain=0.12, fade_in=0.5, fade_out=0.5)
    for tt in (2.6, 4.1, 6.3, 7.9, 9.4, 10.8):
        place(sfx, au.thud(n, tt, rng, amp=1.0), t0, gain=0.32, pan=float(rng.uniform(-0.5, 0.5)))
    place(mus, au.pad_chord(n, [51.9, 77.8, 103.8, 123.5], rng, amp=1.0, attack=1.5, release=2.0), t0, gain=0.34)
    place(mus, au.pulse_drum(n, 72, rng, amp=1.0), t0, gain=0.3, fade_in=1.0, fade_out=1.0)
    # ------------------------------------------------------------------ S6 council: interior, quill, pages, candles, murmur
    t0, d, n = seg("S6")
    place(amb, au.wind_bed(n, rng, base=120), t0, gain=0.06, fade_in=0.5, fade_out=0.5)
    place(amb, au.quill(n, rng, amp=1.0) * np.interp(np.arange(n), [0, sec(7.6), n], [1.0, 1.0, 0.0]).astype(np.float32), t0, gain=0.16, fade_in=0.3, pan=-0.3)
    place(amb, au.candle_flicker(n, rng, amp=1.0), t0, gain=0.10)
    place(amb, au.crowd_bed(n, rng, size=0.15, distress=0.2), t0, gain=0.07, fade_in=0.5, fade_out=0.5)
    for tt in (1.2, 4.3, 7.0):
        place(sfx, au.whoosh(n, tt, 0.35, rng, amp=1.0, f0=1500, f1=600), t0, gain=0.14, pan=-0.4)  # page turns
    for tt in (2.1, 6.1):
        place(sfx, au.thud(n, tt, rng, amp=1.0), t0, gain=0.25, pan=0.5)  # table slap
    place(mus, au.pad_chord(n, [49.0, 73.4, 98.0], rng, amp=1.0, attack=1.5, release=2.0), t0, gain=0.28)
    # ------------------------------------------------------------------ S7 stage: live medieval music, fire, crowd
    t0, d, n = seg("S7")
    place(amb, au.fire_bed(n, rng, amp=1.0), t0, gain=0.30, fade_in=0.5, fade_out=0.8)
    place(amb, au.crowd_bed(n, rng, size=1.5, distress=0.9), t0, gain=0.34, fade_in=0.5, fade_out=0.8)
    place(amb, au.footsteps(n, rng, rate=8.0, count=3.0, shuffle=0.4, surface="wood"), t0, gain=0.3, fade_in=0.5, fade_out=0.8)
    place(mus, au.frame_drum_pattern(n, 112, rng, amp=1.0), t0, gain=0.5, fade_in=0.4, fade_out=1.2)
    place(mus, au.pipe_melody(n, rng, amp=1.0, bpm=112, key=233.1), t0, gain=0.26, fade_in=0.8, fade_out=1.5, pan=0.3)
    place(mus, au.pipe_melody(n, np.random.default_rng(5), amp=1.0, bpm=112, key=174.6), t0, gain=0.16, fade_in=1.5, fade_out=1.5, pan=-0.3)
    for tt in (5.2, 8.1, 10.4):
        place(sfx, au.thud(n, tt, rng, amp=1.0), t0, gain=0.45, pan=float(rng.uniform(-0.4, 0.4)))
    # ------------------------------------------------------------------ S8 road: wind, rain, wheels, hooves, distant bell
    t0, d, n = seg("S8")
    place(amb, au.wind_bed(n, rng, base=220, howl=0.4), t0, gain=0.34, fade_in=0.8, fade_out=1.0)
    place(amb, au.rain_bed(n, rng, intensity=0.5), t0, gain=0.18, fade_in=0.8, fade_out=1.0)
    place(sfx, au.creak_wheels(n, rng, rate=0.8, amp=1.0), t0, gain=0.22, pan=0.2)
    place(sfx, au.hooves(n, rng, rate=1.6, amp=1.0), t0, gain=0.24, pan=0.3)
    place(sfx, au.footsteps(n, rng, rate=5.0, count=2.0, shuffle=0.6, surface="dirt"), t0, gain=0.14)
    place(sfx, au.bell(n, 6.5, f0=196, decay=8, amp=1.0), t0, gain=0.45)
    place(sfx, au.bell(n, 10.5, f0=196, decay=8, amp=0.8), t0, gain=0.45)
    place(mus, au.pad_chord(n, [46.2, 69.3, 92.5, 116.5], rng, amp=1.0, attack=2.0, release=2.5), t0, gain=0.32)
    # ------------------------------------------------------------------ S9 ergot: wind in rye, low hum, heartbeat
    t0, d, n = seg("S9")
    place(amb, au.wind_bed(n, rng, base=500), t0, gain=0.22, fade_in=0.8, fade_out=0.8)
    place(amb, au.bandpass(au.noise(n, rng, "white"), 2000, 6000) * au.slow_lfo(n, rng, 0.4, 0.8), t0, gain=0.05)
    place(mus, au.drone(n, 55.0, rng, amp=1.0, dark=1.0), t0, gain=0.3, fade_in=1.0, fade_out=1.0)
    place(mus, au.pad_chord(n, [65.4, 98.0, 130.8], rng, amp=1.0, attack=3.0, release=2.0), t0, gain=0.2)
    place(sfx, au.heartbeat(n, rate=1.0) * np.interp(np.arange(n), [0, sec(d - 5.4), sec(d - 3.0), sec(d - 1.5), n], [0, 0.0, 1.0, 1.0, 0.0]).astype(np.float32), t0, gain=0.5)
    place(sfx, au.thud(n, d - 1.25, rng, amp=1.0), t0, gain=0.5)
    # ------------------------------------------------------------------ S10 montage: snow wind → cough/breath → whispers → drum/heartbeat build
    t0, d, n = seg("S10")
    A_END, B_END, C_END = 5.2, 9.2, 13.4
    w = au.wind_bed(n, rng, base=300, howl=0.8) * np.interp(np.arange(n), [0, sec(A_END - 0.3), sec(A_END + 0.2), n], [1, 1, 0.0, 0.0]).astype(np.float32)
    place(amb, w, t0, gain=0.4, fade_in=0.3)
    place(amb, au.footsteps(n, rng, rate=4.0, count=1.5, shuffle=0.5, surface="dirt") * np.interp(np.arange(n), [0, sec(A_END), sec(A_END + 0.1), n], [1, 1, 0, 0]).astype(np.float32), t0, gain=0.1)
    # sickbed: laboured breathing + candle
    br = np.zeros(n, np.float32)
    tt = A_END + 0.2
    while tt < B_END:
        L = sec(0.8)
        i = sec(tt)
        x = au.bandpass(rng.standard_normal(L).astype(np.float32), 300, 1500) * (np.sin(np.pi * np.arange(L) / L) ** 2)
        br[i:i + L] += x * 0.8
        tt += 1.5
    place(sfx, br, t0, gain=0.12, pan=-0.2)
    place(amb, au.candle_flicker(n, rng) * np.interp(np.arange(n), [0, sec(A_END), sec(B_END), sec(C_END), n], [0, 1, 1, 1, 0]).astype(np.float32), t0, gain=0.08)
    # shrine: whispering prayers = filtered crowd murmur
    pr = au.crowd_bed(n, rng, size=0.5, distress=0.0)
    pr = au.bandpass(pr, 400, 2200) * np.interp(np.arange(n), [0, sec(B_END), sec(B_END + 0.4), sec(C_END), sec(C_END + 0.2), n], [0, 0, 1, 1, 0, 0]).astype(np.float32)
    place(amb, pr, t0, gain=0.22)
    place(sfx, au.bell(n, B_END + 0.3, f0=220, decay=6, amp=1.0), t0, gain=0.4)
    # grid: heartbeat accelerating + drum build + rising drone
    hb = au.heartbeat(n, rate=1.5, start_rate=0.9) * np.interp(np.arange(n), [0, sec(C_END), sec(C_END + 0.5), sec(d - 0.6), n], [0, 0, 1, 1, 0]).astype(np.float32)
    place(sfx, hb, t0, gain=0.6)
    dr = au.pulse_drum(n, 84, rng, amp=1.0, start=C_END) * np.interp(np.arange(n), [0, sec(C_END), sec(d - 0.8), n], [0, 0.5, 1.0, 0]).astype(np.float32)
    place(mus, dr, t0, gain=0.42)
    place(mus, au.pad_chord(n, [49.0, 58.3, 73.4, 98.0], rng, amp=1.0, attack=2.0, release=1.0) * np.interp(np.arange(n), [0, sec(C_END), n], [0.6, 0.8, 1.3]).astype(np.float32), t0, gain=0.3)
    place(sfx, au.whoosh(n, d - 0.9, 0.9, rng, amp=1.0, f0=300, f1=4000), t0, gain=0.3)
    # ------------------------------------------------------------------ S11 dawn: drips, birds, distant bell, resolving chord
    t0, d, n = seg("S11")
    place(sfx, au.boom(n, 0.0, rng, amp=1.0, f=40), t0, gain=0.5)
    drips = au.rain_bed(n, rng, intensity=1.5) * 0.15
    place(amb, drips, t0, gain=0.25, fade_in=0.5, fade_out=2.0)
    place(amb, au.wind_bed(n, rng, base=200), t0, gain=0.12, fade_in=0.5, fade_out=2.0)
    # bird chirps
    for _ in range(7):
        tt = float(rng.uniform(2.0, d - 1.0))
        L = sec(0.18)
        i = sec(tt)
        f = float(rng.uniform(2200, 3800))
        x = np.sin(2 * np.pi * (f + 600 * np.sin(np.linspace(0, 9, L))) * np.arange(L) / SR).astype(np.float32) * au.env_asr(L, 0.02, 0.08)
        chirp = np.zeros(n, np.float32)
        chirp[i:i + L] = x
        place(sfx, chirp, t0, gain=0.06, pan=float(rng.uniform(-0.7, 0.7)))
    place(sfx, au.bell(n, 3.2, f0=164, decay=9, amp=1.0), t0, gain=0.6)
    place(mus, au.pad_chord(n, [55.0, 82.4, 110.0, 138.6], rng, amp=1.0, attack=3.5, release=3.0), t0, gain=0.34)
    # ------------------------------------------------------------------ S12 credits: tail of chord
    t0, d, n = seg("S12")
    place(mus, au.pad_chord(n, [55.0, 82.4, 110.0], rng, amp=1.0, attack=0.5, release=3.5), t0, gain=0.22)

    # ------------------------------------------------------------------ ducking: lower beds while narration is present
    env = np.abs(vo_mono)
    env = au.lowpass(env, 6.0)
    env = np.convolve(env, np.ones(sec(0.25), np.float32) / sec(0.25), mode="same")
    duck = 1.0 - 0.7 * np.clip(env / (env.max() + 1e-6) * 3.0, 0, 1)
    duck = au.lowpass(duck.astype(np.float32), 3.0)
    duck = np.clip(duck, 0.3, 1.0)[:, None]
    BED, SFXG = 0.55, 0.6  # documentary balance: narration clearly on top of the bed
    bed = (amb * 1.0 + mus * 1.0) * duck * BED + sfx * (0.5 + 0.5 * duck) * SFXG
    mixd = bed + vo * 1.0
    # gentle bus compression / limiter
    mixd = np.tanh(mixd * 1.15) / math.tanh(1.15)
    peak = np.abs(mixd).max()
    if peak > 0.95:
        mixd *= 0.95 / peak
    # master fade in/out
    fi, fo = sec(1.0), sec(2.0)
    mixd[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]
    mixd[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
    wavfile.write(out_wav, SR, (np.clip(mixd, -1, 1) * 32767).astype(np.int16))
    return out_wav
