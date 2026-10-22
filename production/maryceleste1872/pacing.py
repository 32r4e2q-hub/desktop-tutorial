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
TAIL_MIN = 0.55  # 每章口播后的最小收束（与 render.py 一致）
MIN_GAP = 0.22   # 句间停顿下限（再小就听不出是停顿）


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
        # 行与行之间的切点：上一行结束与下一行开始的中点（那里一定是静音）
        cuts = [0.0]
        for k in range(1, len(rows)):
            cuts.append(round((rows[k - 1]['end'] + rows[k]['start']) / 2, 6))
        cuts.append(dur)
        pieces = [samples[int(round(cuts[k] * RATE)):int(round(cuts[k + 1] * RATE))]
                  for k in range(len(rows))]
        speech = sum(len(p) for p in pieces) / RATE
        gaps = max(1, len(rows) - 1)
        budget = (w1 - w0) - LEAD - TAIL_MIN - speech
        gap = budget / gaps
        if gap < MIN_GAP:
            raise SystemExit(f'{cid}: 窗口 {w0:g}–{w1:g} 装不下口播（句间停顿只剩 {gap:.2f}s < {MIN_GAP}）：'
                             f'要么删字，要么给这段加窗口')
        total_n = int(round((w1 - w0 - TAIL_MIN - LEAD) * RATE))
        out = np.zeros(total_n, dtype=np.float32)
        placed = []
        cursor = 0.0
        for k, piece in enumerate(pieces):
            i = int(round(cursor * RATE))
            out[i:i + len(piece)] += piece
            row = rows[k]
            shift = cursor - cuts[k]           # 行内偏移：整块平移，语段时长原样保留
            new_start = round(row['start'] + shift, 2)
            prev_end = placed[-1]['end'] if placed else 0.0
            placed.append({'i': k, 'start': new_start,
                           'end': round(row['end'] + shift, 2), 'text': row['text'],
                           'gap_before': round(max(0.0, new_start - prev_end), 2),
                           'chars_per_second': row['chars_per_second']})
            cursor += len(piece) / RATE
            if k < len(pieces) - 1:
                cursor += gap
        encode(out, src)
        # 以 mp3 再解码回读时长（mp3 分帧取整的 ±25 ms 也一起记进收据）
        final_dur = len(decode(src)) / RATE
        out_rows[cid] = {'duration': round(final_dur, 3), 'clauses': placed}
        report['clips'].append({'id': cid, 'window': [w0, w1], 'speech_seconds': round(speech, 3),
                                'gap_each_seconds': round(gap, 3), 'clauses': len(rows),
                                'file_seconds': round(final_dur, 3), 'sha256': digest(src)})
        print(f'{cid}: 语段 {speech:5.2f}s + 句间停顿 {gaps}×{gap:.2f}s → {final_dur:5.2f}s '
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
