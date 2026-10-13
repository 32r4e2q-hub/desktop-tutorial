#!/usr/bin/env python3
"""智谱 CogVideoX-Flash 生成引擎（本片不用 Agnes）。

读 story.json 的 30 镜，逐镜调用智谱视频生成 API（仓库 Secrets 里的
ZHIPUAI_API_KEY，只在 GitHub Actions 里存在，沙箱读不到）：
提交 → 轮询 → 下载到 work/sinjeong2005/sources/Sxx.mp4 → ffprobe 检验 →
qa/Sxx.jpg 接触表 → results.json 回执（SHA-256 + 请求哈希，断点续跑靠它）。

    python3 production/sinjeong2005/generate.py --validate
    python3 production/sinjeong2005/generate.py --payload '{"workers":1}'
    python3 production/sinjeong2005/generate.py --payload '{"only":"S03,S08"}'   # 只补做
    python3 production/sinjeong2005/generate.py --prune-failed                    # 清死记录

免费节点限流（错误码 1305 / 429）按仓库既有脚本的策略退避重试；
顺序提交（一镜完成再下一镜），避免并发把免费额度打爆。
"""
from __future__ import annotations

import argparse
import concurrent.futures  # noqa: F401  （与旧接口保持兼容，实际顺序执行）
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


def payload_for(project, shot):
    # 已实测：cogvideox-flash 用 quality="speed" 档可提交；图生视频（首帧图）才给 10 秒，
    # 文生视频只有约 5 秒。所以每镜先 CogView 出首帧、再图生视频（mode 记进请求哈希）。
    return {"model": MODEL, "prompt": full_prompt(project, shot),
            "quality": os.getenv("ZHIPU_QUALITY", "speed"),
            "size": SIZE, "fps": FPS, "duration": DURATION,
            "mode": "image_first_v1"}


def request_hash(project, shot):
    payload = payload_for(project, shot)
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def validate(project):
    shots = project["shots"]
    if project["target_duration"] != 180 or len(shots) * GRID_SECONDS != 180:
        raise ValueError(f"Expected the 180-second plan on a {GRID_SECONDS}-second grid")
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
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
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
        stale = [sid for sid, r in doc.get("shots", {}).items()
                 if r.get("status") in ("failed", "blocked", "rate_limited")]
        for sid in stale:
            doc["shots"].pop(sid, None)
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

    def submit(shot, image_url=None):
        """提交一镜：1305/429 只原地退避等待（换参数解决不了限流）；真参数错才降一档。"""
        base = payload_for(project, shot)
        base.pop("mode", None)
        if image_url:
            base["image_url"] = image_url
        variants = [base]
        if image_url:
            variants.append({k: v for k, v in base.items() if k != "image_url"})  # 图生失败退文生
        variants.append({**base, "size": "1280x720"})
        last_error = None
        for variant in variants:
            for attempt in range(1, 41):
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
                        checkpoint(shot["id"] + " rate limited", shot["id"], status="rate_limited",
                                   error=msg.replace(api_key, "[redacted]")[:400])
                        time.sleep(30)
                        continue
                    print(f"{shot['id']}: 本档提交失败，尝试下一档：{msg[:200]}", flush=True)
                    break
        raise RuntimeError(f"提交失败：{last_error}")

    def make_first_frame(shot):
        """用 CogView-3-Flash（免费）按同一提示词出首帧图，返回图片 URL；失败返回 None 走文生。"""
        try:
            resp = client.images.generations(
                model="cogview-3-flash", prompt=full_prompt(project, shot), size="1344x768")
            data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
            if data:
                first = data[0]
                return getattr(first, "url", None) or (first.get("url") if isinstance(first, dict) else None)
        except Exception as exc:  # noqa: BLE001
            print(f"{shot['id']}: 首帧图生成失败，改走文生：{str(exc)[:200]}", flush=True)
        return None

    def generate(shot):
        sid = shot["id"]
        wanted = request_hash(project, shot)
        old = dict(doc["shots"].get(sid, {}))
        dest = sources / f"{sid}.mp4"
        try:
            # 断点续跑：回执在且下载到的文件哈希一致就复用，不花新额度
            if old.get("status") == "completed" and old.get("request_hash") == wanted and old.get("video_url"):
                try:
                    download(old["video_url"], dest)
                    if digest(dest) == old["sha256"]:
                        info = inspect_clip(dest, qa, sid)
                        checkpoint(sid + " reused", sid, files=[qa / f"{sid}.jpg"],
                                   status="completed", request_hash=wanted, inspection=info,
                                   reused_existing_asset=True, error=None)
                        return True
                except Exception:
                    print(f"{sid}: 旧链接失效，重新生成", flush=True)
            if time.monotonic() > deadline:
                checkpoint(sid + " pending (budget)", sid, status="pending", request_hash=wanted)
                return False
            checkpoint(sid + " submitting", sid, status="submitting", request_hash=wanted, error=None)
            image_url = make_first_frame(shot)
            if image_url:
                checkpoint(sid + " first frame ready", sid, status="first_frame", image_url=image_url)
            task_id, used = submit(shot, image_url=image_url)
            checkpoint(sid + " queued", sid, status="queued", task_id=task_id,
                       used_params={k: used.get(k) for k in ("quality", "size", "fps", "duration")},
                       image_first=bool(used.get("image_url")))
            started = time.time()
            while True:
                if time.time() - started > 1200:
                    raise RuntimeError("轮询超时 20 分钟")
                result = client.videos.retrieve_videos_result(id=task_id)
                status = getattr(result, "task_status", None) or (result.get("task_status") if isinstance(result, dict) else None)
                print(f"{sid}: [{int(time.time() - started)}s] {status}", flush=True)
                if status == "SUCCESS":
                    vr = getattr(result, "video_result", None) or result.get("video_result")
                    url = None
                    if vr:
                        first = vr[0]
                        url = getattr(first, "url", None) or (first.get("url") if isinstance(first, dict) else None)
                    if not url:
                        raise RuntimeError("SUCCESS 但无视频地址")
                    download(url, dest)
                    info = inspect_clip(dest, qa, sid)
                    checkpoint(sid + " completed", sid, files=[qa / f"{sid}.jpg"],
                               status="completed", request_hash=wanted, video_url=url,
                               sha256=digest(dest), bytes=dest.stat().st_size,
                               inspection=info, visual_review="pending", error=None)
                    return True
                if status == "FAIL":
                    raise RuntimeError(f"智谱渲染失败：{result}")
                time.sleep(8)
        except Exception as exc:  # noqa: BLE001
            checkpoint(sid + " failed", sid, status="failed",
                       error=str(exc).replace(api_key, "[redacted]")[:600])
            return False

    checkpoint("zhipu generation started")
    outcomes = [generate(shot) for shot in shots]  # 顺序执行，保护免费额度
    if not all(outcomes):
        doc["phase"] = "generation_incomplete"
        checkpoint("generation incomplete")
        return 1
    doc["phase"] = "selected_sources_ready" if only else "sources_ready"
    checkpoint("all requested sources ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
