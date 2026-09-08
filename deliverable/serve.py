#!/usr/bin/env python3
"""Serve the 《白教堂的雾》 delivery package over HTTP with byte-Range support.

Serves this directory and its subdirectories (path-safe: `..` is rejected), so the whole package can be
fetched with curl/wget or played in the browser:

  /                     index: 版本说明 + 每个文件的大小/校验值 + 下载链接
  /movie.mp4            v4.2 交付档（CRF24 · 100.2 MB · 3:16.67 · faststart，可边下边播）
  /preview.mp4          v4.2 30 s 预览
  /poster.jpg           v4.2 海报帧（片名卡 t=15.5s）
  /subtitles.srt        v4.2 字幕（47 条）
  /v4_2/parts/movie.part-00N   入库分片（复原：cat movie.part-* > out.mp4）
  /v4_1/...                     v4.1 那批小文件（若存在）

Usage: python3 deliverable/serve.py [port]      # default 8017
"""
import html
import http.server
import json
import os
import socketserver
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8017

ALIASES = {
    "/movie.mp4": "v4_2/ripper_whitechapel_fog_v4_2_crf24_1080x1920.mp4",
    "/preview.mp4": "v4_2/preview_30s_v4_2.mp4",
    "/poster.jpg": "v4_2/poster_v4_2.jpg",
    "/subtitles.srt": "v4_2/subtitles.srt",
    "/qc.json": "v4_2/qc_report.json",
    "/manifest.json": "v4_2/parts/manifest.json",
    "/v41.mp4": "ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4",
}
TYPES = {
    ".mp4": "video/mp4", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".srt": "application/x-subrip; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8", ".txt": "text/plain; charset=utf-8",
    ".py": "text/plain; charset=utf-8", ".html": "text/html; charset=utf-8",
}

# (display label, relative path, note)
PACKAGE = [
    ("v4.2 交付档 CRF24（100.2 MB，整档只在本地/分片入库）", "v4_2/ripper_whitechapel_fog_v4_2_crf24_1080x1920.mp4", "3:16.67 · 4720 帧 · f723581d…5902"),
    ("v4.2 入库分片 1/3", "v4_2/parts/movie.part-000", "45,000,000 B"),
    ("v4.2 入库分片 2/3", "v4_2/parts/movie.part-001", "45,000,000 B"),
    ("v4.2 入库分片 3/3", "v4_2/parts/movie.part-002", "10,216,657 B"),
    ("v4.2 分片清单（整档 sha256 + 复原命令）", "v4_2/parts/manifest.json", "cat movie.part-* > out.mp4"),
    ("v4.2 30s 预览", "v4_2/preview_30s_v4_2.mp4", "0–30s · 雾街→片名卡→钩子"),
    ("v4.2 海报帧 / 封面", "v4_2/poster_v4_2.jpg", "1080×1920 · t=15.5s"),
    ("v4.2 字幕（47 条）", "v4_2/subtitles.srt", "按旁白实测停顿"),
    ("v4.2 时间线（27 镜入出点）", "v4_2/timeline.json", ""),
    ("v4.2 QC 报告", "v4_2/qc_report.json", "passed: true"),
    ("v4.2 交付清单", "v4_2/final_manifest.json", ""),
    ("v4.2 包说明", "v4_2/README.md", ""),
    ("v4.1 成片（上一会话入库版，87.6 MB）", "ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4", "ABR 3500k · 03d838cc…88d6"),
    ("v4.1 30s 预览 / 海报帧", "preview_30s.mp4", ""),
    ("整包交付说明（含两版关系）", "DELIVERY.md", ""),
    ("校验值汇总", "v4_2/SHA256SUMS.txt", ""),
]


def human(n):
    return f"{n / 1048576:.1f} MB" if n > 400000 else f"{n / 1024:.0f} KB"


