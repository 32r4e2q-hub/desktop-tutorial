#!/usr/bin/env python3
"""Synthesize, tighten, time and provenance-check the six Zhipu GLM-TTS chapters."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BRANCH = "arena/04ec3850-desktop-tutorial"
ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/audio/speech"
MODEL = "glm-tts"
VOICE = "chuichui"
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


def decode_response(body: bytes, content_type: str) -> bytes:
    """Accept the documented streamed audio response and common JSON/base64 wrappers."""
    if "json" not in content_type.lower():
        return body
    payload = json.loads(body.decode("utf-8"))
    if isinstance(payload, dict):
        for key in ("audio", "data", "audio_base64", "base64"):
            value = payload.get(key)
            if isinstance(value, str):
                if value.startswith("data:") and "," in value:
                    value = value.split(",", 1)[1]
                return base64.b64decode(value)
        url = payload.get("url")
        if isinstance(url, str) and url.startswith("https://"):
            with urllib.request.urlopen(urllib.request.Request(
                    url, headers={"User-Agent": "arena-lee-hyung-ho1991-glm-tts/1.0"}), timeout=180) as response:
                return response.read()
        error = payload.get("error") or payload.get("message") or payload
        raise RuntimeError(f"GLM-TTS returned JSON without audio: {str(error)[:500]}")
    raise RuntimeError("GLM-TTS returned an unexpected JSON response")


def synthesize(text: str, key: str, speed: float, destination: Path) -> None:
    payload = {
        "model": MODEL,
        "input": text,
        "voice": VOICE,
        "response_format": FORMAT,
        "speed": round(speed, 3),
        "volume": 1.0,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=data,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "Accept": "audio/mpeg, application/octet-stream, application/json"},
    )
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                audio = decode_response(response.read(), response.headers.get("Content-Type", ""))
            if len(audio) < 1024:
                raise RuntimeError(f"GLM-TTS returned an implausibly small audio body ({len(audio)} bytes)")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(audio)
            return
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")[:1000]
            last_error = RuntimeError(f"HTTP {exc.code}: {body}")
            if exc.code not in (408, 425, 429, 500, 502, 503, 504) or attempt == 5:
                raise last_error from exc
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError) as exc:
            last_error = exc
            if attempt == 5:
                break
        wait = min(45, attempt * 7)
        print(f"TTS_RETRY attempt={attempt}/5 wait={wait}s error={type(last_error).__name__}: {str(last_error)[:180]}", flush=True)
        time.sleep(wait)
    raise RuntimeError(f"GLM-TTS failed after retries: {last_error}")


def run_tool(name: str) -> None:
    path = HERE / name
    subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)


def cached_audio_is_valid(story: dict) -> bool:
    manifest = read_json(HERE / "audio" / "manifest.json", {})
    if manifest.get("provider") != "Zhipu AI" or manifest.get("model") != MODEL or manifest.get("voice_id") != VOICE:
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
    if set(timing) != {chapter["id"] for chapter in story["chapters"]}:
        return False
    if set(cuts) != {chapter["id"] for chapter in story["chapters"]}:
        return False
    for chapter in story["chapters"]:
        expected_ids = [shot["id"] for shot in story["shots"] if shot["narration_id"] == chapter["id"]]
        actual_ids = [row[1] for row in cuts[chapter["id"]]]
        if actual_ids != expected_ids:
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
    paths.extend(str(path.relative_to(ROOT)) for path in sorted((HERE / "audio" / "raw").glob("N0*.mp3")))
    git("add", "--", *paths)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0
    if not changed:
        print("TTS_AUDIO_ALREADY_PUBLISHED", flush=True)
        return
    git("commit", "-m", "lee_hyung_ho1991: add verified GLM-TTS narration and timings", "--", *paths)
    for attempt in range(5):
        result = subprocess.run(["git", "push", "origin", BRANCH], cwd=ROOT, text=True, capture_output=True, timeout=180)
        if result.returncode == 0:
            print("TTS_AUDIO_PUBLISHED", flush=True)
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
            raise RuntimeError(f"{chapter['id']}: GLM-TTS input exceeds 1024 characters")
    if not force and cached_audio_is_valid(story):
        print("TTS_CACHE_HIT: existing audio bytes and narration text hashes match", flush=True)
        return read_json(HERE / "audio" / "manifest.json", {})

    key = os.getenv("ZHIPUAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ZHIPUAI_API_KEY is unavailable; configure the repository Actions secret")

    raw_dir = HERE / "audio" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    speed = INITIAL_SPEED
    tighten = {}
    # GLM-TTS speed can vary by chapter. Calibrate once against the renderer's ±10% gate.
    for calibration in range(3):
        print(f"TTS_SYNTHESIS voice={VOICE} speed={speed:.2f} pass={calibration + 1}", flush=True)
        for chapter in story["chapters"]:
            destination = raw_dir / f"{chapter['id']}.mp3"
            synthesize(chapter["text"], key, speed, destination)
            print(f"TTS_CHAPTER_READY {chapter['id']} bytes={destination.stat().st_size}", flush=True)
        run_tool("tighten_pauses.py")
        tighten = read_json(HERE / "audio" / "tighten-report.json", {})
        tempo = float(tighten.get("tempo_after", 0.0))
        if MIN_TEMPO <= tempo <= MAX_TEMPO:
            break
        if calibration == 2:
            raise RuntimeError(
                f"Narration would need {tempo:.3f} tempo, outside {MIN_TEMPO:.2f}-{MAX_TEMPO:.2f}; "
                "inspect tighten-report.json and adjust the TTS speed or pause cap."
            )
        new_speed = max(0.88, min(1.10, speed * tempo)) if tempo > 0 else speed
        if abs(new_speed - speed) < 0.015:
            new_speed = min(1.10, speed + 0.05) if tempo > MAX_TEMPO else max(0.88, speed - 0.05)
        speed = new_speed
        print(f"TTS_CALIBRATE tempo={tempo:.3f}; retrying all chapters at speed={speed:.2f}", flush=True)

    clips = []
    for chapter in story["chapters"]:
        clean = HERE / "audio" / f"{chapter['id']}.mp3"
        raw = raw_dir / f"{chapter['id']}.mp3"
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
        "provider": "Zhipu AI",
        "model": MODEL,
        "endpoint": ENDPOINT,
        "voice_id": VOICE,
        "voice_description": "Chinese documentary narration voice selected by the production agent",
        "speed": speed,
        "response_format": FORMAT,
        "chapters": len(clips),
        "clips": clips,
        "total_tight_seconds": tighten.get("total_tight_seconds"),
        "tempo_after": tighten.get("tempo_after"),
        "text_integrity": "Each manifest text exactly matches the corresponding story.json chapter.",
        "audio_integrity": "SHA-256 recorded for raw GLM-TTS MP3 and pause-tightened narration MP3.",
    }
    (HERE / "audio" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    run_tool("clause_times.py")
    run_tool("plan_cuts.py")
    subprocess.run([sys.executable, str(HERE / "clause_times.py"), "--check-cuts"], cwd=ROOT, check=True)
    manifest["timing"] = "audio/clause-times.json; per-chapter method is recorded, and cuts use measured or pause-aware estimated clause boundaries."
    (HERE / "audio" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TTS_READY voice={VOICE} speed={speed:.2f} tempo={manifest['tempo_after']} chapters={len(clips)}", flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Regenerate even if the verified audio cache is complete")
    parser.add_argument("--publish", action="store_true", help="Commit only verified narration/timing files to the fixed Arena branch")
    args = parser.parse_args()
    prepare(force=args.force)
    if args.publish:
        publish_audio()


if __name__ == "__main__":
    main()
