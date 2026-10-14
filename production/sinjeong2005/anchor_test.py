#!/usr/bin/env python3
"""小范围验证：同一张 CogView 参考人像能否让两条 CogVideoX 镜头保持同一角色面容。
只写 qa/anchor-test/，不修改正式 results.json，也不覆盖已完成素材。
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "qa" / "anchor-test"


def save(url: str, path: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "arena-sinjeong2005-anchor-test/1.0"})
    with urllib.request.urlopen(req, timeout=180) as response, path.open("wb") as out:
        shutil.copyfileobj(response, out, 256 * 1024)


def get(obj, key, default=None):
    return getattr(obj, key, None) or (obj.get(key, default) if isinstance(obj, dict) else default)


def retrieve(client, task_id):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        result = pool.submit(client.videos.retrieve_videos_result, id=task_id).result(timeout=75)
        status = get(result, "task_status")
        rows = get(result, "video_result", []) or []
        url = get(rows[0], "url") if status == "SUCCESS" and rows else None
        return status, url, result
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    cast = json.loads((HERE / "cast.json").read_text(encoding="utf-8"))
    role = next(c for c in cast["characters"] if c["id"] == "C7")
    shots = {s["id"]: s for s in story["shots"]}
    api_key = os.environ["ZHIPUAI_API_KEY"].strip()
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=api_key)

    report = {"purpose": "同一参考人像跨两条镜头的脸一致性测试", "character": "C7",
              "shots": ["S33", "S34"], "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "tasks": {}, "manual_review": "pending"}

    portrait_prompt = ("单人电影定妆照，横版16:9，写实真人演员：" + role["face"] +
                       "，正面半身肖像，五官清楚，克制自然的表情，灰蓝色电影灯光，浅景深，画面无字无标志。")
    try:
        response = client.images.generations(model="cogview-3-flash", prompt=portrait_prompt, size="1344x768")
        rows = get(response, "data", []) or []
        portrait_url = get(rows[0], "url") if rows else None
        if not portrait_url:
            raise RuntimeError("CogView 没返回肖像 URL")
        report["portrait_url"] = portrait_url
        portrait_path = OUT / "C7-reference.jpg"
        save(portrait_url, portrait_path)
        report["portrait_sha256"] = hashlib.sha256(portrait_path.read_bytes()).hexdigest()
    except Exception as exc:
        report["portrait_error"] = str(exc).replace(api_key, "[redacted]")[:600]
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print("ANCHOR_TEST_FAILED " + report["portrait_error"], flush=True)
        return 1

    for sid in report["shots"]:
        shot = shots[sid]
        prompt = (story.get("style_prefix", "") + shot["prompt"]).strip()
        submitted = False
        last_error = None
        for attempt in range(1, 41):
            try:
                result = client.videos.generations(model="cogvideox-flash", prompt=prompt,
                    image_url=portrait_url, quality="speed", size="1920x1080", fps=30, duration=10)
                task_id = get(result, "id")
                if not task_id:
                    raise RuntimeError("智谱未返回任务 id：" + str(result))
                report["tasks"][sid] = {"task_id": str(task_id), "status": "QUEUED"}
                submitted = True
                print(f"{sid} queued task={task_id}", flush=True)
                break
            except Exception as exc:
                last_error = exc
                text = str(exc)
                if "1305" in text or "429" in text or "访问量过大" in text:
                    print(f"{sid}: 限流第 {attempt} 次，等待30秒", flush=True)
                    time.sleep(30)
                    continue
                report["tasks"][sid] = {"status": "SUBMIT_FAILED", "error": text.replace(api_key, "[redacted]")[:600]}
                break
        if not submitted and sid not in report["tasks"]:
            report["tasks"][sid] = {"status": "SUBMIT_FAILED", "error": str(last_error).replace(api_key, "[redacted]")[:600]}

    pending = {sid: row["task_id"] for sid, row in report["tasks"].items() if row.get("task_id")}
    started = time.time()
    while pending and time.time() - started < 3600:
        for sid, task_id in list(pending.items()):
            try:
                status, url, raw = retrieve(client, task_id)
            except Exception as exc:
                print(f"{sid}: 查询异常 {str(exc)[:180]}", flush=True)
                continue
            print(f"{sid}: {status}", flush=True)
            if status == "SUCCESS" and url:
                mp4 = OUT / f"{sid}.mp4"
                try:
                    save(url, mp4)
                    row = report["tasks"][sid]
                    row.update(status="SUCCESS", video_url=url,
                               bytes=mp4.stat().st_size,
                               sha256=hashlib.sha256(mp4.read_bytes()).hexdigest())
                    jpg = OUT / f"{sid}.jpg"
                    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp4),
                                    "-vf", "fps=1,scale=320:180,tile=5x2", "-frames:v", "1", str(jpg)],
                                   check=True)
                    del pending[sid]
                except Exception as exc:
                    report["tasks"][sid].update(status="DOWNLOAD_FAILED", error=str(exc)[:400])
                    del pending[sid]
            elif status == "FAIL":
                report["tasks"][sid].update(status="FAIL", error=str(raw)[:600])
                del pending[sid]
        if pending:
            time.sleep(15)

    for sid in pending:
        report["tasks"][sid]["status"] = "PENDING_TIMEOUT"
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report["status"] = "PASS_TO_REVIEW" if all(r.get("status") == "SUCCESS" for r in report["tasks"].values()) else "INCOMPLETE"
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ANCHOR_TEST_DONE " + report["status"], flush=True)
    return 0 if report["status"] == "PASS_TO_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
