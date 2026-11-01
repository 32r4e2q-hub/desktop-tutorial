#!/usr/bin/env python3
"""Serve only the cover editor and its two downloadable deliverables."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import os,shutil

HERE=Path(__file__).resolve().parent
FILES={
    '/':('封面模板_可编辑.html','text/html; charset=utf-8',None),
    '/template.zip':('迷案解码人_封面模板.zip','application/zip','mystery-cover-template.zip'),
    '/cover.png':('第一期_西口彰_封面.png','image/png','episode-01-cover.png'),
}
class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self): self.respond(False)
    def do_GET(self): self.respond(True)
    def respond(self,body):
        item=FILES.get(urlsplit(self.path).path)
        if item is None: self.send_error(404); return
        name,mime,download=item;path=HERE/name
        if not path.is_file(): self.send_error(404); return
        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(path.stat().st_size));self.send_header('X-Content-Type-Options','nosniff')
        if download:self.send_header('Content-Disposition',f'attachment; filename="{download}"')
        self.end_headers()
        if body:
            try:
                with path.open('rb') as f: shutil.copyfileobj(f,self.wfile,1024*1024)
            except (BrokenPipeError,ConnectionResetError):pass

if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','8766'))),Handler).serve_forever()
