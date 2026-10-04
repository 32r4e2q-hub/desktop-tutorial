#!/usr/bin/env python3
"""解说词体检：字数/时长能不能塞进去，TTS 会不会拦，每句有没有出处。

三条硬指标全部来自 [`新题目开工手册.md`](../../新题目开工手册.md) 与吉尔戈成片的实测值，
不自己发明阈值：

| 指标 | 依据 |
|---|---|
| 六章、总字数 760–800 | 手册第 2 步：「超过 800 字就塞不进去」 |
| 可用时长 176.1 s、语速 4.46 字/秒 | 吉尔戈实测：785 字 → 收紧停顿后 176.1 s |
| 数字写中文读法 | 手册第 2 步：TTS 才不会念错，逐字听检才对得上 |
| 每句要能指到 SOURCES 一条 | 手册第 1 步 |

「出处映射」是字符二元组召回率：句子的二元组有多少出现在资料段落里。
0.34 以上算对得上，0.18 以下算没有出处。**它只报相似度，不证明事实成立**——
判定真假仍然是人的活。

用法::

    from script_qa import qa_script, write_qa
    qa = qa_script(text, extracted_docs)
    write_qa(out_dir, qa)
"""
from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path
from typing import Optional

# 吉尔戈成片实测：784 字（手册记 785）→ 收紧停顿后 176.1 秒
REF_CHARS = 784
REF_SECONDS = 176.1
CHARS_PER_SECOND = REF_CHARS / REF_SECONDS          # ≈ 4.46 字/秒
BUDGET_SECONDS = REF_SECONDS
TARGET_CHARS = (760, 800)                            # 手册第 2 步
CHAPTER_SECONDS = 30.0                               # 手册：三分钟 = 6 章
SECONDS_PER_SHOT = 4.0                               # 手册：45 镜 × 4 秒

STRONG = 0.34
WEAK = 0.18

# TTS 内容审核会拦血腥 / 教唆式措辞。手册：写到「勒死、麻布、弃尸」这一层就够。
ALLOWED_LAYER = ["勒死", "麻布", "弃尸", "捆绑", "作案", "遇害", "失踪", "遗体"]
HIGH_RISK = [
    "分尸", "碎尸", "肢解", "强奸", "性侵", "猥亵", "虐杀", "折磨", "虐打", "勒颈",
    "砍", "刺穿", "捅", "血迹", "血腥", "鲜血", "腐", "剥", "焚尸", "奸尸",
    "如何作案", "作案步骤", "详细方法", "教你", "步骤一",
]
UNCERTAIN_MARKERS = ["疑似", "可能", "据称", "尚未", "未起诉", "未经", "存疑", "不排除"]

CJK = r"\u4e00-\u9fff"
CJK_RE = re.compile(f"[{CJK}]")
# 字数口径：一个汉字算一个，一个英文字母/数字也算一个。
# 拿 production/gilgo/story.json 的六章正文反算过：这样数出来 784，手册记的是 785，
# 差 1 个字在误差里——用这个口径算时长才跟 176.1 秒对得上。
CHAR_RE = re.compile(f"[{CJK}]|[A-Za-z0-9]")
DIGIT_RE = re.compile(r"\d+(?:\.\d+)?%?")
YEAR_RE = re.compile(r"(?:19|20)\d{2}")
SENT_SPLIT = re.compile(r"(?<=[。！？!?；;])|\n+")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s*(.+?)\s*$", re.M)
CHAPTER_RE = re.compile(r"^\s*(?:第\s*([一二三四五六七八九十\d]+)\s*章|\s*([1-9])\s*[.、)])\s*(.*)$")


# --------------------------------------------------------------------------- 计数


def count_chars(text: str) -> int:
    """字数口径：一个汉字一个，一个英文字母/数字一个，标点不算。"""
    return len(CHAR_RE.findall(text))


