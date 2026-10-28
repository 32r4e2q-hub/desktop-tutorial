#!/usr/bin/env python3
"""Generate the 29 Setagaya shots with Agnes Video 2.5 Flash, then render the 180s first cut.

The 2.5 Flash endpoint requires the documented 720P payload shape (seconds as a string,
size/aspect_ratio/mode/n); transient create failures retry every 61 seconds until accepted.
Clips are normalized and upscaled to the 1920x1080 delivery master.
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
from throttle import RequestGate  # noqa: E402

BRANCH = "arena/fed820f6-desktop-tutorial"
MODEL = "agnes-video-2.5-flash"
SOURCE_SIZE = "720P"
REQUEST_INTERVAL_SECONDS = 61
SUPPORTED_MODES = {"text", "keyframe", "reference"}
ALLOWED_PAYLOAD_FIELDS = {
    "model", "prompt", "seconds", "size", "aspect_ratio", "mode", "n", "seed",
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
LOCK = threading.RLock()


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def retryable_create_error(message: str):
    """Return the matched transient provider marker, or None for a fatal request error."""
    text = str(message or "").lower()
    if "http 408" in text or "http 425" in text:
        return "provider request timeout"
    for marker in RETRYABLE_CREATE_MARKERS:
        if marker in text:
            return marker
    if "http 5" in text:
        return "provider 5xx"
    return None


def retry_create_until_accepted(create_call, gate, interval: int, on_retry):
    """Retry transient create failures indefinitely, respecting Retry-After and the shared gate."""
    attempts = 0
    while True:
        attempts += 1
        try:
            return create_call()
        except agnes.RateLimited as exc:
            cooldown = max(interval, exc.retry_after or 0)
            on_retry(attempts, "HTTP 429", str(exc), cooldown)
            gate.defer(cooldown)
        except agnes.Fatal as exc:
            marker = retryable_create_error(str(exc))
            if not marker:
                raise
            cooldown = max(interval, getattr(exc, "retry_after", None) or 0)
            on_retry(attempts, marker, str(exc), cooldown)
            gate.defer(cooldown)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def style_for(project: dict, shot: dict) -> str:
    """Rumor scenes use the aged hand-drawn STYLE block; everything else uses the 3D block."""
    variant = shot.get("style_variant", "real")
    if variant == "diagram":
        return project["style_rumor_prefix"].strip()
    if variant != "real":
        raise ValueError(f"{shot.get('id')}: unknown style variant {variant!r}")
    return project["style_prefix"].strip()


def full_prompt(project: dict, shot: dict) -> str:
    """Apply the requested prefix/character/negative rules to every generated shot."""
    parts = [style_for(project, shot)]
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
        "seed": payload_seed(project, shot),
    }


def payload_seed(project: dict, shot: dict) -> int:
    """Single-character shots reuse that character's seed so the face stays consistent."""
    roles = [role for role in shot.get("characters", []) if role]
    seeds = project.get("character_seeds", {})
    if len(roles) == 1 and roles[0] in seeds:
        return int(seeds[roles[0]])
    return int(shot["seed"])


def request_hash(project: dict, shot: dict) -> str:
    encoded = json.dumps(full_payload(project, shot), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


DELIVERY_DIR = ROOT / "交付"
DELIVERY_FILM = "世田谷一家四口杀人案_留下无数线索的悬案_三分钟_带声音.mp4"


def publish_delivery(film: Path) -> dict:
    """Copy the finished film, cover and subtitle file into 交付/ (the repo's delivery convention)."""
    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)
    copied = {}
    targets = [(film, DELIVERY_FILM)]
    cover = film.parent / "世田谷一家四口杀人案_封面.jpg"
    if cover.is_file():
        targets.append((cover, "世田谷一家四口杀人案_封面.jpg"))
    for source, name in targets:
        if not source.is_file():
            continue
        destination = DELIVERY_DIR / name
        shutil.copy2(source, destination)
        copied[name] = {"bytes": destination.stat().st_size, "sha256": digest(destination)}
    srt = film.parent / f"{film.stem}_字幕.srt"
    if srt.is_file():
        destination = DELIVERY_DIR / "世田谷一家四口杀人案_字幕.srt"
        shutil.copy2(srt, destination)
        copied[destination.name] = {"bytes": destination.stat().st_size, "sha256": digest(destination)}
    report = film.parent / "delivery" / "technical-report.json"
    if not report.is_file():
        report = ROOT / "work" / "setagaya2000" / "edit" / "delivery" / "technical-report.json"
    if report.is_file():
        destination = DELIVERY_DIR / "世田谷一家四口杀人案_技术报告.json"
        shutil.copy2(report, destination)
        copied[destination.name] = {"bytes": destination.stat().st_size, "sha256": digest(destination)}
    # The brief asks for four named deliverables; keep them byte-identical next to the
    # repository's own naming convention so the hand-off needs no renaming.
    aliases = [
        (film, "Setagaya_Case_Final.mp4"),
        (film.parent / "世田谷一家四口杀人案_封面.png", "Setagaya_Cover.png"),
        (film.parent / f"{film.stem}_字幕.srt", "Setagaya_Subtitles.srt"),
        (ROOT / "work" / "setagaya2000" / "audio" / "voiceover.wav", "Setagaya_Narration.wav"),
    ]
    for source, name in aliases:
        if not source.is_file():
            continue
        destination = DELIVERY_DIR / name
        shutil.copy2(source, destination)
        copied[name] = {"bytes": destination.stat().st_size, "sha256": digest(destination)}
    return copied


