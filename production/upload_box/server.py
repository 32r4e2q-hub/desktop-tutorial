#!/usr/bin/env python3
"""上传台：一个网页拖放区，文件直接落到仓库的 incoming_uploads/。

为什么要它：Agent 没有"聊天窗口外的附件口袋"，但沙箱里可以起一个真的 HTTP 服务，
浏览器（含手机）通过预览域名把文件 POST 进来 → 落到工作区 → Agent 立刻能读。

    python3 production/upload_box/server.py            # 默认 0.0.0.0:8765
    python3 production/upload_box/server.py --port 9000 --no-browser

路由：
    GET  /                 拖放页（手机端也可用，点按钮选文件）
    GET  /files            已收到文件的 JSON 清单（页面每 3 秒轮询）
    POST /upload           multipart 上传，存盘 + 自动把 docx/xlsx 表格解析成 md
    POST /note             追加一条文字补充要求到 notes.md
    POST /delete           删掉某个投递文件（含它的解析结果）
    GET  /view/<name>      看解析出来的 Markdown
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # 允许从仓库根目录之外的地方启动
ROOT = HERE.parent.parent
# 投递口目录：默认仓库根的 incoming_uploads/（已在 .gitignore 里）；
# 环境变量 UPLOAD_INBOX 可换（测试用临时目录，不污染真实投递口）。
INBOX = Path(os.environ.get("UPLOAD_INBOX") or (ROOT / "incoming_uploads"))
EXTRACTED = INBOX / "parsed"
MAX_BYTES = 80 * 1024 * 1024
ALLOWED = {
    ".docx", ".doc", ".docm", ".xlsx", ".xls", ".xlsm", ".csv", ".txt", ".md", ".markdown",
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".srt", ".json", ".zip",
}

import extract_tables  # noqa: E402  (同目录)


def use_inbox(path: str | Path) -> Path:
    """换投递口目录（测试用）。返回新目录。"""
    global INBOX, EXTRACTED
    INBOX = Path(path)
    EXTRACTED = INBOX / "parsed"
    return INBOX


SAFE = re.compile(r"[^\w.\-一-鿿]+")


def safe_name(name: str) -> str:
    name = Path(unquote(name or "")).name.replace("\x00", "")
    name = SAFE.sub("_", name).strip("._") or "file"
    return name[:120]


def unique(target: Path) -> Path:
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    for i in range(1, 1000):
        cand = target.with_name(f"{stem}-{i}{suffix}")
        if not cand.exists():
            return cand
    raise RuntimeError("重名文件太多了")


def inside_inbox(p: Path) -> Path:
    rp = p.resolve()
    if INBOX.resolve() not in rp.parents and rp != INBOX.resolve():
        raise PermissionError("只允许操作 incoming_uploads/ 里的文件")
    return rp


def log_line(text: str) -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    with (INBOX / "events.log").open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {text}\n")


def inbox_listing() -> list[dict]:
    out = []
    if not INBOX.exists():
        return out
    for p in sorted(INBOX.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file() or p.name in {"events.log", "notes.md"}:
            continue
        item = {
            "name": p.name,
            "size": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime).strftime("%m-%d %H:%M:%S"),
            "ext": p.suffix.lower(),
            "view": None,
            "note": "",
        }
        md = EXTRACTED / (p.stem + ".md")
        meta = EXTRACTED / (p.stem + ".json")
        if meta.exists():
            try:
                info = json.loads(meta.read_text(encoding="utf-8"))
            except Exception:
                info = {}
            if info.get("error"):
                item["note"] = "⚠ " + info["error"]
            elif info.get("n_tables"):
                item["note"] = f"✓ 已解析出 {info['n_tables']} 个表格 / {info.get('n_rows', 0)} 行"
            elif info.get("markdown"):
                item["note"] = "✓ 已解析成正文"
        if md.exists():
            item["view"] = f"/view/{p.stem}"
        out.append(item)
    return out


def process(saved: Path) -> dict:
    """存盘后马上解析，让 Agent 和你都能直接看文字版。"""
    res = extract_tables.extract(saved)
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    (EXTRACTED / (saved.stem + ".json")).write_text(
        json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if res["markdown"]:
        (EXTRACTED / (saved.stem + ".md")).write_text(res["markdown"], encoding="utf-8")
    log_line(
        f"收到 {saved.name}（{saved.stat().st_size} 字节）→ "
        + (f"解析失败：{res['error']}" if res["error"] else "已解析")
    )
    return res


# --------------------------------------------------------------------------- 页面

PAGE = """<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>投递台 · 把 Word 表格扔进来</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#101418;color:#e8ecf1;font:16px/1.6 -apple-system,"PingFang SC","Noto Sans CJK SC",sans-serif;
 display:flex;flex-direction:column;min-height:100vh}
