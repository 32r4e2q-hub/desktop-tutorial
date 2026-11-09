#!/usr/bin/env python3
"""Offline readiness check; never contacts Agnes and never creates paid tasks."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
PNG = b'\x89PNG\r\n\x1a\n'

def check():
    story = json.loads((ROOT / 'story.json').read_text(encoding='utf-8'))
    approval_file = ROOT / 'reference' / 'approvals.json'
    approvals = json.loads(approval_file.read_text(encoding='utf-8')) if approval_file.exists() else {}
    errors = []
    shots = story['shots']
    if len(shots) != 30: errors.append('必须为30个镜头')
    cursor = 0
    for s in shots:
        sid=s['id']
        if s['start'] != cursor or s['duration'] != s['end'] - s['start'] or not 5 <= s['duration'] <= 7:
            errors.append(f'{sid}：时间轴不连续或时长不在5–7秒')
        cursor = s['end']
        p=s['prompt']
        if not p.startswith('【STYLE】'+story['style']) or not p.endswith('【NEGATIVE】'+story['negative']):
            errors.append(f'{sid}：STYLE或NEGATIVE未完整拼接')
        for c in s['characters']:
            if story['anchors'][c] not in p: errors.append(f'{sid}：缺角色锚点{c}')
        if not 1 <= len(s['reference_images']) <= 5: errors.append(f'{sid}：参考图数量不合法')
        for n,r in enumerate(s['reference_images'],1):
            if r not in story['reference_ids'] + story.get('additional_review_ids', []) or f'<Picture {n}>={r}' not in p:
                errors.append(f'{sid}：参考图映射不合法：{r}')
        if not s['narration'].strip(): errors.append(f'{sid}：旁白为空')
    if cursor != 180: errors.append(f'总时长不是180秒：{cursor}')
    for ref in story['reference_ids'] + story.get('additional_review_ids', []):
        path = ROOT / 'reference' / f'{ref}.png'
        row = approvals.get(ref, {})
        if not path.exists():
            errors.append(f'{ref}：参考图缺失')
        elif not path.read_bytes().startswith(PNG):
            errors.append(f'{ref}：不是PNG')
        elif row.get('status') != 'approved':
            errors.append(f'{ref}：尚未完成定稿')
        elif hashlib.sha256(path.read_bytes()).hexdigest() != row.get('sha256'):
            errors.append(f'{ref}：与定稿SHA不一致')
    return errors

if __name__ == '__main__':
    errors=check()
    if errors:
        print('视频任务禁止提交：')
        print('\n'.join('- '+e for e in errors))
        sys.exit(1)
    print('规划与参考图定稿初检通过；仍需固定公网revision、声音与服务端调用验证。')
