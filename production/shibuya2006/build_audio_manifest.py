#!/usr/bin/env python3
"""Bind selected-voice MP3s to the shot-locked narration and report safe fit rates.
Run after all 30 S01.mp3..S30.mp3 files exist; never silently invent missing audio.
"""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

import narration_pace as pace

HERE=Path(__file__).resolve().parent

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def duration(path: Path) -> float:
    raw=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)],text=True)
    return float(raw.strip())

def require_review(shot: dict, path: Path, voice: str, reviews: dict) -> None:
    """Do not turn a filename or pause-cut guess into verified narration provenance."""
    row=reviews.get(shot['id'], {})
    if (row.get('status') != 'approved' or not row.get('reviewed_by')
            or not row.get('review_method')
            or row.get('text') != shot['narration']
            or row.get('sha256') != digest(path)
            or row.get('voice_id') != voice):
        raise RuntimeError(f"{shot['id']}: missing approved text/audio/voice alignment review; refusing to relabel an unverified clip")


def main() -> None:
    story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    voice=story['narration_spec']['voice_id']
    review_file=HERE/'audio/review.json'
    review_doc=json.loads(review_file.read_text()) if review_file.exists() else {}
    reviews={r['id']:r for r in review_doc.get('clips', [])}
    clips=[]; missing=[]
    for shot in story['shots']:
        path=HERE/'audio'/f"{shot['id']}.mp3"
        if not path.is_file():
            missing.append(shot['id']);continue
        require_review(shot,path,voice,reviews)
        source=duration(path); target=float(shot['duration'])
        # Shared pace: slow a rushed read down, compress a dragging one, refuse both
        # extremes instead of hiding them behind a shot-window squeeze.
        speed=pace.tempo(shot['narration'],source,target)
        speech=source/speed
        if speech>target+0.02:
            raise SystemExit(f"{shot['id']}: even at {speech/source:.3f}x the line runs {speech:.2f}s "
                             f"past its {target:.0f}s shot; shorten the line or re-record it")
        if speed>1.55+1e-9:
            raise SystemExit(f"{shot['id']}: narration needs {speed:.3f}x, over the 1.55x hard limit")
        clips.append({'id':shot['id'],'file':path.name,'text':shot['narration'],'sha256':digest(path),
                      'voice_id':voice,'voice_description':story['narration_spec']['description'],
                      'narration_id':shot['narration_id'],'target_start':shot['start'],
                      'target_duration':shot['duration'],'alignment':'shot-locked',
                      'source_duration':round(source,3),'atempo':round(speed,4),
                      'speech_seconds':round(speech,3),
                      'hanzi_per_second':pace.rate(shot['narration'],speech),
                      'tail_silence_seconds':round(max(0.0,target-speech),3)})
    if missing:
        raise SystemExit('Missing narration: '+', '.join(missing))
    rates=[c['hanzi_per_second'] for c in clips]
    manifest={'language':'zh-CN','voice':voice,'generation':'Arena TTS; one independent clip per shot',
              'alignment':'one-clip-one-shot-one-caption','max_speedup_factor':1.55,
              'pace':{'target_hanzi_per_second':pace.TARGET_HANZI_PER_SECOND,
                      'min_tempo':pace.MIN_TEMPO,'max_tempo':pace.MAX_TEMPO,
                      'slowdown_allowed':True,
                      'note':'clips are slowed or compressed to one shared pace; out-of-range lines fail instead of being rushed'},
              'slowdown_allowed':True,'clips':clips}
    (HERE/'audio'/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Wrote manifest for {len(clips)} shot-locked clips; tempo {min(x['atempo'] for x in clips):.3f}-{max(x['atempo'] for x in clips):.3f}x; "
          f"pace {min(rates):.2f}-{max(rates):.2f} Hanzi/s")
if __name__=='__main__': main()
