#!/usr/bin/env python3
"""Create shot-length audio with <=1.10x speedup, padding only, never truncating narration.
Writes reproducible intermediates under work/; not a mastered soundtrack or listening review.
"""
import hashlib
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT/'work'/'baiyin_case'/'audio'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    story = json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    rows = {r['id']: r for r in json.loads((HERE/'qa'/'narration.json').read_text(encoding='utf-8'))}
    ffmpeg = os.environ.get('FFMPEG', 'ffmpeg')
    ffprobe = os.environ.get('FFPROBE', 'ffprobe')
    OUT.mkdir(parents=True, exist_ok=True)
    result = []
    for shot in story['shots'][1:]:
        sid = shot['id']
        row = rows[sid]
        src = HERE/row['file']
        if not src.is_file() or digest(src) != row['sha256']:
            raise SystemExit(f'{sid}: missing or changed audio; run check_narration.py again')
        reserve = 1.0 if sid == 'S25' else 2.0 if sid == 'S30' else 0.0
        available = shot['duration'] - reserve - .08
        factor = max(1.0, row['duration_seconds']/available)
        if factor > 1.1001:
            raise SystemExit(f'{sid}: requires {factor:.4f}x; adjust timeline')
        dest = OUT/f'{sid}.wav'
        audio_filter = f'atempo={factor:.8f},aresample=48000,apad,atrim=duration={shot["duration"]},asetpts=PTS-STARTPTS'
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(src),
                        '-vn', '-af', audio_filter, '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(dest)], check=True)
        probe = subprocess.run([ffprobe, '-v','error', '-show_entries','format=duration', '-of','json', str(dest)],
                               capture_output=True,text=True,check=True)
        actual = float(json.loads(probe.stdout)['format']['duration'])
        if abs(actual-shot['duration']) > .001:
            raise SystemExit(f'{sid}: output duration {actual} != {shot["duration"]}')
        result.append({'id': sid, 'source_sha256': digest(src), 'output_sha256': digest(dest),
                       'source_duration': row['duration_seconds'], 'shot_duration': shot['duration'],
                       'atempo': round(factor, 5), 'reserved_tail_seconds': reserve,
                       'output': str(dest.relative_to(ROOT))})
    (HERE/'qa'/'audio_fit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(f'{len(result)} fitted WAVs: 48kHz stereo, max tempo {max(r["atempo"] for r in result):.4f}; listening QC pending')

if __name__ == '__main__':
    main()
