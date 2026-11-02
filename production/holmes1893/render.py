#!/usr/bin/env python3
"""Deterministic 180-second edit from verified Agnes motion clips and selected Chinese VO.

30 shots · 24 fps · 1920×1080. Legend scenes (aged newspaper engravings) are separated from
the photoreal 3D reenactment by three different transitions: a soft paper wipe between two
print shots, a 0.3 s mist dissolve between two 3D shots, and the torn-paper cut at S14 where
the legend is ripped open to reveal the real image underneath.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from production import series_cover  # noqa: E402  全系列统一封面模板（production/series_cover.py）
from production.holmes1893.build_audio import build_soundtrack  # noqa: E402
from production.holmes1893.generate import MODEL, SOURCE_SIZE, digest, request_hash  # noqa: E402

FPS = 24
DURATION = 180
TOTAL_FRAMES = FPS * DURATION
PAD = 0.40  # clone tail so every xfade has room without shifting a single cut time

# Print-panel shots sometimes come back with embedded mattes; only verified paired bands are cropped.
LETTERBOX_CHECK_SHOTS = {"S09", "S12", "S13"}
CARD_TEXT_MAX_WIDTH = 1660
END_CARD_AT = 176.40
# 片尾卡压在最后一镜（S30 现代芝加哥航拍）上，所以压暗放在这一镜的逐镜调色里做。
END_CARD_SHOT = "S30"
# 片尾卡渐隐：S30 从 174.0 s 开始，片尾卡在 174.55 s 亮起，0.55 s 处开始渐隐到黑。
END_CARD_FADE_START = 0.10
END_CARD_FADE_SECONDS = 2.30  # 0.10 s 起到 176.40 s 刚好全黑，片尾卡正是在黑底上浮出
# 片尾压暗：像素乘法系数。实测 0.42 时城市仍可辨认，金色片名与白色字幕都清晰。
END_CARD_DIM_GAIN = 0.42


def run(command, capture=False):
    return subprocess.run([str(part) for part in command], check=True,
                          capture_output=capture, text=capture)


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)
    ], text=True))


def media_summary(path: Path) -> dict:
    data = probe(path)
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    audio = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    if not video:
        raise RuntimeError("Final film has no video stream")
    result = {
        "duration_seconds": float(data["format"]["duration"]),
        "bytes": path.stat().st_size,
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": video.get("avg_frame_rate"),
        "frames": int(video.get("nb_frames") or 0),
        "video_codec": video.get("codec_name"),
    }
    if audio:
        result.update(audio_codec=audio.get("codec_name"), sample_rate=int(audio.get("sample_rate", 0)),
                      audio_channels=int(audio.get("channels", 0)))
    return result


def verify_sources(story: dict, sources: Path) -> dict:
    results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    if results.get("model") != MODEL or results.get("source_size") != SOURCE_SIZE:
        raise RuntimeError("Only verified Agnes Video 2.5 Flash 720P sources are accepted")
    if set(results.get("required_generated_shots", [])) != {shot["id"] for shot in story["shots"]}:
        raise RuntimeError("Provenance does not list every required Agnes shot")
    rows = results.get("shots", {})
    for shot in story["shots"]:
        sid = shot["id"]
        record = rows.get(sid, {})
        source = sources / f"{sid}.mp4"
        if record.get("status") != "completed" or not source.is_file():
            raise RuntimeError(f"Missing verified Agnes footage: {sid}; refusing a still-image substitute")
        if record.get("request_hash") != request_hash(story, shot):
            raise RuntimeError(f"Agnes prompt/provenance mismatch: {sid}")
        if record.get("sha256") != digest(source) or record.get("bytes") != source.stat().st_size:
            raise RuntimeError(f"Agnes source SHA-256/size mismatch: {sid}")
    return rows


# ------------------------------------------------------------------ 双层转场
def transition_into(previous: dict, shot: dict) -> tuple[str, float]:
    """Pick the transition that carries the story from one panel style to the next."""
    before, after = previous["style_variant"], shot["style_variant"]
    if before != "real" and after != "real":
        return "smoothright", 0.35      # 传说版画之间：纸张翻页擦除
    if before != "real" and after == "real":
        return "fade", 0.12             # 撕裂转场：撕裂本身在 S14 画面里完成
    if before == "real" and after != "real":
        return "fade", 0.30             # 回到传说：雾气叠化
    return "fade", 0.30                 # 写实段落之间：0.3秒雾气叠化


def transition_plan(story: dict) -> dict:
    shots = story["shots"]
    return {shots[i]["id"]: transition_into(shots[i - 1], shots[i]) for i in range(1, len(shots))}


# ------------------------------------------------------------------ 素材归一化
def detect_matte_bands(image: Image.Image) -> tuple[int, int] | None:
    """Detect paired, nearly black borders with a sharp boundary in a low-resolution frame."""
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    height, _width = gray.shape
    max_scan = max(2, int(height * 0.30))

    def edge_run(reverse: bool) -> int:
        run_length = 0
        for offset in range(max_scan):
            y = height - 1 - offset if reverse else offset
            row = gray[y, :].astype(np.float32)
            if float(np.mean(row)) < 10.0 and float(np.std(row)) < 4.0 and float(np.mean(row < 20)) > 0.995:
                run_length += 1
            else:
                break
        return run_length

    top, bottom = edge_run(False), edge_run(True)
    minimum = max(22, int(height * 0.06))
    if top < minimum or bottom < minimum:
        return None
    probe_offset = min(max(8, int(height * 0.02)), max(0, height - max(top, bottom) - 1))
    edge_mean = float(np.mean(gray[:min(5, top), :]))
    top_probe = top + probe_offset
    bottom_probe = height - 1 - bottom - probe_offset
    top_contrast = float(np.mean(gray[top_probe, :])) - edge_mean if top_probe < height else 0.0
    bottom_edge_mean = float(np.mean(gray[height-min(5, bottom):, :]))
    bottom_contrast = float(np.mean(gray[bottom_probe, :])) - bottom_edge_mean if bottom_probe >= 0 else 0.0
    if max(top_contrast, bottom_contrast) < 25.0:
        return None
    return top, bottom


def detect_source_letterbox_bands(source: Path, shot: dict, info: dict) -> list[tuple[int, int]]:
    """Sample print shots at three times; only crop when paired hard mattes persist."""
    if shot.get("id") not in LETTERBOX_CHECK_SHOTS:
        return []
    duration = float(info["duration_seconds"])
    sample_bands = []
    for index, fraction in enumerate((0.15, 0.50, 0.85)):
        timestamp = min(max(0.05, duration * fraction), max(0.05, duration - 0.05))
        sample_path = source.parent / f".{source.stem}-letterbox-check-{index}.png"
        try:
            run(["ffmpeg", "-y", "-v", "error", "-ss", f"{timestamp:.3f}", "-i", source,
                 "-frames:v", "1", "-vf", "scale=640:360", sample_path])
            with Image.open(sample_path) as image:
                bands = detect_matte_bands(image)
            if bands:
                sample_bands.append(bands)
        finally:
            sample_path.unlink(missing_ok=True)
    return sample_bands if len(sample_bands) >= 2 else []


def letterbox_crop_filter(shot: dict, info: dict, detected_bands: list[tuple[int, int]] | None = None) -> str | None:
    if shot.get("id") not in LETTERBOX_CHECK_SHOTS or not detected_bands or len(detected_bands) < 2:
        return None
    source_width, source_height = int(info["width"]), int(info["height"])
    scale_y = source_height / 360.0
    top = int(round(float(np.median([band[0] for band in detected_bands])) * scale_y)) + 2
    bottom = int(round(float(np.median([band[1] for band in detected_bands])) * scale_y)) + 2
    top = (top // 2) * 2
    bottom = (bottom // 2) * 2
    active_height = ((source_height - top - bottom) // 2) * 2
    active_width = (int(active_height * 16 / 9) // 2) * 2
    if active_width > source_width or active_height < source_height * 0.5:
        raise RuntimeError(f"{shot['id']} letterbox correction is incompatible with source {source_width}x{source_height}")
    left = ((source_width - active_width) // 2 // 2) * 2
    if left < 0 or top < 0 or bottom < 0:
        raise RuntimeError(f"{shot['id']} letterbox crop is out of bounds for source {source_width}x{source_height}")
    return f"crop={active_width}:{active_height}:{left}:{top}"


def source_luma(source: Path) -> float:
    """Median YAVG of five sampled frames: how dark this clip actually is."""
    values = []
    for fraction in (0.1, 0.3, 0.5, 0.7, 0.9):
        sample = subprocess.run([
            "ffmpeg", "-v", "info", "-ss", f"{fraction * 5:.2f}", "-i", str(source),
            "-frames:v", "1", "-vf", "scale=160:90,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
            "-f", "null", "-",
        ], capture_output=True, text=True)
        for line in (sample.stderr or "").splitlines():
            if "YAVG=" in line:
                try:
                    values.append(float(line.split("YAVG=")[1].strip()))
                except ValueError:
                    pass
    if not values:
        return 64.0
    return float(np.median(values))


def shadow_lift_gamma(luma: float) -> float:
    """Lift the darkest clips only; daylight shots keep the original grade (1.10)."""
    if luma >= 52.0:
        return 1.10
    return float(min(1.48, 1.10 + (52.0 - luma) / 52.0 * 0.42))


def shot_filter(shot: dict, info: dict, detected_bands, luma: float = 64.0) -> tuple[str, dict]:
    """Return the per-input filter chain (normalize to 1920x1080/24fps, clone a 0.4 s tail)."""
    if not 3.75 <= info["duration_seconds"] <= 9.5:
        raise RuntimeError(f"{shot['id']}: invalid Agnes clip duration {info['duration_seconds']:.3f}s")
    if info["width"] < 640 or info["height"] < 360:
        raise RuntimeError(f"{shot['id']}: returned video resolution is too small")
    correction = letterbox_crop_filter(shot, info, detected_bands)
    closing = shot["id"] == END_CARD_SHOT
    parts = ([correction] if correction else []) + [
        "scale=1920:1080:force_original_aspect_ratio=increase",
        "crop=1920:1080",
        "setsar=1",
        f"eq=gamma={shadow_lift_gamma(luma):.3f}:brightness=0.014",
        # 片尾镜整体压暗：金色片名与白字幕要压在航拍亮区上，靠逐镜调色最稳。
        # 片尾镜：S30 结尾本身会「渐白」，纯粹提亮/压暗都盖不住金色片名，
        # 所以先做轻度压暗，再让画面在片尾卡期间渐隐到黑——字幕在合成时后叠，因此保持清晰。
        *(["eq=gamma=0.72:brightness=-0.08:contrast=1.04:saturation=0.92"] if closing else []),
        *([f"fade=t=out:st={END_CARD_FADE_START:.2f}:d={END_CARD_FADE_SECONDS:.2f}"]
          if closing else []),
        # 传说版画：极轻的纸张抖动与颗粒，加强「会动的旧报纸」质感（不改变构图）。
        *(["noise=alls=7:allf=t+u", "vignette=angle=0.32"] if shot["style_variant"] != "real" else []),
        "format=yuv420p",
        # 先补 0.4 秒冻结尾帧、再按「本镜时长 + 尾帧」裁切：叠化只吃掉这段尾巴，
        # 每个镜头的可见时长和切点因此一秒都不动。
        f"tpad=stop_mode=clone:stop_duration={PAD:.2f}",
        f"trim=duration={float(shot['duration']) + PAD:.3f}",
        "setpts=PTS-STARTPTS",
        # xfade 要求输入是恒定帧率与统一时基。
        "fps=24",
        "settb=AVTB",
    ]
    report = {"id": shot["id"], "duration_seconds": float(shot["duration"]),
              "source_luma": round(luma, 1), "grade_gamma": round(shadow_lift_gamma(luma), 3),
              "closing_shot_darkened": closing,
              "source_duration_seconds": round(info["duration_seconds"], 3),
              "source_width": info["width"], "source_height": info["height"],
              "embedded_letterbox_crop_filter": correction,
              "embedded_letterbox_detected_samples": len(detected_bands or [])}
    return ",".join(parts), report


def build_picture(story: dict, sources: Path, work_dir: Path) -> tuple[Path, list[dict]]:
    """One filtergraph: 30 normalized clips joined by the chosen transitions, cut at exact times."""
    shots = story["shots"]
    plan = transition_plan(story)
    reports = []
    command = ["ffmpeg", "-y", "-v", "error", "-threads", "2"]
    for shot in shots:
        command += ["-i", str(sources / f"{shot['id']}.mp4")]
    graph = []
    for index, shot in enumerate(shots):
        source = sources / f"{shot['id']}.mp4"
        info = media_summary(source)
        bands = detect_source_letterbox_bands(source, shot, info)
        chain, report = shot_filter(shot, info, bands, source_luma(source))
        report["source_sha256"] = digest(source)
        reports.append(report)
        graph.append(f"[{index}:v]{chain}[v{index}]")

    current = "v0"
    for index in range(1, len(shots)):
        shot = shots[index]
        kind, duration = plan[shot["id"]]
        # Every cut keeps its nominal time: the previous clip carries a cloned 0.4 s tail, so the
        # overlap is taken from that tail and no shot boundary (and therefore no caption) moves.
        offset = float(shot["start"]) - 1e-6
        label = f"x{index}"
        graph.append(
            f"[{current}][v{index}]xfade=transition={kind}:duration={duration:.3f}:offset={offset:.3f}[{label}]"
        )
        current = label
    graph.append(f"[{current}]trim=duration={DURATION},setpts=PTS-STARTPTS[vout]")

    picture = work_dir / "picture-only.mp4"
    command += [
        "-filter_complex", ";".join(graph),
        "-map", "[vout]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
        "-r", str(FPS), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-t", str(DURATION), str(picture),
    ]
    run(command)
    summary = media_summary(picture)
    if abs(summary["duration_seconds"] - DURATION) > 0.05:
        raise RuntimeError(f"Picture assembly is {summary['duration_seconds']:.2f}s, expected {DURATION}s")
    return picture, reports


# ------------------------------------------------------------------ 字幕
def ass_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def escape_ass(text: str) -> str:
    return text.replace("\\", "/").replace("{", "（").replace("}", "）").replace("\n", " ")


def highlight_text(text: str, phrases: list[str], scale: int = 124) -> str:
    """White caption with the story's keywords enlarged and gold (ASS colours are &HBBGGRR)."""
    text = escape_ass(text)
    out = []
    i = 0
    ordered = sorted(phrases, key=len, reverse=True)
    while i < len(text):
        hit = next((phrase for phrase in ordered if text.startswith(phrase, i)), None)
        if hit:
            out.append(r"{\c&H005FC9F4&\fs" + str(scale) + r"\b1}" + hit + r"{\rCaption}")
            i += len(hit)
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


