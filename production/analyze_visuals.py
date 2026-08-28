#!/usr/bin/env python3
"""Build a visual review package from every detected shot in source/reference videos."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

import cv2
import numpy as np

SUBTITLE_URL = "https://subtitlecat.com/subs/1018/The%20Divine%20Fury%20(2019)-English-zh-CN.srt"
COLS = 8
ROWS = 6
THUMB_W = 240
THUMB_H = 135
LABEL_H = 22


def parse_scenes(path: Path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header = next(index for index, line in enumerate(lines) if line.startswith("Scene Number,"))
    return [
        {
            "scene": int(row["Scene Number"]),
            "start": float(row["Start Time (seconds)"]),
            "end": float(row["End Time (seconds)"]),
        }
        for row in csv.DictReader(lines[header:])
    ]


def timecode(seconds: float) -> str:
    hours = int(seconds // 3600)
    seconds -= hours * 3600
    minutes = int(seconds // 60)
    seconds -= minutes * 60
    return f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"


def make_tile(frame, item):
    resized = cv2.resize(frame, (THUMB_W, THUMB_H), interpolation=cv2.INTER_AREA)
    tile = np.zeros((THUMB_H + LABEL_H, THUMB_W, 3), dtype=np.uint8)
    tile[:THUMB_H] = resized
    label = f"S{item['scene']:04d}  {timecode((item['start'] + item['end']) / 2)}"
    cv2.putText(
        tile,
        label,
        (5, THUMB_H + 16),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.43,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return tile


def save_sheet(tiles, output: Path):
    canvas = np.zeros((ROWS * (THUMB_H + LABEL_H), COLS * THUMB_W, 3), dtype=np.uint8)
    for index, tile in enumerate(tiles):
        row, column = divmod(index, COLS)
        y = row * (THUMB_H + LABEL_H)
        x = column * THUMB_W
        canvas[y : y + tile.shape[0], x : x + tile.shape[1]] = tile
    cv2.imwrite(str(output), canvas, [cv2.IMWRITE_JPEG_QUALITY, 88])


def build_contact_sheets(video: Path, scenes, output_dir: Path, prefix: str):
    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video))
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not fps:
        raise RuntimeError(f"Could not read FPS from {video}")
    targets = []
    for item in scenes:
        midpoint = (item["start"] + item["end"]) / 2
        targets.append((max(0, int(round(midpoint * fps))), item))
    target_index = 0
    frame_index = 0
    tiles = []
    sheet_index = 1
    while target_index < len(targets):
        ok, frame = capture.read()
        if not ok:
            break
        target_frame, item = targets[target_index]
        if frame_index >= target_frame:
            tiles.append(make_tile(frame, item))
            target_index += 1
            if len(tiles) == COLS * ROWS:
                save_sheet(tiles, output_dir / f"{prefix}_{sheet_index:02d}.jpg")
                print(f"{prefix}: saved sheet {sheet_index}", flush=True)
                tiles = []
                sheet_index += 1
        frame_index += 1
    capture.release()
    if tiles:
        save_sheet(tiles, output_dir / f"{prefix}_{sheet_index:02d}.jpg")
    if target_index < len(targets):
        raise RuntimeError(f"Only extracted {target_index}/{len(targets)} scene keyframes from {video}")
    return sheet_index


def detect_reference(reference: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "scenedetect",
            "-q",
            "-i",
            str(reference),
            "-o",
            str(output_dir),
            "detect-content",
            "-t",
            "27",
            "list-scenes",
            "-f",
            "reference-scenes.csv",
        ],
        check=True,
    )
    return output_dir / "reference-scenes.csv"


def make_title_card(path: Path, title: str, subtitle: str):
    height = ROWS * (THUMB_H + LABEL_H)
    width = COLS * THUMB_W
    image = np.zeros((height, width, 3), dtype=np.uint8)
    title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.8, 3)[0]
    subtitle_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)[0]
    cv2.putText(
        image,
        title,
        ((width - title_size[0]) // 2, height // 2 - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.8,
        (255, 255, 255),
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        subtitle,
        ((width - subtitle_size[0]) // 2, height // 2 + 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (180, 190, 210),
        2,
        cv2.LINE_AA,
    )
    cv2.imwrite(str(path), image, [cv2.IMWRITE_JPEG_QUALITY, 92])


def render_review_video(package: Path, source_dir: Path, reference_dir: Path, output: Path):
    source_title = package / "source-title.jpg"
    reference_title = package / "reference-title.jpg"
    make_title_card(source_title, "SOURCE MOVIE - ALL DETECTED SHOTS", "Each tile: scene number and original timecode")
    make_title_card(reference_title, "DOUYIN REFERENCE - ALL DETECTED SHOTS", "Used only as editing and matching reference")

    sequence = [(source_title, 3.0)]
    sequence.extend((path, 4.0) for path in sorted(source_dir.glob("source_*.jpg")))
    if list(reference_dir.glob("reference_*.jpg")):
        sequence.append((reference_title, 3.0))
        sequence.extend((path, 4.0) for path in sorted(reference_dir.glob("reference_*.jpg")))

    concat_file = package / "review-video.txt"
    rows = []
    for path, duration in sequence:
        escaped = path.resolve().as_posix().replace("'", "'\\''")
        rows.extend([f"file '{escaped}'", f"duration {duration:.3f}"])
    escaped_last = sequence[-1][0].resolve().as_posix().replace("'", "'\\''")
    rows.append(f"file '{escaped_last}'")
    concat_file.write_text("\n".join(rows) + "\n", encoding="utf-8")

    total_duration = sum(duration for _, duration in sequence)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:black,format=yuv420p",
            "-r",
            "25",
            "-c:v",
            "libx264",
            "-profile:v",
            "baseline",
            "-level",
            "3.1",
            "-tag:v",
            "avc1",
            "-x264-params",
            "bframes=0:keyint=50:min-keyint=50:scenecut=0",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-c:a",
            "aac",
            "-profile:a",
            "aac_low",
            "-b:a",
            "64k",
            "-ar",
            "44100",
            "-t",
            f"{total_duration:.3f}",
            "-video_track_timescale",
            "90000",
            "-movflags",
            "+faststart",
            str(output),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-xerror",
            "-i",
            str(output),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ],
        check=True,
    )
    probe = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name,duration,size:stream=codec_name,profile,codec_tag_string,width,height,pix_fmt,r_frame_rate,sample_rate",
            "-of",
            "json",
            str(output),
        ],
        text=True,
    )
    metadata = json.loads(probe)
    streams = metadata.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_name") == "h264"), None)
    audio = next((stream for stream in streams if stream.get("codec_name") == "aac"), None)
    if not video or not audio:
        raise RuntimeError(f"Compatibility validation failed: {metadata}")
    if video.get("codec_tag_string") != "avc1" or video.get("pix_fmt") != "yuv420p":
        raise RuntimeError(f"Unexpected video compatibility metadata: {video}")
    with output.open("rb") as handle:
        payload = handle.read()
    for atom in (b"ftyp", b"moov", b"mdat"):
        if atom not in payload:
            raise RuntimeError(f"Required MP4 atom is missing: {atom.decode()}")
    checksum = hashlib.sha256(payload).hexdigest()
    print(f"WINDOWS-COMPATIBLE REVIEW MP4 VERIFIED: {probe}", flush=True)
    print(f"SHA256: {checksum}", flush=True)

    # Publish a raw MP4 URL as a fallback so the user does not need to unpack
    # GitHub's artifact ZIP before testing playback.
    try:
        upload = subprocess.run(
            [
                "curl",
                "-fsS",
                "--retry",
                "2",
                "-F",
                "reqtype=fileupload",
                "-F",
                f"fileToUpload=@{output}",
                "https://catbox.moe/user/api.php",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        direct_url = upload.stdout.strip()
        if direct_url.startswith("https://"):
            print(f"::notice title=Direct validated MP4::{direct_url}", flush=True)
    except Exception as exc:
        print(f"::warning title=Direct upload unavailable::{exc}", flush=True)


def create_visual_package(source: Path, source_scenes: Path, work: Path, output: Path):
    package = work / "visual-review"
    if package.exists():
        shutil.rmtree(package)
    source_dir = package / "source-keyframes"
    reference_dir = package / "reference-keyframes"
    package.mkdir(parents=True)

    source_items = parse_scenes(source_scenes)
    source_sheet_count = build_contact_sheets(source, source_items, source_dir, "source")
    shutil.copy2(source_scenes, package / "source-scenes.csv")

    reference = source.parent / "reference.mp4"
    reference_items = []
    reference_sheet_count = 0
    if reference.exists():
        reference_scene_file = detect_reference(reference, package / "reference-scan")
        reference_items = parse_scenes(reference_scene_file)
        reference_sheet_count = build_contact_sheets(
            reference, reference_items, reference_dir, "reference"
        )
        shutil.copy2(reference_scene_file, package / "reference-scenes.csv")

    try:
        request = urllib.request.Request(SUBTITLE_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            (package / "source-dialogue-zh-CN.srt").write_bytes(response.read())
    except Exception as exc:
        (package / "subtitle-download-error.txt").write_text(str(exc), encoding="utf-8")

    manifest = {
        "mode": "visual-review-only",
        "source_scene_count": len(source_items),
        "source_sheet_count": source_sheet_count,
        "reference_scene_count": len(reference_items),
        "reference_sheet_count": reference_sheet_count,
        "contact_sheet_layout": f"{COLS} columns x {ROWS} rows",
        "instruction": "Each tile is the midpoint frame of one real detected shot. Labels show scene number and original timecode.",
    }
    (package / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (package / "README.txt").write_text(
        "这是视觉识别包，不是最终视频。\n"
        "source-keyframes 包含原片每个真实镜头的中点画面。\n"
        "reference-keyframes 包含参考解说视频的镜头中点画面。\n"
        "每张缩略图下方标注原片镜头编号和时间码。\n",
        encoding="utf-8",
    )

    render_review_video(package, source_dir, reference_dir, output)
    print(
        f"VISUAL REVIEW VIDEO: {output} / {output.stat().st_size/1048576:.1f}MB / "
        f"{len(source_items)} source shots / {len(reference_items)} reference shots",
        flush=True,
    )
