#!/usr/bin/env python3
"""Multi-provider AI video generation with automatic fallback.

Providers (tried in order, first success wins):
  agnes   – Agnes Video V2.0        env AGNES_API_KEY   (free, rate-limited)
  pixazo  – Pixazo "LTX 2.5 Free"   env PIXAZO_API_KEY  (free tier, 60 req/min)

Single shot:
  python3 production/multi_video.py --prompt "..." --seconds 6 --output output/shot.mp4

Batch (shot list JSON, resumable – finished shots are skipped):
  python3 production/multi_video.py --shots production/shots_1518.json --out-dir output/shots

Shot list format:
  {"defaults": {"seconds": 6, "aspect": "16:9", "resolution": "720p", "negative_prompt": "..."},
   "shots": [{"id": "S01", "prompt": "...", "seconds": 8, "seed": 7}, ...]}

Every generated clip gets a JSON side-car with the provider, request ids and the source URL.
Only the standard library is used so it runs on a bare GitHub Actions runner.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import agnes_video as agnes  # noqa: E402  (re-use the battle-tested Agnes client)

USER_AGENT = "multi-video-cli/1.0 (+https://github.com/32r4e2q-hub/desktop-tutorial)"
PIXAZO_BASE = os.environ.get("PIXAZO_BASE_URL", "https://gateway.pixazo.ai").rstrip("/")
PIXAZO_T2V = "/ltx-video/v1/text-to-video"          # LTX 2.5 Free – text to video
PIXAZO_I2V = "/ltx-video/v1/image-to-video"         # LTX 2.5 Free – image to video
PIXAZO_STATUS = "/v2/requests/status/"              # universal status endpoint

PIXAZO_DONE = {"COMPLETED", "SUCCEEDED", "SUCCESS", "DONE"}
PIXAZO_FAILED = {"FAILED", "ERROR", "CANCELLED", "CANCELED", "REJECTED"}

# Free LTX endpoint: W*H*num_frames must stay <= 100,000,000 or the clip gets shortened.
PIXAZO_SIZES = {
    "16:9": (1280, 704),
    "9:16": (576, 1024),
    "1:1": (960, 960),
    "4:3": (1088, 800),
    "3:4": (800, 1088),
}


class ProviderError(Exception):
    """A provider failed for this shot; the next provider should be tried."""


def log(msg: str) -> None:
    print(f"[multi-video {time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- Pixazo (LTX free)

def pixazo_http(method: str, path_or_url: str, api_key: str, payload: Optional[dict] = None, timeout: float = 60):
    url = path_or_url if path_or_url.startswith("http") else PIXAZO_BASE + path_or_url
    headers = {"Ocp-Apim-Subscription-Key": api_key, "Accept": "application/json", "User-Agent": USER_AGENT,
               "Cache-Control": "no-cache"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            code, raw = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        code, raw = exc.code, exc.read()
    except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, http.client.HTTPException) as exc:
        raise agnes.TransientError(f"{type(exc).__name__}: {exc}") from exc
    text = raw.decode("utf-8", "replace")
    try:
        body = json.loads(text) if text.strip() else None
    except ValueError:
        body = None
    return code, body, text


def pixazo_payload(shot: dict) -> Tuple[str, dict]:
    seconds = float(shot.get("seconds", 5))
    fps = int(shot.get("frame_rate", 24))
    frames = agnes.snap_frames(seconds * fps)        # 1 + 8k
    frames = max(25, min(frames, 121))               # free endpoint tops out at 121 (≈5 s @ 24 fps)
    aspect = shot.get("aspect", "16:9")
    width, height = PIXAZO_SIZES.get(aspect, PIXAZO_SIZES["16:9"])
    payload: Dict[str, Any] = {
        "prompt": shot["prompt"],
        "width": width,
        "height": height,
        "num_frames": frames,
        "frame_rate": fps,
        "steps": int(shot.get("steps", 8)),
        "cfg": float(shot.get("cfg", 3.0)),
    }
    if shot.get("negative_prompt"):
        payload["negative"] = shot["negative_prompt"]  # NB: the free endpoint wants `negative`
    if shot.get("seed") is not None:
        payload["seed"] = int(shot["seed"])
    images = shot.get("images") or []
    if images:
        payload["image_url"] = images[0]
        return PIXAZO_I2V, payload
    return PIXAZO_T2V, payload


def pixazo_find_url(body: dict) -> Optional[str]:
    out = body.get("output")
    if isinstance(out, dict):
        media = out.get("media_url")
        if isinstance(media, list) and media:
            return str(media[0])
        if isinstance(media, str):
            return media
        for key in ("video", "preview_video"):
            item = out.get(key)
            if isinstance(item, dict) and item.get("url"):
                return str(item["url"])
        if out.get("url"):
            return str(out["url"])
    return agnes.find_video_url(body)


def pixazo_generate(shot: dict, dest: Path, api_key: str, poll: float, timeout: float) -> dict:
    path, payload = pixazo_payload(shot)
    log("pixazo payload: " + json.dumps(payload, ensure_ascii=False))
    created = None
    delay = 5.0
    for attempt in range(1, 5):
        try:
            code, body, text = pixazo_http("POST", path, api_key, payload, timeout=120)
        except agnes.TransientError as exc:
            problem = f"network error: {exc}"
        else:
            if code in (200, 201, 202) and isinstance(body, dict) and body.get("request_id"):
                created = body
                break
            detail = agnes.describe_error(body, text, code)
            if code in (401, 403):
                raise ProviderError(f"pixazo auth failed (HTTP {code}): {detail} – check PIXAZO_API_KEY")
            if code == 402:
                raise ProviderError(f"pixazo: insufficient balance / free quota exhausted: {detail}")
            if code in (400, 404, 405, 413, 422):
                raise ProviderError(f"pixazo rejected the request (HTTP {code}): {detail}")
            problem = f"HTTP {code}: {detail}"
        if attempt == 4:
            raise ProviderError(f"pixazo: could not create request: {problem}")
        log(f"pixazo create: {problem}; retry in {delay:g}s")
        time.sleep(delay)
        delay = min(delay * 2, 60)

    request_id = created["request_id"]
    status_url = created.get("polling_url") or (PIXAZO_STATUS + urllib.parse.quote(str(request_id), safe=""))
    log(f"pixazo request queued: {request_id}")
    started = time.monotonic()
    failures = 0
    last = None
    while True:
        try:
            code, body, text = pixazo_http("GET", status_url, api_key, timeout=60)
        except agnes.TransientError as exc:
            failures += 1
            log(f"pixazo poll: network error ({exc}) [{failures}/24]")
        else:
            if 200 <= code < 300 and isinstance(body, dict):
                failures = 0
                state = str(body.get("status") or "").upper()
                if state != last:
                    log(f"pixazo status={state or 'unknown'} (elapsed {int(time.monotonic() - started)}s)")
                    last = state
                url = pixazo_find_url(body)
                if state in PIXAZO_DONE or (not state and url):
                    if url:
                        size = agnes.download(url, dest, retries=4, retry_delay=5.0)
                        return {"provider": "pixazo", "model": body.get("model_id") or "ltx-video", "request_id": request_id,
                                "payload": payload, "video_url": url, "size_bytes": size, "final": body}
                    log("pixazo: completed without media url yet; waiting")
                elif state in PIXAZO_FAILED:
                    raise ProviderError(f"pixazo request {state}: {body.get('error') or agnes.describe_error(body, text, code)}")
            elif code in (401, 403):
                raise ProviderError(f"pixazo auth failed while polling (HTTP {code})")
            else:
                failures += 1
                log(f"pixazo poll: HTTP {code}: {agnes.describe_error(body, text, code)} [{failures}/24]")
        if failures >= 24:
            raise ProviderError(f"pixazo: gave up after {failures} polling failures ({request_id})")
        if time.monotonic() - started > timeout:
            raise ProviderError(f"pixazo: timed out after {timeout:g}s ({request_id})")
        time.sleep(poll)


# --------------------------------------------------------------------------- Agnes wrapper

def agnes_generate(shot: dict, dest: Path, api_key: str, poll: float, timeout: float) -> dict:
    ns = argparse.Namespace(
        prompt=shot["prompt"],
        negative_prompt=shot.get("negative_prompt", ""),
        image=shot.get("images") or None,
        mode=shot.get("mode"),
        seed=shot.get("seed"),
        steps=shot.get("steps"),
        seconds=float(shot.get("seconds", 5)),
        num_frames=None,
        frame_rate=float(shot.get("frame_rate", 24)),
        aspect=shot.get("aspect", "16:9"),
        resolution=shot.get("resolution", "720p"),
        width=None,
        height=None,
        model=agnes.DEFAULT_MODEL,
    )
    payload = agnes.build_payload(ns)
    log("agnes payload: " + json.dumps(payload, ensure_ascii=False))
    base = os.environ.get("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).rstrip("/")
    try:
        created = agnes.create_task(base, api_key, payload, retries=4, retry_delay=5.0)
        video_id = created.get("video_id") or created.get("id") or created.get("task_id")
        task_id = created.get("task_id") or created.get("id")
        if not video_id:
            raise ProviderError("agnes: create response has no video_id")
        log(f"agnes task created: video_id={video_id} status={created.get('status')}")
        final, url = agnes.poll_task(base, api_key, agnes.DEFAULT_MODEL, str(video_id), str(task_id) if task_id else None,
                                     interval=poll, timeout=timeout, max_failures=24)
        size = agnes.download(url, dest, retries=4, retry_delay=5.0)
    except agnes.Fatal as exc:
        raise ProviderError(f"agnes: {exc}") from exc
    return {"provider": "agnes", "model": agnes.DEFAULT_MODEL, "request_id": str(video_id), "payload": payload,
            "video_url": url, "size_bytes": size, "final": final}


# --------------------------------------------------------------------------- orchestration

Provider = Tuple[str, str, Callable[[dict, Path, str, float, float], dict]]
PROVIDERS: List[Provider] = [
    ("agnes", "AGNES_API_KEY", agnes_generate),
    ("pixazo", "PIXAZO_API_KEY", pixazo_generate),
]


def available_providers(order: List[str]) -> List[Provider]:
    table = {name: (name, env, fn) for name, env, fn in PROVIDERS}
    chosen = []
    for name in order:
        if name not in table:
            raise SystemExit(f"unknown provider '{name}' (choose from {', '.join(table)})")
        _, env, fn = table[name]
        if os.environ.get(env, "").strip():
            chosen.append((name, env, fn))
        else:
            log(f"provider {name}: skipped – {env} not set")
    return chosen


def generate_shot(shot: dict, dest: Path, providers: List[Provider], poll: float, timeout: float) -> dict:
    errors = []
    for name, env, fn in list(providers):
        log(f"--- shot {shot.get('id', '?')}: trying {name}")
        try:
            result = fn(shot, dest, os.environ[env].strip(), poll, timeout)
        except ProviderError as exc:
            log(f"{name} failed: {exc}")
            errors.append(f"{name}: {exc}")
            continue
        result["errors_before_success"] = errors
        # sticky: the provider that just worked goes first next time (keeps the look consistent)
        idx = next(i for i, p in enumerate(providers) if p[0] == name)
        if idx:
            providers.insert(0, providers.pop(idx))
        return result
    raise ProviderError("all providers failed:\n  " + "\n  ".join(errors))


def write_sidecar(dest: Path, shot: dict, result: dict) -> Path:
    side = dest.with_suffix(".json")
    doc = {
        "shot": shot,
        "provider": result["provider"],
        "model": result.get("model"),
        "request_id": result.get("request_id"),
        "video_url": result.get("video_url"),
        "size_bytes": result.get("size_bytes"),
        "payload": result.get("payload"),
        "errors_before_success": result.get("errors_before_success", []),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    side.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return side


def load_shots(path: Path) -> List[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    defaults = doc.get("defaults", {}) if isinstance(doc, dict) else {}
    prefix = (doc.get("style_prefix") or "") if isinstance(doc, dict) else ""
    negative = (doc.get("negative") or "") if isinstance(doc, dict) else ""
    shots = doc["shots"] if isinstance(doc, dict) else doc
    merged = []
    for i, s in enumerate(shots, 1):
        shot = dict(defaults)
        shot.update(s)
        shot.setdefault("id", f"S{i:02d}")
        if not shot.get("prompt"):
            raise SystemExit(f"shot {shot['id']} has no prompt")
        if prefix and not shot.get("no_prefix"):
            shot["prompt"] = prefix + shot["prompt"]          # identical style header on every shot
        if negative and not shot.get("negative_prompt"):
            shot["negative_prompt"] = negative
        merged.append(shot)
    return merged


def github_summary(rows: List[dict]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    lines = ["## AI video shots", "", "| shot | status | provider | seconds | size | note |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {r['status']} | {r.get('provider', '-')} | {r.get('seconds', '-')} | "
                     f"{(r.get('size_bytes') or 0) / 1e6:.1f} MB | {r.get('note', '')} |")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Generate AI video clips with automatic provider fallback (Agnes → Pixazo LTX).")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt", help="single shot prompt")
    src.add_argument("--shots", type=Path, help="JSON shot list for batch mode")
    p.add_argument("--negative-prompt", default="")
    p.add_argument("--image", action="append", metavar="URL", help="public image URL (image-to-video)")
    p.add_argument("--seconds", type=float, default=5.0)
    p.add_argument("--aspect", default="16:9", choices=sorted(PIXAZO_SIZES))
    p.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p"])
    p.add_argument("--seed", type=int)
    p.add_argument("--output", type=Path, default=Path("output/video.mp4"), help="single-shot output path")
    p.add_argument("--out-dir", type=Path, default=Path("output/shots"), help="batch output directory")
    p.add_argument("--providers", default=os.environ.get("VIDEO_PROVIDERS", "agnes,pixazo"),
                   help="comma-separated priority order")
    p.add_argument("--only", default="", help="batch: comma-separated shot ids to (re)generate")
    p.add_argument("--force", action="store_true", help="batch: regenerate even if the clip already exists")
    p.add_argument("--poll-interval", type=float, default=6.0)
    p.add_argument("--timeout", type=float, default=1500.0, help="per provider, per shot")
    p.add_argument("--max-minutes", type=float, default=0.0,
                   help="batch: stop starting new shots after this many minutes (0 = no limit)")
    p.add_argument("--after-shot", default=os.environ.get("AFTER_SHOT_CMD", ""),
                   help="batch: shell command run after each finished shot (env SHOT_ID, SHOT_PATH, OUT_DIR)")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    order = [s.strip() for s in args.providers.split(",") if s.strip()]
    providers = available_providers(order)
    if not providers and not args.dry_run:
        log("no provider has an API key configured (AGNES_API_KEY / PIXAZO_API_KEY)")
        if os.environ.get("GITHUB_ACTIONS"):
            print("::error::No API key configured. Add AGNES_API_KEY and/or PIXAZO_API_KEY under Settings → Secrets → Actions.")
        return 2

    if args.shots:
        shots = load_shots(args.shots)
        out_dir: Path = args.out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        only = {s.strip() for s in args.only.split(",") if s.strip()}
        rows = []
        failures = 0
        t_start = time.monotonic()
        for shot in shots:
            sid = shot["id"]
            if only and sid not in only:
                continue
            if args.max_minutes and (time.monotonic() - t_start) / 60.0 > args.max_minutes:
                log(f"time budget of {args.max_minutes:g} min reached; leaving {sid} and later shots for the next run")
                rows.append({"id": sid, "status": "deferred", "seconds": shot.get("seconds"), "note": "time budget"})
                continue
            dest = out_dir / f"{sid}.mp4"
            if dest.exists() and dest.stat().st_size > 1024 and not args.force:
                log(f"shot {sid}: already exists, skipping ({dest})")
                rows.append({"id": sid, "status": "kept", "provider": "-", "seconds": shot.get("seconds"),
                             "size_bytes": dest.stat().st_size})
                continue
            if args.dry_run:
                print(json.dumps({"id": sid, "agnes": agnes.build_payload(argparse.Namespace(
                    prompt=shot["prompt"], negative_prompt=shot.get("negative_prompt", ""), image=shot.get("images") or None,
                    mode=None, seed=shot.get("seed"), steps=None, seconds=float(shot.get("seconds", 5)), num_frames=None,
                    frame_rate=24.0, aspect=shot.get("aspect", "16:9"), resolution=shot.get("resolution", "720p"),
                    width=None, height=None, model=agnes.DEFAULT_MODEL)), "pixazo": pixazo_payload(shot)[1]},
                    ensure_ascii=False, indent=2))
                continue
            try:
                result = generate_shot(shot, dest, providers, args.poll_interval, args.timeout)
            except ProviderError as exc:
                failures += 1
                log(f"shot {sid} FAILED: {exc}")
                if os.environ.get("GITHUB_ACTIONS"):
                    print(f"::warning::shot {sid} failed: {exc}")
                rows.append({"id": sid, "status": "failed", "seconds": shot.get("seconds"), "note": str(exc)[:160]})
                continue
            write_sidecar(dest, shot, result)
            log(f"shot {sid}: OK via {result['provider']} → {dest} ({result['size_bytes'] / 1e6:.1f} MB)")
            if args.after_shot:
                env = dict(os.environ, SHOT_ID=sid, SHOT_PATH=str(dest), OUT_DIR=str(out_dir))
                rc = subprocess.call(args.after_shot, shell=True, env=env)
                log(f"after-shot hook exit {rc}")
            rows.append({"id": sid, "status": "ok", "provider": result["provider"], "seconds": shot.get("seconds"),
                         "size_bytes": result["size_bytes"],
                         "note": "; ".join(result.get("errors_before_success", []))[:160]})
        manifest = out_dir / "manifest.json"
        manifest.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        github_summary(rows)
        ok = sum(1 for r in rows if r["status"] in ("ok", "kept"))
        log(f"batch done: {ok}/{len(rows)} clips available, {failures} failed → {manifest}")
        return 1 if failures and ok == 0 else 0

    shot = {"id": "single", "prompt": args.prompt, "negative_prompt": args.negative_prompt, "images": args.image,
            "seconds": args.seconds, "aspect": args.aspect, "resolution": args.resolution, "seed": args.seed}
    if args.dry_run:
        print(json.dumps({"pixazo": pixazo_payload(shot)[1]}, ensure_ascii=False, indent=2))
        return 0
    dest = args.output if args.output.suffix.lower() == ".mp4" else args.output.with_suffix(".mp4")
    try:
        result = generate_shot(shot, dest, providers, args.poll_interval, args.timeout)
    except ProviderError as exc:
        log(f"error: {exc}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::error::{exc}")
        return 1
    side = write_sidecar(dest, shot, result)
    log(f"saved {dest} via {result['provider']} ({result['size_bytes'] / 1e6:.2f} MB); details in {side}")
    github_summary([{"id": "single", "status": "ok", "provider": result["provider"], "seconds": args.seconds,
                     "size_bytes": result["size_bytes"]}])
    print(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
