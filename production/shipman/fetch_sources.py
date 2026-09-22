#!/usr/bin/env python3
"""Restore the already-generated Agnes footage on a fresh runner.

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
import sys
import time
import urllib.request
import subprocess
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from media import probe  # noqa: E402

ATTEMPTS = 12
MIN_DURATION = 6.0
MAX_DURATION = 20.0


def digest(path: Path) -> str:
    handle = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            handle.update(block)
    return handle.hexdigest()


def download_urllib(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 arena-shipman-refetch/1.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    })
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as out:
        while True:
            block = response.read(1024 * 512)
            if not block:
                break
            out.write(block)

def download_curl(url: str, destination: Path) -> None:
    # curl with retries, http1.1, insecure fallback, 180s timeout
    cmd = [
        "curl", "-L", "--fail", "--retry", "5", "--retry-delay", "5",
        "--connect-timeout", "30", "--max-time", "300",
        "--http1.1",
        "-A", "Mozilla/5.0 (X11; Linux x86_64) arena-shipman-refetch/1.0",
        "-o", str(destination),
        url
    ]
    # Try with default, if fails try with --insecure
    try:
        subprocess.check_call(cmd, timeout=320)
    except Exception:
        cmd_insecure = cmd + ["--insecure"]
        # Replace -o position? Actually --insecure before -o is okay
        cmd2 = [
            "curl", "-L", "--fail", "--retry", "5", "--retry-delay", "5",
            "--connect-timeout", "30", "--max-time", "300",
            "--http1.1", "--insecure",
            "-A", "Mozilla/5.0 arena-shipman-refetch",
            "-o", str(destination),
            url
        ]
        subprocess.check_call(cmd2, timeout=320)

def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    last_error = None
    for attempt in range(1, ATTEMPTS + 1):
        temporary.unlink(missing_ok=True)
        try:
            # Alternate methods: odd attempts urllib, even curl
            if attempt % 2 == 1:
                print(f"  attempt {attempt}/{ATTEMPTS} urllib {url[:80]}...", flush=True)
                download_urllib(url, temporary)
            else:
                print(f"  attempt {attempt}/{ATTEMPTS} curl {url[:80]}...", flush=True)
                download_curl(url, temporary)
            # Verify file not empty
            if temporary.stat().st_size < 100000:
                raise RuntimeError(f"downloaded file too small {temporary.stat().st_size}")
            temporary.replace(destination)
            return
        except Exception as error:
            last_error = error
            print(f"  retry {attempt}/{ATTEMPTS} after {type(error).__name__}: {error}", flush=True)
            temporary.unlink(missing_ok=True)
            if attempt < ATTEMPTS:
                sleep_time = min(5 * attempt + (attempt//3)*10, 30)
                time.sleep(sleep_time)
    raise RuntimeError(f"Download failed for {url}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=HERE / "story.json")
    parser.add_argument("--results", type=Path, default=HERE / "results.json")
    parser.add_argument("--dest", type=Path, required=True, help="Directory for Sxx.mp4 clips")
    args = parser.parse_args()

    project = json.loads(args.project.read_text(encoding="utf-8"))
    results = json.loads(args.results.read_text(encoding="utf-8"))
    from generate import request_hash  # noqa: E402 - imports the Agnes client config

    needed = [shot for shot in project["shots"] if shot["kind"] == "agnes"]
    report = {"requested": len(needed), "downloaded": [], "reused": [], "missing": []}

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
        download(url, destination)
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

    if report["missing"]:
        raise RuntimeError("Clips without a verified generation (regeneration required): "
                           + ", ".join(report["missing"]))
    if len(report["downloaded"]) + len(report["reused"]) != len(needed):
        raise RuntimeError("Not all Agnes clips were restored: " + json.dumps(report, ensure_ascii=False))
    print("FETCH_COMPLETE " + json.dumps({"downloaded": len(report["downloaded"]),
                                          "reused": len(report["reused"]),
                                          "clips": len(needed)}, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
