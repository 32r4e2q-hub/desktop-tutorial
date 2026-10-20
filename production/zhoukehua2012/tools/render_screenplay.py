#!/usr/bin/env python3
"""用 story.json + render.CUTS 重写 screenplay.md 里「会变的那一半」。

screenplay.md 是给合作者看的剧本：六段解说 + 45 镜分镜表 + 内容边界 + 公开来源。
前两部分随内容/切点变化，后两部分是人工写的原则与来源，不能被脚本覆盖。
所以这里的做法是：把旧文件里「## 内容边界」「## 公开来源」及其后的内容原样保留，
前面的解说与分镜表按当前 story.json / render.py / audio/clause-times.json 重排。

    python3 production/zhoukehua2012/tools/render_screenplay.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ))
import render  # noqa: E402  (同目录，只取 CUTS / 章节布局)

STORY = PROJ / "story.json"
CLAUSES = PROJ / "audio" / "clause-times.json"
DOC = PROJ / "screenplay.md"

KEEP_FROM = "## 内容边界"


def main() -> int:
    story = json.loads(STORY.read_text(encoding="utf-8"))
    table = json.loads(CLAUSES.read_text(encoding="utf-8"))
    tempo = 0.0
    manifest = json.loads((PROJ / "audio" / "manifest.json").read_text(encoding="utf-8"))
    used = sum(len(v) for v in render.CUTS.values())
    assert used == len(story["shots"]), "CUTS 与镜头数不一致"

    old = DOC.read_text(encoding="utf-8") if DOC.exists() else ""
    keep = old[old.index(KEEP_FROM):] if KEEP_FROM in old else ""

    lines = [
        f"# {story['title']} · 剧本与来源",
        "",
        "三分钟横版（16:9 · 1920×1080 · 30 fps · 180 秒）中文悬疑解说短片。",
        "画面为写实 3D CGI 动画情景重现（智谱 CogVideoX-Flash 免费档生成），全片常驻「AI动画情景重现 · 非新闻影像」。",
        "本片不做真实人物肖像还原：周克华与办案民警只以背影、剪影、手出现；受害者只以物件与聚合数字致意。",
        "",
        "> 本文件由 `tools/render_screenplay.py` 从 `story.json`（解说词）与 `render.py`（CUTS）重排；",
        "> 口播、成片字幕、`抖音脚本.md`、`audio/manifest.json` 用的是同一份数据。",
        "",
        "## 六段解说",
        "",
    ]
    for chapter in story["chapters"]:
        length = len(re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", chapter["text"]))
        lines += [f"### {chapter['id']} · {chapter['title']}（{length} 字）", "", chapter["text"], ""]

    lines += ["## 镜头表（按出场顺序）", "",
              "| # | 镜头 | 类型 | 口播（这一镜在说什么） | 画面职责 | 运镜 |",
              "|---|---|---|---|---|---|"]
    order = 0
    for chapter in story["chapters"]:
        cid = chapter["id"]
        clauses = table[cid]["clauses"]
        cuts = render.CUTS[cid]
        duration = float(table[cid]["duration"])
        for i, (start, sid, _variant) in enumerate(cuts):
            shot = next(s for s in story["shots"] if s["id"] == sid)
            end = cuts[i + 1][0] if i + 1 < len(cuts) else duration
            spoken = " / ".join(c["text"] for c in clauses
                                if start - 0.02 <= c["start"] < end - 0.02) or "（无口播）"
            order += 1
            kind = "信息卡" if shot["kind"] == "graphic" else "动态"
            lines.append(f"| {order} | {sid} | {kind} | {spoken} | {shot['purpose']} | {shot['camera']} |")
    lines += ["", f"共 {order} 镜；`CUTS` 由 `alignment.json` 生成，每一镜的起点都落在口播分句的停顿上。", ""]

    DOC.write_text("\n".join(lines) + ("\n" + keep if keep else ""), encoding="utf-8")
    print(f"screenplay.md 已重写：{order} 镜 / {len(story['chapters'])} 章；内容边界与来源原样保留")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
