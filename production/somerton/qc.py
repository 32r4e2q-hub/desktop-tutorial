#!/usr/bin/env python3
"""Automated post-render QC for a downloaded Somerton Actions artifact.

This checks delivery streams, full decode, source receipts, EDL/story mapping,
narration/subtitle timing and audio levels. Motion and semantic visual review remain
human tasks; a labeled midpoint sheet is emitted for that pass.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageStat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from production.somerton.generate import request_hash  # noqa: E402

FPS = 30
DURATION = 180.0
EXPECTED_SHOTS = 29


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_file(root: Path, relative: str | None = None, basename: str | None = None) -> Path | None:
    if relative:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    wanted = basename or (Path(relative).name if relative else None)
    if not wanted:
        return None
    candidates = [path for path in root.rglob(wanted) if path.is_file()]
    if not candidates:
        return None
    # Prefer the files from the named uploaded artifact paths over duplicated report copies.
    preferred = [p for p in candidates if "work/somerton/clips" in p.as_posix()]
    return sorted(preferred or candidates)[0]


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)
    ], text=True))


def rate(value: str | None) -> float | None:
    if not value:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None


def clock(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def parse_srt(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig").strip()
    cues = []
    for block in re.split(r"\r?\n\s*\r?\n", text):
        lines = block.splitlines()
        timing = next((line for line in lines if "-->" in line), None)
        if timing is None:
            continue
        left, right = [part.strip() for part in timing.split("-->", 1)]
        timing_index = lines.index(timing)
        cues.append({"start": clock(left), "end": clock(right),
                     "text": "\n".join(lines[timing_index + 1:]).strip()})
    return cues


def visible_weight(text: str) -> int:
    return max(1, len(re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", text)))


def clauses(text: str) -> list[str]:
    return [piece.strip() for piece in re.findall(r"[^，。！？；：、]+[，。！？；：、]?", text) if piece.strip()]


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


def add_check(report: dict, name: str, passed: bool, detail: str, severity: str = "error") -> None:
    status = "pass" if passed else ("warn" if severity == "warning" else "fail")
    report["checks"].append({"name": name, "status": status, "detail": detail})
    if not passed and severity == "error":
        report["failures"].append(name)
    elif not passed:
        report["warnings"].append(name)


def draw_midpoint_sheet(video: Path, story: dict, output: Path, sample_dir: Path) -> list[dict]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    samples = []
    for shot in story["shots"]:
        sample_time = float(shot["start"]) + float(shot["duration"]) / 2.0
        frame = sample_dir / f"{shot['id']}.jpg"
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{sample_time:.3f}",
            "-i", str(video), "-map", "0:v:0", "-frames:v", "1", "-vf", "scale=1920:1080",
            "-q:v", "3", str(frame),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        image = Image.open(frame).convert("RGB")
        stat = ImageStat.Stat(image.convert("L"))
        gray = np.asarray(image.convert("L"))
        samples.append({
            "id": shot["id"], "time_seconds": round(sample_time, 3),
            "narration_id": shot["narration_id"], "frame": str(frame),
            "mean_luma": round(stat.mean[0], 2), "luma_stddev": round(stat.stddev[0], 2),
            "near_black_fraction": round(float(np.mean(gray < 12)), 4),
        })

    cols, cell_w, cell_h, header = 4, 390, 238, 27
    rows = math.ceil(len(samples) / cols)
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (17, 22, 28))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    by_id = {shot["id"]: shot for shot in story["shots"]}
    for index, row in enumerate(samples):
        shot = by_id[row["id"]]
        x, y = (index % cols) * cell_w + 10, (index // cols) * cell_h
        end = float(shot["start"]) + float(shot["duration"])
        draw.text((x, y + 5), f"{row['id']} | {shot['start']}-{end:g}s | {row['narration_id']}",
                  font=font, fill=(255, 222, 145))
        frame = Image.open(row["frame"]).convert("RGB")
        frame.thumbnail((360, 203), Image.Resampling.LANCZOS)
        sheet.paste(frame, (x, y + header))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=90)
    return samples


def motion_sample_times(shot: dict, count: int = 9) -> list[float]:
    """Return evenly spaced sample times across a shot, including its first frame."""
    start = float(shot["start"])
    duration = float(shot["duration"])
    if count <= 0 or duration <= 0:
        raise ValueError("motion sample count and shot duration must be positive")
    return [round(start + duration * index / count, 3) for index in range(count)]


def motion_sample_frame_positions(shot: dict, count: int = 9) -> list[tuple[int, float]]:
    """Map intended sample instants to nearest exact 30 fps frame indices and timestamps."""
    positions = []
    for sample_time in motion_sample_times(shot, count):
        frame_index = int(math.floor(sample_time * FPS + 0.5))
        positions.append((frame_index, round(frame_index / FPS, 3)))
    return positions


def assemble_final_motion_sheet(shot_id: str, sample_times: list[float],
                                frame_paths: list[Path], output: Path) -> None:
    """Create a labeled 3x3 contact sheet from final-cut frames of one shot."""
    if len(sample_times) != 9 or len(frame_paths) != 9:
        raise ValueError("exactly nine sample times and frames are required for a 3x3 sheet")
    cell_w, cell_h, label_h = 426, 240, 27
    sheet = Image.new("RGB", (cell_w * 3, (cell_h + label_h) * 3), (17, 22, 28))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    for index, (sample_time, frame_path) in enumerate(zip(sample_times, frame_paths)):
        col, row = index % 3, index // 3
        x, y = col * cell_w, row * (cell_h + label_h)
        draw.text((x + 7, y + 4), f"{shot_id} | t={sample_time:.2f}s", font=font, fill=(255, 222, 145))
        image = Image.open(frame_path).convert("RGB")
        image = image.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
        sheet.paste(image, (x, y + label_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=90)


def draw_final_motion_sheets(video: Path, story: dict, output_dir: Path,
                             frame_dir: Path, count: int = 9) -> tuple[list[dict], list[dict]]:
    """Extract exact source-frame indices at the nine intended instants for every shot."""
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_dir.mkdir(parents=True, exist_ok=True)
    selections = []
    for shot in story["shots"]:
        positions = motion_sample_frame_positions(shot, count)
        selections.append({"shot": shot, "positions": positions})
    frame_indices = sorted({index for item in selections for index, _ in item["positions"]})
    select_terms = "+".join(f"eq(n\\,{index})" for index in frame_indices)
    filter_graph = f"select='{select_terms}',scale=1280:720:flags=lanczos"
    pattern = frame_dir / "source-frame-%03d.jpg"
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-map", "0:v:0", "-vf", filter_graph, "-vsync", "0",
        "-frames:v", str(len(frame_indices)), "-q:v", "3", "-start_number", "1", str(pattern),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    frame_by_index = {
        frame_index: frame_dir / f"source-frame-{output_index:03d}.jpg"
        for output_index, frame_index in enumerate(frame_indices, 1)
    }
    missing = [str(path) for path in frame_by_index.values()
               if not path.is_file() or path.stat().st_size < 1000]
    if missing:
        raise RuntimeError(f"exact motion-frame extraction missed selected frames: {missing}")

    sheets, frame_samples = [], []
    for item in selections:
        shot = item["shot"]
        sid = shot["id"]
        positions = item["positions"]
        times = [sample_time for _, sample_time in positions]
        frame_paths = [frame_by_index[index] for index, _ in positions]
        sheet_path = output_dir / f"{sid}.jpg"
        assemble_final_motion_sheet(sid, times, frame_paths, sheet_path)
        sheets.append({"id": sid, "sample_times_seconds": times,
                       "contact_sheet": str(sheet_path), "frame_count": count})
        frame_samples.extend({"id": sid, "time_seconds": sample_time, "frame": str(path)}
                             for sample_time, path in zip(times, frame_paths))
    return sheets, frame_samples


def remove_motion_frame_files(frame_samples: list[dict]) -> None:
    for sample in frame_samples:
        Path(sample["frame"]).unlink(missing_ok=True)


def uniform_black_edge_run(image: Image.Image, reverse: bool = False) -> int:
    """Count rows of nearly uniform black matte at one edge of a sampled frame."""
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    height, width = gray.shape
    max_scan = max(2, int(height * 0.30))
    run = 0
    for offset in range(0, max_scan, 2):
        y = height - 1 - offset if reverse else offset
        row = gray[y, :].astype(np.float32)
        if float(np.mean(row)) < 10.0 and float(np.std(row)) < 4.0 and float(np.mean(row < 20)) > 0.995:
            run += 2
        else:
            break
    return min(run, max_scan)


def black_edge_boundary_contrast(image: Image.Image, run: int, reverse: bool = False) -> float:
    """Measure whether the matte ends at a sharp boundary rather than a natural dark gradient."""
    if run <= 0:
        return 0.0
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    height = gray.shape[0]
    edge_rows = gray[:min(5, run), :] if not reverse else gray[height-min(5, run):, :]
    probe_offset = min(max(8, int(height * 0.02)), max(0, height - run - 1))
    probe_y = run + probe_offset if not reverse else height - 1 - run - probe_offset
    if not 0 <= probe_y < height:
        return 0.0
    return float(np.mean(gray[probe_y, :])) - float(np.mean(edge_rows))


def scan_final_letterbox_bars(frame_samples: list[dict]) -> dict:
    """Flag persistent paired black mattes with a sharp interior boundary, not dark gradients."""
    by_shot = {}
    for sample in frame_samples:
        with Image.open(sample["frame"]) as image:
            top = uniform_black_edge_run(image, reverse=False)
            bottom = uniform_black_edge_run(image, reverse=True)
            top_contrast = black_edge_boundary_contrast(image, top, reverse=False)
            bottom_contrast = black_edge_boundary_contrast(image, bottom, reverse=True)
            height = image.height
        row = by_shot.setdefault(sample["id"], {"sample_count": 0, "paired": []})
        row["sample_count"] += 1
        min_bar = max(36, int(height * 0.06))
        if top >= min_bar and bottom >= min_bar and max(top_contrast, bottom_contrast) >= 25.0:
            row["paired"].append({"top": top, "bottom": bottom})
    findings = []
    for shot_id, row in by_shot.items():
        if len(row["paired"]) >= max(3, math.ceil(row["sample_count"] * 0.50)):
            findings.append({
                "shot": shot_id,
                "paired_bar_frames": len(row["paired"]),
                "sampled_frames": row["sample_count"],
                "median_top_bar_px": int(np.median([item["top"] for item in row["paired"]])),
                "median_bottom_bar_px": int(np.median([item["bottom"] for item in row["paired"]])),
            })
    return {"available": True, "finding_count": len(findings), "findings": findings,
            "method": "paired uniform-black top/bottom edge bands with a sharp interior boundary must persist in at least half of the exact-frame samples for a shot"}


def run_ffmpeg_scan(video: Path) -> dict:
    command = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(video),
        "-vf", "blackdetect=d=0.20:pix_th=0.10,freezedetect=n=-50dB:d=1.5",
        "-an", "-f", "null", "-",
    ]
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError("black/freeze scan failed: " + proc.stderr[-2000:])
    log = proc.stderr
    black = re.findall(r"black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)", log)
    freeze_starts = re.findall(r"freeze_start:\s*([0-9.]+)", log)
    freeze_durations = re.findall(r"freeze_duration:\s*([0-9.]+)", log)
    freeze_ends = re.findall(r"freeze_end:\s*([0-9.]+)", log)
    return {
        "black_intervals": [{"start": float(a), "end": float(b), "duration": float(c)} for a, b, c in black],
        "freeze_starts": [float(x) for x in freeze_starts],
        "freeze_durations": [float(x) for x in freeze_durations],
        "freeze_ends": [float(x) for x in freeze_ends],
    }


def plausible_ocr_token(token: str, confidence: float) -> bool:
    ascii_token = re.sub(r"[^A-Za-z0-9]", "", token)
    cjk_token = "".join(ch for ch in token if 0x3400 <= ord(ch) <= 0x9FFF)
    if len(ascii_token) > 40 or len(cjk_token) > 40:
        return False
    if cjk_token and not ascii_token:
        if cjk_token == "一":  # a frequent false positive on horizontal lines and ruled paper
            return False
        return (len(cjk_token) >= 2 and confidence >= 72) or (len(cjk_token) == 1 and confidence >= 96)
    if len(ascii_token) >= 4:
        return confidence >= 65
    if len(ascii_token) == 3:
        return confidence >= 75
    if len(ascii_token) == 2:
        return confidence >= 90 and (not ascii_token.isalpha() or ascii_token.isupper())
    if len(ascii_token) == 1:
        return confidence >= 97 and ascii_token.isdigit()
    return False


def ocr_words(image: Image.Image, temp_path: Path, psm: int = 11,
              allow_partial_cjk: bool = False) -> list[dict]:
    """Return plausible OCR tokens; subtitle mode keeps low-confidence CJK fragments for comparison."""
    image.convert("RGB").save(temp_path)
    proc = subprocess.run([
        "tesseract", str(temp_path), "stdout", "-l", "eng+chi_sim", "--psm", str(psm), "tsv",
    ], capture_output=True, text=True, timeout=45)
    temp_path.unlink(missing_ok=True)
    if proc.returncode:
        raise RuntimeError("Tesseract failed: " + proc.stderr[-1000:])
    words = []
    rows = csv.DictReader(proc.stdout.splitlines(), delimiter="\t")
    for row in rows:
        token = (row.get("text") or "").strip()
        try:
            confidence = float(row.get("conf", -1))
        except ValueError:
            continue
        cjk_token = "".join(ch for ch in token if 0x3400 <= ord(ch) <= 0x9FFF)
        partial_cjk = (allow_partial_cjk and cjk_token and len(cjk_token) <= 40 and confidence >= 40)
        if token and (plausible_ocr_token(token, confidence) or partial_cjk):
            words.append({"token": token, "confidence": round(confidence, 1)})
    return words


def unapproved_ocr_words(shot_id: str, words: list[dict]) -> list[dict]:
    if shot_id != "S14":
        return words
    approved = {"tamam", "shud", "tamamshud"}
    return [word for word in words
            if re.sub(r"[^a-z]+", "", word["token"].casefold()) not in approved]


def scan_unapproved_text(artifact: Path, samples: list[dict], output_dir: Path,
                         final_frame_samples: list[dict] | None = None) -> dict:
    """OCR source contacts and final frames, excluding post-produced subtitle/title zones."""
    if not shutil.which("tesseract"):
        return {"available": False, "reason": "tesseract executable not installed", "findings": []}
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_path = output_dir / "ocr-temp.png"
    source_findings = []
    source_cells_scanned = 0
    for sample in samples:
        sid = sample["id"]
        sheet_path = find_file(artifact, f"production/somerton/qa/{sid}.jpg", f"{sid}.jpg")
        if sheet_path is None:
            continue
        sheet = Image.open(sheet_path).convert("RGB")
        cell_w, cell_h = sheet.width // 3, sheet.height // 3
        for row in range(3):
            for col in range(3):
                tile = sheet.crop((col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h))
                gray = np.asarray(tile.convert("L"))
                if float(np.mean(gray)) < 14 or float(np.std(gray)) < 4:
                    continue
                tile = tile.resize((tile.width * 3, tile.height * 3), Image.Resampling.LANCZOS)
                source_cells_scanned += 1
                words = unapproved_ocr_words(sid, ocr_words(tile, temp_path))
                if words:
                    source_findings.append({"shot": sid, "sample_cell": row * 3 + col + 1, "words": words})

    final_findings = []
    final_frames_scanned = 0
    final_samples = samples if final_frame_samples is None else final_frame_samples
    for sample in final_samples:
        sid = sample["id"]
        if sid in {"S14", "S29"}:  # the allowed S14 phrase and post-produced S29 title occupy these frames
            continue
        image = Image.open(sample["frame"]).convert("RGB")
        # Burned-in subtitles occupy the bottom safe-area; OCR the image-bearing region only.
        image = image.crop((0, 0, image.width, int(image.height * 0.80)))
        final_frames_scanned += 1
        words = unapproved_ocr_words(sid, ocr_words(image, temp_path))
        if words:
            final_findings.append({"shot": sid, "time_seconds": sample["time_seconds"], "words": words})
    return {
        "available": True, "languages": "eng+chi_sim", "source_cells_scanned": source_cells_scanned,
        "final_frames_scanned": final_frames_scanned, "source_findings": source_findings,
        "final_findings": final_findings,
        "note": "OCR detections can be false positives on film grain/props; every flagged frame needs visual confirmation. Subtitle band and the approved S14 Tamam Shud and S29 closing-title frames are excluded from final-frame OCR.",
    }


def normalize_visible_text(text: str) -> str:
    return "".join(ch.casefold() for ch in text if ch.isalnum() or 0x3400 <= ord(ch) <= 0x9FFF)


def scan_rendered_subtitles(frame_samples: list[dict], cues: list[dict], output_dir: Path) -> dict:
    """Compare OCR from sampled burned-in subtitle bands with cues active at each sample time."""
    if not shutil.which("tesseract"):
        return {"available": False, "reason": "tesseract executable not installed", "findings": []}
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_path = output_dir / "subtitle-ocr-temp.png"
    cue_edges = [float(cue[key]) for cue in cues for key in ("start", "end")]
    boundary_tolerance = 0.12
    checked = 0
    skipped_boundaries = 0
    recognized = 0
    findings = []
    try:
        for sample in frame_samples:
            timestamp = float(sample["time_seconds"])
            if any(abs(timestamp - edge) <= boundary_tolerance for edge in cue_edges):
                skipped_boundaries += 1
                continue
            active = [cue for cue in cues if float(cue["start"]) <= timestamp < float(cue["end"])]
            expected = "".join(str(cue.get("text", "")) for cue in active)
            image = Image.open(sample["frame"]).convert("RGB")
            top = int(image.height * 0.76)
            band = image.crop((0, top, image.width, image.height))
            band = band.resize((band.width * 2, band.height * 2), Image.Resampling.LANCZOS)
            words = ocr_words(band, temp_path, psm=6, allow_partial_cjk=True)
            actual = "".join(str(word["token"]) for word in words)
            expected_norm = normalize_visible_text(expected)
            actual_norm = normalize_visible_text(actual)
            checked += 1
            if actual_norm:
                recognized += 1
            if expected_norm and actual_norm:
                similarity = difflib.SequenceMatcher(None, expected_norm, actual_norm).ratio()
                matched = similarity >= 0.50 or (len(actual_norm) >= 2 and actual_norm in expected_norm)
                if not matched:
                    findings.append({"shot": sample["id"], "time_seconds": timestamp,
                                     "expected": expected, "ocr": actual,
                                     "similarity": round(similarity, 3), "kind": "caption-mismatch"})
            elif expected_norm and not actual_norm:
                findings.append({"shot": sample["id"], "time_seconds": timestamp,
                                 "expected": expected, "ocr": "", "similarity": 0.0,
                                 "kind": "caption-not-read"})
            elif actual_norm and not expected_norm:
                findings.append({"shot": sample["id"], "time_seconds": timestamp,
                                 "expected": "", "ocr": actual, "similarity": 0.0,
                                 "kind": "unexpected-bottom-text"})
    finally:
        temp_path.unlink(missing_ok=True)
    finding_counts = {kind: sum(row["kind"] == kind for row in findings)
                      for kind in ("caption-not-read", "caption-mismatch", "unexpected-bottom-text")}
    return {
        "available": True,
        "sampled_frames": len(frame_samples),
        "checked_frames": checked,
        "skipped_near_cue_boundaries": skipped_boundaries,
        "frames_with_recognized_text": recognized,
        "finding_count": len(findings),
        "finding_counts": finding_counts,
        "findings": findings,
        "method": "Tesseract OCR of the bottom 24% on sampled final frames, compared with active caption timing; detections require visual confirmation.",
    }


def analyze_caption_voice_activity(audio: Path | np.ndarray, cues: list[dict]) -> dict:
    """Check timed captions against narration RMS activity; arrays are reconstructed source narration."""
    if isinstance(audio, Path):
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(audio), "-map", "0:a:0",
            "-ar", "48000", "-ac", "1", "-f", "f32le", "-acodec", "pcm_f32le", "pipe:1",
        ]
        mono = np.frombuffer(subprocess.check_output(command), dtype="<f4")
        track_source = "standalone-artifact-voiceover"
    else:
        mono = np.asarray(audio, dtype="<f4").reshape(-1)
        track_source = "reconstructed-versioned-narration"
    mono = np.nan_to_num(mono, copy=True)
    hop = 4800  # 100 ms at 48 kHz
    window_count = len(mono) // hop
    windows = mono[:window_count * hop].reshape(window_count, hop)
    rms = np.sqrt(np.mean(np.square(windows.astype(np.float64)), axis=1))
    rms_db = 20.0 * np.log10(np.maximum(rms, 1e-9))
    duration = len(mono) / 48000
    cue_rows = []
    weak_cues = []
    for index, cue in enumerate(cues, 1):
        start, end = float(cue["start"]), float(cue["end"])
        edge_pad = min(0.1, max(0.0, (end - start) / 4))
        lo = max(0, int(math.ceil((start + edge_pad) * 10 - 0.5)))
        hi = min(window_count, int(math.ceil((end - edge_pad) * 10 - 0.5)))
        section = rms_db[lo:hi]
        active_fraction = float(np.mean(section > -42.0)) if len(section) else 0.0
        row = {"cue": index, "start": start, "end": end,
               "text": str(cue.get("text", "")),
               "active_fraction_above_minus42dbfs": round(active_fraction, 3),
               "duration_seconds": round(end - start, 3)}
        cue_rows.append(row)
        if active_fraction < 0.35:
            weak_cues.append(row)
    return {"available": True, "track_source": track_source,
            "duration_seconds": round(duration, 3),
            "cue_count": len(cues), "weak_cue_count": len(weak_cues),
            "weak_cues": weak_cues, "cue_activity": cue_rows,
            "note": "Narration-track RMS activity is a timing aid, not speech recognition or human listening."}


def narration_timing_matches(actual: dict, expected: dict) -> tuple[bool, list[str]]:
    """Confirm rebuilt chapter/shot timing matches the delivered narration receipt."""
    mismatches = []
    for section in ("chapters", "shots"):
        actual_rows = actual.get(section, [])
        expected_rows = expected.get(section, [])
        if len(actual_rows) != len(expected_rows):
            mismatches.append(f"{section}_count:{len(actual_rows)}!={len(expected_rows)}")
            continue
        if section == "chapters":
            exact_fields = ("id", "characters", "shot_ids")
            float_fields = ("start", "duration", "source_seconds", "tempo_factor",
                            "target_chars_per_second", "inserted_pause_seconds",
                            "inserted_pause_at_chapter_seconds", "speech_seconds")
        else:
            exact_fields = ("id", "narration_id", "text", "characters")
            float_fields = ("start", "duration", "source_seconds", "natural_clip_seconds",
                            "natural_speech_seconds", "spoken_seconds", "tempo_factor",
                            "speech_start", "speech_end", "target_chars_per_second")
        for index, (actual_row, expected_row) in enumerate(zip(actual_rows, expected_rows), 1):
            for key in exact_fields:
                if actual_row.get(key) != expected_row.get(key):
                    mismatches.append(f"{section}{index}:{key}")
            for key in float_fields:
                left, right = actual_row.get(key), expected_row.get(key)
                if left is None or right is None:
                    if left is not right:
                        mismatches.append(f"{section}{index}:{key}")
                elif abs(float(left) - float(right)) > 0.002:
                    mismatches.append(f"{section}{index}:{key}")
    for key in ("voice_id", "alignment", "slowdown_allowed", "max_speedup_factor", "duration_seconds"):
        left, right = actual.get(key), expected.get(key)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            if abs(float(left) - float(right)) > 0.002:
                mismatches.append(f"narration:{key}")
        elif left != right:
            mismatches.append(f"narration:{key}")
    return not mismatches, mismatches

def analyze_audio(video: Path, story: dict) -> dict:
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-map", "0:a:0",
        "-ar", "48000", "-ac", "2", "-f", "f32le", "-acodec", "pcm_f32le", "pipe:1",
    ]
    raw = subprocess.check_output(command)
    samples = np.frombuffer(raw, dtype="<f4").reshape(-1, 2)
    mono = samples.mean(axis=1)
    hop = 4800  # 100 ms at 48 kHz
    window_count = len(mono) // hop
    windows = mono[:window_count * hop].reshape(window_count, hop)
    rms = np.sqrt(np.mean(np.square(windows.astype(np.float64)), axis=1))
    rms_db = 20.0 * np.log10(np.maximum(rms, 1e-9))
    chapter_rows = []
    for chapter in story["chapters"]:
        lo = max(0, int(float(chapter["start"]) * 10))
        hi = min(window_count, int((float(chapter["start"]) + float(chapter["duration"])) * 10))
        section = rms_db[lo:hi]
        chapter_rows.append({
            "id": chapter["id"], "windows": int(len(section)),
            "active_fraction_above_minus42dbfs": round(float(np.mean(section > -42.0)), 4) if len(section) else 0.0,
            "median_rms_dbfs": round(float(np.median(section)), 2) if len(section) else None,
        })
    peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    clipping = float(np.mean(np.abs(samples) >= 0.999)) if samples.size else 0.0
    return {
        "samples_per_channel": int(len(samples)), "duration_seconds": round(len(samples) / 48000, 4),
        "sample_rate": 48000, "channels": 2,
        "peak_dbfs": round(20 * math.log10(max(peak, 1e-9)), 2),
        "fraction_samples_at_or_above_0_999": round(clipping, 8),
        "chapter_activity": chapter_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-run-id", default="")
    args = parser.parse_args()
    artifact = args.artifact_root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 2, "checks": [], "failures": [], "warnings": [],
              "artifact_root": str(artifact), "expected_run_id": args.expected_run_id}
    story = load_json(HERE / "story.json")

    results_path = find_file(artifact, "production/somerton/results.json", "results.json")
    if results_path is None:
        add_check(report, "artifact-results-json", False, "results.json missing from downloaded artifact")
        (out / "automated-qc.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1
    results = load_json(results_path)
    report["source_run_id"] = str(results.get("run_id"))
    add_check(report, "artifact-run-id", not args.expected_run_id or str(results.get("run_id")) == args.expected_run_id,
              f"results run_id={results.get('run_id')}")
    add_check(report, "first-cut-phase", results.get("phase") == "first_cut_ready",
              f"phase={results.get('phase')}")
    shots = story.get("shots", [])
    expected_ids = [shot["id"] for shot in shots]
    rows = results.get("shots", {})
    completed = [sid for sid in expected_ids if rows.get(sid, {}).get("status") == "completed"]
    add_check(report, "all-29-source-receipts", len(expected_ids) == EXPECTED_SHOTS and len(completed) == EXPECTED_SHOTS,
              f"{len(completed)}/{EXPECTED_SHOTS} completed receipts")
    source_qc = []
    prompt_hash_validation = []
    for shot in shots:
        sid = shot["id"]
        record = rows.get(sid, {})
        expected_hash = request_hash(story, shot)
        actual_hash = record.get("request_hash")
        hash_matches = actual_hash == expected_hash
        prompt_hash_validation.append({
            "shot": sid, "matches_current_story": hash_matches,
            "expected_request_hash": expected_hash, "actual_request_hash": actual_hash,
        })
        add_check(report, f"source-prompt-hash-{sid}", hash_matches,
                  f"expected={expected_hash[:12]} actual={str(actual_hash)[:12]}", severity="warning")
        source = find_file(artifact, f"work/somerton/clips/{sid}.mp4", f"{sid}.mp4")
        sheet = find_file(artifact, f"production/somerton/qa/{sid}.jpg", f"{sid}.jpg")
        if source is None:
            add_check(report, f"source-clip-{sid}", False, "source clip missing from downloaded artifact")
            continue
        try:
            measured = probe(source)
            stream = next((item for item in measured.get("streams", []) if item.get("codec_type") == "video"), {})
            source_duration = float(measured.get("format", {}).get("duration", 0))
            inspection = record.get("inspection", {})
            digest_ok = sha256(source) == record.get("sha256") and source.stat().st_size == record.get("bytes")
            decode_receipt_ok = inspection.get("decoded_ok") is True
            resolution_ok = stream.get("width", 0) >= 640 and stream.get("height", 0) >= 360
            duration_ok = 3.75 <= source_duration <= 9.5
            sheet_ok = sheet is not None and sheet.stat().st_size > 1000
            ok = record.get("status") == "completed" and digest_ok and decode_receipt_ok and resolution_ok and duration_ok and sheet_ok
            detail = (f"sha256/bytes={'ok' if digest_ok else 'MISMATCH'}, decoded receipt={decode_receipt_ok}, "
                      f"{stream.get('width')}x{stream.get('height')} {source_duration:.3f}s, contact sheet={'present' if sheet_ok else 'missing'}")
            add_check(report, f"source-clip-{sid}", ok, detail)
            source_qc.append({"id": sid, "sha256_matches_receipt": digest_ok, "decoded_receipt": decode_receipt_ok,
                              "width": stream.get("width"), "height": stream.get("height"),
                              "duration_seconds": round(source_duration, 3), "contact_sheet_present": sheet_ok})
        except Exception as exc:
            add_check(report, f"source-clip-{sid}", False, f"{type(exc).__name__}: {exc}")
    report["prompt_hash_validation"] = prompt_hash_validation
    report["source_clip_qc"] = source_qc
    add_check(report, "delivery-metadata", results.get("delivery", {}).get("duration_seconds") == DURATION
              and results.get("delivery", {}).get("width") == 1920
              and results.get("delivery", {}).get("height") == 1080
              and results.get("delivery", {}).get("fps") == FPS,
              json.dumps(results.get("delivery"), ensure_ascii=False))

    delivery = results.get("delivery", {})
    video = find_file(artifact, delivery.get("film"), Path(delivery.get("film", "missing.mp4")).name)
    technical_path = find_file(artifact, "work/somerton/edit/delivery/technical-report.json", "technical-report.json")
    edl_path = find_file(artifact, "work/somerton/edit/delivery/edit-decision-list.json", "edit-decision-list.json")
    narration_path = find_file(artifact, "work/somerton/edit/delivery/narration-timing.json", "narration-timing.json")
    captions_path = find_file(artifact, "work/somerton/edit/delivery/caption-timing.json", "caption-timing.json")
    required_files = {"final-video": video, "technical-report": technical_path,
                      "edit-decision-list": edl_path, "narration-timing": narration_path,
                      "caption-timing": captions_path}
    for name, path in required_files.items():
        add_check(report, f"artifact-{name}-present", path is not None,
                  str(path) if path else f"{name} missing")
    if any(path is None for path in required_files.values()):
        (out / "automated-qc.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 1

    technical = load_json(technical_path)
    edl = load_json(edl_path)
    narration_timing = load_json(narration_path)
    cues = load_json(captions_path)
    report["technical_report"] = technical.get("video", {})
    report["soundtrack_report"] = technical.get("soundtrack", {})
    add_check(report, "technical-report-human-review-complete",
              technical.get("unreviewed_first_cut") is False and technical.get("human_visual_review") == "complete",
              f"human_visual_review={technical.get('human_visual_review')}; unreviewed_first_cut={technical.get('unreviewed_first_cut')}",
              severity="warning")

    edl_ids = [row.get("id") for row in edl]
    add_check(report, "edit-decision-list-order", edl_ids == expected_ids,
              f"EDL entries={len(edl)}, story entries={len(expected_ids)}")
    for shot, edit in zip(shots, edl):
        good = (edit.get("id") == shot["id"]
                and abs(float(edit.get("start", -999)) - float(shot["start"])) < 0.001
                and abs(float(edit.get("end", -999)) - (float(shot["start"]) + float(shot["duration"]))) < 0.001
                and edit.get("narration_id") == shot["narration_id"]
                and edit.get("narration") == shot["narration"])
        add_check(report, f"shot-narration-map-{shot['id']}", good,
                  f"{edit.get('start')}–{edit.get('end')}s → {edit.get('narration_id')}: {edit.get('narration')}; "
                  f"expected {shot['start']}–{shot['start']+shot['duration']}s → {shot['narration_id']}: {shot['narration']}")

    narration_spec = story.get("narration_spec", {})
    max_speedup = float(narration_spec.get("max_speedup_factor", 1.18))
    policy_ok = (narration_timing.get("voice_id") == narration_spec.get("voice_id")
                 and narration_timing.get("alignment") == "one-clip-one-shot-one-caption"
                 and narration_timing.get("slowdown_allowed") is False
                 and abs(float(narration_timing.get("max_speedup_factor", 0)) - max_speedup) < 0.001)
    add_check(report, "narration-shot-alignment-policy", policy_ok,
              f"voice={narration_timing.get('voice_id')}; one clip/caption per shot; slowdown={narration_timing.get('slowdown_allowed')}; max speed-up={narration_timing.get('max_speedup_factor')}")

    chapter_rows = narration_timing.get("chapters", [])
    chapters = story.get("chapters", [])
    add_check(report, "nine-narration-chapters", len(chapter_rows) == 9 and len(chapters) == 9,
              f"timing chapters={len(chapter_rows)}, story chapters={len(chapters)}")
    for expected, measured in zip(chapters, chapter_rows):
        good = (expected.get("id") == measured.get("id")
                and abs(float(expected.get("start", -999)) - float(measured.get("start", -999))) < 0.001
                and abs(float(expected.get("duration", -999)) - float(measured.get("duration", -999))) < 0.001
                and 1.0 <= float(measured.get("tempo_factor", 0)) <= max_speedup + 0.001
                and int(measured.get("characters", -1)) == visible_weight(expected.get("text", ""))
                and measured.get("shot_ids") == expected.get("shot_ids"))
        add_check(report, f"voice-timing-{expected['id']}", good,
                  f"start={measured.get('start')}, duration={measured.get('duration')}, "
                  f"maximum shot speed-up={measured.get('tempo_factor')}, target cps={measured.get('target_chars_per_second')}")

    shot_timing_rows = narration_timing.get("shots", [])
    shot_timing = {row.get("id"): row for row in shot_timing_rows}
    add_check(report, "29-shot-narration-timings", len(shot_timing_rows) == len(shots)
              and [row.get("id") for row in shot_timing_rows] == expected_ids,
              f"timed narration clips={len(shot_timing_rows)}; expected one for each ordered shot")
    for shot in shots:
        measured = shot_timing.get(shot["id"], {})
        maximum_end = min(float(shot["start"]) + float(shot["duration"]) - 0.05, DURATION - 1.0)
        good = (measured.get("narration_id") == shot["narration_id"]
                and measured.get("text") == shot["narration"]
                and abs(float(measured.get("start", -999)) - float(shot["start"])) < 0.001
                and abs(float(measured.get("duration", -999)) - float(shot["duration"])) < 0.001
                and int(measured.get("characters", -1)) == visible_weight(shot["narration"])
                and 1.0 <= float(measured.get("tempo_factor", 0)) <= max_speedup + 0.001
                and float(measured.get("speech_start", -1)) >= float(shot["start"]) - 0.001
                and float(measured.get("speech_end", DURATION + 1)) <= maximum_end + 0.03
                and float(measured.get("speech_end", -1)) > float(measured.get("speech_start", DURATION)))
        add_check(report, f"voice-timing-shot-{shot['id']}", good,
                  f"{measured.get('speech_start')}–{measured.get('speech_end')}s; "
                  f"shot={shot['start']}–{shot['start']+shot['duration']}s; "
                  f"speed-up={measured.get('tempo_factor')}")
    add_check(report, "narration-covers-180s", abs(float(narration_timing.get("duration_seconds", 0)) - DURATION) < 0.001,
              f"narration timeline duration={narration_timing.get('duration_seconds')}")

    try:
        srt_path = find_file(artifact, basename="塔玛姆·舒德_字幕.srt")
        srt_cues = parse_srt(srt_path) if srt_path else []
        add_check(report, "subtitle-file-present", srt_path is not None, str(srt_path) if srt_path else "SRT missing")
        add_check(report, "srt-vs-caption-timing-count", len(srt_cues) == len(cues) == len(shots),
                  f"SRT cues={len(srt_cues)}, timing cues={len(cues)}, shots={len(shots)}")
        for index, (srt, cue) in enumerate(zip(srt_cues, cues), 1):
            exact = (abs(srt["start"] - float(cue["start"])) <= 0.02
                     and abs(srt["end"] - float(cue["end"])) <= 0.02
                     and srt["text"] == cue["text"])
            add_check(report, f"subtitle-cue-{index:03d}", exact,
                      f"SRT {srt['start']:.3f}–{srt['end']:.3f}; JSON {cue['start']}–{cue['end']}")
        ordered = all(float(cues[i]["start"]) <= float(cues[i + 1]["start"])
                      and float(cues[i]["end"]) <= float(cues[i + 1]["start"]) + 0.05
                      for i in range(len(cues) - 1))
        add_check(report, "subtitle-order-and-overlap", ordered, f"{len(cues)} cues")
        cue_by_shot = {cue.get("shot_id"): cue for cue in cues}
        cue_order = [cue.get("shot_id") for cue in cues]
        add_check(report, "one-caption-per-shot-in-order", cue_order == expected_ids,
                  f"mapped subtitle shots={cue_order}")
        for shot in shots:
            cue = cue_by_shot.get(shot["id"], {})
            timing = shot_timing.get(shot["id"], {})
            good = (cue.get("shot_id") == shot["id"]
                    and cue.get("narration_id") == shot["narration_id"]
                    and cue.get("text") == shot["narration"]
                    and abs(float(cue.get("start", -999)) - float(timing.get("speech_start", -999))) <= 0.002
                    and abs(float(cue.get("end", -999)) - float(timing.get("speech_end", -999))) <= 0.002
                    and float(cue.get("start", -1)) >= float(shot["start"]) - 0.001
                    and float(cue.get("end", DURATION + 1)) <= min(
                        float(shot["start"]) + float(shot["duration"]) - 0.05, DURATION - 1.0) + 0.03)
            add_check(report, f"narration-caption-text-{shot['id']}", good,
                      f"caption={cue.get('text')}; expected shot narration={shot['narration']}; "
                      f"cue={cue.get('start')}–{cue.get('end')}s")
    except Exception as exc:
        add_check(report, "subtitle-analysis", False, f"{type(exc).__name__}: {exc}")

    voiceover_path = find_file(artifact, "work/somerton/edit/audio/voiceover.wav", "voiceover.wav")
    try:
        if voiceover_path is not None:
            voice_activity = analyze_caption_voice_activity(voiceover_path, cues)
            voice_activity["provenance"] = "standalone narration track extracted from the production artifact"
        else:
            # The current production artifact omits edit/audio/voiceover.wav. Rebuild the narration
            # from the versioned MP3 receipts, then require its chapter timing to match the artifact.
            from production.somerton.build_audio import build_narration

            with tempfile.TemporaryDirectory(prefix="somerton-narration-qc-") as temp_dir:
                rebuilt_voice, _, rebuilt_timing = build_narration(
                    story, HERE / "audio", Path(temp_dir))
            timing_matches, timing_mismatches = narration_timing_matches(rebuilt_timing, narration_timing)
            if not timing_matches:
                raise ValueError(f"source-rebuilt narration timing differs from artifact: {timing_mismatches}")
            voice_activity = analyze_caption_voice_activity(rebuilt_voice, cues)
            voice_activity["provenance"] = (
                "reconstructed from version-controlled narration MP3s; chapter timing matched the artifact receipt")
        report["caption_voice_activity"] = voice_activity
        add_check(report, "caption-overlaps-voiceover-activity", voice_activity["weak_cue_count"] == 0,
                  f"{voice_activity['cue_count']} caption cues; low-speech-activity cues="
                  f"{voice_activity['weak_cue_count']}; source={voice_activity['track_source']}",
                  severity="warning")
    except Exception as exc:
        report["caption_voice_activity"] = {"available": False,
                                             "reason": f"{type(exc).__name__}: {exc}"}
        add_check(report, "caption-overlaps-voiceover-activity", False,
                  report["caption_voice_activity"]["reason"], severity="warning")

    sound = technical.get("soundtrack", {})
    narration_sound = sound.get("narration", {})
    add_check(report, "mix-duration", abs(float(sound.get("duration_seconds", 0)) - DURATION) < 0.001,
              f"{sound.get('duration_seconds')}s")
    add_check(report, "mix-format", sound.get("sample_rate") == 48000 and sound.get("channels") == 2,
              f"{sound.get('sample_rate')} Hz, {sound.get('channels')} channels")
    add_check(report, "mix-peak-ceiling", float(sound.get("peak_dbfs", 0)) <= -1.4,
              f"mix peak={sound.get('peak_dbfs')} dBFS")
    bgm = sound.get("bgm_under_voice_measured_db")
    add_check(report, "bgm-under-voice-level", bgm is not None and -22.0 <= float(bgm) <= -14.0,
              f"measured BGM-under-voice={bgm} dB; target about -18 dB", severity="warning")
    voice_rows = narration_sound.get("shots", [])
    no_slowdown = (narration_sound.get("slowdown_allowed") is False
                   and len(voice_rows) == EXPECTED_SHOTS
                   and all(1.0 <= float(row.get("tempo_factor", 0))
                           <= float(narration_sound.get("max_speedup_factor", 1.18)) + 0.001
                           for row in voice_rows))
    add_check(report, "no-slowdown-shot-locked-voice", no_slowdown,
              f"{len(voice_rows)} shot clips; tempo range="
              f"{min((float(row.get('tempo_factor', 0)) for row in voice_rows), default=0):.3f}–"
              f"{max((float(row.get('tempo_factor', 0)) for row in voice_rows), default=0):.3f}x")

    try:
        media = probe(video)
        fmt = media.get("format", {})
        streams = media.get("streams", [])
        v = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
        a = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
        format_duration = float(fmt.get("duration", 0))
        video_duration = float(v.get("duration", format_duration))
        audio_duration = float(a.get("duration", format_duration))
        video_start = float(v.get("start_time", 0) or 0)
        audio_start = float(a.get("start_time", 0) or 0)
        fps = rate(v.get("avg_frame_rate"))
        frame_count = int(v.get("nb_frames") or round(video_duration * (fps or 0)))
        media_summary = {
            "format_duration_seconds": format_duration, "video_duration_seconds": video_duration,
            "audio_duration_seconds": audio_duration, "video_start_seconds": video_start,
            "audio_start_seconds": audio_start, "width": v.get("width"), "height": v.get("height"),
            "fps": fps, "frame_count": frame_count, "video_codec": v.get("codec_name"),
            "audio_codec": a.get("codec_name"), "audio_sample_rate": a.get("sample_rate"),
            "audio_channels": a.get("channels"), "file_bytes": video.stat().st_size,
        }
        report["final_media"] = media_summary
        add_check(report, "final-video-resolution", v.get("width") == 1920 and v.get("height") == 1080,
                  f"{v.get('width')}x{v.get('height')}")
        add_check(report, "final-video-frame-rate", fps is not None and abs(fps - FPS) < 0.01,
                  f"{v.get('avg_frame_rate')} ({fps} fps)")
        add_check(report, "final-video-frame-count", frame_count == 5400, f"{frame_count} frames")
        add_check(report, "final-audio-format", a.get("sample_rate") == "48000" and a.get("channels") == 2,
                  f"{a.get('sample_rate')} Hz, {a.get('channels')} channels, {a.get('codec_name')}")
        add_check(report, "av-duration-sync", abs(video_duration - audio_duration) <= 0.08
                  and abs(format_duration - DURATION) <= 0.05,
                  f"format={format_duration:.3f}s video={video_duration:.3f}s audio={audio_duration:.3f}s")
        add_check(report, "av-start-sync", abs(video_start - audio_start) <= 0.03,
                  f"video start={video_start:.4f}s audio start={audio_start:.4f}s")

        decode = subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-xerror", "-i", str(video),
            "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-",
        ], capture_output=True, text=True)
        add_check(report, "full-audio-video-decode", decode.returncode == 0,
                  decode.stderr[-2000:] if decode.returncode else "All video frames and audio packets decode without FFmpeg errors")

        audio_metrics = analyze_audio(video, story)
        report["decoded_audio_metrics"] = audio_metrics
        add_check(report, "decoded-audio-duration", abs(audio_metrics["duration_seconds"] - DURATION) <= 0.08,
                  f"decoded {audio_metrics['duration_seconds']}s")
        add_check(report, "decoded-audio-no-digital-clipping", audio_metrics["peak_dbfs"] < -0.05
                  and audio_metrics["fraction_samples_at_or_above_0_999"] < 1e-6,
                  f"peak={audio_metrics['peak_dbfs']} dBFS; clipped fraction={audio_metrics['fraction_samples_at_or_above_0_999']}")
        weak_chapters = [row["id"] for row in audio_metrics["chapter_activity"]
                         if row["active_fraction_above_minus42dbfs"] < 0.60]
        add_check(report, "speech-audio-present-each-chapter", not weak_chapters,
                  f"low-activity chapters={weak_chapters or 'none'}", severity="warning")

        scan = run_ffmpeg_scan(video)
        report["black_and_freeze_scan"] = scan
        long_black = [row for row in scan["black_intervals"] if row["duration"] > 1.0]
        long_freeze = [duration for duration in scan["freeze_durations"] if duration > 2.5]
        add_check(report, "black-frame-scan", not long_black,
                  f"intervals >1s={long_black}", severity="warning")
        add_check(report, "freeze-scan", not long_freeze,
                  f"freeze intervals >2.5s={long_freeze}", severity="warning")
        samples = draw_midpoint_sheet(video, story, out / "final-film-midpoints.jpg", out / "frames")
        report["midpoint_samples"] = samples
        blank_candidates = [row["id"] for row in samples
                            if row["near_black_fraction"] > 0.90 and row["luma_stddev"] < 8]
        add_check(report, "shot-midpoint-nonblank", not blank_candidates,
                  f"possible blank/dark shots={blank_candidates or 'none'}", severity="warning")

        motion_frame_dir = out / "motion-frames"
        motion_frame_samples = []
        try:
            motion_sheets, motion_frame_samples = draw_final_motion_sheets(
                video, story, out / "final-shot-sheets", motion_frame_dir, count=9)
            report["final_motion_sheets"] = motion_sheets
            complete_sheets = (len(motion_sheets) == len(shots)
                               and all(row["frame_count"] == 9 for row in motion_sheets))
            add_check(report, "final-shot-motion-sheets", complete_sheets,
                      f"{len(motion_sheets)}/{len(shots)} shots, nine exact source-frame samples per sheet")
            letterbox_scan = scan_final_letterbox_bars(motion_frame_samples)
            report["final_letterbox_scan"] = letterbox_scan
            add_check(report, "final-video-letterbox", letterbox_scan["finding_count"] == 0,
                      f"persistent paired black mattes={letterbox_scan['findings'] or 'none'}",
                      severity="warning")
            text_scan = scan_unapproved_text(
                artifact, samples, out / "ocr-review",
                final_frame_samples=[*samples, *motion_frame_samples])
            report["ocr_text_scan"] = text_scan
            if not text_scan.get("available"):
                add_check(report, "ocr-unapproved-scene-text", False,
                          text_scan.get("reason", "OCR unavailable"), severity="warning")
            else:
                source_hits = len(text_scan["source_findings"])
                final_hits = len(text_scan["final_findings"])
                add_check(report, "ocr-unapproved-scene-text", source_hits == 0 and final_hits == 0,
                          f"possible text detections: {source_hits} source contact-sheet cells, {final_hits} final sampled frames; inspect listed tokens visually",
                          severity="warning")
            subtitle_scan = scan_rendered_subtitles(motion_frame_samples, cues, out / "subtitle-ocr")
            report["rendered_subtitle_scan"] = subtitle_scan
            if not subtitle_scan.get("available"):
                add_check(report, "rendered-subtitle-samples", False,
                          subtitle_scan.get("reason", "subtitle OCR unavailable"), severity="warning")
            else:
                finding_counts = subtitle_scan["finding_counts"]
                add_check(report, "rendered-subtitle-samples", subtitle_scan["finding_count"] == 0,
                          f"OCR compared {subtitle_scan['checked_frames']} exact-frame samples; "
                          f"boundary skips={subtitle_scan['skipped_near_cue_boundaries']}; "
                          f"not-read={finding_counts['caption-not-read']}, "
                          f"text-mismatch={finding_counts['caption-mismatch']}, "
                          f"unexpected-bottom-text={finding_counts['unexpected-bottom-text']}",
                          severity="warning")
        finally:
            remove_motion_frame_files(motion_frame_samples)
            if motion_frame_dir.exists():
                for leftover in motion_frame_dir.glob("*.jpg"):
                    leftover.unlink(missing_ok=True)
                motion_frame_dir.rmdir()
    except Exception as exc:
        add_check(report, "media-analysis", False, f"{type(exc).__name__}: {exc}")

    report["automated_status"] = "fail" if report["failures"] else ("pass_with_warnings" if report["warnings"] else "pass")
    report["manual_visual_review"] = {
        "status": "pending",
        "note": "Automated checks, subtitle-band OCR, source-reconstructed narration activity, paired-edge letterbox scans, midpoint stills and nine evenly spaced final-cut frames per shot do not replace continuous full-motion review for morphing, visual glitches, story fit, subtitle placement or human audio semantics. See the 29 final-shot contact sheets and midpoint sheet.",
    }
    output = out / "automated-qc.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    import os
    summary_value = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_value:
        summary = Path(summary_value)
        lines = ["## Somerton automated QC", "", f"**Status:** `{report['automated_status']}`", "",
                 f"- Checks: {sum(c['status']=='pass' for c in report['checks'])} pass, "
                 f"{sum(c['status']=='warn' for c in report['checks'])} warnings, "
                 f"{sum(c['status']=='fail' for c in report['checks'])} failures.",
                 f"- Completed shots: {len(completed)}/29.",
                 f"- Final motion sheets: {len(report.get('final_motion_sheets', []))} (nine frames per shot; not a substitute for continuous review).",
                 f"- Final video: {delivery.get('film')}",
                 f"- Possible OCR text hits: {len(report.get('ocr_text_scan', {}).get('source_findings', []))} source cells, "
                 f"{len(report.get('ocr_text_scan', {}).get('final_findings', []))} final frames.",
                 f"- Rendered subtitle OCR findings: {report.get('rendered_subtitle_scan', {}).get('finding_count', 'unavailable')}.",
                 f"- Caption/voiceover activity findings: {report.get('caption_voice_activity', {}).get('weak_cue_count', 'unavailable')}.",
                 f"- Final letterbox-scan findings: {report.get('final_letterbox_scan', {}).get('finding_count', 'unavailable')}.",
                 "- Manual full-motion visual/audio review remains required.", ""]
        summary.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"automated_status": report["automated_status"],
                      "checks": len(report["checks"]), "failures": report["failures"],
                      "warnings": report["warnings"], "report": str(output)}, ensure_ascii=False, indent=2))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
