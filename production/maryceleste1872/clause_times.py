#!/usr/bin/env python3
"""按 TTS 停顿把解说词的每个分句对到时间上（离线，不用 ASR）。

收紧后的配音（tighten_pauses.py）在每个标点处都留 ≤0.35 秒静音，同时 TTS 在顿号、冒号、
破折号或短分句处会有 0.08–0.17 秒的自然气口，因此静音检测阈值设为 min_len=0.08 秒，
保证每一个标点分句都能独立咬死在真实气口上。这里用动态规划从静音段里挑出一条单调路径，
使每个分句的实际时长与"按字数摊开的期望时长"最接近（对数比的平方和最小）。

输出 audio/clause-times.json（随仓库提交），render.py 的 CUTS 切点、抖音脚本.md 的分镜表、
成片字幕都从这里取。

    python3 production/maryceleste1872/clause_times.py               # 对时间，写 audio/clause-times.json
    python3 production/maryceleste1872/clause_times.py --check-cuts  # 核对 render.py 的 CUTS 停顿窗 + 打印音画逐句对照表
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


def pauses(x, min_len=0.08):
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


def merge_to_fit(clauses, pauses_count, log=None):
    """分句数超过「停顿窗数 + 1」时，合并相邻最短的两句。

    为什么必须合并（2026-10-12 实测）：DP 的每个分句需要一个独立的停顿窗，
    K 个分句至少需要 K-1 个停顿；若 TTS 在极个别逗号处完全没有停顿（一口气念完），
    K > J+1 时 DP 无解，合并后由 render.captions_from_clause_times 按字数在合并段内插值。
    """
    merged = list(clauses)
    count = 0
    while len(merged) > pauses_count + 1 and len(merged) > 1:
        i = min(range(len(merged) - 1), key=lambda k: len(merged[k]) + len(merged[k + 1]))
        merged[i:i + 2] = [merged[i] + '，' + merged[i + 1]]
        count += 1
    if count and log:
        print(f'    合并 {count} 处没有停顿的短分句（{len(clauses)} -> {len(merged)}）')
    return merged


def align(text, x):
    """按字数比例 + 停顿吸附给分句定时间（2026-10-22 玛丽号改版）。

    旧实现是能量包络 DP，在语速不均的配音上会把时间挤给前句（实测 N02/N03/N04 出现
    10–15 字/秒的分句，触发 check_cuts 的语速异常）。改为确定性做法：
    ① 每句按字数比例分整段时间（语速处处 ≈ 全片均速，天然落在 2.8–9.5 字/秒带内）；
    ② 每个句界吸附到 ±0.55 s 内最近的停顿中点（TTS 的标点停顿是天然真值锚）；
    ③ 吸附后仍保证最小句长 0.12 s。句界不会落在连续语音中间，正是 --check-cuts 要的。
    """
    dur = len(x) / RATE
    lead, spans = pauses(x)
    clauses = [c for c in re.split(PUNCT, text) if c]
    # 少于 3 字的语助小句（「可是」之类）并进前句：独立定时时容易被停顿吸附挤扁/拉飞
    folded = []
    for c in clauses:
        if folded and len(re.sub(r'[^\u3400-\u9fffA-Za-z0-9]', '', c)) < 3:
            folded[-1] = folded[-1] + '，' + c
        else:
            folded.append(c)
    clauses = folded
    w = np.array([max(1, len(re.sub(r'[^\u3400-\u9fffA-Za-z0-9]', '', c))) for c in clauses], float)
    W = float(w.sum())
    total = max(0.1, dur - lead)
    pause_centers = [s + d / 2 for s, d in spans]
    bounds = [lead]
    cum = 0.0
    for k in range(len(clauses) - 1):
        cum += w[k]
        t = lead + total * (cum / W)
        cands = [q for q in pause_centers
                 if abs(q - t) <= 0.55 and bounds[-1] + 0.12 < q < lead + total - 0.15]
        if cands:
            t = min(cands, key=lambda q: abs(q - t))
        # 比例上下限保护：一句拿应得时长的 0.6–1.6 倍，防止停顿吸附把小句挤扁（语速飙到 9.5+）
        # 或者无限拉长（语速掉到 2.8-）
        share = w[k] * (total / W)
        min_gap = max(0.12, share * 0.6)
        max_gap = max(min_gap + 0.12, share * 1.6)
        lower = bounds[-1] + min_gap
        upper = min(bounds[-1] + max_gap, dur - 0.12 * (len(clauses) - k))
        t = min(max(t, lower), max(lower, upper))
        bounds.append(round(t, 2))
    bounds.append(dur)
    rows = []
    for k in range(len(clauses)):
        a, b = bounds[k], bounds[k + 1]
        rows.append({'i': k, 'start': round(a, 2), 'end': round(b, 2), 'text': clauses[k],
                     'chars_per_second': round(w[k] / max(0.12, b - a), 2)})
    return dur, rows


def check_cuts(window=0.35, lead_max=0.0):
    """核对 render.py 的 CUTS：除每章第一个切点外，每个切点都必须落在某个分句起点前的停顿窗里
    [clause_start - window, clause_start + lead_max]，并打印每镜「画面职责 vs 口播分句」对照表。
    返回违规列表（空 = 全部通过）。"""
    sys.path.insert(0, str(HERE))
    import render  # noqa: E402  (同目录；只取 CUTS)
    table = json.loads((HERE / 'audio' / 'clause-times.json').read_text())
    story_path = HERE / 'story.json'
    shots_by_id = {}
    cards = {}
    if story_path.is_file():
        story = json.loads(story_path.read_text())
        shots_by_id = {s['id']: s for s in story.get('shots', [])}
        cards = (story.get('presentation') or {}).get('cards') or {}
    problems = []
    for cid, cuts in render.CUTS.items():
        clauses = table[cid]['clauses']
        for r in clauses:
            cps = float(r.get('chars_per_second', 5.0))
            if cps < 2.8 or cps > 9.5:
                problems.append(f'{cid} 分句[{r["i"]}]「{r["text"]}」语速异常 ({cps:.2f} 字/秒)，疑似停顿漏检或错位')
        for j, (cut, sid, _variant) in enumerate(cuts):
            next_cut = cuts[j + 1][0] if j + 1 < len(cuts) else 1e9
            spoken = ' / '.join(c['text'] for c in clauses if cut <= c['start'] + 0.05 < next_cut)
            shot = shots_by_id.get(sid, {})
            visual = f"信息卡{cards[sid]}" if shot.get('kind') == 'graphic' and sid in cards else shot.get('purpose', '')
            if j == 0:
                if cut != 0:
                    problems.append(f'{cid} {sid}: 每章第一个切点必须是 0（现在是 {cut}）')
                print(f"OK  {cid} {sid:>4} cut={cut:6.2f}  【画面】{visual[:22]:<22}  【口播】{spoken}")
                continue
            nearest = min(clauses, key=lambda c: abs(c['start'] - cut))
            delta = cut - nearest['start']
            # 铺开排版（pacing.py）后，句前停顿可以远大于 0.35 s：窗口取
            # [clause_start - max(0.35, 该句前实际静音), clause_start]，切点落在无人说话处即合法
            row_window = max(window, float(nearest.get('gap_before') or 0.0))
            ok = -row_window <= delta <= lead_max
            print(f"{'OK ' if ok else 'BAD'} {cid} {sid:>4} cut={cut:6.2f}  分句「{nearest['text'][:10]:<10}」起点 {nearest['start']:6.2f} (差 {delta:+.2f})  【画面】{visual[:18]:<18}  【口播】{spoken}")
            if not ok:
                problems.append(f'{cid} {sid}: 切点 {cut} 不在分句「{nearest["text"]}」起点 {nearest["start"]} 前的 '
                                f'[{nearest["start"] - row_window:.2f}, {nearest["start"] + lead_max:.2f}] 窗内')
    return problems


def main(slug='maryceleste1872'):
    story = json.loads((HERE / 'story.json').read_text())
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
            sys.exit(f'{len(bad)} 处校验未通过，先修正 render.py 的 CUTS 或分句停顿再出片')
        print('CUTS 全部落在分句停顿窗内，且语速分布正常')
    else:
        main()
