#!/usr/bin/env python3
"""Build machine-readable timeline from the editable Chinese production script.
No media is created and no readiness or approval is inferred.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    text = (HERE / '制作脚本_待制作.md').read_text(encoding='utf-8')
    pattern = re.compile(r'^\|(\d\d)\|(\d+)–(\d+)\|([^|]+)\|([^|]+)\|$', re.M)
    rows = pattern.findall(text)
    if len(rows) != 30:
        raise ValueError(f'Expected 30 shot rows, got {len(rows)}')
    shots = []
    cursor = 0
    for index, (num, start, end, visual, narration) in enumerate(rows, 1):
        start, end = int(start), int(end)
        if int(num) != index or start != cursor or end <= start:
            raise ValueError(f'Invalid timeline at shot {num}')
        shots.append({'id': f'S{num}', 'start': start, 'duration': end-start,
                      'visual': visual, 'narration': '' if index == 1 else narration,
                      'narration_file': None if index == 1 else f'audio/S{num}.mp3',
                      'sfx_only': index == 1})
        cursor = end
    if cursor != 180 or rows[0][4] != '无旁白':
        raise ValueError('Expected 180 seconds and silent opening')
    output = {'title': '白银连环案：追凶28年', 'target_duration': 180,
              'width': 1920, 'height': 1080, 'fps': 24,
              'status': 'draft_not_ready', 'shots': shots}
    (HERE / 'story.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Wrote 30 consecutive shots / 180s; status is draft_not_ready')

if __name__ == '__main__':
    main()
