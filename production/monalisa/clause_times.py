#!/usr/bin/env python3
"""按 TTS 停顿把解说词的每个分句对到时间上（离线，不用 ASR）。

收紧后的配音（tighten_pauses.py）在每个标点处都留 0.35 秒静音，所以
"分句边界 = 某个静音段的起点"几乎总成立；TTS 偶尔会在长数字串里多停一下，
因此静音段数 ≥ 分句数。这里用动态规划从静音段里挑出一条单调路径，使每个分句
的实际时长与"按字数摊开的期望时长"最接近（对数比的平方和最小）。

输出 audio/clause-times.json（随仓库提交），render.py 的 CUTS 切点、抖音脚本.md 的分镜表、
成片字幕（ASR 覆盖不足时）都从这里取。

    python3 production/monalisa/clause_times.py               # 对时间，写 audio/clause-times.json
    python3 production/monalisa/clause_times.py --check-cuts  # 核对 render.py 的 CUTS 是否都落在分句停顿窗内
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


def align_chunked(text, x, min_len=0.30):
    """【spector 版，保留作对照，本片不再用】分块 DP 混合对齐：≥min_len 的可靠停顿切出语音块，块间 DP 分配连续分句
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


def speech_end(x, threshold=0.01):
    """最后一个非静音 10 ms 块的结束时刻（收紧后的配音片尾还留着 0.25 s 静音）。"""
    n = len(x) // HOP * HOP
    rms = np.sqrt((x[:n].reshape(-1, HOP) ** 2).mean(1))
    loud = np.nonzero(rms >= threshold)[0]
    return (int(loud[-1]) + 1) * HOP / RATE if len(loud) else len(x) / RATE


def align_spanning(text, x, min_len=0.25, skip_penalty=0.04):
    """【对照用】跨停顿 DP：分句边界只落在停顿上、分句可跨句内停顿。
    缺点：TTS 在逗号处不停顿时（N05「细密的裂纹网，全部吻合」），两句挤在一个语音块里，它切不开。"""
    return align(text, x, min_len=min_len, split_penalty=float('inf'), inner_penalty=skip_penalty)


