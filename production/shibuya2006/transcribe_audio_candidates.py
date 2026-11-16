#!/usr/bin/env python3
"""Independently transcribe narration candidates; never silently sign off alignment.
Runs on the media runner, where the multilingual ASR model can be downloaded.
This is transcription only, not speech synthesis or a substitute for missing audio.
"""
import difflib
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def normalize(text):
    from opencc import OpenCC
    return re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', OpenCC('t2s').convert(text)).lower()


def main():
    from faster_whisper import WhisperModel
    model = WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=4)
    story = json.loads((HERE/'story.json').read_text())
    candidates = json.loads((HERE/'qa/group-tts-split-candidates.json').read_text())
    by_id = {r['id']: r for r in candidates['clips']}
    rows = []
    report = HERE/'qa/narration-asr.json'
    for shot in story['shots']:
        sid = shot['id']
        path = HERE/'audio'/f'{sid}.mp3'
        kind = 'individual'
        if not path.exists():
            c = by_id.get(sid)
            if c is None:
                rows.append({'id': sid, 'status': 'missing_audio', 'expected': shot['narration']})
                continue
            path = ROOT/c['file']
            kind = 'pause_cut_candidate'
        segments, info = model.transcribe(str(path), language='zh', beam_size=5,
                                         word_timestamps=True, vad_filter=False,
                                         condition_on_previous_text=False)
        segments = list(segments)
        heard = ''.join(s.text for s in segments).strip()
        similarity = difflib.SequenceMatcher(None, normalize(shot['narration']), normalize(heard)).ratio()
        rows.append({'id': sid, 'source_kind': kind, 'file': str(path.relative_to(ROOT)),
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'expected': shot['narration'], 'asr_text': heard,
                     'similarity': round(similarity, 4),
                     'status': 'asr_match_needs_review' if similarity >= .90 else 'inspect_transcript_or_boundary',
                     'segments': [{'start': s.start, 'end': s.end, 'text': s.text,
                                   'words': [{'start': w.start, 'end': w.end, 'word': w.word, 'probability': w.probability}
                                             for w in s.words or []]} for s in segments]})
        report.write_text(json.dumps({'model': 'faster-whisper small multilingual int8',
                                      'policy': 'ASR evidence only; no alignment signoffs or final manifest auto-created',
                                      'shots': rows}, ensure_ascii=False, indent=2)+'\n')
        print(f'{sid}: {similarity:.3f} | {heard}', flush=True)
    report.write_text(json.dumps({'model': 'faster-whisper small multilingual int8',
                                  'policy': 'ASR evidence only; no alignment signoffs or final manifest auto-created',
                                  'shots': rows}, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
