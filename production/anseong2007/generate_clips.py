#!/usr/bin/env python3
"""安城双尸案 · Agnes Video 2.5 Flash reference 模式 · 一次性排队 30 镜。

调用方法沿用 main 的 production/agnes_video.py（create_task / http_json / download），
payload 形状沿用 hakamada58 / iguchi1990 已验证的 2.5 Flash reference schema：
  {model, prompt, seconds, size, aspect_ratio, mode="reference", n, seed, images=[1–5 个公网 raw URL]}
轮询只走 GET /agnesapi?video_id=…&model_name=…（reference 模式不能回落 /v1/videos/<task_id>）。

调度（用户月卡：每分钟最多 5 次创建）：
  1. 创建线程：串行创建所有待生成镜头，两次创建间隔 ≥12.1 s，遵守 Retry-After / 队列满 / 额度耗尽；
     每创建一个立刻把 task id 写进 results.json 并推回分支（断点续跑不重复计费）。
  2. 轮询线程：一个线程轮流查询所有排队任务，全局每 POLL_SPACING 秒最多一次查询，429 时整体退避。
  3. 下载线程池：完成的任务下载 → SHA-256 → 解码 → 九帧接触表 + 静帧筛查。
不轮换密钥、不绕过限额；本地（非 Actions）禁止真实调用。
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "production"))
import agnes_video as agnes  # noqa: E402
import importlib.util  # noqa: E402

# 本项目的 throttle.py 用独立模块名加载：production/dahlia 等项目也有同名 throttle.py，
# 全量 pytest 时谁先进 sys.modules 谁就赢，会互相串台。
_spec = importlib.util.spec_from_file_location("anseong2007_throttle", HERE / "throttle.py")
_throttle = importlib.util.module_from_spec(_spec)
sys.modules["anseong2007_throttle"] = _throttle
_spec.loader.exec_module(_throttle)
BudgetExhausted, RequestGate = _throttle.BudgetExhausted, _throttle.RequestGate

SLUG = "anseong2007"
BRANCH = "arena/7f19693e-desktop-tutorial"
REPOSITORY = "32r4e2q-hub/desktop-tutorial"
MODEL = "agnes-video-2.5-flash"
SIZE = "720P"
CREATES_PER_MINUTE = 5
CREATE_INTERVAL = 60.0 / CREATES_PER_MINUTE + 0.1  # 12.1 s
POLL_SPACING = 4.0           # 全局查询间隔：≤15 次/分钟，避免 "too many video status queries"
POLL_429_BACKOFF = 60.0
PER_TASK_MIN_REPOLL = 45.0   # 同一任务两次查询至少相隔 45 s
RATE_LIMIT_MIN_WAIT = 30.0   # 429 至少冷却 30 s（若 Retry-After 更长则以服务端为准）
QUEUE_FULL_WAIT = 60.0       # 队列满/5xx：60 s 后再试，期间等任一任务完成
CAPACITY_WAIT = 120.0
CREATE_STOP_MARGIN = 600.0   # 预算最后 10 分钟不再新建任务
AUTO_RETRY_FAILED = 1        # Agnes 端任务失败（如 upload_timeout）自动重建次数
ALLOWED = {"model", "prompt", "seconds", "size", "aspect_ratio", "mode", "n", "seed", "images"}
FORBIDDEN = {"width", "height", "fps", "num_frames", "frame_rate", "duration", "resolution",
             "negative_prompt", "quality", "num_inference_steps"}
QUEUE_FULL = ("queue is full", "queue_full", "no available channel", "get_channel_failed",
              "capacity is full", "too many pending", "concurrent")
QUOTA = ("quota exceeded", "insufficient quota", "out of credits", "no credits", "insufficient balance",
         "billing limit", "usage limit reached", "daily limit reached", "monthly limit reached")
PLAN = HERE / "story.json"
RESULTS = HERE / "results.json"
REF = HERE / "reference"
QA = HERE / "qa"
WORK = ROOT / "work" / SLUG / "clips"
LOCK = threading.RLock()
PUSH_LOCK = threading.Lock()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(msg: str) -> None:
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def revision() -> str:
    path = REF / "revision.txt"
    return path.read_text(encoding="utf-8").strip() if path.is_file() else ""


def image_urls(shot: dict, rev: str) -> list[str]:
    return [f"https://raw.githubusercontent.com/{REPOSITORY}/{rev}/production/{SLUG}/reference/{rid}.png"
            for rid in shot["reference_images"]]


def payload(shot: dict, rev: str) -> dict:
    return {"model": MODEL, "prompt": shot["prompt"], "seconds": str(int(shot["duration"])), "size": SIZE,
            "aspect_ratio": "16:9", "mode": "reference", "n": 1, "seed": int(shot["seed"]),
            "images": image_urls(shot, rev)}


def request_hash(p: dict) -> str:
    return hashlib.sha256(json.dumps(p, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


# ───────────────────────────── validation ─────────────────────────────

def validate(project: dict, require_refs: bool) -> list[str]:
    shots = project["shots"]
    if len(shots) != 30:
        raise ValueError("expected exactly 30 shots")
    if project.get("model") != MODEL or project.get("source_size") != SIZE:
        raise ValueError("model must be agnes-video-2.5-flash at 720P")
    cursor = 0
    for s in shots:
        if s["start"] != cursor or not 4 <= int(s["duration"]) <= 9:
            raise ValueError(f"{s['id']}: bad timeline / Agnes seconds must be 4–9")
        cursor += int(s["duration"])
        if not s["prompt"].startswith("【STYLE】") or not s["prompt"].endswith(project["negative"]):
            raise ValueError(f"{s['id']}: STYLE must lead and NEGATIVE must end the prompt")
        for c in s["character_anchors"]:
            if project["anchors"][c] not in s["prompt"]:
                raise ValueError(f"{s['id']}: anchor {c} not copied verbatim")
        if not 1 <= len(s["reference_images"]) <= 5:
            raise ValueError(f"{s['id']}: reference mode needs 1–5 images")
        for n in range(1, len(s["reference_images"]) + 1):
            if f"<Picture {n}>" not in s["prompt"]:
                raise ValueError(f"{s['id']}: prompt does not describe <Picture {n}>")
        p = payload(s, "0" * 40)
        if set(p) != ALLOWED or FORBIDDEN & set(p):
            raise ValueError(f"{s['id']}: payload fields {sorted(p)}")
        if not s["narration"].strip():
            raise ValueError(f"{s['id']}: empty narration")
    if cursor != 180:
        raise ValueError(f"timeline is {cursor}s, expected 180")
    problems = []
    refs = {r["id"]: r for r in project["reference_images"]}
    used = {rid for s in shots for rid in s["reference_images"]}
    for rid in sorted(used):
        row = refs.get(rid)
        path = HERE / f"reference/{rid}.png"
        if not row or row.get("status") != "approved":
            problems.append(f"{rid}: not approved")
        elif not path.is_file() or path.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            problems.append(f"{rid}: missing PNG")
        elif sha(path) != row.get("sha256"):
            problems.append(f"{rid}: image changed since approval")
    if require_refs:
        if problems:
            raise RuntimeError("reference gate failed: " + "; ".join(problems))
        rev = revision()
        if len(rev) != 40:
            raise RuntimeError("reference/revision.txt must pin the immutable commit that contains the PNGs")
    return problems


# ───────────────────────────── receipts ─────────────────────────────

def read_results() -> dict:
    if RESULTS.is_file():
        try:
            return json.loads(RESULTS.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {"project": SLUG, "model": MODEL, "mode": "reference", "shots": {}}


class Receipts:
    def __init__(self, doc: dict, publish: bool):
        self.doc, self.publish, self.last_push = doc, publish, 0.0

    def row(self, sid: str) -> dict:
        with LOCK:
            return self.doc.setdefault("shots", {}).setdefault(sid, {"id": sid})

    def update(self, sid: str, push: bool = False, **values) -> None:
        with LOCK:
            row = self.row(sid)
            row.update(values)
            row["updated_at"] = now()
            self.doc["updated_at"] = now()
            self.save()
        if push:
            self.push()

    def save(self) -> None:
        with LOCK:
            counts: dict[str, int] = {}
            for r in self.doc.get("shots", {}).values():
                counts[r.get("status", "?")] = counts.get(r.get("status", "?"), 0) + 1
            self.doc["status_counts"] = counts
            RESULTS.write_text(json.dumps(self.doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def push(self, force: bool = False, message: str = "") -> None:
        """Commit results.json + qa/ back to the fixed branch ([skip ci] keeps CI quiet)."""
        if not self.publish:
            return
        with PUSH_LOCK:
            if not force and time.monotonic() - self.last_push < 60:
                return
            self.last_push = time.monotonic()
            with LOCK:
                self.save()
            msg = message or f"{SLUG}: Agnes receipts checkpoint {self.doc.get('status_counts')} [skip ci]"
            run = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
            paths = [str(p.relative_to(ROOT)) for p in (RESULTS, QA) if p.exists()]
            for attempt in range(6):
                # Shallow-clone safe: move the index to the remote tip, add ONLY our receipts, commit, push.
                run("fetch", "--depth=1", "origin", f"+refs/heads/{BRANCH}:refs/remotes/origin/{BRANCH}")
                run("reset", "--mixed", "-q", f"origin/{BRANCH}")
                run("add", "-f", "--", *paths)
                if run("diff", "--cached", "--quiet").returncode == 0:
                    return
                run("commit", "-q", "-m", msg)
                if run("push", "origin", f"HEAD:{BRANCH}").returncode == 0:
                    return
                time.sleep(3 + attempt * 2)
            log("checkpoint push failed (will retry at next checkpoint)")


# ───────────────────────────── clip inspection ─────────────────────────────

def inspect_clip(path: Path, sid: str) -> dict:
    import av
    from PIL import Image, ImageChops, ImageOps, ImageStat

    with av.open(str(path)) as container:
        stream = next(s for s in container.streams if s.type == "video")
        duration = float(container.duration / av.time_base) if container.duration else float(stream.duration * stream.time_base)
        width, height = int(stream.width), int(stream.height)
        targets = [duration * (i + 0.5) / 9 for i in range(9)]
        thumbs, small, ix, last = [], [], 0, None
        for frame in container.decode(stream):
            last = frame
            t = float(frame.pts * stream.time_base) if frame.pts is not None else 0.0
            while ix < 9 and t >= targets[ix]:
                im = frame.to_image().convert("RGB")
                thumbs.append(ImageOps.pad(im, (426, 240), color=(12, 12, 12)))
                small.append(im.resize((64, 36)).convert("L"))
                ix += 1
            if ix == 9:
                break
        if last is None:
            raise RuntimeError(f"{sid}: no decodable frames")
        while len(thumbs) < 9:
            im = last.to_image().convert("RGB")
            thumbs.append(ImageOps.pad(im, (426, 240), color=(12, 12, 12)))
            small.append(im.resize((64, 36)).convert("L"))
    if not 3.5 <= duration <= 10.5 or width < 640:
        raise RuntimeError(f"{sid}: unsuitable returned video {duration:.2f}s {width}x{height}")
    diffs = [ImageStat.Stat(ImageChops.difference(a, b)).mean[0] / 255 for a, b in zip(small, small[1:])]
    sheet = Image.new("RGB", (1278, 720), (12, 12, 12))
    for i, im in enumerate(thumbs[:9]):
        sheet.paste(im, ((i % 3) * 426, (i // 3) * 240))
    QA.mkdir(parents=True, exist_ok=True)
    sheet.save(QA / f"{sid}.jpg", quality=86)
    info = {"duration_seconds": round(duration, 3), "width": width, "height": height,
            "fps": str(stream.average_rate) if stream.average_rate else None, "bytes": path.stat().st_size,
            "decoded_ok": True, "motion_mean_difference": round(sum(diffs) / len(diffs), 4),
            "suspected_static": max(diffs) < 0.01, "contact_sheet": f"production/{SLUG}/qa/{sid}.jpg",
            "visual_review": "pending"}
    (QA / f"{sid}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return info


# ───────────────────────────── the scheduler ─────────────────────────────

class Producer:
    def __init__(self, project: dict, shots: list[dict], key: str, base: str, deadline: float,
                 receipts: Receipts, rev: str, force: set[str]):
        self.project, self.shots, self.key, self.base = project, shots, key, base.rstrip("/")
        self.deadline, self.r, self.rev, self.force = deadline, receipts, rev, force
        self.gate = RequestGate(CREATE_INTERVAL, allow_fast_plan=True)
        self.poll_block_until = 0.0
        self.outstanding: dict[str, dict] = {}   # sid -> shot, task accepted & not finished
        self.pending_downloads: set[str] = set()
        self.creator_done = threading.Event()
        self.capacity_freed = threading.Event()
        self.stop_reason = ""
        self.downloads = concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="dl")
        self.futures: list[concurrent.futures.Future] = []

    def redact(self, text: str) -> str:
        return str(text).replace(self.key, "[REDACTED]")[:700] if self.key else str(text)[:700]

    # —— classification of the saved state ——
    def plan(self) -> list[dict]:
        to_create = []
        for shot in self.shots:
            sid = shot["id"]
            p = payload(shot, self.rev)
            ph = request_hash(p)
            row = dict(self.r.row(sid))
            dest = WORK / f"{sid}.mp4"
            if row and (row.get("request_hash") != ph or sid in self.force):
                if row.get("status") in {"queued", "in_progress", "polling"} and row.get("request_hash") == ph:
                    pass
                else:
                    with LOCK:
                        self.r.doc.setdefault("previous_results", {}).setdefault(sid, []).append(row)
                        self.r.doc["shots"][sid] = {"id": sid}
                    row = {}
            if row.get("status") == "completed" and row.get("video_url"):
                if not (dest.is_file() and sha(dest) == row.get("sha256")):
                    self.queue_download(shot, row["video_url"], restore=True)
                continue
            if row.get("video_id") and row.get("status") not in {"failed", "create_failed", "quota_blocked"}:
                self.outstanding[sid] = shot
                continue
            to_create.append(shot)
        return to_create

    # —— creator ——
    def create_all(self, to_create: list[dict]) -> None:
        try:
            queue = list(to_create)
            while queue:
                shot = queue[0]
                sid = shot["id"]
                p = payload(shot, self.rev)
                ph = request_hash(p)
                if time.monotonic() > self.deadline - CREATE_STOP_MARGIN:
                    self.stop_reason = "time budget nearly used; remaining shots will be created on resume"
                    return
                self.gate.acquire_creation(self.deadline)
                attempts = int(self.r.row(sid).get("create_attempts", 0)) + 1
                try:
                    created = agnes.create_task(self.base, self.key, p, retries=1, retry_delay=1)
                except agnes.RateLimited as exc:
                    msg = self.redact(exc)
                    low = msg.lower()
                    if any(m in low for m in QUOTA):
                        self.r.update(sid, push=True, status="quota_blocked", error=msg, request_hash=ph)
                        self.stop_reason = "Agnes reports quota exhausted"
                        return
                    wait = max(CREATE_INTERVAL, float(exc.retry_after or 0), RATE_LIMIT_MIN_WAIT)
                    if any(m in low for m in QUEUE_FULL):
                        wait = max(wait, QUEUE_FULL_WAIT)
                    self.gate.defer(wait)
                    self.r.update(sid, status="rate_limited", error=msg, request_hash=ph,
                                  create_attempts=attempts, cooldown_seconds=wait)
                    log(f"{sid}: HTTP 429 — honoring {wait:g}s cooldown")
                    continue
                except agnes.Fatal as exc:
                    msg = self.redact(exc)
                    low = msg.lower()
                    if any(m in low for m in QUOTA):
                        self.r.update(sid, push=True, status="quota_blocked", error=msg, request_hash=ph)
                        self.stop_reason = "Agnes reports quota exhausted"
                        return
                    if any(m in low for m in QUEUE_FULL) or "http 5" in low or "network error" in low:
                        self.gate.defer(QUEUE_FULL_WAIT)
                        self.r.update(sid, status="waiting_provider_capacity", error=msg,
                                      request_hash=ph, create_attempts=attempts)
                        log(f"{sid}: provider busy/full — waiting for capacity ({msg[:120]})")
                        self.capacity_freed.wait(timeout=CAPACITY_WAIT)
                        self.capacity_freed.clear()
                        if attempts >= 40:
                            queue.pop(0)
                        continue
                    self.r.update(sid, push=True, status="create_failed", error=msg, request_hash=ph,
                                  create_attempts=attempts, request_payload=p)
                    log(f"{sid}: create rejected: {msg[:200]}")
                    queue.pop(0)
                    continue
                video_id = created.get("video_id") or created.get("id") or created.get("task_id")
                task_id = created.get("task_id") or created.get("id") or video_id
                if not video_id:
                    self.r.update(sid, push=True, status="create_failed", error="no task id in response")
                    queue.pop(0)
                    continue
                self.r.update(sid, push=True, status="queued", video_id=str(video_id), task_id=str(task_id),
                              request_hash=ph, request_payload=p, requested_seconds=int(shot["duration"]),
                              create_attempts=attempts, created_at=now(), error=None, next_poll_epoch=time.time() + 90)
                with LOCK:
                    self.outstanding[sid] = shot
                log(f"{sid}: accepted by Agnes ({str(video_id)[:14]}…); {len(queue) - 1} left to queue")
                queue.pop(0)
        except BudgetExhausted as exc:
            self.stop_reason = str(exc)
        finally:
            self.creator_done.set()

    # —— poller ——
    def status_once(self, sid: str) -> None:
        row = self.r.row(sid)
        url = f"{self.base}/agnesapi?" + urllib.parse.urlencode({"video_id": row["video_id"], "model_name": MODEL})
        try:
            resp = agnes.http_json("GET", url, self.key, timeout=60)
        except agnes.TransientError as exc:
            self.r.update(sid, poll_error=self.redact(exc), next_poll_epoch=time.time() + PER_TASK_MIN_REPOLL)
            return
        code, body, text = resp
        if code == 429:
            wait = max(POLL_429_BACKOFF, float(getattr(resp, "retry_after", None) or 0))
            self.poll_block_until = time.monotonic() + wait
            self.r.update(sid, next_poll_epoch=time.time() + wait)
            log(f"poll 429 — all polling pauses {wait:g}s")
            return
        if code in (401, 403):
            raise agnes.Fatal(f"authentication failed while polling (HTTP {code})")
        if not (200 <= code < 300 and isinstance(body, dict)):
            fails = int(row.get("poll_failures", 0)) + 1
            self.r.update(sid, poll_failures=fails, poll_error=agnes.describe_error(body, text, code),
                          next_poll_epoch=time.time() + PER_TASK_MIN_REPOLL * min(4, fails))
            return
        state = str(body.get("status") or "").lower()
        progress = body.get("progress")
        video_url = agnes.find_video_url(body)
        if state in agnes.COMPLETED_STATES or (not state and video_url):
            if not video_url:
                self.r.update(sid, status="in_progress", progress=progress, next_poll_epoch=time.time() + 20)
                return
            with LOCK:
                self.outstanding.pop(sid, None)
            self.capacity_freed.set()
            self.r.update(sid, status="downloading", video_url=video_url, final_response=body, progress=100)
            self.queue_download(next(s for s in self.shots if s["id"] == sid), video_url)
            log(f"{sid}: Agnes completed")
        elif state in agnes.FAILED_STATES:
            with LOCK:
                self.outstanding.pop(sid, None)
            self.capacity_freed.set()
            err = agnes.describe_error(body, text, code)
            retries = int(row.get("auto_retries", 0))
            log(f"{sid}: Agnes task {state}: {err}")
            if retries < AUTO_RETRY_FAILED:
                self.r.update(sid, push=True, status="retry_pending", error=err, auto_retries=retries + 1,
                              failed_video_ids=row.get("failed_video_ids", []) + [row.get("video_id")],
                              video_id=None, task_id=None)
                self.retry_queue.append(next(s for s in self.shots if s["id"] == sid))
            else:
                self.r.update(sid, push=True, status="failed", error=err, final_response=body)
        else:
            wait = 60 if (progress or 0) < 50 else 30
            if state in {"queued", "pending", ""} and (progress or 0) == 0:
                wait = 90
            self.r.update(sid, status=state or "in_progress", progress=progress,
                          next_poll_epoch=time.time() + wait, poll_failures=0)

    def poll_loop(self) -> None:
        while True:
            with LOCK:
                live = list(self.outstanding)
            if not live and self.creator_done.is_set() and not self.retry_queue:
                return
            if time.monotonic() > self.deadline:
                self.stop_reason = self.stop_reason or "time budget used; outstanding tasks resume next run"
                return
            if time.monotonic() < self.poll_block_until or not live:
                time.sleep(2)
                continue
            due = sorted(live, key=lambda s: float(self.r.row(s).get("next_poll_epoch", 0)))
            sid = due[0]
            if float(self.r.row(sid).get("next_poll_epoch", 0)) > time.time():
                time.sleep(1)
                continue
            self.status_once(sid)
            time.sleep(POLL_SPACING)
            self.r.push()

    # —— downloads ——
    def queue_download(self, shot: dict, url: str, restore: bool = False) -> None:
        self.futures.append(self.downloads.submit(self.download_one, shot, url, restore))

    def download_one(self, shot: dict, url: str, restore: bool) -> None:
        sid = shot["id"]
        dest = WORK / f"{sid}.mp4"
        try:
            size = agnes.download(url, dest, retries=4, retry_delay=5)
            digest = sha(dest)
            saved = self.r.row(sid).get("sha256")
            if restore and saved and saved != digest:
                raise RuntimeError("restored file SHA differs from receipt")
            info = inspect_clip(dest, sid)
            self.r.update(sid, push=True, status="completed", bytes=size, sha256=digest, inspection=info,
                          visual_review=self.r.row(sid).get("visual_review", "pending"), completed_at=now(), error=None)
            log(f"{sid}: downloaded + decoded ({info['duration_seconds']}s {info['width']}x{info['height']}, "
                f"motion {info['motion_mean_difference']})")
        except Exception as exc:  # keep the URL; next run restores without re-creating
            self.r.update(sid, push=True, status="completed" if restore else "download_pending",
                          download_error=self.redact(exc))
            log(f"{sid}: download/inspect problem: {self.redact(exc)[:200]}")

    def run(self) -> int:
        self.retry_queue: list[dict] = []
        to_create = self.plan()
        log(f"plan: {len(to_create)} to create, {len(self.outstanding)} already queued at Agnes")
        self.r.push(force=True, message=f"{SLUG}: generation run started [skip ci]")
        poller = threading.Thread(target=self.poll_loop, name="poller", daemon=True)
        poller.start()
        self.create_all(to_create)
        # Agnes-side failures (e.g. upload_timeout) get one automatic re-create; keep polling meanwhile.
        while True:
            if self.retry_queue:
                batch, self.retry_queue = self.retry_queue, []
                self.creator_done.clear()
                self.create_all(batch)
            with LOCK:
                live = bool(self.outstanding)
            if not live and not self.retry_queue:
                break
            if time.monotonic() > self.deadline:
                break
            if not poller.is_alive():
                poller = threading.Thread(target=self.poll_loop, name="poller", daemon=True)
                poller.start()
            time.sleep(5)
        poller.join(timeout=max(1.0, self.deadline - time.monotonic()))
        self.downloads.shutdown(wait=True)
        with LOCK:
            rows = self.r.doc.get("shots", {})
            done = sorted(s for s, r in rows.items() if r.get("status") == "completed" and r.get("sha256"))
            pending = [s["id"] for s in self.project["shots"] if s["id"] not in done]
            self.r.doc.update(phase="clips_ready" if not pending else "clips_pending_resume",
                              pending_shots=pending, stop_reason=self.stop_reason or None,
                              completed_count=len(done), finished_at=now())
        self.r.push(force=True, message=f"{SLUG}: Agnes run finished {len(done)}/30 [skip ci]")
        log(f"COMPLETE: {len(done)}/30 clips; pending={pending}; stop={self.stop_reason or '-'}")
        return 0 if not pending else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--payload", default='{"mode":"full"}')
    ap.add_argument("--budget-hours", type=float, default=5.3)
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    project = json.loads(PLAN.read_text(encoding="utf-8"))
    problems = validate(project, require_refs=False)
    if args.validate:
        print(f"VALID: 30 shots / 180s; {MODEL} mode=reference 720P; prompts STYLE…NEGATIVE; anchors verbatim")
        print(f"reference gate: {'OK' if not problems else 'BLOCKED — ' + '; '.join(problems)}")
        return 0
    options = json.loads(args.payload or "{}")
    ids = [x.strip().upper() for x in str(options.get("only", "")).split(",") if x.strip()]
    shots = [s for s in project["shots"] if not ids or s["id"] in ids]
    if args.dry_run:
        p = payload(shots[0], revision() or "0" * 40)
        p["prompt"] = p["prompt"][:160] + f"… [{len(p['prompt'])} chars]"
        print(json.dumps(p, ensure_ascii=False, indent=2))
        return 0
    if os.getenv("GITHUB_ACTIONS", "").lower() != "true" or not args.publish:
        raise SystemExit("Live Agnes requests only run inside the fixed-branch GitHub Actions workflow")
    validate(project, require_refs=True)
    key = os.getenv("AGNES_API_KEY", "").strip()
    if not key:
        raise SystemExit("AGNES_API_KEY secret unavailable; no request sent")
    base = os.getenv("AGNES_BASE_URL", "").strip() or agnes.DEFAULT_BASE_URL
    WORK.mkdir(parents=True, exist_ok=True)
    doc = read_results()
    doc.update(project=SLUG, model=MODEL, mode="reference", branch=BRANCH, reference_revision=revision(),
               phase="generating", started_at=now(),
               rate_policy={"creates_per_minute": CREATES_PER_MINUTE, "create_interval_seconds": CREATE_INTERVAL,
                            "poll_spacing_seconds": POLL_SPACING, "retry_after_respected": True,
                            "key_rotation": False, "queue_all_then_poll": True})
    force = {x.strip().upper() for x in str(options.get("force", "")).split(",") if x.strip()}
    receipts = Receipts(doc, publish=True)
    producer = Producer(project, shots, key, base, time.monotonic() + args.budget_hours * 3600,
                        receipts, revision(), force)
    return producer.run()


if __name__ == "__main__":
    raise SystemExit(main())