def align(text, x, min_len=0.25, inner_penalty=0.04, split_penalty=0.12, empty_penalty=1.0, snap=0.45):
    """分组 DP（本片，2026-09-26）：把「语音块」序列和「分句」序列同时切成一一对应的组。

    语音块 = 被 ≥min_len 的可靠停顿隔开的连续语音。一组 = m 个相邻语音块 ↔ r 个相邻分句：
      m>1：分句里有句内换气（「可这份活｜让他摸清了三件事」），每个被跨过的停顿罚 inner_penalty；
      r>1：TTS 在逗号处没停（「细密的裂纹网，全部吻合」），每个挤在块内的分句边界罚 split_penalty；
      r=0：语音块不属于任何分句（杂音），罚 empty_penalty（几乎不会用到）。
    代价 = Σ log(组内纯语音时长 / 期望时长)² + 罚分，期望时长 = 组内字数 × 全章纯语音语速。
    组内按字数比例摊时间（跳过组内停顿），再把边界吸附到 snap 秒内的组内停顿上。

    为什么要两种都允许：spector 的分块 DP 只允许 r≥1、m=1，句内换气那半句的时间会被当「空块」丢掉，
    下一句起点推迟 1.1–1.5 s（本片 N02 被算成 8.3 字/秒）；只允许 m≥1、r=1 的跨停顿 DP 又切不开
    逗号处没停顿的两句（N05 被算成 2.8 / 11.4 字/秒）。两种情况 TTS 都会出现。
    """
    dur = len(x) / RATE
    lead, spans = pauses(x, min_len)
    end_of_speech = max(speech_end(x), (spans[-1][0] + spans[-1][1] + 0.05) if spans else 0)
    clauses = [c for c in re.split(PUNCT, text) if c]
    w = [max(1, len(re.sub(r'[^\u3400-\u9fffA-Za-z0-9]', '', c))) for c in clauses]
    blocks = []; prev = lead
    for s0, d0 in spans:
        if s0 > prev + 0.02:
            blocks.append((prev, s0))
        prev = s0 + d0
    if end_of_speech > prev + 0.02:
        blocks.append((prev, end_of_speech))
    K, B = len(clauses), len(blocks)
    pure = [b - a for a, b in blocks]
    rate = sum(pure) / sum(w)                            # 秒/字（纯语音）
    INF = float('inf'); MAXM, MAXR = 5, 5
    wp = [0]
    for v in w:
        wp.append(wp[-1] + v)
    pp = [0.0]
    for v in pure:
        pp.append(pp[-1] + v)

    def group_cost(b0, b1, k0, k1):                     # 块 [b0,b1) ↔ 分句 [k0,k1)
        m, r = b1 - b0, k1 - k0
        if r == 0:
            return empty_penalty * m
        if split_penalty == INF and r > 1:
            return INF
        speech = pp[b1] - pp[b0]
        expected = rate * (wp[k1] - wp[k0])
        return math.log(speech / expected) ** 2 + inner_penalty * (m - 1) + split_penalty * (r - 1)

    dp = [[INF] * (K + 1) for _ in range(B + 1)]
    back = [[None] * (K + 1) for _ in range(B + 1)]
    dp[0][0] = 0.0
    for b1 in range(1, B + 1):
        for k1 in range(0, K + 1):
            best, arg = INF, None
            for m in range(1, min(MAXM, b1) + 1):
                b0 = b1 - m
                for r in range(0, min(MAXR, k1) + 1):
                    k0 = k1 - r
                    if dp[b0][k0] == INF:
                        continue
                    v = dp[b0][k0] + group_cost(b0, b1, k0, k1)
                    if v < best:
                        best, arg = v, (b0, k0)
            dp[b1][k1], back[b1][k1] = best, arg
    if dp[B][K] == INF:
        raise RuntimeError('分组 DP 不可行')
    groups = []; b1, k1 = B, K
    while b1 > 0:
        b0, k0 = back[b1][k1]; groups.append((b0, b1, k0, k1)); b1, k1 = b0, k0
    groups.reverse()

    def at(b0, b1, offset):                             # 组内第 offset 秒纯语音 → 时间轴
        for b in range(b0, b1):
            a, e = blocks[b]
            if offset <= e - a + 1e-9:
                return a + offset
            offset -= e - a
        return blocks[b1 - 1][1]

    rows = []
    for b0, b1, k0, k1 in groups:
        if k1 == k0:
            continue
        speech = pp[b1] - pp[b0]; total = wp[k1] - wp[k0]
        inner = [(blocks[b][1], blocks[b + 1][0]) for b in range(b0, b1 - 1)]   # 组内停顿 (开始, 结束)
        bounds = [blocks[b0][0]]
        for k in range(k0 + 1, k1):
            t = at(b0, b1, speech * (wp[k] - wp[k0]) / total)
            near = [p for p in inner if abs((p[0] + p[1]) / 2 - t) <= snap]
            if near:
                p = min(near, key=lambda q: abs((q[0] + q[1]) / 2 - t))
                bounds.append(p)                        # 吸附到停顿：上一句止于停顿开始、下一句起于停顿结束
            else:
                bounds.append((t, t))
        bounds.append(blocks[b1 - 1][1])
        for idx, k in enumerate(range(k0, k1)):
            a = bounds[idx] if idx == 0 else bounds[idx][1]
            e = bounds[idx + 1] if idx + 1 == len(bounds) - 1 else bounds[idx + 1][0]
            rows.append({'i': k, 'start': round(a, 2), 'end': round(e, 2), 'text': clauses[k],
                         'chars_per_second': round(w[k] / max(0.05, e - a), 2),
                         'group': f'{b1 - b0}块/{k1 - k0}句'})
    rows.sort(key=lambda r: r['i'])
    return dur, rows

def load_render():
    """按文件路径加载**本项目**的 render.py（模块名 monalisa_render）。
    以前是 `import render`：同一个进程里别的项目（dahlia / 脚手架模板）先 import 过 render 时，
    拿到的是别人的 CUTS——离线测试全量跑时就这样核错了对象。render.py 顶部的
    `from media import …` / `from build_audio import …` 也临时让它们解析到本目录。"""
    import importlib.util
    cached = sys.modules.get('monalisa_render')
    if cached is not None:
        return cached
    shared = ('media', 'build_audio')
    saved = {k: sys.modules.pop(k) for k in shared if k in sys.modules}
    sys.path.insert(0, str(HERE))
    try:
        spec = importlib.util.spec_from_file_location('monalisa_render', HERE / 'render.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules['monalisa_render'] = module
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop('monalisa_render', None)
        raise
    finally:
        sys.path.remove(str(HERE))
        for k in shared:
            sys.modules.pop(k, None)
        sys.modules.update(saved)
    return module


def check_cuts(window=0.35, lead_max=0.0):
    """核对 render.py 的 CUTS：除每章第一个切点外，每个切点都必须落在某个分句起点前的停顿窗里
    [clause_start - window, clause_start + lead_max]。返回违规列表（空 = 全部通过）。"""
    render = load_render()
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


def main(slug='monalisa'):
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