main{max-width:760px;width:100%;margin:0 auto;padding:22px 18px 60px}
h1{font-size:21px;margin:0 0 4px}
.sub{color:#96a3b2;font-size:14px;margin:0 0 18px}
#drop{border:2px dashed #3d5570;border-radius:16px;padding:34px 18px;text-align:center;
 background:#161d26;transition:.15s;cursor:pointer}
#drop.hot{border-color:#4cc2ff;background:#132533;transform:scale(1.01)}
#drop b{display:block;font-size:18px;margin-bottom:6px}
#drop span{color:#96a3b2;font-size:13px}
input[type=file]{display:none}
.btn{display:inline-block;margin-top:14px;background:#2b7bff;border:0;color:#fff;border-radius:10px;
 padding:11px 20px;font-size:15px;font-weight:600;cursor:pointer}
.bar{height:6px;background:#233042;border-radius:99px;overflow:hidden;margin-top:14px;display:none}
.bar i{display:block;height:100%;width:0;background:#4cc2ff;transition:.2s}
h2{font-size:14px;color:#96a3b2;font-weight:600;margin:26px 0 8px;text-transform:uppercase;letter-spacing:.06em}
ul{list-style:none;padding:0;margin:0}
li{background:#161d26;border:1px solid #232f3d;border-radius:12px;padding:11px 13px;margin-bottom:9px;
 display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:14px}
li em{color:#7de0a0;font-style:normal;font-size:13px}
li .bad{color:#ffb457}
li a{color:#79b8ff;text-decoration:none;font-size:13px}
li .del{margin-left:auto;color:#7d8896;cursor:pointer;font-size:13px}
li .size{color:#6d7a89;font-size:12px}
textarea{width:100%;background:#161d26;color:#e8ecf1;border:1px solid #232f3d;border-radius:12px;
 padding:11px;font:inherit;font-size:14px;min-height:70px;resize:vertical}
.tip{color:#8a97a6;font-size:13px;margin-top:8px}
.tip code{background:#1c2530;padding:1px 5px;border-radius:5px}
.done{background:#132b20;border:1px solid #2f6b47;color:#a8e6c1;padding:10px 13px;border-radius:12px;
 margin-bottom:14px;display:none;font-size:14px}
.done.show{display:block}
</style></head><body><main>
<div class="done" id="done"></div>
<h1>投递台 · 视频要求收这里</h1>
<p class="sub">Word 表格拖进来就行，我这边收到会自动解析成正文，立刻能开工。</p>
<div id="drop">
  <b>把文件拖到这里 / 点这里选文件</b>
  <span>支持 .docx .xlsx .txt .md .pdf 和图片（.doc / .xls 老格式请先另存为新格式）</span>
  <input type="file" id="f" multiple>
</div>
<div class="bar" id="bar"><i id="bari"></i></div>
<button class="btn" id="pick">选择文件上传</button>

<h2>补充要求（可留空，写一条也行）</h2>
<textarea id="note" placeholder="例：竖版 9:16、时长 3 分钟、标题要三个备选、结尾留悬念……"></textarea>
<button class="btn" id="savenote" style="background:#2f3b4a">保存这条补充</button>

<h2>已收到 <span id="n">0</span></h2>
<ul id="list"></ul>
<p class="tip">表格里如果写了题目 / 时长 / 分镜要求，我会照 <code>production/new_topic.py</code> 开新项目，
再走脚本 → 配音 → 镜头 → 出片那条流水线。<br>
不方便用网页？直接在聊天里把文件发我也一样。</p>
</main>
<script>
const drop=document.getElementById('drop'),fi=document.getElementById('f'),bar=document.getElementById('bar'),
bari=document.getElementById('bari'),list=document.getElementById('list'),n=document.getElementById('n'),
done=document.getElementById('done');
pick.onclick=()=>fi.click();drop.onclick=()=>fi.click();
['dragenter','dragover'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.add('hot')}));
['dragleave','drop'].forEach(e=>drop.addEventListener(e,ev=>{ev.preventDefault();drop.classList.remove('hot')}));
drop.addEventListener('drop',ev=>send(ev.dataTransfer.files));
fi.addEventListener('change',()=>{send(fi.files);fi.value=''});
function send(files){
  if(!files.length)return;
  const fd=new FormData();for(const f of files)fd.append('file',f,f.name);
  const x=new XMLHttpRequest();x.open('POST','/upload');
  bar.style.display='block';
  x.upload.onprogress=e=>{if(e.lengthComputable)bari.style.width=(e.loaded/e.total*100)+'%'};
  x.onload=()=>{bar.style.display='none';bari.style.width='0';
    let r={};try{r=JSON.parse(x.responseText)}catch(_){}
    if(x.status<300){
      let msg=(r.names&&r.names.length)?('✓ 已收到 '+r.names.join('、')+(r.parsed?'（表格已解析成正文）':''))
        :'⚠ 这些文件我没收：'+((r.skipped||[]).join('；')||'请求里没有文件');
      if(r.skipped&&r.skipped.length)msg+='　｜　'+r.skipped.join('；');
      flash(msg,!(r.names&&r.names.length));refresh();}
    else flash('✗ '+(r.error||('HTTP '+x.status)),true);};
  x.onerror=()=>{bar.style.display='none';flash('✗ 上传失败，网络或大小限制问题；试试在聊天里直接发文件',true);};
  x.send(fd);
}
savenote.onclick=async()=>{const t=document.getElementById('note').value.trim();if(!t)return flash('先写点内容',true);
  const r=await fetch('/note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});
  if(r.ok){document.getElementById('note').value='';flash('✓ 补充要求已记到 notes.md');refresh();}};
function flash(t,bad){done.textContent=t;done.className='done show';done.style.borderColor=bad?'#7a4a2f':'';
  done.style.background=bad?'#2b1c13':'';done.style.color=bad?'#ffb457':'';setTimeout(()=>done.className='done',6000);}
async function refresh(){
  const r=await fetch('/files');const items=await r.json();n.textContent=items.length;
  list.innerHTML=items.map(it=>`<li><code>${it.name}</code>
    <span class="size">${(it.size/1024).toFixed(1)} KB · ${it.mtime}</span>
    ${it.note?`<em class="${it.note.startsWith('⚠')?'bad':''}">${it.note}</em>`:''}
    ${it.view?`<a href="${it.view}" target="_blank">看解析</a>`:''}
    <span class="del" data-n="${it.name}">删除</span></li>`).join('')||'<li style="color:#6d7a89">还没有文件</li>';
  list.querySelectorAll('.del').forEach(el=>el.onclick=async()=>{
    if(!confirm('删掉 '+el.dataset.n+' ？'))return;
    await fetch('/delete?name='+encodeURIComponent(el.dataset.n),{method:'POST'});refresh();});
}
refresh();setInterval(refresh,3000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "UploadBox/1.0"

    # ------------------ 工具 ------------------
    def _send(self, code: int, body: bytes, ctype: str, extra=None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def html(self, text: str, code: int = 200) -> None:
        self._send(code, text.encode("utf-8"), "text/html; charset=utf-8")

    def log_message(self, fmt, *args):  # 只关心投递事件，别刷屏
        if "404" in fmt or "/files" in (args[0] if args else ""):
            return
        print(f"· {args[0] if args else fmt}", flush=True)

    def _drain(self, length: int | None = None) -> None:
        """把请求体读干净（回错误响应前必须做，否则 keep-alive 上会串包）。"""
        remaining = int(self.headers.get("Content-Length") or 0) if length is None else length
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 1 << 20))
            if not chunk:
                break
            remaining -= len(chunk)

    # ------------------ 路由 ------------------
    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self.html(PAGE)
        elif path == "/files":
            self.json(inbox_listing())
        elif path.startswith("/view/"):
            stem = safe_name(path[len("/view/"):])
            f = EXTRACTED / (stem + ".md")
            if not f.exists():
                self.html("<h1>还没生成解析结果</h1>", 404)
                return
            md = f.read_text(encoding="utf-8")
            self.html(
                "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                f"<title>{stem}</title><style>body{{background:#101418;color:#e8ecf1;font:15px/1.7 -apple-system,"
                "'PingFang SC',sans-serif;padding:24px;max-width:1000px;margin:auto}}table{{border-collapse:collapse;"
                "width:100%;margin:14px 0;font-size:14px}}th,td{{border:1px solid #2a3646;padding:8px 10px;"
                "vertical-align:top;text-align:left}}th{{background:#1a2330}}h3{{margin:22px 0 6px}}code{{color:#9ecbff}}"
                "</style><pre style='white-space:pre-wrap;word-break:break-word'>"
                + md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                + "</pre>"
            )
        elif path == "/healthz":
            self.json({"ok": True, "inbox": str(INBOX), "ts": time.time()})
        else:
            self.html("not found", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/upload":
            self.handle_upload()
        elif path == "/note":
            self.handle_note()
        elif path == "/delete":
            self.handle_delete()
        elif path.startswith("/reparse"):
            self.handle_reparse()
        else:
            self.json({"error": "没有这个接口"}, 404)

    def handle_reparse(self):
        """解析器改进之后，把已收到的原件重跑一遍（原件一直在，不用重新上传）。"""
        q = parse_qs(urlparse(self.path).query)
        name = safe_name((q.get("name") or [""])[0])
        self._drain()
        if not name:
            self.json({"error": "没给文件名"}, 400)
            return
        try:
            target = inside_inbox(INBOX / name)
        except PermissionError as exc:
            self.json({"error": str(exc)}, 403)
            return
        if not target.is_file():
            self.json({"error": "找不到这个文件"}, 404)
            return
        res = process(target)
        log_line(f"重新解析 {name}")
        self.json({"ok": True, "error": res["error"], "n_tables": res.get("n_tables", 0),
                   "n_rows": res.get("n_rows", 0), "files": inbox_listing()})

    # ------------------ 实现 ------------------
    def handle_upload(self):
        ctype = self.headers.get("Content-Type", "")
        m = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", ctype)
        if "multipart/form-data" not in ctype or not m:
            self._drain()
            self.json({"error": "不是 multipart 表单"}, 400)
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self.json({"error": "空请求"}, 400)
            return
        if length > MAX_BYTES:
            # keep-alive 连接上必须把请求体读完再回话，不然浏览器下一个请求会串味
            self._drain(length)
            self.json({"error": f"一次传太多了（{length // 1048576} MB，上限 80 MB）；"
                                "请把表格单独存一个文件，或直接在聊天里发我"}, 413)
            return
        body = self.rfile.read(length)
        boundary = ("--" + (m.group(1) or m.group(2)).strip()).encode()
        INBOX.mkdir(parents=True, exist_ok=True)
        saved, skipped, notes_text, parsed = [], [], [], 0
        for part in body.split(boundary):
            part = part.lstrip(b"\r\n")
            if not part or part.startswith(b"--") or b"\r\n\r\n" not in part:
                continue
            head, data = part.split(b"\r\n\r\n", 1)
            data = data.rstrip(b"\r\n")
            hs = head.decode("utf-8", "replace")
            if 'name="note"' in hs:
                text = data.decode("utf-8", "replace").strip()
                if text:
                    notes_text.append(text)
                continue
            fm = re.search(r'filename="([^"]*)"', hs) or re.search(r"filename=([^;]+)", hs)
            raw_name = unquote(fm.group(1)) if fm else ""
            if not raw_name:
                continue
            name = safe_name(raw_name)
            suffix = Path(name).suffix.lower()
            if suffix not in ALLOWED:
                msg = f"{name}：{suffix or '无扩展名'} 不在白名单，已跳过"
                skipped.append(msg)
                log_line("跳过 " + msg)
                continue
            target = unique(INBOX / name)
            target.write_bytes(data)
            saved.append(target.name)
            if extract_tables.HANDLERS.get(suffix) is not None:
                try:
                    res = process(target)
                    if not res["error"] and res["markdown"]:
                        parsed += 1
                    if res["error"]:
                        skipped.append(f"{target.name}：{res['error']}")
                except Exception as exc:  # 解析挂了不影响原件已存
                    log_line(f"{target.name} 解析异常：{exc}")
            else:
                log_line(f"收到 {target.name}（{len(data)} 字节，图片/压缩包不解析）")
        for note in notes_text:
            with (INBOX / "notes.md").open("a", encoding="utf-8") as fh:
                fh.write(f"\n{note}\n")
            log_line(f"收到补充要求一条（{len(note)} 字）")
        if not saved and not notes_text:
            if skipped:
                self.json({"ok": False, "names": [], "parsed": 0, "skipped": skipped})
                return
            self.json({"error": "没在请求里找到文件字段"}, 400)
            return
        self.json({"ok": True, "names": saved, "parsed": parsed, "notes": len(notes_text),
                   "skipped": skipped, "files": inbox_listing()})

    def handle_note(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            text = json.loads(self.rfile.read(length).decode()).get("text", "").strip()
        except Exception:
            self.json({"error": "JSON 没解析出来"}, 400)
            return
        if not text:
            self.json({"error": "空的"}, 400)
            return
        INBOX.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        with (INBOX / "notes.md").open("a", encoding="utf-8") as fh:
            fh.write(f"\n- {stamp} {text}\n")
        log_line(f"收到补充要求一条（{len(text)} 字）")
        self.json({"ok": True})

    def handle_delete(self):
        q = parse_qs(urlparse(self.path).query)
        name = safe_name((q.get("name") or [""])[0])
        if not name:
            self.json({"error": "没给文件名"}, 400)
            return
        try:
            target = inside_inbox(INBOX / name)
        except PermissionError as exc:
            self.json({"error": str(exc)}, 403)
            return
        if not target.is_file():
            self.json({"error": "找不到这个文件"}, 404)
            return
        target.unlink()
        for sib in (EXTRACTED / (target.stem + ".md"), EXTRACTED / (target.stem + ".json")):
            if sib.exists():
                sib.unlink()
        log_line(f"删除 {name}")
        self.json({"ok": True, "files": inbox_listing()})


def main() -> int:
    ap = argparse.ArgumentParser(description="文件投递台（Word/Excel 表格 → 工作区 + 解析）")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="0.0.0.0", help="预览要能从外部访问，默认全网卡")
    ap.add_argument("--no-browser", action="store_true", help="只打印地址")
    args = ap.parse_args()

    INBOX.mkdir(parents=True, exist_ok=True)
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"投递台已启动 → http://{args.host}:{args.port}/", flush=True)
    print(f"文件会落到：{INBOX}", flush=True)
    print(f"解析结果：  {EXTRACTED}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("已停止", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
