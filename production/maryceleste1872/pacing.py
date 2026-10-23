#!/usr/bin/env python3
"""Sample-accurate narration pacing, v3.2: 只动真静音间隙，绝不切字。

v3.1 的切片重建（按行界切词边 + 硬拼）造成拼接爆点与字头字尾被啃（用户反馈
“卡顿、丢字吞音”）。v3.2 改为**连续波形上的间隙重映射**：

- 只在检测到的真静音核心（10ms 块 RMS<0.004）里做剪/插；辅音区一概不碰，
  字词边界零损失；剪切/插入点两侧各留静音余量 + 4ms 淡接，杜绝爆点；
- 句间停顿按层级设固定目标（逗号 0.22s / 分号 0.28s / 句号 0.55s /
  感叹 0.60s / 疑问 0.75s——“绳子断了”“都消失了”得 0.6s、“回答是无人知晓”得 0.75s）；
  句内 TTS 微洞 ≥100ms 收到 80ms，<100ms 原样保留（辅音尺度，不动）；
- 行界（clause_times DP）会漂进词中间：间隙核心只认「界域 ±窗口内、未被相邻
  行界认领、≥45ms 的最长静音段」；行时间改贴**真实语音块**（块间 <45ms 微洞
  并入；一行跨多块按字数比例切），语速/字幕/切点都以真实语音为准；
- 标点层级从 story.json 全文还原（行表文本被去标点，行尾字不可用）；
- 章内语速铺满交给 render.chapter_layout 的 atempo（TEMPO_MIN..MAX=0.78..1.15）：
  紧凑口播 + 短层级停顿 → 自动放慢语速与片段等长（悬疑语感），字幕/EDL 同步换算。
"""
from __future__ import annotations

import argparse
import json
import re
import wave
from pathlib import Path

import numpy as np

RATE = 48_000
MIN_LEN = 0.08

# 句间层级停顿目标（文件坐标秒；成片墙钟 ≈ 目标/tempo，更舒展）
GAP_PERIOD = 0.55      # 。；
GAP_EXCLAIM = 0.60     # ！——“绳子断了”“都消失了”
GAP_QUESTION = 0.75    # ？——“回答是无人知晓”
GAP_COMMA = 0.22       # ，、：
GAP_SEMI = 0.28        # 其他
GAP_HOOK_EXTRA = 0.15  # N03 i==8 后 / N08 i==2 后 补重
INTRA_HOLE_MAX = 0.08  # 句内微洞收紧到 ≤80ms（<100ms 原样保留）
SIL_RMS = 0.004        # 真静音核心阈值（辅音/送气不会误判）
BLOCK = 480            # 10ms
XFADE = 192            # 4ms 接缝淡接（静音区，防爆点）
BLOCK_MERGE = 0.045    # 语音块合并阈值（TTS 微洞 <45ms 不算断句）

TEMPO_MIN, TEMPO_MAX = 0.78, 1.15  # 与 render.chapter_layout 一致


def run(cmd):
    __import__('subprocess').run(cmd, check=True)


def silence_mask(samples: np.ndarray) -> np.ndarray:
    blocks = len(samples) // BLOCK
    m = (samples[:blocks * BLOCK].reshape(blocks, BLOCK) ** 2).mean(axis=1) ** 0.5
    return m < SIL_RMS


def cores_of(mask: np.ndarray, lo: int, hi: int):
    """[lo,hi) 样本区间内的真静音核心 [(c0,c1), ...]（样本坐标，夹紧到区域内）。"""
    out = []
    a, b = lo // BLOCK, (hi + BLOCK - 1) // BLOCK
    a = max(0, a); b = min(len(mask), b)
    run_start = None
    for i in range(a, b):
        if mask[i] and run_start is None:
            run_start = i
        elif not mask[i] and run_start is not None:
            out.append((run_start * BLOCK, i * BLOCK)); run_start = None
    if run_start is not None:
        out.append((run_start * BLOCK, b * BLOCK))
    clamped = []
    for c0, c1 in out:
        c0, c1 = max(c0, lo), min(c1, hi)
        if c1 > c0:
            clamped.append((c0, c1))
    return clamped


