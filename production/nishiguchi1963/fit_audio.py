#!/usr/bin/env python3
"""Report real trimmed voice duration against each fixed shot; tolerate incomplete work."""
import json
import tempfile
from pathlib import Path
from build_audio import RATE, decode_mp3, trim_voice_edges

HERE=Path(__file__).resolve().parent

def main():
    story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    manifest=json.loads((HERE/'audio/manifest.json').read_text(encoding='utf-8'))
    records={r['id']:r for r in manifest['clips']}
    rows=[]
    with tempfile.TemporaryDirectory() as temp:
        for shot in story['shots']:
            sid=shot['id']; record=records.get(sid)
            if not record:
                rows.append((sid,shot['duration'],None,None,'missing')); continue
            samples=decode_mp3(HERE/'audio'/record['file'],Path(temp)/f'{sid}.wav',1.0)
            trimmed,_,_=trim_voice_edges(samples)
            seconds=len(trimmed)/RATE
            available=min(shot['duration']-0.08,179.0-shot['start'])
            ratio=seconds/available
            status=('over' if ratio>1.55 else 'speedup' if ratio>1 else 'fit' if ratio>=.85 else 'ok' if ratio>=.7 else 'short')
            rows.append((sid,shot['duration'],seconds,ratio,status))
    print('| 镜头 | 镜头秒数 | 去静音旁白秒数 | 可用窗口占比 | 状态 |')
    print('|---|---:|---:|---:|---|')
    for sid,dur,sec,ratio,status in rows:
        print(f'| {sid} | {dur} | {sec:.2f} | {ratio:.0%} | {status} |' if sec is not None else f'| {sid} | {dur} | — | — | missing |')
    print('\n状态说明：fit 85–100%；ok 70–85%；short 低于70%；speedup 需加速；over 超出1.55倍上限。')
    print('最后一秒静音；不慢放、截字或以冻结画面填充。本表仅测语音能量与时长，不代替听审。')
if __name__=='__main__': main()
