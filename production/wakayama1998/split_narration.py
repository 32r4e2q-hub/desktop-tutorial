#!/usr/bin/env python3
"""把分段录制的旁白切成「一镜一句」的 Sxx.mp3（离线工具，只在准备素材时跑）。

Arena TTS 一次只会给出整段音频；本片为了 29 个镜头共用 10 段录音（每段 2–5 句），
这里在**句子之间**的静音处切开，再逐镜落到 audio/Sxx.mp3，交给 build_story.py 记 SHA-256。

切分不是按固定间隔硬切：先找所有 ≥90ms 的静音段作为候选切点，再用动态规划挑出
「每段时长 / 该句字数」最接近全片平均语速的那一组切点。切完会把逐镜实测时长报出来，
超过镜头窗口的会点名，方便回头单独重录那一句。

    python3 production/wakayama1998/split_narration.py
    python3 production/wakayama1998/split_narration.py --check   # 只测量，不写文件
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
RAW = AUDIO / "raw"
RATE = 48_000
HOP = RATE // 100  # 10 ms

# 录音分段：每段 2–5 句，句序与 story.json 的镜头顺序一致。
SEGMENTS = {
    "C01": ["S01", "S02", "S03"],
    "C02": ["S04", "S05"],
    "C03": ["S06", "S07"],
    "C04": ["S08", "S09"],
    "C05": ["S10", "S11", "S12"],
    "C06": ["S13", "S14", "S15"],
    "C07": ["S16", "S17", "S18"],
    "C08": ["S19", "S20", "S21"],
    "C09": ["S22", "S23", "S24"],
    "C10": ["S25", "S26", "S27", "S28", "S29"],
}


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover - runner 上有系统 ffmpeg
        return "ffmpeg"


def decode(path: Path) -> np.ndarray:
    raw = subprocess.check_output([ffmpeg(), "-v", "error", "-i", str(path),
                                   "-f", "s16le", "-acodec", "pcm_s16le",
                                   "-ar", str(RATE), "-ac", "1", "-"])
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def frames_db(samples: np.ndarray) -> np.ndarray:
    count = len(samples) // HOP
    blocks = samples[:count * HOP].reshape(count, HOP)
    rms = np.sqrt(np.mean(blocks.astype(np.float64) ** 2, axis=1))
    return 20.0 * np.log10(np.maximum(rms, 1e-9))


def silence_candidates(samples: np.ndarray, min_gap: float = 0.09) -> tuple[list[float], np.ndarray]:
    db = frames_db(samples)
    peak = float(np.max(db))
    threshold = max(-52.0, peak - 36.0)
    silent = db < threshold
    runs, start = [], None
    for index, flag in enumerate(silent):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(silent)))
    min_frames = int(round(min_gap * 100))
    points = [(a + b) / 2.0 * HOP / RATE for a, b in runs if b - a >= min_frames]
    # 片头/片尾不算切点。
    duration = len(samples) / RATE
    points = [p for p in points if 0.25 < p < duration - 0.25]
    return points, db


def visible(text: str) -> int:
    return max(1, sum(1 for ch in text if ch.isalnum() or "\u3400" <= ch <= "\u9fff"))


def choose_cuts(duration: float, weights: list[float], candidates: list[float]) -> list[float]:
    """Pick len(weights)-1 cut points so each slice's share of time matches its share of characters."""
    k = len(weights) - 1
    if k == 0:
        return []
    if len(candidates) < k:
        raise RuntimeError(f"only {len(candidates)} silence gaps for {k} cuts")
    total = sum(weights)
    cumulative = np.cumsum(weights)[:-1] / total * duration
    points = np.array(candidates, dtype=np.float64)
    inf = float("inf")
    # cost[j, i]: 前 j+1 个切点里最后一个落在候选 i 上的最小代价
    cost = np.full((k, len(points)), inf)
    back = np.full((k, len(points)), -1, dtype=int)
    cost[0] = np.abs(points - cumulative[0]) * 4.0
    for j in range(1, k):
        for i in range(len(points)):
            best, arg = inf, -1
            for p in range(i):
                if cost[j - 1, p] == inf:
                    continue
                value = cost[j - 1, p] + abs(points[i] - cumulative[j]) * 4.0
                if value < best:
                    best, arg = value, p
            cost[j, i], back[j, i] = best, arg
    last = int(np.argmin(cost[k - 1]))
    cuts = [last]
    for j in range(k - 1, 0, -1):
        cuts.append(int(back[j, cuts[-1]]))
    cuts = sorted(cuts)
    return [float(points[i]) for i in cuts]


def trim_slice(samples: np.ndarray, start: float, end: float) -> np.ndarray:
    a, b = int(start * RATE), int(end * RATE)
    piece = samples[a:b]
    db = frames_db(piece)
    threshold = max(-52.0, float(np.max(db)) - 40.0)
    voiced = np.where(db > threshold)[0]
    if not len(voiced):
        return piece
    head = max(0, voiced[0] * HOP - int(0.05 * RATE))
    tail = min(len(piece), (voiced[-1] + 1) * HOP + int(0.10 * RATE))
    return piece[head:tail]


def write_mp3(samples: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1.0, 1.0)
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1",
                    "-i", "-", "-c:a", "libmp3lame", "-b:a", "160k", str(path)],
                   input=(pcm * 32767).astype("<i2").tobytes(), check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    shots = {shot["id"]: shot for shot in story["shots"]}
    problems = []
    total_speech = 0.0
    for name, ids in SEGMENTS.items():
        source = RAW / f"{name}.mp3"
        if not source.is_file():
            problems.append(f"{name}: missing recording")
            continue
        samples = decode(source)
        duration = len(samples) / RATE
        weights = [visible(shots[sid]["narration"]) for sid in ids]
        expected_cuts = choose_cuts(duration, weights, silence_candidates(samples)[0])
        edges = [0.0] + expected_cuts + [duration]
        print(f"{name}: {duration:5.2f}s -> " + " / ".join(
            f"{sid} {edges[i+1]-edges[i]:4.2f}s" for i, sid in enumerate(ids)))
        for i, sid in enumerate(ids):
            piece = trim_slice(samples, edges[i], edges[i + 1])
            spoken = len(piece) / RATE
            total_speech += spoken
            window = shots[sid]["duration"] - 0.08
            speed = spoken / window
            flag = ""
            if speed > 1.55:
                flag = "  <-- OVER (>1.55x)"
                problems.append(f"{sid}: needs {speed:.2f}x")
            elif speed > 1.02:
                flag = f"  (speedup {speed:.2f}x)"
            print(f"    {sid} d={shots[sid]['duration']}s spoken={spoken:5.2f}s "
                  f"ratio={spoken/window:4.2f}{flag}")
            if not args.check:
                write_mp3(piece, AUDIO / f"{sid}.mp3")
    print(f"\nTOTAL speech {total_speech:.2f}s over 180s ({total_speech/180:.1%} fill)")
    if problems:
        print("\nPROBLEMS:")
        for item in problems:
            print("  -", item)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