def page():
    rows = []
    for label, rel, note in PACKAGE:
        full = os.path.join(HERE, rel)
        if not os.path.isfile(full):
            continue
        rows.append(f'<a class="dl" href="/{rel}"><b>{html.escape(label)}</b>'
                    f'<span>{human(os.path.getsize(full))}{(" · " + html.escape(note)) if note else ""}</span></a>')
    listing = "".join(rows) or '<div class="note">（本地未找到文件）</div>'
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>白教堂的雾 · 开膛手杰克 · 交付包 v4.2</title>
<style>
 body{{background:#0b0b0f;color:#e8e4da;font-family:system-ui,-apple-system,sans-serif;margin:0}}
 .wrap{{max-width:560px;margin:0 auto;padding:18px 14px 48px}}
 h1{{font-size:19px;margin:0 0 4px;letter-spacing:1px}}
 .sub{{color:#9a948a;font-size:12px;margin-bottom:14px;line-height:1.7}}
 video{{width:100%;background:#000;border-radius:10px;display:block}}
 nav{{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}}
 button{{background:#20242c;color:#e8e4da;border:1px solid #3a3f4a;padding:8px 14px;
   border-radius:8px;cursor:pointer;font-size:13px}}
 button.on{{background:#7a1f1f;border-color:#a33}}
 .dl{{display:flex;justify-content:space-between;gap:12px;margin-top:7px;color:#c9a86a;
   font-size:13px;text-decoration:none;border-bottom:1px solid #1e222a;padding-bottom:7px}}
 .dl span{{color:#8b857b;white-space:nowrap}}
 .note{{color:#8b857b;font-size:12px;margin-top:16px;line-height:1.8}}
 code{{background:#171a21;padding:1px 5px;border-radius:4px;font-size:12px}}
</style></head><body><div class="wrap">
<h1>白教堂的雾 —— 开膛手杰克</h1>
<div class="sub"><b>v4.2 CRF24 交付档</b> · 1080×1920 · 24 fps · 3:16.67 · 4720 帧 · 27 镜 ·
H.264 CRF24 medium High@4.1 + AAC 160k · <code>moov</code> 前置（可流式播放）·
100,216,657 B · SHA-256 <code>f723581d…5902</code><br>
入库形式：<code>parts/movie.part-000…002</code> + <code>manifest.json</code>；
复原：<code>cat movie.part-* &gt; out.mp4</code>（实测逐字节一致）。</div>
<video id="v" controls playsinline preload="metadata" src="/preview.mp4"></video>
<nav>
 <button data-src="/preview.mp4" class="on">30s 预览</button>
 <button data-src="/movie.mp4">完整成片 v4.2</button>
 <button data-src="/v41.mp4">v4.1 对照</button>
</nav>
<h3 style="font-size:13px;color:#9a948a;margin:20px 0 6px;font-weight:600">文件</h3>
{listing}
<div class="note">链接只在本次沙箱存活期间有效；文件本体在 Git（分片 + 校验值），见 <code>DELIVERY.md</code>。</div>
</div><script>
const v=document.getElementById('v');
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{{
  v.src=b.dataset.src+'?t='+Date.now(); v.load(); v.play().catch(()=>{{}});
  document.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));
}});
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_HEAD(self):
        self._serve(True)

    def do_GET(self):
        self._serve(False)

    def _resolve(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            return None, "text/html; charset=utf-8"
        rel = ALIASES.get(path) or urllib.parse.unquote(path.lstrip("/"))
        if ".." in rel or rel.startswith("/"):
            return None, None
        full = os.path.normpath(os.path.join(HERE, rel))
        if not full.startswith(HERE) or not os.path.isfile(full):
            return None, None
        return full, TYPES.get(os.path.splitext(full)[1].lower(), "application/octet-stream")

    def _serve(self, head_only):
        target, ctype = self._resolve()
        if target is None:
            if ctype is None:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body = page().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return

        size = os.path.getsize(target)
        start, end, status = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            try:
                spec = rng[6:].split(",")[0].strip()
                s, e = spec.split("-", 1)
                start = max(0, size - int(e)) if s == "" and e.isdigit() else int(s or 0)
                if s and e:
                    end = int(e)
                if start >= size or start > end:
                    raise ValueError
                end = min(end, size - 1)
                status = 206
            except Exception:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-cache")
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if head_only:
            return
        with open(target, "rb") as f:
            f.seek(start)
            left = length
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    def log_message(self, fmt, *args):
        sys.stdout.write("[deliver] " + (fmt % args) + "\n")
        sys.stdout.flush()


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print(f"serving {HERE} (recursive) on 0.0.0.0:{PORT}", flush=True)
    Server(("0.0.0.0", PORT), Handler).serve_forever()
