#!/usr/bin/env python3
"""Bind selected-voice MP3s to the shot-locked narration and report safe fit rates.
Run after all 30 S01.mp3..S30.mp3 files exist; never silently invent missing audio.
"""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def duration(path: Path) -> float:
    raw=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],text=True)
    return float(raw.strip())

def main() -> None:
    story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    voice=story['narration_spec']['voice_id']
    clips=[]; missing=[]
    for shot in story['shots']:
        path=HERE/'audio'/f"{shot['id']}.mp3"
        if not path.is_file():
            missing.append(shot['id']);continue
        source=duration(path); target=float(shot['duration'])
        speed=max(1.0,source/target)
        if speed>1.55+1e-9:
            raise SystemExit(f"{shot['id']}: narration needs {speed:.3f}x, over the 1.55x hard limit")
        clips.append({'id':shot['id'],'file':path.name,'text':shot['narration'],'sha256':digest(path),
                      'voice_id':voice,'voice_description':story['narration_spec']['description'],
                      'narration_id':shot['narration_id'],'target_start':shot['start'],
                      'target_duration':shot['duration'],'alignment':'shot-locked',
                      'source_duration':round(source,3),'atempo':round(speed,4),
                      'tail_silence_seconds':round(max(0.0,target-source/speed),3)})
    if missing:
        raise SystemExit('Missing narration: '+', '.join(missing))
    manifest={'language':'zh-CN','voice':voice,'generation':'Arena TTS; one independent clip per shot',
              'alignment':'one-clip-one-shot-one-caption','max_speedup_factor':1.55,
              'slowdown_allowed':False,'clips':clips}
    (HERE/'audio'/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Wrote manifest for {len(clips)} shot-locked clips; max atempo={max(x['atempo'] for x in clips):.3f}x")
if __name__=='__main__': main()
