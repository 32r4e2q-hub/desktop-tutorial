#!/usr/bin/env python3
"""Generate the 30 Gangnam Mansion (Episode 14) shots with Agnes Video 2.5 Flash, then render the 180s film.

Uses the verified 2.5 Flash 720P reference-mode payload (9 allowed fields only; seconds as string;
1-5 immutable raw-GitHub PNG URLs pinned to reference/revision.txt) and a shared 12.1-second
request gate (<= 5 requests/minute monthly membership cap) across both POST creates and GET polls.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agnes_video as agnes  # noqa: E402
from throttle import RequestGate  # noqa: E402

BRANCH = "arena/bba78b78-desktop-tutorial"
SLUG = "gangnam1994"
MODEL = "agnes-video-2.5-flash"
SOURCE_SIZE = "720P"
REQUEST_INTERVAL_SECONDS = 12.1
QUEUE_FULL_RETRY_SECONDS = 60.0
CAPACITY_RETRY_SECONDS = 120.0
POLL_INTERVAL_SECONDS = 45.0
SUPPORTED_MODES = {"text", "keyframe", "reference"}
ALLOWED_PAYLOAD_FIELDS = {
    "model", "prompt", "seconds", "size", "aspect_ratio", "mode", "n", "seed", "images",
}
FORBIDDEN_PAYLOAD_FIELDS = {
    "width", "height", "fps", "num_frames", "frame_rate", "duration", "resolution",
    "negative_prompt", "quality", "num_inference_steps",
}
RETRYABLE_CREATE_MARKERS = (
    "video queue is full", "queue is full", "no available channel", "get_channel_failed",
    "temporarily unavailable", "network error",
)
HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
RESULTS = HERE / "results.json"
REFERENCE_DIR = HERE / "reference"
REFERENCE_APPROVALS = REFERENCE_DIR / "approvals.json"
REFERENCE_REVISION = REFERENCE_DIR / "revision.txt"
REPOSITORY = "32r4e2q-hub/desktop-tutorial"
LOCK = threading.RLock()

CHARACTER_REFERENCE_IDS = {f"C{i:02d}": f"C{i:02d}" for i in range(1, 10)}
SCENE_REFERENCE_IDS = {f"S{i:02d}": f"S{i:02d}" for i in range(1, 16)}
PROP_REFERENCE_IDS = {f"P{i:02d}": f"P{i:02d}" for i in range(1, 8)}

DELIVERY_DIR = ROOT / "交付"
DELIVERY_FILM = "江南豪门双尸案_报警的人是凶手_三分钟_带声音.mp4"


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True,
                                   stderr=subprocess.STDOUT, timeout=180)


def reference_asset_ids(shot: dict) -> list[str]:
    """Resolve story design IDs plus character roles to final approved image IDs."""
    asset_ids = [CHARACTER_REFERENCE_IDS[role] for role in shot.get("characters", [])]
    design_refs = str(shot.get("reference_ids", shot.get("references", ""))).split("+")
    for ref in (part.strip().upper() for part in design_refs if part.strip()):
        if ref in SCENE_REFERENCE_IDS:
            asset_ids.append(SCENE_REFERENCE_IDS[ref])
        elif ref in PROP_REFERENCE_IDS:
            asset_ids.append(PROP_REFERENCE_IDS[ref])
        elif ref in CHARACTER_REFERENCE_IDS:
            asset_ids.append(ref)
        else:
            raise ValueError(f"{shot.get('id')}: unknown reference design ID {ref!r}")
    return list(dict.fromkeys(asset_ids))


def reference_image_urls(shot: dict) -> list[str]:
    """Return immutable raw-GitHub URLs after verifying the approved local PNG digests."""
    approvals = read_json(REFERENCE_APPROVALS, {})
    assets = approvals.get("assets", {})
    revision = REFERENCE_REVISION.read_text(encoding="utf-8").strip() if REFERENCE_REVISION.is_file() else ""
    if len(revision) != 40 or any(ch not in "0123456789abcdef" for ch in revision.lower()):
        raise RuntimeError("reference/revision.txt must pin the immutable 40-char commit containing the approved PNGs")
    urls = []
    for asset_id in reference_asset_ids(shot):
        record = assets.get(asset_id, {})
        if record.get("status") != "approved":
            raise RuntimeError(f"{asset_id}: reference is not approved")
        path = HERE / record.get("file", "")
        if not path.is_file() or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"{asset_id}: approved reference PNG is missing or invalid")
        if digest(path) != record.get("sha256"):
            raise RuntimeError(f"{asset_id}: image changed after approval")
        relative = path.relative_to(HERE).as_posix()
        urls.append(f"https://raw.githubusercontent.com/{REPOSITORY}/{revision}/production/{SLUG}/{relative}")
    if not 1 <= len(urls) <= 5:
        raise ValueError(f"{shot.get('id')}: reference mode needs 1–5 images, got {len(urls)}")
    return urls


def style_for(project: dict, shot: dict) -> str:
    variant = shot.get("style_variant", "real")
    if variant == "diagram":
        return project["style_rumor_prefix"].strip()
    if variant != "real":
        raise ValueError(f"{shot.get('id')}: unknown style variant {variant!r}")
    return project["style_prefix"].strip()


def full_prompt(project: dict, shot: dict) -> str:
    """Concatenate 【STYLE】 + verbatim 【角色锚点】 + shot prompt + 【NEGATIVE】."""
    parts = [style_for(project, shot)]
    for role in shot.get("characters", []):
        parts.append(project["characters"][role].strip())
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
    seconds = str(max(4, min(12, int(shot["duration"]))))
    return {
        "model": project["model"],
        "prompt": full_prompt(project, shot),
        "seconds": seconds,
        "size": project.get("source_size", SOURCE_SIZE),
        "aspect_ratio": shot["aspect"],
        "mode": "reference",
        "n": 1,
        "seed": payload_seed(project, shot),
        "images": reference_image_urls(shot),
    }


def request_hash(project: dict, shot: dict) -> str:
    encoded = json.dumps(full_payload(project, shot), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def retryable_create_error(message: str):
    text = str(message or "").lower()
    if "http 408" in text or "http 425" in text:
        return "provider request timeout"
    if "network error" in text or "could not create video task" in text:
        return "network/5xx create outcome"
    for marker in RETRYABLE_CREATE_MARKERS:
        if marker in text:
            return marker
    if "http 5" in text:
        return "provider 5xx"
    return None


class AmbiguousCreateError(RuntimeError):
    """The POST may have reached Agnes; reconcile it instead of risking a duplicate charge."""


def retry_create_until_accepted(create_call, gate, interval: float, on_retry):
    attempts = 0
    while True:
        attempts += 1
        try:
            return create_call()
        except agnes.RateLimited as exc:
            text = str(exc).lower()
            if any(marker in text for marker in ("queue is full", "queue_full", "no available channel",
                                                  "get_channel_failed", "too many pending")):
                floor = QUEUE_FULL_RETRY_SECONDS
            elif "capacity" in text or "concurrent" in text:
                floor = CAPACITY_RETRY_SECONDS
            else:
                floor = 30.0
            cooldown = max(interval, floor, exc.retry_after or 0)
            on_retry(attempts, "HTTP 429", str(exc), cooldown)
            gate.defer(cooldown)
        except agnes.Fatal as exc:
            marker = retryable_create_error(str(exc))
            if marker:
                raise AmbiguousCreateError(
                    f"Create outcome is ambiguous ({marker}); do not resubmit until Agnes is reconciled"
                ) from exc
            raise


def create_contact_sheet(source: Path, shot_id: str, qa_dir: Path) -> dict:
    """Decode-check one clip and make a 5x6 motion-review contact sheet."""
    qa_dir.mkdir(parents=True, exist_ok=True)
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)
    ], text=True))
    video = next((stream for stream in probe["streams"] if stream.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError(f"{shot_id}: no video stream")
    duration = float(probe["format"]["duration"])
    if not 3.75 <= duration <= 9.5 or int(video.get("width", 0)) < 640:
        raise RuntimeError(f"{shot_id}: unsuitable returned clip ({duration:.2f}s, {video.get('width')}px)")
    subprocess.run(["ffmpeg", "-v", "error", "-threads", "2", "-i", str(source),
                    "-map", "0:v:0", "-f", "null", "-"], check=True)
    contact = qa_dir / f"{shot_id}.jpg"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", str(source),
        "-vf", "fps=4,scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,tile=5x6",
        "-frames:v", "1", "-q:v", "4", str(contact),
    ], check=True)
    if not contact.is_file():
        raise RuntimeError(f"{shot_id}: contact sheet was not produced")
    info = {
        "duration_seconds": round(duration, 3),
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": video.get("avg_frame_rate"),
        "bytes": source.stat().st_size,
        "decoded_ok": True,
        "contact_sheet": f"production/{SLUG}/qa/{shot_id}.jpg",
        "visual_review": "pending",
    }
    (qa_dir / f"{shot_id}.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return info


def check_outstanding_tasks(publish: bool) -> int:
    if publish and (os.getenv("GITHUB_ACTIONS") != "true" or git("branch", "--show-current").strip() != BRANCH):
        raise RuntimeError("Publishing is restricted to the fixed Arena branch in GitHub Actions")
    key = os.getenv("AGNES_API_KEY", "").strip()
    if not key:
        raise RuntimeError("AGNES_API_KEY is unavailable; old task status cannot be confirmed")
    base = (os.getenv("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).strip() or agnes.DEFAULT_BASE_URL).rstrip("/")
    doc = read_json(RESULTS, {"shots": {}})
    pending = []
    checked = 0
    observations = {}
    checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    terminal = agnes.COMPLETED_STATES | agnes.FAILED_STATES
    for sid, row in sorted(doc.get("shots", {}).items()):
        video_id = row.get("video_id")
        if not video_id or row.get("status") in {"failed", "cancelled", "canceled", "completed"}:
            continue
        observation = {"video_id": str(video_id), "task_id": row.get("task_id"),
                       "checked_at": checked_at, "state": "unconfirmed"}
        observations[sid] = observation
        query = base + "/agnesapi?" + urllib.parse.urlencode({"video_id": video_id, "model_name": MODEL})
        try:
            response = agnes.http_json("GET", query, key, timeout=60)
        except agnes.TransientError as exc:
            observation["error"] = str(exc).replace(key, "[redacted]")[:300]
            pending.append(sid)
            continue
        code, body, text = response
        if code == 404 and row.get("task_id"):
            legacy = base + "/v1/videos/" + urllib.parse.quote(str(row["task_id"]), safe="")
            try:
                response = agnes.http_json("GET", legacy, key, timeout=60)
                code, body, text = response
            except agnes.TransientError as exc:
                observation["error"] = str(exc).replace(key, "[redacted]")[:300]
                pending.append(sid)
                continue
        observation["http_status"] = code
        if not (200 <= code < 300 and isinstance(body, dict)):
            observation["error"] = agnes.describe_error(body, text, code).replace(key, "[redacted]")[:300]
            pending.append(sid)
            continue
        checked += 1
        state = str(body.get("status") or "unknown").lower()
        observation["state"] = state
        observation["progress"] = body.get("progress")
        print(f"STATUS_CHECK {sid}: {state}", flush=True)
        if state not in terminal:
            pending.append(sid)

    doc["task_status_check"] = {
        "run_id": os.getenv("GITHUB_RUN_ID"), "checked_at": checked_at,
        "checked": checked, "unresolved": pending, "create_requests": 0, "shots": observations,
    }
    RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if publish:
        git("config", "user.name", "github-actions[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        git("add", "--", str(RESULTS.relative_to(ROOT)))
        if subprocess.run(["git", "diff", "--cached", "--quiet", "--", str(RESULTS.relative_to(ROOT))], cwd=ROOT).returncode:
            git("commit", "-m", f"{SLUG}: record status-only Agnes task check", "--", str(RESULTS.relative_to(ROOT)))
            for attempt in range(3):
                try:
                    git("push", "origin", BRANCH)
                    break
                except subprocess.CalledProcessError:
                    if attempt == 2:
                        raise
                    git("pull", "--rebase", "origin", BRANCH)
    return 2 if pending else 0


def retrieve_completed_tasks(publish: bool, selected: set[str] | None = None) -> int:
    if publish and (os.getenv("GITHUB_ACTIONS") != "true" or git("branch", "--show-current").strip() != BRANCH):
        raise RuntimeError("Publishing is restricted to the fixed Arena branch in GitHub Actions")
    key = os.getenv("AGNES_API_KEY", "").strip()
    if not key:
        raise RuntimeError("AGNES_API_KEY is unavailable; completed task outputs cannot be retrieved")
    base = (os.getenv("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).strip() or agnes.DEFAULT_BASE_URL).rstrip("/")
    gate = RequestGate(minimum_interval=REQUEST_INTERVAL_SECONDS)
    doc = read_json(RESULTS, {"shots": {}})
    sources = ROOT / "work" / SLUG / "sources"
    qa_dir = HERE / "qa"
    outcomes = {"run_id": os.getenv("GITHUB_RUN_ID"),
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "create_requests": 0, "downloaded": [], "pending": [], "shots": {}}
    commit_paths = [str(RESULTS.relative_to(ROOT))]
    for sid, row in sorted(doc.get("shots", {}).items()):
        if selected and sid not in selected:
            continue
        video_id = row.get("video_id")
        if not video_id:
            continue
        observation = {"video_id": str(video_id), "task_id": row.get("task_id"), "state": "unconfirmed"}
        outcomes["shots"][sid] = observation
        query = base + "/agnesapi?" + urllib.parse.urlencode({"video_id": video_id, "model_name": MODEL})
        try:
            gate.acquire()
            code, body, text = agnes.http_json("GET", query, key, timeout=60)
            if code == 404 and row.get("task_id"):
                legacy = base + "/v1/videos/" + urllib.parse.quote(str(row["task_id"]), safe="")
                gate.acquire()
                code, body, text = agnes.http_json("GET", legacy, key, timeout=60)
            observation["http_status"] = code
            if not (200 <= code < 300 and isinstance(body, dict)):
                observation["error"] = agnes.describe_error(body, text, code).replace(key, "[redacted]")[:300]
                outcomes["pending"].append(sid)
                continue
            state = str(body.get("status") or "unknown").lower()
            observation["state"] = state
            observation["progress"] = body.get("progress")
            if state in agnes.FAILED_STATES:
                observation["error"] = agnes.describe_error(body, text, code).replace(key, "[redacted]")[:300]
                row.update({"status": "provider_failed", "error": observation["error"]})
                outcomes["pending"].append(sid)
                continue
            if state not in agnes.COMPLETED_STATES:
                outcomes["pending"].append(sid)
                continue
            video_url = agnes.find_video_url(body)
            if not video_url:
                observation["error"] = "Provider reports completed but returned no video URL"
                outcomes["pending"].append(sid)
                continue
            dest = sources / f"{sid}.mp4"
            size = agnes.download(video_url, dest, retries=3, retry_delay=5)
            inspection = create_contact_sheet(dest, sid, qa_dir)
            checksum = digest(dest)
            row.update({"status": "completed", "video_url": video_url, "bytes": size,
                        "sha256": checksum, "inspection": inspection,
                        "provider_status": state, "error": None,
                        "updated_at": outcomes["checked_at"]})
            observation.update({"downloaded": True, "bytes": size, "sha256": checksum, "inspection": inspection})
            outcomes["downloaded"].append(sid)
            commit_paths.extend([
                str((qa_dir / f"{sid}.jpg").relative_to(ROOT)),
                str((qa_dir / f"{sid}.json").relative_to(ROOT)),
            ])
        except (agnes.TransientError, agnes.Fatal, OSError, RuntimeError,
                subprocess.CalledProcessError, ValueError) as exc:
            observation["error"] = str(exc).replace(key, "[redacted]")[:400]
            outcomes["pending"].append(sid)

    source_qc = subprocess.CompletedProcess([], 0)
    if (HERE / "qc.py").is_file():
        source_qc = subprocess.run([sys.executable, str(HERE / "qc.py"), "--sources",
                                    str(sources), "--sources-only"], cwd=ROOT)
        commit_paths.extend([str((qa_dir / "qc-report.json").relative_to(ROOT)),
                             str((qa_dir / "qc-summary.md").relative_to(ROOT))])
    doc["task_retrieval"] = outcomes
    RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if publish:
        git("config", "user.name", "github-actions[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        git("add", "--", *commit_paths)
        if subprocess.run(["git", "diff", "--cached", "--quiet", "--", *commit_paths], cwd=ROOT).returncode:
            git("commit", "-m", f"{SLUG}: retrieve completed Agnes clips and QC sheets", "--", *commit_paths)
            for attempt in range(3):
                try:
                    git("push", "origin", BRANCH)
                    break
                except subprocess.CalledProcessError:
                    if attempt == 2:
                        raise
                    git("pull", "--rebase", "origin", BRANCH)
    if source_qc.returncode:
        return 1
    return 2 if outcomes["pending"] else 0


def publish_delivery(film: Path) -> dict:
    """Copy final master and sidecars into 交付/."""
    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
    work = ROOT / "work" / SLUG / "edit"
    sources = [
        (film, DELIVERY_FILM),
        (film.parent / "江南豪门双尸案_Cover.jpg", "江南豪门双尸案_Cover.jpg"),
        (film.with_suffix(".srt"), "江南豪门双尸案_Subtitles.srt"),
        (work / "voiceover.wav", "江南豪门双尸案_Narration.wav"),
        (work / "technical-report.json", "江南豪门双尸案_Technical_Report.json"),
    ]
    copied = {}
    for source, name in sources:
        if source.is_file():
            destination = DELIVERY_DIR / name
            shutil.copy2(source, destination)
            copied[name] = {"bytes": destination.stat().st_size, "sha256": digest(destination)}
    return copied


def commit_delivery(message: str) -> None:
    """Commit provenance, sidecars, and the directly downloadable final MP4."""
    subprocess.run(["git", "config", "core.sparseCheckout", "false"], cwd=ROOT, check=False)
    paths = [str(RESULTS.relative_to(ROOT)), str((DELIVERY_DIR / DELIVERY_FILM).relative_to(ROOT))]
    for name in ("qc-report.json", "qc-summary.md", "narration-fit.md", "verify-master.json"):
        report = HERE / "qa" / name
        if report.is_file():
            paths.append(str(report.relative_to(ROOT)))
    for name in ("江南豪门双尸案_Cover.jpg", "江南豪门双尸案_Subtitles.srt", "江南豪门双尸案_Technical_Report.json"):
        sidecar = DELIVERY_DIR / name
        if sidecar.is_file():
            paths.append(str(sidecar.relative_to(ROOT)))
    git("add", "-f", "--", *paths)
    if not subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=ROOT).returncode:
        return
    git("commit", "-m", message, "--", *paths)
    for attempt in range(5):
        try:
            git("push", "origin", BRANCH)
            return
        except subprocess.CalledProcessError:
            if attempt == 4:
                raise
            git("pull", "--rebase", "origin", BRANCH)


def restore_sources(project: dict, results: dict, sources: Path) -> list[str]:
    restored = []
    sources.mkdir(parents=True, exist_ok=True)
    for shot in project["shots"]:
        sid = shot["id"]
        receipt = results.get("shots", {}).get(sid, {})
        dest = sources / f"{sid}.mp4"
        if not receipt.get("video_url") or not receipt.get("sha256"):
            raise RuntimeError(f"{sid}: no Agnes receipt to restore from")
        if dest.is_file() and digest(dest) == receipt["sha256"] and dest.stat().st_size == receipt.get("bytes"):
            continue
        print(f"RESTORE {sid} from Agnes receipt", flush=True)
        agnes.download(receipt["video_url"], dest, retries=3, retry_delay=5)
        if digest(dest) != receipt["sha256"] or dest.stat().st_size != receipt.get("bytes"):
            raise RuntimeError(f"{sid}: restored footage does not match the original receipt")
        restored.append(sid)
    return restored


def prepare_prompt_changes(project: dict, results: dict, shots: list[dict]) -> list[str]:
    rows = results.setdefault("shots", {})
    history = results.setdefault("previous_results", {})
    changed = []
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for shot in shots:
        sid = shot["id"]
        wanted_hash = request_hash(project, shot)
        old = dict(rows.get(sid, {}))
        if old.get("request_hash") == wanted_hash:
            continue
        if old:
            history.setdefault(sid, []).append(old)
        rows[sid] = {
            "id": sid, "request_hash": wanted_hash, "status": "retrying_create",
            "reused_existing_asset": False, "updated_at": now,
        }
        changed.append(sid)
    return changed


def validate(project: dict, require_audio: bool = True) -> None:
    shots = project.get("shots", [])
    if project.get("target_duration") != 180 or len(shots) != 30:
        raise ValueError("Expected 30 shots and an exact 180-second film")
    if (project.get("width"), project.get("height"), project.get("fps")) != (1920, 1080, 24):
        raise ValueError("Output must be 1920x1080 at 24fps")
    if project.get("model") != MODEL or project.get("source_size") != SOURCE_SIZE:
        raise ValueError("The required source model/size is Agnes Video 2.5 Flash at 720P")
    if not project.get("style_prefix", "").startswith("【STYLE】"):
        raise ValueError("STYLE must be the first text in every prompt")
    if not project.get("negative_prompt", "").startswith("【NEGATIVE】"):
        raise ValueError("NEGATIVE block is missing")
    ids = [shot.get("id") for shot in shots]
    if len(ids) != 30 or len(set(ids)) != 30:
        raise ValueError("Shot IDs must be unique")
    cursor = 0
    for shot in shots:
        duration = int(shot["duration"])
        if shot["start"] != cursor or not 4 <= duration <= 9:
            raise ValueError(f"Invalid or non-contiguous timeline at {shot.get('id')}")
        if shot.get("kind") != "agnes" or not shot.get("prompt", "").strip():
            raise ValueError(f"Every shot must be a real Agnes video clip: {shot.get('id')}")
        if shot.get("seconds") != duration or shot.get("aspect") != "16:9" or shot.get("source_size") != SOURCE_SIZE:
            raise ValueError(f"Invalid duration/aspect/source size at {shot['id']}")
        for role in shot.get("characters", []):
            if role not in project["characters"]:
                raise ValueError(f"Missing character setting {role} in {shot['id']}")
        prompt = full_prompt(project, shot)
        if not prompt.startswith("【STYLE") or not prompt.endswith(project["negative_prompt"].strip()):
            raise ValueError(f"Automatic STYLE/NEGATIVE concatenation failed for {shot['id']}")
        if not shot.get("narration", "").strip():
            raise ValueError(f"Every shot needs its own narration line: {shot['id']}")
        if shot["narration_id"] not in {c["id"] for c in project["chapters"]}:
            raise ValueError(f"Unknown narration chapter in {shot['id']}")
        payload = full_payload(project, shot)
        if set(payload) != ALLOWED_PAYLOAD_FIELDS:
            raise ValueError(f"Unexpected 2.5 Flash payload fields for {shot['id']}: {sorted(payload)}")
        if payload.get("model") != MODEL:
            raise ValueError(f"Wrong Agnes model for {shot['id']}")
        if not isinstance(payload.get("seconds"), str) or not payload["seconds"].isdigit() or int(payload["seconds"]) != duration:
            raise ValueError(f"2.5 Flash seconds must be the duration string for {shot['id']}")
        if payload.get("size") != SOURCE_SIZE or payload.get("aspect_ratio") != "16:9" or payload.get("mode") != "reference" or payload.get("n") != 1:
            raise ValueError(f"Invalid 2.5 Flash size/aspect/mode/count for {shot['id']}")
        if not isinstance(payload.get("images"), list) or not 1 <= len(payload["images"]) <= 5:
            raise ValueError(f"Reference mode needs 1–5 approved images for {shot['id']}")
        if FORBIDDEN_PAYLOAD_FIELDS.intersection(payload):
            raise ValueError(f"2.5 Flash rejects fields: {sorted(FORBIDDEN_PAYLOAD_FIELDS.intersection(payload))}")
        if payload["prompt"] != prompt:
            raise ValueError(f"2.5 Flash prompt must carry STYLE and NEGATIVE inline for {shot['id']}")
        if payload["seed"] != payload_seed(project, shot):
            raise ValueError(f"Character seed was not applied for {shot['id']}")
        cursor += duration
    if cursor != 180:
        raise ValueError(f"Timeline is {cursor}s, not 180s")
    chapters = project.get("chapters", [])
    if len(chapters) != 9 or sum(int(c["duration"]) for c in chapters) != 180:
        raise ValueError("Expected nine narration chapters covering exactly 180 seconds")
    ch_cursor = 0
    for chapter in chapters:
        if chapter["start"] != ch_cursor or not chapter.get("text", "").strip():
            raise ValueError("Narration chapters must be complete and contiguous")
        ch_cursor += chapter["duration"]

    for ref in project.get("reference_images", []):
        if not (HERE / ref["file"]).is_file():
            raise ValueError("Missing approved reference image: " + ref["file"])

    if not require_audio:
        return

    manifest = read_json(HERE / "audio" / "manifest.json", {})
    records = {row.get("id"): row for row in manifest.get("clips", [])}
    narration_spec = project.get("narration_spec", {})
    expected_voice = narration_spec.get("voice_id")
    if manifest.get("voice") != expected_voice or manifest.get("alignment") != "one-clip-one-shot-one-caption":
        raise ValueError("Narration manifest must use the selected voice and shot-locked alignment")
    if manifest.get("slowdown_allowed") is not False:
        raise ValueError("Narration must not be slowed down to fill shot durations")
    if len(records) != len(shots):
        raise ValueError("Narration manifest must contain exactly one clip per shot")
    for shot in shots:
        row = records.get(shot["id"], {})
        audio = HERE / "audio" / row.get("file", "missing.mp3")
        if (row.get("text") != shot.get("narration") or row.get("voice_id") != expected_voice
                or row.get("narration_id") != shot["narration_id"]
                or row.get("target_start") != shot["start"]
                or row.get("target_duration") != shot["duration"]
                or not audio.is_file()):
            raise ValueError("Shot-locked narration text/file/timing mismatch: " + shot["id"])
        if row.get("sha256") != digest(audio):
            raise ValueError("Narration SHA-256 mismatch: " + shot["id"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--check-outstanding", action="store_true")
    parser.add_argument("--retrieve-completed", action="store_true")
    parser.add_argument("--payload", default="{}", help='JSON, e.g. {"only":"S01","workers":2}')
    parser.add_argument("--clips-only", action="store_true")
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()

    project = read_json(PLAN, {})
    if args.check_outstanding:
        return check_outstanding_tasks(args.publish)
    options = json.loads(args.payload or "{}")
    if args.retrieve_completed:
        selected_value = options.get("only", "")
        if not isinstance(selected_value, str):
            raise ValueError("payload.only must be a comma-separated string of shot IDs")
        selected = {part.strip() for part in selected_value.split(",") if part.strip()}
        if selected - {shot["id"] for shot in project.get("shots", [])}:
            raise ValueError("Unknown retrieval shot(s)")
        return retrieve_completed_tasks(args.publish, selected or None)

    mode = str(options.get("mode") or "").strip()
    if not mode and options.get("only"):
        mode = "clips"
    if mode == "clips":
        args.clips_only = True
    elif mode == "render":
        args.render_only = True
    elif mode not in {"", "full", "qc"}:
        raise ValueError("payload.mode must be clips, render, full or qc")

    if mode == "qc":
        validate(project, require_audio=True)
        film = DELIVERY_DIR / DELIVERY_FILM
        if not film.is_file():
            raise RuntimeError(f"QC requested but {film} does not exist")
        if os.getenv("GITHUB_ACTIONS") == "true":
            git("config", "user.name", "github-actions[bot]")
            git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        sources = ROOT / "work" / SLUG / "sources"
        doc = read_json(RESULTS, {"shots": {}})
        restore_sources(project, doc, sources)
        code = subprocess.run([sys.executable, str(HERE / "qc.py"), "--sources", str(sources), "--film", str(film)], cwd=ROOT).returncode
        fit = subprocess.run([sys.executable, str(HERE / "narration_fit.py")], cwd=ROOT, capture_output=True, text=True)
        verify = subprocess.run([
            sys.executable, str(ROOT / "production" / "verify_master.py"),
            "--film", str(film), "--story", str(PLAN),
            "--srt", str(DELIVERY_DIR / "江南豪门双尸案_Subtitles.srt"),
            "--json", str(HERE / "qa" / "verify-master.json"),
        ], cwd=ROOT)
        if fit.returncode or verify.returncode:
            code = 1
        if args.publish:
            git("add", "-f", "--", f"production/{SLUG}/qa", "交付")
            if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
                git("commit", "-m", f"{SLUG}: 成片质检报告")
                for attempt in range(3):
                    try:
                        git("push", "origin", BRANCH)
                        break
                    except subprocess.CalledProcessError:
                        if attempt == 2:
                            raise
                        git("pull", "--rebase", "origin", BRANCH)
        return code

    render_now = not args.clips_only
    validate(project, require_audio=(render_now or args.render_only))
    if args.validate:
        print("VALID: 180 seconds, 30 Agnes Video 2.5 Flash clips (720P source), 1080P delivery, 30 shot-locked lines, 9 chapters and 31 approved references")
        return 0

    if args.render_only:
        doc = read_json(RESULTS, {"project": project["title"], "model": project["model"], "shots": {}})
        sources = ROOT / "work" / SLUG / "sources"
        sources.mkdir(parents=True, exist_ok=True)
        exports = ROOT / "work" / SLUG / "clips"
        exports.mkdir(parents=True, exist_ok=True)
        missing = [shot["id"] for shot in project["shots"]
                   if doc.get("shots", {}).get(shot["id"], {}).get("status") != "completed"]
        if missing:
            raise RuntimeError("Render requested but these clips are not completed: " + ", ".join(missing))
        restore_sources(project, doc, sources)
        if os.getenv("GITHUB_ACTIONS") == "true":
            git("config", "user.name", "github-actions[bot]")
            git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        output = exports / project["film_name"]
        subprocess.run([
            sys.executable, str(HERE / "render.py"),
            "--sources", str(sources), "--work", str(ROOT / "work" / SLUG / "edit"),
            "--output", str(output),
        ], cwd=ROOT, check=True)
        qc = subprocess.run([sys.executable, str(HERE / "qc.py"), "--sources", str(sources),
                             "--film", str(output), "--srt", str(output.with_suffix(".srt"))], cwd=ROOT)
        fit = subprocess.run([sys.executable, str(HERE / "narration_fit.py")], cwd=ROOT)
        verify = subprocess.run([
            sys.executable, str(ROOT / "production" / "verify_master.py"),
            "--film", str(output), "--story", str(PLAN),
            "--srt", str(output.with_suffix(".srt")),
            "--json", str(HERE / "qa" / "verify-master.json"),
        ], cwd=ROOT)
        if qc.returncode or fit.returncode or verify.returncode:
            raise RuntimeError("Technical QC, narration-fit, or verify_master failed; refusing delivery")
        delivered = publish_delivery(output)
        doc["phase"] = "first_cut_ready"
        doc["review"] = {
            "status": "technical_pass_visual_review_pending",
            "visual_review_required": True,
            "note": "Technical, narration-fit, and verify_master checks passed; human visual review remains required.",
        }
        doc["delivery"] = {
            "film": str(output.relative_to(ROOT)),
            "duration_seconds": 180,
            "width": 1920, "height": 1080, "fps": 24,
            "cover": str((output.parent / "江南豪门双尸案_Cover.jpg").relative_to(ROOT)),
            "delivered": delivered,
        }
        RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.publish:
            commit_delivery(f"{SLUG}: 180秒成片、封面、字幕与技术校验报告")
        print("FIRST_CUT_READY " + output.name, flush=True)
        return 0

    requested = options.get("only", "")
    if not isinstance(requested, str):
        raise ValueError("payload.only must be a comma-separated string of shot IDs")
    only = {part.strip() for part in requested.split(",") if part.strip()}
    by_id = {shot["id"]: shot for shot in project["shots"]}
    if only - set(by_id):
        raise ValueError("Unknown Agnes shot(s): " + ", ".join(sorted(only - set(by_id))))
    selected = [shot for shot in project["shots"] if not only or shot["id"] in only]
    workers = min(2, max(1, int(options.get("workers", 2))))
    gate = RequestGate(minimum_interval=REQUEST_INTERVAL_SECONDS)
    deadline = float("inf")
    if args.publish:
        if os.getenv("GITHUB_ACTIONS") != "true" or git("branch", "--show-current").strip() != BRANCH:
            raise RuntimeError("Publishing is restricted to the fixed Arena branch in GitHub Actions")
        git("config", "user.name", "github-actions[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")

    doc = read_json(RESULTS, {"project": project["title"], "model": project["model"], "shots": {}})
    doc["model"] = MODEL
    doc["source_size"] = SOURCE_SIZE
    doc.pop("provider_outage", None)
    doc["phase"] = "generating_sources"
    doc["required_generated_shots"] = [shot["id"] for shot in project["shots"]]
    doc["workflow_policy"] = "agnes-video-2.5-flash-720p-reference-upscale-180s-30shots"
    doc["rate_policy"] = {
        "minimum_request_interval_seconds": REQUEST_INTERVAL_SECONDS,
        "max_requests_per_minute": 5,
        "workers_max": 2,
        "create_before_poll": True,
        "shared_create_poll_gate": True,
        "retry_after_respected": True,
        "queue_full_retry_seconds": QUEUE_FULL_RETRY_SECONDS,
        "capacity_retry_seconds": CAPACITY_RETRY_SECONDS,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
    }
    doc["review"] = {"status": "pending", "visual_review_required": True,
                     "note": "A decoded clip and contact sheet are not a human visual sign-off."}
    base = os.getenv("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).rstrip("/")
    key = os.getenv("AGNES_API_KEY", "").strip()
    if args.publish and not key:
        raise RuntimeError("AGNES_API_KEY is unavailable; configure the repository secret before publishing")
    sources = ROOT / "work" / SLUG / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    qa_dir = HERE / "qa"
    exports = ROOT / "work" / SLUG / "clips"
    exports.mkdir(parents=True, exist_ok=True)

    def checkpoint(label: str, shot_id: str | None = None, files=(), publish=True, **values):
        with LOCK:
            if shot_id:
                row = doc.setdefault("shots", {}).setdefault(shot_id, {"id": shot_id})
                row.update(values)
                row["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            doc["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            doc["run_id"] = os.getenv("GITHUB_RUN_ID")
            RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if args.publish and publish:
                paths = [str(RESULTS.relative_to(ROOT))]
                paths.extend(str(Path(path).resolve().relative_to(ROOT)) for path in files)
                git("add", "--", *paths)
                if subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=ROOT).returncode:
                    git("commit", "-m", f"{SLUG}: {label}", "--", *paths)
                    for attempt in range(3):
                        try:
                            git("push", "origin", BRANCH)
                            break
                        except subprocess.CalledProcessError:
                            if attempt == 2:
                                raise
                            git("pull", "--rebase", "origin", BRANCH)
            print("PRODUCTION_STATUS " + label, flush=True)

    def finish(shot: dict, receipt: dict, wanted_hash: str, reused: bool = False) -> bool:
        sid = shot["id"]
        dest = sources / f"{sid}.mp4"
        if not dest.exists() or digest(dest) != receipt["sha256"]:
            agnes.download(receipt["video_url"], dest, retries=3, retry_delay=5)
        if dest.stat().st_size != receipt["bytes"] or digest(dest) != receipt["sha256"]:
            raise RuntimeError(f"{sid}: downloaded bytes differ from the Agnes receipt")
        info = create_contact_sheet(dest, sid, qa_dir)
        shutil.copy2(dest, exports / dest.name)
        checkpoint(sid + " generated and decoded", sid, files=[qa_dir / f"{sid}.jpg", qa_dir / f"{sid}.json"],
                   status="completed", request_hash=wanted_hash, video_url=receipt["video_url"],
                   sha256=receipt["sha256"], bytes=receipt["bytes"], inspection=info,
                   reused_existing_asset=reused, visual_review="pending", error=None)
        return True

    def paced_create(sid: str, payload: dict):
        with LOCK:
            attempts = int(doc.get("shots", {}).get(sid, {}).get("create_attempts", 0))

        def create():
            nonlocal attempts
            attempts += 1
            checkpoint(sid + " waiting for Agnes create slot", sid, publish=False,
                       status="waiting_create_slot", create_attempts=attempts, error=None)
            gate.acquire_creation(deadline)
            return agnes.create_task(base, key, payload, retries=1, retry_delay=1)

        def record_retry(attempt, marker, message, cooldown):
            redacted = str(message).replace(key, "[redacted]")[:600]
            with LOCK:
                doc["provider_outage"] = {
                    "model": MODEL, "reason": marker, "last_error": redacted,
                    "create_attempts": attempts, "retry_interval_seconds": cooldown,
                    "last_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            checkpoint(sid + " provider busy; retrying", sid,
                       publish=(attempt == 1 or attempt % 10 == 0),
                       status="rate_limited" if marker == "HTTP 429" else "provider_cooldown",
                       capacity_error=marker, create_attempts=attempts,
                       applied_cooldown_seconds=cooldown, error=redacted)
            print(f"{sid}: {marker}; retrying create in {cooldown:g}s (attempt {attempt})", flush=True)

        created = retry_create_until_accepted(create, gate, REQUEST_INTERVAL_SECONDS, record_retry)
        with LOCK:
            doc.pop("provider_outage", None)
        return created

    def prequeue_tasks(shots: list[dict]) -> bool:
        """Submit all 30 shots serially at 12.1s spacing (<= 5/min) before polling."""
        for shot in shots:
            sid = shot["id"]
            payload = full_payload(project, shot)
            wanted_hash = request_hash(project, shot)
            with LOCK:
                old = dict(doc.setdefault("shots", {}).get(sid, {}))
            has_receipt = (old.get("request_hash") == wanted_hash and old.get("video_url")
                           and old.get("sha256") and old.get("bytes"))
            if has_receipt:
                continue
            if old.get("video_id") or old.get("task_id"):
                if old.get("request_hash") != wanted_hash:
                    checkpoint(sid + " blocked: older task needs reconciliation", sid,
                               status="create_unknown",
                               error="Existing task has a different request hash; refusing duplicate POST")
                    return False
                if old.get("video_id"):
                    continue
                return False
            if old.get("video_url"):
                return False
            safe_to_create = {"", "retrying_create", "rate_limited", "blocked"}
            if old.get("status", "") not in safe_to_create:
                return False
            if not key:
                checkpoint(sid + " blocked", sid, status="blocked", request_hash=wanted_hash,
                           error="AGNES_API_KEY is unavailable to this workflow")
                return False

            checkpoint(sid + " submitting", sid, status="submitting", request_hash=wanted_hash,
                       request_payload=payload, error=None)
            try:
                created = paced_create(sid, payload)
            except AmbiguousCreateError as exc:
                checkpoint(sid + " create outcome unknown; stopping before duplicate POST", sid,
                           status="create_unknown", request_hash=wanted_hash,
                           request_payload=payload, error=str(exc).replace(key, "[redacted]")[:600])
                return False
            except Exception as exc:
                checkpoint(sid + " create rejected; stopping batch", sid,
                           status="failed", request_hash=wanted_hash,
                           request_payload=payload,
                           error=str(exc).replace(key, "[redacted]")[:600])
                return False

            video_id = created.get("video_id") or created.get("id") or created.get("task_id")
            task_id = created.get("task_id") or created.get("id") or video_id
            if not video_id:
                checkpoint(sid + " create response missing task ID", sid,
                           status="create_unknown", request_hash=wanted_hash,
                           request_payload=payload, error="Agnes returned no task identifier")
                return False
            with LOCK:
                attempts = int(doc.get("shots", {}).get(sid, {}).get("create_attempts", 1))
            checkpoint(sid + " queued", sid, status="queued", request_hash=wanted_hash,
                       request_payload=payload, video_id=str(video_id), task_id=str(task_id or ""),
                       requested_seconds=float(payload["seconds"]), requested_size=payload["size"],
                       create_attempts=attempts)
        return True

    def reset_shot_for_retry(sid: str, wanted_hash: str, dest: Path, error: str) -> None:
        with LOCK:
            row = dict(doc.setdefault("shots", {}).get(sid, {"id": sid}))
            if row:
                doc.setdefault("previous_results", {}).setdefault(sid, []).append(row)
            doc["shots"][sid] = {"id": sid, "request_hash": wanted_hash}
        dest.unlink(missing_ok=True)
        (qa_dir / f"{sid}.jpg").unlink(missing_ok=True)
        (qa_dir / f"{sid}.json").unlink(missing_ok=True)
        (exports / dest.name).unlink(missing_ok=True)
        checkpoint(sid + " asset/task failed; retrying", sid, status="retrying_create",
                   request_hash=wanted_hash, video_id=None, task_id=None, video_url=None,
                   sha256=None, bytes=None, error=error[:600])
        gate.defer(REQUEST_INTERVAL_SECONDS)

    def generate_one(shot: dict) -> bool:
        sid = shot["id"]
        payload = full_payload(project, shot)
        wanted_hash = request_hash(project, shot)
        with LOCK:
            old = dict(doc.setdefault("shots", {}).get(sid, {}))
        dest = sources / f"{sid}.mp4"
        try:
            if (old.get("request_hash") == wanted_hash and old.get("video_url")
                    and old.get("sha256") and old.get("bytes")):
                try:
                    return finish(shot, old, wanted_hash, reused=True)
                except (agnes.Fatal, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
                    reset_shot_for_retry(sid, wanted_hash, dest, str(exc))
                    old = {"id": sid, "request_hash": wanted_hash, "status": "retrying_create"}
            if (old.get("status") in {"submitting", "waiting_create_slot", "create_unknown", "failed", "provider_failed"}
                    or (old.get("task_id") and not old.get("video_id"))
                    or (old.get("video_url") and not old.get("bytes"))):
                return False
            stale_without_saved_task = (
                old.get("status") not in {"completed", "retrying_create"}
                and not old.get("video_url") and not old.get("video_id")
            )
            if old and (old.get("request_hash") != wanted_hash or stale_without_saved_task):
                with LOCK:
                    doc.setdefault("previous_results", {}).setdefault(sid, []).append(old)
                    doc["shots"][sid] = {"id": sid, "request_hash": wanted_hash}
                old = {"id": sid, "request_hash": wanted_hash, "status": "retrying_create"}
            if not key:
                checkpoint(sid + " blocked", sid, status="blocked", request_hash=wanted_hash,
                           error="AGNES_API_KEY is unavailable to this workflow")
                return False

            video_id, task_id = old.get("video_id"), old.get("task_id")
            poll_retries = 0
            while True:
                try:
                    if not video_id:
                        checkpoint(sid + " submitting", sid, status="submitting",
                                   request_hash=wanted_hash, error=None)
                        created = paced_create(sid, payload)
                        video_id = created.get("video_id") or created.get("id") or created.get("task_id")
                        task_id = created.get("task_id") or created.get("id")
                        if not video_id:
                            raise agnes.Fatal("Agnes returned no task identifier")
                        video_id, task_id = str(video_id), str(task_id or "")
                        checkpoint(sid + " queued", sid, status="queued", video_id=video_id,
                                   task_id=task_id, requested_seconds=float(payload["seconds"]),
                                   requested_size=payload["size"])
                    else:
                        print(sid + ": resuming saved Agnes task", flush=True)
                    remaining = deadline - time.monotonic()
                    final, url = agnes.poll_task(
                        base, key, MODEL, str(video_id), str(task_id) if task_id else None,
                        interval=POLL_INTERVAL_SECONDS, timeout=min(1500, remaining), max_failures=12,
                        before_request=lambda: gate.wait_unblocked(deadline), rate_limit_callback=gate.defer,
                    )
                    size = agnes.download(url, dest, retries=3, retry_delay=5)
                    receipt = {"video_url": url, "bytes": size, "sha256": digest(dest), "request_hash": wanted_hash}
                    checkpoint(sid + " Agnes task completed", sid, status="downloaded", video_url=url,
                               bytes=size, sha256=receipt["sha256"], reported_size=final.get("size"),
                               reported_seconds=final.get("seconds"), error=None)
                    try:
                        return finish(shot, receipt, wanted_hash)
                    except (agnes.Fatal, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
                        reset_shot_for_retry(sid, wanted_hash, dest, str(exc))
                        video_id = task_id = None
                        continue
                except AmbiguousCreateError as exc:
                    message = str(exc).replace(key, "[redacted]")[:600]
                    checkpoint(sid + " create outcome unknown; reconcile before retry", sid,
                               status="create_unknown", request_hash=wanted_hash,
                               request_payload=payload, error=message)
                    return False
                except agnes.Fatal as exc:
                    message = str(exc)
                    lowered = message.lower()
                    if "video task failed" in lowered or "task failed" in lowered:
                        reset_shot_for_retry(sid, wanted_hash, dest, message)
                        video_id = task_id = None
                        continue
                    transient_poll = (
                        retryable_create_error(message) is not None
                        or "timed out after" in lowered
                        or "gave up after" in lowered
                        or "could not download" in lowered
                    )
                    if not transient_poll:
                        raise
                    poll_retries += 1
                    cooldown = REQUEST_INTERVAL_SECONDS
                    checkpoint(sid + " poll/download transient error; retrying", sid,
                               status="poll_retry", poll_retries=poll_retries,
                               applied_cooldown_seconds=cooldown,
                               error=message.replace(key, "[redacted]")[:600])
                    gate.defer(cooldown)
                    continue
        except Exception as exc:
            error = str(exc).replace(key, "[redacted]") if key else str(exc)
            checkpoint(sid + " failed", sid, status="failed", error=error[:600])
            return False

    subprocess.run([sys.executable, str(HERE / "build_story.py")], cwd=ROOT, check=True)
    project = read_json(PLAN, {})
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["ffprobe", "-version"], check=True, stdout=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("ffmpeg and ffprobe are required on the Actions runner") from exc

    checkpoint("Agnes generation started")
    changes = prepare_prompt_changes(project, doc, selected)
    if changes:
        checkpoint("queued prompt-refresh shots: " + ",".join(changes))
    if prequeue_tasks(selected):
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(generate_one, selected))
    else:
        outcomes = [False]

    if not all(outcomes):
        doc["phase"] = "generation_incomplete"
        checkpoint("generation incomplete")
        return 1
    if only:
        doc["phase"] = "selected_sources_ready"
        checkpoint("selected Agnes sources ready")
        return 0
    if args.clips_only:
        doc["phase"] = "sources_ready_pending_render"
        checkpoint("all 30 Agnes clips ready; waiting for voice clips / render trigger")
        return 0

    doc["phase"] = "rendering_first_cut"
    checkpoint("all Agnes shots ready; rendering master")
    output = exports / project["film_name"]
    subprocess.run([
        sys.executable, str(HERE / "render.py"),
        "--sources", str(sources), "--work", str(ROOT / "work" / SLUG / "edit"),
        "--output", str(output),
    ], cwd=ROOT, check=True)
    delivered = publish_delivery(output)
    doc["phase"] = "first_cut_ready"
    doc["delivery"] = {
        "film": str(output.relative_to(ROOT)), "duration_seconds": 180,
        "width": 1920, "height": 1080, "fps": 24,
        "cover": str((output.parent / "江南豪门双尸案_Cover.jpg").relative_to(ROOT)),
        "delivered": delivered,
    }
    checkpoint(f"{SLUG} 180-second cut ready", publish=False)
    if args.publish:
        commit_delivery(f"{SLUG}: 180秒成片、封面、字幕与技术校验报告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
