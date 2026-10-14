#!/usr/bin/env python3
"""智谱 CogVideoX-Flash 生成引擎（本片不用 Agnes）。

读 story.json 的 40 镜，调用智谱视频生成 API（仓库 Secrets 里的
ZHIPUAI_API_KEY，只在 GitHub Actions 里存在，沙箱读不到）：
提交 → 轮询 → 下载到 work/sinjeong2005/sources/Sxx.mp4 → ffprobe 检验 →
qa/Sxx.jpg 接触表 → results.json 回执（SHA-256 + 请求哈希，断点续跑靠它）。

    python3 production/sinjeong2005/generate.py --validate
    python3 production/sinjeong2005/generate.py --payload '{"workers":1}'
    python3 production/sinjeong2005/generate.py --payload '{"only":"S03,S08"}'   # 只补做
    python3 production/sinjeong2005/generate.py --prune-failed                    # 清死记录

调度方式（2026-10-14 改）：流水线式——先快速探活旧任务，能收的先收；
缺任务的逐个提交（限流 1305/429 就先跳过、稍后再试），然后多任务轮流
轮询收割。智谱免费档单任务排队可达几十分钟，串行一镜一镜等会把整轮
预算耗在少数镜头上；流水线让供应商队列自己并行。
"""
from __future__ import annotations

import argparse
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
PLAN = HERE / "story.json"
RESULTS = HERE / "results.json"
BRANCH = "arena/f3e80641-desktop-tutorial"
MODEL = "cogvideox-flash"
SIZE = "1920x1080"
FPS = 30
DURATION = 10
GRID_SECONDS = 6


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def full_prompt(project, shot):
    return (project.get("style_prefix", "") + shot["prompt"]).strip()


def shot_anchor_url(shot):
    """返回本镜头复用的角色参考人像 URL；无映射时走普通文生。"""
    anchors = read_json(HERE / "portrait_anchors.json", {})
    key = (anchors.get("shots") or {}).get(shot["id"])
    if not key:
        return None
    entry = (anchors.get("portraits") or {}).get(key)
    if isinstance(entry, dict):
        return entry.get("url")
    return entry if isinstance(entry, str) and entry.startswith("https://") else None


def payload_for(project, shot):
    # cogvideox-flash 实测固定约 5.1 秒；重复出场角色可以用同一张参考人像图生，
    # 保持演员脸部连续。锚点 URL 和模式都进入哈希，任何参考图变化都会触发对应镜头重做。
    anchor = shot_anchor_url(shot)
    payload = {"model": MODEL, "prompt": full_prompt(project, shot),
               "quality": os.getenv("ZHIPU_QUALITY", "speed"),
               "size": SIZE, "fps": FPS, "duration": DURATION,
               "mode": "image_v1" if anchor else "text_v2"}
    if anchor:
        payload["image_url"] = anchor
    return payload


def request_hash(project, shot):
    payload = payload_for(project, shot)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def validate(project):
    shots = project["shots"]
    if project["target_duration"] != 180:
        raise ValueError("Expected the 180-second plan")
    if sum(c["duration"] for c in project["chapters"]) != 180:
        raise ValueError("Invalid chapter plan")
    if project.get("model") != MODEL:
        raise ValueError(f"本片指定智谱 {MODEL}，story.json 里却是 {project.get('model')}")
    for shot in shots:
        if shot["kind"] != "zhipu":
            raise ValueError(f"{shot['id']}: 本片全部镜头应为 zhipu，实际 {shot['kind']}")
        prompt = full_prompt(project, shot)
        if not prompt:
            raise ValueError(f"{shot['id']}: empty prompt")
        if len(prompt) > 512:
            raise ValueError(f"{shot['id']}: 智谱提示词 {len(prompt)} 字超过 512 上限")
    for chapter in project["chapters"]:
        if not chapter["text"].strip():
            raise ValueError(f"{chapter['id']}: empty narration")
    print(f"VALID: 180s plan; {len(shots)} Zhipu shots; prompts ≤512 chars; chapters ok")
    return True


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, timeout=180,
                          capture_output=True, text=True).stdout