def commit_delivery(message: str) -> None:
    """Commit results.json plus the 交付/ files, then push to the fixed branch."""
    paths = [str(RESULTS.relative_to(ROOT))]
    if DELIVERY_DIR.exists():
        paths.append(str(DELIVERY_DIR.relative_to(ROOT)))
    git("add", "-f", "--", *paths)
    if not subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=ROOT).returncode:
        return
    git("commit", "-m", message, "--", *paths)
    for attempt in range(3):
        try:
            git("push", "origin", BRANCH)
            return
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            git("pull", "--rebase", "origin", BRANCH)


def restore_sources(project: dict, results: dict, sources: Path) -> list[str]:
    """Rebuild ignored work/ footage from the recorded Agnes receipts of a finished run.

    A render-only run starts on a fresh checkout, where ``work/`` is empty but ``results.json``
    still carries the original video URL, byte size and SHA-256 of every clip. Each clip is
    re-downloaded and byte-verified, so the render gate still proves the exact model output.
    """
    restored = []
    sources.mkdir(parents=True, exist_ok=True)
    for shot in project["shots"]:
        sid = shot["id"]
        receipt = results.get("shots", {}).get(sid, {})
        dest = sources / f"{sid}.mp4"
        if not receipt.get("video_url") or not receipt.get("sha256"):
            raise RuntimeError(f"{sid}: no Agnes receipt to restore from")
        if dest.is_file() and digest(dest) == receipt["sha256"] \
                and dest.stat().st_size == receipt.get("bytes"):
            continue
        print(f"RESTORE {sid} from Agnes receipt", flush=True)
        agnes.download(receipt["video_url"], dest, retries=3, retry_delay=5)
        if digest(dest) != receipt["sha256"] or dest.stat().st_size != receipt.get("bytes"):
            raise RuntimeError(f"{sid}: restored footage does not match the original receipt")
        restored.append(sid)
    return restored


