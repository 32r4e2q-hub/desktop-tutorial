#!/usr/bin/env python3
"""Regenerate an explicitly incomplete or complete shot-locked VO manifest."""
import hashlib
import json
from pathlib import Path
import av

HERE = Path(__file__).resolve().parent

def main():
    story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    transcripts=json.loads((HERE/'audio/transcripts.json').read_text(encoding='utf-8'))
    clips=[]
    for shot in story['shots']:
        path=HERE/'audio'/f"{shot['id']}.mp3"
        if not path.is_file():
            continue
        if transcripts.get(shot['id']) != shot['narration']:
            raise RuntimeError(f"{shot['id']}: absent or mismatched verified transcript; re-record before manifest refresh")
        with av.open(str(path)) as container:
            duration=round(container.duration/av.time_base,3)
        clips.append({'id':shot['id'],'file':path.name,'text':shot['narration'],
          'voice_id':story['narration_spec']['voice_id'],
          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
          'narration_id':shot['narration_id'],'target_start':shot['start'],
          'target_duration':shot['duration'],'alignment':'shot-locked',
          'source_duration_seconds':duration})
    doc={'language':'zh-CN','voice':story['narration_spec']['voice_id'],
         'generation':'Arena TTS selected voice; '+('complete' if len(clips)==len(story['shots']) else 'incomplete'),
         'alignment':'one-clip-one-shot-one-caption','slowdown_allowed':False,
         'max_speedup_factor':story['narration_spec']['max_speedup_factor'],'clips':clips}
    (HERE/'audio/manifest.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"{len(clips)}/{len(story['shots'])} voice clips recorded (transcripts checked).")

if __name__=='__main__': main()
