#!/usr/bin/env python3
"""把本片所有面向观众的中文文字抽出来，跑一遍去 AI 味预检。

抽的内容：30 条解说 + 钩子大字 + 金色注释 + 封面两行字 + 发布文案正文。
结果写进 production/<slug>/qa/deai-report.md；有硬拦截（假对比句壳）时退出码 1。

用法::

    python3 production/mihashi2006/editorial/check_narration.py
    python3 production/mihashi2006/editorial/check_narration.py --quiet   # 只写报告

规则来源：liuhaisi2026212-maker/taishang-laojun 的去AI味规则与 ai_tell_linter.py（CC BY-NC 4.0）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
LINTER = HERE / "ai_tell_linter.py"
QA = PROJECT / "qa" / "deai-report.md"


def collect() -> list[tuple[str, str]]:
    story = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))
    presentation = story.get("presentation", {})
    items: list[tuple[str, str]] = []
    for shot in story["shots"]:
        items.append((f"{shot['id']} 解说", shot["narration"].strip()))
    for hook in presentation.get("hooks", []):
        items.append((f"{hook['id']} 钩子", hook["text"].strip()))
    for note in presentation.get("explainers", []):
        items.append((f"{note.get('id', 'E')} 注释", note["text"].strip()))
    cover = presentation.get("cover_text", "")
    if cover:
        items.append(("封面大字", cover.strip()))
    publish = PROJECT / "抖音发布文案.md"
    if publish.is_file():
        for line in publish.read_text(encoding="utf-8").splitlines():
            text = line.strip()
            if text and not text.startswith("#") and not text.startswith("-"):
                items.append(("发布文案", text))
    return [(label, text) for label, text in items if text]


def main() -> int:
    parser = argparse.ArgumentParser(description="本片文字去 AI 味预检")
    parser.add_argument("--quiet", action="store_true", help="不在终端打印明细，只写报告")
    args = parser.parse_args()

    items = collect()
    body = "\n".join(text for _, text in items)
    proc = subprocess.run(
        [sys.executable, str(LINTER), "-", "--format", "json"],
        input=body, text=True, capture_output=True, check=False,
    )
    if proc.returncode not in (0, 1):
        sys.stderr.write(proc.stderr or "linter 运行失败\n")
        return 2
    report = json.loads(proc.stdout or "{}")
    hard = report.get("hard_blocks", []) or []
    soft = report.get("soft_warnings", []) or []

    lines = [
        "# 去 AI 味预检报告（自动生成）",
        "",
        f"- 检查文本：{len(items)} 条（30 镜解说 + 钩子 + 注释 + 封面 + 发布文案）",
        f"- 硬拦截（假对比句壳）：{len(hard)} 处",
        f"- 软提醒（空转词/句式）：{len(soft)} 处",
        "- 规则来源：liuhaisi2026212-maker/taishang-laojun（CC BY-NC 4.0），清单见 editorial/README.md",
        "",
    ]
    if hard:
        lines += ["## 硬拦截（必须改）", ""]
        for hit in hard:
            lines.append(f"- 第 {hit.get('line')} 行 · {hit.get('pattern')}：{hit.get('text')}")
    else:
        lines += ["硬拦截：0。没有出现「不是X而是Y」「你以为X其实Y」这类句壳。", ""]
    if soft:
        lines += ["## 软提醒（逐条判断）", ""]
        for hit in soft:
            lines.append(f"- 第 {hit.get('line')} 行 · {hit.get('pattern') or hit.get('term')}：{hit.get('text')}")
    else:
        lines += ["软提醒：0。空转词清单未命中；仍需人念一遍确认语气。", ""]
    numbered = ["## 送检原文（按行号）", ""]
    numbered += [f"{i}. [{label}] {text}" for i, (label, text) in enumerate(items, 1)]
    QA.parent.mkdir(parents=True, exist_ok=True)
    QA.write_text("\n".join(lines + numbered) + "\n", encoding="utf-8")

    if not args.quiet:
        print(f"送检 {len(items)} 条 → 硬拦截 {len(hard)} / 软提醒 {len(soft)}")
        for hit in hard:
            print(f"  [硬] {hit.get('pattern')}：{hit.get('text')}")
        for hit in soft:
            print(f"  [软] {hit.get('pattern') or hit.get('term')}：{hit.get('text')}")
        print(f"报告：{QA.relative_to(PROJECT.parents[1])}")
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
