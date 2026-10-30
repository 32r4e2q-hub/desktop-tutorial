#!/usr/bin/env python3
"""解说词与片段等长：量一遍每个镜头里旁白到底占了多少秒。

本片的核心做法是**镜头时长跟着旁白走**，不是先定镜头再把旁白硬塞进去：
先录一镜一句的旁白，量出每句的"自然语音时长"，再把它落到 Agnes 2.5 Flash 允许的
4–9 秒档位上（`build_story.py` 的 `SHOT_ROWS`），最后 `build_audio.py` 只在必要时
做 ≤1.55× 的轻微加速（只快不慢，禁止慢放填时长）。

这个脚本给出每个镜头的实测占比如下，用来在 `--validate` 之前先看一遍：

    占比 = 自然语音秒数 / 该镜可用窗口秒数
    可用窗口 = min(镜头末尾 − 0.08 s, 179.0 s) − 镜头起点

判定：
  * `fit`      0.85–1.00 —— 理想：旁白几乎铺满镜头，不需要加速
  * `ok`       0.70–0.85 —— 可接受：留白用于呼吸和画面交代
  * `short`    < 0.70     —— 旁白偏短：要么把这一镜的秒数改小，要么把这句话写足
  * `needs-speedup`  > 1.00 但 ≤ 上限 —— 需要轻微加速才能装进这一镜
  * `over`     > 1.00 且超出上限 —— 失败：必须改句子或改镜头时长，别硬加速

用法：
    python3 production/setagaya2000/narration_fit.py            # 表格
    python3 production/setagaya2000/narration_fit.py --json     # 机器可读
    python3 production/setagaya2000/narration_fit.py --strict   # short/over 也算失败

需要 `ffmpeg` / `ffprobe` 在 PATH 上（没有系统 ffprobe 时用同目录的 `ffprobe_shim.py`）。
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FIT_LOW = 0.85
OK_LOW = 0.70
TAIL_GUARD = 0.08      # 语音必须在切点前收住
FINAL_GUARD = 1.0      # 最后 1 秒留静音给片尾卡


def classify(ratio: float, speedup_needed: float, max_speedup: float) -> str:
    """把"占比 / 需要多少加速"翻译成判定，纯函数，方便离线单测。"""
    if speedup_needed > max_speedup + 1e-6:
        return "over"
    if ratio > 1.0:
        return "needs-speedup"
    if ratio >= FIT_LOW:
        return "fit"
    if ratio >= OK_LOW:
        return "ok"
    return "short"


def measure(audio_dir: Path, scratch: Path) -> dict:
    """镜头 → 自然语音秒数（与 build_audio 完全同一套裁剪口径）。

    build_audio 依赖 numpy，只在真正量音频时才导入，这样 `classify()` 可以离线单测。
    """
    import build_audio as ba  # noqa: PLC0415  只复用它的解码/静音裁剪/语速上限，保证口径一致

    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    manifest = json.loads((audio_dir / "manifest.json").read_text(encoding="utf-8"))
    records = {row["id"]: row for row in manifest["clips"]}
    max_speedup = float(story.get("narration_spec", {}).get("max_speedup_factor", 1.55))
    rows = []
    for shot in story["shots"]:
        sid = shot["id"]
        record = records.get(sid)
        if record is None:
            raise SystemExit(f"缺少旁白清单条目：{sid}")
        source = audio_dir / record["file"]
        if not source.is_file():
            raise SystemExit(f"缺少旁白文件：{source}")
        samples = ba.decode_mp3(source, scratch / f"{sid}.wav", 1.0)
        trimmed, onset, offset = ba.trim_voice_edges(samples)
        natural = len(trimmed) / ba.RATE
        speech = offset - onset

        start = float(shot["start"])
        duration = float(shot["duration"])
        window_end = min(start + duration - TAIL_GUARD, float(story["target_duration"]) - FINAL_GUARD)
        available = window_end - start
        ratio = speech / available if available > 0 else 0.0
        needed = max(1.0, natural / available) if available > 0 else float("inf")

        verdict = classify(ratio, needed, max_speedup)

        rows.append({
            "id": sid,
            "start": start,
            "duration": duration,
            "available_seconds": round(available, 3),
            "natural_speech_seconds": round(speech, 3),
            "natural_clip_seconds": round(natural, 3),
            "fill_ratio": round(ratio, 3),
            "speedup_needed": round(needed, 3),
            "characters": ba.visible_weight(shot["narration"]),
            "chars_per_second": round(ba.visible_weight(shot["narration"]) / duration, 3),
            "verdict": verdict,
            "text": shot["narration"],
        })
    return {
        "voice": manifest.get("voice"),
        "max_speedup_factor": max_speedup,
        "thresholds": {"fit_low": FIT_LOW, "ok_low": OK_LOW},
        "shots": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, default=HERE / "audio")
    parser.add_argument("--json", action="store_true", help="输出 JSON 而不是表格")
    parser.add_argument("--strict", action="store_true", help="short / needs-speedup 也算失败")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as scratch:
        report = measure(args.audio, Path(scratch))

    rows = report["shots"]
    failures = [row for row in rows if row["verdict"] == "over"]
    if args.strict:
        failures += [row for row in rows if row["verdict"] in ("short", "needs-speedup")]

    if args.json:
        print(json.dumps({**report, "failures": [row["id"] for row in failures]},
                         ensure_ascii=False, indent=2))
    else:
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        print("| 镜头 | 时长 | 自然语音 | 占比 | 需要加速 | 字数 | 字/秒 | 判定 |")
        print("|---|---|---|---|---|---|---|---|")
        for row in rows:
            print(f"| {row['id']} | {row['duration']:g}s | {row['natural_speech_seconds']:.2f}s | "
                  f"{row['fill_ratio']:.0%} | {row['speedup_needed']:.2f}× | {row['characters']} | "
                  f"{row['chars_per_second']:.2f} | {row['verdict']} |")
        print()
        print("判定分布：" + " · ".join(f"{key} {value}" for key, value in sorted(counts.items())))
        if failures:
            print("不合格：" + ", ".join(row["id"] for row in failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
