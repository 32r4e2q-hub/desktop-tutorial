#!/usr/bin/env python3
"""音画同步闸门：拿成片、配音原轨和字幕时间轴互相对，不信任「我按计划排的」这件事。

为什么不能只看成片的音量包络：混音里配乐和音效是连续的，切点上还专门有音效重音，
「有没有人声」在成品混音里量不出来。所以这里用**配音原轨**（audio/N0x.mp3，SHA-256 有收据）
按 narration-timing.json 的 placement（章起点 + 全局 tempo）折算到成片时间轴，再逐条核：

1. **切点落在配音的停顿里** —— 每个镜头切点 ±60 ms 内，配音原轨必须是静音（< -45 dBFS）。
   切在字中间，人耳听到的是「话被剪断」，这是自动审计最容易漏的一类音画不同步。
2. **字幕跟着人声出现** —— 每条字幕的起点，要么正好落在人声中间（长句被切成两条字幕，
   属于继续显示），要么必须落在某个「静音→有声」的配音起点 ±0.30 s 内；
   不允许比声音早 0.45 s 以上（字幕抢跑）或晚 0.40 s 以上（字幕追不上）。
3. **成片里确实混进了这段配音** —— 配音有声处的成片电平，必须比配音停顿处的成片电平
   高出至少 2.5 dB（否则人声被音乐压掉、被静音或被换轨；混音里配乐是连续的，
   这个差值天然不会很大，它只是一道「配音还在」的兜底）。
4. **没有长时间无声** —— 成片混音连续 2.5 s 低于 -55 dBFS，说明混音掉了一段。

输出 ``delivery/av-sync-report.json``；有问题时退出码非 0。

    python3 production/zhoukehua2012/tools/check_av_sync.py --film 交付/xxx.mp4
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
ROOT = PROJ.parent.parent

RATE = 48000
HOP = 480                       # 10 ms
PAUSE_DB = -45.0                # 配音原轨里视为「停顿」的门限
CUT_TAIL = 0.15                 # 切点前 150 ms 必须已经静下来（否则上一句被剪断）
CUT_LEAD = 0.25                 # 切点后 250 ms 内必须起新的一句（否则切点悬在空气里）
CAPTION_EARLY = 0.45
CAPTION_LATE = 0.40
CAPTION_TOLERANCE = 0.30
MIN_CONTRAST_DB = 2.5
SILENT_GAP = 2.5
SILENT_DB = -55.0


def decode(path: Path) -> np.ndarray:
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
        check=True, capture_output=True).stdout
    return np.frombuffer(out, dtype="<i2").astype(np.float32) / 32768


def envelope(samples: np.ndarray) -> np.ndarray:
    n = len(samples) // HOP * HOP
    blocks = samples[:n].reshape(-1, HOP)
    return 20.0 * np.log10(np.sqrt((blocks ** 2).mean(axis=1)) + 1e-9)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def place_narration(timeline: list[dict]) -> tuple[np.ndarray, float]:
    """把六段配音按 placement 铺到成片时间轴上，返回 10 ms 一格的配音包络。"""
    tempo = float(timeline[0]["tempo"])
    duration = max(float(row["end"]) for row in timeline) + 1.0
    grid = np.full(int(duration / (HOP / RATE)) + 2, -120.0, dtype=np.float32)
    for row in timeline:
        clip = PROJ / "audio" / (row["id"] + ".mp3")
        level = envelope(decode(clip))
        # 原轨第 i 格（10 ms）落在成片的 start + i*0.01/tempo 秒
        for i, value in enumerate(level):
            t = float(row["start"]) + i * (HOP / RATE) / tempo
            index = int(round(t / (HOP / RATE)))
            if 0 <= index < len(grid):
                grid[index] = max(grid[index], value)
    return grid, tempo


def onsets(level: np.ndarray) -> np.ndarray:
    smooth = np.convolve(level, np.ones(3) / 3, mode="same")
    voiced = smooth > PAUSE_DB
    return np.array([(i - 1) * HOP / RATE for i in range(1, len(voiced)) if voiced[i] and not voiced[i - 1]])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--film", default=str(ROOT / "交付" / "周克华案_逃亡八年，最后四天_三分钟_带声音.mp4"))
    parser.add_argument("--delivery", default=str(PROJ / "delivery"))
    parser.add_argument("--out", default=str(PROJ / "delivery" / "av-sync-report.json"))
    args = parser.parse_args()

    film = Path(args.film)
    delivery = Path(args.delivery)
    edl = load_json(delivery / "edit-decision-list.json")
    cues = load_json(delivery / "caption-timing.json")
    timeline = load_json(delivery / "narration-timing.json")

    narration, tempo = place_narration(timeline)
    mix = envelope(decode(film))

    narration_end = max(float(row["end"]) for row in timeline)
    cuts = sorted({row["start_frame"] / 30.0 for row in edl} - {0.0})
    cut_rows, cut_problems = [], []
    for cut in cuts:
        if cut >= narration_end:      # 片尾卡之后没有解说，切点本来就该落在空白上
            continue
        i = min(int(round(cut / (HOP / RATE))), len(narration) - 1)
        lo = max(0, i - int(CUT_TAIL * RATE / HOP))
        hi = min(len(narration) - 1, max(lo, i - 2))
        segment = narration[lo:hi + 1]
        tail = float(segment.max()) if segment.size else -120.0
        j = min(len(narration) - 1, i + int(CUT_LEAD * RATE / HOP))
        segment = narration[i:j + 1]
        lead = float(segment.max()) if segment.size else -120.0
        cut_rows.append({"seconds": round(cut, 3), "narration_tail_db": round(tail, 1),
                         "narration_after_cut_db": round(lead, 1),
                         "in_pause": bool(tail < PAUSE_DB),
                         "new_sentence_starts": bool(lead >= PAUSE_DB)})
        if tail >= PAUSE_DB:
            cut_problems.append(f"{cut:.2f}s 切点前 {CUT_TAIL:.2f}s 还有配音（{tail:.1f} dBFS），上一句会被剪断")
        if lead < PAUSE_DB:
            cut_problems.append(f"{cut:.2f}s 切点后 0.25s 没有新句子（{lead:.1f} dBFS），镜头切在空白上")

    voice_onsets = onsets(narration)
    cue_rows, cue_problems = [], []
    for cue in cues:
        start = float(cue["start"])
        at = int(round(start / (HOP / RATE)))
        voiced_now = float(narration[max(0, at - 1):at + 2].max()) >= PAUSE_DB
        nearest = float(voice_onsets[np.argmin(np.abs(voice_onsets - start))]) if len(voice_onsets) else None
        delta = None if nearest is None else round(start - nearest, 3)
        cue_rows.append({"text": cue["text"], "start": round(start, 3),
                         "continues_previous_clause": bool(voiced_now),
                         "nearest_voice_onset": None if nearest is None else round(nearest, 3),
                         "delta_seconds": delta})
        if voiced_now:
            continue
        if delta is None:
            cue_problems.append(f"「{cue['text']}」找不到对应的配音起点")
        elif delta > CAPTION_LATE:
            cue_problems.append(f"「{cue['text']}」字幕比人声晚 {delta:.2f}s")
        elif delta < -CAPTION_EARLY:
            cue_problems.append(f"「{cue['text']}」字幕比人声早 {-delta:.2f}s")
        elif abs(delta) > CAPTION_TOLERANCE:
            cue_problems.append(f"「{cue['text']}」字幕与配音偏差 {delta:+.2f}s（上限 ±{CAPTION_TOLERANCE}s）")

    length = min(len(narration), len(mix))
    a, b = narration[:length], mix[:length]
    voiced = a >= PAUSE_DB - 10
    quiet = a <= PAUSE_DB - 20
    contrast = (float(b[voiced].mean() - b[quiet].mean())
                if voiced.any() and quiet.any() else 0.0)
    if contrast < MIN_CONTRAST_DB:
        cue_problems.append(f"成片里人声不突出：有声段只比停顿段高 {contrast:.1f} dB（要求 {MIN_CONTRAST_DB}）")

    silent_runs, start = [], None
    for i, value in enumerate(mix):
        if value < SILENT_DB and start is None:
            start = i
        if value >= SILENT_DB and start is not None:
            silent_runs.append((start * HOP / RATE, i * HOP / RATE))
            start = None
    if start is not None:
        silent_runs.append((start * HOP / RATE, len(mix) * HOP / RATE))
    silent_problems = [f"{s:.1f}–{e:.1f}s 连续 {e - s:.1f}s 无声" for s, e in silent_runs if e - s >= SILENT_GAP]

    deltas = [abs(row["delta_seconds"]) for row in cue_rows if row["delta_seconds"] is not None]
    report = {
        "film": str(film),
        "tempo": round(tempo, 4),
        "cuts_checked": len(cut_rows),
        "cuts_in_pause": sum(1 for row in cut_rows if row["in_pause"]),
        "caption_cues_checked": len(cue_rows),
        "caption_delta_median_seconds": round(float(np.median(deltas)), 3) if deltas else None,
        "caption_delta_p95_seconds": round(float(np.percentile(deltas, 95)), 3) if deltas else None,
        "caption_delta_max_seconds": round(max(deltas), 3) if deltas else None,
        "voice_over_pause_contrast_db": round(contrast, 2),
        "silent_runs": [{"start": round(s, 2), "end": round(e, 2)} for s, e in silent_runs],
        "cuts": cut_rows,
        "captions": cue_rows,
        "problems": cut_problems + cue_problems + silent_problems,
        "status": "PASS" if not (cut_problems + cue_problems + silent_problems) else "FAIL",
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"切点 {len(cut_rows)} 个（落在配音停顿 {report['cuts_in_pause']} 个）· "
          f"字幕 {len(cue_rows)} 条（中位 {report['caption_delta_median_seconds']}s / "
          f"P95 {report['caption_delta_p95_seconds']}s / 最大 {report['caption_delta_max_seconds']}s）· "
          f"人声比停顿段高 {contrast:.1f} dB · tempo {tempo:.4f}")
    for problem in report["problems"][:20]:
        print("  ! " + problem)
    print("音画同步闸门：" + ("PASS" if report["status"] == "PASS" else f"FAIL（{len(report['problems'])} 处）"))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
