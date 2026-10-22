#!/usr/bin/env python3
"""Generate the 29 Somerton shots with Agnes Video 2.5 Flash, then render the 180s first cut.

The 2.5 Flash endpoint requires the documented 720P payload shape (seconds as a string,
size/aspect_ratio/mode/n); clips are normalized and upscaled to the 1920x1080 delivery master.
All generated footage is downloaded to ignored ``work/``. Only JSON provenance and small
contact sheets are checkpointed into the fixed Arena branch. No still-image substitute is used.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agnes_video as agnes  # noqa: E402
from throttle import BudgetExhausted, RequestGate  # noqa: E402

BRANCH = "arena/dc7c8423-desktop-tutorial"
MODEL = "agnes-video-2.5-flash"
SOURCE_SIZE = "720P"
SUPPORTED_MODES = {"text", "keyframe", "reference"}
ALLOWED_PAYLOAD_FIELDS = {
    "model", "prompt", "seconds", "size", "aspect_ratio", "mode", "n", "seed",
}
FORBIDDEN_PAYLOAD_FIELDS = {
    "width", "height", "fps", "num_frames", "frame_rate", "duration", "resolution",
    "negative_prompt", "quality", "num_inference_steps",
}
CAPACITY_FAILURE_POLICIES = (
    ("video queue is full", 90, 24),
    ("queue is full", 90, 24),
    ("no available channel", 300, 3),
    ("get_channel_failed", 300, 3),
    ("temporarily unavailable", 300, 3),
)
HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
RESULTS = HERE / "results.json"
LOCK = threading.RLock()
CAPACITY_LOCK = threading.Lock()
CAPACITY_ABORT = threading.Event()
CAPACITY_STATE = {"consecutive": 0, "last_error": None}


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


class ProviderCapacity(RuntimeError):
    """Agnes rejected creation because its model channel or video queue is unavailable."""


def capacity_failure_policy(message: str):
    """Return (marker, cooldown, consecutive limit) for known transient provider-capacity errors."""
    text = str(message or "").lower()
    for marker, cooldown, limit in CAPACITY_FAILURE_POLICIES:
        if marker in text:
            return marker, cooldown, limit
    if "http 5" in text:
        return "provider 5xx", 120, 3
    return None


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def full_prompt(project: dict, shot: dict) -> str:
    """Apply the requested prefix/character/negative rules to every generated shot."""
    parts = [project["style_prefix"].strip()]
    for role in shot.get("characters", []):
        parts.append(project["characters"][role].strip())
    parts.append(shot["prompt"].strip())
    parts.append(project["negative_prompt"].strip())
    return "\n\n".join(parts)


def full_payload(project: dict, shot: dict) -> dict:
    """2.5 Flash schema copied from the repo's tested Agnes 2.5 implementation.

    Important: this endpoint rejects width/height/fps/num_frames/frame_rate/resolution and a
    separate negative_prompt field. Negative constraints therefore remain appended to prompt.
    """
    seconds = str(max(4, min(12, int(shot["duration"]))))
    return {
        "model": project["model"],
        "prompt": full_prompt(project, shot),
        "seconds": seconds,
        "size": project.get("source_size", SOURCE_SIZE),
        "aspect_ratio": shot["aspect"],
        "mode": "text",
        "n": 1,
        "seed": int(shot["seed"]),
    }


def request_hash(project: dict, shot: dict) -> str:
    encoded = json.dumps(full_payload(project, shot), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate(project: dict) -> None:
    shots = project.get("shots", [])
    if project.get("target_duration") != 180 or len(shots) != 29:
        raise ValueError("Expected 29 shots and an exact 180-second film")
    if (project.get("width"), project.get("height"), project.get("fps")) != (1920, 1080, 30):
        raise ValueError("Output must be 1920x1080 at 30fps")
    if project.get("model") != MODEL or project.get("source_size") != SOURCE_SIZE:
        raise ValueError("The required source model/size is Agnes Video 2.5 Flash at 720P")
    if not project.get("style_prefix", "").startswith("【STYLE】"):
        raise ValueError("STYLE must be the first text in every prompt")
    if not project.get("negative_prompt", "").startswith("【NEGATIVE】"):
        raise ValueError("NEGATIVE block is missing")
    ids = [shot.get("id") for shot in shots]
    if len(ids) != 29 or len(set(ids)) != 29:
        raise ValueError("Shot IDs must be unique")
    cursor = 0
    for shot in shots:
        duration = int(shot["duration"])
        if shot["start"] != cursor or not 4 <= duration <= 9:
            raise ValueError(f"Invalid or non-contiguous timeline at {shot.get('id')}")
        if shot.get("kind") != "agnes" or not shot.get("prompt", "").strip():
            raise ValueError(f"Every shot must be a real Agnes video clip: {shot.get('id')}")
        if shot.get("seconds") != duration or shot.get("aspect") != "16:9" \
                or shot.get("source_size") != SOURCE_SIZE:
            raise ValueError(f"Invalid duration/aspect/source size at {shot['id']}")
        for role in shot.get("characters", []):
            if role not in project["characters"]:
                raise ValueError(f"Missing character setting {role} in {shot['id']}")
        prompt = full_prompt(project, shot)
        if not prompt.startswith("【STYLE】") or not prompt.endswith(project["negative_prompt"].strip()):
            raise ValueError(f"Automatic STYLE/NEGATIVE concatenation failed for {shot['id']}")
        if shot["narration_id"] not in {c["id"] for c in project["chapters"]}:
            raise ValueError(f"Unknown narration chapter in {shot['id']}")
        payload = full_payload(project, shot)
        if set(payload) != ALLOWED_PAYLOAD_FIELDS:
            raise ValueError(f"Unexpected 2.5 Flash payload fields for {shot['id']}: {sorted(payload)}")
        if payload.get("model") != MODEL:
            raise ValueError(f"Wrong Agnes model for {shot['id']}")
        if not isinstance(payload.get("seconds"), str) or not payload["seconds"].isdigit() \
                or int(payload["seconds"]) != duration:
            raise ValueError(f"2.5 Flash seconds must be the duration string for {shot['id']}")
        if payload.get("size") != SOURCE_SIZE or payload.get("aspect_ratio") != "16:9" \
                or payload.get("mode") not in SUPPORTED_MODES or payload.get("n") != 1:
            raise ValueError(f"Invalid 2.5 Flash size/aspect/mode/count for {shot['id']}")
        if FORBIDDEN_PAYLOAD_FIELDS.intersection(payload):
            raise ValueError(f"2.5 Flash rejects fields: {sorted(FORBIDDEN_PAYLOAD_FIELDS.intersection(payload))}")
        if payload["prompt"] != prompt:
            raise ValueError(f"2.5 Flash prompt must carry STYLE and NEGATIVE inline for {shot['id']}")
        cursor += duration
    if cursor != 180:
        raise ValueError(f"Timeline is {cursor}s, not 180s")
    chapters = project.get("chapters", [])
    if len(chapters) != 9 or sum(int(c["duration"]) for c in chapters) != 180:
        raise ValueError("Expected nine narration units covering exactly 180 seconds")
    ch_cursor = 0
    for chapter in chapters:
        if chapter["start"] != ch_cursor or not chapter.get("text", "").strip():
            raise ValueError("Narration chapters must be complete and contiguous")
        ch_cursor += chapter["duration"]

    manifest = read_json(HERE / "audio" / "manifest.json", {})
    records = {row.get("id"): row for row in manifest.get("clips", [])}
    for chapter in chapters:
        row = records.get(chapter["id"], {})
        audio = HERE / "audio" / row.get("file", "missing.mp3")
        if row.get("text") != chapter["text"] or not audio.is_file():
            raise ValueError("Narration text/file mismatch: " + chapter["id"])
        if row.get("sha256") != digest(audio):
            raise ValueError("Narration SHA-256 mismatch: " + chapter["id"])

    for ref in project.get("reference_images", []):
        if not (HERE / ref["file"]).is_file():
            raise ValueError("Missing approved reference image: " + ref["file"])


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True,
                                  stderr=subprocess.STDOUT, timeout=120)


def create_contact_sheet(source: Path, shot_id: str, qa_dir: Path) -> dict:
    """Decode-check one clip and make a small 3x3 motion-review contact sheet."""
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
        "-vf", "fps=1,scale=426:240:force_original_aspect_ratio=decrease,pad=426:240:(ow-iw)/2:(oh-ih)/2,tile=3x3",
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
        "contact_sheet": f"production/somerton/qa/{shot_id}.jpg",
        "visual_review": "pending",
    }
    (qa_dir / f"{shot_id}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    return info


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--payload", default="{}", help='JSON, e.g. {"only":"S01","workers":1}')
    args = parser.parse_args()
    project = read_json(PLAN, {})
    validate(project)
    if args.validate:
        print("VALID: 180 seconds, 29 Agnes Video 2.5 Flash clips (720P source), final 16:9 1080P, nine TTS chapters and approved references")
        return 0

    CAPACITY_ABORT.clear()
    with CAPACITY_LOCK:
        CAPACITY_STATE.update(consecutive=0, last_error=None)
    options = json.loads(args.payload or "{}")
    requested = options.get("only", "")
    if not isinstance(requested, str):
        raise ValueError("payload.only must be a comma-separated string of shot IDs")
    only = {part.strip() for part in requested.split(",") if part.strip()}
    canary_then_full = options.get("canary_then_full") is True
    by_id = {shot["id"]: shot for shot in project["shots"]}
    if only - set(by_id):
        raise ValueError("Unknown Agnes shot(s): " + ", ".join(sorted(only - set(by_id))))
    if canary_then_full and only != {"S01"}:
        raise ValueError("canary_then_full requires only=S01")
    selected = ([by_id["S01"]] if canary_then_full else
                [shot for shot in project["shots"] if not only or shot["id"] in only])
    workers = min(2, max(1, int(options.get("workers", 2))))
    gate = RequestGate(minimum_interval=75)
    deadline = time.monotonic() + 320 * 60
    if args.publish:
        if os.getenv("GITHUB_ACTIONS") != "true" or git("branch", "--show-current").strip() != BRANCH:
            raise RuntimeError("Publishing is restricted to the fixed Arena branch in GitHub Actions")
        git("config", "user.name", "github-actions[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")

    doc = read_json(RESULTS, {"project": project["title"], "model": project["model"], "shots": {}})
    doc["model"] = MODEL
    doc["source_size"] = SOURCE_SIZE
    doc["required_generated_shots"] = [shot["id"] for shot in project["shots"]]
    doc["workflow_policy"] = "agnes-video-2.5-flash-720p-upscale-180s-29shots"
    doc["rate_policy"] = {"minimum_creation_interval_seconds": 75, "workers_max": 2,
                          "retry_after_respected": True, "key_rotation": False,
                          "queue_full_cooldown_seconds": 90, "queue_full_consecutive_limit": 24,
                          "channel_unavailable_cooldown_seconds": 300,
                          "channel_unavailable_consecutive_limit": 3}
    doc["review"] = {"status": "pending", "visual_review_required": True,
                     "note": "A decoded clip and contact sheet are not a human visual sign-off."}
    base = os.getenv("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).rstrip("/")
    key = os.getenv("AGNES_API_KEY", "").strip()
    if args.publish and not key:
        raise RuntimeError("AGNES_API_KEY is unavailable; configure the repository secret before publishing")
    sources = ROOT / "work" / "somerton" / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    qa_dir = HERE / "qa"
    exports = ROOT / "work" / "somerton" / "clips"
    exports.mkdir(parents=True, exist_ok=True)

    def checkpoint(label: str, shot_id: str | None = None, files=(), **values):
        with LOCK:
            if shot_id:
                row = doc.setdefault("shots", {}).setdefault(shot_id, {"id": shot_id})
                row.update(values)
                row["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            doc["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            doc["run_id"] = os.getenv("GITHUB_RUN_ID")
            RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if args.publish:
                paths = [str(RESULTS.relative_to(ROOT))]
                paths.extend(str(Path(path).resolve().relative_to(ROOT)) for path in files)
                git("add", "--", *paths)
                if subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=ROOT).returncode:
                    git("commit", "-m", "somerton: " + label, "--", *paths)
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
        rate_attempts = 0
        while True:
            if CAPACITY_ABORT.is_set():
                raise ProviderCapacity("Agnes provider capacity was exhausted earlier in this run")
            checkpoint(sid + " waiting for Agnes create slot", sid, status="waiting_create_slot", error=None)
            gate.acquire_creation(deadline)
            try:
                created = agnes.create_task(base, key, payload, retries=1, retry_delay=75)
            except agnes.RateLimited as exc:
                rate_attempts += 1
                if rate_attempts >= 8:
                    raise
                cooldown = max(min(300, 75 * (2 ** (rate_attempts - 1))), exc.retry_after or 0)
                checkpoint(sid + " provider rate limit", sid, status="rate_limited",
                           quota_retry=rate_attempts, provider_retry_after_seconds=exc.retry_after,
                           applied_cooldown_seconds=cooldown,
                           error=str(exc).replace(key, "[redacted]")[:500])
                gate.defer(cooldown)
                continue
            except agnes.Fatal as exc:
                message = str(exc)
                policy = capacity_failure_policy(message)
                if not policy:
                    raise
                marker, cooldown, limit = policy
                redacted = message.replace(key, "[redacted]")[:600]
                with CAPACITY_LOCK:
                    CAPACITY_STATE["consecutive"] += 1
                    CAPACITY_STATE["last_error"] = redacted
                    consecutive = CAPACITY_STATE["consecutive"]
                    exhausted = consecutive >= limit
                    if exhausted:
                        CAPACITY_ABORT.set()
                with LOCK:
                    doc["provider_outage"] = {
                        "model": MODEL,
                        "reason": marker,
                        "consecutive_capacity_failures": consecutive,
                        "cooldown_seconds": cooldown,
                        "last_error": redacted,
                    }
                checkpoint(sid + (" provider capacity exhausted" if exhausted else " provider cooldown"),
                           sid, status="provider_unavailable" if exhausted else "provider_cooldown",
                           capacity_error=marker, capacity_retry=consecutive,
                           applied_cooldown_seconds=0 if exhausted else cooldown, error=redacted)
                if exhausted:
                    raise ProviderCapacity(
                        f"Agnes {MODEL} capacity remained unavailable after {consecutive} consecutive "
                        f"create failures ({marker}); no more shots will submit requests."
                    ) from exc
                gate.defer(cooldown)
                continue
            else:
                with CAPACITY_LOCK:
                    CAPACITY_STATE["consecutive"] = 0
                    CAPACITY_STATE["last_error"] = None
                    CAPACITY_ABORT.clear()
                with LOCK:
                    doc.pop("provider_outage", None)
                return created

    def generate_one(shot: dict) -> bool:
        sid = shot["id"]
        if CAPACITY_ABORT.is_set():
            print(sid + ": skipped while Agnes provider capacity is unavailable", flush=True)
            return False
        payload = full_payload(project, shot)
        wanted_hash = request_hash(project, shot)
        with LOCK:
            old = dict(doc.setdefault("shots", {}).get(sid, {}))
        dest = sources / f"{sid}.mp4"
        try:
            if (old.get("request_hash") == wanted_hash and old.get("video_url")
                    and old.get("sha256") and old.get("bytes")):
                print(sid + ": reusing matching Agnes result", flush=True)
                return finish(shot, old, wanted_hash, reused=True)
            if old.get("request_hash") != wanted_hash:
                with LOCK:
                    if old:
                        doc.setdefault("previous_results", {}).setdefault(sid, []).append(old)
                    doc["shots"][sid] = {"id": sid}
                old = {}
            if not key:
                checkpoint(sid + " blocked", sid, status="blocked", request_hash=wanted_hash,
                           error="AGNES_API_KEY is unavailable to this workflow")
                return False

            video_id, task_id = old.get("video_id"), old.get("task_id")
            if not video_id:
                checkpoint(sid + " submitting", sid, status="submitting", request_hash=wanted_hash, error=None)
                created = paced_create(sid, payload)
                video_id = created.get("video_id") or created.get("id") or created.get("task_id")
                task_id = created.get("task_id") or created.get("id")
                if not video_id:
                    raise agnes.Fatal("Agnes returned no task identifier")
                checkpoint(sid + " queued", sid, status="queued", video_id=str(video_id),
                           task_id=str(task_id or ""), requested_seconds=float(payload["seconds"]),
                           requested_size=payload["size"])
            else:
                print(sid + ": resuming saved Agnes task", flush=True)
            remaining = deadline - time.monotonic()
            if remaining < 30:
                raise BudgetExhausted("Generation budget reached; saved task can be resumed")
            final, url = agnes.poll_task(
                base, key, MODEL, str(video_id), str(task_id) if task_id else None,
                interval=25, timeout=min(1500, remaining), max_failures=12,
                before_request=lambda: gate.wait_unblocked(deadline), rate_limit_callback=gate.defer,
            )
            size = agnes.download(url, dest, retries=3, retry_delay=5)
            receipt = {"video_url": url, "bytes": size, "sha256": digest(dest), "request_hash": wanted_hash}
            checkpoint(sid + " Agnes task completed", sid, status="downloaded", video_url=url,
                       bytes=size, sha256=receipt["sha256"], reported_size=final.get("size"),
                       reported_seconds=final.get("seconds"), error=None)
            return finish(shot, receipt, wanted_hash)
        except ProviderCapacity as exc:
            checkpoint(sid + " provider unavailable", sid, status="provider_unavailable",
                       error=str(exc).replace(key, "[redacted]")[:600])
            return False
        except Exception as exc:  # a checkpoint survives worker/API timeouts; reruns can resume.
            error = str(exc).replace(key, "[redacted]") if key else str(exc)
            checkpoint(sid + " failed", sid, status="failed", error=error[:600])
            return False

    subprocess.run([sys.executable, str(HERE / "build_story.py")], cwd=ROOT, check=True)
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["ffprobe", "-version"], check=True, stdout=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("ffmpeg and ffprobe are required on the Actions runner") from exc

    checkpoint("Agnes generation started")
    if canary_then_full:
        # The fixed-branch push event probes one shot first. Continue to all remaining footage
        # in this same process (and shared 75s request gate) only if S01 really completes.
        canary_ok = generate_one(by_id["S01"])
        if canary_ok:
            checkpoint("S01 canary passed; continuing full 29-shot production", "S01",
                       canary_status="passed")
            selected = [shot for shot in project["shots"] if shot["id"] != "S01"]
            only = set()
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                outcomes = list(pool.map(generate_one, selected))
        else:
            outcomes = [False]
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(generate_one, selected))
    if not all(outcomes):
        doc["phase"] = "provider_capacity" if CAPACITY_ABORT.is_set() else "generation_incomplete"
        checkpoint("provider capacity unavailable" if CAPACITY_ABORT.is_set() else "generation incomplete")
        reason = "Agnes模型通道/排队暂不可用" if CAPACITY_ABORT.is_set() else "Agnes镜头尚未全部完成"
        (exports / "未完成说明.txt").write_text(
            reason + "；没有用参考图或静态帧替代视频。请查看 results.json 后断点续跑。\n",
            encoding="utf-8",
        )
        return 1
    if only:
        doc["phase"] = "selected_sources_ready"
        checkpoint("selected Agnes sources ready")
        return 0

    doc["phase"] = "rendering_first_cut"
    checkpoint("all Agnes shots ready; rendering first cut")
    output = exports / project["film_name"]
    subprocess.run([
        sys.executable, str(HERE / "render.py"),
        "--sources", str(sources), "--work", str(ROOT / "work" / "somerton" / "edit"),
        "--output", str(output),
    ], cwd=ROOT, check=True)
    doc["phase"] = "first_cut_ready"
    doc["review"] = {"status": "pending", "visual_review_required": True,
                     "note": "First cut rendered; a human must inspect all 29 contact sheets and final playback."}
    doc["delivery"] = {"film": str(output.relative_to(ROOT)), "duration_seconds": 180,
                       "width": 1920, "height": 1080, "fps": 30,
                       "cover": str((output.parent / "塔玛姆·舒德_封面.jpg").relative_to(ROOT))}
    checkpoint("Somerton 180-second first cut ready")
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("## 塔玛姆·舒德：索马顿海滩无名男尸\n\n")
            stream.write("29个Agnes Video 2.5 Flash动态镜头（720P源片后期放大）；1920×1080；16:9；30fps；180秒。\n\n")
            stream.write("初版已渲染。逐镜接触表和成片仍需人工视觉/听觉复核。\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
