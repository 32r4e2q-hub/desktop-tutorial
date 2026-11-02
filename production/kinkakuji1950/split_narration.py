#!/usr/bin/env python3
"""把 10 条配音母带切成 30 条「一镜一句」的旁白，并输出逐镜试装表。

Arena 的语音工具每次只说一段话；本片 30 个镜头、10 条母带（每条 3 句）。
本脚本按「句末停顿」把母带切成 3 段：先算能量包络与静音区间，再按每句字数算出
理论边界，在 ±0.9 秒内挑最长的静音作为切点；切点离理论边界太远时退回理论边界，
并在报告里标注 ``forced``，方便人工复核。

用法::

    python3 production/kinkakuji1950/split_narration.py            # 切分并写报告
    python3 production/kinkakuji1950/split_narration.py --report   # 只看表
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / "audio" / "raw"
OUT = HERE / "audio"
RATE = 48_000
GROUPS = [("G01", ["S01", "S02", "S03"]), ("G02", ["S04", "S05", "S06"]),
          ("G03", ["S07", "S08", "S09"]), ("G04", ["S10", "S11", "S12"]),
          ("G05", ["S13", "S14", "S15"]), ("G06", ["S16", "S17", "S18"]),
          ("G07", ["S19", "S20", "S21"]), ("G08", ["S22", "S23", "S24"]),
          ("G09", ["S25", "S26", "S27"]), ("G10", ["S28", "S29", "S30"])]


def visible(text: str) -> int:
    return max(1, sum(1 for ch in text if ch.isalnum() or "\u3400" <= ch <= "\u9fff"))


def decode(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as reader:
        rate = reader.getframerate()
        data = np.frombuffer(reader.readframes(reader.getnframes()), dtype="<i2")
    if rate != RATE:
        raise RuntimeError(f"{path}: expected {RATE} Hz")
    return data.astype(np.float32) / 32768.0


def to_wav(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source),
        "-ar", str(RATE), "-ac", "1", "-c:a", "pcm_s16le", str(target),
    ], check=True)


def energy(samples: np.ndarray, hop: int = RATE // 100) -> np.ndarray:
    count = max(1, len(samples) // hop)
    blocks = samples[:count * hop].reshape(count, hop)
    return np.sqrt(np.mean(np.square(blocks.astype(np.float64)), axis=1))


def speech_window(samples: np.ndarray) -> tuple[int, int]:
    levels = energy(samples)
    threshold = max(0.0004, float(levels.max()) * 0.02)
    active = np.flatnonzero(levels > threshold)
    hop = RATE // 100
    return int(active[0]) * hop, min(len(samples), (int(active[-1]) + 1) * hop)


def silences(samples: np.ndarray, floor: float) -> list[tuple[int, int]]:
    """静音区间（按样本），以 10ms 帧判定的低能量连续段。"""
    levels = energy(samples)
    hop = RATE // 100
    quiet = levels < floor
    gaps, start = [], None
    for index, value in enumerate(quiet):
        if value and start is None:
            start = index
        elif not value and start is not None:
            gaps.append((start * hop, index * hop))
            start = None
    if start is not None:
        gaps.append((start * hop, len(quiet) * hop))
    return gaps


def choose_cuts(samples: np.ndarray, texts: list[str], window: tuple[int, int]) -> tuple[list[int], list[str]]:
    start, end = window
    span = end - start
    weights = [visible(text) for text in texts]
    total = sum(weights)
    expected = [start + span * sum(weights[:i + 1]) / total for i in range(len(texts) - 1)]
    floor = max(0.0015, float(np.abs(samples).max()) * 0.012)
    gaps = [gap for gap in silences(samples, floor) if gap[1] - gap[0] >= int(0.10 * RATE)]
    cuts, notes = [], []
    for target in expected:
        best, best_score = None, None
        for gap in gaps:
            centre = (gap[0] + gap[1]) / 2
            distance = abs(centre - target)
            if distance > 0.9 * RATE:
                continue
            length = (gap[1] - gap[0]) / RATE
            score = distance / RATE - 0.45 * length  # 越近越好，越长越好
            if best_score is None or score < best_score:
                best, best_score = int(centre), score
        if best is None:
            cuts.append(int(target))
            notes.append("forced")
        else:
            cuts.append(best)
            notes.append("silence")
    return cuts, notes


def write_mp3(samples: np.ndarray, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    pcm = np.int16(np.round(clipped * 32767.0)).astype("<i2")
    with wave.open(str(target.with_suffix(".wav")), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(RATE)
        writer.writeframes(pcm.tobytes())
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(target.with_suffix(".wav")),
        "-c:a", "libmp3lame", "-b:a", "192k", "-ar", str(RATE), str(target),
    ], check=True)
    target.with_suffix(".wav").unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="只打印现有切分报告")
    args = parser.parse_args()

    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    narration = {shot["id"]: shot["narration"] for shot in story["shots"]}
    planned = {shot["id"]: shot["duration"] for shot in story["shots"]}
    report_path = HERE / "qa" / "narration-split.json"
    if args.report:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        rows = []
        for group, ids in GROUPS:
            wav = RAW / f"{group}.wav"
            to_wav(RAW / f"{group}.mp3", wav)
            samples = decode(wav)
            window = speech_window(samples)
            cuts, notes = choose_cuts(samples, [narration[sid] for sid in ids], window)
            bounds = [window[0], *cuts, window[1]]
            # 单条母带内保留句首句尾各 30ms / 120ms 的自然气口，条与条之间做 12ms 淡入淡出。
            pad_head, pad_tail = int(0.03 * RATE), int(0.14 * RATE)
            for index, sid in enumerate(ids):
                head = max(0, bounds[index] - pad_head)
                tail = min(len(samples), bounds[index + 1] + pad_tail)
                clip = samples[head:tail].copy()
                fade = int(0.012 * RATE)
                if len(clip) > 2 * fade:
                    clip[:fade] *= np.linspace(0.0, 1.0, fade)
                    clip[-fade:] *= np.linspace(1.0, 0.0, fade)
                write_mp3(clip, OUT / f"{sid}.mp3")
                duration = len(clip) / RATE
                rows.append({
                    "id": sid,
                    "group": group,
                    "cut": notes[index] if index < len(notes) else "tail",
                    "audio_seconds": round(duration, 3),
                    "planned_seconds": planned[sid],
                    "speech_seconds": round((bounds[index + 1] - bounds[index]) / RATE, 3),
                    "chars": visible(narration[sid]),
                    "chars_per_second": round(visible(narration[sid]) /
                                              ((bounds[index + 1] - bounds[index]) / RATE), 2),
                    "text": narration[sid],
                })
            wav.unlink(missing_ok=True)
        report = {"rate": RATE, "groups": len(GROUPS), "clips": rows,
                  "total_speech_seconds": round(sum(r["speech_seconds"] for r in rows), 2)}
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")

    print(f"{'id':4} {'cut':8} {'audio':>6} {'plan':>5} {'c/s':>5}  text")
    for row in report["clips"]:
        flag = "  <-- 挤" if row["audio_seconds"] > row["planned_seconds"] else ""
        print(f"{row['id']:4} {row['cut']:8} {row['audio_seconds']:6.2f} "
              f"{row['planned_seconds']:5} {row['chars_per_second']:5.2f}  {row['text']}{flag}")
    print(f"total speech {report['total_speech_seconds']:.2f}s "
          f"across {len(report['clips'])} lines")


if __name__ == "__main__":
    main()
