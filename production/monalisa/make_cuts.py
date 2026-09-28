"""按 audio/clause-times.json 的停顿把 render.py 的 CUTS 重对一遍。

规则（与长岛那部一致，见 新题目开工手册.md 第 6 步）：
- 每个切点必须落在某个分句起点前的停顿窗里：cut = clause_start - 0.15；
- 每个镜头至少 2.05 秒（参考片 45 镜的最短槽位就是 2.05s，低于这个值画面会像闪屏）；
- 每个镜头至多用 7.2 秒（Agnes 每条素材 7 秒，超了就得放慢，render.py 的变速闸门只允许 1.33×）；
- 在此基础上**尽量**贴着 build_story.py 里定好的「这一镜从第几个分句开始」的语义对位；
  语义与最小时长冲突时，让边界挪到相邻的停顿上（挪动次数会打印出来，便于人工复核）。

用法：python3 production/monalisa/make_cuts.py            # 重写 render.py 的 CUTS
      python3 production/monalisa/make_cuts.py --dry     # 只打印方案
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_SLOT, MAX_SOFT, INF = 2.20, 7.5, float("inf")

# 语义首选：每章各镜从第几个分句开始（与 build_story.py 的 SHOTS 叙事职责一一对应）
PREF = {"N01": [0, 3, 5, 7, 8, 10, 12, 15], "N02": [0, 5, 6, 8, 10, 13, 15], "N03": [0, 1, 3, 4, 5, 7, 9, 12], "N04": [0, 4, 6, 9, 11, 14, 15], "N05": [0, 2, 4, 8, 10, 11, 12, 15], "N06": [0, 1, 4, 7, 8, 10, 16]}


def solve(clauses, duration, pref):
    """在「分句起点 - 0.15」这些候选切点里，选一组满足时长约束、且最贴语义的切法。"""
    starts = [round(c["start"] - 0.15, 2) for c in clauses]
    S, C = len(pref), len(clauses)
    dp = [[INF] * C for _ in range(S)]
    back = [[None] * C for _ in range(S)]
    for i in range(C):
        dp[0][i] = float(abs(i - pref[0]))
    for k in range(1, S):
        for i in range(1, C):
            for j in range(i):
                if dp[k - 1][j] == INF:
                    continue
                slot = starts[i] - starts[j]
                if slot < MIN_SLOT:
                    continue
                total = dp[k - 1][j] + abs(i - pref[k])
                if slot > MAX_SOFT:
                    total += 3.0 * (slot - MAX_SOFT) ** 2
                if total < dp[k][i]:
                    dp[k][i] = total
                    back[k][i] = j
    tail = [i for i in range(C) if dp[S - 1][i] < INF and duration - starts[i] >= MIN_SLOT]
    if not tail:
        raise SystemExit("没有可行切法：最小时长约束过严，考虑合并镜头")
    last = min(tail, key=lambda i: dp[S - 1][i])
    order = [last]
    for k in range(S - 1, 0, -1):
        order.append(back[k][order[-1]])
    order.reverse()
    if any(o is None for o in order):
        raise SystemExit("DP 回溯失败（存在不可达状态）")
    return order, starts


def main(dry=False):
    ct = json.loads((HERE / "audio" / "clause-times.json").read_text())
    story = json.loads((HERE / "story.json").read_text())
    per_chapter = {}
    for ch in story["chapters"]:
        group = [s for s in story["shots"] if s["narration_id"] == ch["id"]]
        per_chapter[ch["id"]] = [s["id"] for s in group]

    cuts, moved = {}, 0
    for cid, ids in per_chapter.items():
        order, starts = solve(ct[cid]["clauses"], ct[cid]["duration"], PREF[cid])
        marks = [0.0] + [starts[i] for i in order[1:]]
        ends = marks[1:] + [ct[cid]["duration"]]
        lens = [round(b - a, 2) for a, b in zip(marks, ends)]
        assert len(ids) == len(marks) == len(lens)
        moved += sum(1 for a, b in zip(order, PREF[cid]) if a != b)
        cuts[cid] = list(zip(marks, ids))
        print(f"{cid}  分句对位 {order}（首选 {PREF[cid]}）")
        print(f"     镜头 {' '.join(ids)}")
        print(f"     槽位 {lens}  最短 {min(lens)} 最长 {max(lens)}")
    print(f"总计 {sum(len(v) for v in cuts.values())} 镜；为凑最小时长挪动的边界 {moved} 处")

    if dry:
        return
    lines = ["CUTS = {"]
    for cid in sorted(cuts):
        body = ", ".join(f"({t:.2f},'{sid}','')" for t, sid in cuts[cid])
        lines.append(f"    '{cid}': [{body}],")
    lines.append("}")
    path = HERE / "render.py"
    text = path.read_text()
    i = text.index("CUTS = {")
    j = text.index("\n}\n", i) + 3
    path.write_text(text[:i] + "\n".join(lines) + "\n" + text[j:])
    print("render.py 的 CUTS 已重写")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