def split_chapters(text: str) -> list[dict]:
    """按 `##` 标题 → `第N章 / N.` → 空行 分章；返回 [{title, text}]。"""
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    if HEADING_RE.search(text):
        parts = HEADING_RE.split(text)
        # split 结果：[前言, 标题1, 正文1, 标题2, 正文2 …]
        chapters = []
        if parts[0].strip():
            chapters.append({"title": "（标题前）", "text": parts[0].strip()})
        for i in range(1, len(parts) - 1, 2):
            chapters.append({"title": parts[i].strip(), "text": parts[i + 1].strip()})
        return [c for c in chapters if c["text"]]

    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) > 1 and any(CHAPTER_RE.match(b) for b in blocks):
        chapters, buf = [], None
        for b in blocks:
            m = CHAPTER_RE.match(b)
            if m:
                if buf:
                    chapters.append(buf)
                buf = {"title": f"第 {m.group(1) or m.group(2)} 章", "text": m.group(3) or ""}
            elif buf:
                buf["text"] = (buf["text"] + "\n" + b).strip()
            else:
                chapters.append({"title": "（无标题）", "text": b})
        if buf:
            chapters.append(buf)
        return [c for c in chapters if c["text"]]

    return [{"title": f"第 {i + 1} 段", "text": b} for i, b in enumerate(blocks)]


def split_sentences(text: str, min_len: int = 6) -> list[str]:
    out = []
    for s in SENT_SPLIT.split(text):
        s = (s or "").strip()
        if len(s) >= min_len:
            out.append(s)
    return out


def _bigrams(text: str) -> set[str]:
    chars = CJK_RE.findall(text)
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


# --------------------------------------------------------------------------- 出处


def build_index(docs: list[dict]) -> list[dict]:
    """把资料段落摊平成 [{doc, page, para, text, bigrams, digits}]。"""
    index = []
    for doc in docs:
        for p in doc.get("paragraphs", []):
            index.append({
                "doc": doc.get("file", "?"),
                "page": p["page"],
                "para": p["para"],
                "text": p["text"],
                "bigrams": _bigrams(p["text"]),
                "digits": set(DIGIT_RE.findall(p["text"])),
            })
    return index


def match_sentence(sentence: str, index: list[dict]) -> tuple[float, Optional[dict]]:
    """字符二元组召回率 + 数字命中加成。返回 (分数, 最佳段落)。"""
    if not index:
        return 0.0, None
    grams = _bigrams(sentence)
    nums = set(DIGIT_RE.findall(sentence))
    best_score, best = 0.0, None
    for item in index:
        if not grams:
            score = 0.0
        else:
            score = len(grams & item["bigrams"]) / len(grams)
        if nums and (nums & item["digits"]):
            score += 0.15
        if score > best_score:
            best_score, best = score, item
    return round(min(best_score, 1.0), 3), best


# --------------------------------------------------------------------------- 体检


