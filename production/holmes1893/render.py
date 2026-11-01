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
from production.holmes1893.build_audio import build_soundtrack  # noqa: E402
from production.holmes1893.generate import MODEL, SOURCE_SIZE, digest, request_hash  # noqa: E402

FPS = 24
DURATION = 180
TOTAL_FRAMES = FPS * DURATION
PAD = 0.40  # clone tail so every xfade has room without shifting a single cut time

# Print-panel shots sometimes come back with embedded mattes; only verified paired bands are cropped.
LETTERBOX_CHECK_SHOTS = {"S09", "S12", "S13"}
CARD_TEXT_MAX_WIDTH = 1660
END_CARD_AT = 174.55


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
    parts = ([correction] if correction else []) + [
        "scale=1920:1080:force_original_aspect_ratio=increase",
        "crop=1920:1080",
        "setsar=1",
        f"eq=gamma={shadow_lift_gamma(luma):.3f}:brightness=0.014",
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
        # \\p1 的绘图坐标按字号缩放：字号 100 时 1 单位 = 1 像素，片尾底板因此能精确铺满画面。
        "Style: Plate,Noto Sans CJK SC,100,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
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
    # 片尾底板：一层半透明墨色，让金色片名压在亮画面上也读得清（第 0 层，字幕与片名都在它之上）。
    plate_start = ass_time(END_CARD_AT - 0.30)
    lines += [
        # 一层均匀的墨色底：整块盖住画面，避免出现任何硬边色带；金色片名与白字幕都压在它上面。
        f"Dialogue: 0,{plate_start},{ass_time(179.90)},Plate,,0,0,0,,"
        f"{{\\an7\\pos(0,0)\\p1\\bord0\\shad0\\1c&H0C0805&\\1a&H78&\\fad(800,0)}}"
        f"m 0 0 l 1920 0 l 1920 1080 l 0 1080",
    ]
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


def fill_crop(image: Image.Image, width: int, height: int, x_bias: float = 0.5) -> Image.Image:
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((max(width, round(image.width * ratio)),
                            max(height, round(image.height * ratio))), Image.Resampling.LANCZOS)
    left = int((resized.width - width) * x_bias)
    top = int((resized.height - height) * 0.5)
    return resized.crop((left, top, left + width, top + height))


def tear_path(width: int, height: int, seed: int = 1893) -> list[tuple[float, float]]:
    """A jagged paper-tear line down the centre of the cover, leaning slightly."""
    rng = np.random.default_rng(seed)
    points = []
    x = width * 0.5
    for y in range(-20, height + 40, 22):
        x += float(rng.normal(0, 13))
        x = min(max(x, width * 0.42), width * 0.58)
        points.append((x + (y / height - 0.5) * 90, y))
    return points


def make_cover(sources: Path, output: Path, story: dict, work_dir: Path) -> None:
    """Left: the black building with one guttering window. Right: the lit White City."""
    left_frame = grab_frame(sources / "S02.mp4", 3.2, work_dir, "castle")
    right_frame = grab_frame(sources / "S01.mp4", 1.8, work_dir, "whitecity")
    compose_cover(left_frame, right_frame, output, story)


def compose_cover(left_frame: Image.Image, right_frame: Image.Image, output: Path,
                  story: dict) -> None:
    """Compose the '传说 vs 真相' cover from any two images (footage frames or references).

    A white torn seam runs down the middle; '传说' sits over the dark half and '真相' over the
    bright half. In the finished film both panels are frames of verified Agnes clips.
    """
    width, height = 1920, 1080
    # Both panels are full-frame crops: the tear decides which half a viewer actually sees, so
    # there is no seam to hide and each side keeps the whole 1920-pixel width for its subject.
    left = fill_crop(left_frame, width, height, 0.36)
    right = fill_crop(right_frame, width, height, 0.62)
    image = Image.new("RGB", (width, height))

    # Soften the seam, then cut the tear through it.
    torn = tear_path(width, height)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (torn[0][0], 0), *torn, (torn[-1][0], height), (0, height)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    base = Image.new("RGB", (width, height))
    base.paste(right, (0, 0))
    base.paste(left, (0, 0), mask)
    image = base

    rgba = image.convert("RGBA")
    # Warm the left (legend) half, cool the right (fact) half.
    wash = np.zeros((height, width, 4), dtype=np.uint8)
    xx = np.arange(width)[None, :]
    legend_side = (xx <= width * 0.5)
    warm = np.clip((width * 0.52 - xx) / (width * 0.52), 0, 1)
    cool = np.clip((xx - width * 0.48) / (width * 0.52), 0, 1)
    wash[:, :, 3] = np.clip(warm * 46 + cool * 26, 0, 60).repeat(height, axis=0).astype(np.uint8)
    wash[:, :, 0] = np.where(legend_side, 60, 4).repeat(height, axis=0).astype(np.uint8)
    wash[:, :, 1] = np.where(legend_side, 32, 10).repeat(height, axis=0).astype(np.uint8)
    wash[:, :, 2] = np.where(legend_side, 6, 26).repeat(height, axis=0).astype(np.uint8)
    image = Image.alpha_composite(rgba, Image.fromarray(wash, "RGBA"))

    # Bottom gradient for the title block.
    gradient = np.zeros((height, width, 4), dtype=np.uint8)
    for y in range(height):
        strength = int(228 * max(0.0, (y - height * 0.50) / (height * 0.50)) ** 1.15)
        gradient[y, :, :] = (3, 5, 8, strength)
    image = Image.alpha_composite(image, Image.fromarray(gradient, "RGBA"))

    draw = ImageDraw.Draw(image)

    # The tear itself: hot white core with a soft glow, then splinters.
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(glow).line(torn, fill=(255, 248, 226, 200), width=16, joint="curve")
    image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(26)))
    image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(9)))
    draw = ImageDraw.Draw(image)
    draw.line(torn, fill=(255, 252, 240, 255), width=4, joint="curve")
    rng = np.random.default_rng(77)
    for point in torn[::3]:
        for _ in range(2):
            dx, dy = rng.normal(0, 40), rng.normal(0, 46)
            draw.line([point, (point[0] + dx, point[1] + dy)], fill=(255, 250, 236, 150), width=2)

    serif = find_font(True)
    sans = find_font()
    legend_font = ImageFont.truetype(str(serif), 168)
    vs_font = ImageFont.truetype(str(serif), 92)
    title_font_size = fit_size(draw, story["presentation"]["cover"]["text"], 150, 980, serif=True)
    title_font = ImageFont.truetype(str(serif), title_font_size)
    sub_font = ImageFont.truetype(str(sans), 44)
    micro_font = ImageFont.truetype(str(sans), 27)
    kicker_font = ImageFont.truetype(str(sans), 32)

    def centered(text: str, font, centre_x: int, y: int, fill: str, stroke: int, stroke_fill: str):
        box = draw.textbbox((0, 0), text, font=font)
        w = box[2] - box[0]
        draw.text((centre_x - w / 2 - box[0], y - box[1]), text, font=font, fill=fill,
                  stroke_width=stroke, stroke_fill=stroke_fill)

    kicker = "真实案件 · 动画情景复原"
    kicker_box = draw.textbbox((0, 0), kicker, font=kicker_font)
    draw.text((72, 52 - kicker_box[1]), kicker, font=kicker_font, fill="#e8e2d2",
              stroke_width=2, stroke_fill="#0b0c0a")
    draw.text((width - 300, 52 - kicker_box[1]), "第二期", font=kicker_font, fill="#f4c95f",
              stroke_width=2, stroke_fill="#0b0c0a")

    centered("传说", legend_font, int(width * 0.245), 150, "#e6c58a", 10, "#120f08")
    centered("vs", vs_font, int(width * 0.5), 268, "#fffaf0", 7, "#0d0c0a")
    centered("真相", legend_font, int(width * 0.755), 150, "#f4c95f", 10, "#120f08")

    title_text = story["presentation"]["cover"]["text"]
    centered(title_text, title_font, width // 2, 742, "#f4c95f", 8, "#100e07")
    subtext = story["presentation"]["cover"]["subtext"]
    centered(subtext, sub_font, width // 2, 742 + title_font_size + 36, "#f3efe5", 3, "#0c0d0a")
    draw.text((72, height - 74), "AI动画情景复原 · 非真实影像", font=micro_font, fill="#a7a49c",
              stroke_width=2, stroke_fill="#0b0c09")
    tag = "1893 芝加哥世博会 · 英格尔伍德"
    tag_box = draw.textbbox((0, 0), tag, font=micro_font)
    draw.text((width - (tag_box[2] - tag_box[0]) - 72, height - 74), tag, font=micro_font,
              fill="#a7a49c", stroke_width=2, stroke_fill="#0b0c09")

    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, quality=95, subsampling=0)
    image.convert("RGB").save(output.with_suffix(".png"))


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
    ass_filter = f"ass={ass_path.as_posix()}" + (f":fontsdir={font_dir.as_posix()}" if font_dir.is_dir() else "")
    final = args.output
    final.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", picture, "-i", mix,
        "-vf", ass_filter, "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-maxrate", "3200k", "-bufsize", "6400k", "-profile:v", "high", "-level", "4.1",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", str(DURATION), "-movflags", "+faststart", final,
    ])
    summary = media_summary(final)
    if summary["width"] != 1920 or summary["height"] != 1080 or abs(summary["duration_seconds"] - 180.0) > 0.04:
        raise RuntimeError("Final video failed format/duration gate: " + json.dumps(summary, ensure_ascii=False))
    if summary.get("sample_rate") != 48000 or summary.get("audio_channels") != 2:
        raise RuntimeError("Final audio stream must be 48kHz stereo")
    if summary["frames"] not in (0, TOTAL_FRAMES):
        raise RuntimeError(f"Expected {TOTAL_FRAMES} frames, got {summary['frames']}")

    cover = final.parent / "H·H·霍姆斯_封面.jpg"
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
