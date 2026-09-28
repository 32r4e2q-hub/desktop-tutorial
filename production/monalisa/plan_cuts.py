"""为每一章找「既满足时长闸门、又最贴语义」的切法，并打印每镜覆盖哪几句解说。

用途：make_cuts.py 只按代价函数挑一组边界；边界挪动之后，画面与解说的对应关系会变，
所以这里把候选切法连同它覆盖的分句文字一起打印出来，供人（或代理）逐镜核对，
再去 build_story.py 里把「叙事职责」改成与之一致——这一步是长岛那部被指
「解说跟画面对不上」之后加的工序。

用法：python3 production/monalisa/plan_cuts.py
"""
import json
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_SLOT, MAX_SLOT = 2.05, 7.2
PREF = {"N01": [0, 3, 5, 7, 8, 10, 12, 15], "N02": [0, 5, 6, 8, 10, 13, 15], "N03": [0, 1, 3, 4, 5, 7, 9, 12], "N04": [0, 4, 6, 9, 11, 14, 15], "N05": [0, 2, 4, 8, 10, 11, 12, 15], "N06": [0, 1, 4, 7, 8, 10, 12]}


def feasible(points, duration, S):
    """枚举：从候选切点里选 S-1 个，使每段落在 [MIN_SLOT, MAX_SLOT]。"""
    out = []
    for combo in combinations(range(1, len(points)), S - 1):
        marks = [0.0] + [points[i] for i in combo] + [duration]
        lens = [round(b - a, 2) for a, b in zip(marks, marks[1:])]
        if all(MIN_SLOT <= x <= MAX_SLOT for x in lens):
            out.append((combo, marks, lens))
    return out


def main():
    ct = json.loads((HERE / "audio" / "clause-times.json").read_text())
    story = json.loads((HERE / "story.json").read_text())
    for ch in story["chapters"]:
        cid = ch["id"]
        clauses = ct[cid]["clauses"]
        dur = ct[cid]["duration"]
        ids = [s["id"] for s in story["shots"] if s["narration_id"] == cid]
        points = [round(c["start"] - 0.15, 2) for c in clauses]
        cands = feasible(points, dur, len(ids))
        if not cands:
            print(f"\n===== {cid}：没有全部落在 [{MIN_SLOT},{MAX_SLOT}] 的切法 → 该章需要改镜头数或改解说")
            continue

        def cost(combo):
            return sum(abs(a - b) for a, b in zip(combo, PREF[cid][1:]))

        cands.sort(key=lambda c: (cost(c[0]), max(l for l in c[2])))
        print(f"\n===== {cid}（{len(ids)} 镜 / {len(clauses)} 个分句 / {dur:.1f}s）"
              f"可行切法 {len(cands)} 种，语义偏移最小 {cost(cands[0][0])} =====")
        combo, marks, lens = cands[0]
        for k, sid in enumerate(ids):
            i0 = 0 if k == 0 else combo[k - 1]
            i1 = (combo[k] if k + 1 < len(ids) else len(clauses))
            text = "／".join(c["text"] for c in clauses[i0:i1])
            want = PREF[cid][k] if k == 0 else combo[k - 1]
            flag = "" if i0 == PREF[cid][k] else f"   ← 解说原拟从第 {PREF[cid][k]} 句开始"
            print(f"  {sid} [{marks[k]:5.2f}→{marks[k+1]:5.2f} {lens[k]:4.2f}s] "
                  f"分句{i0}-{i1-1}：{text[:46]}{flag}")


if __name__ == "__main__":
    main()