def xfadeslice(samples: np.ndarray, start: int, end: int) -> np.ndarray:
    seg = samples[start:end].copy()
    n = min(XFADE, len(seg) // 2)
    if n > 0:
        w = np.linspace(0.0, 1.0, n, dtype=np.float32)
        seg[:n] *= w
        seg[-n:] *= w[::-1]
    return seg


def remap_gap(samples: np.ndarray, mask: np.ndarray, lo: int, hi: int,
              target: float, out: list):
    """把 [lo,hi) 的静音间隙重映射到 target 秒；out 收集输出段。返回长度增量（样本）。"""
    cores = cores_of(mask, lo, hi)
    if cores:
        c0, c1 = max(cores, key=lambda c: c[1] - c[0])
    else:
        mid = (lo + hi) // 2
        c0 = c1 = mid
    cur = (c1 - c0) / RATE
    out.append(xfadeslice(samples, lo, c0))
    if cur >= target:
        half = int(target * RATE / 2)
        if cur * RATE > 2 * half + XFADE:
            out.append(xfadeslice(samples, c0, c0 + half))
            out.append(xfadeslice(samples, c1 - half, c1))
            delta = int(target * RATE) - (c1 - c0)
        else:
            out.append(samples[c0:c1])
            delta = 0
    else:
        mid = (c0 + c1) // 2
        add = int(round((target - cur) * RATE))
        out.append(samples[c0:mid])
        out.append(np.zeros(add, dtype=np.float32))
        out.append(samples[mid:c1])
        delta = add
    out.append(xfadeslice(samples, c1, hi))   # 间隙右段（静音余量）必须保留
    return delta


def tier_of(punct: str, hook: bool) -> float:
    if punct in '。；':
        base = GAP_PERIOD
    elif punct == '！':
        base = GAP_EXCLAIM
    elif punct == '？':
        base = GAP_QUESTION
    elif punct in '，、：':
        base = GAP_COMMA
    else:
        base = GAP_SEMI
    return base + (GAP_HOOK_EXTRA if hook else 0.0)


def speech_blocks(samples: np.ndarray, thr: float = 0.008):
    """语音块（输入坐标样本对）；块间 <45ms 微洞并入（不算断句）。"""
    hop = BLOCK
    n = len(samples) // hop
    rms = np.sqrt((samples[:n * hop].reshape(n, hop) ** 2).mean(axis=1))
    on = rms > thr
    raw = []
    s = None
    for i, v in enumerate(on):
        if v and s is None:
            s = i
        elif not v and s is not None:
            raw.append((s * hop, i * hop)); s = None
    if s is not None:
        raw.append((s * hop, n * hop))
    merged = []
    for a, b in raw:
        if merged and a - merged[-1][1] < BLOCK_MERGE * RATE:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    return [(a, b) for a, b in merged if b - a >= 0.06 * RATE]


def read_audio(path: Path) -> np.ndarray:
    with wave.open(str(path), 'rb') as f:
        return np.frombuffer(f.readframes(f.getnframes()),
                             dtype='<i2').astype(np.float32) / 32768


def write_audio(path: Path, samples: np.ndarray) -> None:
    ints = np.clip(samples * 32767, -32767, 32767).astype('<i2')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(RATE)
        f.writeframes(ints.tobytes())


def chapter_budget(w0: float, w1: float) -> float:
    from render import LEAD, TAIL_MIN
    return (w1 - w0) - LEAD - TAIL_MIN


def trailing_puncts(chapter_text: str, row_texts: list[str]) -> list[str]:
    """行表文本被去标点——从全文按累计位置还原每行的收尾标点。"""
    pos = 0
    out = []
    for t in row_texts:
        pos += len(t)
        while pos < len(chapter_text) and chapter_text[pos] not in '，。！？；：、—':
            pos += 1
        out.append(chapter_text[pos] if pos < len(chapter_text) else '。')
        pos += 1
    return out


def main() -> None:
    HERE = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument('--audio-dir', default=str(HERE / 'audio'))
    ap.add_argument('--manifest', default=str(HERE / 'audio' / 'manifest.json'))
    ap.add_argument('--clause-times', default=str(HERE / 'audio' / 'clause-times.json'))
    ap.add_argument('--report', default=str(HERE / 'audio' / 'pacing-report.json'))
    args = ap.parse_args()

    import sys
    sys.path.insert(0, str(HERE))
    from render import CHAPTER_WINDOWS, digest

    audio_dir = Path(args.audio_dir)
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    story = json.loads((HERE / 'story.json').read_text(encoding='utf-8'))
    ch_text = {c['id']: c['text'] for c in story['chapters']}

    ids = [f'N{i:02d}' for i in range(1, 9)]
    raw = {}
    for cid in ids:
        wav = audio_dir / f'{cid}.wav'
        run(['ffmpeg', '-v', 'error', '-y', '-i', str(audio_dir / f'{cid}.mp3'),
             '-ac', '1', '-ar', str(RATE), '-c:a', 'pcm_s16le', str(wav)])
        raw[cid] = read_audio(wav)
        wav.unlink()

    table = json.loads(Path(args.clause_times).read_text(encoding='utf-8'))
    rows_by_id = {cid: table[cid]['clauses'] for cid in ids}

    def build_chapter(cid, rows, samples, mask, extra, puncts):
        n = len(rows)
        bounds = [int(float(r['end']) * RATE) for r in rows[:-1]]

        # ---- 句间静音核心：[bb-0.5s, bb+0.8s] 全含的未认领静音段，取最长（≥45ms） ----
        claimed = []          # (c0, c1, target)
        inter = [None] * len(bounds)
        for k, b in enumerate(bounds):
            win_lo = max(0, b - int(0.5 * RATE))
            win_hi = min(len(samples), b + int(0.8 * RATE))
            cands = [c for c in cores_of(mask, win_lo, win_hi)
                     if c[1] - c[0] >= int(BLOCK_MERGE * RATE)
                     and not any(not (c[1] <= z0 or c[0] >= z1)
                                 for z0, z1, _t in claimed)]
            if not cands:
                continue          # 行界落在连续语音/微洞上 → 保持原样，绝不在词中插停
            c0, c1 = max(cands, key=lambda c: c[1] - c[0])
            hook = (cid == 'N03' and rows[k]['i'] == 8) or (cid == 'N08' and rows[k]['i'] == 2)
            target = tier_of(puncts[k], hook) + extra
            claimed.append((c0, c1, target))
            inter[k] = (c0, c1, target)

        # ---- 句内微洞 ≥100ms → 80ms（<100ms 一概不动；排除已认领核心）----
        intra = []
        for row in rows:
            a, b = int(float(row['start']) * RATE), int(float(row['end']) * RATE)
            for c0, c1 in cores_of(mask, a, b):
                if (c1 - c0) / RATE < 0.10:
                    continue
                if any(not (c1 <= z0 or c0 >= z1) for z0, z1, _t in claimed):
                    continue
                intra.append((c0, c1, INTRA_HOLE_MAX))

        # ---- 连续重排：语音段原样保留，只动静音 ----
        ops = sorted([(e[0], e[1], e[2]) for e in inter if e] +
                     [(c0, c1, t) for c0, c1, t in intra], key=lambda t: t[0])
        out: list = []
        cursor = 0
        op_deltas = []
        for lo, hi, target in ops:
            if lo < cursor:
                raise RuntimeError(f'{cid}: 重叠间隙 @{lo}')
            out.append(samples[cursor:lo])        # 语音段完整原样保留（零裁剪）
            delta = remap_gap(samples, mask, lo, hi, target, out)
            op_deltas.append((lo, hi, delta))
            cursor = hi
        out.append(samples[cursor:])
        merged = np.concatenate(out) if out else samples

        def shift_before(pos):
            return sum(d for o0, o1, d in op_deltas if o1 <= pos)

        # ---- 行时间贴真实语音块（<45ms 微洞并块；跨块按字数比例切） ----
        blocks = speech_blocks(samples)
        core_ends = sorted((e[0], e[1]) for e in inter if e)
        # 行分组：inter[k] 为 None 的边界不拆组
        groups = []
        cur = [0]
        for k in range(n - 1):
            if inter[k] is None:
                cur.append(k + 1)
            else:
                groups.append(cur); cur = [k + 1]
        groups.append(cur)

        placed = [None] * n
        for grp in groups:
            # 本组语音块：夹在拆组的已认领核心之间
            if grp[0] > 0 and inter[grp[0] - 1] is not None:
                before = inter[grp[0] - 1][1]
            else:
                before = 0
            if grp[-1] < n - 1 and inter[grp[-1]] is not None:
                after = inter[grp[-1]][0]
            else:
                after = len(samples)
            seg_blocks = [(a, b) for a, b in blocks
                          if a >= before - BLOCK_MERGE * RATE and b <= after + BLOCK_MERGE * RATE]
            if not seg_blocks:
                for gi in grp:
                    r = rows[gi]
                    rs = int(float(r['start']) * RATE) + shift_before(int(float(r['start']) * RATE))
                    re_ = int(float(r['end']) * RATE) + shift_before(int(float(r['end']) * RATE))
                    placed[gi] = [r, rs, re_]
                continue
            total_chars = sum(len(re.sub(r'[^A-Za-z0-9\u3400-\u9fff]', '', rows[gi]['text'])) for gi in grp)
            total_chars = max(1, total_chars)
            cum = 0
            cuts_in = []
            for gi in grp[:-1]:
                cum += len(re.sub(r'[^A-Za-z0-9\u3400-\u9fff]', '', rows[gi]['text']))
                cuts_in.append(cum / total_chars)
            starts = [seg_blocks[0][0]]
            dur_map = []
            acc = 0.0
            for a, b in seg_blocks:
                dur_map.append((acc, acc + (b - a), a, b))
                acc += (b - a)
            bounds_in = [p * acc for p in cuts_in]
            for t_target in bounds_in:
                for d0, d1, a, b in dur_map:
                    if d0 <= t_target <= d1 and d1 > d0:
                        frac = (t_target - d0) / (d1 - d0)
                        cuts_in_pos = a + (b - a) * frac
                        break
                else:
                    cuts_in_pos = seg_blocks[-1][1]
                starts.append(int(cuts_in_pos))
            ends = starts[1:] + [seg_blocks[-1][1]]
            for idx, gi in enumerate(grp):
                s_in = int(starts[idx]); e_in = int(ends[idx])
                placed[gi] = [rows[gi],
                              s_in + shift_before(s_in),
                              e_in + shift_before(e_in)]
        return merged, placed, sum(1 for e in inter if e), len(intra)

    out_table = {}
    report = []
    tempo_report = {}
    for cid in ids:
        rows = sorted(rows_by_id[cid], key=lambda r: r['i'])
        if len(rows) < MIN_LEN:
            raise SystemExit(f'{cid}: {len(rows)} clause(s) < min length {MIN_LEN}s')
        samples = raw[cid]
        mask = silence_mask(samples)
        puncts = trailing_puncts(ch_text[cid], [r['text'] for r in rows])

        w0, w1 = CHAPTER_WINDOWS[cid]
        budget = chapter_budget(w0, w1)
        extra = 0.0
        for attempt in range(3):
            merged, placed, n_gaps, n_intra = build_chapter(
                cid, rows, samples, mask, extra, puncts)
            d = len(merged) / RATE
            tempo = d / budget
            if tempo >= 0.79:
                break
            n_inter = max(1, n_gaps)
            extra += (0.80 * budget - d) / n_inter
        else:
            raise SystemExit(f'{cid}: 补停 3 轮后 tempo={tempo:.3f} 仍 < 0.79，人工检查')
        if tempo > TEMPO_MAX:
            raise SystemExit(f'{cid}: 口播 {d:.2f}s 超窗（需变速 {tempo:.3f} > '
                             f'{TEMPO_MAX}）：该删字，不能硬塞')

        tmp = audio_dir / f'{cid}.wav'
        write_audio(tmp, merged)
        run(['ffmpeg', '-v', 'error', '-y', '-i', str(tmp),
             '-codec:a', 'libmp3lame', '-b:a', '192k', '-ar', '48000',
             str(audio_dir / f'{cid}.mp3')])
        tmp.unlink()

        prev_end_f = 0.0
        chapter_rows = []
        for row, ns, ne in placed:
            gap_before = (ns / RATE) - prev_end_f if prev_end_f > 0 else 0.0
            chars = len(re.sub(r'[^A-Za-z0-9\u3400-\u9fff]', '', row['text']))
            chapter_rows.append({
                'i': row['i'],
                'start': round(ns / RATE, 2),
                'end': round(ne / RATE, 2),
                'text': row['text'],
                'chars_per_second': round(chars / max(0.12, (ne - ns) / RATE), 2),
                'gap_before': round(max(0.0, gap_before), 2),
            })
            prev_end_f = ne / RATE
        out_table[cid] = {'duration': round(d, 3), 'clauses': chapter_rows}
        tempo_report[cid] = {'file_len': round(d, 3), 'budget': round(budget, 3),
                             'implied_tempo': round(tempo, 4), 'extra': round(extra, 3)}
        report.append({
            'chapter': cid,
            'clauses': len(rows),
            'input_len': round(len(samples) / RATE, 3),
            'output_len': round(d, 3),
            'gaps_remapmed': n_gaps,
            'intra_holes_tightened': n_intra,
            'gap_extra': round(extra, 3),
            'implied_tempo': round(tempo, 4),
        })
        print(f"{cid} 文本{len(rows)}句  时长 {d:6.2f}s  句间重映射 {n_gaps:2d}  "
              f"句内微洞 {n_intra:2d}  tempo {tempo:.3f}")

    out_manifest = dict(manifest)
    for clip in out_manifest['clips']:
        clip['sha256'] = digest(audio_dir / clip['file'])
    Path(args.manifest).write_text(
        json.dumps(out_manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    Path(args.clause_times).write_text(
        json.dumps(out_table, ensure_ascii=False, indent=2), encoding='utf-8')
    Path(args.report).write_text(json.dumps(
        {'note': 'v3.2 gap-remap pacing (no word cuts, click-free splices); '
                 'layer pauses from story punctuation; rows pinned to real speech; '
                 'fill via chapter_layout atempo',
         'gap_targets': {'period': GAP_PERIOD, 'exclaim': GAP_EXCLAIM,
                         'question': GAP_QUESTION, 'comma': GAP_COMMA,
                         'semi': GAP_SEMI, 'hook_extra': GAP_HOOK_EXTRA},
         'intra_hole_max': INTRA_HOLE_MAX, 'sil_rms': SIL_RMS,
         'tempo_window': [TEMPO_MIN, TEMPO_MAX],
         'chapters': report, 'tempo': tempo_report},
        ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
