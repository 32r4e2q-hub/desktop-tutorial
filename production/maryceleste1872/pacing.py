#!/usr/bin/env python3
"""配音排版（pacing）：把收紧后的八段口播按分句拆开，均匀铺进用户脚本的段落窗口。

为什么要这一步（2026-10-22 玛丽号）：TTS 的自然语速约 4.8–5.1 字/秒，一口气念完后
剩下的窗口只能堆在段尾；而用户脚本的八段时间轴（10/20/25/35/20/25/29/13 秒）里，
镜头蒙太奇要**跟着旁白一起摊开**（N05 的海盗/叛变打叉、N06 的海怪/水龙卷都是
语少画多的段落）。把分句之间的停顿按窗口预算均匀拉开，得到三件事：

1. 口播自然语速（不硬变速，声音不飘），句间停顿变成悬疑呼吸（0.26–2.6 s）——
   正是用户「悬疑处放慢」「『都消失了』『绳子断了』处停顿」的实现方式；
2. 分句时间与用户段落窗口逐秒对齐，段内蒙太奇的切点可以落在分句起点上；
3. clause-times.json 由本环节**按实际拼装位置精确写出**（行内语段原样保留，
   只在行与行之间加静音），所以 chars_per_second 带不动、--check-cuts 口径不变。

链路：tighten_pauses.py（只剪静音）→ clause_times.py（在紧凑版上对分句）
      → pacing.py（铺进窗口，重写 audio/N0x.mp3 与 clause-times.json，更新 manifest）
      → generate.py --validate → tools/plan_cuts.py → clause_times.py --check-cuts
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AUDIO = HERE / 'audio'
CLAUSES = AUDIO / 'clause-times.json'
MANIFEST = AUDIO / 'manifest.json'
STORY = HERE / 'story.json'
RATE = 48000

LEAD = 0.35      # 每章口播前的呼吸（与 render.py 一致）
TAIL_MIN = 0.55  # 每章口播后的最小收束（与 render.py 一致；「都消失了」「绳子断了」的0.5s悬疑停顿也由它兜住）
MIN_GAP = 0.22   # 句间停顿下限（再小就听不出是停顿）

# ── 2026-10-23「解说一卡一卡」修复：句间停顿不再均摊，按标点分级 ──────────────
# 旧版把窗口预算除以句数得到同一个 gap（玛丽号 v3 实测 N04 十六句碎片每句垫 420 ms，
# 4 字短语配半秒空拍=机械顿挫）。现在：逗号级轻提（语流不断），句号/问叹级换气
# （悬疑呼吸），剩余预算大头给句读；窗口仍精确填满，逐字不动。
COMMA_GAP = 0.22     # 逗号/顿号/冒号/分号：轻提
COMMA_MIN = 0.16
COMMA_MAX = 0.28
SENT_GAP_MIN = 0.32  # 句号/问叹：至少换口气（窗口紧时按比例缩放，仍显著长于逗号）
SENT_GAP_MAX = 1.60  # 悬疑呼吸上限；再长就假了
INTRA_SIL = 0.03     # 句内（分句内部）TTS 微洞超过 30 ms 的一律缝到 30 ms

COMMA_MARKS = '，、：；,'
SENT_MARKS = '。.'
EXCLAIM_MARKS = '？?！!'


def row_mark(text: str, cursor: int, plain: str, original: str):
    """定位分句文本在原文里的尾点，返回其后第一个标点（自 cursor 起推进）。"""
    target = ''.join(ch for ch in text if not ch.isspace())
    if not target:
        return '，', cursor
    pos = plain.find(target, cursor)
    if pos < 0:
        pos = plain.find(target[:6], cursor)
    if pos < 0:
        return '，', cursor
    end = pos + len(target)
    idx_map = [i for i, ch in enumerate(original)
               if not ch.isspace() and ch not in '，。、：；？！「」…—·']
    if end - 1 < len(idx_map):
        o = idx_map[end - 1] + 1
        while o < len(original) and original[o] not in '，。、：；？！':
            o += 1
        mark = original[o] if o < len(original) else '。'
    else:
        mark = '。'
    return mark, end


def tier_gaps(marks, budget: float):
    """按标点分级把 budget 分到 len(marks) 个句间停顿上，返回每段秒数。
    柔性下限：窗口紧时按比例缩放地板值（逗号仍显著短于句读），绝不超预算。"""
    n = len(marks)
    if n == 0:
        return []
    is_comma = [m in COMMA_MARKS for m in marks]
    weights = [1.0 if c else (2.9 if m in EXCLAIM_MARKS else 2.6)
               for c, m in zip(is_comma, marks)]
    floor = [COMMA_MIN if c else SENT_GAP_MIN for c in is_comma]
    cap = [COMMA_MAX if c else SENT_GAP_MAX for c in is_comma]
    hard_min = 0.12
    if sum(floor) > budget:
        scale = max(hard_min / min(floor), budget / sum(floor))
        floor = [max(hard_min, f * scale) for f in floor]
        if sum(floor) > budget + 1e-9:
            return None
    extra = budget - sum(floor)
    wsum = sum(weights)
    gaps = [f + extra * w / wsum for f, w in zip(floor, weights)]
    for _ in range(8):
        over = sum(max(0.0, g - c) for g, c in zip(gaps, cap))
        if over <= 1e-9:
            break
        gaps = [min(g, c) for g, c in zip(gaps, cap)]
        free = [i for i in range(n) if gaps[i] < cap[i] - 1e-9]
        if not free:
            break
        wfree = sum(weights[i] for i in free)
        for i in free:
            gaps[i] += over * weights[i] / wfree
    return gaps


def trim_to_speech(x):
    """把语段裁到真实语音边界（DP 给的行界常带 ±0.2 s 静音垫边，不裁掉的话
    实际停顿会比账本长一截——2026-10-23 实测句间多出 380–430 ms）。"""
    if len(x) < 960:
        return x
    hop = 480
    n = len(x) // hop * hop
    rms = np.sqrt((x[:n].reshape(-1, hop) ** 2).mean(axis=1))
    loud = np.where(rms >= 0.01)[0]
    if len(loud) == 0:
        return x
    a = max(0, loud[0] * hop - 240)   # 留 5 ms 呼吸
    b = min(len(x), (loud[-1] + 1) * hop + 240)
    return x[a:b]


def shrink_internal(x, max_sil=INTRA_SIL):
    """分句内部的 TTS 微洞（80–300 ms 的假停顿）缝到 max_sil，词不动。"""
    if len(x) < 960:
        return x
    hop = 480
    n = len(x) // hop * hop
    rms = np.sqrt((x[:n].reshape(-1, hop) ** 2).mean(axis=1))
    quiet = rms < 0.01
    spans, start = [], None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        if not q and start is not None:
            spans.append((start * hop, i * hop))
            start = None
    if start is not None:
        spans.append((start * hop, len(x)))
    pieces, cursor = [], 0
    touched = False
    for a, b in spans:
        if a == 0 or b >= len(x):
            continue  # 片段边缘的缝由句间停顿接管
        length = (b - a) / RATE
        if length <= max_sil:
            continue
        keep = int(max_sil * RATE)
        pieces.append(x[cursor:a])
        pieces.append(np.zeros(keep, dtype=np.float32))
        cursor = b
        touched = True
    if not touched:
        return x
    pieces.append(x[cursor:])
    out = pieces[0]
    ramp = np.linspace(0, 1, 240, dtype=np.float32)
    for piece in pieces[1:]:
        if len(out) >= 240 and len(piece) >= 240:
            out[-240:] = out[-240:] * (1 - ramp) + piece[:240] * ramp
            out = np.concatenate([out, piece[240:]])
        else:
            out = np.concatenate([out, piece])
    return out


def decode(path: Path) -> np.ndarray:
    proc = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(RATE), '-f', 's16le', '-'],
        check=True, capture_output=True)
    return np.frombuffer(proc.stdout, dtype='<i2').astype(np.float32) / 32768


def encode(x: np.ndarray, path: Path):
    tmp = path.with_suffix('.tmp.wav')
    with wave.open(str(tmp), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(RATE)
        f.writeframes(np.int16(np.clip(x, -1, 1) * 32767).tobytes())
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(tmp), '-ac', '1', '-ar', str(RATE),
                    '-c:a', 'libmp3lame', '-b:a', '192k', '-map_metadata', '-1', '-fflags', '+bitexact',
                    '-flags:a', '+bitexact', str(path)], check=True)
    tmp.unlink()


def digest(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    table = json.loads(CLAUSES.read_text())
    if any('gap_before' in r for v in table.values() for r in v['clauses']):
        raise SystemExit('clause-times.json 已经是铺开排版后的版本（行里有 gap_before）：'
                         '重跑链路请先 tighten_pauses.py + clause_times.py 回到紧凑版，别对已铺开的音频二次铺开')
    story = json.loads(STORY.read_text())
    windows = story['chapter_windows']
    report = {'lead': LEAD, 'tail_min': TAIL_MIN, 'rate': RATE, 'clips': []}
    out_rows = {}
    for chapter in story['chapters']:
        cid = chapter['id']
        w0, w1 = windows[cid]
        entry = table[cid]
        rows = entry['clauses']
        src = AUDIO / (cid + '.mp3')
        samples = decode(src)
        dur = len(samples) / RATE
        # 2026-10-23「一卡一卡」修复：行间切点直接取语段边界（旧版取中点会把半截
        # 静音并进语段，实际停顿=片内静音+gap，账目对不上）；语段内 ≥30 ms 的 TTS
        # 微洞缝掉；句间停顿按标点分级铺进窗口——逗号轻提（语流不断），句读换气。
        pieces = [shrink_internal(trim_to_speech(
            samples[int(round(r['start'] * RATE)):int(round(r['end'] * RATE))]))
            for r in rows]
        speech = sum(len(p) for p in pieces) / RATE
        budget = (w1 - w0) - LEAD - TAIL_MIN - speech
        text = chapter['text']
        plain = ''.join(ch for ch in text if not ch.isspace() and ch not in '，。、：；？！「」…—·')
        cursor_txt = 0
        marks = []
        for r in rows:
            mark, cursor_txt = row_mark(r['text'], cursor_txt, plain, text)
            marks.append(mark)
        gap_list = tier_gaps(marks[:-1], budget) if len(rows) > 1 else []
        if gap_list is None:
            raise SystemExit(f'{cid}: 窗口 {w0:g}–{w1:g} 装不下口播（分级后句间停顿低于下限）：'
                             f'要么删字，要么给这段加窗口')
        total_n = int(round((w1 - w0 - TAIL_MIN - LEAD) * RATE))
        out = np.zeros(total_n, dtype=np.float32)
        placed = []
        cursor = 0.0
        for k, piece in enumerate(pieces):
            i = int(round(cursor * RATE))
            out[i:i + len(piece)] += piece
            row = rows[k]
            new_start = round(cursor, 2)
            prev_end = placed[-1]['end'] if placed else 0.0
            placed.append({'i': k, 'start': new_start,
                           'end': round(cursor + len(piece) / RATE, 2), 'text': row['text'],
                           'gap_before': round(max(0.0, new_start - prev_end), 2),
                           'chars_per_second': row['chars_per_second']})
            cursor += len(piece) / RATE
            if k < len(pieces) - 1:
                cursor += gap_list[k]
        encode(out, src)
        # 以 mp3 再解码回读时长（mp3 分帧取整的 ±25 ms 也一起记进收据）
        final_dur = len(decode(src)) / RATE
        out_rows[cid] = {'duration': round(final_dur, 3), 'clauses': placed}
        report['clips'].append({'id': cid, 'window': [w0, w1], 'speech_seconds': round(speech, 3),
                                'gap_tier_seconds': [round(g, 3) for g in gap_list],
                                'gap_marks': marks[:-1], 'clauses': len(rows),
                                'file_seconds': round(final_dur, 3), 'sha256': digest(src)})
        print(f'{cid}: 语段 {speech:5.2f}s + 分级停顿 {[round(g,2) for g in gap_list]} → {final_dur:5.2f}s '
              f'（窗口 {w0:g}–{w1:g}）')

    CLAUSES.write_text(json.dumps(out_rows, ensure_ascii=False, indent=1))
    manifest = json.loads(MANIFEST.read_text())
    by_id = {row['id']: row for row in report['clips']}
    for clip in manifest['clips']:
        clip['sha256'] = by_id[clip['id']]['sha256']
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (AUDIO / 'pacing-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('written', CLAUSES, '与', AUDIO / 'pacing-report.json', '；manifest SHA-256 已更新')
    return 0


if __name__ == '__main__':
    sys.exit(main())
