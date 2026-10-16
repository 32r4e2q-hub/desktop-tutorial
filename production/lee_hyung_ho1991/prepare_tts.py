#!/usr/bin/env python3
"""Generate, tighten, time and provenance-check Mandarin narration with Edge TTS."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BRANCH = "arena/1f36798e-desktop-tutorial"
PROVIDER = "Microsoft Edge TTS"
MODEL = "edge-tts"
VOICE = "zh-CN-YunyangNeural"
FORMAT = "mp3"
INITIAL_SPEED = 1.0
MIN_TEMPO, MAX_TEMPO = 0.86, 1.10


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def edge_rate(speed: float) -> str:
    """Edge TTS accepts signed percentages such as +0% or -5%."""
    percent = round((speed - 1.0) * 100)
    return f"{percent:+d}%"


def synthesize(text: str, speed: float, destination: Path) -> None:
    """Create MP3 using Microsoft Edge's Chinese neural voice; no Zhipu TTS or Agnes."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable, "-m", "edge_tts",
        "--voice", VOICE,
        f"--rate={edge_rate(speed)}",  # bind negative percentages to the option for argparse
        "--text", text,
        "--write-media", str(destination),
        "--no-progress",
    ]
    last_error = "unknown Edge TTS error"
    for attempt in range(1, 4):
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=240)
            if result.returncode == 0 and destination.is_file() and destination.stat().st_size >= 1024:
                return
            last_error = (result.stderr or result.stdout or f"exit code {result.returncode}")[-1200:]
        except (OSError, subprocess.TimeoutExpired) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        destination.unlink(missing_ok=True)
        if attempt < 3:
            wait = attempt * 5
            print(f"EDGE_TTS_RETRY attempt={attempt}/3 wait={wait}s error={last_error[:200]}", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"Microsoft Edge TTS failed after 3 attempts: {last_error}")


def run_tool(name: str) -> None:
    path = HERE / name
    subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)


def cached_audio_is_valid(story: dict) -> bool:
    manifest = read_json(HERE / "audio" / "manifest.json", {})
    if (manifest.get("provider") != PROVIDER or manifest.get("model") != MODEL
            or manifest.get("voice_id") != VOICE):
        return False
    rows = {row.get("id"): row for row in manifest.get("clips", [])}
    for chapter in story["chapters"]:
        row = rows.get(chapter["id"], {})
        clean = HERE / "audio" / row.get("file", "missing")
        raw = HERE / "audio" / row.get("raw_file", "missing")
        if (row.get("text") != chapter["text"] or not clean.is_file() or not raw.is_file()
                or digest(clean) != row.get("sha256") or digest(raw) != row.get("raw_sha256")):
            return False
    timing = read_json(HERE / "audio" / "clause-times.json", {})
    cuts = read_json(HERE / "audio" / "cuts.json", {})
    chapter_ids = {chapter["id"] for chapter in story["chapters"]}
    if set(timing) != chapter_ids or set(cuts) != chapter_ids:
        return False
    for chapter in story["chapters"]:
        expected_ids = [shot["id"] for shot in story["shots"] if shot["narration_id"] == chapter["id"]]
        if [row[1] for row in cuts[chapter["id"]]] != expected_ids:
            return False
    return True


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, timeout=120)
    if check and result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


def publish_audio() -> None:
    if os.getenv("GITHUB_ACTIONS") != "true" or git("branch", "--show-current") != BRANCH:
        raise RuntimeError("Audio publishing is permitted only from the fixed Arena branch in GitHub Actions")
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    paths = [
        "production/lee_hyung_ho1991/audio/manifest.json",
        "production/lee_hyung_ho1991/audio/tighten-report.json",
        "production/lee_hyung_ho1991/audio/clause-times.json",
        "production/lee_hyung_ho1991/audio/cuts.json",
    ]
    paths.extend(str(path.relative_to(ROOT)) for path in sorted((HERE / "audio").glob("N0*.mp3")))
    raw_dir = HERE / "audio" / "raw"
    paths.extend(str(path.relative_to(ROOT)) for pattern in ("N0*.mp3", "N0*.wav")
                 for path in sorted(raw_dir.glob(pattern)))
    git("add", "--", *paths)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0
    if not changed:
        print("TTS_AUDIO_ALREADY_PUBLISHED", flush=True)
        return
    git("commit", "-m", "lee_hyung_ho1991: add verified Edge TTS narration and timings", "--", *paths)
    for attempt in range(5):
        result = subprocess.run(["git", "push", "origin", BRANCH], cwd=ROOT, text=True, capture_output=True, timeout=180)
        if result.returncode == 0:
            print("EDGE_TTS_AUDIO_PUBLISHED", flush=True)
            return
        print(f"TTS_AUDIO_PUSH_RETRY {attempt + 1}: {result.stderr[-500:]}", flush=True)
        git("fetch", "origin", BRANCH)
        git("rebase", "FETCH_HEAD")
        time.sleep(2 + attempt * 2)
    raise RuntimeError("Could not push verified narration to the fixed Arena branch")


