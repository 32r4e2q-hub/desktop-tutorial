#!/usr/bin/env python3
"""Refresh shot-locked voice manifest from audio/Sxx.mp3 files already generated."""
import hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
chapters={sid:c['id'] for c in story['chapters'] for sid in c['shot_ids']}
clips=[]; missing=[]
for shot in story['shots']:
    audio=HERE/'audio'/f"{shot['id']}.mp3"
    if not audio.is_file():
        missing.append(shot['id']); continue
    clips.append({'id':shot['id'],'file':audio.name,'voice_id':'voice-00','narration_id':shot['narration_id'],'target_start':shot['start'],'target_duration':shot['duration'],'text':shot['narration'],'sha256':hashlib.sha256(audio.read_bytes()).hexdigest()})
manifest={'voice':'voice-00','language':'zh-CN','alignment':'one-clip-one-shot-one-caption','slowdown_allowed':False,'clips':clips}
(HERE/'audio'/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f"manifest clips={len(clips)}/29; missing={','.join(missing) if missing else 'none'}")
