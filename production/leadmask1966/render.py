#!/usr/bin/env python3
"""Deterministic 180-second edit from verified Agnes motion clips and selected Chinese VO."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from production.leadmask1966.build_audio import build_soundtrack  # noqa: E402
from production.leadmask1966.generate import MODEL, SOURCE_SIZE, digest, request_hash  # noqa: E402

FPS = 30
DURATION = 180
TOTAL_FRAMES = FPS * DURATION

# Hand-drawn rumor illustrations are the only shots that sometimes come back letterboxed.
LETTERBOX_CHECK_SHOTS = {"S20", "S22", "S23", "S24", "S25"}
CARD_TEXT_MAX_WIDTH = 1660
FADE_IN_SKIP = set()



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


def chapter_boundaries(story: dict) -> tuple[set[str], set[str]]:
    first, last = set(), set()
    grouped = {}
    for shot in story["shots"]:
        grouped.setdefault(shot["narration_id"], []).append(shot)
    for shots in grouped.values():
        first.add(shots[0]["id"])
        last.add(shots[-1]["id"])
    return first, last


def chapter_fade_filters(shot: dict, first_ids: set[str], last_ids: set[str]) -> list[str]:
    """Return chapter-boundary fades, except where a shot must start on its required scene."""
    shot_id = shot["id"]
    start = float(shot["start"])
    duration = float(shot["duration"])
    filters = []
    if shot_id in first_ids and start > 0 and shot_id not in FADE_IN_SKIP:
        filters.append("fade=t=in:st=0:d=0.30")
    if shot_id in last_ids and start + duration < DURATION:
        filters.append(f"fade=t=out:st={max(0.0, duration-0.30):.3f}:d=0.30")
    return filters


def detect_matte_bands(image: Image.Image) -> tuple[int, int] | None:
    """Detect paired, nearly black borders with a sharp boundary in a low-resolution frame."""
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    height, _width = gray.shape
    max_scan = max(2, int(height * 0.30))

    def edge_run(reverse: bool) -> int:
        run = 0
        for offset in range(max_scan):
            y = height - 1 - offset if reverse else offset
            row = gray[y, :].astype(np.float32)
            if float(np.mean(row)) < 10.0 and float(np.std(row)) < 4.0 and float(np.mean(row < 20)) > 0.995:
                run += 1
            else:
                break
        return run

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
    """Sample rumor shots at three times; only crop when paired hard mattes persist."""
    if shot.get("id") not in LETTERBOX_CHECK_SHOTS:
        return []
    duration = float(info["duration_seconds"])
    sample_bands = []
    for index, fraction in enumerate((0.15, 0.50, 0.85)):
        timestamp = min(max(0.05, duration * fraction), max(0.05, duration - 0.05))
        sample_path = source.parent / f".{source.stem}-letterbox-check-{index}.png"
        try:
            run([
                "ffmpeg", "-y", "-v", "error", "-ss", f"{timestamp:.3f}", "-i", source,
                "-frames:v", "1", "-vf", "scale=640:360", sample_path,
            ])
            with Image.open(sample_path) as image:
                bands = detect_matte_bands(image)
            if bands:
                sample_bands.append(bands)
        finally:
            sample_path.unlink(missing_ok=True)
    return sample_bands if len(sample_bands) >= 2 else []


def letterbox_crop_filter(shot: dict, info: dict, detected_bands: list[tuple[int, int]] | None = None) -> str | None:
    """Crop only verified embedded mattes; regenerated full-frame footage stays untouched."""
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


def normalize_clip(source: Path, target: Path, shot: dict, first_ids: set[str], last_ids: set[str]) -> dict:
    duration = float(shot["duration"])
    target_frames = round(duration * FPS)
    info = media_summary(source)
    if not 3.75 <= info["duration_seconds"] <= 9.5:
        raise RuntimeError(f"{shot['id']}: invalid Agnes clip duration {info['duration_seconds']:.3f}s")
    if info["width"] < 640 or info["height"] < 360:
        raise RuntimeError(f"{shot['id']}: returned video resolution is too small")
    detected_bands = detect_source_letterbox_bands(source, shot, info)
    correction = letterbox_crop_filter(shot, info, detected_bands)
    filters = ([correction] if correction else []) + [
        "scale=1920:1080:force_original_aspect_ratio=increase",
        "crop=1920:1080",
        "fps=30",
        "setsar=1",
        "eq=gamma=1.10:brightness=0.008",
    ]
    filters.extend(chapter_fade_filters(shot, first_ids, last_ids))
    filters.append("format=yuv420p")
    target.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", source,
        "-map", "0:v:0", "-vf", ",".join(filters), "-an", "-t", f"{duration:.3f}",
        "-frames:v", str(target_frames), "-r", str(FPS), "-fps_mode", "cfr",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", target,
    ])
    return {"id": shot["id"], "duration_seconds": duration, "frames": target_frames,
            "source_duration_seconds": round(info["duration_seconds"], 3),
            "source_width": info["width"], "source_height": info["height"],
            "source_sha256": digest(source), "normalized_file": str(target),
            "embedded_letterbox_crop_filter": correction,
            "embedded_letterbox_detected_samples": len(detected_bands)}


def ass_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def escape_ass(text: str) -> str:
    return text.replace("\\", "/").replace("{", "（").replace("}", "）").replace("\n", " ")


def highlight_text(text: str, phrases: list[str]) -> str:
    text = escape_ass(text)
    out = []
    i = 0
    ordered = sorted(phrases, key=len, reverse=True)
    while i < len(text):
        hit = next((phrase for phrase in ordered if text.startswith(phrase, i)), None)
        if hit:
            out.append(r"{\c&H004DD4FF&\fs70\b1}" + hit + r"{\rCaption}")
            i += len(hit)
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def write_subtitles(path: Path, cues: list[dict], story: dict, srt_path: Path) -> None:
    phrases = story["presentation"]["highlight_keywords"]
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
        "Style: Caption,Noto Sans CJK SC,58,&H00FFFFFF,&H0000FFFF,&H00111110,&H99000000,1,0,0,0,100,100,0,0,1,3.2,1.0,2,115,115,72,1",
        "Style: Title,Noto Serif CJK SC,112,&H00F2CF72,&H0000FFFF,&H0013110D,&H99000000,1,0,0,0,100,100,1,0,1,5,2,5,80,80,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for cue in cues:
        line = highlight_text(cue["text"], phrases)
        lines.append(
            f"Dialogue: 1,{ass_time(cue['start'])},{ass_time(cue['end'])},Caption,,0,0,0,,{{\\q2\\fad(70,80)}}{line}"
        )

    # Only the closing title is a post-produced overlay; the Agnes model itself is never asked
    # to render legible text anywhere in the film (S29 is the single shot that carries a title).
    lines += [
        f"Dialogue: 2,{ass_time(175.90)},{ass_time(179.60)},Title,,0,0,0,,{{\\pos(960,392)\\fad(420,430)\\fs104}}铅面具事件",
        f"Dialogue: 2,{ass_time(176.10)},{ass_time(179.60)},Caption,,0,0,0,,{{\\pos(960,560)\\fad(460,430)\\fs42}}巴西 · 1966 · 至今未解",
        f"Dialogue: 2,{ass_time(176.30)},{ass_time(179.60)},Caption,,0,0,0,,{{\\pos(960,640)\\fad(500,430)\\fs34}}AI动画情景重现 · 非历史影像",
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
        rows.append(f"{i}\n{srt_clock(cue['start'])} --> {srt_clock(cue['end'])}\n{cue['text']}\n")
    srt_path.write_text("\n".join(rows), encoding="utf-8")


def find_font(serif: bool = False) -> Path:
    candidates = []
    font_root = Path("/usr/share/fonts")
    if font_root.exists():
        for pattern in ("**/NotoSerifCJK-Regular.ttc", "**/NotoSansCJK-Regular.ttc", "**/*CJK*" ) if serif else ("**/NotoSansCJK-Regular.ttc", "**/*CJK*"):
            candidates.extend(font_root.glob(pattern))
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
    """Shrink a line until it fits, but never below the legibility floor."""
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
    """Scale to cover the target box, then crop around a horizontal bias (0=left, 1=right)."""
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((max(width, round(image.width * ratio)),
                            max(height, round(image.height * ratio))), Image.Resampling.LANCZOS)
    left = int((resized.width - width) * x_bias)
    top = int((resized.height - height) * 0.5)
    return resized.crop((left, top, left + width, top + height))


def make_cover(sources: Path, output: Path, story: dict, work_dir: Path) -> None:
    """Left: the lead eye-mask macro. Right: the red-orange light over the hill at night."""
    width, height = 1920, 1080
    background = fill_crop(grab_frame(sources / "S01.mp4", 2.2, work_dir, "hill"), width, height, 0.62)
    mask = fill_crop(grab_frame(sources / "S13.mp4", 1.3, work_dir, "mask"), 1180, height, 0.5)
    panel = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    panel.paste(mask, (0, 0))
    alpha = np.zeros((height, width), dtype=np.uint8)
    for x in range(width):
        if x < 900:
            fade = 255
        elif x < 1250:
            fade = int(255 * (1.0 - (x - 900) / 350.0) ** 1.35)
        else:
            fade = 0
        alpha[:, x] = fade
    panel.putalpha(Image.fromarray(alpha, "L"))
    image = Image.alpha_composite(background.convert("RGBA"), panel)

    # Darken the left side so the gold title reads on a phone screen.
    shade = np.zeros((height, width, 4), dtype=np.uint8)
    for x in range(width):
        strength = int(184 * max(0.0, 1.0 - x / 1180.0) ** 1.45)
        shade[:, x, :] = (3, 7, 10, strength)
    image = Image.alpha_composite(image, Image.fromarray(shade, "RGBA"))

    draw = ImageDraw.Draw(image)
    serif = True
    title_size = fit_size(draw, story["presentation"]["cover"]["text"], 172, 760, serif=True)
    title_font = ImageFont.truetype(str(find_font(serif)), title_size)
    small = ImageFont.truetype(str(find_font()), 36)
    sub = ImageFont.truetype(str(find_font()), 40)
    micro = ImageFont.truetype(str(find_font()), 30)
    draw.text((112, 214), "1966 · 巴西 · 尼泰罗伊", font=small, fill="#d8c08a",
              stroke_width=2, stroke_fill="#0d0f0c")
    draw.text((104, 300), story["presentation"]["cover"]["text"], font=title_font, fill="#f4c95f",
              stroke_width=9, stroke_fill="#111008")
    draw.text((112, 520), "两个人戴着铅面具，死在山头", font=sub, fill="#f2eee4",
              stroke_width=3, stroke_fill="#0e0f0c")
    draw.text((112, 580), story["presentation"]["cover"]["subtext"], font=micro, fill="#cfc7b4",
              stroke_width=2, stroke_fill="#0e0f0c")
    draw.text((112, 930), "AI动画情景重现 · 非历史影像", font=micro, fill="#9c9a94",
              stroke_width=2, stroke_fill="#0e0f0c")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output, quality=95, subsampling=0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    rows = verify_sources(story, args.sources)
    args.work.mkdir(parents=True, exist_ok=True)
    normalized = args.work / "normalized"
    normalized.mkdir(parents=True, exist_ok=True)
    first_ids, last_ids = chapter_boundaries(story)
    clip_report = []
    concat_list = args.work / "clips.ffconcat"
    lines = ["ffconcat version 1.0"]
    for shot in story["shots"]:
        source = args.sources / f"{shot['id']}.mp4"
        target = normalized / f"{shot['id']}.mp4"
        clip_report.append(normalize_clip(source, target, shot, first_ids, last_ids))
        escaped = str(target.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    silent_video = args.work / "leadmask-picture-only.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-r", str(FPS),
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", str(DURATION), silent_video])

    mix, audio_report, cues = build_soundtrack(story, HERE / "audio", args.work)
    audio_report_path = args.work / "audio" / "mix-report.json"
    if not audio_report_path.is_file():
        raise RuntimeError("Measured audio report was not written")
    ass_path = args.work / "leadmask-captions.ass"
    srt_path = args.work / "铅面具事件_字幕.srt"
    write_subtitles(ass_path, cues, story, srt_path)
    # Fontconfig resolves the installed Noto CJK family name on GitHub-hosted Ubuntu.
    final = args.output
    final.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", silent_video, "-i", mix,
        "-vf", f"ass={ass_path.as_posix()}", "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", str(DURATION), "-movflags", "+faststart", final,
    ])
    summary = media_summary(final)
    if summary["width"] != 1920 or summary["height"] != 1080 or abs(summary["duration_seconds"] - 180.0) > 0.04:
        raise RuntimeError("Final video failed format/duration gate: " + json.dumps(summary, ensure_ascii=False))
    if summary.get("sample_rate") != 48000 or summary.get("audio_channels") != 2:
        raise RuntimeError("Final audio stream must be 48kHz stereo")
    if summary["frames"] not in (0, TOTAL_FRAMES):
        raise RuntimeError(f"Expected 5400 frames, got {summary['frames']}")

    cover = final.parent / "铅面具事件_封面.jpg"
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
        "soundtrack": audio_report,
        "caption_cues": len(cues),
        "captions_ass": str(ass_path),
        "captions_srt": str(srt_path),
        "cover": str(cover),
        "source_model": MODEL,
        "source_resolution": SOURCE_SIZE,
        "final_resolution": "1920x1080 (upscaled in post)",
        "all_29_generated_shots_verified_by_sha256": True,
        "note": "Generated footage and the composited title/captions are an AI-produced reenactment, "
                "not historical footage. Rumor scenes are hand-drawn illustrations, not claims of fact.",
    }
    delivery = args.work / "delivery"
    delivery.mkdir(parents=True, exist_ok=True)
    (delivery / "technical-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                      encoding="utf-8")
    (delivery / "edit-decision-list.json").write_text(json.dumps([
        {"id": shot["id"], "start": shot["start"], "end": shot["start"] + shot["duration"],
         "duration": shot["duration"], "kind": "agnes", "narration_id": shot["narration_id"],
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
