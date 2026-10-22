#!/usr/bin/env python3
"""按真实配音的分句时间，自动规划 render.py 的 CUTS（每镜落在一个分句起点上）。

为什么需要它：45 镜 = 38 个动态镜头 + 7 张信息卡，规划网格是「每镜 4 秒」，
但真实配音里每个分句的长短差很多；切点必须落在分句停顿里（模板的
``clause_times.py --check-cuts`` 会核对 [clause_start-0.35, clause_start] 这个窗），
所以切点只能取「某个分句的起点」。人手动排容易顾此失彼，这里用 DP：
把 k 个镜头分给 m 个分句起点（m ≥ k），目标是最小化每镜时长与 4.0 秒的偏差，
同时保证每镜 2.2–6.5 秒、严格递增，最后一镜落在章末之内。

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

# 本片逐镜时长按用户脚本（5–9 s 量级，最长 S20 9 s）：以「成片秒」为目标，换算到
# 各章的收紧后配音秒（× tempo）再排；槽位 >6.5 成片秒的由 render 的乒乓循环兜底。
MIN_SHOT, MAX_SHOT = 2.4, 9.6    # 成片秒下限/上限
MAX_TAIL = 9.05                  # 章末最后一镜（含 0.55 s 段内呼吸；9.05+0.55 ≤ 9.6 ≤ 乒乓容量 9.74）


def plan_chapter(clauses: list[dict], shots: list[str], chapter_duration: float,
                 tempo: float = 1.0, film_targets: list[float] | None = None):
    """返回 [(cut_seconds, shot_id), ...]；cut_seconds 是章内偏移（收紧后配音秒），第一个固定为 0。

    film_targets：每镜在成片里的目标秒数（用户脚本时长）；成本按换算到成片秒的偏差算。
    """
    # 可切锚点 = 分句起点 + 各句前停顿的中点（pacing 铺开排版后，停顿可达 3 秒：
    # 画面在无人说话的呼吸里切换，check-cuts 的自适应窗口认这一类）
    raw_anchors = []
    for c in clauses:
        st = float(c["start"])
        gb = float(c.get("gap_before") or 0.0)
        if gb >= 0.6:
            raw_anchors.append(round(st - gb * 0.5, 2))
        raw_anchors.append(round(st, 2))
    starts = sorted({0.0, *(a for a in raw_anchors if a >= 0.0)})
    k, m = len(shots), len(starts)
    if m < k:
        raise SystemExit(f"分句数 {m} 少于镜头数 {k}：这一章需要更多标点分句，先改解说词")
    INF = float("inf")
    tgt = film_targets or [5.0] * k
    lo, hi, tail_hi = MIN_SHOT * tempo, MAX_SHOT * tempo, MAX_TAIL * tempo

    def span(p: int, q: int | None) -> float:
        """镜头从分句起点 starts[p] 开始，到 starts[q]（q 为 None 表示章末）结束。

        第一镜的起点强制是 0（cut=0），所以 p==0 时从 0 算，而不是 starts[0]。
        """
        a = 0.0 if p == 0 else starts[p]
        return (chapter_duration if q is None else starts[q]) - a

    # dp[i][q]：镜头 0..i 已排好、且镜头 i 从分句 q 开始时的最小代价（只累计已经确定的镜头时长）
    dp = [[INF] * m for _ in range(k)]
    back = [[-1] * m for _ in range(k)]
    # 第一镜必须从章首开始（切点强制 0）：只允许 idx[0] == 0，防止 DP 把首镜起点
    # 漂到后面的分句上、让首镜真实时长脱离成本核算（2026-10-22 玛丽号 S19/S22 被撑到 10 s+）
    dp[0][0] = 0.0
    for i in range(1, k):
        for q in range(i, m):
            for p in range(i - 1, q):
                if dp[i - 1][p] == INF:
                    continue
                d = span(p, q)
                if not (lo <= d <= hi):
                    continue
                cost = dp[i - 1][p] + abs(d / tempo - tgt[i])
                if cost < dp[i][q]:
                    dp[i][q] = cost
                    back[i][q] = p
    best_cost, best_q = INF, -1
    for q in range(k - 1, m):
        if dp[k - 1][q] == INF:
            continue
        tail = span(q, None)
        if not (lo <= tail <= tail_hi):
            continue
        cost = dp[k - 1][q] + abs(tail / tempo - tgt[k - 1])
        if cost < best_cost:
            best_cost, best_q = cost, q
    if best_q < 0:
        raise SystemExit("这一章排不出合法切点：分句太长或太短，需要调整解说词的标点")

    idx = [0] * k
    q = best_q
    for i in range(k - 1, -1, -1):
        idx[i] = q
        q = back[i][q] if i else -1
    return [(0.0 if i == 0 else round(starts[idx[i]], 2), sid) for i, sid in enumerate(shots)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    story = json.loads((PROJ / "story.json").read_text())
    table = json.loads(TABLES.read_text())
    sys.path.insert(0, str(PROJ))
    import render  # noqa: E402  取逐章窗口排版（与 render.audio_layout 同一公式）
    durations = {cid: float(table[cid]["duration"]) for cid in table}
    tempos = {r["id"]: r["tempo"] for r in render.chapter_layout(story["chapters"], durations)}
    shots: dict[str, list[str]] = {}
    targets: dict[str, list[float]] = {}
    for shot in sorted(story["shots"], key=lambda s: s["start"]):
        shots.setdefault(shot["narration_id"], []).append(shot["id"])
        targets.setdefault(shot["narration_id"], []).append(float(shot["duration"]))
    blocks, summary = [], []
    for cid in sorted(shots):
        duration = float(table[cid]["duration"])
        tempo = tempos[cid]
        rows = plan_chapter(table[cid]["clauses"], shots[cid], duration, tempo, targets[cid])
        body = ", ".join(f"({t},'{sid}','')" for t, sid in rows)
        blocks.append(f"    '{cid}': [{body}],")
        film = " ".join(f"{sid}@{t / tempo:.2f}s" for t, sid in rows)
        summary.append(f"{cid}（配音 {duration:6.2f}s / tempo {tempo:.3f} / {len(shots[cid])} 镜）: {film}")
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
