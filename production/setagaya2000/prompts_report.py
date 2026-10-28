#!/usr/bin/env python3
"""把分镜与生成收据整理成两份可交付文档。

* ``镜头提示词与生成记录.md`` —— 29 个镜头逐条列出：时间轴、运镜、角色、自动拼接后的完整提示词
  （STYLE + 角色设定 + 镜头描述 + NEGATIVE）、旁白、Agnes 回执（task/url/sha256/bytes/尺寸/时长）、
  接触表路径、复核状态。交付要求里的"提示词与生成记录"就是这份。
* ``qa/生成记录.csv`` —— 同上内容的表格版，方便用表格软件核对。

用法::

    python3 production/setagaya2000/prompts_report.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "production"))
sys.path.insert(0, str(HERE))


def load_generate():
    spec = importlib.util.spec_from_file_location("setagaya2000_generate", HERE / "generate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def clock(seconds: float) -> str:
    return f"{int(seconds)//60:02d}:{int(seconds)%60:02d}"


def main() -> int:
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    results_path = HERE / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else {}
    receipts = results.get("shots", {})
    gen = load_generate()

    lines = [
        f"# {story['title']}",
        "",
        "## 生成记录总览",
        "",
        f"- 模型：`{story['model']}`（免费档 720P 源片），成片 1920×1080 · {story['fps']}fps · "
        f"{story['target_duration']} 秒",
        f"- 镜头数：{len(story['shots'])}；每条提示词自动以【STYLE】开头、以【NEGATIVE】结尾，"
        "出现人物时自动拼接【角色设定】",
        f"- 生成状态：{sum(1 for s in story['shots'] if receipts.get(s['id'], {}).get('status') == 'completed')}"
        f"/{len(story['shots'])} 条已生成并逐字节校验",
        f"- 收据文件：`results.json`（video_url / task_id / sha256 / bytes / request_hash）",
        "",
        "## 逐镜提示词（已拼接，可直接复制重跑）",
        "",
    ]
    rows = []
    for shot in story["shots"]:
        receipt = receipts.get(shot["id"], {})
        start, end = shot["start"], shot["start"] + shot["duration"]
        lines += [
            f"### {shot['id']}｜{clock(start)}—{clock(end)}｜{shot['duration']} 秒｜{shot['camera']}",
            "",
            f"- 段：{shot['narration_id']}　风格变体：{shot['style_variant']}"
            f"　角色：{'、'.join(shot['characters']) or '—'}　seed：{shot['seed']}",
            f"- 旁白：{shot['narration']}",
            f"- 状态：{receipt.get('status', '未生成')}"
            + (f"　sha256：`{receipt.get('sha256')}`　bytes：{receipt.get('bytes')}"
               f"　源片：{receipt.get('inspection', {}).get('width')}×"
               f"{receipt.get('inspection', {}).get('height')}"
               f"　时长：{receipt.get('inspection', {}).get('duration_seconds')}s"
               if receipt.get("status") == "completed" else ""),
            f"- 接触表：`{receipt.get('inspection', {}).get('contact_sheet', '—')}`"
            f"　人工复核：{receipt.get('visual_review', 'pending')}",
            "",
            "```text",
            gen.full_prompt(story, shot),
            "```",
            "",
        ]
        rows.append({
            "镜号": shot["id"], "开始": clock(start), "结束": clock(end), "秒数": shot["duration"],
            "段": shot["narration_id"], "运镜": shot["camera"],
            "角色": "、".join(shot["characters"]), "seed": shot["seed"],
            "旁白": shot["narration"], "状态": receipt.get("status", "未生成"),
            "sha256": receipt.get("sha256", ""), "bytes": receipt.get("bytes", ""),
            "源片尺寸": (f"{receipt.get('inspection', {}).get('width')}x"
                          f"{receipt.get('inspection', {}).get('height')}"
                          if receipt.get("status") == "completed" else ""),
            "接触表": receipt.get("inspection", {}).get("contact_sheet", ""),
            "人工复核": receipt.get("visual_review", "pending"),
        })

    lines += ["## 事实边界", ""] + [f"- {item}" for item in story["fact_boundary"]] + [""]
    lines += ["## 来源", ""] + [f"- [{s['title']}]({s['url']})：{s['supports']}" for s in story["sources"]]
    (HERE / "镜头提示词与生成记录.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    (HERE / "qa").mkdir(parents=True, exist_ok=True)
    with (HERE / "qa" / "生成记录.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    done = sum(1 for row in rows if row["状态"] == "completed")
    print(f"WROTE 镜头提示词与生成记录.md + qa/生成记录.csv（{done}/{len(rows)} 条已完成）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
