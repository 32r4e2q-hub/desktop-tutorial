#!/usr/bin/env python3
"""Serve the 《白教堂的雾》 delivery package over HTTP with byte-Range support.

Endpoints (aliases, plus direct access to every file in this directory):
  /                  player page with 完整成片 / 30s 预览 / 海报帧 + 下载按钮
  /movie.mp4         完整成片 1080x1920 · 3:12.29 · H.264 High@4.1 + AAC · faststart
  /preview.mp4       30 秒预览（片头段落，含旁白与字幕）
  /poster.jpg        海报帧 / 封面（片名字卡 t=7.0s）
  /poster_alt.jpg    备选封面（结尾 “他是谁？” t=188.0s）
  /subtitles.srt     字幕文件（47 条）
Usage: python3 deliverable/serve.py [port]     # default 8017
"""
import html
import http.server
import os
import socketserver
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8017

ALIASES = {
    "/movie.mp4": "ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4",
    "/preview.mp4": "preview_30s.mp4",
    "/poster.jpg": "poster_frame.jpg",
    "/poster_alt.jpg": "poster_alt_ending.jpg",
}
TYPES = {
    ".mp4": "video/mp4", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".srt": "application/x-subrip; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".md": "text/markdown; charset=utf-8", ".html": "text/html; charset=utf-8",
}

_rows = []
for name in ["ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4", "preview_30s.mp4",
             "poster_frame.jpg", "poster_alt_ending.jpg", "preview_sheet.jpg",
             "subtitles.srt", "timeline.json", "qc_report.json", "final_manifest.json"]:
    path = os.path.join(HERE, name)
    if os.path.exists(path):
        _rows.append((name, os.path.getsize(path)))


def page():
    def size(n):
        return f"{n/1048576:.1f} MB" if n > 400000 else f"{n/1024:.0f} KB"
    links = "".join(
        f'<a class="dl" href="/{html.escape(n)}" download>⬇ {html.escape(n)}'
        f'<span>{size(s)}</span></a>' for n, s in _rows)
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>白教堂的雾 · 开膛手杰克 · 交付包</title>
<style>
 body{{background:#0b0b0f;color:#e8e4da;font-family:system-ui,-apple-system,sans-serif;margin:0}}
 .wrap{{max-width:540px;margin:0 auto;padding:18px 14px 44px}}
 h1{{font-size:19px;margin:0 0 4px;letter-spacing:1px}}
 .sub{{color:#9a948a;font-size:12px;margin-bottom:14px;line-height:1.6}}
 video{{width:100%;background:#000;border-radius:10px;display:block}}
 nav{{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}}
 button{{background:#20242c;color:#e8e4da;border:1px solid #3a3f4a;padding:8px 14px;
   border-radius:8px;cursor:pointer;font-size:13px}}
 button.on{{background:#7a1f1f;border-color:#a33}}
 .dl{{display:flex;justify-content:space-between;gap:10px;margin-top:6px;color:#c9a86a;
   font-size:13px;text-decoration:none;border-bottom:1px solid #1e222a;padding-bottom:6px}}
 .dl span{{color:#8b857b}}
 .note{{color:#8b857b;font-size:12px;margin-top:16px;line-height:1.8}}
 img{{width:100%;border-radius:10px;margin-top:10px}}
</style></head><body><div class="wrap">
<h1>白教堂的雾 —— 开膛手杰克</h1>
<div class="sub">最终交付 v4.1（保存素材重导出）· 1080×1920 · 24 fps · 3:12.29 · 4615 帧 ·
H.264 High 4.1 + AAC 160k · moov 前置（faststart，可边下边播）· 87,559,177 字节 ·
SHA-256 03d838cc…88d6</div>
<video id="v" controls playsinline preload="metadata" src="/preview.mp4"></video>
<nav>
 <button data-src="/preview.mp4" class="on">30s 预览</button>
 <button data-src="/movie.mp4">完整成片</button>
</nav>
<div style="margin-top:16px">
{links}
</div>
<div class="note">链接只在本次沙箱存活期间有效；文件本体已保存在 Git 中（见 DELIVERY.md 的固定地址与校验值）。</div>
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
        name = ALIASES.get(path, os.path.basename(path))
        full = os.path.join(HERE, name)
        if not os.path.isfile(full):
            return None, None
        return full, TYPES.get(os.path.splitext(name)[1].lower(), "application/octet-stream")

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
                first = rng[6:].split(",")[0].strip()
                s, e = first.split("-", 1)
                if s == "" and e.isdigit():          # suffix range: last N bytes
                    start = max(0, size - int(e))
                else:
                    start = int(s or 0)
                if e and s:
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
    print(f"serving {HERE} on 0.0.0.0:{PORT}", flush=True)
    Server(("0.0.0.0", PORT), Handler).serve_forever()