def qa_script(text: str, docs: Optional[list[dict]] = None, script_name: str = "剧本") -> dict:
    docs = docs or []
    index = build_index(docs)
    chapters = split_chapters(text)
    total = count_chars(text)

    chapter_rows = []
    for i, ch in enumerate(chapters, 1):
        chars = count_chars(ch["text"])
        seconds = chars / CHARS_PER_SECOND
        chapter_rows.append({
            "index": i,
            "title": ch["title"],
            "chars": chars,
            "seconds": round(seconds, 1),
            "shots": max(1, math.ceil(seconds / SECONDS_PER_SHOT)),
            "sentences": len(split_sentences(ch["text"])),
        })

    est_seconds = total / CHARS_PER_SECOND
    verdicts: list[str] = []
    structural = 0
    if len(chapters) != 6:
        structural += 1
        verdicts.append(f"章数是 {len(chapters)}，手册要求 **6 章**（三分钟 = 6 章 × 30 秒）")
    if total < TARGET_CHARS[0] or total > TARGET_CHARS[1]:
        structural += 1
        fix = "要补" if total < TARGET_CHARS[0] else "要删"
        verdicts.append(
            f"总字数 {total}，手册区间是 {TARGET_CHARS[0]}–{TARGET_CHARS[1]}，"
            f"{fix} {abs(total - (TARGET_CHARS[0] if total < TARGET_CHARS[0] else TARGET_CHARS[1]))} 字"
        )
    if est_seconds > BUDGET_SECONDS:
        structural += 1
        verdicts.append(
            f"按 {CHARS_PER_SECOND:.2f} 字/秒估算 {est_seconds:.1f} 秒，超过 {BUDGET_SECONDS} 秒预算——"
            f"**只能删字，不能硬变速**（±10 % 以外人声会飘）"
        )
    if not docs:
        verdicts.append("这个工作区还没有上传资料，出处映射没跑——先传资料")
    if structural == 0:
        verdicts.insert(0, "字数、章数、时长都在区间内 ✅")

    # 逐句扫描的单位是「章节正文里的句子」：标题行不算句子，
    # 否则「## 第3章」会被当成一句没有出处的解说词。
    units: list[tuple[int, str]] = []
    for ci, ch in enumerate(chapters, 1):
        for s in split_sentences(ch["text"]):
            units.append((ci, s))

    # 风险词 / 数字 / 不确定措辞
    risk_hits, digit_hits, uncertain_hits, allowed_hits = [], [], [], []
    for _ci, s in units:
        for w in HIGH_RISK:
            if w in s:
                risk_hits.append({"word": w, "sentence": s})
        for w in ALLOWED_LAYER:
            if w in s:
                allowed_hits.append({"word": w, "sentence": s})
        for m in DIGIT_RE.finditer(s):
            raw = m.group(0)
            if YEAR_RE.fullmatch(raw.rstrip("%")):
                continue
            digit_hits.append({"digit": raw, "sentence": s})
        for w in UNCERTAIN_MARKERS:
            if w in s:
                uncertain_hits.append({"word": w, "sentence": s})
                break

    # 逐句出处映射
    sentences = []
    for ci, s in units:
        score, para = match_sentence(s, index)
        level = "强" if score >= STRONG else ("弱" if score >= WEAK else "无")
        sentences.append({
            "chapter": ci,
            "text": s,
            "chars": count_chars(s),
            "score": score,
            "level": level,
            "cite": (f"《{para['doc']}》第 {para['page']} 页 ¶{para['para']}" if para else None),
            "quote": (para["text"][:80] + ("…" if para and len(para["text"]) > 80 else "") if para else None),
        })
    covered = [s for s in sentences if s["level"] == "强"]
    weak = [s for s in sentences if s["level"] == "弱"]
    missing = [s for s in sentences if s["level"] == "无"]

    return {
        "script": script_name,
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "reference": {
            "chars_per_second": round(CHARS_PER_SECOND, 3),
            "budget_seconds": BUDGET_SECONDS,
            "target_chars": list(TARGET_CHARS),
            "baseline": "吉尔戈成片：784 字（手册记 785）→ 176.1 秒",
        },
        "totals": {
            "chapters": len(chapters),
            "chars": total,
            "sentences": len(sentences),
            "estimated_seconds": round(est_seconds, 1),
            "planned_shots": sum(c["shots"] for c in chapter_rows),
        },
        "verdicts": verdicts,
        "chapters": chapter_rows,
        "risks": {
            "high_risk": risk_hits,
            "allowed_layer": allowed_hits[:12],
            "digits": digit_hits,
            "uncertain": uncertain_hits,
        },
        "citations": {
            "docs": len(docs),
            "paragraphs": len(index),
            "strong": len(covered),
            "weak": len(weak),
            "missing": len(missing),
            "coverage": round(len(covered) / len(sentences), 3) if sentences else 0.0,
            "sentences": sentences,
        },
    }


