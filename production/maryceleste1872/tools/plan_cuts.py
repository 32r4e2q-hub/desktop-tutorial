#!/usr/bin/env python3
"""按真实配音的分句时间 + 台词锚定表，规划 render.py 的 CUTS（每镜对准自己的口播）。

2026-10-23 改版（用户反馈「解说词跟片段没完全咬合、内容不匹配」）：旧版是纯
时长 DP，只把镜头往 4 秒目标上凑，**不知道哪句台词属于哪个镜头**——于是
「日志停在十天前」配到了航海仪器、「妻子和女儿」配到了货舱。新版改为
SHOT_PLAN 台词锚定：每镜绑定它该覆盖的分句序号（来自用户脚本的镜头职责），
切点落在该镜首句起点前 0.12–0.32 s 的停顿里（画先入、话后到）。

用法::

    python3 production/maryceleste1872/tools/plan_cuts.py             # 写回 render.py 的 CUTS
    python3 production/maryceleste1872/tools/plan_cuts.py --dry-run   # 只打印，不改文件

前置：audio/clause-times.json 已经由 clause_times.py 生成（TTS 已收紧、对过时间）。
改完务必跑一次：python3 production/maryceleste1872/clause_times.py --check-cuts
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
TABLES = PROJ / "audio" / "clause-times.json"

# —— 台词锚定表：每镜覆盖的分句序号（0 起），按口播顺序严格连续、无缝无重 ——
# 依据=用户脚本的镜头职责（story.json shots.purpose）与解说词分句内容逐句对照：
# N02：妻子女儿在 S04 舷梯；「还有七名船员」给 S05B 拉缆绳；酒精桶台词才给 S05A
#      （旧版把 S05A 排在船员前面，货物/船员顺序切反了）；
# N04：日志台词必须落在 S15 日志特写；空绳架 S14 压轴「自己离开还是被带走」
#      （旧版把 S15 垫在结尾两问下）；N03/N06 同理逐句对齐。
SHOT_PLAN: dict[str, list[tuple[str, list[int]]]] = {
    "N01": [("S01", [0, 1]), ("S02", [2, 3, 4, 5])],
    "N02": [("S03", [0, 1, 2, 3]), ("S04", [4, 5]), ("S05B", [6, 7]), ("S05A", [8, 9])],
    "N03": [("S06", [0, 1, 2]), ("S07A", [3, 4, 5, 6, 7]), ("S07B", [8, 9]), ("S08", [10, 11]), ("S09", [12])],
    "N04": [("S10", [0]), ("S11", [1]), ("S12", [2, 3, 4]), ("S13", [5, 6, 7]),
            ("S15", [8, 9, 10, 11]), ("S14", [12, 13, 14, 15])],
    "N05": [("S16", [0, 1, 2]), ("S17", [3, 4]), ("S18A", [5, 6, 7]), ("S18B", [8, 9, 10])],
    "N06": [("S19", [0, 1, 2]), ("S20", [3, 4, 5, 6]), ("S21", [7, 8, 9, 10])],
    "N07": [("S22", [0, 1, 2, 3]), ("S23", [4, 5]), ("S24", [6, 7, 8]), ("S25", [9, 10]), ("S26", [11, 12])],
    "N08": [("S27", [0, 1, 2]), ("S28", [3, 4, 5, 6])],
}


def plan_chapter(clauses: list[dict], shot_groups: list[tuple[str, list[int]]]):
    """返回 [(cut_seconds, shot_id), ...]；cut 是章内偏移，第一镜固定 0。

    切点=该镜首句起点前的停顿里（lead 0.12–0.32 s，句前停顿时长自适应），
    画面比话音早入一点，听感上「说到哪、切到哪」。
    """
    n = len(clauses)
    seen: list[int] = [i for _sid, idxs in shot_groups for i in idxs]
    if seen != list(range(n)):
        raise SystemExit(f"SHOT_PLAN 分句覆盖不是 0..{n - 1} 的严格序列：{seen}")
    rows = []
    for slot, (sid, idxs) in enumerate(shot_groups):
        if slot == 0:
            rows.append((0.0, sid))
            continue
        first = clauses[idxs[0]]
        gap = float(first.get("gap_before") or 0.0)
        lead = min(0.32, max(0.12, gap * 0.5))
        cut = float(first["start"]) - lead
        prev_end = float(clauses[idxs[0] - 1]["end"])
        cut = round(max(cut, prev_end + 0.06), 2)
        rows.append((cut, sid))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    table = json.loads(TABLES.read_text())
    blocks, summary = [], []
    for cid in sorted(SHOT_PLAN):
        clauses = table[cid]["clauses"]
        rows = plan_chapter(clauses, SHOT_PLAN[cid])
        body = ", ".join(f"({t},'{sid}','')" for t, sid in rows)
        blocks.append(f"    '{cid}': [{body}],")
        bits = []
        for j, (t, sid) in enumerate(rows):
            idxs = SHOT_PLAN[cid][j][1]
            spoken = "/".join(clauses[i]["text"][:8] for i in idxs)
            bits.append(f"{sid}@{t:.2f}[{spoken}]")
        summary.append(f"{cid}（{len(clauses)} 句 / {len(rows)} 镜）: " + " ".join(bits))
    text = "CUTS = {\n" + "\n".join(blocks) + "\n}"
    print("\n".join(summary))
    if args.dry_run:
        print("\n" + text)
        return 0
    source = RENDER.read_text()
    new_source, count = re.subn(r"CUTS = \{.*?\n\}", text, source, count=1, flags=re.S)
    if count != 1:
        raise SystemExit("render.py 里找不到唯一的 CUTS 块，先看一眼文件")
    RENDER.write_text(new_source)
    print(f"render.py 的 CUTS 已更新（{len(summary)} 章）；记得跑 clause_times.py --check-cuts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