CAPTION_LINE_MAX = 26


def split_caption(text: str, limit: int = CAPTION_LINE_MAX) -> list[str]:
    """Split one narration line into at most two balanced subtitle lines (ASS never wraps)."""
    text = text.strip()
    if len(text) <= limit:
        return [text]
    best = None
    for index, char in enumerate(text):
        if char in "，；：、。？！,;: " and 0 < index < len(text) - 1:
            left, right = text[:index + 1].strip(), text[index + 1:].strip()
            if len(left) <= limit and len(right) <= limit:
                balance = abs(len(left) - len(right))
                if best is None or balance < best[0]:
                    best = (balance, left, right)
    if best:
        return [best[1], best[2]]
    for index in range(len(text) // 2, 0, -1):
        left, right = text[:index].strip(), text[index:].strip()
        if len(left) <= limit and len(right) <= limit:
            return [left, right]
    raise RuntimeError(f"caption cannot be split into two readable lines: {text!r}")


def dots_events(story: dict) -> list[str]:
    """S26: the confession's twenty-seven dots light up one by one, then five go out again."""
    shot = next((row for row in story["shots"] if row["id"] == "S26"), None)
    if shot is None:
        return []
    start = float(shot["start"]) + 0.55
    events = []
    spacing, radius = 38, 8
    origin_x, origin_y = 960 - spacing * 13, 764
    dying = {3, 8, 12, 19, 24}
    for index in range(27):
        column, row = index % 14, index // 14
        x = origin_x + column * spacing * 2
        y = origin_y + row * 36
        draw = f"m {x - radius} {y} b {x} {y - radius * 1.4} {x + radius} {y - radius * 1.4} {x + radius} {y} " \
               f"b {x + radius} {y + radius * 1.4} {x - radius} {y + radius * 1.4} {x - radius} {y} "
        appear = start + index * 0.13
        events.append(
            f"Dialogue: 3,{ass_time(appear)},{ass_time(float(shot['start']) + float(shot['duration']) - 0.05)},"
            f"Dot,,0,0,0,,{{\\an7\\pos(0,0)\\p1\\c&H002A3CE8&\\alpha&H20&\\bord0\\blur1}}{draw}"
        )
        if index in dying:
            fade_at = start + 27 * 0.13 + 0.25
            events.append(
                f"Dialogue: 3,{ass_time(fade_at)},{ass_time(float(shot['start']) + float(shot['duration']) - 0.05)},"
                f"Dot,,0,0,0,,{{\\an7\\pos(0,0)\\p1\\c&H00343CE6&\\alpha&HA8&\\bord0\\blur1}}{draw}"
            )
    return events


def write_subtitles(path: Path, cues: list[dict], story: dict, srt_path: Path) -> None:
    pres = story["presentation"]
    phrases = pres["highlight_keywords"]
    size = int(pres["subtitle_style"]["font_size_px"])
    highlight = int(round(size * float(pres["subtitle_style"]["highlight_scale"])))
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "YCbCr Matrix: TV.709",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Caption,Noto Sans CJK SC,{size},&H00FFFFFF,&H0000FFFF,&H00111110,&H99000000,1,0,0,0,100,100,0,0,1,3.2,1.0,2,115,115,76,1",
        # ASS 颜色是 &HBBGGRR：金色 #F4C95F 必须写成 &H005FC9F4，否则会渲染成浅蓝。
        "Style: Title,Noto Serif CJK SC,112,&H005FC9F4,&H0000FFFF,&H0013110D,&H99000000,1,0,0,0,100,100,1,0,1,5,2,5,80,80,0,1",
        "Style: Tag,Noto Sans CJK SC,26,&H00E6E6E6,&H0000FFFF,&H00101010,&H99000000,1,0,0,0,100,100,1,0,1,2,0,7,96,96,42,1",
        "Style: Dot,Noto Sans CJK SC,20,&H00343CE6,&H0000FFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for cue in cues:
        rendered = "\\N".join(highlight_text(part, phrases, highlight) for part in split_caption(cue["text"]))
        lines.append(
            f"Dialogue: 1,{ass_time(cue['start'])},{ass_time(cue['end'])},Caption,,0,0,0,,{{\\q2\\fad(70,80)}}{rendered}"
        )

    # 双层画面的常驻标签：一眼分辨「传说想象」与「史实复原」。
    shots = {shot["id"]: shot for shot in story["shots"]}
    for cue in cues:
        shot = shots[cue["shot_id"]]
        if shot["style_variant"] != "real":
            label = "传说画面 · 泛黄报纸版画"
        else:
            label = "史实复原 · 3D情景动画"
        lines.append(
            f"Dialogue: 1,{ass_time(cue['start'])},{ass_time(cue['end'])},Tag,,0,0,0,,"
            f"{{\\fad(200,200)}}{label}"
        )

    lines += dots_events(story)

    # Only the closing title is a post-produced overlay; the model is never asked to render text.
    # 片尾压暗不放在 ASS 里：\\p1 整幅绘图在部分 libass 构建上会被整层丢弃（实测成片里底板
    # 完全没渲染），改由 main() 在滤镜链上用 eq 做时间门控压暗，ASS 只负责文字。
    lines += [
        f"Dialogue: 2,{ass_time(END_CARD_AT)},{ass_time(179.45)},Title,,0,0,0,,{{\\pos(960,158)\\fad(420,430)\\fs100}}"
        + pres["end_title"],
        f"Dialogue: 2,{ass_time(END_CARD_AT + 0.18)},{ass_time(179.45)},Caption,,0,0,0,,{{\\pos(960,278)\\fad(460,430)\\fs42}}"
        + pres["end_subtitle"],
        # 传说 vs 真相：两个数字并排，作为最后一个画面上的问题（字幕之下、片名之上）。
        f"Dialogue: 3,{ass_time(END_CARD_AT + 0.40)},{ass_time(179.45)},Title,,0,0,0,,{{\\pos(604,432)\\fad(500,430)\\fs92}}{pres['end_numbers'][0]}",
        f"Dialogue: 3,{ass_time(END_CARD_AT + 0.40)},{ass_time(179.45)},Caption,,0,0,0,,{{\\pos(604,508)\\fad(500,430)\\fs28}}{pres['end_numbers'][1]}",
        f"Dialogue: 3,{ass_time(END_CARD_AT + 0.62)},{ass_time(179.45)},Title,,0,0,0,,{{\\pos(1316,432)\\fad(540,430)\\fs92}}{pres['end_numbers'][2]}",
        f"Dialogue: 3,{ass_time(END_CARD_AT + 0.62)},{ass_time(179.45)},Caption,,0,0,0,,{{\\pos(1316,508)\\fad(540,430)\\fs28}}{pres['end_numbers'][3]}",
        f"Dialogue: 3,{ass_time(END_CARD_AT + 0.95)},{ass_time(179.45)},Title,,0,0,0,,{{\\pos(960,646)\\fad(560,430)\\fs40}}"
        + pres.get("end_question", ""),
        # A quiet, persistent honesty label: this is a reenactment, not news or evidence material.
        f"Dialogue: 1,{ass_time(0.80)},{ass_time(179.90)},Tag,,0,0,0,,{{\\an9\\pos(1868,42)\\alpha&H70&\\fs24\\c&H00E6E6E6&}}AI动画情景复原 · 非真实影像",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def srt_clock(seconds: float) -> str:
        milliseconds = round(seconds * 1000)
        hours, milliseconds = divmod(milliseconds, 3_600_000)
        minutes, milliseconds = divmod(milliseconds, 60_000)
        secs, milliseconds = divmod(milliseconds, 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    rows = []
    for i, cue in enumerate(cues, 1):
        body = "\n".join(split_caption(cue["text"]))
        rows.append(f"{i}\n{srt_clock(cue['start'])} --> {srt_clock(cue['end'])}\n{body}\n")
    question = pres.get("end_question", "").strip()
    if question:
        rows.append(f"{len(cues) + 1}\n{srt_clock(END_CARD_AT + 0.85)} --> {srt_clock(179.45)}\n{question}\n")
    srt_path.write_text("\n".join(rows), encoding="utf-8")


# ------------------------------------------------------------------ 字体 / 封面
def find_font(serif: bool = False) -> Path:
    override = os.getenv("HOLMES_FONT_SERIF" if serif else "HOLMES_FONT")
    if override and Path(override).is_file():
        return Path(override)
    candidates = []
    font_root = Path("/usr/share/fonts")
    if font_root.exists():
        patterns = ("**/NotoSerifCJK*", "**/*CJK*") if serif else ("**/NotoSansCJK*", "**/*CJK*")
        for pattern in patterns:
            candidates.extend(sorted(font_root.glob(pattern)))
    candidates += [ROOT / ".cache/fonts/NotoSerifCJKsc-Regular.otf"] if serif else []
    candidates += [ROOT / ".cache/fonts/NotoSansCJKsc-Regular.otf", ROOT / ".cache/fonts/NotoSerifCJKsc-Regular.otf"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("Noto CJK fonts are required to render Chinese titles and subtitles")


def text_width(draw: ImageDraw.ImageDraw, text: str, size: int, serif: bool = False) -> float:
    font = ImageFont.truetype(str(find_font(serif)), size)
    return float(draw.textlength(text, font=font))


def fit_size(draw: ImageDraw.ImageDraw, text: str, requested: int, max_width: int,
             serif: bool = False, floor: int = 60) -> int:
    size = int(requested)
    while size > floor and text_width(draw, text, size, serif) > max_width:
        size -= 2
    return size


def grab_frame(video: Path, seconds: float, work_dir: Path, tag: str) -> Image.Image:
    path = work_dir / f"cover-{tag}.jpg"
    run(["ffmpeg", "-y", "-v", "error", "-ss", f"{seconds:.3f}", "-i", video,
         "-frames:v", "1", "-q:v", "2", path])
    with Image.open(path) as image:
        return image.convert("RGB")


def make_cover(sources: Path, output: Path, story: dict, work_dir: Path) -> None:
    """封面走全系列统一的「谜案解码人」竖版模板，窗口里放本片的一帧。"""
    series_cover.make(story, sources, output, work_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    verify_sources(story, args.sources)
    args.work.mkdir(parents=True, exist_ok=True)

    picture, clip_report = build_picture(story, args.sources, args.work)

    mix, audio_report, cues = build_soundtrack(story, HERE / "audio", args.work)
    if not (args.work / "audio" / "mix-report.json").is_file():
        raise RuntimeError("Measured audio report was not written")
    ass_path = args.work / "holmes-captions.ass"
    srt_path = args.work / "H·H·霍姆斯_字幕.srt"
    write_subtitles(ass_path, cues, story, srt_path)

    font_dir = ROOT / ".cache" / "fonts"
    ass_part = f"ass={ass_path.as_posix()}" + (f":fontsdir={font_dir.as_posix()}" if font_dir.is_dir() else "")
    # 字幕单独一层；片尾压暗已经在 S30 的逐镜调色里完成，这里不再依赖任何时间表达式。
    graph = f"[0:v]{ass_part}[v]"
    final = args.output
    final.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", picture, "-i", mix,
        "-filter_complex", graph, "-map", "[v]", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-maxrate", "3200k", "-bufsize", "6400k", "-profile:v", "high", "-level", "4.1",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", str(DURATION), "-movflags", "+faststart", final,
    ])
    # 自述式诊断：沙箱读不到 Actions 日志，只能靠 run.log 里的这几行定位渲染问题。
    print("RENDER_GRAPH " + graph, flush=True)
    picture_info = probe(picture)
    print(f"PICTURE_DURATION {picture_info.get('duration_seconds')} "
          f"frames={picture_info.get('frames')} {picture_info.get('width')}x{picture_info.get('height')}", flush=True)
    for stamp in (170.0, 176.0, 179.0):
        print(f"PICTURE_LUMA {stamp:.1f} {frame_luma(picture, stamp, final.parent):.1f}", flush=True)
    for stamp in (100.0, 160.0, 176.0, 178.0):
        print(f"LUMA {stamp:.1f} {frame_luma(final, stamp, final.parent):.1f}", flush=True)
    # 把片尾两帧同时导进仓库 qa/：沙箱读不到 Actions 日志，也下载不了 artifact，只能看图定位。
    qa_dir = HERE / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    print("S30_REPORT " + json.dumps(
        next((row for row in clip_report if row.get("id") == END_CARD_SHOT), {}), ensure_ascii=False), flush=True)
    run(["ffmpeg", "-y", "-v", "error", "-i", str(picture), "-ss", "176.000",
         "-frames:v", "1", "-q:v", "3", str(qa_dir / "render-picture176.jpg")])
    for stamp, tag in ((160.0, "body"), (176.0, "endcard")):
        run(["ffmpeg", "-y", "-v", "error", "-i", str(final), "-ss", f"{stamp:.3f}",
             "-frames:v", "1", "-q:v", "3", str(qa_dir / f"render-{tag}.jpg")])
    verify_end_card_dim(final)
    summary = media_summary(final)
    if summary["width"] != 1920 or summary["height"] != 1080 or abs(summary["duration_seconds"] - 180.0) > 0.04:
        raise RuntimeError("Final video failed format/duration gate: " + json.dumps(summary, ensure_ascii=False))
    if summary.get("sample_rate") != 48000 or summary.get("audio_channels") != 2:
        raise RuntimeError("Final audio stream must be 48kHz stereo")
    if summary["frames"] not in (0, TOTAL_FRAMES):
        raise RuntimeError(f"Expected {TOTAL_FRAMES} frames, got {summary['frames']}")

    cover = final.parent / "H·H·霍姆斯_传说里的杀人城堡_封面.jpg"
    make_cover(args.sources, cover, story, args.work)
    srt_copy = final.parent / f"{final.stem}_字幕.srt"
    srt_copy.write_text(srt_path.read_text(encoding="utf-8"), encoding="utf-8")
    report = {
        "title": story["title"],
        "output": final.name,
        "unreviewed_first_cut": True,
        "human_visual_review": "pending",
        "video": summary,
        "shots": clip_report,
        "transitions": {shot["id"]: transition_plan(story).get(shot["id"]) for shot in story["shots"][1:]},
        "soundtrack": audio_report,
        "caption_cues": len(cues),
        "captions_ass": str(ass_path),
        "captions_srt": str(srt_path),
        "cover": str(cover),
        "source_model": MODEL,
        "source_resolution": SOURCE_SIZE,
        "final_resolution": "1920x1080 (upscaled in post)",
        "style_consistency": "Two STYLE blocks drive the film on purpose: the photoreal 3D block for "
                             "history and the aged newspaper-engraving block for the legend panels "
                             "(S09, S12, S13, S14). The corner tag plus the torn transition at S14 "
                             "keep the two layers instantly distinguishable; this is the brief's "
                             "two-layer rule, not style drift.",
        "all_30_generated_shots_verified_by_sha256": True,
        "note": "Every shot is an Agnes Video 2.5 Flash (720P) motion clip upscaled to 1080p; titles, "
                "captions, tags and the end card are composited in post. The footage is an AI-produced "
                "reenactment, not historical image material, and the legend panels are explicitly "
                "marked as newspaper invention rather than evidence.",
    }
    delivery = args.work / "delivery"
    delivery.mkdir(parents=True, exist_ok=True)
    (delivery / "technical-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                      encoding="utf-8")
    (delivery / "edit-decision-list.json").write_text(json.dumps([
        {"id": shot["id"], "start": shot["start"], "end": shot["start"] + shot["duration"],
         "duration": shot["duration"], "kind": "agnes", "narration_id": shot["narration_id"],
         "style_variant": shot["style_variant"], "transition_in": transition_plan(story).get(shot["id"]),
         "narration": shot["narration"]}
        for shot in story["shots"]
    ], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (delivery / "narration-timing.json").write_text(json.dumps(audio_report["narration"], ensure_ascii=False, indent=2) + "\n",
                                                             encoding="utf-8")
    (delivery / "caption-timing.json").write_text(json.dumps(cues, ensure_ascii=False, indent=2) + "\n",
                                                          encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
