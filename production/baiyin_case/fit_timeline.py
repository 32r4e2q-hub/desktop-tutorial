#!/usr/bin/env python3
"""Fit integer-second shot windows to measured MP3s without cutting speech.
Edits the production script (source of truth), rebuilds story.json, then run
check_narration.py. Does not create or approve footage.
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent


def main():
    story = json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    rows = json.loads((HERE/'qa/narration.json').read_text(encoding='utf-8'))
    if len(rows) != 29 or any('duration_seconds' not in r for r in rows):
        raise SystemExit('Need all 29 measured audio files first')
    reserve = {'S25': 1.0, 'S30': 2.0}
    durations = [2] + [math.ceil(r['duration_seconds']/1.10 + .12 + reserve.get(r['id'], 0)) for r in rows]
    remaining = 180 - sum(durations)
    if remaining < 0:
        raise SystemExit(f'Cannot fit at <=1.1x; need {-remaining} more seconds')
    # Keep original durations wherever possible, subject to the voiced minima.
    for i in range(1, 30):
        give = min(remaining, max(0, story['shots'][i]['duration'] - durations[i]))
        durations[i] += give
        remaining -= give
    durations[-1] += remaining
    path = HERE/'制作脚本_待制作.md'
    text = path.read_text(encoding='utf-8')
    current = 0
    for i, duration in enumerate(durations, 1):
        pattern = rf'(?m)^(\|{i:02d}\|)\d+–\d+(\|)'
        replacement = rf'\g<1>{current}–{current+duration}\g<2>'
        text, count = re.subn(pattern, replacement, text)
        if count != 1:
            raise SystemExit(f'Expected exactly one row for S{i:02d}, got {count}')
        current += duration
    assert current == 180
    path.write_text(text, encoding='utf-8')
    subprocess.run([sys.executable, str(HERE/'build_story.py')], check=True)
    print('Adjusted shot windows, preserving S25 1s black and S30 2s source card; <=1.10x planned')

if __name__ == '__main__':
    main()
