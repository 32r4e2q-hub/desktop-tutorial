#!/usr/bin/env python3
"""成片预览/交付服务器：把 MP4 挂到沙箱预览地址上，在线播 + 下载二合一。

为什么不用 `python -m http.server`：它不支持 Range 请求，浏览器播 MP4 时
不能拖进度条（seek 会静默失败），手机端体验尤其差。这个脚本只用标准库，
实现单区间 Range（206 + Content-Range），seek/边下边播都正常。

典型用法（在 Arena 沙箱里，后台常驻）：

    python3 production/serve_film.py --film 交付/DB库珀劫机案_三分钟_带声音.mp4

脚本会：① 检查 moov 是否在前（不在且有 ffmpeg 就重排，多花几十秒，
没有 ffmpeg 则告警）；② 生成带 <video> 播放器 + 下载按钮的 index.html；
③ 打印预览地址：https://{port}-{E2B_SANDBOX_ID}.e2b.app/

这条链路是 2026-09-14 吃亏吃出来的：私有仓库的 raw/codeload 下载在用户
那边全灭（登录态、跨站、可点性轮着坏），最后靠预览服务器一次交付成功。
手册见《电影解说剪辑制作手册》"成片交付"那一节。
"""
from __future__ import annotations

import argparse
import functools
import html
import mimetypes
import os
import re
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def moov_first(path: Path) -> bool:
    """读顶层 box 头，判断 moov 是否排在 mdat 前面（浏览器边下边播的前提）。"""
    with path.open("rb") as fh:
        while True:
            head = fh.read(8)
            if len(head) < 8:
                return False
            size = int.from_bytes(head[:4], "big")
            kind = head[4:]
            if kind == b"moov":
                return True
            if kind == b"mdat":
                return False
            fh.seek(max(size, 8) - 8, os.SEEK_CUR)


def ensure_streamable(src: Path, dst: Path) -> Path:
    """保证交付文件可流式播放：moov 在前就直接符号链接，否则 ffmpeg 重排。"""
    if moov_first(src):
        print(f"[serve] moov 在前，无需重排：{src.name}")
        if dst.is_symlink() or dst.exists():
            dst.unlink()
        dst.symlink_to(src.resolve())
        return dst
    print("[serve] moov 在 mdat 之后，浏览器会等全量下载才播——尝试 ffmpeg 重排…")
    if not shutil.which("ffmpeg"):
        print("[serve] 警告：没有 ffmpeg，只能原样链接，手机端可能要等很久",
              file=sys.stderr)
        if dst.is_symlink() or dst.exists():
            dst.unlink()
        dst.symlink_to(src.resolve())
        return dst
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y",
                    "-i", str(src), "-c", "copy", "-movflags", "+faststart",
                    str(dst)], check=True)
    print(f"[serve] 重排完成：{dst}（原片不动）")
    return dst


INDEX_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title></head>
<body style="font-family:sans-serif;max-width:960px;margin:24px auto;padding:0 12px;background:#111;color:#eee">
<h2>{title}</h2>
<p>{desc}</p>
<video src="{file}" controls preload="metadata" playsinline style="width:100%;background:#000"></video>
<p><a style="color:#7df" href="{file}" download="{file}">&#11015; 下载 MP4（{mb} MB）</a></p>
<p style="color:#888;font-size:13px">播放在线 progressive；点下载拿完整文件。</p>
</body></html>
"""


def write_index(serve_dir: Path, serve_name: str, title: str, desc: str,
                size_mb: float) -> None:
    (serve_dir / "index.html").write_text(INDEX_TEMPLATE.format(
        title=html.escape(title), desc=html.escape(desc),
        file=html.escape(serve_name), mb=f"{size_mb:.1f}"), encoding="utf-8")


class RangeHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler + 单区间 Range（206），只够视频用，不求全。"""
    protocol_version = "HTTP/1.1"

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        if not os.path.isfile(path):
            self.send_error(404, "File not found")
            return None
        ctype, _ = mimetypes.guess_type(path)
        size = os.path.getsize(path)
        fh = open(path, "rb")
        start, end = 0, size - 1
        status = 200
        byte_range = self.headers.get("Range")
        if byte_range:
            m = re.match(r"bytes=(\d*)-(\d*)$", byte_range.strip())
            if m:
                s, e = m.groups()
                if s:
                    start = int(s)
                    end = int(e) if e else size - 1
                elif e:  # 后缀区间：最后 N 字节
                    start = max(size - int(e), 0)
                if start >= size:
                    self.send_error(416, "Requested Range Not Satisfiable")
                    fh.close()
                    return None
                end = min(end, size - 1)
                status = 206
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        if status == 206:
            self.send_header("Content-Range",
                             f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        fh.seek(start)
        self.range_left = length
        self.range_fh = fh
        return fh

    def copyfile(self, source, outputfile):
        left = getattr(self, "range_left", None)
        if left is None:  # 目录页等非文件响应，走默认拷贝
            return super().copyfile(source, outputfile)
        try:
            while left > 0:
                chunk = source.read(min(1 << 20, left))
                if not chunk:
                    break
                outputfile.write(chunk)
                left -= len(chunk)
        finally:
            source.close()
            del self.range_left
            del self.range_fh

    def log_message(self, *args):  # 打到 stdout，start_process 能看到访问记录
        sys.stdout.write("%s - %s\n" % (self.address_string(),
                                        args[0] % tuple(args[1:])))
        sys.stdout.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--film", required=True, help="成片 MP4 路径")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--name", default="",
                    help="对外文件名（默认原名去 CJK 风险：ASCII 化）")
    ap.add_argument("--title", default="成片预览")
    ap.add_argument("--desc", default="")
    ap.add_argument("--dir", default="/tmp/serve-film",
                    help="服务目录（放链接/重排副本 + index.html）")
    args = ap.parse_args()

    src = Path(args.film).resolve()
    if not src.is_file():
        print(f"[serve] 找不到成片：{src}", file=sys.stderr)
        return 2
    serve_dir = Path(args.dir)
    serve_dir.mkdir(parents=True, exist_ok=True)
    serve_name = args.name or src.name
    served = ensure_streamable(src, serve_dir / serve_name)
    write_index(serve_dir, serve_name, args.title, args.desc,
                served.stat().st_size / 1e6)

    box = os.environ.get("E2B_SANDBOX_ID", "")
    print(f"[serve] 本地：http://127.0.0.1:{args.port}/")
    if box:
        print(f"[serve] 预览：https://{args.port}-{box}.e2b.app/")
    else:
        print("[serve] 非沙箱环境：只有本机能访问", file=sys.stderr)
    handler = functools.partial(RangeHandler, directory=str(serve_dir))
    server = ThreadingHTTPServer(("0.0.0.0", args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
