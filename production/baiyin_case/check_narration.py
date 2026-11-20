#!/usr/bin/env python3
"""Measure shot-locked audio. Missing/overlong clips are not a pass.
Uses ffprobe on PATH, or FFPROBE=/absolute/path/to/ffprobe.
Durations are container durations; final trimmed/aligned clips require separate QC.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    story = json.loads((HERE / 'story.json').read_text(encoding='utf-8'))
    rows = []
    lines = ['# 逐镜旁白初检（非终检）', '',
             '容器时长未经静音裁剪；需经逐镜试听和时间轴匹配。首镜无旁白。', '',
             '| 镜头 | 窗口（秒） | 音频（秒） | 不裁剪所需倍速 | 结果 |',
             '|---|---:|---:|---:|---|']
    for shot in story['shots'][1:]:
        path = HERE / shot['narration_file']
        row = {'id': shot['id'], 'window_seconds': shot['duration'], 'file': shot['narration_file']}
        if not path.is_file():
            row['status'] = 'MISSING'
            lines.append(f"| {shot['id']} | {shot['duration']} | — | — | 未生成 |")
        else:
            proc = subprocess.run([os.environ.get('FFPROBE', 'ffprobe'), '-v', 'error',
                                   '-show_entries', 'format=duration', '-of', 'json', str(path)],
                                  text=True, capture_output=True, check=True)
            duration = float(json.loads(proc.stdout)['format']['duration'])
            speed = max(1.0, duration / shot['duration'])
            row.update(duration_seconds=round(duration, 3), speed_required=round(speed, 4),
                       sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       status='FITS_RAW' if speed <= 1 else 'OVER_WINDOW')
            label = '容器时长可放入，待听检' if speed <= 1 else '超窗，需处理'
            lines.append(f"| {shot['id']} | {shot['duration']} | {duration:.3f} | {speed:.3f} | {label} |")
        rows.append(row)
    missing = sum(r['status'] == 'MISSING' for r in rows)
    over = sum(r['status'] == 'OVER_WINDOW' for r in rows)
    lines += ['', f'未生成：{missing}段；容器时长超窗：{over}段。',
              '未检测语音起止点、错词、串镜或人耳听感，不可作为成片放行依据。']
    (HERE / 'qa').mkdir(exist_ok=True)
    (HERE / 'qa' / 'narration.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (HERE / 'qa' / 'narration.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'MISSING={missing} OVER_WINDOW={over}; final QC not performed')
    return 1 if missing or over else 0

if __name__ == '__main__':
    raise SystemExit(main())
