#!/usr/bin/env python3
"""把上传的文档拆成「带出处的段落」。

出处的粒度是 **(文件, 页码, 段序号)**——后面抽事实句、做时间线、给解说词找出处，
全都回到这三个数字上。手册第 1 步要求「每一句解说都能指到 sources 里的一条」，
没有这一步的分段编号，那句话就没法落地。

支持：PDF（pypdf）/ Word .docx（zipfile + XML，不引第三方库）/ Markdown / 纯文本 /
网页存档 .html。拆不开的格式会**如实报错**，不会假装抽到了内容。

用法::

    python3 production/docs_lab/extract.py --file ~/资料.pdf --out /tmp/paras.json
"""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

KINDS = {
    ".pdf": "pdf", ".docx": "docx", ".md": "markdown", ".markdown": "markdown",
    ".txt": "text", ".text": "text", ".html": "html", ".htm": "html",
    ".json": "text", ".srt": "text",
}

MIN_PARA_CHARS = 8          # 短于这个的碎片（页码、页眉）直接丢
MAX_PARA_CHARS = 4000


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_paragraphs(raw: str) -> list[str]:
    """空行优先；没有空行时退回按单换行切，再合并过短的碎片。"""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]
    if len(blocks) <= 1:
        blocks = [b.strip() for b in raw.split("\n") if b.strip()]
    merged: list[str] = []
    for b in blocks:
        if merged and (len(b) < 40 or re.match(r"^[\d\.\)\s]*$", b)):
            merged[-1] = merged[-1] + b
        else:
            merged.append(b)
    return [b[:MAX_PARA_CHARS] for b in merged if len(b) >= MIN_PARA_CHARS]


# --------------------------------------------------------------------------- 各格式


def _from_pdf(path: Path) -> tuple[list[dict], int]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("读 PDF 需要 pypdf：pip install pypdf") from exc
    reader = PdfReader(str(path))
    paragraphs: list[dict] = []
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # 加密页 / 坏页：记为 0 字，不假装成功
            text = ""
        for para in _split_paragraphs(_norm(text)):
            paragraphs.append({"page": page_no, "para": len(paragraphs) + 1, "text": para})
    return paragraphs, len(reader.pages)


_W_P = re.compile(r"<w:p\b[^>]*>(.*?)</w:p>", re.S)
_W_T = re.compile(r"<w:t[^>]*>(.*?)</w:t>", re.S)


def _unescape_xml(s: str) -> str:
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
             .replace("&apos;", "'").replace("&amp;", "&"))


def _from_docx(path: Path) -> tuple[list[dict], int]:
    """直接解 zip 读 word/document.xml——不引 python-docx，少一个依赖。"""
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", "replace")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise RuntimeError("这个 .docx 打不开（不是有效的 Word 文件）") from exc
    paragraphs: list[dict] = []
    for block in _W_P.findall(xml):
        text = _norm(_unescape_xml("".join(_W_T.findall(block))))
        if len(text) >= MIN_PARA_CHARS:
            paragraphs.append({"page": 1, "para": len(paragraphs) + 1, "text": text[:MAX_PARA_CHARS]})
    if not paragraphs:
        raise RuntimeError("Word 文档里没有可提取的文字（可能是纯图片扫描件）")
    # docx 没有稳定页码，用每 30 段一页估一个「位置」，出处照样能指回去
    for p in paragraphs:
        p["page"] = (p["para"] - 1) // 30 + 1
    return paragraphs, max(1, (len(paragraphs) - 1) // 30 + 1)


class _HTMLText(HTMLParser):
    SKIP = {"script", "style", "head", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "section", "article"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in ("p", "div", "li", "h1", "h2", "h3", "h4", "tr", "section", "article"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _from_html(path: Path) -> tuple[list[dict], int]:
    parser = _HTMLText()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    parser.close()
    paragraphs = [
        {"page": 1, "para": i + 1, "text": p[:MAX_PARA_CHARS]}
        for i, p in enumerate(_split_paragraphs(_norm("".join(parser.parts))))
    ]
    return paragraphs, 1


def _from_text(path: Path) -> tuple[list[dict], int]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    paragraphs = [
        {"page": 1, "para": i + 1, "text": p[:MAX_PARA_CHARS]}
        for i, p in enumerate(_split_paragraphs(_norm(raw)))
    ]
    return paragraphs, 1


# --------------------------------------------------------------------------- 入口


def extract_document(path: Path) -> dict:
    """拆一份文档。返回 {file, kind, pages, paragraph_count, chars, sha256, paragraphs}。"""
    path = Path(path)
    kind = KINDS.get(path.suffix.lower())
    if kind is None:
        raise RuntimeError(
            f"不支持的格式 {path.suffix}（支持 pdf / docx / md / txt / html）"
        )
    handlers = {"pdf": _from_pdf, "docx": _from_docx, "html": _from_html,
                "markdown": _from_text, "text": _from_text}
    paragraphs, pages = handlers[kind](path)
    if not paragraphs:
        raise RuntimeError("没抽出任何段落——可能是扫描件 PDF（只有图没有文字层）")
    return {
        "file": path.name,
        "kind": kind,
        "bytes": path.stat().st_size,
        "sha256": sha256_of(path),
        "pages": pages,
        "paragraph_count": len(paragraphs),
        "chars": sum(len(p["text"]) for p in paragraphs),
        "paragraphs": paragraphs,
    }


def save_extracted(doc: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (Path(doc["file"]).name + ".json")
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def load_extracted(path: Path) -> Optional[dict]:
    if not Path(path).exists():
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="拆文档成带出处的段落")
    ap.add_argument("--file", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    doc = extract_document(Path(args.file))
    save_extracted(doc, Path(args.out))
    print(json.dumps({k: v for k, v in doc.items() if k != "paragraphs"}, ensure_ascii=False, indent=2))
