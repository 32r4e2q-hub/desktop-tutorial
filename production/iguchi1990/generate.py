#!/usr/bin/env python3
"""Queue and retrieve the 30 actual Agnes Video 2.5 Flash clips for iguchi1990.

Generation is intentionally fail-closed: no provider call is possible until every character,
scene, and prop reference exists, has an individual visual-review approval, and the manifest
is complete. Accepted task IDs and SHA-256 receipts are checkpointed so a later workflow run
resumes rather than duplicates paid/quota-consuming generations. MP4s remain in ignored work/;
only results and small contact sheets are committed.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import shutil
import subprocess
import sys
import threading
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "production"))
sys.path.insert(0, str(ROOT / "production" / "setagaya2000"))

import agnes_video as agnes  # noqa: E402
from throttle import BudgetExhausted, RequestGate  # noqa: E402

BRANCH = "arena/36f9cd13-desktop-tutorial"
MODEL = "agnes-video-2.5-flash"
SOURCE_SIZE = "720P"
MIN_CREATE_INTERVAL = 61.0
WORKERS_MAX = 2
REQUEST_FIELDS = {"model", "prompt", "seconds", "size", "aspect_ratio", "mode", "n", "seed", "images"}
FORBIDDEN_FIELDS = {"width", "height", "fps", "num_frames", "frame_rate", "duration",
                    "resolution", "negative_prompt", "quality", "num_inference_steps"}
QUEUE_FULL_MARKERS = ("video queue is full", "queue is full", "queue_full", "no available channel",
                      "get_channel_failed", "capacity is full")
RETRYABLE_MARKERS = QUEUE_FULL_MARKERS + ("temporarily unavailable", "network error", "provider 5xx",
                                          "service unavailable", "gateway timeout")
QUOTA_MARKERS = ("quota exceeded", "insufficient quota", "out of credits", "no credits",
                 "billing limit", "usage limit reached", "daily limit reached", "monthly limit reached")
PLAN = HERE / "story.json"
RESULTS = HERE / "results.json"
REF_MANIFEST = HERE / "reference" / "manifest.json"
WORK = ROOT / "work" / "iguchi1990"
SOURCES = WORK / "sources"
QA = HERE / "qa"
LOCK = threading.RLock()


def read_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def api_base_url() -> str:
    base = os.getenv("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).rstrip("/")
    return base[:-3] if base.endswith("/v1") else base


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True,
                                  stderr=subprocess.STDOUT, timeout=120)


def reference_index(project: dict) -> dict[str, dict]:
    return {row["id"]: row for row in project.get("reference_images", [])}


def png_dimensions(path: Path) -> tuple[int, int] | None:
    """Read the PNG IHDR dimensions without adding a runtime imaging dependency."""
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def full_prompt(project: dict, shot: dict) -> str:
    """Compose the required order: STYLE, ordered <Picture N> refs, role anchors, scene, NEGATIVE."""
    refs = reference_index(project)
    parts = [project["style_prefix"].strip()]
    for number, ref_id in enumerate(shot.get("references", []), 1):
        if ref_id not in refs:
            raise ValueError(f"{shot['id']}: unknown reference {ref_id}")
        row = refs[ref_id]
        parts.append(
            f"<Picture {number}> is the {row['category']} reference for {row['description']}. "
            "Preserve its period, materials, palette and identity cues; adapt its composition "
            "to the requested moving shot. Do not reproduce any lettering."
        )
    for role in shot.get("characters", []):
        character = project["characters"].get(role)
        if not character:
            raise ValueError(f"{shot['id']}: missing character anchor {role}")
        parts.append(character["anchor"].strip() + " " + character["identity"].strip())
    parts.append(shot["prompt"].strip())
    parts.append(project["negative_prompt"].strip())
    return "\n\n".join(parts)


def payload_seed(project: dict, shot: dict) -> int:
    roles = [role for role in shot.get("characters", []) if role]
    seeds = project.get("character_seeds", {})
    if len(roles) == 1 and roles[0] in seeds:
        return int(seeds[roles[0]])
    return int(shot["seed"])


def full_payload(project: dict, shot: dict) -> dict:
    references = reference_index(project)
    image_urls = [references[ref_id]["url"] for ref_id in shot.get("references", [])]
    return {
        "model": project["model"],
        "prompt": full_prompt(project, shot),
        "seconds": str(int(shot["duration"])),
        "size": project["source_size"],
        "aspect_ratio": shot["aspect"],
        "mode": "reference",
        "n": 1,
        "seed": payload_seed(project, shot),
        "images": image_urls,
    }


def request_hash(project: dict, shot: dict) -> str:
    blob = json.dumps(full_payload(project, shot), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def reference_errors(project: dict) -> list[str]:
    errors: list[str] = []
    refs = project.get("reference_images", [])
    try:
        manifest = read_json(REF_MANIFEST, {})
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read reference/manifest.json: {exc}"]
    manifest_rows = {row.get("id"): row for row in manifest.get("references", [])}
    if manifest.get("status") != "complete":
        errors.append(f"reference manifest status is {manifest.get('status')!r}, not 'complete'")
    if manifest.get("required_reference_count") != len(refs):
        errors.append("reference manifest count differs from story.json")
    for ref in refs:
        image_path = HERE / "reference" / ref["file"]
        record = manifest_rows.get(ref["id"], {})
        if not image_path.is_file():
            errors.append(f"{ref['id']}: missing {ref['file']}")
        else:
            if record.get("sha256") != digest(image_path):
                errors.append(f"{ref['id']}: manifest SHA-256 mismatch; rerun build_story.py and review again")
            size = image_path.stat().st_size
            dimensions = png_dimensions(image_path)
            if size >= 15 * 1024 * 1024:
                errors.append(f"{ref['id']}: reference is not below Agnes's 15 MB per-image limit")
            if dimensions is None or any(value < 256 or value > 5760 for value in dimensions):
                errors.append(f"{ref['id']}: reference must be a PNG with both dimensions from 256 to 5760 pixels")
        if not ref.get("approved") or ref.get("review_status") != "approved":
            errors.append(f"{ref['id']}: story.json is not approved ({ref.get('review_status', 'missing')})")
        if not record.get("approved") or record.get("review_status") != "approved":
            errors.append(f"{ref['id']}: reference manifest is not approved ({record.get('review_status', 'missing')})")
    return errors


def validate_project(project: dict, require_approved_refs: bool = False) -> None:
    shots = project.get("shots", [])
    if len(shots) != 30 or project.get("target_duration") != 180:
        raise ValueError("Expected exactly 30 shots spanning exactly 180 seconds")
    if (project.get("width"), project.get("height"), project.get("fps")) != (1920, 1080, 24):
        raise ValueError("Delivery master must be 1920x1080 at 24fps")
    if project.get("model") != MODEL or project.get("source_size") != SOURCE_SIZE:
        raise ValueError("Required model/size is Agnes Video 2.5 Flash at 720P source")
    if not project.get("style_prefix", "").startswith("【STYLE】"):
        raise ValueError("STYLE prefix is missing")
    if not project.get("negative_prompt", "").startswith("【NEGATIVE】"):
        raise ValueError("NEGATIVE suffix is missing")

    reference_ids = set(reference_index(project))
    shot_ids = [shot.get("id") for shot in shots]
    if shot_ids != [f"S{i:02d}" for i in range(1, 31)] or len(set(shot_ids)) != 30:
        raise ValueError("Shot IDs must be S01–S30 in order and unique")
    cursor = 0
    for shot in shots:
        duration = int(shot["duration"])
        if shot.get("start") != cursor or not 4 <= duration <= 12:
            raise ValueError(f"Invalid/non-contiguous timeline at {shot.get('id')}")
        if shot.get("kind") != "agnes" or shot.get("seconds") != duration:
            raise ValueError(f"Every shot must be a real Agnes clip with matching seconds: {shot['id']}")
        if shot.get("aspect") != "16:9" or shot.get("source_size") != SOURCE_SIZE:
            raise ValueError(f"Bad aspect/source size at {shot['id']}")
        if not shot.get("narration", "").strip() or not shot.get("prompt", "").strip():
            raise ValueError(f"Missing prompt or shot-locked narration at {shot['id']}")
        if not 1 <= len(shot.get("references", [])) <= 5:
            raise ValueError(f"Each reference-mode shot needs 1–5 images: {shot['id']}")
        if set(shot["references"]) - reference_ids:
            raise ValueError(f"Unknown references in {shot['id']}: {sorted(set(shot['references']) - reference_ids)}")
        if shot["narration_id"] not in {chapter["id"] for chapter in project.get("chapters", [])}:
            raise ValueError(f"Unknown narration chapter in {shot['id']}")
        for role in shot.get("characters", []):
            if role not in project.get("characters", {}):
                raise ValueError(f"Missing character anchor {role} in {shot['id']}")
        payload = full_payload(project, shot)
        existing_sizes = [(HERE / "reference" / reference_index(project)[ref_id]["file"]).stat().st_size
                          for ref_id in shot["references"]
                          if (HERE / "reference" / reference_index(project)[ref_id]["file"]).is_file()]
        if any(size >= 15 * 1024 * 1024 for size in existing_sizes):
            raise ValueError(f"Reference image exceeds the 15 MB per-image limit in {shot['id']}")
        if sum(existing_sizes) + len(payload["prompt"].encode("utf-8")) >= 50 * 1024 * 1024:
            raise ValueError(f"Reference payload exceeds Agnes's 50 MB total request limit in {shot['id']}")
        if set(payload) != REQUEST_FIELDS:
            raise ValueError(f"Unexpected Agnes request fields in {shot['id']}: {sorted(payload)}")
        if FORBIDDEN_FIELDS.intersection(payload):
            raise ValueError(f"Unsupported request fields in {shot['id']}: {sorted(FORBIDDEN_FIELDS.intersection(payload))}")
        if payload["model"] != MODEL or payload["mode"] != "reference" or payload["size"] != SOURCE_SIZE \
                or payload["aspect_ratio"] != "16:9" or payload["n"] != 1:
            raise ValueError(f"Bad Agnes Video 2.5 Flash settings in {shot['id']}")
        if not payload["seconds"].isdigit() or int(payload["seconds"]) != duration:
            raise ValueError(f"Agnes seconds must be the shot duration as a string in {shot['id']}")
        if not payload["prompt"].startswith("【STYLE】") or not payload["prompt"].endswith(project["negative_prompt"].strip()):
            raise ValueError(f"STYLE/NEGATIVE were not inlined correctly in {shot['id']}")
        for index in range(1, len(payload["images"]) + 1):
            if f"<Picture {index}>" not in payload["prompt"]:
                raise ValueError(f"Missing <Picture {index}> prompt reference in {shot['id']}")
        cursor += duration
    if cursor != 180:
        raise ValueError(f"Shot timeline ends at {cursor}s, not 180s")

    chapters = project.get("chapters", [])
    if len(chapters) != 9:
        raise ValueError("Expected nine narration chapters")
    chapter_cursor = 0
    for chapter in chapters:
        if chapter["start"] != chapter_cursor or not chapter.get("text", "").strip():
            raise ValueError("Narration chapters must be non-empty and contiguous")
        chapter_cursor += int(chapter["duration"])
    if chapter_cursor != 180:
        raise ValueError("Narration chapters do not span 180 seconds")
    if "无BGM" not in project.get("presentation", {}).get("audio_style", ""):
        raise ValueError("Audio brief must explicitly forbid BGM")

    if require_approved_refs:
        errors = reference_errors(project)
        if errors:
            raise ValueError("Reference gate blocked generation:\n- " + "\n- ".join(errors))


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def commit_checkpoint(doc: dict, shot_id: str | None = None) -> None:
    """Atomically persist a small receipt/QA sheet to the fixed session branch."""
    with LOCK:
        RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if os.getenv("GITHUB_ACTIONS", "").lower() != "true":
            return
        paths = [str(RESULTS.relative_to(ROOT))]
        if shot_id and (QA / f"{shot_id}.jpg").is_file():
            paths.append(str((QA / f"{shot_id}.jpg").relative_to(ROOT)))
        _run(["git", "add", "-f", "--", *paths])
        changed = subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=ROOT).returncode != 0
        if not changed:
            return
        _run(["git", "config", "user.name", "arena-autopilot"])
        _run(["git", "config", "user.email", "arena-autopilot@users.noreply.github.com"])
        _run(["git", "commit", "-m", f"iguchi1990: {shot_id or 'production'} checkpoint [skip-iguchi1990]", "--", *paths])
        for attempt in range(3):
            try:
                _run(["git", "push", "origin", BRANCH], capture_output=True, text=True)
                return
            except subprocess.CalledProcessError:
                if attempt == 2:
                    raise
                _run(["git", "pull", "--rebase", "origin", BRANCH], capture_output=True, text=True)


def log(message: str) -> None:
    print(time.strftime("[%H:%M:%S] ") + message, flush=True)


def redact(message: str, api_key: str) -> str:
    return str(message).replace(api_key, "[redacted]")[:800] if api_key else str(message)[:800]


def retryable_create_error(message: str) -> str | None:
    text = str(message or "").lower()
    if any(marker in text for marker in QUOTA_MARKERS):
        return "quota_exhausted"
    if "http 408" in text or "http 425" in text:
        return "provider_timeout"
    for marker in RETRYABLE_MARKERS:
        if marker in text:
            return "queue_full" if marker in QUEUE_FULL_MARKERS else marker
    if "http 5" in text:
        return "provider_5xx"
    return None


def _record_status(doc: dict, sid: str, values: dict, publish: bool = False) -> None:
    with LOCK:
        row = doc.setdefault("shots", {}).setdefault(sid, {"id": sid})
        row.update(values)
        row["updated_at"] = now_utc()
        doc["updated_at"] = now_utc()
        if publish:
            commit_checkpoint(doc, sid)
        else:
            RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _new_task_row(doc: dict, shot: dict, wanted_hash: str) -> dict:
    sid = shot["id"]
    with LOCK:
        old = dict(doc.setdefault("shots", {}).get(sid, {}))
        if old and old.get("request_hash") != wanted_hash:
            if old.get("video_id") and old.get("status") not in {"completed", "failed", "cancelled"}:
                raise RuntimeError(f"{sid}: saved Agnes task uses a different prompt; let it finish before changing/replacing it")
            doc.setdefault("previous_results", {}).setdefault(sid, []).append(old)
            old = {}
        if old.get("request_hash") == wanted_hash and old.get("status") == "completed" \
                and old.get("video_url") and old.get("sha256"):
            return old
        if old.get("request_hash") == wanted_hash and old.get("status") in {"failed", "quota_blocked", "create_failed"}:
            return old
        if old.get("request_hash") == wanted_hash and old.get("video_id") \
                and old.get("status") not in {"failed", "cancelled"}:
            return old
        row = {"id": sid, "request_hash": wanted_hash, "status": "waiting_create_slot",
               "generation_attempts": int(old.get("generation_attempts", 0)),
               "create_attempts": int(old.get("create_attempts", 0)), "error": None}
        doc.setdefault("shots", {})[sid] = row
        return row


def create_with_gate(shot: dict, payload: dict, doc: dict, gate: RequestGate,
                     deadline: float, api_key: str) -> dict:
    sid = shot["id"]
    attempts = 0
    while True:
        attempts += 1
        _record_status(doc, sid, {"status": "waiting_create_slot", "last_create_attempt": attempts})
        gate.acquire_creation(deadline)
        try:
            created = agnes.create_task(
                api_base_url(),
                api_key, payload, retries=1, retry_delay=1,
            )
            gate.defer(MIN_CREATE_INTERVAL)
            with LOCK:
                doc["last_create_epoch"] = time.time()
            return created
        except agnes.RateLimited as exc:
            with LOCK:
                doc["last_create_epoch"] = time.time()
            message = redact(str(exc), api_key)
            classification = retryable_create_error(message)
            if classification == "quota_exhausted":
                _record_status(doc, sid, {"status": "quota_blocked", "error": message,
                                           "create_attempts": attempts}, publish=True)
                raise RuntimeError("Agnes reports the account quota/credits are exhausted; stopping without trying to bypass it") from exc
            cooldown = max(MIN_CREATE_INTERVAL, float(exc.retry_after or 0))
            gate.defer(cooldown)
            _record_status(doc, sid, {"status": "rate_limited", "error": message,
                                       "create_attempts": attempts,
                                       "applied_cooldown_seconds": cooldown}, publish=True)
            if attempts >= 3:
                raise RuntimeError("Agnes rejected three creation attempts with HTTP 429 after the required cooldowns; stopping and preserving the provider limit") from exc
            log(f"{sid}: provider rate limit; honoring {cooldown:g}s cooldown")
        except agnes.Fatal as exc:
            with LOCK:
                doc["last_create_epoch"] = time.time()
            message = redact(str(exc), api_key)
            classification = retryable_create_error(message)
            if classification == "queue_full":
                gate.defer(MIN_CREATE_INTERVAL)
                _record_status(doc, sid, {"status": "waiting_provider_capacity", "error": message,
                                           "create_attempts": attempts,
                                           "applied_cooldown_seconds": MIN_CREATE_INTERVAL}, publish=True)
                raise ProviderQueueFull(message) from exc
            if classification == "quota_exhausted":
                _record_status(doc, sid, {"status": "quota_blocked", "error": message,
                                           "create_attempts": attempts}, publish=True)
                raise RuntimeError("Agnes reports the account quota/credits are exhausted; stopping without trying to bypass it") from exc
            if classification:
                cooldown = max(MIN_CREATE_INTERVAL, float(getattr(exc, "retry_after", 0) or 0))
                gate.defer(cooldown)
                _record_status(doc, sid, {"status": "provider_cooldown", "error": message,
                                           "create_attempts": attempts,
                                           "applied_cooldown_seconds": cooldown}, publish=attempts == 1 or attempts % 5 == 0)
                log(f"{sid}: transient provider error ({classification}); retrying after {cooldown:g}s")
                continue
            _record_status(doc, sid, {"status": "create_failed", "error": message,
                                       "create_attempts": attempts}, publish=True)
            raise


class ProviderQueueFull(RuntimeError):
    pass


def frame_motion_metrics(frames: list[bytes], frame_size: int = 64 * 36) -> dict:
    """Flag an obviously frozen result using low-resolution grayscale frame differences."""
    if len(frames) < 2 or any(len(frame) != frame_size for frame in frames):
        return {"sample_frames": len(frames), "mean_difference": 0.0,
                "moving_transitions": 0, "suspected_static": True}
    diffs = []
    for before, after in zip(frames, frames[1:]):
        total = sum(abs(a - b) for a, b in zip(before, after))
        diffs.append(total / (frame_size * 255.0))
    active = sum(value >= 0.003 for value in diffs)
    return {"sample_frames": len(frames),
            "mean_difference": round(sum(diffs) / len(diffs), 6),
            "max_difference": round(max(diffs), 6),
            "moving_transitions": active,
            "suspected_static": active == 0}


def create_contact_sheet(source: Path, shot: dict) -> dict:
    """Decode-check a real MP4, estimate motion, and save a 3x3 review contact sheet."""
    QA.mkdir(parents=True, exist_ok=True)
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)
    ], text=True, cwd=ROOT))
    video = next((stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError(f"{shot['id']}: no video stream in downloaded result")
    duration = float(probe["format"]["duration"])
    width, height = int(video.get("width", 0)), int(video.get("height", 0))
    if not 3.5 <= duration <= 13 or width < 640 or height < 360:
        raise RuntimeError(f"{shot['id']}: invalid video output {width}x{height}, {duration:.3f}s")
    if abs((width / height) - (16 / 9)) > 0.04:
        raise RuntimeError(f"{shot['id']}: Agnes output is not horizontal 16:9 ({width}x{height})")
    subprocess.run(["ffmpeg", "-v", "error", "-threads", "2", "-i", str(source),
                    "-map", "0:v:0", "-f", "null", "-"], check=True, cwd=ROOT)
    raw_motion = subprocess.check_output([
        "ffmpeg", "-v", "error", "-threads", "2", "-i", str(source),
        "-vf", "fps=2,scale=64:36:flags=area,format=gray", "-frames:v", "24",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ], cwd=ROOT)
    frame_size = 64 * 36
    sampled_frames = [raw_motion[i:i + frame_size]
                      for i in range(0, len(raw_motion) - frame_size + 1, frame_size)]
    motion = frame_motion_metrics(sampled_frames, frame_size)
    contact = QA / f"{shot['id']}.jpg"
    fps = 8.0 / max(duration, 1.0)
    vf = (f"fps={fps:.6f},scale=426:240:force_original_aspect_ratio=decrease,"
          "pad=426:240:(ow-iw)/2:(oh-ih)/2,tile=3x3")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", str(source),
                    "-vf", vf, "-frames:v", "1", "-q:v", "4", str(contact)],
                   check=True, cwd=ROOT)
    return {"duration_seconds": round(duration, 3), "width": width, "height": height,
            "fps": video.get("avg_frame_rate"), "bytes": source.stat().st_size,
            "decoded_ok": True, "motion": motion,
            "motion_review": "suspected_static" if motion["suspected_static"] else "pending_visual_review",
            "contact_sheet": str(contact.relative_to(ROOT)),
            "visual_review": "pending"}


def download_and_verify(shot: dict, row: dict, doc: dict, api_key: str) -> dict:
    sid = shot["id"]
    dest = SOURCES / f"{sid}.mp4"
    SOURCES.mkdir(parents=True, exist_ok=True)
    if not dest.is_file() or digest(dest) != row.get("sha256"):
        agnes.download(row["video_url"], dest, retries=4, retry_delay=5)
    actual_sha, actual_bytes = digest(dest), dest.stat().st_size
    if actual_sha != row.get("sha256") or actual_bytes != row.get("bytes"):
        raise RuntimeError(f"{sid}: downloaded MP4 does not match saved Agnes SHA-256/byte receipt")
    inspection = create_contact_sheet(dest, shot)
    _record_status(doc, sid, {"status": "completed", "inspection": inspection,
                              "reused_existing_asset": bool(row.get("reused_existing_asset", False)),
                              "error": None}, publish=True)
    return {"status": "completed", "id": sid}


def poll_one(shot: dict, row: dict, project: dict, doc: dict, gate: RequestGate,
             deadline: float, api_key: str) -> dict:
    sid = shot["id"]
    try:
        _record_status(doc, sid, {"status": "polling", "error": None})
        final, url = agnes.poll_task(
            api_base_url(), api_key,
            # Reference-mode polling must use video_id + model_name; do not fall back to the
            # text-mode-only /v1/videos/<task_id> route.
            MODEL, str(row["video_id"]), None,
            interval=2, timeout=max(1.0, deadline - time.monotonic()), max_failures=24,
            before_request=lambda: gate.wait_unblocked(deadline), rate_limit_callback=gate.defer,
        )
        reported_size = final.get("size") if isinstance(final, dict) else None
        reported_seconds = final.get("seconds") if isinstance(final, dict) else None
        if reported_size and str(reported_size).upper() != SOURCE_SIZE:
            raise RuntimeError(f"{sid}: Agnes reported unexpected size {reported_size!r}, expected 720P")
        receipt = dict(row)
        receipt.update({"video_url": url, "completed_response": final,
                        "reported_size": reported_size, "reported_seconds": reported_seconds})
        dest = SOURCES / f"{sid}.mp4"
        SOURCES.mkdir(parents=True, exist_ok=True)
        agnes.download(url, dest, retries=4, retry_delay=5)
        receipt["bytes"] = dest.stat().st_size
        receipt["sha256"] = digest(dest)
        receipt["requested_seconds"] = int(shot["duration"])
        receipt["requested_size"] = SOURCE_SIZE
        receipt["updated_at"] = now_utc()
        with LOCK:
            doc.setdefault("shots", {})[sid].update(receipt)
        inspection = create_contact_sheet(dest, shot)
        _record_status(doc, sid, {"status": "completed", "video_url": url,
                                  "bytes": receipt["bytes"], "sha256": receipt["sha256"],
                                  "requested_seconds": receipt["requested_seconds"],
                                  "requested_size": SOURCE_SIZE, "inspection": inspection,
                                  "visual_review": "pending", "error": None}, publish=True)
        log(f"{sid}: downloaded and decoded ({receipt['bytes']} bytes, {receipt['sha256'][:12]}…)")
        return {"status": "completed", "id": sid}
    except agnes.Fatal as exc:
        message = redact(str(exc), api_key)
        is_task_failure = "video task failed" in message.lower() or "video task rejected" in message.lower()
        status = "failed" if is_task_failure else "poll_pending"
        _record_status(doc, sid, {"status": status, "error": message}, publish=True)
        log(f"{sid}: {status}: {message}")
        return {"status": status, "id": sid, "error": message}
    except Exception as exc:
        message = redact(str(exc), api_key)
        _record_status(doc, sid, {"status": "poll_pending", "error": message}, publish=True)
        log(f"{sid}: poll/download will resume: {message}")
        return {"status": "poll_pending", "id": sid, "error": message}


def selected_shots(project: dict, options: dict) -> list[dict]:
    raw = options.get("only")
    if raw is None or raw == "" or raw == []:
        return list(project["shots"])
    if isinstance(raw, str):
        ids = {item.strip().upper() for item in raw.split(",") if item.strip()}
    elif isinstance(raw, list):
        ids = {str(item).strip().upper() for item in raw}
    else:
        raise ValueError("payload.only must be a comma-separated string or array of shot IDs")
    unknown = ids - {shot["id"] for shot in project["shots"]}
    if unknown:
        raise ValueError("Unknown shot IDs in payload.only: " + ", ".join(sorted(unknown)))
    return [shot for shot in project["shots"] if shot["id"] in ids]


def run_generation(project: dict, options: dict, publish: bool) -> int:
    if not publish or os.getenv("GITHUB_ACTIONS", "").lower() != "true":
        raise RuntimeError("Live Agnes requests are disabled outside the fixed-branch GitHub Actions workflow")
    validate_project(project, require_approved_refs=True)
    api_key = os.getenv("AGNES_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AGNES_API_KEY repository secret is unavailable; no request was sent")

    mode = options.get("mode", "clips")
    if mode != "clips":
        raise ValueError("This workflow only queues video clips; rendering is a later production stage")
    workers = int(options.get("workers", WORKERS_MAX))
    if not 1 <= workers <= WORKERS_MAX:
        raise ValueError(f"workers must be between 1 and {WORKERS_MAX}")
    shots = selected_shots(project, options)
    force = bool(options.get("force", False))
    if force and len(shots) > 3:
        raise ValueError("force is limited to three shots per run to prevent accidental quota-consuming regeneration")
    time_budget = float(options.get("time_budget_minutes", 270))
    if not 1 <= time_budget <= 285:
        raise ValueError("time_budget_minutes must be between 1 and 285")
    deadline = time.monotonic() + time_budget * 60

    doc = read_json(RESULTS, {"project": project["title"], "model": MODEL, "shots": {}})
    doc.update({"project": project["title"], "model": MODEL, "source_size": SOURCE_SIZE,
                "branch": BRANCH, "phase": "queueing_and_polling",
                "reference_gate": project.get("reference_gate"),
                "required_generated_shots": [shot["id"] for shot in shots],
                "rate_policy": {"minimum_creation_interval_seconds": int(MIN_CREATE_INTERVAL),
                                "workers_max": WORKERS_MAX, "retry_after_respected": True,
                                "provider_queue_full_respected": True, "key_rotation": False,
                                "queue_all_available_shots_before_final_poll_drain": True},
                "updated_at": now_utc()})
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    SOURCES.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)

    # Persisted epoch plus the shared throttle prevents a restarted Actions job from resetting
    # the creation cadence. Gate cooldown is also extended after each response, never shortened.
    latest_create = doc.get("last_create_epoch")
    remaining = max(0.0, float(latest_create) + MIN_CREATE_INTERVAL - time.time()) if latest_create else 0.0
    gate = RequestGate(minimum_interval=MIN_CREATE_INTERVAL)
    if remaining:
        gate.defer(remaining)

    shot_map = {shot["id"]: shot for shot in shots}
    outstanding: dict[str, dict] = {}
    to_submit: list[dict] = []
    terminal_errors: list[str] = []

    for shot in shots:
        sid = shot["id"]
        wanted_hash = request_hash(project, shot)
        row = _new_task_row(doc, shot, wanted_hash)
        if force and row.get("status") == "completed":
            with LOCK:
                doc.setdefault("previous_results", {}).setdefault(sid, []).append(dict(row))
                doc["shots"][sid] = {"id": sid, "request_hash": wanted_hash,
                                     "generation_attempts": int(row.get("generation_attempts", 0))}
            row = doc["shots"][sid]
        if row.get("status") == "completed" and row.get("video_url") and row.get("sha256") and not force:
            try:
                download_and_verify(shot, row, doc, api_key)
                log(f"{sid}: reusing matching completed result")
                continue
            except Exception as exc:
                _record_status(doc, sid, {"status": "restore_pending", "error": redact(str(exc), api_key)}, publish=True)
                row = doc["shots"][sid]
        if row.get("video_id") and row.get("status") not in {"failed", "quota_blocked", "create_failed"}:
            outstanding[sid] = row
        elif row.get("status") in {"failed", "quota_blocked", "create_failed"}:
            terminal_errors.append(f"{sid}: {row.get('status')} — {row.get('error', 'manual review required')}")
        else:
            to_submit.append(shot)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers, thread_name_prefix="agnes-poll")
    active: dict[concurrent.futures.Future, str] = {}
    polled_this_run: set[str] = set()

    def start_pollers() -> None:
        for sid, shot in shot_map.items():
            if len(active) >= workers:
                break
            row = doc.get("shots", {}).get(sid, {})
            if sid in outstanding and row.get("video_id")                     and row.get("status") not in {"completed", "failed", "quota_blocked", "create_failed"}                     and sid not in active.values() and sid not in polled_this_run:
                future = executor.submit(poll_one, shot, dict(row), project, doc, gate, deadline, api_key)
                active[future] = sid
                polled_this_run.add(sid)

    def wait_one() -> None:
        if not active:
            return
        done, _ = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
        for future in done:
            sid = active.pop(future)
            try:
                result = future.result()
                if result.get("status") == "failed":
                    terminal_errors.append(f"{sid}: Agnes task failed — {result.get('error', '')}")
            except Exception as exc:
                _record_status(doc, sid, {"status": "poll_pending", "error": redact(str(exc), api_key)}, publish=True)
        start_pollers()

    queue_error: str | None = None
    try:
        # One serial creator enforces the provider's 1-RPM cap. Up to two independent pollers
        # run in the background, so tasks are queued promptly without waiting on each MP4.
        index = 0
        while index < len(to_submit):
            start_pollers()
            shot = to_submit[index]
            sid = shot["id"]
            try:
                payload = full_payload(project, shot)
                created = create_with_gate(shot, payload, doc, gate, deadline, api_key)
            except ProviderQueueFull:
                log(f"{sid}: provider queue is full; waiting for one saved task to finish before retrying")
                start_pollers()
                if active:
                    wait_one()
                    continue  # retry the same shot only after capacity is released
                pollable = [task_id for task_id, row in outstanding.items()
                            if row.get("video_id") and row.get("status") not in {"completed", "failed"}
                            and task_id not in polled_this_run]
                if pollable:
                    continue
                unfinished = [task_id for task_id, saved in outstanding.items()
                              if doc.get("shots", {}).get(task_id, {}).get("status") not in
                              {"completed", "failed", "quota_blocked", "create_failed"}]
                if unfinished:
                    queue_error = "Provider queue is full and saved tasks could not be polled; resume in a later workflow run."
                    break
                try:
                    gate.wait_unblocked(deadline)
                except BudgetExhausted as exc:
                    queue_error = str(exc)
                    break
                continue
            except RuntimeError as exc:
                queue_error = str(exc)
                log("Stopping new task creation: " + queue_error)
                break
            except (agnes.Fatal, BudgetExhausted, ValueError) as exc:
                _record_status(doc, sid, {"status": "create_failed", "error": redact(str(exc), api_key)}, publish=True)
                queue_error = redact(str(exc), api_key)
                break

            video_id = created.get("video_id") or created.get("id") or created.get("task_id")
            task_id = created.get("task_id") or created.get("id") or video_id
            if not video_id:
                _record_status(doc, sid, {"status": "create_failed", "error": "Agnes response has no task identifier"}, publish=True)
                queue_error = "Agnes response did not include a task identifier"
                break
            with LOCK:
                current = doc.setdefault("shots", {}).setdefault(sid, {"id": sid})
                current.update({"request_hash": request_hash(project, shot), "status": "queued",
                                "video_id": str(video_id), "task_id": str(task_id),
                                "requested_seconds": int(shot["duration"]), "requested_size": SOURCE_SIZE,
                                "request": payload, "generation_attempts": int(current.get("generation_attempts", 0)) + 1,
                                "create_attempts": int(current.get("create_attempts", 0)) + 1,
                                "created_at": now_utc(), "error": None})
                doc["last_create_epoch"] = time.time()
                doc["updated_at"] = now_utc()
                outstanding[sid] = current
                commit_checkpoint(doc, sid)
            log(f"{sid}: accepted by Agnes (task {str(video_id)[:12]}…); next create waits at least 61s")
            index += 1
            start_pollers()

        # Finish all accepted tasks already in Agnes. A polling timeout retains its task ID and
        # does not create a replacement; the next run resumes that same provider task.
        start_pollers()
        while active:
            wait_one()

        pending = [shot["id"] for shot in shots
                   if doc.get("shots", {}).get(shot["id"], {}).get("status") != "completed"]
        doc["phase"] = "clips_complete" if not pending else "clips_pending_resume"
        doc["pending_shots"] = pending
        doc["failed_shots"] = [shot["id"] for shot in shots
                               if doc.get("shots", {}).get(shot["id"], {}).get("status") in
                               {"failed", "quota_blocked", "create_failed"}]
        doc["queue_error"] = queue_error
        doc["updated_at"] = now_utc()
        commit_checkpoint(doc)
        if pending or queue_error or terminal_errors:
            log(f"Generation paused: {len(pending)} clip(s) pending; accepted task IDs remain resumable.")
            for error in terminal_errors:
                log(error)
            return 1
        log(f"Generation complete: {len(shots)} selected Agnes clips are downloaded and decoded.")
        return 0
    finally:
        executor.shutdown(wait=True, cancel_futures=False)

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and resume Agnes Video 2.5 Flash reference-mode clips.")
    parser.add_argument("--validate", action="store_true", help="offline storyboard/API validation only")
    parser.add_argument("--payload", default="{}", help='JSON, e.g. {"mode":"clips","workers":2}')
    parser.add_argument("--publish", action="store_true", help="required for the fixed-branch Actions workflow")
    parser.add_argument("--dry-run", action="store_true", help="print a redacted request preview; never call Agnes")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        project = read_json(PLAN, {})
        options = json.loads(args.payload or "{}")
        validate_project(project, require_approved_refs=False)
        if args.validate:
            errors = reference_errors(project)
            print(f"VALID storyboard: {len(project['shots'])} shots, 180 seconds, {MODEL}, 720P source, 16:9, shot-locked narration.")
            print(f"Reference gate: {project.get('reference_gate', {}).get('approved_count', 0)}/{len(project.get('reference_images', []))} approved.")
            if errors:
                print("GENERATION BLOCKED until references are complete and individually approved:")
                for error in errors:
                    print("- " + error)
            return 0
        if args.dry_run:
            shot = selected_shots(project, options)[0]
            payload = full_payload(project, shot)
            payload["prompt"] = f"[prompt {len(payload['prompt'])} chars; starts {payload['prompt'][:100]!r}; ends {payload['prompt'][-100:]!r}]"
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        return run_generation(project, options, args.publish)
    except (ValueError, RuntimeError, BudgetExhausted, agnes.Fatal, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
