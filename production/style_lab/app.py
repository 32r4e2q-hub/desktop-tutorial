#!/usr/bin/env python3
"""参考视频上传区（本地网页）：拖进来 → 自动量风格 → 给三组提示词候选。

只做三件事，**不做剪辑、不产出成片**：

1. 收下上传的参考片（分片写盘，顺手算 SHA-256，跟仓库其它环节一样的收据习惯）；
2. 后台跑 ``analyze.py`` + ``style_profile.py``，进度可轮询；
3. 把实测值、接触表、中文风格档案、三组 STYLE_PREFIX 候选摆到网页上。

参考片只用于分析：不复制进任何成片，音轨不参与任何输出（手册第 1 步的事实边界）。

启动::

    python3 -m uvicorn production.style_lab.app:app --host 0.0.0.0 --port 8000
    # 或：python3 production/style_lab/app.py --port 8000
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse

# `python3 -m uvicorn production.style_lab.app:app` 与
# `python3 production/style_lab/app.py` 两种启动方式都能 import 到同目录的模块
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze as analyze_mod  # type: ignore  # noqa: E402
from style_profile import build_style_profile, write_profile  # type: ignore  # noqa: E402

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
WEB = HERE / "web"
CHUNK = 1 << 20
MAX_BYTES = 4 * 1024 * 1024 * 1024  # 4 GB 上限，超过直接拒绝，避免把盘写满

STATE: dict[str, dict[str, Any]] = {}
LOCK = threading.Lock()

app = FastAPI(title="参考风格实验室", docs_url="/api/docs")


# --------------------------------------------------------------------------- 状态


def _slug(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", stem).strip("-").lower()
    return (stem or "reference")[:40]


def _set_state(run_id: str, **fields: Any) -> None:
    with LOCK:
        STATE.setdefault(run_id, {}).update(fields)


def _get_state(run_id: str) -> dict[str, Any]:
    with LOCK:
        return dict(STATE.get(run_id, {}))


def _persist(run_id: str) -> None:
    run_dir = RUNS / run_id
    if not run_dir.exists():
        return
    (run_dir / "state.json").write_text(
        json.dumps(_get_state(run_id), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_runs() -> list[dict[str, Any]]:
    runs = []
    if not RUNS.exists():
        return runs
    for d in sorted(RUNS.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta = d / "state.json"
        metrics = d / "reference_metrics.json"
        if not metrics.exists():
            continue
        try:
            m = json.loads(metrics.read_text(encoding="utf-8"))
        except Exception:
            continue
        state = {}
        if meta.exists():
            try:
                state = json.loads(meta.read_text(encoding="utf-8"))
            except Exception:
                state = {}
        runs.append({
            "run_id": d.name,
            "file": m.get("source", {}).get("file"),
            "duration": m.get("container", {}).get("duration"),
            "state": state.get("state", "done"),
            "chosen": (json.loads((d / "chosen.json").read_text(encoding="utf-8")).get("candidate")
                       if (d / "chosen.json").exists() else None),
        })
    return runs


# --------------------------------------------------------------------------- 分析线程


def _progress(run_id: str) -> Any:
    def fn(stage: str, pct: float, detail: str = "") -> None:
        _set_state(run_id, stage=stage, pct=round(float(pct), 1), detail=detail)
        if int(pct) % 10 == 0:
            _persist(run_id)

    return fn


def _run_analysis(run_id: str, video: Path, run_dir: Path, samples: int, threshold: float) -> None:
    try:
        _set_state(run_id, state="analyzing", stage="准备", pct=1.0, detail="")
        metrics = analyze_mod.analyze_video(
            video, run_dir, samples=samples, threshold=threshold, progress=_progress(run_id),
            sha256=_get_state(run_id).get("sha256"),
        )
        _set_state(run_id, state="profiling", stage="生成风格档案", pct=95.0, detail="")
        profile = build_style_profile(metrics)
        write_profile(run_dir, profile)
        _set_state(run_id, state="done", stage="完成", pct=100.0, detail="风格档案已生成")
    except Exception as exc:  # 出错也要在网页上看见，而不是转圈
        _set_state(
            run_id, state="error", stage="失败", pct=100.0,
            detail=f"{type(exc).__name__}: {exc}",
            traceback=traceback.format_exc(limit=6),
        )
    finally:
        _persist(run_id)


# --------------------------------------------------------------------------- 页面


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = (WEB / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/runs")
async def list_runs() -> JSONResponse:
    return JSONResponse({"runs": _load_runs()})


@app.post("/api/upload")
async def upload(
    request: Request,
    file: UploadFile = File(...),
    samples: int = Form(48),
    threshold: float = Form(0.24),
) -> JSONResponse:
    samples = max(12, min(96, int(samples)))
    threshold = max(0.05, min(0.9, float(threshold)))
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{_slug(file.filename or 'reference')}"
    run_dir = RUNS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "reference.mp4").suffix.lower() or ".mp4"
    dest = run_dir / f"reference{ext}"

    hasher = hashlib.sha256()
    size = 0
    try:
        with open(dest, "wb") as fh:
            while True:
                chunk = await file.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    fh.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail=f"文件超过 {MAX_BYTES // (1 << 30)} GB 上限")
                hasher.update(chunk)
                fh.write(chunk)
    finally:
        await file.close()

    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="空文件")

    _set_state(
        run_id,
        state="queued",
        stage="已上传",
        pct=0.0,
        detail=f"{size / 1_048_576:.1f} MB",
        file=file.filename,
        size=size,
        sha256=hasher.hexdigest(),
        samples=samples,
        threshold=threshold,
        created=time.strftime("%Y-%m-%d %H:%M:%S"),
    )
    _persist(run_id)

    thread = threading.Thread(
        target=_run_analysis, args=(run_id, dest, run_dir, samples, threshold), daemon=True
    )
    thread.start()
    return JSONResponse({"run_id": run_id, "size": size, "sha256": hasher.hexdigest()})


@app.get("/api/state/{run_id}")
async def state(run_id: str) -> JSONResponse:
    st = _get_state(run_id)
    if not st:
        meta = RUNS / run_id / "state.json"
        if meta.exists():
            st = json.loads(meta.read_text(encoding="utf-8"))
        else:
            raise HTTPException(status_code=404, detail="没有这个 run")
    return JSONResponse(st)


@app.get("/api/report/{run_id}")
async def report(run_id: str) -> JSONResponse:
    run_dir = RUNS / run_id
    metrics_path = run_dir / "reference_metrics.json"
    if not metrics_path.exists():
        raise HTTPException(status_code=404, detail="报告还没生成")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    candidates = {}
    cand_path = run_dir / "style-candidates.json"
    if cand_path.exists():
        candidates = json.loads(cand_path.read_text(encoding="utf-8"))
    markdown = ""
    md_path = run_dir / "风格档案.md"
    if md_path.exists():
        markdown = md_path.read_text(encoding="utf-8")
    chosen = None
    if (run_dir / "chosen.json").exists():
        chosen = json.loads((run_dir / "chosen.json").read_text(encoding="utf-8"))
    # 命令行跑出来的那一类（--no-copy）没有原片副本，播放器就别给一个 404 的地址
    ref_name = metrics.get("artifacts", {}).get("reference_copy")
    video_url = f"/media/{run_id}/{ref_name}" if ref_name and (run_dir / ref_name).exists() else None
    sheet_url = f"/media/{run_id}/contact-sheet.jpg" if (run_dir / "contact-sheet.jpg").exists() else None
    return JSONResponse({
        "run_id": run_id,
        "state": _get_state(run_id).get("state", "done"),
        "metrics": metrics,
        "candidates": candidates,
        "markdown": markdown,
        "chosen": chosen,
        "contact_sheet": sheet_url,
        "video": video_url,
    })


@app.post("/api/choose/{run_id}")
async def choose(run_id: str, payload: dict) -> JSONResponse:
    run_dir = RUNS / run_id
    cand_path = run_dir / "style-candidates.json"
    if not cand_path.exists():
        raise HTTPException(status_code=404, detail="还没有候选")
    data = json.loads(cand_path.read_text(encoding="utf-8"))
    cid = str(payload.get("candidate", ""))
    match = next((c for c in data["candidates"] if c["id"] == cid), None)
    if not match:
        raise HTTPException(status_code=400, detail=f"没有候选 {cid}")
    chosen = {
        "candidate": cid,
        "label": match["label"],
        "style_prefix": match["style_prefix"],
        "negative_prompt": match["negative_prompt"],
        "chosen_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "run_id": run_id,
    }
    (run_dir / "chosen.json").write_text(json.dumps(chosen, ensure_ascii=False, indent=2), encoding="utf-8")
    _set_state(run_id, chosen=cid)
    _persist(run_id)
    return JSONResponse(chosen)


@app.delete("/api/run/{run_id}")
async def delete_run(run_id: str) -> JSONResponse:
    run_dir = RUNS / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="没有这个 run")
    import shutil

    shutil.rmtree(run_dir)
    with LOCK:
        STATE.pop(run_id, None)
    return JSONResponse({"deleted": run_id})


# --------------------------------------------------------------------------- 媒体（支持 Range）


@app.get("/media/{run_id}/{name}")
async def media(run_id: str, name: str, request: Request):
    path = RUNS / run_id / name
    if ".." in name or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="没有这个文件")
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    size = path.stat().st_size
    range_header = request.headers.get("range")
    if not range_header:
        return FileResponse(path, media_type=ctype, headers={"Accept-Ranges": "bytes"})

    m = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not m:
        raise HTTPException(status_code=416, detail="Range 无法解析")
    start_s, end_s = m.group(1), m.group(2)
    start = int(start_s) if start_s else 0
    end = int(end_s) if end_s else size - 1
    end = min(end, size - 1)
    if start > end or start >= size:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})

    def streamer():
        with open(path, "rb") as fh:
            fh.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                data = fh.read(min(CHUNK, remaining))
                if not data:
                    break
                remaining -= len(data)
                yield data

    return StreamingResponse(
        streamer(),
        status_code=206,
        media_type=ctype,
        headers={
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="参考视频上传区")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    import uvicorn

    RUNS.mkdir(parents=True, exist_ok=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
