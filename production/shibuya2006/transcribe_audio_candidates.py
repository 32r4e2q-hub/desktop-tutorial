#!/usr/bin/env python3
"""Independently transcribe narration candidates; never silently sign off alignment.

Why this decodes with ffmpeg instead of handing faster-whisper a file path
--------------------------------------------------------------------------
The 2026-11-16 run (43816706197) died on the very first clip with

    TypeError: open() got an unexpected keyword argument 'metadata_errors'

raised inside ``av.container.core.open``: the runner had resolved a PyAV build older
than the one faster-whisper passes ``metadata_errors`` to. That is a dependency
mismatch in the media environment, not a defect in the narration recordings, so the
fix is to take PyAV out of the audio path: ffmpeg decodes each clip to 16 kHz mono
float32 and the model is handed an in-memory array.

The evidence is unchanged and the policy is unchanged: transcription only, no speech
synthesis, no stand-in for missing audio, no automatic alignment sign-off. Missing or
moderation-blocked narration stays missing — it is reported as such.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SAMPLE_RATE = 16_000
DEFAULT_MODEL = os.environ.get("SHIBUYA_ASR_MODEL", "small")
MATCH_THRESHOLD = 0.90


def normalize(text: str) -> str:
    """Compare spoken characters, not punctuation or OpenCC's traditional forms."""
    try:
        from opencc import OpenCC
        text = OpenCC("t2s").convert(text)
    except ImportError:
        # OpenCC unavailable is not a reason to skip the check; it only folds 繁→简.
        pass
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", text).lower()


def ffmpeg_binary() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("ffmpeg not found on PATH; cannot decode narration for ASR")
    return binary


def ffprobe_binary() -> str | None:
    return shutil.which("ffprobe")


def decode_float32(path: Path, sample_rate: int = SAMPLE_RATE):
    """Decode any audio file to mono float32 PCM via ffmpeg (no PyAV in the way)."""
    import numpy as np

    command = [
        ffmpeg_binary(), "-nostdin", "-v", "error", "-i", str(path),
        "-vn", "-ac", "1", "-ar", str(sample_rate), "-f", "f32le", "-acodec", "pcm_f32le", "-",
    ]
    result = subprocess.run(command, capture_output=True)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()[-800:]
        raise RuntimeError(f"ffmpeg could not decode {path}: {detail}")
    samples = np.frombuffer(result.stdout, dtype="<f4")
    if samples.size == 0:
        raise RuntimeError(f"ffmpeg decoded no samples from {path}")
    return samples.astype(np.float32, copy=False)


def measured_seconds(path: Path) -> float | None:
    probe = ffprobe_binary()
    if not probe:
        return None
    result = subprocess.run([
        probe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(path),
    ], capture_output=True, text=True)
    try:
        return round(float(result.stdout.strip()), 3)
    except ValueError:
        return None


def load_model(model_size: str):
    cache = os.environ.get("WHISPER_CACHE_DIR")
    if cache:
        Path(cache).mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", cache)
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "15")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "90")
    from faster_whisper import WhisperModel
    kwargs = {"device": "cpu", "compute_type": "int8", "cpu_threads": 4}
    if cache:
        kwargs["download_root"] = cache
    return WhisperModel(model_size, **kwargs)


def transcribe_clip(model, path: Path, language: str) -> dict:
    import difflib

    samples = decode_float32(path)
    segments, info = model.transcribe(
        samples, language=language, beam_size=5, word_timestamps=True,
        vad_filter=False, condition_on_previous_text=False,
    )
    segments = list(segments)
    heard = "".join(segment.text for segment in segments).strip()
    words = [word for segment in segments for word in (segment.words or [])]
    first_word = round(words[0].start, 3) if words else None
    last_word = round(words[-1].end, 3) if words else None
    return {
        "asr_text": heard,
        "segments": [
            {"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text,
             "words": [{"start": round(w.start, 3), "end": round(w.end, 3),
                        "word": w.word, "probability": round(float(w.probability or 0), 4)}
                       for w in (s.words or [])]}
            for s in segments
        ],
        "first_word_start": first_word,
        "last_word_end": last_word,
        "decoded_seconds": round(len(samples) / SAMPLE_RATE, 3),
        "detected_language": getattr(info, "language", None),
    }


def candidate_index() -> dict:
    path = HERE / "qa/group-tts-split-candidates.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row for row in data.get("clips", [])}


