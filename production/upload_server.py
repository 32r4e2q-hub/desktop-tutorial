#!/usr/bin/env python3
"""Resumable browser uploader for a new user-supplied commentary video."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UPLOAD_DIR = Path("incoming_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHUNK_SIZE = 5 * 1024 * 1024
MAX_SIZE = 5 * 1024**3

PAGE = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>上传全新电影解说</title><style>*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 20% 0,#1d2942,#080c15 52%,#04060b);color:#f3f6ff;font:15px/1.65 system-ui,"Microsoft YaHei"}main{width:min(720px,92vw);padding:32px;background:#141b2bf5;border:1px solid #35435f;border-radius:20px;box-shadow:0 24px 80px #0009}h1{margin:0 0 8px}.lead,.small{color:#aebbd1}.notice{margin:20px 0;padding:13px 15px;background:#202a40;border-left:4px solid #7199ff;border-radius:9px}.pick{display:block;margin:20px 0;padding:40px 20px;border:2px dashed #5d729a;border-radius:14px;text-align:center;cursor:pointer}.pick input{display:none}button{padding:12px 22px;border:0;border-radius:10px;background:#5d87f7;color:white;font-weight:750}button:disabled{opacity:.4}.track{height:10px;margin:20px 0 8px;background:#2a354d;border-radius:99px;overflow:hidden}.bar{height:100%;width:0;background:linear-gradient(90deg,#557ff3,#74c7ff)}.ok{color:#50dda0;font-weight:700}.err{color:#ff8181}.file{word-break:break-all;color:#c1cbe0}.existing{margin-top:20px;padding:12px 14px;background:#101724;border-radius:10px}</style><main><h1>上传全新电影解说视频</h1><p class=lead>支持 MP4、MOV、MKV、WebM，最大 5 GB。</p><div class=notice>成片目标：约10分钟、剧情连贯完整、保持原解说风格、清理旧字幕及水印，只保留新解说字幕。</div><label class=pick>点击选择视频<br><span class=small>采用5 MB分块上传并自动重试</span><input id=f type=file accept="video/*,.mp4,.mov,.mkv,.webm"></label><div id=n class=file>尚未选择文件</div><p><button id=g disabled>开始上传</button></p><div class=track><div id=b class=bar></div></div><div id=s>等待选择视频</div><div id=e class=existing>正在检查服务器中的文件…</div></main><script>const C=5*1024*1024,f=document.querySelector('#f'),g=document.querySelector('#g'),b=document.querySelector('#b'),s=document.querySelector('#s'),n=document.querySelector('#n'),e=document.querySelector('#e');let x;async function status(){try{let j=await(await fetch('/status')).json();e.innerHTML=j.files.length?'<b>服务器已保存：</b><br>'+j.files.map(v=>`${v.name}（${(v.size/1048576).toFixed(1)} MB）<br>SHA-256：${v.sha256||'等待校验'}`).join('<br><br>'):'服务器中尚无已完成文件'}catch(_){e.textContent='无法读取服务器状态'}}status();f.onchange=()=>{x=f.files[0];n.textContent=x?`${x.name}（${(x.size/1048576).toFixed(1)} MB）`:'尚未选择文件';g.disabled=!x};let wait=m=>new Promise(r=>setTimeout(r,m));async function send(id,i,t,a,z){let q=new URLSearchParams({id,name:x.name,index:i,total:t,size:x.size,offset:a});for(let k=1;k<=6;k++){try{let r=await fetch('/upload?'+q,{method:'POST',body:z});let j=await r.json();if(!r.ok)throw Error(j.error);return j}catch(err){if(k===6)throw err;s.textContent=`网络波动，第 ${k} 次重试…`;await wait(k*900)}}}g.onclick=async()=>{g.disabled=true;f.disabled=true;let id=Date.now().toString(36)+Math.random().toString(36).slice(2),t=Math.ceil(x.size/C),last;try{for(let i=0;i<t;i++){let a=i*C,z=Math.min(x.size,a+C);s.textContent=`上传中 ${(z/1048576).toFixed(0)} / ${(x.size/1048576).toFixed(0)} MB（${i+1}/${t}）`;last=await send(id,i,t,a,x.slice(a,z));b.style.width=(z/x.size*100)+'%'}s.className='ok';s.textContent=`上传完成 ✓  SHA-256：${last.sha256}`;g.textContent='上传完成';await status()}catch(err){s.className='err';s.textContent='上传失败：'+err.message;g.disabled=false;f.disabled=false}};</script></html>'''


def safe_name(value: str) -> str:
    value = re.sub(r"[\x00-\x1f/\\]", "_", Path(value).name).strip()
    return (value or "uploaded-video.mp4")[:220]


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def completed_files() -> list[dict]:
    rows = []
    for meta in sorted(UPLOAD_DIR.glob("*.upload.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            rows.append(json.loads(meta.read_text(encoding="utf-8")))
        except Exception:
            pass
    return rows


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def json_response(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urllib.parse.urlsplit(self.path).path == "/status":
            self.json_response(200, {"files": completed_files()})
            return
        body = PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            parsed = urllib.parse.urlsplit(self.path)
            if parsed.path != "/upload":
                raise ValueError("上传地址无效")
            query = urllib.parse.parse_qs(parsed.query)
            get = lambda key: query[key][0]
            uid = re.sub(r"[^A-Za-z0-9_-]", "", get("id"))
            filename = safe_name(get("name"))
            index, total = int(get("index")), int(get("total"))
            size, offset = int(get("size")), int(get("offset"))
            length = int(self.headers.get("Content-Length", "0"))
            if not uid or not (0 <= index < total <= 2000 and 0 < size <= MAX_SIZE):
                raise ValueError("文件或分块参数无效")
            if offset != index * CHUNK_SIZE or length != min(CHUNK_SIZE, size - offset):
                raise ValueError("分块位置或大小无效")
            partial = UPLOAD_DIR / f".{uid}.part"
            received_path = UPLOAD_DIR / f".{uid}.json"
            with partial.open("r+b" if partial.exists() else "w+b") as handle:
                handle.seek(offset)
                remaining = length
                while remaining:
                    block = self.rfile.read(min(remaining, 1024 * 1024))
                    if not block:
                        raise ValueError("上传连接提前中断")
                    handle.write(block)
                    remaining -= len(block)
            received = set(json.loads(received_path.read_text()) if received_path.exists() else [])
            received.add(index)
            received_path.write_text(json.dumps(sorted(received)), encoding="utf-8")
            done = len(received) == total and all(i in received for i in range(total))
            response = {"ok": True, "done": done}
            if done:
                if partial.stat().st_size != size:
                    raise ValueError("文件大小校验失败")
                target = UPLOAD_DIR / filename
                os.replace(partial, target)
                received_path.unlink(missing_ok=True)
                digest = file_hash(target)
                info = {"name": filename, "size": size, "sha256": digest}
                (UPLOAD_DIR / f"{filename}.upload.json").write_text(
                    json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                response.update(info)
                print(f"UPLOAD COMPLETE {filename} {size} {digest}", flush=True)
            self.json_response(200, response)
        except Exception as exc:
            self.json_response(400, {"error": str(exc)})


port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
