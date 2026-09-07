#!/usr/bin/env python3
"""Serve the finished movie + previews over HTTP with Range support (for the Arena live preview).

Endpoints:
  /                 player page (video switcher: full | preview | master | raw)
  /movie.mp4        delivery file (falls back to the raw 27-shot preview until the final render exists)
  /preview.mp4      30 s preview
  /master.mp4       full-res master (may not exist yet)
  /raw.mp4          27-shot concatenated preview (no VO / subtitles)
  /poster.jpg       poster frame (if present)
Usage: python3 ripper/play_server.py [port]
"""
import http.server
import os
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")

FULL = os.path.join(OUT, "白教堂的雾_开膛手杰克_1080x1920_交付版_v4.mp4")
MASTER = os.path.join(OUT, "ripper_whitechapel_fog_1080x1920.mp4")
PREVIEW = os.path.join(OUT, "preview_30s.mp4")
RAW = os.path.join(OUT, "_raw_27shots_1088x1920.mp4")
POSTER = os.path.join(OUT, "poster_frame.jpg")

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8003

PAGE = """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>白教堂的雾 · 开膛手杰克 · 预览</title>
<style>
 body{background:#0b0b0f;color:#e8e4da;font-family:system-ui,sans-serif;margin:0}
 .wrap{max-width:520px;margin:0 auto;padding:18px 14px 40px}
 h1{font-size:19px;margin:0 0 4px;letter-spacing:1px}
 .sub{color:#9a948a;font-size:12px;margin-bottom:14px}
 video{width:100%;background:#000;border-radius:10px;display:block}
 nav{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
 button{background:#20242c;color:#e8e4da;border:1px solid #3a3f4a;padding:8px 14px;border-radius:8px;cursor:pointer;font-size:13px}
 button.on{background:#7a1f1f;border-color:#a33}
 .dl{display:block;margin-top:10px;color:#c9a86a;font-size:13px;text-decoration:none}
 .note{color:#8b857b;font-size:12px;margin-top:14px;line-height:1.7}
</style></head><body><div class="wrap">
<h1>白教堂的雾 —— 开膛手杰克</h1>
<div class="sub" id="stat">1080×1920 竖屏 · 旁白+字幕成片（重建中…）</div>
<video id="v" controls playsinline preload="auto"></video>
<nav>
 <button data-src="movie.mp4"   data-n="完整成片（配音版）">完整成片</button>
 <button data-src="preview.mp4" data-n="30 秒预览">30s 预览</button>
 <button data-src="raw.mp4"     data-n="27 镜粗剪（无旁白）">27 镜粗剪</button>
 <button data-src="master.mp4"  data-n="母版">母版</button>
</nav>
<a class="dl" href="movie.mp4" download>⬇ 下载完整成片 (movie.mp4)</a>
<a class="dl" style="margin-top:4px" href="raw.mp4" download>⬇ 下载 27 镜粗剪 (raw.mp4)</a>
<div class="note">说明：渲染完成后 /movie.mp4 会自动切换到最终配音版；当前如尚不存在则提供 27 镜粗剪。</div>
</div>
<script>
const v=document.getElementById('v'),stat=document.getElementById('stat');
const params=new URLSearchParams(location.search);
let cur=params.get('v')||'movie.mp4';
function set(src,n){
  v.src=src+'?t='+Date.now();v.play().catch(()=>{});stat.textContent=n;
  document.querySelectorAll('button').forEach(b=>b.classList.toggle('on',b.dataset.src===src));
}
document.querySelectorAll('button').forEach(b=>b.onclick=()=>set(b.dataset.src,b.dataset.n));
const first={movie.mp4:'完整成片（旁白+字幕）',preview.mp4:'30 秒预览',raw.mp4:'27 镜粗剪（无旁白/字幕）',master.mp4:'母版'}[cur]||cur;
set(cur,first);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self._serve(head_only=True)

    def do_GET(self):
        self._serve(head_only=False)

    def _target(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", ""):
            return None, "text/html; charset=utf-8"
        table = {
            "/movie.mp4": (FULL if os.path.exists(FULL) else RAW),
            "/preview.mp4": (PREVIEW if os.path.exists(PREVIEW) else RAW),
            "/master.mp4": (MASTER if os.path.exists(MASTER) else RAW),
            "/raw.mp4": RAW,
            "/poster.jpg": POSTER if os.path.exists(POSTER) else RAW,
        }
        if path in table:
            p = table[path]
            if p and os.path.exists(p):
                return p, "video/mp4" if p.endswith((".mp4", ".mp4")) else "image/jpeg"
        return None, "text/plain; charset=utf-8"

    def _serve(self, head_only=False):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", ""):
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return
        target, ctype = self._target()
        if target is None:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        size = os.path.getsize(target)
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        status = 200
        if rng and rng.startswith("bytes="):
            try:
                spec = rng[6:].split(",")[0].strip()
                s, e = spec.split("-", 1)
                start = int(s) if s else 0
                end = int(e) if e else size - 1
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                end = min(end, size - 1)
                status = 206
            except Exception:
                pass
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if head_only:
            return
        with open(target, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                self.wfile.write(chunk)
                left -= len(chunk)

    def log_message(self, fmt, *args):
        sys.stdout.write("[play] %s\n" % (fmt % args))
        sys.stdout.flush()


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"serving {OUT} on :{PORT}", flush=True)
    srv.serve_forever()