def blocked_reasons() -> dict:
    """Map shot id -> why the source TTS never existed (moderation, script change)."""
    path = HERE / "audio/groups/manifest.json"
    if not path.is_file():
        return {}
    reasons = {}
    for group in json.loads(path.read_text(encoding="utf-8")).get("groups", []):
        if group.get("status") == "generated":
            continue
        for shot in group.get("shots", []):
            reasons[shot] = group.get("status", "unavailable")
    return reasons


def summarize(shot: dict, clip: dict, heard: str, source_seconds: float | None) -> dict:
    import difflib

    similarity = difflib.SequenceMatcher(
        None, normalize(shot["narration"]), normalize(heard)).ratio()
    target = float(shot["duration"])
    speech = clip["decoded_seconds"]
    if similarity >= MATCH_THRESHOLD:
        status = "asr_match_needs_review"
    else:
        status = "inspect_transcript_or_boundary"
    return {
        "similarity": round(similarity, 4),
        "status": status,
        "target_seconds": target,
        "speech_seconds": speech,
        "source_seconds": source_seconds,
        "atempo_needed": round(max(1.0, speech / target), 4),
        "tail_silence_seconds": round(max(0.0, target - speech), 3),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--limit", type=int, default=0, help="debug: only the first N shots")
    args = parser.parse_args(argv)

    if not ffmpeg_binary():
        raise RuntimeError("ffmpeg missing")
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    candidates = candidate_index()
    blocked = blocked_reasons()
    model = load_model(args.model)

    rows: list[dict] = []
    report_path = HERE / "qa/narration-asr.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    shots = story["shots"][: args.limit] if args.limit else story["shots"]
    for shot in shots:
        sid = shot["id"]
        path = HERE / "audio" / f"{sid}.mp3"
        kind = "individual"
        if not path.is_file():
            candidate = candidates.get(sid)
            if candidate is None:
                rows.append({
                    "id": sid, "status": "missing_audio", "expected": shot["narration"],
                    "reason": blocked.get(sid, "no generated source and no verified cut"),
                    "target_seconds": float(shot["duration"]),
                })
                continue
            path = ROOT / candidate["file"]
            kind = "pause_cut_candidate"
            if not path.is_file():
                rows.append({
                    "id": sid, "status": "missing_audio", "expected": shot["narration"],
                    "reason": f"candidate cut {candidate['file']} was never materialised",
                    "target_seconds": float(shot["duration"]),
                })
                continue
        clip = transcribe_clip(model, path, args.language)
        row = {
            "id": sid,
            "source_kind": kind,
            "file": str(path.relative_to(ROOT)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "expected": shot["narration"],
            "asr_text": clip["asr_text"],
            "first_word_start": clip["first_word_start"],
            "last_word_end": clip["last_word_end"],
            "segments": clip["segments"],
        }
        row.update(summarize(shot, clip, clip["asr_text"], measured_seconds(path)))
        row["status"] = (
            "asr_match_needs_review" if row["similarity"] >= MATCH_THRESHOLD
            else "inspect_transcript_or_boundary")
        rows.append(row)
        report_path.write_text(json.dumps(
            {"model": f"faster-whisper {args.model} multilingual int8",
             "decode": "ffmpeg -> 16 kHz mono float32 (PyAV not used)",
             "policy": "ASR evidence only; no alignment signoffs or final manifest auto-created",
             "shots": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{sid}: {row['similarity']:.3f} | {row['status']} | {clip['asr_text']}", flush=True)

    report_path.write_text(json.dumps(
        {"model": f"faster-whisper {args.model} multilingual int8",
         "decode": "ffmpeg -> 16 kHz mono float32 (PyAV not used)",
         "policy": "ASR evidence only; no alignment signoffs or final manifest auto-created",
         "shots": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing = [row["id"] for row in rows if row["status"] == "missing_audio"]
    matched = [row["id"] for row in rows if row["status"] == "asr_match_needs_review"]
    print(f"ASR evidence: {len(matched)} match / {len(missing)} missing / "
          f"{len(rows)} rows; nothing auto-approved", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        import platform
        detail = traceback.format_exc()
        (HERE / "qa").mkdir(parents=True, exist_ok=True)
        (HERE / "qa/narration-asr-error.txt").write_text(
            detail + "\n--- environment ---\n"
            + f"python={sys.version.split()[0]} platform={platform.platform()} "
              f"ffmpeg={shutil.which('ffmpeg')} ffprobe={shutil.which('ffprobe')}\n",
            encoding="utf-8")
        raise
