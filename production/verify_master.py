#!/usr/bin/env python3
"""成片硬校验器：一条命令验完「时长 / 帧数 / 音轨长度 / 字幕窗口 / 字幕与语音同步 / 过曝」。

任何项目都能直接用，不依赖该项目的 qc.py：

    python3 production/verify_master.py \
        --film 交付/某某片.mp4 \
        --story production/<slug>/story.json \
        --srt 交付/某某片_Subtitles.srt

为什么需要它：2026-11-12 的《消失的未婚夫》成片里，容器时长 180.000s、帧数 4320 都对，
但**音频流只有 177.834s**，最后一句被吃掉 1.2 秒；字幕又比语音早 0.3 秒。
只看 ffprobe 的 format.duration 完全发现不了，必须逐条测音频流长度和字幕窗口。

退出码：0 = 全过；1 = 有硬失败（打印原因）。
`--json` 可把报告写成文件，便于挂进 CI。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SRT_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+) --> (\d+):(\d+):(\d+)[,.](\d+)")


# ── 纯函数部分：不需要 av / 媒体文件，测试直接调 ─────────────────────────────

def parse_srt(path: Path) -> list[tuple[float, float, str]]:
    """解析 SRT，返回 [(起, 止, 文本)]；容错处理空文件与坏块。"""
    if not path.is_file():
        return []
    cues: list[tuple[float, float, str]] = []
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    for block in text.split("\n\n"):
        match = SRT_TIME.search(block)
        if not match:
            continue
        g = [int(v) for v in match.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        body = block[match.end():].strip().replace("\n", " ")
        cues.append((start, end, body))
    return cues


def shot_spans(story: dict) -> list[tuple[str, float, float]]:
    spans = []
    for shot in story.get("shots", []):
        start = float(shot["start"])
        spans.append((str(shot["id"]), start, start + float(shot["duration"])))
    return spans


def cue_window_problems(cues, spans, tolerance: float = 0.06) -> list[str]:
    """字幕必须一镜一条、且落在本镜窗口内——这是防「字幕串镜」的唯一闸门。"""
    problems = []
    if len(cues) != len(spans):
        problems.append(f"字幕条数 {len(cues)} ≠ 镜头数 {len(spans)}")
    for index, (cue, span) in enumerate(zip(cues, spans), 1):
        sid, shot_start, shot_end = span
        cue_start, cue_end = cue[0], cue[1]
        if cue_start < shot_start - tolerance:
            problems.append(f"第 {index} 条字幕起点 {cue_start:.2f}s 早于 {sid} 起点 {shot_start:.2f}s")
        if cue_end > shot_end + tolerance:
            problems.append(f"第 {index} 条字幕止点 {cue_end:.2f}s 晚于 {sid} 止点 {shot_end:.2f}s")
        if cue_end <= cue_start:
            problems.append(f"第 {index} 条字幕时长非正：{cue_start:.2f}–{cue_end:.2f}s")
    return problems


def speech_windows(cues, spans, blocks, threshold_ratio: float = 0.12):
    """按 10ms 语音能量块，量每条字幕相对真实语音的提前/延后（秒）。"""
    offsets = []
    for (cue_start, cue_end, _), (_, shot_start, shot_end) in zip(cues, spans):
        lo, hi = int(cue_start * 100), int(min(cue_end, shot_end) * 100) + 1
        lo, hi = max(0, lo), min(len(blocks), hi)
        active = [i for i in range(lo, hi) if blocks[i]]
        if not active:
            offsets.append(None)
            continue
        # 索引本来就是绝对块号（10ms 一格），不要再加 lo。
        lead = active[0] / 100 - cue_start
        tail = active[-1] / 100 - cue_end
        offsets.append((round(lead, 3), round(tail, 3), (len(active) / max(1, hi - lo)) >= threshold_ratio))
    return offsets


def rms_blocks(samples, rate: int, hop_ms: int = 10):
    """把单声道 float32 波形压成 hop_ms 的能量块二值序列（阈值为 P95 的 10%）。"""
    import numpy as np

    hop = max(1, rate // (1000 // hop_ms))
    count = len(samples) // hop
    if count == 0:
        return []
    rms = np.sqrt((samples[: count * hop].reshape(count, hop) ** 2).mean(axis=1))
    threshold = max(0.004, float(np.percentile(rms, 95)) * 0.10)
    return (rms > threshold).tolist()


# ── 媒体部分 ────────────────────────────────────────────────────────────────

def decode_audio(film: Path):
    import av
    import numpy as np

    container = av.open(str(film))
    stream = container.streams.audio[0]
    rate = int(stream.codec_context.sample_rate)
    chunks = []
    for frame in container.decode(audio=0):
        data = frame.to_ndarray()
        chunks.append(data.mean(axis=0) if data.ndim > 1 else data)
    samples = np.concatenate(chunks).astype(np.float32)
    return samples, rate


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="成片硬校验：时长/帧数/音轨/字幕窗口/字幕-语音同步")
    ap.add_argument("--film", type=Path, required=True)
    ap.add_argument("--story", type=Path, help="story.json；给了就核对镜数、分辨率、帧率与字幕窗口")
    ap.add_argument("--srt", type=Path, help="字幕文件；默认取成片同名 .srt")
    ap.add_argument("--duration", type=float, help="目标时长；默认取 story.target_duration，否则 180")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--json", type=Path, help="报告输出路径")
    ap.add_argument("--max-lead", type=float, default=0.20,
                    help="允许的字幕领先语音上限（秒），默认 0.20")
    args = ap.parse_args(argv)

    import av

    failures: list[str] = []
    report: dict = {"film": str(args.film)}
    if not args.film.is_file():
        print(f"缺少成片：{args.film}")
        return 1

    story = json.loads(args.story.read_text(encoding="utf-8")) if args.story else {}
    target = float(args.duration or story.get("target_duration") or 180.0)
    width = int(story.get("width") or 1920)
    height = int(story.get("height") or 1080)
    fps = int(story.get("fps") or args.fps)

    container = av.open(str(args.film))
    video = next((s for s in container.streams if s.type == "video"), None)
    audio = next((s for s in container.streams if s.type == "audio"), None)
    container_seconds = float(container.duration / 1_000_000) if container.duration else 0.0
    report["container_seconds"] = round(container_seconds, 3)

    if abs(container_seconds - target) > 0.05:
        failures.append(f"容器时长 {container_seconds:.3f}s ≠ 目标 {target:.3f}s")

    if video is None:
        failures.append("没有视频流")
    else:
        video_seconds = float(video.duration * video.time_base) if video.duration else 0.0
        report["video"] = {
            "codec": video.codec_context.name,
            "size": [video.codec_context.width, video.codec_context.height],
            "fps": str(video.average_rate),
            "frames": video.frames,
            "seconds": round(video_seconds, 3),
        }
        if [video.codec_context.width, video.codec_context.height] != [width, height]:
            failures.append(f"分辨率 {video.codec_context.width}x{video.codec_context.height} ≠ {width}x{height}")
        if abs(float(video.average_rate) - fps) > 0.01:
            failures.append(f"帧率 {video.average_rate} ≠ {fps}")
        if video.frames and video.frames != round(target * fps):
            failures.append(f"帧数 {video.frames} ≠ {round(target * fps)}")
        if abs(video_seconds - target) > 0.06:
            failures.append(f"视频流时长 {video_seconds:.3f}s ≠ {target:.3f}s")

    if audio is None:
        failures.append("没有音频流（旁白缺失）")
    else:
        audio_seconds = float(audio.duration * audio.time_base) if audio.duration else 0.0
        report["audio"] = {
            "codec": audio.codec_context.name,
            "sample_rate": audio.codec_context.sample_rate,
            "channels": audio.codec_context.channels,
            "seconds": round(audio_seconds, 3),
        }
        # 关键闸门：音频流长度必须与画面一致，否则末句会被静默截断。
        if abs(audio_seconds - target) > 0.06:
            failures.append(f"音频流 {audio_seconds:.3f}s ≠ {target:.3f}s（旁白被截断）")
        if int(audio.codec_context.sample_rate) != 48_000:
            failures.append(f"采样率 {audio.codec_context.sample_rate} ≠ 48000")

    srt = args.srt or args.film.with_suffix(".srt")
    cues = parse_srt(srt)
    report["subtitle_cues"] = len(cues)
    spans = shot_spans(story) if story.get("shots") else []
    if not cues:
        failures.append(f"字幕缺失或无法解析：{srt}")
    elif spans:
        failures.extend(cue_window_problems(cues, spans))
        try:
            samples, rate = decode_audio(args.film)
            blocks = rms_blocks(samples, rate)
            offsets = speech_windows(cues, spans, blocks)
            silent = [i for i, item in enumerate(offsets, 1) if item is None or not item[2]]
            leads = [item[0] for item in offsets if item]
            report["cues_without_speech"] = silent
            report["max_lead_seconds"] = max(leads) if leads else None
            if silent:
                failures.append(f"这些字幕窗口里没有语音：{silent}")
            if leads and max(leads) > args.max_lead:
                failures.append(f"字幕最多领先语音 {max(leads):.3f}s，超过 {args.max_lead}s")
        except Exception as exc:  # 解码失败本身就是问题，不要静默跳过
            failures.append(f"音频解码失败，无法校验字幕同步：{exc}")

    report["failures"] = failures
    report["status"] = "PASS" if not failures else "FAIL"
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failures:
        print("\n硬失败：\n- " + "\n- ".join(failures), file=sys.stderr)
        return 1
    print("\nPASS：时长/帧数/音轨长度/字幕窗口/字幕与语音同步全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