def prepare_prompt_changes(project: dict, results: dict, shots: list[dict]) -> list[str]:
    """Checkpoint changed requests before workers start, so stale rows cannot look reused."""
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
    if project.get("target_duration") != 180 or len(shots) != 29:
        raise ValueError("Expected 29 shots and an exact 180-second film")
    if (project.get("width"), project.get("height"), project.get("fps")) != (1920, 1080, 24):
        raise ValueError("Output must be 1920x1080 at 24fps")
    if project.get("model") != MODEL or project.get("source_size") != SOURCE_SIZE:
        raise ValueError("The required source model/size is Agnes Video 2.5 Flash at 720P")
    if not project.get("style_prefix", "").startswith("【STYLE】"):
        raise ValueError("STYLE must be the first text in every prompt")
    if not project.get("style_rumor_prefix", "").startswith("【STYLE"):
        raise ValueError("Rumor STYLE block is missing")
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
        if not prompt.startswith(style_for(project, shot)):
            raise ValueError(f"Wrong STYLE variant inlined for {shot['id']}")
        if payload["seed"] != payload_seed(project, shot):
            raise ValueError(f"Character seed was not applied for {shot['id']}")
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

    if not require_audio:
        for ref in project.get("reference_images", []):
            if not (HERE / ref["file"]).is_file():
                raise ValueError("Missing approved reference image: " + ref["file"])
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
        "contact_sheet": f"production/setagaya2000/qa/{shot_id}.jpg",
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
    parser.add_argument("--clips-only", action="store_true",
                        help="generate all 29 clips but do not render (voice may not exist yet)")
    parser.add_argument("--render-only", action="store_true",
                        help="skip generation entirely and render from verified clips")
    args = parser.parse_args()
    project = read_json(PLAN, {})
    options = json.loads(args.payload or "{}")
    mode = str(options.get("mode") or "").strip()
    if not mode and options.get("only"):
        # 单镜/金丝雀试跑绝不进入出片阶段：配音还没齐也一样能先攒素材。
        mode = "clips"
    if mode == "clips":
        args.clips_only = True
    elif mode == "render":
        args.render_only = True
    elif mode not in {"", "full", "qc"}:
        raise ValueError("payload.mode must be clips, render, full or qc")
    if mode == "qc":
        # QC-only run: verify the plan and the delivered film, refresh qa/ (contact sheets,
        # full-resolution stills, qc-report.json, qc-summary.md), never regenerate footage.
        validate(project, require_audio=True)
        film = DELIVERY_DIR / "Setagaya_Case_Final.mp4"
        if not film.is_file():
            raise RuntimeError("QC requested but 交付/Setagaya_Case_Final.mp4 does not exist")
        if os.getenv("GITHUB_ACTIONS") == "true":
            git("config", "user.name", "github-actions[bot]")
            git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
        code = subprocess.run([sys.executable, str(HERE / "qc.py")], cwd=ROOT).returncode
        if args.publish:
            git("add", "-f", "--", "production/setagaya2000/qa", "交付")
            if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
                git("commit", "-m", "setagaya2000: 成片质检（原始像素抽帧 + QC 报告）")
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
        print("VALID: 180 seconds, 29 Agnes Video 2.5 Flash clips (720P source), 1080P delivery, 29 shot-locked voice lines, nine chapters and approved references")
        return 0

    if args.render_only:
        doc = read_json(RESULTS, {"project": project["title"], "model": project["model"], "shots": {}})
        sources = ROOT / "work" / "setagaya2000" / "sources"
        sources.mkdir(parents=True, exist_ok=True)
        exports = ROOT / "work" / "setagaya2000" / "clips"
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
            "--sources", str(sources), "--work", str(ROOT / "work" / "setagaya2000" / "edit"),
            "--output", str(output),
        ], cwd=ROOT, check=True)
        doc["phase"] = "first_cut_ready"
        delivered = publish_delivery(output)
        doc["delivery"] = {"film": str(output.relative_to(ROOT)), "duration_seconds": 180,
                           "width": 1920, "height": 1080, "fps": 24,
                           "cover": str((output.parent / "世田谷一家四口杀人案_封面.jpg").relative_to(ROOT)),
                           "delivered": delivered}
        RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.publish:
            commit_delivery("setagaya2000: 180秒成片、封面、字幕与交付报告")
        print("FIRST_CUT_READY " + output.name, flush=True)
        return 0

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
    gate = RequestGate(minimum_interval=REQUEST_INTERVAL_SECONDS)
    # The retry loop is intentionally unbounded; the Actions job timeout is the outer safety cap.
    # Every create attempt is still checkpointed, and a restarted run resumes completed/task IDs.
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
    doc["workflow_policy"] = "agnes-video-2.5-flash-720p-upscale-180s-29shots"
    doc["rate_policy"] = {"minimum_creation_interval_seconds": REQUEST_INTERVAL_SECONDS,
                          "workers_max": 2, "retry_after_respected": True,
                          "key_rotation": False, "capacity_retry_interval_seconds": REQUEST_INTERVAL_SECONDS,
                          "capacity_retries_unbounded": True}
    doc["review"] = {"status": "pending", "visual_review_required": True,
                     "note": "A decoded clip and contact sheet are not a human visual sign-off."}
    base = os.getenv("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).rstrip("/")
    key = os.getenv("AGNES_API_KEY", "").strip()
    if args.publish and not key:
        raise RuntimeError("AGNES_API_KEY is unavailable; configure the repository secret before publishing")
    sources = ROOT / "work" / "setagaya2000" / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    qa_dir = HERE / "qa"
    exports = ROOT / "work" / "setagaya2000" / "clips"
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
                    git("commit", "-m", "setagaya2000: " + label, "--", *paths)
                    for attempt in range(3):
                        try:
                            git("push", "origin", BRANCH)
                            break
                        except subprocess.CalledProcessError:
                            if attempt == 2:
                                raise
                            git("pull", "--rebase", "origin", BRANCH)
            print("PRODUCTION_STATUS " + label, flush=True)

    def prepare_selected(shots: list[dict]) -> None:
        changes = prepare_prompt_changes(project, doc, shots)
        if changes:
            checkpoint("queued prompt-refresh shots: " + ",".join(changes))

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
        """Keep submitting a shot until Agnes accepts it; transient failures never exhaust a cap."""
        attempts = 0

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
                    "model": MODEL,
                    "reason": marker,
                    "last_error": redacted,
                    "create_attempts": attempt,
                    "retry_interval_seconds": cooldown,
                    "last_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            checkpoint(sid + " provider busy; retrying", sid,
                       publish=(attempt == 1 or attempt % 10 == 0),
                       status="rate_limited" if marker == "HTTP 429" else "provider_cooldown",
                       capacity_error=marker, create_attempts=attempt,
                       applied_cooldown_seconds=cooldown, error=redacted)
            print(f"{sid}: {marker}; retrying create in {cooldown:g}s (attempt {attempt})", flush=True)

        created = retry_create_until_accepted(create, gate, REQUEST_INTERVAL_SECONDS, record_retry)
        with LOCK:
            doc.pop("provider_outage", None)
        return created

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
                print(sid + ": reusing matching Agnes result", flush=True)
                try:
                    return finish(shot, old, wanted_hash, reused=True)
                except (agnes.Fatal, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
                    reset_shot_for_retry(sid, wanted_hash, dest, str(exc))
                    old = {"id": sid, "request_hash": wanted_hash, "status": "retrying_create"}
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
                        interval=25, timeout=min(1500, remaining), max_failures=12,
                        before_request=lambda: gate.wait_unblocked(deadline), rate_limit_callback=gate.defer,
                    )
                    size = agnes.download(url, dest, retries=3, retry_delay=5)
                    receipt = {"video_url": url, "bytes": size, "sha256": digest(dest),
                               "request_hash": wanted_hash}
                    checkpoint(sid + " Agnes task completed", sid, status="downloaded", video_url=url,
                               bytes=size, sha256=receipt["sha256"], reported_size=final.get("size"),
                               reported_seconds=final.get("seconds"), error=None)
                    try:
                        return finish(shot, receipt, wanted_hash)
                    except (agnes.Fatal, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
                        reset_shot_for_retry(sid, wanted_hash, dest, str(exc))
                        video_id = task_id = None
                        continue
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
        except Exception as exc:  # a checkpoint survives fatal/API timeouts; reruns can resume.
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
        # in this same process (and shared 61s request gate) only if S01 really completes.
        canary_ok = generate_one(by_id["S01"])
        if canary_ok:
            checkpoint("S01 canary passed; continuing full 29-shot production", "S01",
                       canary_status="passed")
            selected = [shot for shot in project["shots"] if shot["id"] != "S01"]
            only = set()
            prepare_selected(selected)
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                outcomes = list(pool.map(generate_one, selected))
        else:
            outcomes = [False]
    else:
        prepare_selected(selected)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            outcomes = list(pool.map(generate_one, selected))
    if not all(outcomes):
        doc["phase"] = "generation_incomplete"
        checkpoint("generation incomplete")
        (exports / "未完成说明.txt").write_text(
            "Agnes镜头尚未全部完成；没有用参考图或静态帧替代视频。请查看 results.json 后修复致命错误再断点续跑。\n",
            encoding="utf-8",
        )
        return 1
    if only:
        doc["phase"] = "selected_sources_ready"
        checkpoint("selected Agnes sources ready")
        return 0
    if args.clips_only:
        doc["phase"] = "sources_ready_pending_render"
        checkpoint("all 29 Agnes clips ready; waiting for voice clips before rendering")
        (exports / "剪好前说明.txt").write_text(
            "29 条 Agnes 视频已全部完成并通过解码检查；旁白一到就渲染成片。\n", encoding="utf-8")
        return 0

    doc["phase"] = "rendering_first_cut"
    checkpoint("all Agnes shots ready; rendering first cut")
    output = exports / project["film_name"]
    subprocess.run([
        sys.executable, str(HERE / "render.py"),
        "--sources", str(sources), "--work", str(ROOT / "work" / "setagaya2000" / "edit"),
        "--output", str(output),
    ], cwd=ROOT, check=True)
    doc["phase"] = "first_cut_ready"
    doc["review"] = {"status": "pending", "visual_review_required": True,
                     "note": "First cut rendered; a human must inspect all 29 contact sheets and final playback."}
    doc["delivery"] = {"film": str(output.relative_to(ROOT)), "duration_seconds": 180,
                       "width": 1920, "height": 1080, "fps": 24,
                       "cover": str((output.parent / "世田谷一家四口杀人案_封面.jpg").relative_to(ROOT)),
                       "delivered": publish_delivery(output)}
    checkpoint("setagaya2000 180-second first cut ready", publish=False)
    if args.publish:
        commit_delivery("setagaya2000: 180秒成片、封面、字幕与交付报告")
    summary = os.getenv("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write("## 世田谷一家四口杀人案：留下无数线索，凶手为何仍未找到？\n\n")
            stream.write("29个Agnes Video 2.5 Flash动态镜头（720P源片后期放大）；1920×1080；16:9；24fps；180秒。\n\n")
            stream.write("初版已渲染。逐镜接触表和成片仍需人工视觉/听觉复核。\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
