#!/usr/bin/env python3
"""把「镜头 → 口播分句」的对齐表写成 render.py 的 CUTS（音画同步的唯一来源）。

为什么不用 tools/plan_cuts.py：那个脚本只保证「每镜尽量接近 4 秒、切点落在停顿里」，
它不知道这一镜的画面在说什么。本片 45 镜里有信息卡、有跨城市的实拍感镜头，
按秒数摊开会把「南京的银行」摊到「长沙枪击」上。这里改成人工指定落点：
``alignment.json`` 里每条 ``[镜头号, 分句序号]`` 表示这一镜从该分句的起点开始，
到下一镜的起点结束 —— 切点天然落在停顿上（分句起点就是气口），
画面和口播讲的是同一件事。

    python3 production/zhoukehua2012/tools/plan_alignment.py            # 写回 render.py 的 CUTS
    python3 production/zhoukehua2012/tools/plan_alignment.py --dry-run  # 只打印
    python3 production/zhoukehua2012/tools/plan_alignment.py --audit    # 只检查时长/唯一性

改完务必跑：python3 production/zhoukehua2012/clause_times.py --check-cuts
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
RENDER = PROJ / "render.py"
CLAUSES = PROJ / "audio" / "clause-times.json"
ALIGN = PROJ / "alignment.json"

LEAD = 0.05             # 切点比口播分句起点早 50 ms：分句起点是「开口」的时刻，
                        # 成片按 1/30 s 对齐到帧，若正好落在起点上会被四舍五入到字里，
                        # 耳朵听到的就是话被剪断。提前 50 ms 落进停顿里，check-cuts 的
                        # [-0.35, 0] 窗也认。
MIN_SHOT = 1.4          # 允许的短镜（信息插入/快切），低于这个值就是排错了
MAX_SHOT = 8.5          # 单镜上限；超过说明分句太少或落点排错


def load():
    table = json.loads(CLAUSES.read_text(encoding="utf-8"))
    align = json.loads(ALIGN.read_text(encoding="utf-8"))
    chapters = [k for k in align if not k.startswith("_")]
    return table, align, chapters


def plan(table, align, chapters):
    out = {}
    problems = []
    totals = []
    for cid in chapters:
        entry = table[cid]
        clauses = entry["clauses"]
        duration = float(entry["duration"])
        pairs = align[cid]
        cuts = []
        for shot, index in pairs:
            if not 0 <= index < len(clauses):
                problems.append(f"{cid} {shot}: 分句序号 {index} 超出 0–{len(clauses) - 1}")
                continue
            start = 0.0 if not cuts else max(0.0, float(clauses[index]["start"]) - LEAD)
            cuts.append((round(start, 2), shot))
        if not cuts:
            continue
        starts = [c[0] for c in cuts]
        if starts != sorted(starts) or len(set(starts)) != len(starts):
            problems.append(f"{cid}: 切点没有严格递增（{starts}）")
        span_end = duration
        for i, (start, shot) in enumerate(cuts):
            end = cuts[i + 1][0] if i + 1 < len(cuts) else span_end
            length = end - start
            if length < MIN_SHOT:
                problems.append(f"{cid} {shot}: 只有 {length:.2f}s（< {MIN_SHOT}s）")
            elif length > MAX_SHOT:
                problems.append(f"{cid} {shot}: 长达 {length:.2f}s（> {MAX_SHOT}s）")
        totals.append((cid, [round((cuts[i + 1][0] if i + 1 < len(cuts) else span_end) - cuts[i][0], 2)
                             for i in range(len(cuts))]))
        out[cid] = cuts
    return out, problems, totals


def shots_in(plan_dict):
    seen = []
    for cid, cuts in plan_dict.items():
        seen += [s for _, s in cuts]
    return seen


def render_block(plan_dict):
    lines = ["CUTS = {"]
    for cid, cuts in plan_dict.items():
        body = ", ".join(f"({t:.2f},'{sid}','')" for t, sid in cuts)
        lines.append(f"    '{cid}': [{body}],")
    lines.append("}")
    return "\n".join(lines)


def write_back(plan_dict):
    source = RENDER.read_text(encoding="utf-8")
    block = render_block(plan_dict)
    new, count = re.subn(r"^CUTS = \{.*?^\}", block, source, flags=re.S | re.M)
    if count != 1:
        raise SystemExit("render.py 里找不到唯一的 CUTS 块，拒绝写回")
    RENDER.write_text(new, encoding="utf-8")
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()

    table, align, chapters = load()
    plan_dict, problems, totals = plan(table, align, chapters)

    all_shots = shots_in(plan_dict)
    duplicates = sorted({s for s in all_shots if all_shots.count(s) > 1})
    if duplicates:
        problems.append("重复使用镜头: " + ",".join(duplicates)
                        + "（本片规定每镜只用一次；要换次序请改落点，不要复用）")

    story_shots = {s["id"] for s in json.loads((PROJ / "story.json").read_text(encoding="utf-8"))["shots"]}
    missing = sorted(story_shots - set(all_shots))
    extra = sorted(set(all_shots) - story_shots)
    if missing:
        problems.append("没有安排落点的镜头: " + ",".join(missing))
    if extra:
        problems.append("story.json 里不存在的镜头: " + ",".join(extra))

    for cid, lengths in totals:
        print(f"{cid}  镜头 {len(lengths)} 个 · 时长 " + " ".join(f"{x:.2f}" for x in lengths))

    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    if args.audit:
        print("对齐表结构正常（时长、唯一性、镜头清单都对得上）")
        return 0

    if args.dry_run:
        print(render_block(plan_dict))
        return 0

    write_back(plan_dict)
    print("render.py 的 CUTS 已按 alignment.json 重写")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
