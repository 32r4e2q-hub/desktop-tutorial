#!/usr/bin/env python3
"""脚本 / 文案上传服务器。

浏览器里把脚本文件拖进上传区，或直接把文字粘进来，内容就直接落到仓库的
`抖音文案/` 文件夹，对话里的我立刻就能读到，不用再往聊天框里粘一大段字。

用法：
    python 电影解说工具包/upload_text_server.py [端口]     # 默认 8801

特点：
  * 支持拖拽 / 点击选择 / 直接粘贴三种方式，粘贴时可以给稿子起名字
  * 自动识别编码（UTF-8、UTF-8 BOM、GBK/GB18030、Big5、UTF-16），
    统一另存为 UTF-8，Windows 记事本存的 txt 也不会乱码
  * Word 的 .docx 可以直接传，服务器自动抽出正文存成 txt（.doc/.pdf 请另存或粘贴）
  * 上传后立即显示字数、行数、预计口播时长，方便卡抖音的时长
  * 单文件上限 20 MB，文件名做了安全清洗
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
DOC_DIR = ROOT / "抖音文案"          # 上传进来的文案都放这里（仓库内，会随工作区保存）
LOG = DOC_DIR / "上传记录.jsonl"
MAX_BYTES = 20 * 1024 * 1024          # 单个文件上限 20 MB
ALLOWED_SUFFIX = {
    ".txt", ".text", ".md", ".markdown", ".json",
    ".csv", ".srt", ".vtt", ".log", ".yml", ".yaml", ".docx",
}
# 中文口播速度约每秒 4.5 字，用来估算成片时长
CHARS_PER_SECOND = 4.5

DOC_DIR.mkdir(parents=True, exist_ok=True)
LOCK = threading.Lock()

PAGE = r"""<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>脚本 / 文档上传区</title>
<style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;padding:28px 14px 64px;background:radial-gradient(circle at 18% 0,#1d2942,#080c15 55%,#04060b);color:#f3f6ff;font:15px/1.7 system-ui,"Microsoft YaHei",sans-serif}
main{width:min(860px,94vw);margin:0 auto;padding:30px 32px 36px;background:#141b2bee;border:1px solid #35435f;border-radius:20px;box-shadow:0 24px 80px #0009}
h1{margin:0 0 8px;font-size:25px}
h2{margin:34px 0 12px;font-size:17px;color:#cfdcf5}
.lead{color:#aebbd1;margin:0 0 22px}
.lead em{color:#8fb2ff;font-style:normal}
.drop{display:block;padding:46px 20px;border:2px dashed #5d729a;border-radius:16px;text-align:center;cursor:pointer;background:#101827;transition:.16s}
.drop:hover,.drop.hot{border-color:#7fa8ff;background:#16203a}
.drop b{display:block;font-size:18px;margin-bottom:8px}
.drop span{color:#93a3bd;font-size:13px}
input[type=file]{display:none}
input[type=text]{width:100%;margin-top:6px;padding:12px 14px;border-radius:11px;border:1px solid #35435f;background:#101827;color:#eaf0ff;font:14px/1.7 inherit}
input[type=text]:focus{outline:none;border-color:#7fa8ff}
textarea{width:100%;min-height:220px;margin-top:8px;padding:14px;border-radius:12px;border:1px solid #35435f;background:#101827;color:#eaf0ff;font:14px/1.75 inherit;resize:vertical}
textarea:focus{outline:none;border-color:#7fa8ff}
button{padding:11px 20px;border:0;border-radius:10px;background:#5d87f7;color:#fff;font-weight:700;font-size:14px;cursor:pointer}
button:hover{background:#6f95ff}
button:disabled{opacity:.45;cursor:not-allowed}
button.ghost{background:#26324b;color:#cfdcf5}
button.ghost:hover{background:#32405e}
.bar-row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:12px}
.track{height:8px;margin:18px 0 6px;background:#2a354d;border-radius:99px;overflow:hidden}
.bar{height:100%;width:0;background:linear-gradient(90deg,#557ff3,#74c7ff);transition:.2s}
#status{min-height:24px;color:#b9c6dd;word-break:break-all}
ul.files{list-style:none;margin:0;padding:0}
ul.files li{padding:12px 14px;margin-bottom:9px;background:#101724;border:1px solid #26324b;border-radius:11px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
ul.files .nm{flex:1;min-width:200px;word-break:break-all;font-weight:650;color:#e6edff}
ul.files .mt{color:#8f9db6;font-size:12.5px}
.tag{display:inline-block;padding:1px 8px;margin-left:6px;border-radius:99px;background:#26324b;color:#9fb7e6;font-size:12px}
.card{margin-top:16px;padding:16px;background:#101827;border:1px solid #26324b;border-radius:12px}
.card .hd{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
pre.pv{margin:0;max-height:280px;overflow:auto;padding:14px;background:#0a101c;border-radius:10px;white-space:pre-wrap;word-break:break-word;font:13.5px/1.75 "Consolas","Microsoft YaHei",monospace;color:#d7e2f7}
.hint{margin-top:22px;padding:13px 15px;background:#202a40;border-left:4px solid #7199ff;border-radius:9px;color:#c4d1e8;font-size:14px}
.ok{color:#50dda0;font-weight:700}
.warn{color:#ffd36e}
.err{color:#ff8181}
.muted{color:#7f8da6;font-size:13px}
</style>
<main>
  <h1>脚本 / 文档上传区</h1>
  <p class="lead">把脚本文件拖进来，或直接粘进来，内容会存到仓库的 <em>抖音文案/</em> 文件夹，对话里的我马上就能读到 —— 不用再往聊天框里粘一大段字。</p>

  <div class="drop" id="drop" tabindex="0" role="button">
    <b>拖拽脚本文件到这里，或点击选择</b>
    <span>.txt .md .json .csv .srt，以及 Word 的 .docx（自动抽出正文），可多选，单个最大 20 MB</span>
    <input id="file" type="file" multiple accept=".txt,.text,.md,.markdown,.json,.csv,.srt,.vtt,.log,.yml,.yaml,.docx,text/plain">
  </div>
  <div class="track"><div class="bar" id="bar"></div></div>
  <div id="status">等待上传</div>

  <h2>或者：直接把脚本粘贴到这里</h2>
  <input id="taName" type="text" placeholder="给这份稿子起个名字（可不填，默认用「粘贴的脚本_时间戳」）" maxlength="80">
  <textarea id="ta" placeholder="从任何地方复制脚本，Ctrl+V 粘进来，然后点下面的按钮…"></textarea>
  <div class="bar-row">
    <button id="save">保存这段文字</button>
    <span class="muted" id="taInfo">0 字</span>
  </div>

  <div id="card"></div>

  <h2>已经收到的文件</h2>
  <ul class="files" id="list"><li class="muted">正在读取…</li></ul>

  <div class="hint">
    <b>上传完成后：</b>回到对话跟我说一句「脚本传好了」，我就能读到 <code>抖音文案/</code> 里最新的稿子，按它继续往下做。<br>
    PDF / .doc（老版 Word）请先在软件里「另存为 → txt 或 docx」，或直接把文字粘贴到上面的框里。
  </div>
</main>
<script>
const $ = s => document.querySelector(s);
const drop = $('#drop'), fileInput = $('#file'), bar = $('#bar'), statusEl = $('#status');
const listEl = $('#list'), cardEl = $('#card'), ta = $('#ta'), taInfo = $('#taInfo'), taName = $('#taName');

const fmtSize = n => n < 1024 ? n + ' B' : (n >= 1048576 ? (n / 1048576).toFixed(2) + ' MB' : (n / 1024).toFixed(1) + ' KB');
const fmtTime = s => { s = Math.round(s); const m = Math.floor(s / 60); return m ? `${m} 分 ${s % 60} 秒` : `${s} 秒`; };

function say(text, cls) { statusEl.className = cls || ''; statusEl.textContent = text; }

function showCard(info) {
  const t = info.text || '';
  const chars = info.chars, lines = info.lines;
  cardEl.innerHTML = `
    <div class="card">
      <div class="hd">
        <div><b class="ok">✓ 已保存：${info.saved}</b>
          <div class="muted">${info.encoding === 'docx' ? '由 Word 抽出正文' : '编码 ' + info.encoding} · ${fmtSize(info.bytes)} · ${chars} 字 · ${lines} 行
          · 预计口播 约 ${fmtTime(chars / 4.5)}</div></div>
        <div><button class="ghost" id="copy">复制全文</button></div>
      </div>
      <pre class="pv" id="pv"></pre>
    </div>`;
  $('#pv').textContent = t.length > 4000 ? t.slice(0, 4000) + '\n\n……（预览到此为止，完整内容已保存）' : t;
  $('#copy').onclick = async () => {
    try { await navigator.clipboard.writeText(t); $('#copy').textContent = '已复制 ✓'; }
    catch (e) { $('#copy').textContent = '请手动全选复制'; }
  };
}

async function uploadFile(file) {
  const buf = await file.arrayBuffer();
  const url = '/upload?name=' + encodeURIComponent(file.name);
  for (let attempt = 1; attempt <= 4; attempt++) {
    try {
      const r = await fetch(url, { method: 'POST', body: buf });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || '上传失败');
      return j;
    } catch (err) {
      if (attempt === 4) throw err;
      say(`网络波动，第 ${attempt} 次重试…`, 'warn');
      await new Promise(res => setTimeout(res, attempt * 800));
    }
  }
}

async function handleFiles(files) {
  const list = [...files];
  if (!list.length) return;
  fileInput.disabled = true;
  let done = 0;
  for (const f of list) {
    const lower = f.name.toLowerCase();
    if (lower.endsWith('.pdf') || lower.endsWith('.doc')) {
      say(`× ${f.name}：浏览器读不了这个格式，请另存为 txt / docx，或直接把文字粘到下面的框里`, 'err');
      continue;
    }
    if (lower.endsWith('.docx') && f.size > 10 * 1048576) {
      say(`× ${f.name}：docx 超过 10 MB，多半是插了很多图，请把正文复制粘贴到下面的框里`, 'err');
      continue;
    }
    try {
      say(`正在上传 ${f.name} …`);
      const info = await uploadFile(f);
      done++;
      showCard(info);
      say(`✓ 已保存 ${info.saved}（${info.chars} 字，${info.lines} 行）`, 'ok');
    } catch (err) {
      say(`× ${f.name} 上传失败：${err.message}`, 'err');
    }
    bar.style.width = (done / list.length * 100) + '%';
    await loadList();
  }
  fileInput.disabled = false;
  fileInput.value = '';
  if (done) say(`✓ 全部完成（${done}/${list.length}）· 回到对话说一句「脚本传好了」即可`, 'ok');
}

function bindDrop() {
  ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => {
    e.preventDefault(); drop.classList.add('hot');
  }));
  ['dragleave', 'dragend', 'drop'].forEach(ev => drop.addEventListener(ev, e => {
    e.preventDefault(); drop.classList.remove('hot');
  }));
  drop.addEventListener('drop', e => { if (e.dataTransfer && e.dataTransfer.files) handleFiles(e.dataTransfer.files); });
  // 整个页面都支持拖入，避免拖到页面空白处被浏览器直接打开
  window.addEventListener('dragover', e => e.preventDefault());
  window.addEventListener('drop', e => { e.preventDefault(); if (e.dataTransfer && e.dataTransfer.files.length) handleFiles(e.dataTransfer.files); });
  drop.addEventListener('click', e => { if (e.target.tagName !== 'INPUT') fileInput.click(); });
  drop.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
  });
  fileInput.addEventListener('change', () => handleFiles(fileInput.files));
}

async function loadList() {
  try {
    const j = await (await fetch('/list')).json();
    if (!j.files.length) { listEl.innerHTML = '<li class="muted">还没有收到任何文件</li>'; return; }
    listEl.innerHTML = j.files.map(f => {
      const fromWord = f.encoding === 'docx';
      const oddEnc = f.encoding && !fromWord && !f.encoding.startsWith('utf-8');
      return `
      <li>
        <span class="nm">${f.saved}${fromWord ? '<span class="tag">Word 正文</span>' : ''}${oddEnc ? `<span class="tag">原编码 ${f.encoding}</span>` : ''}</span>
        <span class="mt">${f.chars} 字 · ${fmtSize(f.bytes)} · ${f.time}</span>
        <button class="ghost" data-view="${encodeURIComponent(f.saved)}">查看</button>
      </li>`;
    }).join('');
    listEl.querySelectorAll('[data-view]').forEach(btn => btn.onclick = async () => {
      try {
        const r = await fetch('/view?name=' + btn.dataset.view);
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || '读取失败');
        showCard(j);
        cardEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } catch (err) { say('读取失败：' + err.message, 'err'); }
    });
  } catch (err) { listEl.innerHTML = '<li class="err">列表读取失败</li>'; }
}

ta.addEventListener('input', () => { taInfo.textContent = ta.value.length + ' 字'; });
// Ctrl / ⌘ + Enter 直接保存，省得去点按钮
ta.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); $('#save').click(); }
});

$('#save').onclick = async () => {
  const text = ta.value.trim();
  if (!text) { say('粘贴框里还没有内容', 'warn'); return; }
  $('#save').disabled = true;
  try {
    say('正在保存粘贴的内容…');
    const name = taName.value.trim();
    const url = '/paste' + (name ? '?name=' + encodeURIComponent(name) : '');
    const r = await fetch(url, { method: 'POST', body: text, headers: { 'Content-Type': 'text/plain;charset=utf-8' } });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || '保存失败');
    showCard(j);
    say(`✓ 已保存 ${j.saved}（${j.chars} 字）`, 'ok');
    ta.value = ''; taInfo.textContent = '0 字'; taName.value = '';
    await loadList();
  } catch (err) { say('保存失败：' + err.message, 'err'); }
  $('#save').disabled = false;
};

bindDrop();
loadList();
</script>
</html>
"""


def decode_any(raw: bytes) -> tuple[str, str]:
    """把字节还原成文字，返回 (文本, 编码名)。乱码兜底一路降级，尽量不丢字。"""
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "utf-8-bom"
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")) and len(raw) % 2 == 0:
        try:
            return raw.decode("utf-16"), "utf-16"
        except UnicodeError:
            pass
    for enc in ("utf-8", "gb18030", "big5"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace"), "utf-8(部分乱码)"


def looks_binary(text: str) -> bool:
    if not text:
        return False
    bad = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t\f")
    return bad / len(text) > 0.05


def safe_name(value: str, fallback: str = "文案.txt") -> str:
    value = urllib.parse.unquote(value or "")
    value = re.sub(r"[\x00-\x1f/\\:*?\"<>|]", "_", Path(value).name).strip(" .")
    return value[:120] or fallback


def safe_stem(value: str, fallback: str = "粘贴的脚本") -> str:
    """给「自己起名」的稿子用：去掉路径分隔符和扩展名，只留一个干净的名字。"""
    stem = os.path.splitext(safe_name(value, fallback))[0].strip(" .")
    return stem[:80] or fallback


def docx_to_text(raw: bytes) -> str:
    """从 .docx 里抽出正文：按段落换行，表格按行用制表符连起来。不依赖第三方库。"""
    import io

    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        xml = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError("这个 .docx 打不开（可能已损坏，或是改了后缀的 .doc），"
                         "请用 Word / WPS 另存为 docx 或 txt 再传") from exc
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise ValueError("这个 .docx 的正文读不出来，请另存为 txt 再传") from exc

    def paragraph_text(element) -> str:
        pieces: list[str] = []
        for node in element.iter():
            if node.tag == namespace + "t" and node.text:
                pieces.append(node.text)
            elif node.tag == namespace + "tab":
                pieces.append("\t")
            elif node.tag in (namespace + "br", namespace + "cr"):
                pieces.append("\n")
        return "".join(pieces)

    def walk(node) -> list[str]:
        """按文档顺序走一遍；表格里的段落只由表格分支处理，不会被抽两遍。"""
        out: list[str] = []
        for child in node:
            if child.tag == namespace + "p":
                out.append(paragraph_text(child))
            elif child.tag == namespace + "tbl":
                for row in child.iter(namespace + "tr"):
                    cells = []
                    for cell in row.iter(namespace + "tc"):
                        cells.append(" ".join(paragraph_text(p) for p in cell.iter(namespace + "p")).strip())
                    if any(cells):
                        out.append("\t".join(cells))
            else:
                out.extend(walk(child))
        return out

    blocks = walk(root)
    text = "\n".join(blocks)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise ValueError("这个 .docx 里没有可读的文字（可能整篇都是图片），请把文字复制粘贴到下面的框里")
    return text


def unique_path(name: str) -> Path:
    """加时间戳前缀，重名自动加序号，绝不覆盖旧稿。"""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    stem, suffix = os.path.splitext(safe_name(name))
    suffix = suffix or ".txt"
    candidate = DOC_DIR / f"{stamp}_{stem}{suffix}"
    index = 2
    while candidate.exists():
        candidate = DOC_DIR / f"{stamp}_{stem}-{index}{suffix}"
        index += 1
    return candidate


def save_text(raw: bytes, name: str, source: str, stem: str | None = None) -> dict:
    if len(raw) > MAX_BYTES:
        raise ValueError(f"文件太大（上限 {MAX_BYTES // 1024 // 1024} MB）")
    if not raw.strip():
        raise ValueError("内容为空")
    suffix = os.path.splitext(name)[1].lower() or ".txt"
    if suffix not in ALLOWED_SUFFIX:
        raise ValueError(f"这个格式不支持（{suffix or '无扩展名'}）："
                         "请传 txt / md / docx，或把文字直接粘贴到框里")
    if suffix == ".docx":
        text, encoding = docx_to_text(raw), "docx"
        suffix = ".txt"                      # 抽出来的正文按 txt 存，方便直接读
    else:
        text, encoding = decode_any(raw)
        if looks_binary(text):
            raise ValueError("这看起来是二进制文件，不是纯文本，请另存为 txt 再传")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    base_name = os.path.splitext(safe_name(name))[0] if stem is None else safe_stem(stem)
    target = unique_path(base_name + suffix)
    target.write_text(text, encoding="utf-8", newline="\n")
    info = {
        "saved": target.name,
        "chars": sum(1 for ch in text if not ch.isspace()),
        "total_chars": len(text),
        "lines": len(text.rstrip("\n").split("\n")) if text.strip() else 0,
        "bytes": len(raw),
        "encoding": encoding,
        "source": source,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with LOCK:
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(info, ensure_ascii=False) + "\n")
    print(f"UPLOAD {info['saved']} chars={info['chars']} enc={encoding} via={source}", flush=True)
    return {**info, "text": text}


def list_files() -> list[dict]:
    entries: dict[str, dict] = {}
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("saved"):
                entries[item["saved"]] = item
    files = [item for name, item in entries.items() if (DOC_DIR / name).is_file()]
    files.sort(key=lambda item: item.get("time", ""), reverse=True)
    return files[:60]


def read_saved(name: str) -> dict:
    name = Path(safe_name(name)).name
    target = DOC_DIR / name
    if target.parent.resolve() != DOC_DIR.resolve() or not target.is_file():
        raise ValueError("找不到这个文件")
    text = target.read_text(encoding="utf-8", errors="replace")
    meta = next((item for item in list_files() if item["saved"] == name), {})
    return {
        "saved": name,
        "text": text,
        "chars": meta.get("chars", sum(1 for ch in text if not ch.isspace())),
        "lines": meta.get("lines", len(text.rstrip("\n").split("\n"))),
        "bytes": meta.get("bytes", target.stat().st_size),
        "encoding": meta.get("encoding", "utf-8"),
        "time": meta.get("time", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(target.stat().st_mtime))),
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "TextUpload/1.0"

    def log_message(self, *args):  # 默认日志太吵，只留我们自己的 print
        pass

    def send_body(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json_response(self, code: int, payload: dict) -> None:
        self.send_body(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

    def read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BYTES:
            raise ValueError(f"内容太大（上限 {MAX_BYTES // 1024 // 1024} MB）")
        chunks, remaining = [], length
        while remaining > 0:
            block = self.rfile.read(min(remaining, 1 << 20))
            if not block:
                raise ValueError("上传连接中断")
            chunks.append(block)
            remaining -= len(block)
        return b"".join(chunks)

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/list":
            self.json_response(200, {"files": list_files()})
            return
        if parsed.path == "/view":
            try:
                self.json_response(200, read_saved(query.get("name", [""])[0]))
            except Exception as exc:
                self.json_response(404, {"error": str(exc)})
            return
        if parsed.path in ("/favicon.ico",):
            self.send_body(204, b"", "image/x-icon")
            return
        self.send_body(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/upload":
                raw = self.read_body()
                name = safe_name(query.get("name", [""])[0])
                self.json_response(200, save_text(raw, name, "文件"))
            elif parsed.path == "/paste":
                raw = self.read_body()
                stamp = time.strftime("%Y%m%d-%H%M%S")
                wanted = query.get("name", [""])[0]
                stem = safe_stem(wanted) if wanted.strip() else f"粘贴的脚本_{stamp}"
                self.json_response(200, save_text(raw, "粘贴的脚本.txt", "粘贴", stem=stem))
            else:
                self.json_response(404, {"error": "地址无效"})
        except Exception as exc:
            self.json_response(400, {"error": str(exc)})


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8801
    print(f"文案上传区已启动：http://0.0.0.0:{port}  保存目录：{DOC_DIR}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
