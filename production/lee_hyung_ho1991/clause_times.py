#!/usr/bin/env python3
"""按 TTS 停顿把解说词的每个分句对到时间上（离线，不用 ASR）。

tighten_pauses.py 只把过长静音缩短到 0.35 秒，不添加语音或改变文字；Edge TTS
通常会在标点处留下可测停顿。这里用动态规划从检测到的停顿中挑出一条单调路径，使每个分句
的实际时长与“按字数摊开的期望时长”最接近（对数比的平方和最小）。

输出 audio/clause-times.json；plan_cuts.py 将切点落在实测停顿内，render.py 的字幕在跳过 ASR 时也使用此分句时间。

    python3 production/lee_hyung_ho1991/clause_times.py               # 对时间，写 audio/clause-times.json
    python3 production/lee_hyung_ho1991/clause_times.py --check-cuts  # 核对 render.py 的 CUTS 是否都落在分句停顿窗内
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


def _proportional_fallback(clauses, weights, dur, lead, spans):
    """Keep chapter timing usable when short TTS pauses are not long enough for DP."""
    count = len(clauses)
    speech_end = max(lead + 0.1, dur - 0.25)
    speech = max(0.1, speech_end - lead)
    total_weight = float(weights.sum())
    boundaries = [lead]
    snapped = []
    for index in range(1, count):
        target = lead + speech * float(weights[:index].sum()) / total_weight
        candidates = []
        for pause_start, pause_len in spans:
            pause_end = pause_start + pause_len
            if (boundaries[-1] + 0.05 < pause_end < speech_end - 0.05
                    and abs(pause_end - target) <= 0.55):
                candidates.append((abs(pause_end - target), pause_end))
        if candidates:
            boundary = min(candidates)[1]
            snapped.append(True)
        else:
            boundary = target
            snapped.append(False)
        lower = boundaries[-1] + 0.05
        upper = speech_end - (count - index) * 0.05
        boundaries.append(max(lower, min(upper, boundary)))
    boundaries.append(speech_end)
    rows = []
    for index, clause in enumerate(clauses):
        a, b = boundaries[index], boundaries[index + 1]
        rows.append({
            'i': index, 'start': round(a, 2), 'end': round(b, 2), 'text': clause,
            'chars_per_second': round(float(weights[index]) / max(0.05, b - a), 2),
            'pause_snap': (True if index == 0 else snapped[index - 1]),
            'alignment': 'pause-aware-proportional',
        })
    return dur, rows


def align(text, x):
    dur = len(x) / RATE
    lead, spans = pauses(x)
    clauses = [c for c in re.split(PUNCT, text) if c]
    weights = np.array([max(1, len(re.sub(r'[^\u3400-\u9fffA-Za-z0-9]', '', c))) for c in clauses], float)
    if not clauses:
        raise ValueError('Narration contains no alignable clauses')
    count, pause_count = len(clauses), len(spans)
    if pause_count < count - 1:
        return _proportional_fallback(clauses, weights, dur, lead, spans)
    speech = max(0.1, dur - lead - 0.25 - sum(d for _, d in spans))
    rate = speech / weights.sum()                      # 秒/字
    starts = [lead] + [s + d for s, d in spans]       # 候选分句开始时间：片头或静音结束
    ends = [s for s, _ in spans] + [dur]              # 候选分句结束时间：静音开始或片尾
    INF = float('inf')
    dp = [[INF] * (pause_count + 1) for _ in range(count)]
    back = [[-1] * (pause_count + 1) for _ in range(count)]

    def cost(k, a, b):
        actual = b - a
        expected = weights[k] * rate
        if actual <= 0.05:
            return INF
        return math.log(actual / expected) ** 2

    for j in range(pause_count + 1):
        if j == pause_count and count > 1:
            continue
        dp[0][j] = cost(0, starts[0], ends[j])
    for k in range(1, count):
        for j in range(k, pause_count + 1):
            if j == pause_count and k != count - 1:
                continue
            best, best_i = INF, -1
            for i in range(k - 1, j):
                if dp[k - 1][i] == INF:
                    continue
                candidate = dp[k - 1][i] + cost(k, starts[i + 1], ends[j])
                if candidate < best:
                    best, best_i = candidate, i
            dp[k][j], back[k][j] = best, best_i
    if not math.isfinite(dp[count - 1][pause_count]):
        return _proportional_fallback(clauses, weights, dur, lead, spans)
    j = pause_count
    path = [None] * count
    for k in range(count - 1, -1, -1):
        path[k] = j
        j = back[k][j]
    rows = []
    for k in range(count):
        a = starts[0] if k == 0 else starts[path[k - 1] + 1]
        b = ends[path[k]]
        rows.append({'i': k, 'start': round(a, 2), 'end': round(b, 2), 'text': clauses[k],
                     'chars_per_second': round(float(weights[k]) / (b - a), 2),
                     'pause_snap': True, 'alignment': 'energy-pause-dp'})
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


def main():
    story = json.loads((HERE / 'story.json').read_text())
    root = HERE.parents[1]
    result = {}
    for ch in story['chapters']:
        dur, rows = align(ch['text'], decode(HERE / 'audio' / (ch['id'] + '.mp3')))
        result[ch['id']] = {'duration': round(dur, 3), 'alignment': rows[0].get('alignment', 'energy-pause-dp'), 'clauses': rows}
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