def prepare(force: bool = False) -> dict:
    story = read_json(HERE / "story.json", {})
    if not story.get("chapters") or len(story["chapters"]) != 6:
        raise RuntimeError("story.json must contain the six fact-checked narration chapters")
    for chapter in story["chapters"]:
        if len(chapter["text"]) > 1024:
            raise RuntimeError(f"{chapter['id']}: narration chapter exceeds 1024 characters")
    if not force and cached_audio_is_valid(story):
        print("TTS_CACHE_HIT: narration bytes, voice and text hashes match", flush=True)
        return read_json(HERE / "audio" / "manifest.json", {})

    raw_dir = HERE / "audio" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    speed = INITIAL_SPEED
    tighten = {}
    for calibration in range(3):
        print(f"EDGE_TTS_SYNTHESIS voice={VOICE} rate={edge_rate(speed)} pass={calibration + 1}", flush=True)
        for chapter in story["chapters"]:
            destination = raw_dir / f"{chapter['id']}.{FORMAT}"
            synthesize(chapter["text"], speed, destination)
            print(f"TTS_CHAPTER_READY {chapter['id']} bytes={destination.stat().st_size}", flush=True)
        run_tool("tighten_pauses.py")
        tighten = read_json(HERE / "audio" / "tighten-report.json", {})
        tempo = float(tighten.get("tempo_after", 0.0))
        if MIN_TEMPO <= tempo <= MAX_TEMPO:
            break
        if calibration == 2:
            raise RuntimeError(
                f"Narration would need {tempo:.3f} tempo, outside {MIN_TEMPO:.2f}-{MAX_TEMPO:.2f}; "
                "inspect tighten-report.json and adjust TTS rate or pause cap."
            )
        new_speed = max(0.88, min(1.10, speed * tempo)) if tempo > 0 else speed
        if abs(new_speed - speed) < 0.015:
            new_speed = min(1.10, speed + 0.05) if tempo > MAX_TEMPO else max(0.88, speed - 0.05)
        speed = new_speed
        print(f"TTS_CALIBRATE tempo={tempo:.3f}; retrying at rate={edge_rate(speed)}", flush=True)

    clips = []
    for chapter in story["chapters"]:
        clean = HERE / "audio" / f"{chapter['id']}.mp3"
        raw = raw_dir / f"{chapter['id']}.{FORMAT}"
        clips.append({
            "id": chapter["id"],
            "file": clean.name,
            "raw_file": f"raw/{raw.name}",
            "text": chapter["text"],
            "sha256": digest(clean),
            "raw_sha256": digest(raw),
            "bytes": clean.stat().st_size,
            "raw_bytes": raw.stat().st_size,
        })
    manifest = {
        "provider": PROVIDER,
        "model": MODEL,
        "voice_id": VOICE,
        "voice_description": "Mandarin Chinese male neural narration, selected by the production agent",
        "speed": speed,
        "response_format": FORMAT,
        "chapters": len(clips),
        "clips": clips,
        "total_tight_seconds": tighten.get("total_tight_seconds"),
        "tempo_after": tighten.get("tempo_after"),
        "text_integrity": "Each manifest text exactly matches the corresponding story.json chapter.",
        "audio_integrity": "SHA-256 recorded for raw Edge TTS MP3 and pause-tightened narration MP3.",
    }
    (HERE / "audio" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    run_tool("clause_times.py")
    run_tool("plan_cuts.py")
    subprocess.run([sys.executable, str(HERE / "clause_times.py"), "--check-cuts"], cwd=ROOT, check=True)
    manifest["timing"] = "audio/clause-times.json; pause-aware measured or estimated clause boundaries drive cuts and subtitles."
    (HERE / "audio" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TTS_READY provider={PROVIDER} voice={VOICE} rate={edge_rate(speed)} tempo={manifest['tempo_after']} chapters={len(clips)}", flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Regenerate even if the verified audio cache is complete")
    parser.add_argument("--publish", action="store_true", help="Commit verified narration/timing files to the fixed Arena branch")
    args = parser.parse_args()
    prepare(force=args.force)
    if args.publish:
        publish_audio()


if __name__ == "__main__":
    main()
