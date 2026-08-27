#!/usr/bin/env python3
"""Build a visual review package from every detected shot in source/reference videos."""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import urllib.request
import zipfile
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

    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(package))
    print(
        f"VISUAL REVIEW PACKAGE: {output} / {output.stat().st_size/1048576:.1f}MB / "
        f"{len(source_items)} source shots / {len(reference_items)} reference shots",
        flush=True,
    )
