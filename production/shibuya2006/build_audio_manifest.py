#!/usr/bin/env python3
"""Bind selected-voice MP3s to the shot-locked narration and report safe fit rates.
Run after all 30 S01.mp3..S30.mp3 files exist; never silently invent missing audio.
"""
from __future__ import annotations
import hashlib, json, re, subprocess
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

PAUSE_CAP_SECONDS = 0.45
PAUSE_KEPT_SECONDS = 0.25


def voiced_span(path: Path) -> dict:
    """Speech time with leading/trailing/internal silence removed.

    Pace must be measured against what is actually spoken: take files pad differently,
    and pacing against the padded length is what made the v5 film uneven.
    """
    out=subprocess.run(['ffmpeg','-hide_banner','-i',str(path),'-af',
                        'silencedetect=noise=-40dB:d=0.12','-f','null','-'],
                       capture_output=True,text=True).stderr
    match=re.search(r'Duration: (\d+):(\d+):([\d.]+)',out)
    if not match:
        raise RuntimeError(f'cannot measure {path.name}')
    total=int(match.group(1))*3600+int(match.group(2))*60+float(match.group(3))
    starts=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',out)]
    ends=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',out)]
    silence=0.0
    long_pauses=0
    for index,start in enumerate(starts):
        stop=ends[index] if index<len(ends) else total
        length=max(0.0,stop-start)
        silence+=length
        if length>=PAUSE_CAP_SECONDS:
            long_pauses+=1
    voiced=max(0.0,total-silence)
    # The renderer caps long internal pauses (they are dead air, not pace), so the
    # length a line will actually occupy is the voiced time plus the shortened pauses.
    capped=voiced+long_pauses*PAUSE_KEPT_SECONDS
    return {'total':total,'voiced':voiced,'capped':capped,'long_pauses':long_pauses}


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
        span=voiced_span(path)
        voiced, capped = span['voiced'], span['capped']
        # Shared pace, measured on spoken time: slow a rushed read down, compress a
        # dragging one, refuse both extremes instead of hiding them in a shot squeeze.
        speed=pace.tempo(shot['narration'],voiced,target)
        speech=capped/speed
        if speech>target+0.02:
            raise SystemExit(f"{shot['id']}: even at {speed:.3f}x the line speaks {speech:.2f}s "
                             f"past its {target:.0f}s shot; shorten the line or re-record it")
        if speed>1.55+1e-9:
            raise SystemExit(f"{shot['id']}: narration needs {speed:.3f}x, over the 1.55x hard limit")
        clips.append({'id':shot['id'],'file':path.name,'text':shot['narration'],'sha256':digest(path),
                      'voice_id':voice,'voice_description':story['narration_spec']['description'],
                      'narration_id':shot['narration_id'],'target_start':shot['start'],
                      'target_duration':shot['duration'],'alignment':'shot-locked',
                      'source_duration':round(source,3),'voiced_duration':round(voiced,3),
                      'capped_duration':round(capped,3),'long_pauses':span['long_pauses'],
                      'atempo':round(speed,4),'speech_seconds':round(speech,3),
                      'hanzi_per_second':pace.delivered_rate(shot['narration'],voiced,speed),
                      'tail_silence_seconds':round(max(0.0,target-speech),3)})
    if missing:
        raise SystemExit('Missing narration: '+', '.join(missing))
    rates=[c['hanzi_per_second'] for c in clips]
    manifest={'language':'zh-CN','voice':voice,'generation':'Arena TTS; one independent clip per shot',
              'alignment':'one-clip-one-shot-one-caption','max_speedup_factor':1.55,
              'pace':{'target_hanzi_per_second':pace.TARGET_VOICED_HANZI_PER_SECOND,
                      'measured_on':'spoken time (silence stripped), not file length',
                      'min_tempo':pace.MIN_TEMPO,'max_tempo':pace.MAX_TEMPO,
                      'slowdown_allowed':True,
                      'note':'clips are slowed or compressed to one shared pace; out-of-range lines fail instead of being rushed'},
              'slowdown_allowed':True,'clips':clips}
    (HERE/'audio'/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"Wrote manifest for {len(clips)} shot-locked clips; tempo {min(x['atempo'] for x in clips):.3f}-{max(x['atempo'] for x in clips):.3f}x; "
          f"pace {min(rates):.2f}-{max(rates):.2f} Hanzi/s")
if __name__=='__main__': main()