def inspect_clip(path, qa_dir, sid):
    sys.path.insert(0, str(HERE))
    from media import probe
    info = probe(path)
    if info["duration"] < 4.5 or info.get("width", 0) < 640:
        raise RuntimeError(f"{sid}: clip unusable: {info}")
    # 接触表：每秒 1 帧、缩到 320 宽、5×2 平铺（Actions 里有 ffmpeg）
    if shutil.which("ffmpeg"):
        qa_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path),
                        "-vf", "fps=1,scale=320:180,tile=5x2", "-frames:v", "1",
                        str(qa_dir / f"{sid}.jpg")], check=False)
    return info


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "arena-sinjeong2005/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out, 1024 * 256)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", default="{}")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--prune-failed", action="store_true")
    args = parser.parse_args()

    project = read_json(PLAN, {})
    validate(project)

    manifest = read_json(HERE / "audio/manifest.json", {})
    by_id = {r["id"]: r for r in manifest.get("clips", [])}
    for chapter in project["chapters"]:
        rec = by_id.get(chapter["id"], {})
        if rec.get("text") != chapter["text"]:
            raise ValueError("Narration text mismatch: " + chapter["id"])
        if rec.get("sha256"):
            path = HERE / "audio" / rec.get("file", "missing.mp3")
            if not path.is_file() or digest(path) != rec["sha256"]:
                raise ValueError("Narration audio mismatch: " + chapter["id"])
    if args.validate:
        return 0

    doc = read_json(RESULTS, {"project": project["title"], "model": MODEL, "shots": {}})
    doc["model"] = MODEL
    if args.prune_failed:
        # 带 task_id 的失败记录改回 queued 供断点续查（不丢已提交的任务），其余清掉重提
        stale = []
        for sid, r in list(doc.get("shots", {}).items()):
            if r.get("status") in ("failed", "blocked", "rate_limited"):
                if r.get("task_id"):
                    r["status"] = "queued"
                else:
                    doc["shots"].pop(sid, None)
                    stale.append(sid)
        RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        print("PRUNED_STALE " + json.dumps(stale))
        return 0

    options = json.loads(args.payload or "{}")
    only = {s.strip() for s in str(options.get("only", "")).split(",") if s.strip()}
    shots = [s for s in project["shots"] if s["kind"] == "zhipu"]
    if only - {s["id"] for s in shots}:
        raise ValueError("Unknown shot ID in only")
    if only:
        shots = [s for s in shots if s["id"] in only]
    shot_by_id = {s["id"]: s for s in shots}

    if args.publish:
        if os.getenv("GITHUB_ACTIONS") != "true" or git("branch", "--show-current").strip() != BRANCH:
            raise RuntimeError("Publish only from this Arena branch in Actions")
        git("config", "user.name", "github-actions[bot]")
        git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")

    sources = ROOT / "work/sinjeong2005/sources"
    sources.mkdir(parents=True, exist_ok=True)
    qa = HERE / "qa"
    deadline = time.monotonic() + 260 * 60

    def checkpoint(label, sid=None, files=(), **values):
        if sid:
            row = doc["shots"].setdefault(sid, {"id": sid})
            row.update(values)
            row["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        doc["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        doc["run_id"] = os.getenv("GITHUB_RUN_ID")
        RESULTS.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        if args.publish:
            paths = [str(RESULTS.relative_to(ROOT))] + [str(Path(p).relative_to(ROOT)) for p in files]
            git("add", "--", *paths)
            if subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=ROOT).returncode:
                git("commit", "-m", f"sinjeong2005: {label}", "--", *paths)
                for attempt in range(3):
                    try:
                        git("push", "origin", BRANCH)
                        break
                    except subprocess.CalledProcessError:
                        if attempt == 2:
                            raise
                        git("pull", "--rebase", "origin", BRANCH)
        print("PRODUCTION_STATUS " + label, flush=True)

    api_key = os.getenv("ZHIPUAI_API_KEY", "").strip()
    if not api_key:
        for shot in shots:
            checkpoint(shot["id"] + " blocked", shot["id"], status="blocked",
                       error="ZHIPUAI_API_KEY is unavailable to this workflow")
        return 1

    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=api_key)

    import concurrent.futures

    def retrieve(task_id):
        """查一次任务状态；90 秒限时，超时/异常一律按仍在处理，绝不堵住收割。"""
        last = None
        for attempt in range(2):
            pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            try:
                result = pool.submit(client.videos.retrieve_videos_result, id=task_id).result(timeout=90)
                status = getattr(result, "task_status", None) or (result.get("task_status") if isinstance(result, dict) else None)
                url = None
                if status == "SUCCESS":
                    vr = getattr(result, "video_result", None) or result.get("video_result")
                    if vr:
                        first = vr[0]
                        url = getattr(first, "url", None) or (first.get("url") if isinstance(first, dict) else None)
                return status, url, result
            except Exception as exc:  # noqa: BLE001
                last = exc
                time.sleep(10)
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
        msg = str(last)
        if '"task_status":"FAIL"' in msg or '"code":"1301"' in msg or "1301" in msg:
            print(f"查询返回失败状态（1301 等）：{msg[:160]}", flush=True)
            return "FAIL", None, msg
        print(f"查询异常（按处理中处理）：{msg[:120]}", flush=True)
        return "PROCESSING", None, None

    def finish(sid, url, label):
        dest = sources / f"{sid}.mp4"
        download(url, dest)
        info = inspect_clip(dest, qa, sid)
        checkpoint(sid + " " + label, sid, files=[qa / f"{sid}.jpg"],
                   status="completed", request_hash=request_hash(project, shot_by_id[sid]),
                   video_url=url, sha256=digest(dest), bytes=dest.stat().st_size,
                   inspection=info, visual_review="pending", error=None)
        return True

    def submit_one(shot, max_attempts=6):
        """提交一镜。限流就抛 RateLimited 让主循环稍后再试；真参数错降档到 720p。"""
        base = payload_for(project, shot)
        base.pop("mode", None)
        variants = [base, {**base, "size": "1280x720"}]
        last_error = None
        for variant in variants:
            for attempt in range(1, max_attempts + 1):
                try:
                    resp = client.videos.generations(**variant)
                    task_id = getattr(resp, "id", None) or (resp.get("id") if isinstance(resp, dict) else None)
                    if task_id:
                        return str(task_id), variant
                    raise RuntimeError(f"智谱未返回任务 id：{resp}")
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    msg = str(exc)
                    if "1305" in msg or "429" in msg or "访问量过大" in msg:
                        print(f"{shot['id']}: 智谱限流 1305，第 {attempt} 次，等 30s", flush=True)
                        time.sleep(30)
                        continue
                    print(f"{shot['id']}: 本档提交失败，尝试下一档：{msg[:200]}", flush=True)
                    break
            else:
                # 本档尝试全被限流打回：降档也没用，直接抛给主循环稍后再试
                raise RuntimeError(f"提交失败：{last_error}")
        raise RuntimeError(f"提交失败：{last_error}")

    class RateLimited(Exception):
        pass

    checkpoint("zhipu generation started")

    # ---- 阶段 0：复用已完成的（按回执链接+哈希校验），其次收集旧任务 ----
    done = set()
    outstanding = {}   # sid -> task_id（已提交、待收割）
    needs_submit = []  # 待提交（或待重提）的 sid
    for shot in shots:
        sid = shot["id"]
        wanted = request_hash(project, shot)
        old = dict(doc["shots"].get(sid, {}))
        if old.get("status") == "completed" and old.get("request_hash") == wanted and old.get("video_url"):
            try:
                dest = sources / f"{sid}.mp4"
                download(old["video_url"], dest)
                if digest(dest) == old["sha256"]:
                    info = inspect_clip(dest, qa, sid)
                    checkpoint(sid + " reused", sid, files=[qa / f"{sid}.jpg"],
                               status="completed", request_hash=wanted, inspection=info,
                               reused_existing_asset=True, error=None)
                    done.add(sid)
                    continue
            except Exception:
                print(f"{sid}: 旧链接失效，重新生成", flush=True)
        if old.get("task_id") and old.get("request_hash") == wanted and old.get("status") in (
                "queued", "submitting", "first_frame", "failed", "rate_limited", "pending"):
            outstanding[sid] = str(old["task_id"])
        else:
            needs_submit.append(sid)

    # ---- 阶段 1：快速探活旧任务，能收的先收，死了的排队重提 ----
    for sid in list(outstanding):
        status, url, raw = retrieve(outstanding[sid])
        print(f"{sid}: 旧任务状态 {status}", flush=True)
        if status == "SUCCESS" and url:
            try:
                finish(sid, url, "completed (resumed)")
                done.add(sid)
                del outstanding[sid]
            except Exception as exc:  # noqa: BLE001
                print(f"{sid}: 收割失败，下轮再试：{str(exc)[:160]}", flush=True)
        elif status == "FAIL":
            row = doc["shots"].get(sid, {})
            if int(row.get("resubmits", 0)) < 10:
                checkpoint(sid + " task failed, requeue", sid, status="pending",
                           task_id=None, resubmits=int(row.get("resubmits", 0)) + 1,
                           error=f"旧任务 FAIL：{str(raw)[:200]}")
                needs_submit.append(sid)
            else:
                checkpoint(sid + " failed", sid, status="failed",
                           error=f"旧任务多次 FAIL：{str(raw)[:200]}")
            del outstanding[sid]

    print(f"流水线：已完成 {len(done)}，在队 {len(outstanding)}，待提交 {len(needs_submit)}", flush=True)
    last_heartbeat = time.monotonic()

    # ---- 阶段 2：提交与收割交替推进，直到全部完成或预算耗尽 ----
    while (needs_submit or outstanding) and time.monotonic() < deadline:
        # 提交一轮：每镜最多试几次，限流就留到下一轮
        for sid in list(needs_submit):
            if time.monotonic() > deadline:
                break
            shot = shot_by_id[sid]
            checkpoint(sid + " submitting", sid, status="submitting",
                       request_hash=request_hash(project, shot), error=None)
            try:
                task_id, used = submit_one(shot)
            except RuntimeError as exc:
                msg = str(exc)
                if "1305" in msg or "429" in msg or "访问量过大" in msg:
                    checkpoint(sid + " rate limited", sid, status="rate_limited",
                               error=msg.replace(api_key, "[redacted]")[:400])
                    continue  # 留在 needs_submit，下一轮再提交
                checkpoint(sid + " failed", sid, status="failed",
                           error=msg.replace(api_key, "[redacted]")[:600])
                needs_submit.remove(sid)
                continue
            checkpoint(sid + " queued", sid, status="queued", task_id=task_id,
                       used_params={k: used.get(k) for k in ("quality", "size", "fps", "duration")},
                       image_first=bool(used.get("image_url")),
                       anchor_role=(json.loads((HERE / "portrait_anchors.json").read_text()).get("shots", {}).get(sid)
                                    if used.get("image_url") else None))
            outstanding[sid] = task_id
            needs_submit.remove(sid)
        # 收割一轮
        for sid in list(outstanding):
            status, url, raw = retrieve(outstanding[sid])
            print(f"{sid}: {status}", flush=True)
            if status == "SUCCESS" and url:
                try:
                    finish(sid, url, "completed")
                    done.add(sid)
                except Exception as exc:  # noqa: BLE001
                    print(f"{sid}: 收割失败，下轮再试：{str(exc)[:160]}", flush=True)
                    continue
                del outstanding[sid]
            elif status == "FAIL":
                row = doc["shots"].get(sid, {})
                if int(row.get("resubmits", 0)) < 10:
                    checkpoint(sid + " task failed, requeue", sid, status="pending",
                               task_id=None, resubmits=int(row.get("resubmits", 0)) + 1,
                               error=f"任务 FAIL：{str(raw)[:200]}")
                    needs_submit.append(sid)
                else:
                    checkpoint(sid + " failed", sid, status="failed",
                               error=f"任务多次 FAIL：{str(raw)[:200]}")
                del outstanding[sid]
        if time.monotonic() - last_heartbeat > 600:
            last_heartbeat = time.monotonic()
            checkpoint(f"heartbeat done={len(done)} queued={len(outstanding)} submit={len(needs_submit)}")
        if needs_submit or outstanding:
            time.sleep(20)

    # ---- 收尾：未完成的保留任务号与状态，下一轮接着收 ----
    for sid in needs_submit:
        row = doc["shots"].get(sid, {})
        if row.get("status") not in ("failed",):
            checkpoint(sid + " pending (budget)", sid, status="pending",
                       request_hash=request_hash(project, shot_by_id[sid]))
    for sid, task_id in outstanding.items():
        checkpoint(sid + " queued (budget)", sid, status="queued", task_id=task_id,
                   request_hash=request_hash(project, shot_by_id[sid]))

    missing = [s["id"] for s in shots if s["id"] not in done]
    if missing:
        doc["phase"] = "generation_incomplete"
        checkpoint("generation incomplete: " + ",".join(missing))
        return 1
    doc["phase"] = "selected_sources_ready" if only else "sources_ready"
    checkpoint("all requested sources ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
