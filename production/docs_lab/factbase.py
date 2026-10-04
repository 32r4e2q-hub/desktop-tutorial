#!/usr/bin/env python3
"""从拆好的段落里做事实底稿：候选事实句、时间线、待标注的不确定句。

这是手册第 1 步（先写事实边界）的**底稿**，不是结论。它做的事情只有一件：
把「哪些句子看起来是可核查的事实、它在哪一页哪一段」摆出来，让人去核。
不替人判断真假，也不自动写进 `SOURCES`——`build_story.py` 里的
`SOURCES` / `PRINCIPLES` 仍由人根据这份底稿填写。

打分规则（可核查性信号）::

    +2  含日期（2026年4月8日 / 1993–2010 / 2023-01-26）
    +1  含数字 + 单位（99.96%、1.93 米、12 天、7 项）
    +1  含司法/调查动词或名词（逮捕、起诉、认罪、判决、搜查、DNA、证词…）
    -1  含不确定措辞（疑似、可能、据称、尚未…）——这些不降级，只是另列一栏

用法::

    from factbase import build_factbase, write_factbase
    fb = build_factbase(extracted_docs)
    write_factbase(out_dir, fb)
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------- 信号

DATE_PATTERNS = [
    re.compile(r"((?:19|20)\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"),
    re.compile(r"((?:19|20)\d{2})\s*年\s*(\d{1,2})\s*月"),
    re.compile(r"((?:19|20)\d{2})\s*年"),
    re.compile(r"((?:19|20)\d{2})[-/](\d{1,2})[-/](\d{1,2})"),
    re.compile(r"((?:19|20)\d{2})\s*[-–—]\s*((?:19|20)\d{2})"),   # 1993–2010
]
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|个百分点|米|公分|厘米|公里|千米|英里|英尺|英寸|磅|公斤|个|名|位|项|起|次|天|日|年|月|小时|分钟|秒|万美元|美元|元|岁|楼|号)")
LEGAL_TERMS = [
    "逮捕", "拘留", "起诉", "指控", "认罪", "不认罪", "辩护", "判决", "宣判", "量刑", "终身监禁", "不得假释",
    "保释", "上诉", "庭审", "法庭", "法院", "检察官", "地检", "大陪审团", "证词", "证人", "证物", "证据",
    "搜查", "搜查令", "取证", "鉴定", "比对", "DNA", "线粒体", "毛发", "指纹", "监控", "摄像头", "基站",
    "专案组", "州警", "县警", "FBI", "联邦调查局", "供述", "交代", "移交", "立案", "结案", "撤销",
    "遇害", "失踪", "遗体", "尸体", "发现", "报案", "搜寻", "搜救",
]
UNCERTAIN_TERMS = ["疑似", "可能", "据称", " reportedly", "尚未", "未起诉", "未经", "未判决", "存疑",
                   "无法确认", "不能排除", "有争议", "据说", "外界推测", "不排除", "待核"]
SENT_SPLIT = re.compile(r"(?<=[。！？!?；;])|\n+")
MIN_SENTENCE = 12
MAX_FACTS = 80
MAX_TIMELINE = 60


def split_sentences(para: str) -> list[str]:
    parts = [s.strip() for s in SENT_SPLIT.split(para) if s and s.strip()]
    # 太短的碎片（标题、页码）并回上一句，避免底稿里出现半句话
    merged: list[str] = []
    for s in parts:
        if merged and len(s) < MIN_SENTENCE:
            merged[-1] = merged[-1] + s
        else:
            merged.append(s)
    return [s for s in merged if len(s) >= MIN_SENTENCE]


def _date_hits(text: str) -> list[tuple[str, tuple[int, int, int]]]:
    """返回 (原文片段, 可排序的 (年, 月, 日))。"""
    hits = []
    for pat in DATE_PATTERNS:
        for m in pat.finditer(text):
            g = [int(x) for x in m.groups() if x]
            if pat is DATE_PATTERNS[4]:          # 年份区间：取起始年
                key = (g[0], 0, 0)
            else:
                key = (g[0], g[1] if len(g) > 1 else 0, g[2] if len(g) > 2 else 0)
            hits.append((re.sub(r"\s+", "", m.group(0)), key))   # 「2010 年」「2010年」算同一个时间
    # 去重：同一句里重复出现的同一年只留一次
    seen, out = set(), []
    for raw, key in hits:
        if key in seen:
            continue
        seen.add(key)
        out.append((raw, key))
    return out


def _signals(text: str) -> tuple[int, list[str]]:
    score, tags = 0, []
    dates = _date_hits(text)
    if dates:
        score += 2
        tags.append("日期")
    if NUMBER_RE.search(text):
        score += 1
        tags.append("数字")
    legal = sorted({t for t in LEGAL_TERMS if t in text})
    if legal:
        score += 1
        tags.append("司法/" + "、".join(legal[:3]))
    return score, tags


def cite(doc: str, page: int, para: int) -> str:
    return f"《{doc}》第 {page} 页 ¶{para}"


# --------------------------------------------------------------------------- 构建


def build_factbase(docs: list[dict], workspace: str = "default") -> dict:
    """docs = extract.extract_document() 的结果列表。"""
    facts: list[dict] = []
    timeline: list[dict] = []
    uncertain: list[dict] = []
    seen_sentences: dict[str, dict] = {}
    seen_uncertain: set[str] = set()

    for doc in docs:
        fname = doc.get("file", "?")
        for para in doc.get("paragraphs", []):
            for sent in split_sentences(para["text"]):
                key = re.sub(r"\s+", "", sent)
                if key in seen_sentences:
                    seen_sentences[key]["重复出现"] += 1
                    continue
                score, tags = _signals(sent)
                record = {
                    "text": sent,
                    "chars": len(sent),
                    "doc": fname,
                    "page": para["page"],
                    "para": para["para"],
                    "cite": cite(fname, para["page"], para["para"]),
                    "score": score,
                    "tags": tags,
                    "重复出现": 1,
                }
                seen_sentences[key] = record
                if any(t in sent for t in UNCERTAIN_TERMS) and key not in seen_uncertain:
                    # 同一句话可能在两份资料里都出现，只列一次——出处留第一次那条
                    seen_uncertain.add(key)
                    uncertain.append(record)
                if score >= 2:
                    facts.append(record)
                for raw, key_date in _date_hits(sent):
                    timeline.append({
                        "date_text": raw,
                        "sort": list(key_date),
                        "sentence": sent,
                        "cite": record["cite"],
                    })

    facts.sort(key=lambda r: (-r["score"], -r["chars"]))
    timeline.sort(key=lambda r: tuple(r["sort"]))
    # 同一年只保留信息量最大的几句，时间线才读得下去
    per_year: dict[int, int] = {}
    trimmed = []
    for item in timeline:
        y = item["sort"][0]
        per_year[y] = per_year.get(y, 0) + 1
        if per_year[y] <= 3:
            trimmed.append(item)
    timeline = trimmed[:MAX_TIMELINE]

    doc_meta = [
        {
            "file": d.get("file"), "kind": d.get("kind"), "sha256": d.get("sha256"),
            "pages": d.get("pages"), "paragraph_count": d.get("paragraph_count"),
            "chars": d.get("chars"), "bytes": d.get("bytes"),
            "uploaded_at": d.get("uploaded_at"),
        }
        for d in docs
    ]
    return {
        "workspace": workspace,
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stats": {
            "docs": len(docs),
            "paragraphs": sum(d.get("paragraph_count", 0) for d in docs),
            "sentences": len(seen_sentences),
            "fact_candidates": len(facts),
            "timeline_entries": len(timeline),
            "uncertain_sentences": len(uncertain),
        },
        "docs": doc_meta,
        "facts": facts[:MAX_FACTS],
        "timeline": timeline,
        "uncertain": uncertain[:40],
    }


# --------------------------------------------------------------------------- 成文


def render_markdown(fb: dict) -> str:
    st = fb["stats"]
    lines = [
        "# 事实底稿",
        "",
        f"工作区 **{fb['workspace']}** · {st['docs']} 份资料 · {st['paragraphs']} 段 · "
        f"{st['sentences']} 句 · 建成于 {fb['built_at']}。",
        "",
        "> 这是**底稿**不是结论：下面每一条都是「看起来可核查的句子 + 它在哪一页哪一段」，"
        "真假要人去核。核完再填进 `build_story.py` 的 `SOURCES` / `PRINCIPLES`。",
        "",
        "## 一、资料清单",
        "",
        "| 文件 | 类型 | 页 | 段 | 字数 | SHA-256 |",
        "|---|---|---|---|---|---|",
    ]
    if fb["docs"]:
        for d in fb["docs"]:
            lines.append(
                f"| {d['file']} | {d['kind']} | {d['pages']} | {d['paragraph_count']} | {d['chars']} | "
                f"`{(d['sha256'] or '')[:12]}…` |"
            )
    else:
        lines.append("| （还没有资料） | | | | | |")

    lines += ["", "## 二、时间线（按年份归并，同年最多 3 条）", "", "| 时间 | 句子 | 出处 |", "|---|---|---|"]
    for item in fb["timeline"]:
        lines.append(f"| {item['date_text']} | {item['sentence']} | {item['cite']} |")
    if not fb["timeline"]:
        lines.append("| （没检出日期） | | |")

    lines += ["", "## 三、候选事实句（按可核查信号排序，前 80 条）", "", "| 信号 | 句子 | 出处 |", "|---|---|---|"]
    for f in fb["facts"]:
        lines.append(f"| {'+'.join(f['tags']) or '—'} | {f['text']} | {f['cite']} |")
    if not fb["facts"]:
        lines.append("| （没检出） | | |")

    lines += [
        "",
        "## 四、必须标注为不确定的句子",
        "",
        "含「疑似 / 可能 / 据称 / 未起诉 / 尚未 / 存疑」等措辞的句子都在这里。"
        "手册第 1 步：**未定论的事不写成结论**——这些句子进解说词时必须带不确定标记，",
        "或者干脆不写。",
        "",
    ]
    for u in fb["uncertain"]:
        lines.append(f"- {u['text']} —— {u['cite']}")
    if not fb["uncertain"]:
        lines.append("- （没有）")

    lines += [
        "",
        "## 五、事实边界草稿（填 `build_story.py` 的 `PRINCIPLES` 时用）",
        "",
        "- 每一句解说都要能指到 `SOURCES` 里的一条公开来源；这条底稿里的「出处」就是索引；",
        "- 上面第四节列出的句子，片中只能写成「疑似 / 尚未起诉」这一层，不写成结论；",
        "- TTS 内容审核会拦血腥与教唆式措辞：作案手法写到「勒死、麻布、弃尸」这一层就够，不写过程；",
        "- AI 画面一律标注「AI动画情景重现 · 非新闻影像」；真实人物只以背影、剪影、手出现；",
        "- 受害者不以人像出现；不展示遗体；",
        "- 中文姓名、日期、字幕一律后期添加，不交给视频模型拼写。",
        "",
        "## 已知误差",
        "",
        "- 「候选事实句」靠信号打分（日期 / 数字 / 司法词），**会漏也会误报**："
        "没有这些信号的事实句不会入选，有这些信号的废话会入选；",
        "- 时间线按年份归并，同年最多留 3 条，长报道的细节会被裁掉；",
        "- PDF 的页码来自 PDF 自身分页；Word 没有稳定页码，按每 30 段估算一页，出处仍指得回去；",
        "- 扫描件 PDF（只有图、没有文字层）抽不出内容，会如实报错，不会假装抽到了。",
    ]
    return "\n".join(lines)


def write_factbase(out_dir: Path, fb: dict) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "sources.json").write_text(json.dumps(fb, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "事实底稿.md").write_text(render_markdown(fb), encoding="utf-8")
    return fb


def load_factbase(out_dir: Path) -> Optional[dict]:
    p = Path(out_dir) / "sources.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="从已拆好的段落生成事实底稿")
    ap.add_argument("--extracted-dir", required=True, help="放 *.json 段落文件的目录")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(args.extracted_dir).glob("*.json"))]
    fb = build_factbase(docs, workspace=Path(args.out).name)
    write_factbase(Path(args.out), fb)
    print(json.dumps(fb["stats"], ensure_ascii=False, indent=2))
