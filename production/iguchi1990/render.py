#!/usr/bin/env python3
"""Render the 180-second Iguchi Mariko film from SHA-verified Agnes clips and VO.

Sound is deliberately built from non-tonal, shot-specific environmental noise and
foley only. This module never loads, creates, or mixes music.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from production.iguchi1990.generate import request_hash  # noqa: E402

FPS = 24
RATE = 48_000
DURATION = 180
TOTAL_FRAMES = FPS * DURATION
TOTAL_SAMPLES = RATE * DURATION
SILENT_TAIL_SECONDS = 1.0
TITLE_FILE = "井口真理子命案_她没能回家_三分钟_1080p24.mp4"

# These small masks are bound to the exact reviewed source bytes. If a clip changes,
# rendering fails closed until a reviewer recalibrates its mask.
BLUR_MASKS = {
    "S04": {"sha256": "e00597e806875df166d07a687e7d258e70aa9a6ca5d6abb1cbdc490e6d9f62ee",
            "boxes": [(0, 0, 420, 245), (760, 0, 420, 205), (1510, 0, 410, 260)]},
    "S05": {"sha256": "412df7243452f19e13b4f526d43e7162b51d195cf270c22e1d1a5ba6b8bf2a89",
            "boxes": [(0, 35, 440, 220), (760, 25, 390, 190), (1350, 570, 330, 220)]},
    "S06": {"sha256": "345523a4d40e899d004e8a6380bd0c96f20e0f5011d9542ea0cde8b7144d52e5",
            "boxes": [(690, 670, 520, 300, 3.0, 5.0)]},
    "S07": {"sha256": "67d1049c0c8cb53547b0afbe7ad39ad07f980cb6f740ec6f32ddf2e098bd6305",
            "boxes": [(80, 55, 500, 260)]},
    "S08": {"sha256": "cb9347dd379ab032d9b53d1313d08b321620070845f42b231596515f97315754",
            "boxes": [(1060, 545, 600, 470, 0.0, 3.5), (1060, 420, 600, 550, 3.5, 7.0)]},
    "S09": {"sha256": "dd4464270bdce60836612ca33d4eecb572625704b6ca2ea4f5626bac0ee42e09",
            "boxes": [(620, 50, 1220, 220, 0.0, 0.55), (620, 340, 1220, 170, 0.0, 0.55),
                      (720, 50, 1120, 220, 0.55, 1.05), (720, 340, 1120, 170, 0.55, 1.05),
                      (1150, 50, 690, 220, 1.05, 1.55), (1150, 340, 690, 170, 1.05, 1.55),
                      (620, 50, 480, 220, 1.55, 2.2), (1500, 50, 340, 220, 1.55, 2.2),
                      (620, 340, 480, 170, 1.55, 2.2),
                      (620, 50, 680, 220, 2.2, 2.7), (620, 340, 680, 170, 2.2, 2.7),
                      (620, 50, 780, 220, 2.7, 3.0), (620, 340, 780, 170, 2.7, 3.0),
                      (620, 50, 1220, 220, 3.0, 6.0), (620, 340, 1220, 170, 3.0, 6.0),
                      (800, 500, 420, 150, 3.0, 6.0)]},
    "S10": {"sha256": "680dade4a5368f9ded6273ed3e6a78f9e4b365c8b8fe0a6553f04d67b1fedec0",
            "boxes": [(330, 350, 1250, 620)]},
    "S12": {"sha256": "3b8a0564227d4d21c8870c2e57c606c12e7f30924556954b952c109187565ce7",
            "boxes": [(1110, 30, 650, 280)]},
    "S13": {"sha256": "5100b577b693c804eb0a47e4cf9f0a80e9642e4ff20f13c46bb8ea4f15400823",
            "boxes": [(1340, 80, 150, 180), (690, 0, 610, 160)]},
    "S15": {"sha256": "9c20f9727b6b55b1d709839ce9214503b6772c144db9632cfec598ee98b5fb4d",
            "boxes": [(1170, 660, 390, 220), (1430, 65, 170, 160)]},
    "S16": {"sha256": "d9deb03af992c23ad952dc885950e2a698cf56dd2a8b01e00dde7f673ece28c0",
            "boxes": [(920, 610, 430, 330)]},
    "S29": {"sha256": "0a925babb3abbad15a23d618d104bdde30fcff3d289385d7963a0b01a8243d3e",
            "boxes": [(720, 70, 640, 210)]},
}

# Short, non-musical environmental beds. All material is synthesized from filtered
# aperiodic noise plus sparse irregular transients; there are no notes, chords or loops.
SOUND_PROFILES = {
    "S01": ("station", "steps"), "S02": ("rain", "rain"),
    "S03": ("terminal", "steps"), "S04": ("market", "rustle"),
    "S05": ("street", "traffic"), "S06": ("room", "paper"),
    "S07": ("train", "train_clicks"), "S08": ("train", "train_clicks"),
    "S09": ("station", "traffic"), "S10": ("quiet_terminal", "paper"),
    "S11": ("terminal", "steps"), "S12": ("office", "paper"),
    "S13": ("office", "paper"), "S14": ("night_field", "steps"),
    "S15": ("night_street", "rain"), "S16": ("station", "steps"),
    "S17": ("lake", "wind"), "S18": ("night_house", "wind"),
    "S19": ("room", "rustle"), "S20": ("taxi", "traffic"),
    "S21": ("night_street", "wind"), "S22": ("office", "paper"),
    "S23": ("interview", "paper"), "S24": ("police_car", "rain"),
    "S25": ("interview", "room"), "S26": ("field", "soil"),
    "S27": ("room", "rustle"), "S28": ("landfill", "machinery"),
    "S29": ("terminal", "steps"), "S30": ("room", "wind"),
}

PROFILE_CUTOFFS = {
    "station": (120.0, 5600.0), "terminal": (140.0, 5200.0),
    "quiet_terminal": (100.0, 4200.0), "market": (190.0, 7200.0),
    "street": (90.0, 3600.0), "rain": (260.0, 9000.0),
    "room": (100.0, 4200.0), "office": (110.0, 4800.0),
    "train": (38.0, 2400.0), "night_field": (75.0, 3400.0),
    "night_street": (65.0, 3300.0), "lake": (80.0, 3000.0),
    "night_house": (65.0, 2600.0), "taxi": (48.0, 2800.0),
    "interview": (90.0, 3100.0), "police_car": (50.0, 2700.0),
    "field": (70.0, 2900.0), "landfill": (40.0, 2300.0),
}


def run(command: list[str], capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run([str(part) for part in command], check=True,
                          capture_output=capture, text=capture)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)
    ], text=True))


def decoded_frame_count(path: Path) -> int:
    data = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=nb_read_frames", "-of", "json", str(path),
    ], text=True))
    streams = data.get("streams", [])
    if not streams or not streams[0].get("nb_read_frames"):
        raise RuntimeError(f"Could not count decoded video frames in {path}")
    return int(streams[0]["nb_read_frames"])


def _rate(value: str | None) -> float:
    if not value:
        return 0.0
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    return float(value)


def validate_source_motion(sid: str, video: dict, decoded_frames: int, target_duration: float) -> int:
    target_frames = round(target_duration * FPS)
    duration = float(video.get("duration") or 0.0)
    if duration + 0.001 < target_duration:
        raise RuntimeError(f"{sid}: source is shorter than its target shot; refusing frame padding")
    if _rate(video.get("avg_frame_rate")) + 0.001 < FPS:
        raise RuntimeError(f"{sid}: source cadence is below 24 fps; refusing frame duplication")
    if decoded_frames < target_frames:
        raise RuntimeError(
            f"{sid}: only {decoded_frames} decoded moving frames for a {target_frames}-frame shot; "
            "refusing to freeze or pad"
        )
    return target_frames


def media_summary(path: Path) -> dict:
    data = probe(path)
    video = next((row for row in data.get("streams", []) if row.get("codec_type") == "video"), None)
    audio = next((row for row in data.get("streams", []) if row.get("codec_type") == "audio"), None)
    if video is None:
        raise RuntimeError(f"No video stream: {path}")
    result = {
        "duration_seconds": float(data["format"]["duration"]), "bytes": path.stat().st_size,
        "width": int(video["width"]), "height": int(video["height"]),
        "fps": video.get("avg_frame_rate"), "frames": int(video.get("nb_frames") or 0),
        "video_codec": video.get("codec_name"),
    }
    if audio:
        result.update(audio_codec=audio.get("codec_name"),
                      sample_rate=int(audio.get("sample_rate", 0)),
                      audio_channels=int(audio.get("channels", 0)),
                      audio_bitrate=int(audio.get("bit_rate") or 0))
    return result


def validate_timeline(story: dict) -> None:
    shots = story.get("shots", [])
    if len(shots) != 30 or [shot["id"] for shot in shots] != [f"S{i:02d}" for i in range(1, 31)]:
        raise ValueError("Expected exactly S01–S30 in order")
    cursor = 0
    for shot in shots:
        if int(shot["start"]) != cursor or int(shot["duration"]) <= 0:
            raise ValueError(f"Non-contiguous shot timeline at {shot['id']}")
        if shot.get("kind") != "agnes" or shot.get("seconds") != shot["duration"]:
            raise ValueError(f"Non-Agnes or mismatched target duration in {shot['id']}")
        cursor += int(shot["duration"])
    if cursor != DURATION or story.get("target_duration") != DURATION:
        raise ValueError(f"Expected a contiguous {DURATION}-second timeline, got {cursor}")
    if (story.get("width"), story.get("height"), story.get("fps")) != (1920, 1080, FPS):
        raise ValueError("Storyboard delivery spec must be 1920x1080 at 24 fps")


def verify_sources(story: dict, sources: Path) -> dict:
    results_path = HERE / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    if results.get("model") != "agnes-video-2.5-flash" or results.get("source_size") != "720P":
        raise RuntimeError("Only SHA-receipted Agnes Video 2.5 Flash 720P footage is accepted")
    rows = results.get("shots", {})
    verified = {}
    for shot in story["shots"]:
        sid = shot["id"]
        record = rows.get(sid, {})
        source = sources / f"{sid}.mp4"
        if record.get("status") != "completed" or not source.is_file():
            raise RuntimeError(f"Missing completed dynamic source {sid}; no still-image fallback is allowed")
        if record.get("request_hash") != request_hash(story, shot):
            raise RuntimeError(f"Prompt/provenance hash mismatch for {sid}")
        if record.get("sha256") != sha256(source) or int(record.get("bytes", -1)) != source.stat().st_size:
            raise RuntimeError(f"Source hash/byte receipt mismatch for {sid}")
        info = probe(source)
        stream = next((row for row in info.get("streams", []) if row.get("codec_type") == "video"), None)
        if not stream or int(stream["width"]) != 1280 or int(stream["height"]) != 720:
            raise RuntimeError(f"Unexpected source dimensions for {sid}; expected 1280x720")
        source_video = {**stream, "duration": stream.get("duration") or info["format"]["duration"]}
        decoded_frames = decoded_frame_count(source)
        validate_source_motion(sid, source_video, decoded_frames, float(shot["duration"]))
        verified[sid] = {**record, "decoded_frames_verified": decoded_frames}
    return verified


def _frame_png(source: Path, timestamp: float) -> Image.Image:
    payload = subprocess.check_output([
        "ffmpeg", "-v", "error", "-ss", f"{max(0.0, timestamp):.3f}", "-i", str(source),
        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1",
    ])
    from io import BytesIO
    with Image.open(BytesIO(payload)) as image:
        return image.convert("RGB")


def _dark_edge_run(gray: np.ndarray, reverse: bool, axis: int, limit: int) -> int:
    length = gray.shape[axis]
    count = 0
    for offset in range(min(limit, length)):
        index = length - 1 - offset if reverse else offset
        band = gray[:, index] if axis == 1 else gray[index, :]
        mean, spread, dark_fraction = float(np.mean(band)), float(np.std(band)), float(np.mean(band < 20))
        strict_black = mean < 12 and spread < 8 and dark_fraction > 0.985
        # Generated letterbox edges can contain a few compression/lighting specks.
        # Tolerate only the first six edge rows, then require a strict black run.
        edge_noise = offset < 6 and mean < 12 and spread < 16 and dark_fraction > 0.80
        if strict_black or edge_noise:
            count += 1
        else:
            break
    return count


def detect_paired_mattes(source: Path, shot: dict, info: dict) -> dict | None:
    """Detect persistent embedded black bars only in the two manually flagged clips."""
    sid = shot["id"]
    if sid not in {"S08", "S28"}:
        return None
    duration = float(info["duration_seconds"])
    reports = []
    for fraction in (0.16, 0.50, 0.84):
        image = _frame_png(source, min(duration - 0.06, max(0.04, duration * fraction))).resize((640, 360))
        gray = np.asarray(image.convert("L"), dtype=np.uint8)
        h, w = gray.shape
        if sid == "S08":
            top = _dark_edge_run(gray, False, axis=0, limit=int(h * 0.22))
            bottom = _dark_edge_run(gray, True, axis=0, limit=int(h * 0.22))
            candidate = {"axis": "horizontal", "first": top, "last": bottom}
        else:
            left = _dark_edge_run(gray, False, axis=1, limit=int(w * 0.30))
            right = _dark_edge_run(gray, True, axis=1, limit=int(w * 0.30))
            candidate = {"axis": "vertical", "first": left, "last": right}
        min_band = 10
        if candidate["first"] >= min_band and candidate["last"] >= min_band:
            reports.append(candidate)
    if len(reports) < 2:
        return None
    first = int(round(float(np.median([row["first"] for row in reports])) * info["height"] / 360))
    last = int(round(float(np.median([row["last"] for row in reports])) * info["width"] / 640)) if sid == "S28" else int(round(float(np.median([row["last"] for row in reports])) * info["height"] / 360))
    # Crop two pixels into the active image to avoid retaining a thin compression halo.
    return {"axis": reports[0]["axis"], "first": max(0, first + 2), "last": max(0, last + 2),
            "samples": len(reports)}


def _crop_values(info: dict, mattes: dict | None) -> tuple[int, int, int, int]:
    width, height = int(info["width"]), int(info["height"])
    if not mattes:
        return width, height, 0, 0
    if mattes["axis"] == "horizontal":
        top, bottom = int(mattes["first"]), int(mattes["last"])
        active_h = (height - top - bottom) // 2 * 2
        return width // 2 * 2, active_h, 0, top // 2 * 2
    left, right = int(mattes["first"]), int(mattes["last"])
    active_w = (width - left - right) // 2 * 2
    return active_w, height // 2 * 2, left // 2 * 2, 0


def _blur_spec(sid: str, source_sha: str) -> list[tuple[int, int, int, int, float, float]]:
    spec = BLUR_MASKS.get(sid)
    if not spec:
        return []
    if spec["sha256"] != source_sha:
        raise RuntimeError(f"{sid}: source changed since blur mask review; re-review before rendering")
    result = []
    for row in spec["boxes"]:
        if len(row) == 4:
            x, y, w, h = row
            start, end = 0.0, 1e6
        else:
            x, y, w, h, start, end = row
        x, y = max(0, int(x)) // 2 * 2, max(0, int(y)) // 2 * 2
        w, h = int(w) // 2 * 2, int(h) // 2 * 2
        if x + w > 1920 or y + h > 1080 or min(w, h) < 64:
            raise ValueError(f"Invalid blur box for {sid}: {(x,y,w,h)}")
        result.append((x, y, w, h, float(start), float(end)))
    return result


def _normalized_graph(shot: dict, info: dict, mattes: dict | None, masks: list[tuple]) -> tuple[str, str]:
    width, height, left, top = _crop_values(info, mattes)
    sid = shot["id"]
    if mattes and sid == "S28":
        ratio = width / height
        if ratio > 16 / 9:
            front_w, front_h = 1920, int(1920 / ratio) // 2 * 2
        else:
            front_h, front_w = 1080, int(1080 * ratio) // 2 * 2
        base = (f"crop={width}:{height}:{left}:{top},split=2[fgsrc][bgsrc];"
                f"[bgsrc]scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,"
                "crop=1920:1080,boxblur=32:12,eq=brightness=-0.16:saturation=0.78[bg];"
                f"[fgsrc]scale={front_w}:{front_h}:flags=lanczos[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2[filled]")
        current = "filled"
    else:
        base = (f"crop={width}:{height}:{left}:{top},"
                "scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,"
                "crop=1920:1080:(iw-1920)/2:(ih-1080)/2,setsar=1,"
                "eq=gamma=1.02:contrast=1.01:saturation=0.98[base]")
        current = "base"
    graph = f"[0:v]{base};"
    for index, (x, y, w, h, start, end) in enumerate(masks):
        graph += f"[{current}]split=2[main{index}][copy{index}];"
        graph += (f"[copy{index}]crop={w}:{h}:{x}:{y},"
                  f"boxblur=22:2[soft{index}];")
        graph += (f"[main{index}][soft{index}]overlay={x}:{y}:"
                  f"enable='between(t,{start:.3f},{end:.3f})'[layer{index}];")
        current = f"layer{index}"
    final_filters = "fps=24,setsar=1,format=yuv420p"
    if sid == "S30":
        final_filters += f",fade=t=out:st={float(shot['duration'])-1:.3f}:d=1"
    graph += f"[{current}]{final_filters}[outv]"
    return graph, "outv"


def normalize_clip(source: Path, target: Path, shot: dict, receipt: dict) -> dict:
    info = probe(source)
    video = next((row for row in info.get("streams", []) if row.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError(f"{shot['id']}: source has no video stream")
    width, height = int(video["width"]), int(video["height"])
    video = {**video, "duration": video.get("duration") or info["format"]["duration"]}
    duration = float(video["duration"])
    if width != 1280 or height != 720:
        raise RuntimeError(f"{shot['id']}: expected 1280x720, received {width}x{height}")
    target_duration = float(shot["duration"])
    target_frames = validate_source_motion(
        shot["id"], video, int(receipt.get("decoded_frames_verified", 0)), target_duration
    )
    source_sha = sha256(source)
    if receipt.get("sha256") != source_sha:
        raise RuntimeError(f"{shot['id']}: source SHA-256 changed between receipt and normalization")
    mattes = detect_paired_mattes(source, shot, {"duration_seconds": duration, "width": width, "height": height})
    if shot["id"] in {"S08", "S28"} and not mattes:
        raise RuntimeError(f"{shot['id']}: expected embedded black bars were not verified; review before rendering")
    masks = _blur_spec(shot["id"], source_sha)
    graph, label = _normalized_graph(shot, {"width": width, "height": height}, mattes, masks)
    frames = round(target_duration * FPS)
    target.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", source,
        "-filter_complex", graph, "-map", f"[{label}]", "-an",
        "-frames:v", str(frames), "-r", str(FPS), "-fps_mode", "cfr",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", target,
    ])
    result = media_summary(target)
    if result["frames"] != frames or result["width"] != 1920 or result["height"] != 1080:
        raise RuntimeError(f"{shot['id']}: normalized clip failed exact frame/size QC: {result}")
    return {
        "id": shot["id"], "source_sha256": source_sha, "source_duration_seconds": round(duration, 3),
        "target_duration_seconds": target_duration, "target_frames": frames,
        "blur_mask_count": len(masks), "embedded_mattes": mattes,
        "normalized_duration_seconds": result["duration_seconds"],
    }


def _decode_mp3(path: Path, tempo: float = 1.0) -> np.ndarray:
    filters = []
    if abs(tempo - 1.0) > 0.0001:
        filters.append(f"atempo={tempo:.6f}")
    filters.append("aresample=48000")
    command = ["ffmpeg", "-v", "error", "-i", str(path), "-af", ",".join(filters),
               "-ac", "2", "-ar", str(RATE), "-f", "f32le", "pipe:1"]
    raw = subprocess.check_output(command)
    if len(raw) % (4 * 2):
        raise RuntimeError(f"Decoded narration has malformed stereo samples: {path.name}")
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()


def _active_bounds(samples: np.ndarray) -> tuple[int, int]:
    if samples.size == 0:
        raise ValueError("Empty TTS audio")
    mono = np.mean(samples, axis=1)
    hop = RATE // 100
    usable = len(mono) // hop * hop
    if usable == 0:
        raise ValueError("TTS clip is shorter than 10 ms")
    rms = np.sqrt(np.mean(mono[:usable].reshape(-1, hop) ** 2, axis=1))
    threshold = max(0.0025, float(rms.max()) * 0.035)
    active = np.flatnonzero(rms >= threshold)
    if not len(active):
        raise RuntimeError("TTS clip has no detectable voice activity")
    start = max(0, int(active[0]) * hop - int(0.04 * RATE))
    end = min(len(samples), (int(active[-1]) + 1) * hop + int(0.07 * RATE))
    return start, end


def _shape_noise(length: int, rng: np.random.Generator, low: float, high: float) -> np.ndarray:
    white = rng.standard_normal(length).astype(np.float32)
    spectrum = np.fft.rfft(white)
    hz = np.fft.rfftfreq(length, 1 / RATE)
    # Smooth aperiodic band-limited noise. No oscillator, note, chord or musical loop is used.
    low_pass = 1.0 / np.sqrt(1.0 + (hz / max(high, 1.0)) ** 6)
    high_pass = (hz / max(low, 1.0)) / np.sqrt(1.0 + (hz / max(low, 1.0)) ** 2)
    pink = 1.0 / np.sqrt(np.maximum(hz, 30.0))
    spectrum *= (low_pass * high_pass * pink)
    shaped = np.fft.irfft(spectrum, n=length).astype(np.float32)
    rms = float(np.sqrt(np.mean(shaped * shaped))) if length else 0.0
    if rms > 1e-8:
        shaped /= rms
    return shaped


def _transient_kind(kind: str, duration: float, rng: np.random.Generator) -> list[tuple[float, float, float]]:
    count_by_kind = {
        "steps": 5, "rain": 7, "traffic": 3, "rustle": 3, "paper": 3,
        "train_clicks": 8, "wind": 2, "soil": 3, "machinery": 3, "room": 1,
    }
    count = count_by_kind.get(kind, 0)
    if duration < 1.0 or count == 0:
        return []
    # Irregular timing is intentional: it should resemble incidental foley, not a beat.
    times = sorted(rng.uniform(0.3, max(0.31, duration - 0.28), size=count).tolist())
    return [(at, float(rng.uniform(0.045, 0.18)), float(rng.uniform(0.35, 1.0))) for at in times]


def synthesize_ambience(story: dict, work_dir: Path) -> tuple[np.ndarray, dict]:
    rng = np.random.default_rng(19900407)
    stereo = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    reports = []
    for shot in story["shots"]:
        sid = shot["id"]
        profile, event_kind = SOUND_PROFILES[sid]
        low, high = PROFILE_CUTOFFS[profile]
        seconds = float(shot["duration"])
        count = round(seconds * RATE)
        left = _shape_noise(count, rng, low, high)
        right = _shape_noise(count, rng, low, high)
        # Low-level diegetic atmosphere (-36 dBFS RMS) under the narration.
        segment = np.column_stack((left, right)) * 0.016
        events = _transient_kind(event_kind, seconds, rng)
        for at, span, strength in events:
            start = round(at * RATE)
            size = min(round(span * RATE), count - start)
            if size <= 0:
                continue
            texture = _shape_noise(size, rng, max(low, 250.0), min(high, 10_000.0))
            envelope = np.exp(-np.linspace(0.0, 4.2, size, dtype=np.float32))
            amplitude = 0.018 * strength
            pan = float(rng.uniform(-0.18, 0.18))
            segment[start:start + size, 0] += texture * envelope * amplitude * (1.0 - pan)
            segment[start:start + size, 1] += texture * envelope * amplitude * (1.0 + pan)
        edge = min(round(0.035 * RATE), count // 2)
        if edge:
            ramp = np.linspace(0.0, 1.0, edge, dtype=np.float32)
            segment[:edge] *= ramp[:, None]
            segment[-edge:] *= ramp[::-1, None]
        start_sample = int(shot["start"] * RATE)
        stereo[start_sample:start_sample + count] += segment
        reports.append({"shot_id": sid, "profile": profile, "foley_kind": event_kind,
                        "aperiodic_transient_count": len(events), "music": False})
    # The closing second is absolute digital silence: no voice, ambience or foley.
    stereo[-RATE:, :] = 0
    report = {
        "sample_rate": RATE, "channels": 2, "duration_seconds": DURATION,
        "design": "shot-specific filtered aperiodic environmental noise and sparse irregular foley only",
        "music": False, "melodic_bed": False, "shots": reports,
    }
    return stereo, report


def write_wav(path: Path, audio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(audio, -0.98, 0.98)
    pcm = np.round(clipped * 32767).astype("<i2")
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(pcm.tobytes())


def build_voice(story: dict, audio_dir: Path, work_dir: Path) -> tuple[np.ndarray, list[dict], dict]:
    manifest = json.loads((audio_dir / "manifest.json").read_text(encoding="utf-8"))
    voice_id = story.get("narration_spec", {}).get("voice_id")
    if not voice_id or manifest.get("voice_id") != voice_id:
        raise RuntimeError("Narration manifest does not use the selected voice")
    rows = {row["id"]: row for row in manifest.get("clips", [])}
    if set(rows) != {shot["id"] for shot in story["shots"]}:
        raise RuntimeError("Expected exactly one TTS clip for each of the 30 shots")
    max_speedup = min(float(story["narration_spec"].get("max_speedup_factor", 1.15)), 1.15)
    voice = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    captions, timings = [], []
    work_audio = work_dir / "audio"
    work_audio.mkdir(parents=True, exist_ok=True)

    for shot in story["shots"]:
        sid = shot["id"]
        record = rows[sid]
        if (record.get("text") != shot["narration"] or record.get("voice_id") != voice_id
                or record.get("target_start") != shot["start"]
                or record.get("target_duration") != shot["duration"]
                or record.get("alignment") != "shot-locked"):
            raise RuntimeError(f"TTS text/voice/timing mismatch for {sid}")
        audio_path = audio_dir / record["file"]
        if not audio_path.is_file() or record.get("status") != "ready":
            raise RuntimeError(f"Missing selected-voice audio clip {sid}")
        audio_sha = sha256(audio_path)
        if record.get("sha256") != audio_sha:
            raise RuntimeError(f"TTS SHA-256 mismatch for {sid}")
        samples = _decode_mp3(audio_path)
        start, end = _active_bounds(samples)
        trimmed = samples[start:end]
        shot_start = int(shot["start"] * RATE)
        shot_end = int((shot["start"] + shot["duration"]) * RATE)
        safe_end = min(shot_end - int(0.12 * RATE), TOTAL_SAMPLES - RATE)
        clip_start = shot_start + int(0.12 * RATE)
        available = safe_end - clip_start
        tempo = 1.0
        if len(trimmed) > available:
            required = len(trimmed) / max(1, available)
            if required > max_speedup + 0.005:
                # Do not cut syllables or force unnatural speed: revise the line instead.
                raise RuntimeError(f"{sid}: TTS takes {len(trimmed)/RATE:.2f}s, exceeds its {available/RATE:.2f}s shot window")
            tempo = min(max_speedup, required * 1.005)
            samples = _decode_mp3(audio_path, tempo)
            start, end = _active_bounds(samples)
            trimmed = samples[start:end]
        if len(trimmed) > available:
            raise RuntimeError(f"{sid}: complete narration still crosses the shot boundary")

        active_mono = np.mean(trimmed, axis=1)
        rms = float(np.sqrt(np.mean(active_mono * active_mono)))
        if rms < 1e-7:
            raise RuntimeError(f"{sid}: narration has near-zero level")
        gain = min(1.8, max(0.65, 0.115 / rms))
        trimmed *= gain
        peak = float(np.max(np.abs(trimmed)))
        if peak > 0.82:
            trimmed *= 0.82 / peak
        fade = min(round(0.012 * RATE), len(trimmed) // 2)
        if fade > 0:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            trimmed[:fade] *= ramp[:, None]
            trimmed[-fade:] *= ramp[::-1, None]
        clip_end = clip_start + len(trimmed)
        voice[clip_start:clip_end] += trimmed

        active_seconds = len(trimmed) / RATE
        # _active_bounds keeps 40 ms of leading and 70 ms of trailing room tone.
        # The cue omits that padding and therefore follows the audible sentence itself.
        speech_start = clip_start / RATE + min(0.04, active_seconds / 4)
        speech_end = clip_start / RATE + max(0.0, active_seconds - 0.07)
        cue = {"shot_id": sid, "start": round(speech_start, 3),
               "end": round(speech_end, 3), "text": shot["narration"]}
        if captions and cue["start"] < captions[-1]["end"]:
            raise RuntimeError(f"Subtitle overlap at {sid}")
        captions.append(cue)
        timings.append({"shot_id": sid, "target_start": shot["start"], "target_duration": shot["duration"],
                        "source_sha256": audio_sha, "decoded_seconds": round(len(samples) / RATE, 3),
                        "speech_seconds": round(active_seconds, 3), "start_seconds": cue["start"],
                        "end_seconds": cue["end"], "tempo_factor": round(tempo, 4),
                        "rms_gain": round(gain, 4), "characters": len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", shot["narration"]))})

    return voice, captions, {
        "voice_id": voice_id, "alignment": "one sentence, one TTS file, one shot, one subtitle cue",
        "sample_rate": RATE, "channels": 2, "duration_seconds": DURATION,
        "max_speedup_factor": max_speedup, "shots": timings,
        "silent_tail_seconds": SILENT_TAIL_SECONDS, "music": False,
    }


def _ass_clock(seconds: float) -> str:
    centis = int(round(seconds * 100))
    hours, centis = divmod(centis, 360000)
    minutes, centis = divmod(centis, 6000)
    secs, centis = divmod(centis, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _srt_clock(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _escape_ass(text: str) -> str:
    return text.replace("\\", "/").replace("{", "（").replace("}", "）").replace("\n", " ")


def split_subtitle(text: str, limit: int = 24) -> list[str]:
    text = text.strip()
    if limit < 1 or not text:
        raise ValueError("Subtitle text and line limit must be non-empty")
    lines = []
    remaining = text
    punctuation = "，；：、。？！,;: "
    while len(remaining) > limit:
        floor = max(1, int(limit * 0.55))
        breaks = [index + 1 for index, char in enumerate(remaining[:limit])
                  if floor <= index + 1 <= limit and char in punctuation]
        # Prefer a natural pause, but never let a line exceed the mobile-safe width.
        split_at = max(breaks) if breaks else limit
        lines.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        lines.append(remaining)
    if any(len(line) > limit for line in lines):
        raise ValueError(f"Cannot safely wrap caption: {text!r}")
    return lines


def highlight_line(text: str, phrases: list[str]) -> str:
    ordered = sorted((phrase for phrase in phrases if phrase), key=len, reverse=True)
    out = []
    index = 0
    while index < len(text):
        hit = next((phrase for phrase in ordered if text.startswith(phrase, index)), None)
        if hit:
            out.append(r"{\c&H005FC9F4&\fs66\b1}" + hit + r"{\rCaption}")
            index += len(hit)
        else:
            out.append(_escape_ass(text[index]))
            index += 1
    return "".join(out)


def write_subtitles(ass_path: Path, srt_path: Path, captions: list[dict], story: dict) -> None:
    phrases = story["presentation"].get("highlight_keywords", [])
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,Noto Sans CJK SC,58,&H00FFFFFF,&H0000FFFF,&H00000000,&H7F000000,1,0,0,0,100,100,0,0,1,3.4,1.0,2,120,120,76,1",
        "Style: Title,Noto Sans CJK SC,88,&H005FC9F4,&H0000FFFF,&H0013110D,&H99000000,1,0,0,0,100,100,1,0,1,5,2,7,100,100,0,1",
        "Style: Small,Noto Sans CJK SC,25,&H00F0F0F0,&H0000FFFF,&H00000000,&H7F000000,0,0,0,0,100,100,0,0,1,2.5,0.8,9,48,48,38,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    # A concise title over the moving opening image, plus a persistent honesty label.
    lines.append(f"Dialogue: 2,0:00:00.20,0:00:03.50,Title,,0,0,0,,{{\\fad(220,350)}}井口真理子命案\\N{{\\fs48\\c&H00FFFFFF&}}她没能回家 · 案件回顾")
    lines.append(f"Dialogue: 3,0:00:00.00,{_ass_clock(DURATION-SILENT_TAIL_SECONDS)},Small,,0,0,0,,{{\\alpha&H35&}}AI情景复原 · 非真实影像")
    for cue in captions:
        rendered = r"\N".join(highlight_line(part, phrases) for part in split_subtitle(cue["text"]))
        lines.append(f"Dialogue: 1,{_ass_clock(cue['start'])},{_ass_clock(cue['end'])},Caption,,0,0,0,,{{\\fad(60,70)\\q2}}{rendered}")
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    srt = ["1\n00:00:00,000 --> 00:00:03,500\n【AI情景复原，非真实影像】井口真理子命案：她没能回家\n"]
    for index, cue in enumerate(captions, 2):
        body = "\n".join(split_subtitle(cue["text"]))
        srt.append(f"{index}\n{_srt_clock(cue['start'])} --> {_srt_clock(cue['end'])}\n{body}\n")
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text("\n".join(srt), encoding="utf-8")


def find_cjk_font() -> Path:
    candidates = [Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
                  Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc")]
    for root in (Path("/usr/share/fonts"), Path.home() / ".fonts"):
        if root.exists():
            candidates.extend(root.glob("**/NotoSansCJK*"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("Noto CJK font is required for visual QA contact sheets")


def write_timeline_contact_sheet(video: Path, story: dict, target: Path) -> None:
    font_path = find_cjk_font()
    font = ImageFont.truetype(str(font_path), 18)
    tile_w, tile_h, columns = 320, 180, 6
    rows = math.ceil(len(story["shots"]) / columns)
    sheet = Image.new("RGB", (tile_w * columns, tile_h * rows), (10, 14, 20))
    draw = ImageDraw.Draw(sheet)
    for index, shot in enumerate(story["shots"]):
        timestamp = float(shot["start"]) + float(shot["duration"]) * 0.5
        image = _frame_png(video, timestamp).resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        x, y = (index % columns) * tile_w, (index // columns) * tile_h
        sheet.paste(image, (x, y))
        draw.rectangle((x, y, x + 60, y + 27), fill=(0, 0, 0))
        draw.text((x + 7, y + 3), shot["id"], fill=(255, 230, 150), font=font)
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, quality=90, subsampling=0)


def _wav_float(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as stream:
        if stream.getnchannels() != 2 or stream.getframerate() != RATE or stream.getsampwidth() != 2:
            raise RuntimeError("Intermediate mix must be 48 kHz stereo PCM16")
        raw = stream.readframes(stream.getnframes())
    return np.frombuffer(raw, dtype="<i2").reshape(-1, 2).astype(np.float32) / 32768.0


def verify_encoded_silent_tail(path: Path) -> dict:
    raw = subprocess.check_output([
        "ffmpeg", "-v", "error", "-sseof", "-1", "-i", str(path), "-vn", "-ac", "2",
        "-ar", str(RATE), "-t", "1", "-f", "f32le", "pipe:1",
    ])
    samples = np.frombuffer(raw, dtype="<f4").reshape(-1, 2)
    if len(samples) < RATE * 0.9:
        raise RuntimeError("Could not decode at least 0.9 seconds of the final audio tail")
    rms = float(np.sqrt(np.mean(samples * samples)))
    peak = float(np.max(np.abs(samples)))
    if rms > 0.001 or peak > 0.01:
        raise RuntimeError(f"Encoded final second is not silent enough (RMS {rms:.6f}, peak {peak:.6f})")
    return {"decoded_seconds": round(len(samples) / RATE, 3), "rms": round(rms, 7),
            "peak": round(peak, 7), "rms_limit": 0.001, "peak_limit": 0.01}


def render(sources: Path, work: Path, output: Path) -> dict:
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    validate_timeline(story)
    receipts = verify_sources(story, sources)
    work.mkdir(parents=True, exist_ok=True)
    normalized_dir = work / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    clip_reports = []
    list_file = work / "clips.ffconcat"
    entries = ["ffconcat version 1.0"]
    for shot in story["shots"]:
        source = sources / f"{shot['id']}.mp4"
        normalized = normalized_dir / f"{shot['id']}.mp4"
        clip_reports.append(normalize_clip(source, normalized, shot, receipts[shot["id"]]))
        entries.append("file '" + str(normalized.resolve()).replace("'", "'\\''") + "'")
    list_file.write_text("\n".join(entries) + "\n", encoding="utf-8")

    voice, captions, voice_report = build_voice(story, HERE / "audio", work)
    ambience, sfx_report = synthesize_ambience(story, work)
    mix = voice + ambience
    mix[-RATE:, :] = 0
    pre_limit_peak = float(np.max(np.abs(mix)))
    if pre_limit_peak > 0.95:
        mix *= 0.95 / pre_limit_peak
    peak = float(np.max(np.abs(mix)))
    mix_path = work / "final-mix.wav"
    write_wav(mix_path, mix)
    if np.max(np.abs(mix[-RATE:, :])) != 0:
        raise RuntimeError("The final second of the mix is not digitally silent")
    mix_info = {"duration_seconds": DURATION, "sample_rate": RATE, "channels": 2,
                "peak": round(peak, 5), "pre_limiter_peak": round(pre_limit_peak, 5), "music": False}
    sfx_report["integrated_mix"] = mix_info
    sfx_report["voiceover"] = voice_report

    output.parent.mkdir(parents=True, exist_ok=True)
    ass_path = output.with_suffix(".ass")
    srt_path = output.with_suffix(".srt")
    write_subtitles(ass_path, srt_path, captions, story)
    fonts_dir = "/usr/share/fonts/opentype/noto"
    run([
        "ffmpeg", "-y", "-v", "error", "-threads", "2", "-f", "concat", "-safe", "0",
        "-i", list_file, "-i", mix_path,
        "-vf", f"ass={ass_path.as_posix()}:fontsdir={fonts_dir}",
        "-map", "0:v:0", "-map", "1:a:0", "-frames:v", str(TOTAL_FRAMES),
        "-r", str(FPS), "-fps_mode", "cfr", "-c:v", "libx264", "-preset", "medium",
        "-crf", "21", "-maxrate", "3000k", "-bufsize", "6000k", "-profile:v", "high",
        "-level", "4.1", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-ar", str(RATE), "-ac", "2", "-t", str(DURATION), "-movflags", "+faststart",
        "-metadata", "title=井口真理子命案：她没能回家",
        "-metadata", "comment=AI情景复原，非真实影像；案件回顾",
        output,
    ])
    summary = media_summary(output)
    encoded_tail = verify_encoded_silent_tail(output)
    if (summary["width"], summary["height"], summary["frames"]) != (1920, 1080, TOTAL_FRAMES):
        raise RuntimeError("Final video failed exact frame/size gate: " + json.dumps(summary))
    if abs(summary["duration_seconds"] - DURATION) > 0.03:
        raise RuntimeError("Final video is not exactly 180 seconds: " + str(summary["duration_seconds"]))
    if summary.get("sample_rate") != RATE or summary.get("audio_channels") != 2:
        raise RuntimeError("Final audio must be 48 kHz stereo")

    subtitle_cues = len(captions)
    timeline_path = HERE / "qa" / "final_timeline.jpg"
    write_timeline_contact_sheet(output, story, timeline_path)
    work_report = {
        "title": story["title"], "output": output.name,
        "human_visual_review": "pending_final_full-playback; 30 source contact sheets were reviewed",
        "source_model": "agnes-video-2.5-flash", "source_resolution": "1280x720",
        "delivery": summary, "total_frames_expected": TOTAL_FRAMES,
        "shots": clip_reports, "caption_cues": subtitle_cues,
        "voice_id": voice_report["voice_id"], "voice_report": voice_report,
        "sound_design": sfx_report, "encoded_tail_silence": encoded_tail,
        "music": False, "melodic_bed": False,
        "timeline_contact_sheet": str(timeline_path),
        "source_provenance": str(HERE / "results.json"),
        "policy": "Every source byte is checked against its receipt and each prompt hash against story.json. "
                  "Source excess is trimmed to the exact shot frame count; no still-frame padding or retiming. "
                  "Only shot-locked VO, aperiodic environmental ambience and irregular original foley are mixed. "
                  "The closing second is digitally silent.",
    }
    report_path = HERE / "qa" / "render_report.json"
    report_path.write_text(json.dumps(work_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "audio" / "render_audio_report.json").write_text(json.dumps(sfx_report, ensure_ascii=False, indent=2) + "\n",
                                                               encoding="utf-8")
    timing_path = HERE / "qa" / "narration_timing.json"
    timing_path.write_text(json.dumps(voice_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(work_report, ensure_ascii=False, indent=2))
    return work_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    render(args.sources, args.work, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
