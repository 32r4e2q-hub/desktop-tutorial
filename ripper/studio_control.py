#!/usr/bin/env python3
"""一键控制台：触发 Agnes 片段生成 + 实时状态。浏览器打开即是一个大按钮。"""
from __future__ import annotations

import json
import subprocess
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = "32r4e2q-hub/desktop-tutorial"
BRANCH = "arena/01a07943-desktop-tutorial"
CLIPS_DIR = Path(__file__).resolve().parent / "clips"

PAGE = r'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>开膛手杰克 · Agnes 生成控制台</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 20% 0,#1d2942,#080c15 52%,#04060b);color:#f3f6ff;font:15px/1.65 system-ui,"Microsoft YaHei"}
main{width:min(760px,92vw);padding:32px;background:#141b2bf5;border:1px solid #35435f;border-radius:20px;box-shadow:0 24px 80px #0009}
h1{margin:0 0 6px;font-size:22px}.lead,.desc{color:#aebbd1;margin:6px 0}
.bigbtn{width:100%;padding:22px;margin:20px 0 12px;border:0;border-radius:14px;background:linear-gradient(90deg,#5d87f7,#74c7ff);color:#fff;font-size:19px;font-weight:800;cursor:pointer;transition:.2s}
.bigbtn:hover{filter:brightness(1.1)}.bigbtn:disabled{opacity:.45;cursor:wait}
.status{padding:14px;background:#101724;border-radius:12px;margin-bottom:10px;min-height:90px;white-space:pre-wrap;font:13px/1.6 ui-monospace,Consolas,monospace}
.ok{color:#50dda0}.warn{color:#ffd36e}.err{color:#ff8181}
.steps{background:#202a40;border-left:4px solid #7199ff;border-radius:9px;padding:12px 15px;margin-top:14px;font-size:13px;color:#c9d4ea}
a{color:#8fb4ff}
</style></head><body><main>
<h1>▍开膛手杰克 · Agnes 动画生成控制台</h1>
<p class=lead>27 个镜头 · 1080×1920 · 统一电影风格 · 一键生成后自动推回制作分支</p>
<button class=bigbtn id=go>▶ 开始生成（Agnes Video V2.0）</button>
<div class=status id=s>正在读取状态…</div>
<div class=steps>
<b>说明：</b>点击按钮后，GitHub Actions 会逐个生成 27 个 6 秒 AI 动画片段（每个约 30–90 秒），
完成后自动提交到分支 <code>arena/01a07943-desktop-tutorial</code>。
页面会每 8 秒自动刷新进度；生成完成后我再进行拼装、配音、字幕和成片输出。
</div>
</main>
<script>
const s=document.querySelector('#s'),go=document.querySelector('#go');
async function get(j){try{let r=await fetch('/status');return await r.json()}catch(e){return null}}
async function refresh(){let st=await get();if(!st){s.className='status err';s.textContent='控制台连接断开';return}
  s.className='status '+(st.kind||'');s.textContent=st.text}
async function start(){go.disabled=true;s.className='status warn';s.textContent='正在向 GitHub 发送触发指令…';
  try{let r=await fetch('/trigger',{method:'POST'});let j=await r.json();
    if(!r.ok)throw Error(j.error);s.className='status ok';
    s.textContent='✅ 已触发！GitHub Actions 正在启动…\n'+j.summary}catch(e){s.className='status err';s.textContent='触发失败：'+e.message;go.disabled=false}
  setTimeout(refresh,4000)}
go.onclick=start;refresh();setInterval(refresh,8000);
</script></body></html>'''


def run_gh(*args: str) -> str:
    return subprocess.run(["gh", *args], cwd="/home/user/desktop-tutorial",
                          capture_output=True, text=True, timeout=120).stdout


def status_payload() -> dict:
    # 最新 run
    runs = []
    try:
        for line in run_gh("run", "list", "-w", "ai-shots.yml", "-L", "3", "--json", "databaseId,status,conclusion,displayTitle,event,createdAt").splitlines():
            pass
        import json as _j
        runs = _j.loads(run_gh("run", "list", "-w", "ai-shots.yml", "-L", "3",
                               "--json", "databaseId,status,conclusion,displayTitle,event,createdAt"))
    except Exception:
        runs = []
    running = next((r for r in runs if r.get("status") in ("queued", "in_progress")), None)
    if running:
        return {"kind": "warn", "text": f"⏳ 生成进行中（run #{running['databaseId']}，{running['status']}）\n等待完成…（单个镜头约 30–90 秒，27 镜约 20–40 分钟）"}
    # 检查片段
    clips = sorted(CLIPS_DIR.glob("S*.mp4")) if CLIPS_DIR.exists() else []
    if clips:
        return {"kind": "ok", "text": f"✅ 已完成 {len(clips)} 个片段（目标 27）\n最近：{clips[-1].name}\n等待全部完成后开始拼装"}
    last = runs[0] if runs else None
    if last:
        return {"kind": "", "text": f"上次运行 #{last['databaseId']}：{last.get('conclusion') or last.get('status')}\n本机片段：0 个。点击按钮开始生成。"}
    return {"kind": "", "text": "尚无运行记录。点击按钮开始生成。"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def send_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/status":
            self.send_json(200, status_payload())
            return
        body = PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/trigger":
            self.send_json(404, {"error": "not found"})
            return
        try:
            payload = '{"only":"","force":"false"}'
            req = urllib.request.Request(
                f"https://api.github.com/repos/{REPO}/dispatches",
                data=json.dumps({"event_type": "ai-shots", "client_payload": json.loads(payload)}).encode(),
                headers={"Authorization": "token " + __import__("os").environ.get("GH_TOKEN", ""),
                         "Accept": "application/vnd.github+json", "User-Agent": "studio-control"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status != 204:
                    raise RuntimeError(f"GitHub 返回 {resp.status}")
            self.send_json(200, {"ok": True, "summary": "事件 ai-shots 已发送到 GitHub，Actions 即将开始。"})
        except Exception as exc:
            self.send_json(400, {"error": str(exc)})


port = int(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else 8001
ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
