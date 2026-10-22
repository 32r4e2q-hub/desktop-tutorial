#!/usr/bin/env python3
"""《玛丽·赛勒斯特号》原创分段配乐（numpy 直接合成，不采样、不依赖外部素材）。

用户脚本的每段 BGM 设计，在这里逐段落实（时间轴按 render.py 的 CHAPTER_WINDOWS 与
镜头实际切点 shot_times 注入；S17『嘭』后静音一秒、S23 爆燃『咚』+ 耳鸣、片尾最后一秒静音
都按脚本实现）：

  N01 黄金钩子 0–10 s   低沉大提琴单音渐强 + 海浪（远处船钟在 write_sfx）
  N02 启航    10–30 s   温暖弦乐（码头清晨的暖色和声）
  N03 发现    30–55 s   紧张低音弦乐持续铺底 + 风声
  N04 细节    55–90 s   诡异单音钢琴点缀 + 心跳般低频
  N05 猜想一   90–110 s  鼓点加快、铜管短促；『嘭』一声后静音约一秒
  N06 猜想二  110–135 s  宏大管弦、海怪低吼与雷雨；S21 起骤然安静
  N07 解释    135–164 s  悬疑钢琴固定音型、低频脉冲渐强；爆燃处『咚』+ 耳鸣后复起
  N08 结尾    164–177 s  大提琴单音收尾、海浪渐弱；最后一秒静音

所有内容都是低电平铺底：build_audio.build_soundtrack 会把 BGM 压在旁白下（ducking）
并统一到 -20 dBFS 左右，这里只管音乐性，不管响度。
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

RATE = 44100
WINDOWS = {  # 与 render.CHAPTER_WINDOWS 一致（改这里没用，以 render.py 为闸门）
    'N01': (0.0, 10.0), 'N02': (10.0, 30.0), 'N03': (30.0, 55.0), 'N04': (55.0, 90.0),
    'N05': (90.0, 110.0), 'N06': (110.0, 135.0), 'N07': (135.0, 164.0), 'N08': (164.0, 177.0),
}


def _t(a: float, b: float) -> np.ndarray:
    return np.arange(int(a * RATE), int(b * RATE)) / RATE


def _add(buf: np.ndarray, start: float, sig: np.ndarray, level: float = 1.0):
    i = int(start * RATE)
    if i < 0:
        sig = sig[-i:]
        i = 0
    n = min(len(sig), len(buf) - i)
    if n > 0:
        buf[i:i + n] += sig[:n] * level


def _env_adsr(n: int, attack: float, release: float, rate: int = RATE) -> np.ndarray:
    env = np.ones(n)
    a = min(n, int(attack * rate))
    r = min(n, int(release * rate))
    if a:
        env[:a] = np.linspace(0, 1, a) ** 1.5
    if r:
        env[-r:] *= np.linspace(1, 0, r) ** 1.3
    return env


def cello(t0: float, t1: float, freq: float, level: float = 1.0, vib: float = 4.6) -> np.ndarray:
    """大提琴质感长音：基波 + 低谐波 + 慢揉弦，软起音。"""
    t = _t(t0, t1) - t0
    n = len(t)
    if n == 0:
        return np.zeros(0)
    f = freq * (1 + 0.0035 * np.sin(2 * np.pi * vib * t))
    ph = 2 * np.pi * np.cumsum(f) / RATE
    sig = (np.sin(ph) + 0.55 * np.sin(2 * ph + 0.4) + 0.28 * np.sin(3 * ph + 1.1)
           + 0.12 * np.sin(4 * ph + 2.0))
    sig += 0.02 * np.random.default_rng(int(freq)).normal(0, 1, n)  # 弓弦噪声
    return sig * _env_adsr(n, 1.2, 1.4) * 0.32 * level


def strings_pad(t0: float, t1: float, freqs, level: float = 1.0, detune: float = 0.006) -> np.ndarray:
    """温暖弦乐组：失谐锯齿波叠加，慢起音。"""
    t = _t(t0, t1) - t0
    n = len(t)
    if n == 0:
        return np.zeros(0)
    sig = np.zeros(n)
    for k, f in enumerate(freqs):
        for d in (-detune, 0.0, detune):
            ff = f * (1 + d)
            ph = 2 * np.pi * ff * t + k * 0.7
            saw = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.18 * np.sin(3 * ph)
            sig += saw
    sig /= max(1, len(freqs) * 3)
    return sig * _env_adsr(n, 2.2, 2.0) * 0.30 * level


def piano(t0: float, freq: float, level: float = 1.0, decay: float = 2.6) -> np.ndarray:
    """单音钢琴：快起音 + 指数衰减 + 少量高频分音。"""
    t = _t(t0, t0 + decay + 0.2) - t0   # 包络按发声后经过的时间算
    n = len(t)
    if n == 0:
        return np.zeros(0)
    ph = 2 * np.pi * freq * t
    sig = (np.sin(ph) + 0.42 * np.sin(2.01 * ph) + 0.18 * np.sin(3.02 * ph)
           + 0.08 * np.sin(4.98 * ph))
    return sig * np.exp(-t * (3.4 / decay)) * 0.26 * level


def kick(t0: float, level: float = 1.0) -> np.ndarray:
    t = _t(t0, t0 + 0.55) - t0
    n = len(t)
    if n == 0:
        return np.zeros(0)
    f = 78 * np.exp(-t * 9) + 42
    ph = 2 * np.pi * np.cumsum(f) / RATE
    return np.sin(ph) * np.exp(-t * 7.5) * 0.55 * level


def brass_stab(t0: float, freq: float, dur: float = 0.55, level: float = 1.0) -> np.ndarray:
    t = _t(t0, t0 + dur) - t0
    n = len(t)
    if n == 0:
        return np.zeros(0)
    ph = 2 * np.pi * freq * t
    sig = np.sign(np.sin(ph)) * 0.35 + np.sin(ph) * 0.65 + 0.3 * np.sin(2 * ph)
    return sig * _env_adsr(n, 0.03, 0.22) * 0.16 * level


def growl(t0: float, t1: float, level: float = 1.0) -> np.ndarray:
    """海怪低吼：低频调频 + 噪声。"""
    t = _t(t0, t1) - t0
    n = len(t)
    if n == 0:
        return np.zeros(0)
    f = 55 + 16 * np.sin(2 * np.pi * 0.23 * t)
    ph = 2 * np.pi * np.cumsum(f) / RATE
    sig = np.sin(ph + 2.2 * np.sin(2 * np.pi * 0.9 * t))
    rng = np.random.default_rng(77)
    sig += 0.25 * np.convolve(rng.normal(0, 1, n), np.ones(24) / 24, 'same')
    return sig * _env_adsr(n, 0.8, 1.2) * 0.30 * level


def sub_pulse(t0: float, t1: float, hz: float, level0: float, level1: float) -> np.ndarray:
    """心跳般低频脉冲（用户 N04 / N07），力度从 level0 渐变到 level1。"""
    t = _t(t0, t1) - t0
    n = len(t)
    if n == 0:
        return np.zeros(0)
    beat = np.mod(t, 1.35)
    lvl = np.linspace(level0, level1, n)
    sig = np.sin(2 * np.pi * 47 * t) * np.exp(-beat * 6.5)
    sig += 0.55 * np.sin(2 * np.pi * 47 * (t - 0.16)) * np.exp(-np.mod(t - 0.16, 1.35) * 7.5)
    return sig * lvl * 0.5


def waves_bed(t0: float, t1: float, level: float = 1.0, seed: int = 3) -> np.ndarray:
    """海浪铺底：慢起伏的低通噪声。"""
    t = _t(t0, t1) - t0
    n = len(t)
    if n == 0:
        return np.zeros(0)
    rng = np.random.default_rng(seed)
    noise = np.convolve(rng.normal(0, 1, n), np.ones(96) / 96, 'same')
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * 0.09 * t + seed)
    return noise * swell * 0.34 * level


def tinnitus(t0: float, dur: float = 2.2, level: float = 1.0) -> np.ndarray:
    t = _t(t0, t0 + dur)
    n = len(t)
    if n == 0:
        return np.zeros(0)
    tt = t - t0
    return np.sin(2 * np.pi * 3800 * tt) * np.exp(-tt * 1.7) * 0.12 * level


def generate_maryceleste_score(output: Path, duration: float = 180.0, shot_times=None) -> None:
    shot_times = shot_times or {}
    n_total = int(math.ceil(duration * RATE))
    score = np.zeros(n_total, dtype=np.float64)

    # ---- N01 低沉大提琴单音渐强 + 海浪 ----
    _add(score, 0.4, cello(0.4, 11.0, 65.41, level=1.15))            # C2
    _add(score, 2.0, cello(2.0, 11.0, 98.00, level=0.55))            # G2 持续音
    _add(score, 0.0, waves_bed(0.0, 12.0, 0.85, seed=11))

    # ---- N02 温暖弦乐 ----
    _add(score, 10.0, strings_pad(10.0, 31.0, (130.81, 196.0, 246.94, 329.63), level=1.0))  # C 大调系
    _add(score, 10.0, strings_pad(18.0, 31.0, (164.81, 220.0), level=0.55))
    _add(score, 10.0, waves_bed(10.0, 31.0, 0.55, seed=22))

    # ---- N03 紧张低音弦乐 + 风 ----
    t = _t(30.0, 56.0) - 30.0
    trem = (1 - 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * 5.5 * t)))
    _add(score, 30.0, strings_pad(30.0, 56.0, (82.41, 123.47, 164.81), level=0.95) * trem)
    _add(score, 30.0, cello(30.0, 56.0, 82.41, level=0.7))
    wind = np.convolve(np.random.default_rng(33).normal(0, 1, len(t)), np.ones(40) / 40, 'same')
    _add(score, 30.0, wind * (0.4 + 0.3 * np.sin(2 * np.pi * 0.17 * t)) * 0.16)
    _add(score, 30.0, waves_bed(30.0, 56.0, 0.5, seed=44))

    # ---- N04 诡异单音钢琴 + 心跳低频 ----
    for k, (dt, f) in enumerate([(1.2, 659.26), (5.8, 493.88), (9.5, 739.99), (14.0, 523.25),
                                 (18.6, 587.33), (23.5, 440.0), (28.2, 698.46), (31.5, 523.25)]):
        _add(score, 55.0 + dt, piano(55.0 + dt, f, level=0.62 + 0.04 * (k % 3)))
    _add(score, 55.0, sub_pulse(55.0, 90.0, 47.0, 0.42, 0.62))
    _add(score, 55.0, waves_bed(55.0, 90.0, 0.28, seed=55))

    # ---- N05 鼓点加快 + 铜管短促；S17『嘭』后静音约一秒 ----
    s17 = shot_times.get('S17', 97.0)
    drum_t = 90.2
    step = 0.92
    while drum_t < s17 - 0.1:
        _add(score, drum_t, kick(drum_t, level=min(1.0, 0.5 + (drum_t - 90) * 0.045)))
        step = max(0.42, step * 0.90)
        drum_t += step
    for dt, f in [(1.0, 110.0), (4.4, 146.83), (7.0, 110.0), (9.6, 123.47)]:
        _add(score, 90.0 + dt, brass_stab(90.0 + dt, f))
    mute_a, mute_b = s17, s17 + 1.05           # 『嘭』一声后静音（嘭本身在 write_sfx）
    score[int(mute_a * RATE):int(mute_b * RATE)] *= 0.12
    _add(score, s17 + 1.05, strings_pad(s17 + 1.05, 110.0, (98.0, 130.81), level=0.55))

    # ---- N06 宏大管弦 + 海怪低吼 + 雷雨；S21 起骤然安静 ----
    s21 = shot_times.get('S21', 127.0)
    _add(score, 110.0, strings_pad(110.0, s21, (110.0, 146.83, 164.81, 220.0), level=1.15))
    _add(score, 110.0, strings_pad(113.0, s21, (82.41, 110.0), level=0.8))
    _add(score, 112.0, growl(112.0, min(s21, 112.0 + 9.0), level=1.0))
    _add(score, 118.4, growl(118.4, min(s21, 118.4 + 7.0), level=0.85))
    dr = 110.4
    while dr < s21 - 0.3:
        _add(score, dr, kick(dr, level=0.8))
        dr += 1.15
    _add(score, s21, waves_bed(s21, 136.0, 0.35, seed=66))   # 骤然安静：只剩海与一点冷色余音
    _add(score, s21, cello(s21, 136.0, 73.42, level=0.35))

    # ---- N07 悬疑钢琴固定音型 + 低频脉冲渐强；爆燃『咚』+ 耳鸣 ----
    s23 = shot_times.get('S23', 141.0)
    ost = [293.66, 311.13, 246.94]   # D4 / Eb4 / B3 —— 不安的三音型
    p = 135.0
    k = 0
    while p < s23 - 0.2:
        _add(score, p, piano(p, ost[k % 3], level=0.5, decay=1.7))
        p += 1.15
        k += 1
    _add(score, 135.0, sub_pulse(135.0, s23, 47.0, 0.35, 1.05))
    boom_a = s23
    score[int(boom_a * RATE):int((boom_a + 1.25) * RATE)] *= 0.06
    _add(score, boom_a + 1.25, tinnitus(boom_a + 1.25, 2.4, level=1.0))
    _add(score, boom_a + 1.3, strings_pad(boom_a + 1.3, 164.0, (116.54, 155.56, 174.61), level=0.62))
    p = boom_a + 2.2
    while p < 163.4:
        _add(score, p, piano(p, ost[k % 3] / 2, level=0.34, decay=2.0))
        p += 2.30
        k += 1
    _add(score, boom_a + 1.3, sub_pulse(boom_a + 1.3, 164.0, 47.0, 0.4, 0.18))

    # ---- N08 大提琴单音收尾 + 海浪渐弱；最后一秒静音 ----
    for t0, t1, f in [(164.0, 168.4, 110.0), (168.2, 172.4, 98.0), (172.2, 175.6, 87.31),
                      (175.4, 178.6, 82.41)]:
        _add(score, t0, cello(t0, t1, f, level=0.95))
    _add(score, 164.0, waves_bed(164.0, 178.6, 0.55, seed=77))
    tail = np.ones(n_total)
    tail[int(178.6 * RATE):] = np.linspace(1, 0, max(1, n_total - int(178.6 * RATE))) ** 2  # 最后一秒静音
    score *= tail

    peak = np.max(np.abs(score)) or 1.0
    score = score / peak * 0.62
    rng = np.random.default_rng(20261022)
    stereo = np.stack([score * 0.98, np.roll(score, 180) * 0.98], axis=1)
    stereo += rng.normal(0, 1e-5, stereo.shape)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(np.int16(np.clip(stereo, -1, 1) * 32767).tobytes())


if __name__ == '__main__':
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/tmp/score.wav')
    generate_maryceleste_score(out)
    print('score written:', out)
