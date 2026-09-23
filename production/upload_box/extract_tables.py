#!/usr/bin/env python3
"""把 Word / Excel 里的表格抽成 Markdown 纯文本，只用标准库。

为什么不用 python-docx / openpyxl：出片机和这个沙箱都不保证装得上第三方包，
而"读需求表格"这件事不需要完整实现 OOXML——docx 就是 zip 里的一个
word/document.xml，xlsx 就是 sharedStrings + 若干 sheet XML。

用法：
    python3 extract_tables.py 需求.docx              # 打到 stdout
    python3 extract_tables.py 需求.docx -o 需求.md   # 存文件
    python3 extract_tables.py --json 需求.docx      # 结构化（给上传台用）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class ExtractError(Exception):
    """人类能看懂的失败原因（不是 traceback）。"""


# --------------------------------------------------------------------------- docx


def _para_text(p) -> str:
    """一个 w:p 里的文字：w:t 拼起来，制表符/换行按可读字符处理。"""
    buf: list[str] = []
    for node in p.iter():
        tag = node.tag
        if tag == W + "t":
            buf.append(node.text or "")
        elif tag == W + "tab":
            buf.append("\t")
        elif tag in (W + "br", W + "cr"):
            buf.append("\n")
    return "".join(buf).strip()


def _cell_text(tc) -> str:
    parts = [_para_text(p) for p in tc.findall(f"{W}p")]
    parts = [x for x in parts if x]
    if not parts:  # 嵌套表格 / 非常规结构：兜底把所有文字抓出来
        fallback = " ".join(
            (n.text or "").strip() for n in tc.iter(W + "t") if (n.text or "").strip()
        )
        return fallback
    return "\n".join(parts)


def docx_blocks(path: Path) -> list[dict]:
    """按文档顺序返回 [{'kind':'para','text':...}, {'kind':'table','rows':[[...]]}]。"""
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if "word/document.xml" not in names:
                raise ExtractError("这个 zip 里没有 word/document.xml，不是有效的 .docx")
            root = ET.fromstring(z.read("word/document.xml"))
    except zipfile.BadZipFile as exc:
        raise ExtractError(
            "这个 .docx 打不开（不是有效的 zip，可能损坏，或者是改名过来的旧版 .doc）"
        ) from exc

    body = root.find(f"{W}body")
    if body is None:
        raise ExtractError("document.xml 里没有 body")

    blocks: list[dict] = []
    for el in body:
        if el.tag == W + "p":
            text = _para_text(el)
            if text:
                blocks.append({"kind": "para", "text": text})
        elif el.tag == W + "tbl":
            rows = []
            for tr in el.findall(f"{W}tr"):
                rows.append([_cell_text(tc) for tc in tr.findall(f"{W}tc")])
            rows = [r for r in rows if any(c.strip() for c in r)]
            if rows:
                blocks.append({"kind": "table", "rows": rows})
    if not blocks:
        raise ExtractError("文档里既没有文字也没有表格（可能是空文档）")
    return blocks


# --------------------------------------------------------------------------- xlsx


def _col_index(ref: str) -> int:
    m = re.match(r"([A-Za-z]+)", ref or "")
    if not m:
        return 0
    n = 0
    for ch in m.group(1).upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall(f"{S}si"):
        out.append("".join(t.text or "" for t in si.iter(f"{S}t")))
    return out


def xlsx_blocks(path: Path) -> list[dict]:
    try:
        with zipfile.ZipFile(path) as z:
            shared = _shared_strings(z)
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            rels = {}
            rel_path = "xl/_rels/workbook.xml.rels"
            if rel_path in z.namelist():
                for rel in ET.fromstring(z.read(rel_path)).findall(f"{PR}Relationship"):
                    rels[rel.get("Id")] = rel.get("Target", "")
            blocks: list[dict] = []
            for sheet in wb.iter(f"{S}sheet"):
                name = sheet.get("name") or "sheet"
                target = rels.get(sheet.get(f"{R}id"), "")
                if not target:
                    continue
                member = "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
                if member not in z.namelist():
                    continue
                root = ET.fromstring(z.read(member))
                rows: list[list[str]] = []
                for row in root.iter(f"{S}row"):
                    cells: dict[int, str] = {}
                    for c in row.findall(f"{S}c"):
                        t = c.get("t")
                        if t == "inlineStr":
                            txt = "".join(x.text or "" for x in c.iter(f"{S}t"))
                        else:
                            v = c.find(f"{S}v")
                            txt = v.text if v is not None and v.text is not None else ""
                            if t == "s":  # 共享字符串下标
                                try:
                                    txt = shared[int(txt)]
                                except (ValueError, IndexError):
                                    pass
                        if str(txt).strip():
                            cells[_col_index(c.get("r", ""))] = str(txt).strip()
                    if cells:
                        width = max(cells) + 1
                        rows.append([cells.get(i, "") for i in range(width)])
                if rows:
                    width = max(len(r) for r in rows)
                    rows = [r + [""] * (width - len(r)) for r in rows]
                    blocks.append({"kind": "table", "rows": rows, "title": f"工作表：{name}"})
            if not blocks:
                raise ExtractError("表格里没有内容")
            return blocks
    except zipfile.BadZipFile as exc:
        raise ExtractError("这个 .xlsx 打不开（不是有效的 zip，可能损坏或改名过来的旧版 .xls）") from exc


# --------------------------------------------------------------------------- 文本


def text_blocks(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    return [{"kind": "para", "text": raw}] if raw.strip() else []


def pdf_blocks(path: Path) -> list[dict]:
    raise ExtractError(
        "PDF 先不自动解析（原件已存好）。要么直接在聊天里发我，"
        "要么把要求那页粘成 Word/纯文本再传"
    )


def legacy_blocks(path: Path) -> list[dict]:
    kind = "Word" if path.suffix.lower() == ".doc" else "Excel"
    raise ExtractError(
        f"旧版 {kind} 97-2003 二进制格式读不了——请打开后「另存为 → "
        f"{'docx' if kind == 'Word' else 'xlsx'}」再传一次"
    )


HANDLERS = {
    ".docx": docx_blocks,
    ".docm": docx_blocks,
    ".xlsx": xlsx_blocks,
    ".xlsm": xlsx_blocks,
    ".doc": legacy_blocks,
    ".xls": legacy_blocks,
    ".txt": text_blocks,
    ".md": text_blocks,
    ".markdown": text_blocks,
    ".csv": text_blocks,
    ".pdf": pdf_blocks,
}


# --------------------------------------------------------------------------- 渲染


def _esc(cell: str) -> str:
    return cell.replace("|", "\\|").replace("\n", "<br>").strip()


def to_markdown(blocks: list[dict]) -> str:
    out: list[str] = []
    tno = 0
    for b in blocks:
        if b["kind"] == "para":
            out.append(b["text"])
            continue
        tno += 1
        rows = b["rows"]
        title = b.get("title") or f"表格 {tno}"
        out.append(f"### {title}（{len(rows)} 行 × {len(rows[0])} 列）")
        width = max(len(r) for r in rows)
        norm = [[_esc(c) for c in r] + [""] * (width - len(r)) for r in rows]
        head = norm[0] if any(x for x in norm[0]) else [f"列{i + 1}" for i in range(width)]
        body = norm
        if any(x for x in norm[0]):
            body = norm[1:]
        out.append("| " + " | ".join(head) + " |")
        out.append("|" + "|".join([" --- "] * width) + "|")
        for r in body:
            out.append("| " + " | ".join(r[:width]) + " |")
    return "\n\n".join(x for x in out if x).strip() + "\n"


def extract(path: str | Path) -> dict:
    """返回 {'source', 'kind', 'blocks', 'markdown', 'error'}。永不抛异常。"""
    p = Path(path)
    suffix = p.suffix.lower()
    result = {"source": p.name, "kind": suffix.lstrip("."), "blocks": [], "markdown": "", "error": ""}
    handler = HANDLERS.get(suffix)
    if handler is None:
        result["error"] = f"这种文件（{suffix or '无扩展名'}）不用解析文本，已原样存好"
        return result
    try:
        blocks = handler(p)
        result["blocks"] = blocks
        result["markdown"] = to_markdown(blocks)
        result["n_tables"] = sum(1 for b in blocks if b["kind"] == "table")
        result["n_rows"] = sum(len(b.get("rows", [])) for b in blocks if b["kind"] == "table")
    except ExtractError as exc:
        result["error"] = str(exc)
    except Exception as exc:  # XML 炸了之类的，别把上传台带崩
        result["error"] = f"解析失败：{type(exc).__name__}: {exc}"
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Word/Excel 表格 → Markdown（纯标准库）")
    ap.add_argument("file")
    ap.add_argument("-o", "--out", help="写到这个 .md 文件")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON")
    args = ap.parse_args(argv)

    result = extract(args.file)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.out:
        Path(args.out).write_text(result["markdown"] or f"解析失败：{result['error']}\n", encoding="utf-8")
        print(f"已写入 {args.out}")
    else:
        sys.stdout.write(result["markdown"] or f"解析失败：{result['error']}\n")
    return 0 if not result["error"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
