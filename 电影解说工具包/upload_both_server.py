#!/usr/bin/env python3
"""视频 + 文案双区上传服务器（一个页面、一个端口，两个上传区）。

用法：
    python3 电影解说工具包/upload_both_server.py [端口]     # 默认 8802

页面左侧（视频区）：
  * 拖拽 / 点击选择视频（MP4 / MOV / MKV / WebM / AVI / M4V / TS），单个最大 3 GB
  * 选中后本地即可预览；5 MB 分块上传、自动重试，断了把同一个文件再传一次即可
  * 文件落到仓库根目录的 `incoming_uploads/`（已在 .gitignore，不会污染 Git），
    上传完显示大小 / SHA-256，有 ffprobe 时再显示时长与分辨率，可在页面里直接回放

页面右侧（文案区，跟原 upload_text_server.py 同一套逻辑）：
  * 拖拽 / 点击选择 txt 等纯文本，或把文案直接粘进文本框保存
  * 自动识别编码（UTF-8 / GBK·GB18030 / Big5 / UTF-16），统一存 UTF-8 不乱码
  * 文件落到 `抖音文案/`，带时间戳永不覆盖，上传完显示字数 / 行数 / 预计口播时长

两个区互不影响：可以只传视频、只传文案，也可以两个一起传。
上传完成后回对话说一句「视频和文案传好了」，就能开始做片子。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "incoming_uploads"        # 视频落点（.gitignore 已忽略）
DOC_DIR = ROOT / "抖音文案"                    # 文案落点（随仓库保存）
LOG = DOC_DIR / "上传记录.jsonl"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
DOC_DIR.mkdir(parents=True, exist_ok=True)

# ---- 文案参数（与 upload_text_server.py 保持一致）----
TEXT_MAX = 20 * 1024 * 1024
TEXT_SUFFIX = {".txt", ".text", ".md", ".markdown", ".json", ".csv", ".srt", ".vtt", ".log", ".yml", ".yaml"}
CHARS_PER_SECOND = 4.5  # 中文口播约 4.5 字/秒，用来估算时长

# ---- 视频参数（与 upload_server.py 保持一致）----
CHUNK = 5 * 1024 * 1024
VIDEO_MAX = 3 * 1024 ** 3
VIDEO_SUFFIX = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".ts"}
VIDEO_MIME = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime",
              ".webm": "video/webm", ".mkv": "video/x-matroska", ".avi": "video/x-msvideo",
              ".ts": "video/mp2t"}

LOCK = threading.Lock()

PAGE = r"""<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>上传视频 + 文案</title>
<style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;padding:28px 14px 64px;background:radial-gradient(circle at 18% 0,#1d2942,#080c15 55%,#04060b);color:#f3f6ff;font:15px/1.7 system-ui,"Microsoft YaHei",sans-serif}
main{width:min(1180px,96vw);margin:0 auto}
header{margin:0 0 20px}
h1{margin:0 0 6px;font-size:26px}
h2{margin:0 0 6px;font-size:19px}
.lead{color:#aebbd1;margin:0}
.lead em{color:#8fb2ff;font-style:normal}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.panel{padding:24px 24px 28px;background:#141b2bee;border:1px solid #35435f;border-radius:20px;box-shadow:0 24px 80px #0009}
.sub{color:#93a3bd;font-size:13px;margin:0 0 16px}
.drop{display:block;padding:38px 18px;border:2px dashed #5d729a;border-radius:16px;text-align:center;cursor:pointer;background:#101827;transition:.16s}
.drop:hover,.drop.hot{border-color:#7fa8ff;background:#16203a}
.drop b{display:block;font-size:17px;margin-bottom:6px}
.drop span{color:#93a3bd;font-size:13px}
input[type=file]{display:none}
textarea{width:100%;min-height:150px;margin-top:6px;padding:14px;border-radius:12px;border:1px solid #35435f;background:#101827;color:#eaf0ff;font:14px/1.7 inherit;resize:vertical}
textarea:focus{outline:none;border-color:#7fa8ff}
button{padding:11px 20px;border:0;border-radius:10px;background:#5d87f7;color:#fff;font-weight:700;font-size:14px;cursor:pointer}
button:hover{background:#6f95ff}
button:disabled{opacity:.45;cursor:not-allowed}
button.ghost{background:#26324b;color:#cfdcf5;padding:7px 13px;font-weight:600}
button.ghost:hover{background:#32405e}
.bar-row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:12px}
.track{height:8px;margin:16px 0 6px;background:#2a354d;border-radius:99px;overflow:hidden}
.bar{height:100%;width:0;background:linear-gradient(90deg,#557ff3,#74c7ff);transition:.2s}
.status{min-height:24px;color:#b9c6dd;word-break:break-all;font-size:14px}
video{width:100%;max-height:320px;margin-top:14px;border-radius:12px;background:#000;display:none}
.card{margin-top:16px;padding:15px;background:#101827;border:1px solid #26324b;border-radius:12px}
.card .hd{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}
pre.pv{margin:10px 0 0;max-height:240px;overflow:auto;padding:13px;background:#0a101c;border-radius:10px;white-space:pre-wrap;word-break:break-word;font:13px/1.75 Consolas,"Microsoft YaHei",monospace;color:#d7e2f7}
ul.files{list-style:none;margin:14px 0 0;padding:0}
ul.files li{padding:11px 13px;margin-bottom:8px;background:#101724;border:1px solid #26324b;border-radius:11px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
ul.files .nm{flex:1;min-width:160px;word-break:break-all;font-weight:650;color:#e6edff;font-size:14px}
ul.files .mt{color:#8f9db6;font-size:12.5px}
.tag{display:inline-block;padding:1px 8px;margin-left:6px;border-radius:99px;background:#26324b;color:#9fb7e6;font-size:12px}
.list-title{margin:22px 0 0;font-size:15px;color:#cfdcf5}
.hint{margin-top:18px;padding:14px 16px;background:#141b2bee;border:1px solid #35435f;border-left:4px solid #7199ff;border-radius:12px;color:#c4d1e8;font-size:14px}
.ok{color:#50dda0;font-weight:700}.warn{color:#ffd36e}.err{color:#ff8181}
.muted{color:#7f8da6;font-size:13px}
</style>
<main>
  <header>
    <h1>🎬 上传视频 + 文案</h1>
    <p class="lead">左边传视频，右边传文案，两个区互不影响。视频存到 <em>incoming_uploads/</em>，文案存到 <em>抖音文案/</em>，传完回对话说一句「视频和文案传好了」即可开工。</p>
  </header>

  <div class="grid">
    <!-- ============ 视频区 ============ -->
    <section class="panel">
      <h2>📹 视频上传区</h2>
      <p class="sub">支持 MP4 / MOV / MKV / WebM / AVI / M4V / TS，单个最大 3 GB，5 MB 分块上传自动重试。</p>
      <div class="drop" id="vDrop" tabindex="0" role="button">
        <b>拖拽视频到这里，或点击选择</b>
        <span id="vName">尚未选择文件</span>
        <input id="vFile" type="file" accept="video/*,.mp4,.mov,.mkv,.webm,.avi,.m4v,.ts">
      </div>
      <video id="vPreview" controls preload="metadata"></video>
      <div class="track"><div class="bar" id="vBar"></div></div>
      <div class="status" id="vStatus">等待选择视频</div>
      <div class="bar-row">
        <button id="vGo" disabled>开始上传视频</button>
        <span class="muted" id="vInfo"></span>
      </div>
      <div id="vCard"></div>
      <h3 class="list-title">已收到的视频</h3>
      <ul class="files" id="vList"><li class="muted">正在读取…</li></ul>
    </section>

    <!-- ============ 文案区 ============ -->
    <section class="panel">
      <h2>📝 文案上传区</h2>
      <p class="sub">支持 .txt .md .json .csv .srt 等纯文本，可多选，单个最大 20 MB；GBK 等编码自动识别。</p>
      <div class="drop" id="tDrop" tabindex="0" role="button">
        <b>拖拽 txt 文件到这里，或点击选择</b>
        <span>也可以把文字直接粘到下面输入框保存</span>
        <input id="tFile" type="file" multiple accept=".txt,.text,.md,.markdown,.json,.csv,.srt,.vtt,.log,.yml,.yaml,text/plain">
      </div>
      <div class="track"><div class="bar" id="tBar"></div></div>
      <div class="status" id="tStatus">等待上传</div>
      <textarea id="ta" placeholder="从任何地方复制文案，Ctrl+V 粘进来，然后点下面的按钮…"></textarea>
      <div class="bar-row">
        <button id="tSave">保存这段文字</button>
        <span class="muted" id="taInfo">0 字</span>
      </div>
      <div id="tCard"></div>
      <h3 class="list-title">已收到的文案</h3>
      <ul class="files" id="tList"><li class="muted">正在读取…</li></ul>
    </section>
  </div>

  <div class="hint"><b>上传完成后：</b>回对话说一句「视频和文案传好了」，我会读 <b>incoming_uploads/</b> 里的视频和 <b>抖音文案/</b> 里的最新文案，开始做片子（分镜、配音稿、字幕、时长都按这份文案来）。Word / PDF 请先「另存为 → 纯文本 txt」，或直接把文字粘进右边输入框。</div>
</main>
<script>
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmtSize = n => n < 1024 ? n + ' B' : (n >= 1048576 ? (n / 1048576).toFixed(2) + ' MB' : (n / 1024).toFixed(1) + ' KB');
const fmtTime = s => { s = Math.round(s); const m = Math.floor(s / 60); return m ? `${m} 分 ${s % 60} 秒` : `${s} 秒`; };
const wait = ms => new Promise(r => setTimeout(r, ms));

/* ---------------- 视频区 ---------------- */
const vDrop = $('#vDrop'), vFile = $('#vFile'), vBar = $('#vBar'), vStatus = $('#vStatus'),
      vGo = $('#vGo'), vName = $('#vName'), vInfo = $('#vInfo'), vPreview = $('#vPreview'),
      vList = $('#vList'), vCard = $('#vCard');
let picked = null;

function vSay(t, cls) { vStatus.className = 'status' + (cls ? ' ' + cls : ''); vStatus.textContent = t; }

function pickVideo(file) {
  picked = file || null;
  if (!picked) { vGo.disabled = true; return; }
  vName.textContent = `${picked.name}（${fmtSize(picked.size)}）`;
  vInfo.textContent = picked.type || '';
  vGo.disabled = false;
  vBar.style.width = '0%';
  try {
    vPreview.src = URL.createObjectURL(picked);
    vPreview.style.display = 'block';
  } catch (e) { vPreview.style.display = 'none'; }
  vSay('已选择，点击「开始上传视频」');
}

async function sendChunk(id, file, i, total, offset, blob) {
  const q = new URLSearchParams({ id, name: file.name, index: i, total, size: file.size, offset });
  for (let k = 1; k <= 5; k++) {
    try {
      const r = await fetch('/video/upload?' + q, { method: 'POST', body: blob });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || '上传失败');
      return j;
    } catch (err) {
      if (k === 5) throw err;
      vSay(`网络波动，第 ${k} 次重试…`, 'warn');
      await wait(k * 900);
    }
  }
}

vGo.onclick = async () => {
  if (!picked) return;
  vGo.disabled = true; vFile.disabled = true;
  const id = Date.now().toString(36) + Math.random().toString(36).slice(2);
  const total = Math.max(1, Math.ceil(picked.size / (5 * 1024 * 1024)));
  try {
    let last = null;
    for (let i = 0; i < total; i++) {
      const a = i * 5 * 1024 * 1024, z = Math.min(picked.size, a + 5 * 1024 * 1024);
      vSay(`上传中 ${fmtSize(z)} / ${fmtSize(picked.size)}（分块 ${i + 1}/${total}）`);
      last = await sendChunk(id, picked, i, total, a, picked.slice(a, z));
      vBar.style.width = (z / picked.size * 100) + '%';
    }
    const meta = [fmtSize(last.size), last.duration ? '时长 ' + fmtTime(last.duration) : '',
                  last.width ? `${last.width}×${last.height}` : ''].filter(Boolean).join(' · ');
    vCard.innerHTML = `<div class="card"><b class="ok">✓ 视频已保存：${esc(last.saved)}</b>
      <div class="muted">${esc(meta)}<br>SHA-256：${esc(last.sha256)}</div></div>`;
    vSay('✓ 视频上传完成，可以回到对话了', 'ok');
    vGo.textContent = '上传完成 ✓';
    vPreview.src = '/video/file?name=' + encodeURIComponent(last.saved);
    vPreview.style.display = 'block';
    loadVideos();
  } catch (err) {
    vSay('× 上传失败：' + err.message, 'err');
    vGo.disabled = false; vFile.disabled = false; vGo.textContent = '重新上传';
  }
};

async function loadVideos() {
  try {
    const j = await (await fetch('/video/list')).json();
    if (!j.files.length) { vList.innerHTML = '<li class="muted">还没有收到视频</li>'; return; }
    vList.innerHTML = j.files.map(f => `<li>
      <span class="nm">${esc(f.saved)}</span>
      <span class="mt">${fmtSize(f.bytes)}${f.duration ? ' · ' + fmtTime(f.duration) : ''}${f.width ? ' · ' + f.width + '×' + f.height : ''} · ${esc(f.time)}</span>
      <button class="ghost" data-play="${esc(encodeURIComponent(f.saved))}">播放</button></li>`).join('');
    vList.querySelectorAll('[data-play]').forEach(btn => btn.onclick = () => {
      vPreview.src = '/video/file?name=' + btn.dataset.play;
      vPreview.style.display = 'block';
      vPreview.scrollIntoView({ behavior: 'smooth', block: 'center' });
      vPreview.play().catch(() => {});
    });
  } catch (e) { vList.innerHTML = '<li class="err">列表读取失败</li>'; }
}

['dragenter', 'dragover'].forEach(ev => vDrop.addEventListener(ev, e => { e.preventDefault(); vDrop.classList.add('hot'); }));
['dragleave', 'dragend', 'drop'].forEach(ev => vDrop.addEventListener(ev, e => { e.preventDefault(); vDrop.classList.remove('hot'); }));
vDrop.addEventListener('drop', e => { if (e.dataTransfer.files.length) pickVideo(e.dataTransfer.files[0]); });
vDrop.addEventListener('click', e => { if (e.target.tagName !== 'INPUT') vFile.click(); });
vDrop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); vFile.click(); } });
vFile.addEventListener('change', () => pickVideo(vFile.files[0]));

/* ---------------- 文案区 ---------------- */
const tDrop = $('#tDrop'), tFile = $('#tFile'), tBar = $('#tBar'), tStatus = $('#tStatus'),
      tList = $('#tList'), tCard = $('#tCard'), ta = $('#ta'), taInfo = $('#taInfo');

function tSay(t, cls) { tStatus.className = 'status' + (cls ? ' ' + cls : ''); tStatus.textContent = t; }

function showTextCard(info) {
  const t = info.text || '';
  tCard.innerHTML = `<div class="card"><div class="hd"><div>
      <b class="ok">✓ 已保存：${esc(info.saved)}</b>
      <div class="muted">编码 ${esc(info.encoding)} · ${fmtSize(info.bytes)} · ${info.chars} 字 · ${info.lines} 行 · 预计口播约 ${fmtTime(info.chars / 4.5)}</div>
    </div><button class="ghost" id="tCopy">复制全文</button></div>
    <pre class="pv" id="tPv"></pre></div>`;
  $('#tPv').textContent = t.length > 4000 ? t.slice(0, 4000) + '\n\n……（预览到此为止，完整内容已保存）' : t;
  $('#tCopy').onclick = async () => {
    try { await navigator.clipboard.writeText(t); $('#tCopy').textContent = '已复制 ✓'; }
    catch (e) { $('#tCopy').textContent = '请手动全选复制'; }
  };
}

async function uploadTextFile(file) {
  const buf = await file.arrayBuffer();
  for (let k = 1; k <= 4; k++) {
    try {
      const r = await fetch('/text/upload?name=' + encodeURIComponent(file.name), { method: 'POST', body: buf });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || '上传失败');
      return j;
    } catch (err) {
      if (k === 4) throw err;
      tSay(`网络波动，第 ${k} 次重试…`, 'warn');
      await wait(k * 800);
    }
  }
}

async function handleTextFiles(files) {
  const list = [...files];
  if (!list.length) return;
  tFile.disabled = true;
  let done = 0;
  for (const f of list) {
    try {
      tSay(`正在上传 ${f.name} …`);
      const info = await uploadTextFile(f);
      done++;
      showTextCard(info);
      tSay(`✓ 已保存 ${info.saved}（${info.chars} 字，${info.lines} 行）`, 'ok');
    } catch (err) { tSay(`× ${f.name} 上传失败：${err.message}`, 'err'); }
    tBar.style.width = (done / list.length * 100) + '%';
    loadTexts();
  }
  tFile.disabled = false; tFile.value = '';
  if (done) tSay(`✓ 全部完成（${done}/${list.length}）· 回到对话说一句「文案传好了」即可`, 'ok');
}

async function loadTexts() {
  try {
    const j = await (await fetch('/text/list')).json();
    if (!j.files.length) { tList.innerHTML = '<li class="muted">还没有收到任何文件</li>'; return; }
    tList.innerHTML = j.files.map(f => `<li>
      <span class="nm">${esc(f.saved)}${f.encoding && !String(f.encoding).startsWith('utf-8') ? `<span class="tag">原编码 ${esc(f.encoding)}</span>` : ''}</span>
      <span class="mt">${f.chars} 字 · ${fmtSize(f.bytes)} · ${esc(f.time)}</span>
      <button class="ghost" data-view="${esc(encodeURIComponent(f.saved))}">查看</button></li>`).join('');
    tList.querySelectorAll('[data-view]').forEach(btn => btn.onclick = async () => {
      try {
        const r = await fetch('/text/view?name=' + btn.dataset.view);
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || '读取失败');
        showTextCard(j);
        tCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } catch (err) { tSay('读取失败：' + err.message, 'err'); }
    });
  } catch (e) { tList.innerHTML = '<li class="err">列表读取失败</li>'; }
}

['dragenter', 'dragover'].forEach(ev => tDrop.addEventListener(ev, e => { e.preventDefault(); tDrop.classList.add('hot'); }));
['dragleave', 'dragend', 'drop'].forEach(ev => tDrop.addEventListener(ev, e => { e.preventDefault(); tDrop.classList.remove('hot'); }));
tDrop.addEventListener('drop', e => { if (e.dataTransfer.files.length) handleTextFiles(e.dataTransfer.files); });
tDrop.addEventListener('click', e => { if (e.target.tagName !== 'INPUT') tFile.click(); });
tDrop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); tFile.click(); } });
tFile.addEventListener('change', () => handleTextFiles(tFile.files));

ta.addEventListener('input', () => { taInfo.textContent = ta.value.length + ' 字'; });
$('#tSave').onclick = async () => {
  const text = ta.value.trim();
  if (!text) { tSay('粘贴框里还没有内容', 'warn'); return; }
  $('#tSave').disabled = true;
  try {
    tSay('正在保存粘贴的内容…');
    const r = await fetch('/text/paste', { method: 'POST', body: text, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || '保存失败');
    showTextCard(j);
    tSay(`✓ 已保存 ${j.saved}（${j.chars} 字，${j.lines} 行）`, 'ok');
    loadTexts();
  } catch (err) { tSay('保存失败：' + err.message, 'err'); }
  $('#tSave').disabled = false;
};

loadVideos();
loadTexts();
</script>
</html>
"""

# ================= 文案：存 / 读 =================

def decode_any(raw: bytes) -> tuple[str, str]:
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


def safe_text_name(value: str, fallback: str = "文案.txt") -> str:
    value = urllib.parse.unquote(value or "")
    value = re.sub(r"[\x00-\x1f\\/:*?\"<>|]", "_", Path(value).name).strip(" .")
    return value[:120] or fallback


def unique_doc_path(name: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    stem, suffix = os.path.splitext(safe_text_name(name))
    suffix = suffix or ".txt"
    candidate = DOC_DIR / f"{stamp}_{stem}{suffix}"
    i = 2
    while candidate.exists():
        candidate = DOC_DIR / f"{stamp}_{stem}-{i}{suffix}"
        i += 1
    return candidate


def save_text(raw: bytes, name: str, source: str) -> dict:
    if len(raw) > TEXT_MAX:
        raise ValueError(f"文件太大（上限 {TEXT_MAX // 1024 // 1024} MB）")
    if not raw.strip():
        raise ValueError("内容为空")
    text, encoding = decode_any(raw)
    if looks_binary(text):
        raise ValueError("这看起来是二进制文件，不是纯文本，请另存为 txt 再传")
    suffix = os.path.splitext(name)[1].lower() or ".txt"
    if suffix not in TEXT_SUFFIX:
        raise ValueError(f"只接收纯文本文件（不支持 {suffix}）")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    target = unique_doc_path(os.path.splitext(name)[0] + suffix)
    target.write_text(text, encoding="utf-8", newline="\n")
    info = {
        "saved": target.name,
        "chars": sum(1 for ch in text if not ch.isspace()),
        "total_chars": len(text),
        "lines": text.count("\n") + 1,
        "bytes": len(raw),
        "encoding": encoding,
        "source": source,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with LOCK:
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(info, ensure_ascii=False) + "\n")
    print(f"TEXT UPLOAD {info['saved']} chars={info['chars']} enc={encoding} via={source}", flush=True)
    return {**info, "text": text}


def list_texts() -> list[dict]:
    entries: dict[str, dict] = {}
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("saved"):
                entries[item["saved"]] = item
    files = [it for name, it in entries.items() if (DOC_DIR / name).is_file()]
    files.sort(key=lambda it: it.get("time", ""), reverse=True)
    return files[:60]


def read_text(name: str) -> dict:
    name = Path(safe_text_name(name)).name
    target = DOC_DIR / name
    if target.parent.resolve() != DOC_DIR.resolve() or not target.is_file():
        raise ValueError("找不到这个文件")
    text = target.read_text(encoding="utf-8", errors="replace")
    meta = next((it for it in list_texts() if it["saved"] == name), {})
    return {
        "saved": name, "text": text,
        "chars": meta.get("chars", sum(1 for ch in text if not ch.isspace())),
        "lines": meta.get("lines", text.count("\n") + 1),
        "bytes": meta.get("bytes", target.stat().st_size),
        "encoding": meta.get("encoding", "utf-8"),
        "time": meta.get("time", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(target.stat().st_mtime))),
    }


# ================= 视频：存 / 读 =================

def safe_video_name(value: str) -> str:
    value = urllib.parse.unquote(value or "")
    value = re.sub(r"[\x00-\x1f\\/:*?\"<>|]", "_", Path(value).name).strip(" .")
    return value[:180] or "uploaded-video.mp4"


def file_hash(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            d.update(block)
    return d.hexdigest().upper()


def probe_video(path: Path) -> dict:
    """有 ffprobe 就取时长/分辨率，没有就安静跳过（不阻塞上传）。"""
    exe = shutil.which("ffprobe")
    if not exe:
        return {}
    try:
        out = subprocess.run(
            [exe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,codec_name,avg_frame_rate",
             "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        data = json.loads(out.stdout or "{}")
        stream = (data.get("streams") or [{}])[0]
        num, _, den = str(stream.get("avg_frame_rate", "0/1")).partition("/")
        fps = round(float(num) / float(den), 2) if den and float(den) else None
        return {"width": stream.get("width"), "height": stream.get("height"),
                "codec": stream.get("codec_name"), "fps": fps,
                "duration": round(float(data.get("format", {}).get("duration", 0)), 2) or None}
    except Exception:
        return {}


def unique_video_path(name: str) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    stem, suffix = os.path.splitext(safe_video_name(name))
    candidate = VIDEO_DIR / f"{stamp}_{stem}{suffix}"
    i = 2
    while candidate.exists():
        candidate = VIDEO_DIR / f"{stamp}_{stem}-{i}{suffix}"
        i += 1
    return candidate


def list_videos() -> list[dict]:
    files = []
    for p in VIDEO_DIR.iterdir():
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in VIDEO_SUFFIX:
            files.append({"saved": p.name, "bytes": p.stat().st_size,
                          "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)),
                          **probe_video(p)})
    files.sort(key=lambda it: it["time"], reverse=True)
    return files[:60]


# ================= HTTP =================

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "UploadBoth/1.0"

    def log_message(self, *args):
        pass

    def send_body(self, code, body: bytes, content_type: str, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json_response(self, code, payload):
        self.send_body(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                       "application/json; charset=utf-8")

    def read_body(self, limit: int) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > limit:
            raise ValueError(f"内容太大（上限 {limit // 1024 // 1024} MB）")
        chunks, remaining = [], length
        while remaining > 0:
            block = self.rfile.read(min(remaining, 1 << 20))
            if not block:
                raise ValueError("上传连接中断")
            chunks.append(block)
            remaining -= len(block)
        return b"".join(chunks)

    # ---- GET ----
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/text/list":
                self.json_response(200, {"files": list_texts()})
            elif parsed.path == "/text/view":
                self.json_response(200, read_text(query.get("name", [""])[0]))
            elif parsed.path == "/video/list":
                self.json_response(200, {"files": list_videos()})
            elif parsed.path == "/video/file":
                self.serve_video(query.get("name", [""])[0])
            elif parsed.path == "/favicon.ico":
                self.send_body(204, b"", "image/x-icon")
            else:
                self.send_body(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        except Exception as exc:
            self.json_response(404, {"error": str(exc)})

    def serve_video(self, name: str):
        name = Path(safe_video_name(name)).name
        target = VIDEO_DIR / name
        if target.parent.resolve() != VIDEO_DIR.resolve() or not target.is_file():
            raise ValueError("找不到这个视频")
        size = target.stat().st_size
        mime = VIDEO_MIME.get(target.suffix.lower(), "application/octet-stream")
        start, end = 0, size - 1
        range_hdr = self.headers.get("Range", "")
        m = re.match(r"bytes=(\d*)-(\d*)", range_hdr)
        if m:
            if m.group(1):
                start = int(m.group(1))
            if m.group(2):
                end = min(int(m.group(2)), size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with target.open("rb") as fh:
            fh.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                block = fh.read(min(remaining, 1 << 20))
                if not block:
                    break
                try:
                    self.wfile.write(block)
                except (BrokenPipeError, ConnectionResetError):
                    break
                remaining -= len(block)

    # ---- POST ----
    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if parsed.path == "/text/upload":
                raw = self.read_body(TEXT_MAX)
                self.json_response(200, save_text(raw, safe_text_name(query.get("name", [""])[0]), "文件"))
            elif parsed.path == "/text/paste":
                raw = self.read_body(TEXT_MAX)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                self.json_response(200, save_text(raw, f"粘贴的文案_{stamp}.txt", "粘贴"))
            elif parsed.path == "/video/upload":
                self.json_response(200, self.save_video_chunk(query))
            else:
                self.json_response(404, {"error": "地址无效"})
        except Exception as exc:
            self.json_response(400, {"error": str(exc)})

    def save_video_chunk(self, query) -> dict:
        get = lambda k: query[k][0]
        uid = re.sub(r"[^A-Za-z0-9_-]", "", get("id"))
        filename = safe_video_name(get("name"))
        index, total = int(get("index")), int(get("total"))
        size, offset = int(get("size")), int(get("offset"))
        length = int(self.headers.get("Content-Length") or 0)
        suffix = os.path.splitext(filename)[1].lower()
        if suffix not in VIDEO_SUFFIX:
            raise ValueError(f"只接收视频文件（不支持 {suffix or '无扩展名'}）")
        if not uid or not (0 <= index < total <= 2000 and 0 < size <= VIDEO_MAX):
            raise ValueError("文件或分块参数无效")
        if offset != index * CHUNK or length != min(CHUNK, size - offset):
            raise ValueError("分块位置或大小无效")
        partial = VIDEO_DIR / f".{uid}.part"
        got_path = VIDEO_DIR / f".{uid}.json"
        with LOCK:
            with partial.open("r+b" if partial.exists() else "w+b") as fh:
                fh.seek(offset)
                remaining = length
                while remaining:
                    block = self.rfile.read(min(remaining, 1024 * 1024))
                    if not block:
                        raise ValueError("上传连接提前中断")
                    fh.write(block)
                    remaining -= len(block)
            got = set(json.loads(got_path.read_text()) if got_path.exists() else [])
            got.add(index)
            got_path.write_text(json.dumps(sorted(got)), encoding="utf-8")
        if len(got) != total:
            return {"ok": True, "done": False}
        if partial.stat().st_size != size:
            raise ValueError("文件大小校验失败")
        target = unique_video_path(filename)
        os.replace(partial, target)
        got_path.unlink(missing_ok=True)
        info = {"ok": True, "done": True, "saved": target.name, "size": size,
                "sha256": file_hash(target), **probe_video(target)}
        print(f"VIDEO UPLOAD {info['saved']} size={size} sha256={info['sha256'][:12]}", flush=True)
        return info


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8802
    print(f"视频+文案上传区已启动：http://0.0.0.0:{port}  视频→{VIDEO_DIR}  文案→{DOC_DIR}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
