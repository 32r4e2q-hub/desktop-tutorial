#!/usr/bin/env python3
"""Resume the saved v4 project, export a new explicitly versioned delivery, and verify it.

No new generative API calls. Large masters/caches stay in ignored directories.
Usage: .venv/bin/python ripper/finish.py [--export-only] [--workers 2]
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.io import wavfile
from scipy import signal

import assemble as A

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DELIVERY = HERE / 'deliverable'
VERSION = A.RENDER_VERSION
NAME = 'ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def progress(stage, **extra):
    write_json(DELIVERY / 'status.json', {
        'version': VERSION, 'stage': stage,
        'updated_at': datetime.now(timezone.utc).isoformat(), **extra,
    })
    print('\nSTAGE:', stage, extra, flush=True)


def verify_sources():
    manifest = json.loads((HERE / 'source_manifest.json').read_text())
    for asset in manifest['assets']:
        path = ROOT / asset['path']
        data = path.read_bytes()
        git_sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if len(data) != asset['size'] or git_sha != asset['sha']:
            raise RuntimeError(f'Source differs from pinned latest asset: {path}')
    return manifest


def stamp(seconds):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def export_subtitles(blocks):
    bounds = json.loads((Path(A.BUILD) / 'subtitle_bounds.json').read_text())
    cues = []
    for block in blocks:
        key = block['vo']
        for i, text in enumerate(A.NARRATION[key]):
            start = block['start'] + A.PRE_ROLL + bounds[key][i]
            end = block['start'] + A.PRE_ROLL + bounds[key][i + 1]
            cues.append(f'{len(cues) + 1}\n{stamp(start)} --> {stamp(end)}\n{text}\n')
    (DELIVERY / 'subtitles.srt').write_text('\n'.join(cues), encoding='utf-8')
    return len(cues)


def narration_alignment(path, blocks):
    # Compare decoded delivered speech to each original, rather than just checking for loud audio.
    sr, mixed = wavfile.read(Path(A.BUILD) / 'qc_audio.wav')
    mixed = mixed.astype(np.float64) / 32768
    results = []
    for block in blocks:
        raw = subprocess.check_output([
            A.FFMPEG, '-v', 'error', '-i', str(Path(A.VO) / (block['vo'] + '.mp3')),
            '-t', '8', '-ac', '1', '-ar', str(sr), '-f', 's16le', '-',
        ])
        template = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
        expected = block['start'] + A.PRE_ROLL
        begin = max(0, int((expected - 0.35) * sr))
        end = min(len(mixed), int((expected + 0.35) * sr) + len(template))
        window = mixed[begin:end]
        correlation = signal.correlate(window, template, mode='valid', method='fft')
        peak = int(np.argmax(correlation))
        aligned = window[peak:peak + len(template)]
        score = float(np.corrcoef(aligned, template)[0, 1])
        delta = (begin + peak) / sr - expected
        results.append({'vo': block['vo'], 'offset_error_seconds': round(delta, 5),
                        'correlation': round(score, 4), 'passed': abs(delta) <= 0.10 and score >= 0.7})
    return results


def inspect_export(path, total, blocks):
    report = A.qc(str(path), total, blocks)
    decoded = subprocess.run([A.FFMPEG, '-v', 'error', '-xerror', '-i', str(path), '-f', 'null', '-'],
                             capture_output=True, text=True)
    report['full_decode_ok'] = decoded.returncode == 0
    if decoded.returncode:
        report['problems'].append('Full decode failed: ' + decoded.stderr[-2000:])
    cap = cv2.VideoCapture(str(path))
    report['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    report['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    report['fps'] = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if (report['width'], report['height']) != (1080, 1920) or abs(report['fps'] - 24) > 0.001:
        report['problems'].append('Unexpected delivered video dimensions/fps')
    if report['frames'] != round(total * A.FPS):
        report['problems'].append('Incomplete frame count')
    if 'h264' not in report['probe'] or 'aac' not in report['probe']:
        report['problems'].append('Expected H.264/AAC streams')
    if not (-30 < report['audio_rms_db'] < -10) or report['audio_peak_db'] >= 0:
        report['problems'].append('Audio loudness/peak outside delivery limits')
    report['narration_alignment'] = narration_alignment(path, blocks)
    if not all(row['passed'] for row in report['narration_alignment']):
        report['problems'].append('Narration alignment did not pass')
    report['subtitle_safe_width_pixels'] = int(A.W * 0.84)
    report['subtitle_lines_fit'] = all(
        A.render_text(line, A.subtitle_size(line), False, (245, 240, 230), 3, (10, 8, 6))[0].shape[1]
        <= int(A.W * 0.84) for lines in A.NARRATION.values() for line in lines
    )
    if not report['subtitle_lines_fit']:
        report['problems'].append('Subtitle exceeds safe width')
    report['version'] = VERSION
    report['passed'] = not report['problems']
    return report


def preview_sheet(path, timeline):
    cols, tw, th, label = 7, 180, 320, 28
    rows = math.ceil(len(timeline) / cols)
    canvas = Image.new('RGB', (cols * tw, rows * (th + label)), '#10131a')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(HERE / 'assets/fonts/NotoSansCJKsc-Regular.otf'), 14)
    cap = cv2.VideoCapture(str(path))
    for i, shot in enumerate(timeline):
        t = shot['start'] + shot['dur'] * 0.5
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f'Cannot preview {shot["id"]}')
        thumb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize((tw, th), Image.Resampling.LANCZOS)
        x, y = (i % cols) * tw, (i // cols) * (th + label)
        canvas.paste(thumb, (x, y))
        draw.text((x + 8, y + th + 3), f'{shot["id"]}  {t:06.2f}s', font=font, fill='#ede4cf')
    cap.release()
    canvas.save(DELIVERY / 'preview_sheet.jpg', quality=88)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--export-only', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error('--workers must be between 1 and 4')
    DELIVERY.mkdir(parents=True, exist_ok=True)
    progress('verifying_saved_sources')
    source = verify_sources()
    subprocess.run([sys.executable, str(HERE / 'vo_align.py')], check=True)
    timeline, blocks, total, _ = A.build_timeline()
    write_json(DELIVERY / 'timeline.json', {'total_seconds': total, 'shots': [
        {k:v for k,v in shot.items() if k != 'path'} for shot in timeline]})
    cues = export_subtitles(blocks)
    if not args.export_only:
        progress('rendering_latest_saved_v4', duration_seconds=total, clips=len(timeline))
        subprocess.run([sys.executable, str(HERE / 'assemble.py'), 'render', '--workers', str(args.workers), '--incremental'], check=True)
    if not Path(A.FINAL).exists():
        raise RuntimeError('No rendered master available')
    progress('encoding_delivery')
    encoded = Path(A.OUT) / NAME
    # The legacy preview mux uses -shortest and drops a last frame when the WAV ends
    # between frame boundaries. Encode from the complete picture stream + original WAV,
    # padding only the sub-frame audio tail; never weaken the strict final frame-count QC.
    full_video = Path(A.BUILD) / 'video_only.mp4'
    soundtrack = Path(A.BUILD) / 'soundtrack.wav'
    cap = cv2.VideoCapture(str(full_video))
    full_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if full_frames != round(total * A.FPS):
        raise RuntimeError(f'Incomplete picture master: {full_frames} frames')
    exact_end = full_frames / A.FPS
    subprocess.run([
        A.FFMPEG, '-hide_banner', '-loglevel', 'warning', '-y',
        '-i', str(full_video), '-i', str(soundtrack),
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'veryfast',
        '-b:v', '3500k', '-maxrate', '5000k', '-bufsize', '7000k',
        '-profile:v', 'high', '-level:v', '4.1', '-pix_fmt', 'yuv420p', '-threads', '2',
        '-af', f'apad=whole_dur={exact_end:.9f}', '-t', f'{exact_end:.9f}',
        '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart',
        '-metadata', 'title=白教堂的雾 — 开膛手杰克 · v4.1续做版',
        '-metadata', 'comment=New export resumed from saved v4; not the unlocated original session export.',
        str(encoded),
    ], check=True)
    progress('checking_delivery')
    report = inspect_export(encoded, total, blocks)
    write_json(DELIVERY / 'qc_report.json', report)
    if not report['passed']:
        raise RuntimeError('Export failed QC: ' + '; '.join(report['problems']))
    preview_sheet(encoded, timeline)
    downloads = Path('/home/user/downloads')
    downloads.mkdir(parents=True, exist_ok=True)
    deliverable = downloads / NAME
    shutil.copy2(encoded, deliverable)
    # Only archive the exact obsolete v3 file this agent retrieved earlier; do not touch user files.
    old = downloads / 'ripper_whitechapel_fog_1080x1920.mp4'
    if old.exists():
        data = old.read_bytes()
        old_hash = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if old_hash == 'f8c18a9a6d589a8b7c17f12651831cd889cc73a9':
            cache = ROOT / '.cache/ripper-resume'
            cache.mkdir(parents=True, exist_ok=True)
            old.replace(cache / 'previous_v3.mp4')
    fingerprints = {str(p.relative_to(ROOT)): sha256(p) for p in [
        HERE / 'assemble.py', HERE / 'finish.py', HERE / 'vo_align.py', HERE / 'shots.json',
        HERE / 'requirements.txt', HERE / 'engine/audio.py', HERE / 'engine/text.py', HERE / 'engine/common.py',
        Path(A.BUILD) / 'subtitle_bounds.json',
    ]}
    manifest = {
        'title': '白教堂的雾 — 开膛手杰克', 'version': VERSION,
        'status': 'automated_qc_passed_visual_review_pending',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source_commit': source['source_commit'], 'last_source_edit_commit': source['last_edit_commit'],
        'session_branch': 'arena/01a076fd-desktop-tutorial',
        'provenance_note': 'New export from saved v4 inputs. Original Arena conversation cannot be loaded; this is not claimed to be its last 88MB export.',
        'file': NAME, 'download_file': str(deliverable), 'size_bytes': deliverable.stat().st_size,
        'sha256': sha256(deliverable), 'duration_seconds': report['duration'],
        'width': report['width'], 'height': report['height'], 'fps': report['fps'],
        'shots': len(timeline), 'narration_blocks': len(blocks), 'subtitle_cues': cues,
        'qc_passed': report['passed'], 'production_file_sha256': fingerprints,
    }
    write_json(DELIVERY / 'final_manifest.json', manifest)
    progress('automated_qc_passed_visual_review_pending', file=str(deliverable), size_bytes=deliverable.stat().st_size)
    print('DELIVERABLE_READY', deliverable, flush=True)
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        progress('failed', error=str(exc))
        raise