def render_markdown(qa: dict) -> str:
    t = qa["totals"]
    c = qa["citations"]
    lines = [
        "# 解说词体检",
        "",
        f"`{qa['script']}` · {qa['checked_at']} · 基准：{qa['reference']['baseline']}"
        f"（{qa['reference']['chars_per_second']} 字/秒）。",
        "",
        "## 结论",
        "",
    ]
    lines += [f"- {v}" for v in qa["verdicts"]]
    lines += [
        "",
        "## 一、字数与时长",
        "",
        f"- 章数 **{t['chapters']}**（要求 6）· 总字数 **{t['chars']}**（要求 760–800）· 句数 {t['sentences']}",
        f"- 估算时长 **{t['estimated_seconds']} 秒**（预算 {qa['reference']['budget_seconds']} 秒）",
        f"- 按 45 镜 × 4 秒的网格，这段解说大约要 **{t['planned_shots']} 个镜头**",
        "",
        "| 章 | 标题 | 字数 | 估时(秒) | 预计镜头 | 句数 |",
        "|---|---|---|---|---|---|",
    ]
    for ch in qa["chapters"]:
        lines.append(f"| {ch['index']} | {ch['title']} | {ch['chars']} | {ch['seconds']} | {ch['shots']} | {ch['sentences']} |")

    lines += ["", "## 二、TTS 与措辞风险", ""]
    r = qa["risks"]
    if r["high_risk"]:
        lines.append(f"**高风险 {len(r['high_risk'])} 处**（可能被 TTS 拦，或超出手册的事实边界）：")
        lines.append("")
        lines.append("| 词 | 所在句 |")
        lines.append("|---|---|")
        for hit in r["high_risk"]:
            lines.append(f"| {hit['word']} | {hit['sentence']} |")
    else:
        lines.append("- 高风险措辞：没有 ✅")
    if r["digits"]:
        lines += ["", f"**阿拉伯数字 {len(r['digits'])} 处**（手册：数字要写中文读法，TTS 才不念错）：", "",
                  "| 数字 | 所在句 |", "|---|---|"]
        for hit in r["digits"]:
            lines.append(f"| {hit['digit']} | {hit['sentence']} |")
    if r["uncertain"]:
        lines += ["", f"**不确定措辞 {len(r['uncertain'])} 处**（片中要带不确定标记，别写成结论）：", ""]
        for hit in r["uncertain"][:20]:
            lines.append(f"- 「{hit['word']}」：{hit['sentence']}")
    if r["allowed_layer"]:
        lines += ["", "- 已写在手册允许层（勒死 / 麻布 / 弃尸 这一层）的措辞：" +
                  "、".join(sorted({h['word'] for h in r['allowed_layer']}))]

    lines += [
        "",
        "## 三、逐句出处映射",
        "",
        f"资料 {c['docs']} 份 / {c['paragraphs']} 段 · 对得上 **{c['strong']}** 句 · 弱匹配 {c['weak']} 句 · "
        f"没出处 **{c['missing']}** 句 · 覆盖率 {c['coverage'] * 100:.0f} %。",
        "",
        "> 相似度 ≥ 0.34 记「强」，< 0.18 记「无」。**相似不等于事实成立**，只是告诉你去哪一段核。",
        "",
        "| 章 | 分数 | 判定 | 句子 | 出处 | 资料原文 |",
        "|---|---|---|---|---|---|",
    ]
    if c["sentences"]:
        for s in c["sentences"]:
            quote = (s["quote"] or "—").replace("|", "/")
            lines.append(
                f"| {s.get('chapter', '-')} | {s['score']} | {s['level']} | {s['text']} | "
                f"{s['cite'] or '—'} | {quote} |"
            )
    else:
        lines.append("| — | — | — | （没检出句子） | — | — |")

    lines += [
        "",
        "## 已知误差",
        "",
        "- 语速基准取自吉尔戈成片（4.46 字/秒），换音色或换语速档就要重算；",
        "- 出处映射是字符二元组召回率：改写过的句子（换说法、加修饰）分数会偏低，"
        "**没出处不等于没来源**，只是没在资料里找到相似段落；",
        "- 风险词表是关键词匹配，会漏（同义改写）也会误报（「砍价」「刺骨」这种正常词）。",
    ]
    return "\n".join(lines)


def write_qa(out_dir: Path, qa: dict) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script-qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "剧本体检.md").write_text(render_markdown(qa), encoding="utf-8")
    return qa


def load_qa(out_dir: Path) -> Optional[dict]:
    p = Path(out_dir) / "script-qa.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="解说词体检")
    ap.add_argument("--script", required=True)
    ap.add_argument("--extracted-dir", default=None, help="放 *.json 段落文件的目录（做出处映射）")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    docs = []
    if args.extracted_dir:
        docs = [json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(Path(args.extracted_dir).glob("*.json"))]
    text = Path(args.script).read_text(encoding="utf-8")
    qa = qa_script(text, docs, script_name=Path(args.script).name)
    write_qa(Path(args.out), qa)
    print(json.dumps(qa["totals"], ensure_ascii=False, indent=2))
    for v in qa["verdicts"]:
        print(" -", v)
