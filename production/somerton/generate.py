#!/usr/bin/env python3
"""Generate the 29 Somerton shots with Agnes Video V2.0, then render the 180s first cut.

All generated footage is downloaded to ignored ``work/``. Only JSON provenance and small
contact sheets are checkpointed into the fixed Arena branch. The film is never substituted
with reference stills if an Agnes shot is missing.
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

BRANCH = "arena/f29814ef-desktop-tutorial"
HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
RESULTS = HERE / "results.json"
LOCK = threading.RLock()


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


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
    return agnes.build_payload(argparse.Namespace(
        prompt=full_prompt(project, shot),
        negative_prompt=project["negative_prompt"],
        image=None,
        mode=None,
        seed=shot["seed"],
        steps=None,
        seconds=shot["seconds"],
        num_frames=None,
        frame_rate=shot["frame_rate"],
        aspect=shot["aspect"],
        resolution=shot["resolution"],
        width=None,
        height=None,
        model=project["model"],
    ))


def request_hash(project: dict, shot: dict) -> str:
    encoded = json.dumps(full_payload(project, shot), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate(project: dict) -> None:
    shots = project.get("shots", [])
    if project.get("target_duration") != 180 or len(shots) != 29:
        raise ValueError("Expected 29 shots and an exact 180-second film")
    if (project.get("width"), project.get("height"), project.get("fps")) != (1920, 1080, 30):
        raise ValueError("Output must be 1920x1080 at 30fps")
    if project.get("model") != "agnes-video-v2.0":
        raise ValueError("The required video model is Agnes Video V2.0")
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
        if shot.get("seconds") != duration or shot.get("aspect") != "16:9":
            raise ValueError(f"Invalid duration/aspect at {shot['id']}")
        for role in shot.get("characters", []):
            if role not in project["characters"]:
                raise ValueError(f"Missing character setting {role} in {shot['id']}")
        prompt = full_prompt(project, shot)
        if not prompt.startswith("【STYLE】") or not prompt.endswith(project["negative_prompt"].strip()):
            raise ValueError(f"Automatic STYLE/NEGATIVE concatenation failed for {shot['id']}")
        if shot["narration_id"] not in {c["id"] for c in project["chapters"]}:
            raise ValueError(f"Unknown narration chapter in {shot['id']}")
        payload = full_payload(project, shot)
        if payload["model"] != "agnes-video-v2.0" or (payload["num_frames"] - 1) % 8:
            raise ValueError(f"Invalid Agnes Video request for {shot['id']}")
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
        print("VALID: 180 seconds, 29 Agnes Video V2.0 clips, 16:9, nine TTS chapters and approved references")
        return 0

    options = json.loads(args.payload or "{}")
    requested = options.get("only", "")
    if not isinstance(requested, str):
        raise ValueError("payload.only must be a comma-separated string of shot IDs")
    only = {part.strip() for part in requested.split(",") if part.strip()}
    by_id = {shot["id"]: shot for shot in project["shots"]}
    if only - set(by_id):
        raise ValueError("Unknown Agnes shot(s): " + ", ".join(sorted(only - set(by_id))))
    selected = [shot for shot in project["shots"] if not only or shot["id"] in only]
    workers = min(2, max(1, int(options.get("workers", 2))))
    gate = RequestGate(minimum_interval=75)
    deadline = time.monotonic() + 320 * 60
    if args.publish:
        if os.getenv("GITHUB_ACTIONS") != "true" or git("branch", "--show-current").strip() != BRANCH:
            raise RuntimeError("Publishing is restricted to the fixed Arena branch in GitHub Actions")
        git("config", "user.name", "github-actions[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")

    doc = read_json(RESULTS, {"project": project["title"], "model": project["model"], "shots": {}})
    doc["required_generated_shots"] = [shot["id"] for shot in project["shots"]]
    doc["workflow_policy"] = "agnes-v2.0-180s-29shots-rate-aware"
    doc["rate_policy"] = {"minimum_creation_interval_seconds": 75, "workers_max": 2,
                          "retry_after_respected": True, "key_rotation": False}
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
        for attempt in range(8):
            checkpoint(sid + " waiting for Agnes create slot", sid, status="waiting_create_slot", error=None)
            gate.acquire_creation(deadline)
            try:
                return agnes.create_task(base, key, payload, retries=1, retry_delay=75)
            except agnes.RateLimited as exc:
                cooldown = max(min(300, 75 * (2 ** attempt)), exc.retry_after or 0)
                checkpoint(sid + " provider cooldown", sid, status="rate_limited",
                           quota_retry=attempt + 1, provider_retry_after_seconds=exc.retry_after,
                           applied_cooldown_seconds=cooldown,
                           error=str(exc).replace(key, "[redacted]")[:500])
                gate.defer(cooldown)
                if attempt == 7:
                    raise
        raise RuntimeError("Agnes create retry budget exhausted")

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
                           task_id=str(task_id or ""), requested_seconds=payload["num_frames"] / payload["frame_rate"])
            else:
                print(sid + ": resuming saved Agnes task", flush=True)
            remaining = deadline - time.monotonic()
            if remaining < 30:
                raise BudgetExhausted("Generation budget reached; saved task can be resumed")
            final, url = agnes.poll_task(
                base, key, agnes.DEFAULT_MODEL, str(video_id), str(task_id) if task_id else None,
                interval=25, timeout=min(1500, remaining), max_failures=12,
                before_request=lambda: gate.wait_unblocked(deadline), rate_limit_callback=gate.defer,
            )
            size = agnes.download(url, dest, retries=3, retry_delay=5)
            receipt = {"video_url": url, "bytes": size, "sha256": digest(dest), "request_hash": wanted_hash}
            checkpoint(sid + " Agnes task completed", sid, status="downloaded", video_url=url,
                       bytes=size, sha256=receipt["sha256"], reported_size=final.get("size"),
                       reported_seconds=final.get("seconds"), error=None)
            return finish(shot, receipt, wanted_hash)
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(generate_one, selected))
    if not all(outcomes):
        doc["phase"] = "generation_incomplete"
        checkpoint("generation incomplete")
        (exports / "未完成说明.txt").write_text(
            "Agnes镜头尚未全部完成；没有用参考图或静态帧替代视频。请查看 results.json 后断点续跑。\n",
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
            stream.write("29个Agnes Video V2.0动态镜头；1920×1080；16:9；30fps；180秒。\n\n")
            stream.write("初版已渲染。逐镜接触表和成片仍需人工视觉/听觉复核。\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
