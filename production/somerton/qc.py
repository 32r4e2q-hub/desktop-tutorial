#!/usr/bin/env python3
"""Automated post-render QC for a downloaded Somerton Actions artifact.

This checks delivery streams, full decode, source receipts, EDL/story mapping,
narration/subtitle timing and audio levels. Motion and semantic visual review remain
human tasks; a labeled midpoint sheet is emitted for that pass.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageStat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
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


def ocr_words(image: Image.Image, temp_path: Path) -> list[dict]:
    """Return only plausible OCR tokens; this is a flagging aid, never a visual sign-off."""
    image.convert("RGB").save(temp_path)
    proc = subprocess.run([
        "tesseract", str(temp_path), "stdout", "-l", "eng+chi_sim", "--psm", "11", "tsv",
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
        if token and plausible_ocr_token(token, confidence):
            words.append({"token": token, "confidence": round(confidence, 1)})
    return words


def unapproved_ocr_words(shot_id: str, words: list[dict]) -> list[dict]:
    if shot_id != "S14":
        return words
    approved = {"tamam", "shud", "tamamshud"}
    return [word for word in words
            if re.sub(r"[^a-z]+", "", word["token"].casefold()) not in approved]


def scan_unapproved_text(artifact: Path, samples: list[dict], output_dir: Path) -> dict:
    """OCR sampled source frames and the final cut, excluding post-produced subtitle/title zones."""
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
    for sample in samples:
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
    for shot in shots:
        sid = shot["id"]
        record = rows.get(sid, {})
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
                and edit.get("narration_id") == shot["narration_id"])
        add_check(report, f"shot-narration-map-{shot['id']}", good,
                  f"{edit.get('start')}–{edit.get('end')}s → {edit.get('narration_id')}; expected {shot['start']}–{shot['start']+shot['duration']}s → {shot['narration_id']}")

    chapter_rows = narration_timing.get("chapters", [])
    chapters = story.get("chapters", [])
    add_check(report, "nine-narration-chapters", len(chapter_rows) == 9 and len(chapters) == 9,
              f"timing chapters={len(chapter_rows)}, story chapters={len(chapters)}")
    for expected, measured in zip(chapters, chapter_rows):
        good = (expected.get("id") == measured.get("id")
                and abs(float(expected.get("start", -999)) - float(measured.get("start", -999))) < 0.001
                and abs(float(expected.get("duration", -999)) - float(measured.get("duration", -999))) < 0.001
                and 0.60 <= float(measured.get("tempo_factor", 0)) <= 1.22
                and int(measured.get("characters", -1)) == visible_weight(expected.get("text", "")))
        add_check(report, f"voice-timing-{expected['id']}", good,
                  f"start={measured.get('start')}, duration={measured.get('duration')}, tempo={measured.get('tempo_factor')}, target cps={measured.get('target_chars_per_second')}")
    add_check(report, "narration-covers-180s", abs(float(narration_timing.get("duration_seconds", 0)) - DURATION) < 0.001,
              f"narration duration={narration_timing.get('duration_seconds')}")

    try:
        srt_path = find_file(artifact, basename="塔玛姆·舒德_字幕.srt")
        srt_cues = parse_srt(srt_path) if srt_path else []
        add_check(report, "subtitle-file-present", srt_path is not None, str(srt_path) if srt_path else "SRT missing")
        add_check(report, "srt-vs-caption-timing-count", len(srt_cues) == len(cues),
                  f"SRT cues={len(srt_cues)}, timing cues={len(cues)}")
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
        for chapter in chapters:
            chapter_start = float(chapter["start"])
            chapter_end = chapter_start + float(chapter["duration"])
            # Assign by cue start to exactly one chapter; a small end tolerance here
            # incorrectly pulls the next chapter's first subtitle into this chapter.
            chapter_cues = [cue for cue in cues if chapter_start <= float(cue["start"]) < chapter_end]
            expected_clauses = clauses(chapter["text"])
            actual_text = [cue["text"] for cue in chapter_cues]
            good = actual_text == expected_clauses and all(
                float(cue["end"]) <= float(chapter["start"]) + float(chapter["duration"]) + 0.03
                for cue in chapter_cues
            )
            add_check(report, f"narration-caption-text-{chapter['id']}", good,
                      f"caption clauses={len(actual_text)}, expected clauses={len(expected_clauses)}")
    except Exception as exc:
        add_check(report, "subtitle-analysis", False, f"{type(exc).__name__}: {exc}")

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
    pause_records = narration_sound.get("chapters", [])
    requested_pauses = [p for p in pause_records if float(p.get("inserted_pause_seconds", 0)) > 0]
    add_check(report, "dramatic-pause-settings", all(abs(float(p["inserted_pause_seconds"]) - 0.5) < 0.001
              for p in requested_pauses) and len(requested_pauses) == 2,
              f"configured pauses={[(p.get('id'), p.get('inserted_pause_seconds'), p.get('inserted_pause_at_chapter_seconds')) for p in requested_pauses]}")

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
        text_scan = scan_unapproved_text(artifact, samples, out / "ocr-review")
        report["ocr_text_scan"] = text_scan
        if not text_scan.get("available"):
            add_check(report, "ocr-unapproved-scene-text", False,
                      text_scan.get("reason", "OCR unavailable"), severity="warning")
        else:
            source_hits = len(text_scan["source_findings"])
            final_hits = len(text_scan["final_findings"])
            add_check(report, "ocr-unapproved-scene-text", source_hits == 0 and final_hits == 0,
                      f"possible text detections: {source_hits} source contact-sheet cells, {final_hits} final midpoints; inspect listed tokens visually",
                      severity="warning")
    except Exception as exc:
        add_check(report, "media-analysis", False, f"{type(exc).__name__}: {exc}")

    report["automated_status"] = "fail" if report["failures"] else ("pass_with_warnings" if report["warnings"] else "pass")
    report["manual_visual_review"] = {
        "status": "pending",
        "note": "Automated checks and midpoint stills do not replace full-motion review for morphing, visual glitches, story fit or subtitle placement. See the 29-shot contact sheets and final-film midpoint sheet.",
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
                 f"- Final video: {delivery.get('film')}",
                 f"- Possible OCR text hits: {len(report.get('ocr_text_scan', {}).get('source_findings', []))} source cells, "
                 f"{len(report.get('ocr_text_scan', {}).get('final_findings', []))} final frames.",
                 "- Manual full-motion visual/audio review remains required.", ""]
        summary.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"automated_status": report["automated_status"],
                      "checks": len(report["checks"]), "failures": report["failures"],
                      "warnings": report["warnings"], "report": str(output)}, ensure_ascii=False, indent=2))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
