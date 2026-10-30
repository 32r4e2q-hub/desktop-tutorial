#!/usr/bin/env python3
"""成片质检：容器规格 / 画面冻结与黑帧 / 音频电平与静音 / 字幕时间轴 / 封面尺寸。

这不是"看一眼就签收"的脚本：它把能量化的部分全部量化，写进
``work/wakayama1998/edit/delivery/qc-report.json`` 与 ``qa/qc-summary.md``，
任何一项硬闸门不过就以非零退出码收口。无法量化的部分（构图语义、人脸观感）
在报告里明确标注为需要人工复核，不伪装成通过。

用法::

    python3 production/wakayama1998/qc.py [--delivery 交付] [--work work/wakayama1998/edit]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

FILM_NAME = "Wakayama_Case_Final.mp4"
COVER_NAME = "Wakayama_Cover.png"
SRT_NAME = "Wakayama_Subtitles.srt"
EXPECTED = {"width": 1920, "height": 1080, "fps": 24, "duration": 180.0, "frames": 4320}
BLACK_MEAN = 7.0
FREEZE_DIFF = 0.35
FREEZE_SECONDS = 1.4
FLASH_MEAN_JUMP = 55.0


def run(command, capture=True):
    return subprocess.run([str(part) for part in command], check=True,
                          capture_output=capture, text=capture)


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        text=True))


def decode_gray(path: Path, fps: float = 4.0, width: int = 320, height: int = 180) -> np.ndarray:
    process = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(path), "-an",
        "-vf", f"fps={fps},scale={width}:{height},format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ], check=True, capture_output=True)
    frame_bytes = width * height
    count = len(process.stdout) // frame_bytes
    return np.frombuffer(process.stdout[:count * frame_bytes], dtype=np.uint8).reshape(count, height, width)


def decode_audio(path: Path) -> np.ndarray:
    process = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0",
        "-ac", "1", "-ar", "48000", "-f", "s16le", "-",
    ], check=True, capture_output=True)
    return np.frombuffer(process.stdout, dtype="<i2").astype(np.float32) / 32768.0


def dbfs(value: float) -> float:
    return -120.0 if value <= 1e-12 else round(20.0 * float(np.log10(value)), 2)


def analyse_picture(frames: np.ndarray, fps: float, shots: list[dict]) -> dict:
    means = frames.reshape(len(frames), -1).mean(axis=1)
    diffs = np.abs(np.diff(frames.astype(np.int16), axis=0)).reshape(max(1, len(frames) - 1), -1).mean(axis=1)
    duration = len(frames) / fps

    # Shot boundaries are fade-to-black hand-offs. A black sample landing exactly on a cut is the
    # planned 0.3s chapter fade, not a black-frame defect; anything else is reported.
    cut_times = [float(shot["start"]) for shot in shots]
    black = [round(float(i / fps), 2) for i, mean in enumerate(means) if mean < BLACK_MEAN]
    unexpected_black = [at for at in black
                        if at < duration - 1.6
                        and not any(abs(at - cut) <= 0.45 for cut in cut_times)]

    freeze_runs, start = [], None
    for index, diff in enumerate(diffs):
        if diff < FREEZE_DIFF:
            if start is None:
                start = index
        else:
            if start is not None and (index - start) / fps >= FREEZE_SECONDS:
                freeze_runs.append({"start": round(start / fps, 2), "end": round(index / fps, 2)})
            start = None
    if start is not None and (len(diffs) - start) / fps >= FREEZE_SECONDS:
        freeze_runs.append({"start": round(start / fps, 2), "end": round(len(diffs) / fps, 2)})

    # A hard cut between a dark and a bright shot also changes the mean luma; only jumps that
    # do not sit on a shot boundary are treated as flicker.
    flashes = []
    for index, jump in enumerate(np.abs(np.diff(means))):
        at = index / fps
        if jump <= FLASH_MEAN_JUMP:
            continue
        if any(abs(at - cut) <= 0.6 for cut in cut_times):
            continue
        flashes.append(round(float(at), 2))
    return {
        "sampled_frames": int(len(frames)),
        "sample_fps": fps,
        "mean_luma_min": round(float(means.min()), 2),
        "mean_luma_max": round(float(means.max()), 2),
        "mean_luma_avg": round(float(means.mean()), 2),
        "unexpected_black_samples": unexpected_black,
        "freeze_runs": freeze_runs,
        "flash_samples": flashes,
        "motion_percentile_10": round(float(np.percentile(diffs, 10)), 3),
        "motion_median": round(float(np.median(diffs)), 3),
    }


def analyse_sound(samples: np.ndarray, chapters: list[dict]) -> dict:
    rate = 48000
    window = rate
    windows = [samples[i:i + window] for i in range(0, len(samples), window) if len(samples[i:i + window])]
    levels = [float(np.sqrt(np.mean(window_.astype(np.float64) ** 2))) for window_ in windows]
    silent = [index for index, level in enumerate(levels) if dbfs(level) < -50.0]
    per_chapter = []
    for chapter in chapters:
        start = int(float(chapter["start"]) * rate)
        end = int((float(chapter["start"]) + float(chapter["duration"])) * rate)
        segment = samples[start:end]
        per_chapter.append({
            "id": chapter["id"],
            "start": chapter["start"],
            "rms_dbfs": dbfs(float(np.sqrt(np.mean(segment.astype(np.float64) ** 2)))),
            "peak_dbfs": dbfs(float(np.abs(segment).max())),
        })
    tail = samples[int(179.0 * rate):]
    return {
        "duration_seconds": round(len(samples) / rate, 3),
        "rms_dbfs": dbfs(float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))),
        "peak_dbfs": dbfs(float(np.abs(samples).max())),
        "silent_seconds": len(silent),
        "silent_fraction": round(len(silent) / max(1, len(levels)), 4),
        "final_second_dbfs": dbfs(float(np.sqrt(np.mean(tail.astype(np.float64) ** 2)))) if len(tail) else None,
        "chapters": per_chapter,
    }


def parse_srt(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    cues = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        match = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", lines[1])
        if not match:
            continue
        values = [int(value) for value in match.groups()]
        start = values[0] * 3600 + values[1] * 60 + values[2] + values[3] / 1000
        end = values[4] * 3600 + values[5] * 60 + values[6] + values[7] / 1000
        cues.append({"index": int(lines[0]), "start": round(start, 3), "end": round(end, 3),
                     "lines": lines[2:]})
    return cues


def check_subtitles(srt: Path, story: dict) -> dict:
    all_cues = parse_srt(srt)
    shots = {shot["id"]: shot for shot in story["shots"]}
    # Cues after the last shot's narration belong to the end card (title + question), which is
    # post-produced overlay text rather than shot-locked narration.
    end_card = [cue for cue in all_cues if cue["start"] >= story["shots"][-1]["start"]
                and cue["lines"] and cue["lines"][0] == story["presentation"].get("end_question", "")]
    cues = [cue for cue in all_cues if cue not in end_card]
    problems = []
    if len(cues) != len(shots):
        problems.append(f"expected {len(shots)} shot-locked cues, found {len(cues)}")
    if story["presentation"].get("end_question") and not end_card:
        problems.append("the end-card question is missing from the SRT")
    overlaps = 0
    for position, (cue, shot) in enumerate(zip(cues, story["shots"])):
        if cue["index"] != position + 1:
            problems.append(f"cue {position + 1}: index is {cue['index']}")
        shot_end = shot["start"] + shot["duration"]
        if cue["start"] < shot["start"] - 0.05 or cue["end"] > shot_end + 0.05:
            problems.append(f"{shot['id']}: cue {cue['start']}-{cue['end']} escapes shot "
                            f"{shot['start']}-{shot_end}")
        if cue["end"] - cue["start"] < 0.6:
            problems.append(f"{shot['id']}: cue shorter than 0.6s")
        if len(cue["lines"]) > 2:
            problems.append(f"{shot['id']}: more than two subtitle lines")
        if any(len(line) > 26 for line in cue["lines"]):
            problems.append(f"{shot['id']}: a subtitle line exceeds 26 characters")
        if position and cue["start"] < cues[position - 1]["end"] - 0.001:
            overlaps += 1
    if overlaps:
        problems.append(f"{overlaps} overlapping cues")
    return {
        "cues": len(cues),
        "end_card_cues": len(end_card),
        "covers_all_shots": len(cues) == len(shots),
        # Two-line cues are split at punctuation, so the joined lines must equal the narration.
        "covers_all_lines": ["".join(cue["lines"]) for cue in cues] == [shot["narration"] for shot in story["shots"]],
        "problems": problems,
    }


def export_fullres_stills(film: Path, story: dict, out_dir: Path) -> list[str]:
    """One full-resolution still per shot, so AI pseudo-text can be checked at native pixels.

    3x3 contact sheets are downscaled to 426 px tiles, where garbled on-screen lettering hides.
    These JPEGs keep the full 1920x1080 detail and land in the repo for a human (or an agent)
    to inspect shot by shot.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    produced = []
    for shot in story["shots"]:
        at = shot["start"] + min(1.6, shot["duration"] / 2)
        target = out_dir / f"{shot['id']}.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(film),
                        "-frames:v", "1", "-q:v", "3", str(target)], check=True)
        produced.append(str(target.relative_to(ROOT)))
    return produced


