#!/usr/bin/env python3
"""按 TTS 停顿把解说词的每个分句对到时间上（离线，不用 ASR）。

收紧后的配音（tighten_pauses.py）在每个标点处都留 0.35 秒静音，所以
"分句边界 = 某个静音段的起点"几乎总成立；TTS 偶尔会在长数字串里多停一下，
因此静音段数 ≥ 分句数。这里用动态规划从静音段里挑出一条单调路径，使每个分句
的实际时长与"按字数摊开的期望时长"最接近（对数比的平方和最小）。

输出 audio/clause-times.json（随仓库提交），render.py 的 CUTS 切点、抖音脚本.md 的分镜表、
成片字幕（ASR 覆盖不足时）都从这里取。

    python3 production/btk/clause_times.py               # 对时间，写 audio/clause-times.json
    python3 production/btk/clause_times.py --check-cuts  # 核对 render.py 的 CUTS 是否都落在分句停顿窗内
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


def pauses(x, min_len=0.18):
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


def align(text, x):
    """Align text clause boundaries to real audio pauses with monotonic dynamic programming.

    A few punctuation boundaries may have no detectable pause, or TTS may pause inside
    a clause. Sequence alignment therefore permits merging text clauses and ignoring
    extra pauses instead of inventing impossible timestamps.
    """
    dur = len(x) / RATE
    lead, spans = pauses(x)
    clauses = [c.strip() for c in re.findall(r'[^，。！？；：、—]+[，。！？；：、—]*', text) if c.strip()]
    weight = lambda c: max(1, len(re.sub(r'[^\u3400-\u9fffA-Za-z0-9]', '', c)))
    weights = [weight(c) for c in clauses]
    total_weight = max(1, sum(weights))
    text_bounds = []
    running = 0
    for w in weights[:-1]:
        running += w
        text_bounds.append(running / total_weight)

    gap_total = sum(d for _, d in spans)
    speech_total = max(0.1, dur - lead - gap_total)
    pause_bounds = []
    prior_gap = 0.0
    for start, length in spans:
        active_before = max(0.0, start - lead - prior_gap)
        pause_bounds.append((start, length, min(1.0, active_before / speech_total)))
        prior_gap += length

    # dp[i][j] consumes i text boundaries and j pause boundaries.
    nt, na = len(text_bounds), len(pause_bounds)
    inf = float('inf')
    dp = [[inf] * (na + 1) for _ in range(nt + 1)]
    back = [[None] * (na + 1) for _ in range(nt + 1)]
    dp[0][0] = 0.0
    skip_text, skip_pause = 0.055, 0.018
    for i in range(nt + 1):
        for j in range(na + 1):
            here = dp[i][j]
            if here == inf:
                continue
            if i < nt and here + skip_text < dp[i + 1][j]:
                dp[i + 1][j] = here + skip_text
                back[i + 1][j] = (i, j, 'text')
            if j < na and here + skip_pause < dp[i][j + 1]:
                dp[i][j + 1] = here + skip_pause
                back[i][j + 1] = (i, j, 'pause')
            if i < nt and j < na:
                mismatch = text_bounds[i] - pause_bounds[j][2]
                cost = here + 3.0 * mismatch * mismatch
                if cost < dp[i + 1][j + 1]:
                    dp[i + 1][j + 1] = cost
                    back[i + 1][j + 1] = (i, j, 'match')
    i, j = nt, na
    matched = []
    while i or j:
        step = back[i][j]
        if step is None:
            break
        pi, pj, action = step
        if action == 'match':
            matched.append((pi, pj))
        i, j = pi, pj
    matched.reverse()

    rows = []
    prev_text = -1
    prev_pause = -1
    for text_index, pause_index in matched:
        group = ''.join(clauses[prev_text + 1:text_index + 1])
        start = lead if prev_pause < 0 else pause_bounds[prev_pause][0] + pause_bounds[prev_pause][1]
        end = pause_bounds[pause_index][0]
        if group and end > start:
            rows.append({'i': len(rows), 'start': round(start, 2), 'end': round(end, 2),
                         'text': group, 'chars_per_second': round(weight(group) / (end - start), 2)})
        prev_text, prev_pause = text_index, pause_index
    group = ''.join(clauses[prev_text + 1:])
    start = lead if prev_pause < 0 else pause_bounds[prev_pause][0] + pause_bounds[prev_pause][1]
    if group and dur > start:
        rows.append({'i': len(rows), 'start': round(start, 2), 'end': round(dur, 2),
                     'text': group, 'chars_per_second': round(weight(group) / (dur - start), 2)})
    if not rows:
        rows = [{'i': 0, 'start': round(lead, 2), 'end': round(dur, 2),
                 'text': ''.join(clauses), 'chars_per_second': round(total_weight / max(.1, dur - lead), 2)}]
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


def main(slug='btk'):
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
