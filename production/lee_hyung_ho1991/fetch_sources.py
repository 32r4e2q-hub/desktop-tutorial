#!/usr/bin/env python3
"""Restore the already-generated CogVideoX-Flash footage on a fresh runner.

Generated clips are never committed to Git: they live on the provider CDN and in
Actions artifacts. Every generation is recorded in ``results.json`` with its
request hash, byte size and SHA-256, so a re-render can pull the exact same
footage back instead of spending new generation quota — and, crucially, cannot
quietly substitute something else when a clip is missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from media import probe  # noqa: E402

ATTEMPTS = 4
MIN_DURATION = 4.0
MAX_DURATION = 20.0


def digest(path: Path) -> str:
    handle = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            handle.update(block)
    return handle.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    last_error = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "arena-lee-hyung-ho1991-refetch/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as out:
                while True:
                    block = response.read(1024 * 256)
                    if not block:
                        break
                    out.write(block)
            temporary.replace(destination)
            return
        except Exception as error:  # noqa: BLE001 - retried below
            last_error = error
            temporary.unlink(missing_ok=True)
            if attempt < ATTEMPTS:
                print(f"  retry {attempt}/{ATTEMPTS - 1} after {type(error).__name__}: {error}", flush=True)
                time.sleep(attempt * 5)
    raise RuntimeError(f"Download failed for {url}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=HERE / "story.json")
    parser.add_argument("--results", type=Path, default=HERE / "results.json")
    parser.add_argument("--dest", type=Path, required=True, help="Directory for Sxx.mp4 clips")
    parser.add_argument("--allow-incomplete", action="store_true", help="Preflight: fetch available verified receipts; missing receipts are allowed, broken downloads are not")
    args = parser.parse_args()

    project = json.loads(args.project.read_text(encoding="utf-8"))
    results = json.loads(args.results.read_text(encoding="utf-8"))
    from generate import request_hash  # noqa: E402 - imports the CogVideoX client config

    needed = [shot for shot in project["shots"] if shot["kind"] == "cogvideo"]
    report = {"requested": len(needed), "downloaded": [], "reused": [], "missing": []}

    refreshed = False
    for shot in needed:
        sid = shot["id"]
        receipt = results.get("shots", {}).get(sid, {})
        destination = args.dest / f"{sid}.mp4"
        wanted_hash = request_hash(project, shot)
        url = receipt.get("video_url")
        if receipt.get("status") != "completed" or not url or receipt.get("request_hash") != wanted_hash:
            report["missing"].append(sid)
            print(f"MISSING_RECEIPT {sid}: no verified generation to fetch", flush=True)
            continue
        if destination.exists() and digest(destination) == receipt["sha256"]:
            report["reused"].append(sid)
            continue
        print(f"FETCH {sid} {url}", flush=True)
        try:
            download(url, destination)
        except RuntimeError:
            # CDN links are signed and expire; query the SAME successful task,
            # never pay for a replacement of already verified footage.
            key = os.getenv('ZHIPUAI_API_KEY', '').strip()
            if not key or not receipt.get('task_id'):
                raise
            from zhipuai import ZhipuAI
            from generate import obj_get
            client = ZhipuAI(api_key=key, timeout=60.0, max_retries=0)
            result = client.videos.retrieve_videos_result(id=receipt['task_id'])
            videos = obj_get(result, 'video_result') or []
            fresh_url = obj_get(videos[0], 'url') if videos else None
            if str(obj_get(result, 'task_status', '')).upper() != 'SUCCESS' or not fresh_url:
                raise RuntimeError(f'{sid}: existing task cannot restore its successful source; not regenerating it')
            print(f'REFRESH_URL {sid}: querying original successful task, SHA-256 remains mandatory', flush=True)
            download(fresh_url, destination)
            receipt['video_url'] = fresh_url
            refreshed = True
        found = digest(destination)
        if found != receipt["sha256"]:
            raise RuntimeError(f"{sid}: downloaded bytes do not match the recorded SHA-256 "
                               f"({found} != {receipt['sha256']})")
        info = probe(destination)
        if not MIN_DURATION <= info["duration"] <= MAX_DURATION or info.get("width", 0) < 640:
            raise RuntimeError(f"{sid}: fetched clip is unusable: {info}")
        report["downloaded"].append({"id": sid, "bytes": destination.stat().st_size,
                                     "duration": round(info["duration"], 3),
                                     "size": f"{info.get('width')}x{info.get('height')}"})
        print(f"  OK {sid} {destination.stat().st_size} bytes / {info['duration']:.2f}s", flush=True)

    if refreshed:
        args.results.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if report["missing"] and not args.allow_incomplete:
        raise RuntimeError("Clips without a verified generation (regeneration required): "
                           + ", ".join(report["missing"]))
    if len(report["downloaded"]) + len(report["reused"]) != len(needed) - (len(report["missing"]) if args.allow_incomplete else 0):
        raise RuntimeError("Not all CogVideoX clips were restored: " + json.dumps(report, ensure_ascii=False))
    print("FETCH_COMPLETE " + json.dumps({"downloaded": len(report["downloaded"]),
                                          "reused": len(report["reused"]),
                                          "clips": len(needed), "missing": len(report["missing"])}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
