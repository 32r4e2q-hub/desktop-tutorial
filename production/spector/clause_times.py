#!/usr/bin/env python3
"""按 TTS 停顿把解说词的每个分句对到时间上（离线，不用 ASR）。

收紧后的配音（tighten_pauses.py）在每个标点处都留 0.35 秒静音，所以
"分句边界 = 某个静音段的起点"几乎总成立；TTS 偶尔会在长数字串里多停一下，
因此静音段数 ≥ 分句数。这里用动态规划从静音段里挑出一条单调路径，使每个分句
的实际时长与"按字数摊开的期望时长"最接近（对数比的平方和最小）。

输出 audio/clause-times.json（随仓库提交），render.py 的 CUTS 切点、抖音脚本.md 的分镜表、
成片字幕（ASR 覆盖不足时）都从这里取。

    python3 production/spector/clause_times.py               # 对时间，写 audio/clause-times.json
    python3 production/spector/clause_times.py --check-cuts  # 核对 render.py 的 CUTS 是否都落在分句停顿窗内
"""
import json, math, re, subprocess, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
RATE = 48000; HOP = 480
PUNCT = r'[，。！？；：、—]+'


def decode(p):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-ac', '1', '-ar', str(RATE), '-f', 's16le', '-'],
                         check=True, capture_output=True).stdout
    return np.frombuffer(out, '<i2').astype(np.float32) / 32768


def pauses(x, min_len=0.10):  # 男声 voice-01 停顿更短：0.12 时 N04/N05 静音段少于分句数 DP 退化；停顿普查后定 0.10（六章皆可行）
    n = len(x) // HOP * HOP
    rms = np.sqrt((x[:n].reshape(-1, HOP) ** 2).mean(1)); quiet = rms < 0.01
    spans = []; s = None; lead = 0.0
    for i, q in enumerate(quiet):
        if not q: lead = i * 0.01; break
    for i, q in enumerate(quiet):
        if q and s is None: s = i
        if not q and s is not None:
            if (i - s) * 0.01 >= min_len and s > 0: spans.append((s * 0.01, (i - s) * 0.01))
            s = None
    return lead, spans


def align(text, x, min_len=0.30):
    """分块 DP 混合对齐：≥min_len 的可靠停顿切出语音块，块间 DP 分配连续分句
    （允许空块=句内戏剧停顿），块内按字数权重比例切分。
    纯停顿 DP 在男声快语速段（N05 物理段）会把句内微停顿误当边界，产出 25 字/秒
    这类不可能值——那正是字幕与声音错位的根源；比例切分保证单调且速度平滑。"""
    dur = len(x) / RATE
    lead, spans = pauses(x, min_len)
    clauses = [c for c in re.split(PUNCT, text) if c]
    w = [max(1, len(re.sub(r'[^\u3400-\u9fffA-Za-z0-9]', '', c))) for c in clauses]
    blocks = []; prev = lead
    for s0, d0 in spans:
        if s0 > prev + 0.02: blocks.append((prev, s0))
        prev = s0 + d0
    if prev < dur - 0.05: blocks.append((prev, dur))
    K, B = len(clauses), len(blocks)
    rate = sum(b - a for a, b in blocks) / sum(w)      # 秒/字
    EMPTY = 0.35
    INF = float('inf')
    dp = [[INF] * (K + 1) for _ in range(B + 1)]; back = [[-1] * (K + 1) for _ in range(B + 1)]
    dp[0][0] = 0.0
    import math
    for b in range(1, B + 1):
        a0, b0 = blocks[b - 1]; db = b0 - a0
        for k in range(0, K + 1):
            best = INF; bj = -1
            for j in range(max(0, k - K), k + 1):
                if dp[b - 1][j] == INF: continue
                if j == k:
                    c = EMPTY                       # 空块：停顿落在某个分句内部
                else:
                    expect = rate * sum(w[j:k])
                    c = math.log(db / expect) ** 2
                v = dp[b - 1][j] + c
                if v < best: best = v; bj = j
            dp[b][k] = best; back[b][k] = bj
    if dp[B][K] == INF: raise RuntimeError('分块 DP 不可行')
    assign = []; b, k = B, K
    while b > 0:
        j = back[b][k]; assign.append((b - 1, j, k)); b, k = b - 1, j
    assign.reverse()
    rows = []; idx = 0
    for bi, j, k in assign:
        a0, b0 = blocks[bi]; db = b0 - a0
        if j == k: continue
        sw = sum(w[j:k]); t = a0
        for ci in range(j, k):
            frac = w[ci] / sw
            rows.append({'i': ci, 'start': round(t, 2), 'end': round(t + frac * db, 2),
                         'text': clauses[ci], 'chars_per_second': round(w[ci] / max(0.05, frac * db), 2)})
            t += frac * db
    return dur, rows


def check_cuts(window=0.35, lead_max=0.0):
    """核对 render.py 的 CUTS：除每章第一个切点外，每个切点都必须落在某个分句起点前的停顿窗里
    [clause_start - window, clause_start + lead_max]。返回违规列表（空 = 全部通过）。"""
    sys.path.insert(0, str(HERE))
    import render  # noqa: E402  (同目录；只取 CUTS)
    table = json.loads((HERE / 'audio' / 'clause-times.json').read_text())
    problems = []
    for cid, cuts in render.CUTS.items():
        clauses = table[cid]['clauses']
        for j, (cut, sid, _variant) in enumerate(cuts):
            if j == 0:
                if cut != 0:
                    problems.append(f'{cid} {sid}: 每章第一个切点必须是 0（现在是 {cut}）')
                continue
            nearest = min(clauses, key=lambda c: abs(c['start'] - cut))
            delta = cut - nearest['start']
            ok = -window <= delta <= lead_max
            print(f"{'OK ' if ok else 'BAD'} {cid} {sid:>4} cut={cut:6.2f}  分句「{nearest['text'][:12]}」起点 {nearest['start']:6.2f}  差 {delta:+.2f}")
            if not ok:
                problems.append(f'{cid} {sid}: 切点 {cut} 不在分句「{nearest["text"]}」起点 {nearest["start"]} 前的 '
                                f'[{nearest["start"] - window:.2f}, {nearest["start"] + lead_max:.2f}] 窗内')
    return problems


def main(slug='spector'):
    story = json.loads((HERE / 'story.json').read_text())
    root = HERE.parents[1]
    result = {}
    for ch in story['chapters']:
        dur, rows = align(ch['text'], decode(HERE / 'audio' / (ch['id'] + '.mp3')))
        result[ch['id']] = {'duration': round(dur, 3), 'clauses': rows}
        print(ch['id'], f'dur {dur:.2f}')
        for r in rows:
            print(f"   {r['i']:2d} {r['start']:6.2f}-{r['end']:6.2f}  {r['chars_per_second']:4.1f}/s  {r['text']}")
    out = HERE / 'audio' / 'clause-times.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print('written', out)


if __name__ == '__main__':
    if '--check-cuts' in sys.argv:
        bad = check_cuts()
        if bad:
            print('\n'.join(bad), file=sys.stderr)
            sys.exit(f'{len(bad)} 个切点不在停顿窗内，先改 render.py 的 CUTS 再出片')
        print('CUTS 全部落在分句停顿窗内')
    else:
        main()
