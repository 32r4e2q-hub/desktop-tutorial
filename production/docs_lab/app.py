#!/usr/bin/env python3
"""资料 / 剧本上传区（本地网页，独立服务）。

工作区（workspace）是这里的组织单位：一个案子的资料和一个剧本放在同一个工作区里，
剧本的「逐句出处映射」才能指着资料说话。

两个 tab：

* **资料** —— PDF / Word / Markdown / TXT / 网页存档 → 拆成带出处的段落
  （文件 + 页码 + 段号）→ 抽候选事实句、时间线、待标注的不确定句 → 事实底稿.md；
* **剧本** —— 解说词 → 查章数 / 字数 / 时长 / TTS 风险词 / 数字读法，
  并逐句回指资料段落，给出「对得上 / 弱 / 没出处」。

只做抽取与体检，**不替人判断真假，也不自动写进 `build_story.py`**——
核完的 `SOURCES` / `PRINCIPLES` 仍然由人填（手册第 1 步）。

启动::

    python3 production/docs_lab/app.py --port 8010
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))          # 还想 import 得到 production/ 下的东西时用

from extract import extract_document, save_extracted  # type: ignore  # noqa: E402
from factbase import build_factbase, write_factbase  # type: ignore  # noqa: E402
from script_qa import qa_script, write_qa  # type: ignore  # noqa: E402

WORKSPACES = HERE / "workspaces"
WEB = HERE / "web"
CHUNK = 1 << 20
MAX_BYTES = 200 * 1024 * 1024            # 单文件 200 MB 上限
DOC_EXT = {".pdf", ".docx", ".md", ".markdown", ".txt", ".text", ".html", ".htm", ".srt"}
SCRIPT_EXT = {".md", ".markdown", ".txt", ".text"}

app = FastAPI(title="资料与剧本工作台", docs_url="/api/docs")


# --------------------------------------------------------------------------- 工作区


def _ws_dir(ws: str) -> Path:
    if not re.fullmatch(r"[\w\u4e00-\u9fff-]{1,40}", ws or ""):
        raise HTTPException(status_code=400, detail="工作区名字只能用中文/字母/数字/连字符，40 字以内")
    d = WORKSPACES / ws
    d.mkdir(parents=True, exist_ok=True)
    for sub in ("docs", "extracted", "scripts"):
        (d / sub).mkdir(exist_ok=True)
    return d


def _state(ws_dir: Path) -> dict:
    p = ws_dir / "state.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"workspace": ws_dir.name, "docs": [], "scripts": []}


def _save_state(ws_dir: Path, st: dict) -> None:
    (ws_dir / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_name(name: str) -> str:
    name = Path(name or "").name
    return re.sub(r"[^\w.\u4e00-\u9fff-]", "_", name)[:120] or "unnamed"


def _extracted_docs(ws_dir: Path) -> List[dict]:
    docs = []
    for p in sorted((ws_dir / "extracted").glob("*.json")):
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        meta = _state(ws_dir)
        uploaded = next((d.get("uploaded_at") for d in meta.get("docs", []) if d.get("file") == doc.get("file")), None)
        doc["uploaded_at"] = uploaded
        docs.append(doc)
    return docs


def _rebuild_factbase(ws_dir: Path) -> dict:
    fb = build_factbase(_extracted_docs(ws_dir), workspace=ws_dir.name)
    write_factbase(ws_dir, fb)
    return fb


# --------------------------------------------------------------------------- 页面


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"))


@app.get("/api/workspaces")
async def list_workspaces() -> JSONResponse:
    out = []
    if WORKSPACES.exists():
        for d in sorted(WORKSPACES.iterdir()):
            if not d.is_dir():
                continue
            st = _state(d)
            out.append({
                "name": d.name,
                "docs": len(st.get("docs", [])),
                "scripts": len(st.get("scripts", [])),
                "updated": max(
                    [p.stat().st_mtime for p in [d / "sources.json", d / "script-qa.json", d / "state.json"] if p.exists()]
                    or [d.stat().st_mtime]
                ),
            })
    out.sort(key=lambda x: -x["updated"])
    return JSONResponse({"workspaces": out})


@app.post("/api/docs/{ws}")
async def upload_docs(ws: str, files: List[UploadFile] = File(...)) -> JSONResponse:
    ws_dir = _ws_dir(ws)
    st = _state(ws_dir)
    results = []
    for up in files:
        name = _safe_name(up.filename or "")
        ext = Path(name).suffix.lower()
        if ext not in DOC_EXT:
            results.append({"file": name, "ok": False,
                            "error": f"不支持 {ext or '（无扩展名）'}，支持 pdf / docx / md / txt / html"})
            await up.close()
            continue
        dest = ws_dir / "docs" / name
        size = 0
        try:
            with open(dest, "wb") as fh:
                while True:
                    chunk = await up.read(CHUNK)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise HTTPException(status_code=413, detail=f"{name} 超过 200 MB 上限")
                    fh.write(chunk)
        finally:
            await up.close()
        if size == 0:
            dest.unlink(missing_ok=True)
            results.append({"file": name, "ok": False, "error": "空文件"})
            continue
        try:
            doc = extract_document(dest)
        except Exception as exc:
            dest.unlink(missing_ok=True)
            results.append({"file": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"})
            continue
        doc["uploaded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_extracted(doc, ws_dir / "extracted")
        st["docs"] = [d for d in st.get("docs", []) if d.get("file") != name]
        st["docs"].append({"file": name, "kind": doc["kind"], "pages": doc["pages"],
                           "paragraph_count": doc["paragraph_count"], "chars": doc["chars"],
                           "bytes": doc["bytes"], "sha256": doc["sha256"],
                           "uploaded_at": doc["uploaded_at"]})
        results.append({"file": name, "ok": True, "kind": doc["kind"], "pages": doc["pages"],
                        "paragraphs": doc["paragraph_count"], "chars": doc["chars"]})
    _save_state(ws_dir, st)
    fb = _rebuild_factbase(ws_dir)
    return JSONResponse({"results": results, "stats": fb["stats"], "workspace": ws})


@app.get("/api/docs/{ws}")
async def list_docs(ws: str) -> JSONResponse:
    ws_dir = _ws_dir(ws)
    return JSONResponse({"workspace": ws, "docs": _state(ws_dir).get("docs", [])})


@app.delete("/api/doc/{ws}/{name}")
async def delete_doc(ws: str, name: str) -> JSONResponse:
    ws_dir = _ws_dir(ws)
    name = _safe_name(name)
    (ws_dir / "docs" / name).unlink(missing_ok=True)
    (ws_dir / "extracted" / (name + ".json")).unlink(missing_ok=True)
    st = _state(ws_dir)
    st["docs"] = [d for d in st.get("docs", []) if d.get("file") != name]
    _save_state(ws_dir, st)
    _rebuild_factbase(ws_dir)
    return JSONResponse({"deleted": name, "stats": _rebuild_factbase(ws_dir)["stats"]})


@app.post("/api/rebuild/{ws}")
async def rebuild(ws: str) -> JSONResponse:
    return JSONResponse(_rebuild_factbase(_ws_dir(ws)))


@app.get("/api/factbase/{ws}")
async def factbase(ws: str) -> JSONResponse:
    ws_dir = _ws_dir(ws)
    src = ws_dir / "sources.json"
    md = ws_dir / "事实底稿.md"
    return JSONResponse({
        "workspace": ws,
        "sources": json.loads(src.read_text(encoding="utf-8")) if src.exists() else None,
        "markdown": md.read_text(encoding="utf-8") if md.exists() else "",
    })


@app.post("/api/script/{ws}")
async def upload_script(ws: str, file: UploadFile = File(...)) -> JSONResponse:
    ws_dir = _ws_dir(ws)
    name = _safe_name(file.filename or "script.md")
    if Path(name).suffix.lower() not in SCRIPT_EXT:
        raise HTTPException(status_code=400, detail="剧本只收 md / txt")
    dest = ws_dir / "scripts" / name
    size = 0
    try:
        with open(dest, "wb") as fh:
            while True:
                chunk = await file.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(status_code=413, detail="剧本超过 200 MB")
                fh.write(chunk)
    finally:
        await file.close()
    text = dest.read_text(encoding="utf-8", errors="replace")
    qa = qa_script(text, _extracted_docs(ws_dir), script_name=name)
    write_qa(ws_dir, qa)
    st = _state(ws_dir)
    st["scripts"] = [s for s in st.get("scripts", []) if s.get("file") != name]
    st["scripts"].append({"file": name, "chars": qa["totals"]["chars"],
                          "chapters": qa["totals"]["chapters"],
                          "seconds": qa["totals"]["estimated_seconds"],
                          "coverage": qa["citations"]["coverage"],
                          "checked_at": qa["checked_at"]})
    _save_state(ws_dir, st)
    return JSONResponse(qa)


@app.get("/api/script/{ws}")
async def get_script_qa(ws: str) -> JSONResponse:
    ws_dir = _ws_dir(ws)
    p = ws_dir / "script-qa.json"
    md = ws_dir / "剧本体检.md"
    return JSONResponse({
        "workspace": ws,
        "qa": json.loads(p.read_text(encoding="utf-8")) if p.exists() else None,
        "markdown": md.read_text(encoding="utf-8") if md.exists() else "",
    })


@app.delete("/api/workspace/{ws}")
async def delete_workspace(ws: str) -> JSONResponse:
    ws_dir = _ws_dir(ws)
    shutil.rmtree(ws_dir, ignore_errors=True)
    return JSONResponse({"deleted": ws})


@app.get("/media/{ws}/{kind}/{name}")
async def media(ws: str, kind: str, name: str, request: Request):
    if kind not in ("docs", "scripts"):
        raise HTTPException(status_code=404, detail="没有这类文件")
    path = _ws_dir(ws) / kind / _safe_name(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="没有这个文件")
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=ctype, headers={"Accept-Ranges": "bytes",
                                                         "Content-Disposition": "inline"})


def main() -> int:
    ap = argparse.ArgumentParser(description="资料与剧本上传区")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8010)
    args = ap.parse_args()
    import uvicorn

    WORKSPACES.mkdir(parents=True, exist_ok=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
