#!/usr/bin/env python3
"""Restore the already-generated footage (Agnes 或智谱 CogVideoX-Flash) on a fresh runner.

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
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from media import probe  # noqa: E402
# 2026-10-11：本片 38 镜改走智谱 CogVideoX-Flash 后，收据里的 request_hash 是
# generate_cogvideox 的 payload 哈希；且 5 个露脸镜（S06/S12/S16/S27/S40）实测
# 被 flash 收下 image_url、以定妆照图生视频，其收据哈希是「带定妆照」版本。
# 旧代码只认 Agnes 哈希，会把整批智谱收据判成 MISSING_RECEIPT、render 直接缺料。
# 三种合法哈希都认（Agnes / 智谱纯文生 / 智谱带定妆照），防掉包的严格性不变。
from generate import request_hash as agnes_request_hash  # noqa: E402
import generate_cogvideox as _cog  # noqa: E402


def cogvideox_request_hashes(project, shot):
    """同一镜头的两种智谱哈希：纯文生 与 带定妆照（image_url）。"""
    saved = _cog.REF_IMAGE_OK
    try:
        _cog.REF_IMAGE_OK = None
        plain = _cog.request_hash(project, shot)
        _cog.REF_IMAGE_OK = True
        with_portrait = _cog.request_hash(project, shot)
    finally:
        _cog.REF_IMAGE_OK = saved
    return plain, with_portrait

ATTEMPTS = 4
# 4.0 与 media.inspect_clip / jeong2000 实证窗口对齐：CogVideoX-Flash 出片 5.108 s，
# 旧值 6.0 按 Agnes（6–12 s）定的，会把智谱素材全部判成 unusable。
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
            request = urllib.request.Request(url, headers={"User-Agent": "arena-maryceleste1872-refetch/1.0"})
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


def refresh_video_url(task_id: str):
    """2026-10-23：智谱 CDN 签名 URL 会过期（401）。用 SDK 对已完成的 task_id 重新查询，
    平台重签出新临时 URL 就换用；SHA-256 收据校验保证换到的字节就是原片。"""
    import os
    try:
        from zhipuai import ZhipuAI
    except ImportError:
        print(f"  refresh skipped ({task_id}): zhipuai SDK not installed", flush=True)
        return None
    key = os.environ.get("ZHIPUAI_API_KEY")
    if not key:
        print(f"  refresh skipped ({task_id}): ZHIPUAI_API_KEY not set", flush=True)
        return None

    def field(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    try:
        polled = ZhipuAI(api_key=key).videos.retrieve_videos_result(id=task_id)
        status = str(field(polled, "task_status", "")).upper()
        if status != "SUCCESS":
            print(f"  refresh ({task_id}): task_status={status or 'unknown'}", flush=True)
            return None
        entries = field(polled, "video_result") or []
        first = entries[0] if entries else None
        url = field(first, "url") if first is not None else None
        return str(url) if url else None
    except Exception as error:
        print(f"  refresh ({task_id}) failed: {type(error).__name__}: {error}", flush=True)
        return None


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
        wanted_hashes = {agnes_request_hash(project, shot),
                         *cogvideox_request_hashes(project, shot)}
        url = receipt.get("video_url")
        if receipt.get("status") != "completed" or not url \
                or receipt.get("request_hash") not in wanted_hashes:
            report["missing"].append(sid)
            print(f"MISSING_RECEIPT {sid}: no verified generation to fetch", flush=True)
            continue
        if destination.exists() and digest(destination) == receipt["sha256"]:
            report["reused"].append(sid)
            continue
        print(f"FETCH {sid} {url}", flush=True)
        try:
            download(url, destination)
        except Exception as error:
            # URL 签名过期(401)是常态（2026-10-23 实测 15 小时后过期）：先按 task_id
            # 换新签名 URL，换不到再失败。换到的字节仍走 SHA-256 收据校验，防掉包口径不变。
            task_id = receipt.get("task_id")
            if not task_id:
                raise
            print(f"  URL unusable ({error}); refreshing signed URL via task {task_id}", flush=True)
            fresh = refresh_video_url(task_id)
            if not fresh:
                raise
            print(f"REFRESH {sid} {fresh}", flush=True)
            download(fresh, destination)
            try:
                doc = json.loads(args.results.read_text(encoding="utf-8"))
                doc.setdefault("shots", {}).setdefault(sid, {})["video_url"] = fresh
                args.results.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
                print(f"  results.json 已更新 {sid} 的 video_url", flush=True)
            except Exception as persist_error:
                print(f"  results.json 更新失败（不影响取片）: {persist_error}", flush=True)
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
