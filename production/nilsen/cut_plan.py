#!/usr/bin/env python3
"""按分句停顿把 render.py 的 CUTS 重对一遍（第 8 步的"手工活"，做成可复算的）。

规则（都来自 新题目开工手册.md 第 8 步 + 闸门）：
- 每章第一个切点是 0；
- 其余每个切点必须落在某个分句起点前 0.35 s 的停顿窗内 → 这里统一取 **起点 − 0.20 s**；
- 每段 ≤ 6.7 s（Agnes 素材只有 7 s）；
- 信息卡那一段至少 3.2 s，否则观众读不完；动画镜头至少 1.8 s，否则像闪屏；
- 本章的镜头必须全部用到、各用一次、按编号顺序（render.py 的 make_edl 也会再断言一遍）。

做法：把每个合法切点当候选，动态规划枚举「选哪 n−1 个切点」，代价取各段时长与理想值的偏差平方和，
所以结果是"在停顿窗允许的前提下尽量均匀"，而不是硬套 4 秒网格。

    python3 production/nilsen/cut_plan.py           # 打印 CUTS 与每段时长
    python3 production/nilsen/cut_plan.py --write    # 直接写回 render.py 的 CUTS 块
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEAD = 0.20          # 画面比新句子早 0.20 秒换（手册建议 0.15，这里留出窗内余量）
MAX_SEG = 6.7
MIN_SEG = 1.8
MIN_CARD = 3.2
TOL = 1e-6



# 每个镜头对位到解说的哪一句（句子必须逐字出现在该章解说里）。
# 切点会尽量贴在这一句的起点前 0.2 s；DP 同时保证顺序单调、每段 ≤ 6.7 s、信息卡 ≥ 3.2 s。
ANCHORS = {
    "S01": "一九八三年二月", "S02": "下水道堵了", "S03": "还有几截像手指的",
    "S04": "再报警", "S05": "当晚警察上了顶楼", "S06": "开门的男人只说了一句",
    "S07": "东西都在衣柜里", "S08": "是一具还是两具",
    "S09": "他叫丹尼斯·尼尔森", "S10": "一九四五年生在苏格兰渔港",
    "S11": "祖父死在北海的渔船上", "S12": "母亲让他看最后一眼",
    "S13": "他在军队食堂学过屠宰", "S14": "退伍后在就业中心当保安", "S15": "晚上去酒吧找人",
    "S16": "动手是从一九七八年冬天开始的", "S17": "他把人带回自己家", "S18": "凌晨趁人睡着",
    "S19": "之后他把人洗干净", "S20": "一放就是几个星期", "S21": "房子有花园",
    "S22": "他就架火", "S23": "往火里扔橡胶盖味道",
    "S24": "一九八一年十月", "S25": "没有花园", "S26": "他改成把东西煮散",
    "S27": "邻居投诉有味道", "S28": "说房子结构有问题", "S29": "二月八号疏通公司来了人",
    "S30": "井盖被挪过位",
    "S31": "他配合得让办案的人心里发毛", "S32": "说不准确切的人数",
    "S33": "整晚的供词在法庭上被逐字念了", "S34": "辩方说他有精神疾病",
    "S34": "一九八三年十月二十四日", "S35": "中央刑事法院开庭", "S36": "活下来的人出庭作证",
    "S37": "有人被掐醒后逃出来报过警", "S38": "十一月四日",
    "S39": "一九九四年十二月", "S40": "二〇一八年五月",
    "S41": "他在监狱医院死于手术后并发症", "S42": "八个死者连名字都没有",
    "S43": "第一个死的是个十四岁男孩", "S44": "一九九〇年拿照片去问",
    "S45": "有些人失踪",
}


def clause_start_of(clauses, phrase):
    """在分句表里找这句话的起点（找不到就返回 None，退回均匀分布）。"""
    for c in clauses:
        if phrase and phrase in c["text"]:
            return c["start"]
    return None


def chapter_plan(cid, clauses, duration, shots, is_card):
    """返回 [(cut, shot_id)]：锚点句尽量贴住，段长硬约束由 DP 保证。"""
    cands = sorted({round(c["start"] - LEAD, 2) for c in clauses if c["start"] - LEAD > 0.4})
    cands = [t for t in cands if t <= duration - MIN_SEG + TOL]
    n = len(shots)
    target = duration / n
    # 期望起点：有锚点用锚点（提前 0.2 s 换画面），没锚点退回均匀网格
    want = [0.0]
    for sid in shots[1:]:
        st = clause_start_of(clauses, ANCHORS.get(sid, ""))
        want.append(None if st is None else round(max(0.0, st - LEAD), 2))

    def seg_ok(i, start, end):
        lo = MIN_CARD if is_card[i] else MIN_SEG
        return (lo - TOL) <= (end - start) <= (MAX_SEG + TOL)

    INF = float("inf")
    m = len(cands)
    dp = [[(INF, -1)] * m for _ in range(n)]
    for j, t in enumerate(cands):
        if seg_ok(0, 0.0, t):
            dp[1][j] = ((t - (want[1] if want[1] is not None else t)) ** 2, -1)
    for k in range(2, n):
        for j, t in enumerate(cands):
            best = (INF, -1)
            for i in range(j):
                prev = dp[k - 1][i]
                if prev[0] == INF or not seg_ok(k - 1, cands[i], t):
                    continue
                w = want[k]
                # 没锚点的镜头：既贴均匀网格，也给自己留出的最小时长兜底
                cost = prev[0] + ((t - w) ** 2 if w is not None else (t - cands[i] - target) ** 2)
                if cost < best[0]:
                    best = (cost, i)
            dp[k][j] = best
    # 末镜的锚点代价已经在 dp[n-1] 里；这里只要求尾段长度合法（太长会空转、太短像闪屏）
    last_ok = [(dp[n - 1][j][0], j) for j in range(m)
               if dp[n - 1][j][0] < INF and seg_ok(n - 1, cands[j], duration)]
    if not last_ok:
        raise SystemExit(f"{cid}: 配不出来（{n} 镜 / {len(cands)} 个合法切点 / {duration:.1f} 秒）——减镜头或加长配音")
    j = min(last_ok)[1]
    chosen = []
    for k in range(n - 1, 0, -1):
        chosen.append(cands[j])
        j = dp[k][j][1]
    chosen = [0.0] + list(reversed(chosen))
    assert len(chosen) == n and all(b > a for a, b in zip(chosen, chosen[1:])), (cid, chosen)
    return [(t, sid) for t, sid in zip(chosen, shots)]


def main() -> int:
    write = "--write" in sys.argv
    story = json.loads((HERE / "story.json").read_text())
    table = json.loads((HERE / "audio" / "clause-times.json").read_text())
    shots_by_chapter: dict[str, list[dict]] = {}
    for s in story["shots"]:
        shots_by_chapter.setdefault(s["narration_id"], []).append(s)

    blocks, report = [], []
    for cid, shots in shots_by_chapter.items():
        info = table[cid]
        plan = chapter_plan(cid, info["clauses"], info["duration"], [s["id"] for s in shots],
                            [s["kind"] == "graphic" for s in shots])
        cuts = ", ".join(f"({t},'{{}}','')" .format(sid) for (t, sid) in plan)
        blocks.append(f"    '{cid}': [{cuts}],")
        edges = [t for t, _ in plan] + [info["duration"]]
        segs = [round(b - a, 2) for a, b in zip(edges, edges[1:])]
        worst = max(segs)
        cards = [(s["id"], seg) for s, seg in zip(shots, segs) if s["kind"] == "graphic"]
        lines = []
        for (t, sid), seg, shot in zip(plan, segs, shots):
            sp = ANCHORS.get(sid, "")
            at = clause_start_of(info["clauses"], sp)
            lines.append(f"      {sid} {t:6.2f}s +{seg:4.2f}s {'卡' if shot['kind'] == 'graphic' else '  '}"
                         f" 锚点 {'%.2fs' % at if at is not None else '—'} 偏移 "
                         f"{(t - (at - LEAD)):+.2f}" if at is not None else
                         f"      {sid} {t:6.2f}s +{seg:4.2f}s {'卡' if shot['kind'] == 'graphic' else '  '} 无锚点")
        report.append(f"  {cid} {info['duration']:.2f}s → {len(plan)} 段 最长 {worst:.2f}s "
                      f"卡片 {[f'{i}:{s}s' for i, s in cards]}" + "\n" + "\n".join(lines))
        assert worst <= MAX_SEG + TOL, (cid, segs)
        assert all(x >= MIN_SEG - TOL for x in segs), (cid, segs)

    text = "CUTS = {\n" + "\n".join(blocks) + "\n}"
    render_py = HERE / "render.py"
    src = render_py.read_text(encoding="utf-8")
    if write:
        import re
        new = re.sub(r"CUTS = \{.*?\n\}", text, src, count=1, flags=re.S)
        if new == src:
            raise SystemExit("render.py 里没找到 CUTS 块，未改动")
        render_py.write_text(new, encoding="utf-8")
        print("render.py 的 CUTS 已写入；记得跑 clause_times.py --check-cuts")
    else:
        print(text)
        print("\n".join(report))
        print("（上面是预览，加 --write 才写回 render.py）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