def make_contact_sheets(film: Path, story: dict, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    produced = []
    timestamps = [shot["start"] + min(1.2, shot["duration"] / 2) for shot in story["shots"]]
    for group in range(0, len(timestamps), 9):
        chunk = timestamps[group:group + 9]
        inputs, filters = [], []
        for offset, at in enumerate(chunk):
            inputs += ["-ss", f"{at:.3f}", "-i", str(film)]
            filters.append(f"[{offset}:v]scale=426:240:force_original_aspect_ratio=decrease,"
                           f"pad=426:240:(ow-iw)/2:(oh-ih)/2,setsar=1[v{offset}]")
            if offset == 0:
                # Input seeking is per-input; repeated -ss before each -i is what we want.
                pass
        labels = "".join(f"[v{offset}]" for offset in range(len(chunk)))
        rows = 3 if len(chunk) > 3 else 1
        cols = 3
        filters.append(f"{labels}xstack=inputs={len(chunk)}:layout=" + "|".join(
            f"{(index % cols) * 426}_{(index // cols) * 240}" for index in range(len(chunk))) + ":fill=black[out]")
        target = out_dir / f"sheet-{group // 9 + 1}.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
                        "-map", "[out]", "-frames:v", "1", "-q:v", "4", str(target)], check=True)
        produced.append(str(target.relative_to(ROOT)))
    return produced


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delivery", type=Path, default=ROOT / "交付")
    parser.add_argument("--work", type=Path, default=ROOT / "work" / "wakayama1998" / "edit")
    args = parser.parse_args()

    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    film = args.delivery / FILM_NAME
    if not film.is_file():
        print(f"MISSING {film}", flush=True)
        return 1
    cover = args.delivery / COVER_NAME
    srt = args.delivery / SRT_NAME

    data = probe(film)
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    audio = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    if not video:
        print("FAIL: no video stream", flush=True)
        return 1
    container = {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": video.get("avg_frame_rate"),
        "frames": int(video.get("nb_frames") or 0),
        "duration_seconds": round(float(data["format"]["duration"]), 3),
        "bytes": film.stat().st_size,
        "video_codec": video.get("codec_name"),
        "audio_codec": (audio or {}).get("codec_name"),
        "sample_rate": int((audio or {}).get("sample_rate", 0) or 0),
        "channels": int((audio or {}).get("channels", 0) or 0),
    }
    failures = []
    if (container["width"], container["height"]) != (EXPECTED["width"], EXPECTED["height"]):
        failures.append("not 1920x1080")
    if container["fps"] != "24/1":
        failures.append(f"fps is {container['fps']}, expected 24/1")
    if abs(container["duration_seconds"] - EXPECTED["duration"]) > 0.04:
        failures.append(f"duration is {container['duration_seconds']}s, expected 180s")
    if container["frames"] not in (0, EXPECTED["frames"]):
        failures.append(f"frames is {container['frames']}, expected 4320")
    if container["sample_rate"] != 48000 or container["channels"] != 2:
        failures.append("audio must be 48 kHz stereo")

    frames = decode_gray(film)
    picture = analyse_picture(frames, fps=4.0, shots=story["shots"])
    if picture["unexpected_black_samples"]:
        failures.append(f"unexpected black samples before the tail: {picture['unexpected_black_samples'][:6]}")
    long_freezes = [run_ for run_ in picture["freeze_runs"] if run_["end"] - run_["start"] >= 2.5]
    if long_freezes:
        failures.append(f"freeze longer than 2.5s: {long_freezes}")

    sound = analyse_sound(decode_audio(film), story["chapters"])
    if sound["rms_dbfs"] < -30:
        failures.append(f"overall loudness too low: {sound['rms_dbfs']} dBFS")
    if sound["peak_dbfs"] > -1.0:
        failures.append(f"peak too hot: {sound['peak_dbfs']} dBFS")
    if (sound["final_second_dbfs"] or -120) > -40:
        failures.append("the last second is not silent as briefed")

    subtitles = check_subtitles(srt, story) if srt.is_file() else {"cues": 0, "problems": ["missing SRT"]}
    if subtitles["problems"]:
        failures.append(f"subtitle problems: {subtitles['problems'][:4]}")

    cover_info = {"exists": cover.is_file()}
    if cover.is_file():
        from PIL import Image
        with Image.open(cover) as image:
            cover_info.update(width=image.width, height=image.height, mode=image.mode,
                              bytes=cover.stat().st_size)
        if (cover_info["width"], cover_info["height"]) != (1920, 1080):
            failures.append("cover is not 1920x1080")

    sheets = make_contact_sheets(film, story, HERE / "qa" / "sheets")
    stills = export_fullres_stills(film, story, HERE / "qa" / "fullres")

    report = {
        "film": str(film.relative_to(ROOT)) if film.is_relative_to(ROOT) else str(film),
        "container": container,
        "picture": picture,
        "sound": sound,
        "subtitles": subtitles,
        "cover": cover_info,
        "contact_sheets": sheets,
        "fullres_stills": stills,
        "hard_gate_failures": failures,
        "human_review_still_required": [
            "逐镜确认每一帧都是连续运动（本脚本只能量化帧间差异，不能判断语义）",
            "确认没有遗体、伤口、血腥、可读乱码文字与人物面部崩坏",
            "确认字幕没有遮挡人物面部与关键物证",
            "确认人物、服装、住宅在三分钟里保持一致",
        ],
    }
    delivery_dir = args.work / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    (delivery_dir / "qc-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
    summary = [
        "# 成片质检摘要",
        "",
        f"- 文件：{report['film']}（{container['bytes'] / 1e6:.1f} MB）",
        f"- 规格：{container['width']}×{container['height']} · {container['fps']} fps · "
        f"{container['duration_seconds']} 秒 · {container['frames']} 帧 · "
        f"{container['video_codec']} + {container['audio_codec']} {container['sample_rate']} Hz "
        f"{container['channels']} 声道",
        f"- 画面：平均亮度 {picture['mean_luma_avg']} · 非预期黑帧 {len(picture['unexpected_black_samples'])} · "
        f"冻结段 {len(picture['freeze_runs'])} · 闪烁跳变 {len(picture['flash_samples'])}",
        f"- 声音：RMS {sound['rms_dbfs']} dBFS · 峰值 {sound['peak_dbfs']} dBFS · "
        f"静音占比 {sound['silent_fraction'] * 100:.1f}% · 最后一秒 {sound['final_second_dbfs']} dBFS",
        f"- 字幕：{subtitles['cues']} 条（{len(subtitles['problems'])} 个问题）",
        f"- 封面：{cover_info.get('width')}×{cover_info.get('height')}",
        f"- 原始像素抽帧：{len(stills)} 张（`qa/fullres/`，用于查 AI 伪文字与面部崩坏）",
        "",
        "## 硬闸门",
        "",
    ]
    summary += [f"- ❌ {item}" for item in failures] or ["- ✅ 全部通过"]
    summary += ["", "## 仍需人工复核", ""] + [f"- {item}" for item in report["human_review_still_required"]]
    (HERE / "qa" / "qc-summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("container", "subtitles", "hard_gate_failures")},
                     ensure_ascii=False, indent=2))
    print(f"QC {'PASS' if not failures else 'FAIL'} → {delivery_dir/'qc-report.json'}", flush=True)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
