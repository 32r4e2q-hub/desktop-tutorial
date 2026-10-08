#!/usr/bin/env python3
"""按 audio/clause-times.json 重对 render.py 的 CUTS（切点 = 分句起点 − 0.15 s）。

狂犬病模式的手册规定：脚手架给的 4 秒均匀网格只是起点，拿到配音后必须重对；
每个切点都要落在某个分句起点前的停顿窗里（`clause_times.py --check-cuts` 守着），
每一段画面在成片时间轴上 ≤ 6.3 s（Agnes 素材只有 7 s）。

用法::

    python3 production/unterweger/tools/retime_cuts.py            # 只打印建议的 CUTS
    python3 production/unterweger/tools/retime_cuts.py --write    # 写回 render.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
LEAD = 0.15          # 画面比新句子早 0.15 s 换（手册：分句起点 − 0.15 s）
WINDOW_BACK = 0.90   # 允许向前最多借 0.90 s
WINDOW_FWD = 0.30    # 允许向后最多 0.30 s
MIN_SEG = 0.90       # 单段画面下限（raw 秒）
MAX_SEG_FILM = 6.30  # 单段画面上限（成片秒）


def load():
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    table = json.loads((HERE / "audio" / "clause-times.json").read_text(encoding="utf-8"))
    shots = {}
    for shot in story["shots"]:
        shots.setdefault(shot["narration_id"], []).append(shot["id"])
    return story, table, shots


def plan_chapter(cid, clauses, duration, shot_ids, tempo):
    targets = [c["start"] for c in clauses]
    n = len(shot_ids)
    cuts = [0.0]
    for k in range(1, n):
        ideal = k * duration / n
        candidates = [s for s in targets if ideal - WINDOW_BACK <= s <= ideal + WINDOW_FWD]
        if not candidates:
            candidates = sorted(targets, key=lambda s: abs(s - ideal))[:1]
        start = min(candidates, key=lambda s: abs(s - ideal))
        cut = round(start - LEAD, 2)
        # 约束：单调、离上一段够远、且不超过素材能覆盖的长度
        cut = max(cut, cuts[-1] + MIN_SEG)
        limit = (duration - MIN_SEG) - max(0, n - 1 - k) * MIN_SEG
        cut = min(cut, limit)
        film_len = (cut - cuts[-1]) / tempo
        if film_len > MAX_SEG_FILM:  # 极少见：往前挪到更近的分句
            cut = round(cuts[-1] + MAX_SEG_FILM * tempo, 2)
        cuts.append(round(cut, 2))
    return [(c, sid, "") for c, sid in zip(cuts, shot_ids)]


def render_cuts_block(cuts_by_chapter):
    lines = ["CUTS = {"]
    for cid, entries in cuts_by_chapter.items():
        body = ", ".join(f"({t:g},'{sid}','')" for t, sid, _v in entries)
        lines.append(f"    '{cid}': [{body}],")
    lines.append("}")
    return "\n".join(lines)


def main():
    story, table, shots = load()
    tempo_cache = {}
    cuts_by_chapter = {}
    for chapter in story["chapters"]:
        cid = chapter["id"]
        row = table[cid]
        duration = row["duration"]
        # 成片里的章长 = duration / tempo；tempo 由 render.py 的 audio_layout 决定，
        # 这里按同一公式算一遍（180 − 0.6 − 6.0 − 5 × 1.08 = 168 秒可用）
        total = sum(table[c["id"]]["duration"] for c in story["chapters"])
        tempo = total / 168.0
        tempo_cache[cid] = tempo
        cuts_by_chapter[cid] = plan_chapter(cid, row["clauses"], duration, shots[cid], tempo)
    block = render_cuts_block(cuts_by_chapter)
    print(block)
    print(f"\n变速比 {total / 168.0:.3f}")
    for cid, entries in cuts_by_chapter.items():
        seg = [(entries[i + 1][0] - entries[i][0]) / tempo_cache[cid] for i in range(len(entries) - 1)]
        seg.append((table[cid]["duration"] - entries[-1][0]) / tempo_cache[cid])
        flag = "OK" if max(seg) <= MAX_SEG_FILM + 1e-6 else "TOO LONG"
        print(f"{cid}: {len(entries)} 段，成片最长一段 {max(seg):.2f}s（{flag}），合计 {sum(seg):.2f}s")
    if "--write" in sys.argv:
        path = HERE / "render.py"
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"^CUTS = \{.*?^\}", block, text, flags=re.M | re.S)
        path.write_text(text, encoding="utf-8")
        print(f"\n已写回 {path}")
    else:
        print("\n（只打印；加 --write 写回 render.py）")


if __name__ == "__main__":
    main()
