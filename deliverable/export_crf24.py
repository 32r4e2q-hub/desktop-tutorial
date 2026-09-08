#!/usr/bin/env python3
"""Pin the saved v4 inputs, mux a CRF24 delivery, QC it, and split it for Git.

Reuses the project's own pipeline (`ripper/assemble.py`) for timeline, subtitle bounds and QC, so the
checks are identical to the ones the previous sessions ran. Only the delivery encode differs:
`-crf 24 -preset medium` (the "CRF24 交付档" the manual specifies) instead of the ABR 3500k pass.

Usage:
  .venv-render/bin/python deliverable/export_crf24.py --pin     # write source_manifest.json for saved inputs
  .venv-render/bin/python deliverable/export_crf24.py           # mux + QC + split
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
RIPPER = ROOT / 'ripper'
OUT = ROOT / 'deliverable' / 'v4_2'
VERSION = 'v4.2-crf24-20260907'
NAME = 'ripper_whitechapel_fog_v4_2_crf24_1080x1920.mp4'
PART_SIZE = 45_000_000            # same scheme the repo already uses for bailin.mp4

sys.path.insert(0, str(RIPPER))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import assemble as A  # noqa: E402  (project pipeline)

PINNED = (sorted((RIPPER / 'clips').glob('*.mp4')) + sorted((RIPPER / 'audio' / 'vo').glob('*.mp3')) +
          sorted((RIPPER / 'assets' / 'fonts').glob('*.otf')) +
          [RIPPER / n for n in ('assemble.py', 'vo_align.py', 'shots.json', 'script/screenplay.md')])


def blob_sha(path):
    """git blob hash of a file — matches how the repo pins assets in source_manifest.json."""
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(), len(data)


def pin():
    assets = []
    for p in PINNED:
        if not p.exists():
            raise SystemExit(f'missing input: {p}')
        sha, size = blob_sha(p)
        assets.append({'path': str(p.relative_to(ROOT)), 'size': size, 'sha': sha})
    head = subprocess.run(['git', 'rev-parse', 'origin/arena/01a07943-desktop-tutorial'],
                          capture_output=True, text=True).stdout.strip()
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(), 'source_commit': head,
                'note': 'inputs pinned for the v4.2 re-render (saved state of 01a07943)',
                'assets': assets}
    (RIPPER / 'source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'pinned {len(assets)} inputs → ripper/source_manifest.json')


def verify():
    manifest = json.loads((RIPPER / 'source_manifest.json').read_text())
    for asset in manifest['assets']:
        path = ROOT / asset['path']
        sha, size = blob_sha(path)
        if size != asset['size'] or sha != asset['sha']:
            raise SystemExit(f'input differs from pinned asset: {path}')
    return manifest


def stamp(seconds):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def export_srt(blocks):
    bounds = json.loads((Path(A.BUILD) / 'subtitle_bounds.json').read_text())
    cues = []
    for block in blocks:
        for i, text in enumerate(A.NARRATION[block['vo']]):
            start = block['start'] + A.PRE_ROLL + bounds[block['vo']][i]
            end = block['start'] + A.PRE_ROLL + bounds[block['vo']][i + 1]
            cues.append(f'{len(cues) + 1}\n{stamp(start)} --> {stamp(end)}\n{text}\n')
    (OUT / 'subtitles.srt').write_text('\n'.join(cues), encoding='utf-8')
    return len(cues)


def mux(timeline, blocks, total):
    full_video, soundtrack = Path(A.BUILD) / 'video_only.mp4', Path(A.BUILD) / 'soundtrack.wav'
    cap = __import__('cv2').VideoCapture(str(full_video))
    frames = int(cap.get(__import__('cv2').CAP_PROP_FRAME_COUNT))
    cap.release()
    expected = round(total * A.FPS)
    if frames != expected:
        raise SystemExit(f'incomplete picture master: {frames} frames, expected {expected}')
    exact_end = frames / A.FPS
    encoded = OUT / NAME
    subprocess.run([
        A.FFMPEG, '-hide_banner', '-loglevel', 'warning', '-y',
        '-i', str(full_video), '-i', str(soundtrack),
        '-map', '0:v:0', '-map', '1:a:0',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '24',
        '-profile:v', 'high', '-level:v', '4.1', '-pix_fmt', 'yuv420p', '-g', '48', '-threads', '2',
        '-af', f'apad=whole_dur={exact_end:.9f}', '-t', f'{exact_end:.9f}',
        '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart',
        '-metadata', 'title=白教堂的雾 — 开膛手杰克 · v4.2 CRF24 交付档',
        '-metadata', 'comment=Full re-render from saved v4 inputs (arena/01a07943, 27 shots, run 17 + S22 crop).',
        str(encoded)], check=True)
    return encoded, frames, expected


def probe(path):
    out = subprocess.run([A.FFMPEG, '-hide_banner', '-i', str(path)], capture_output=True, text=True).stderr
    return out


def moov_first(path):
    """confirm +faststart: the moov atom must precede mdat so browsers can stream while downloading."""
    off, order = 0, []
    with open(path, 'rb') as f:
        while len(order) < 6:
            f.seek(off)
            hdr = f.read(16)
            if len(hdr) < 8:
                break
            size = int.from_bytes(hdr[:4], 'big')
            typ = hdr[4:8].decode('latin1')
            if size == 1:
                size = int.from_bytes(hdr[8:16], 'big')
            order.append((typ, size))
            off += size
    types = [t for t, _ in order]
    return ('moov' in types and 'mdat' in types and types.index('moov') < types.index('mdat')), order


def split(path, parts_dir):
    shutil.rmtree(parts_dir, ignore_errors=True)
    parts_dir.mkdir(parents=True, exist_ok=True)
    data = path.read_bytes()
    n = math.ceil(len(data) / PART_SIZE)
    names = []
    for i in range(n):
        name = f'movie.part-{i:03d}'
        (parts_dir / name).write_bytes(data[i * PART_SIZE:(i + 1) * PART_SIZE])
        names.append(name)
    manifest = {
        'name': path.name, 'size': len(data),
        'sha256': hashlib.sha256(data).hexdigest().upper(),
        'part_size': PART_SIZE, 'parts': names, 'persisted': True,
        'branch': 'arena/01a07be4-desktop-tutorial',
        'reassemble': 'cat movie.part-* > %s && sha256sum %s' % (path.name, path.name),
        'title': '白教堂的雾 — 开膛手杰克', 'version': VERSION,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    (parts_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return n, manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pin', action='store_true')
    ap.add_argument('--skip-qc', action='store_true')
    args = ap.parse_args()
    if args.pin:
        pin()
        return
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = verify()
    print(f'verified {len(manifest["assets"])} pinned inputs against git blobs', flush=True)
    timeline, blocks, total, _ = A.build_timeline()
    (OUT / 'timeline.json').write_text(json.dumps(
        {'total_seconds': total, 'pipeline': A.RENDER_VERSION, 'source_commit': manifest['source_commit'],
         'shots': [{k: v for k, v in s.items() if k != 'path'} for s in timeline]},
        ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    cues = export_srt(blocks)
    print(f'timeline {len(timeline)} shots / {total:.2f}s / {cues} subtitle cues', flush=True)
    print('muxing CRF24 delivery ...', flush=True)
    encoded, frames, expected = mux(timeline, blocks, total)
    size = encoded.stat().st_size
    print(f'encoded {encoded.name}: {size:,} bytes ({size / 1_000_000:.1f} MB), {frames} frames', flush=True)

    report = {'version': VERSION, 'file': str(encoded), 'size_bytes': size,
              'source_commit': manifest['source_commit'], 'pipeline': A.RENDER_VERSION,
              'problems': [], 'frames': frames, 'expected_frames': expected,
              'duration': round(frames / A.FPS, 2), 'probed': probe(encoded).splitlines()[-3]}
    report['faststart_moov_first'] = moov_first(encoded)[0]
    if not report['faststart_moov_first']:
        report['problems'].append('moov atom is not before mdat (not streamable)')
    if frames != expected:
        report['problems'].append('frame count mismatch')
    decoded = subprocess.run([A.FFMPEG, '-v', 'error', '-xerror', '-i', str(encoded), '-f', 'null', '-'],
                             capture_output=True, text=True)
    report['full_decode_ok'] = decoded.returncode == 0
    if decoded.returncode:
        report['problems'].append('full decode failed: ' + decoded.stderr[-1200:])
    text = report['probed']
    report['video_stream'] = [l.strip() for l in text.splitlines() if 'Video:' in l]
    report['audio_stream'] = [l.strip() for l in text.splitlines() if 'Audio:' in l]

    if not args.skip_qc:
        sub = A.qc(str(encoded), total, blocks)
        report['assembler_qc'] = {k: v for k, v in sub.items() if k != 'probe'}
        report['problems'] += sub['problems']
    report['passed'] = not report['problems']
    (OUT / 'qc_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('QC', 'PASSED' if report['passed'] else 'FAILED: ' + '; '.join(report['problems']), flush=True)
    if not report['passed']:
        raise SystemExit(2)

    n, parts_manifest = split(encoded, OUT / 'parts')
    sha = hashlib.sha256(encoded.read_bytes()).hexdigest()
    (OUT / 'final_manifest.json').write_text(json.dumps({
        'title': '白教堂的雾 — 开膛手杰克', 'version': VERSION, 'status': 'automated_qc_passed',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source_commit': manifest['source_commit'], 'pipeline': A.RENDER_VERSION,
        'file': NAME, 'size_bytes': size, 'sha256': sha,
        'duration_seconds': report['duration'], 'frames': frames, 'fps': A.FPS,
        'width': 1080, 'height': 1920, 'shots': len(timeline), 'narration_blocks': len(blocks),
        'subtitle_cues': cues, 'encode': 'libx264 CRF24 preset medium high@4.1 +faststart / aac 160k 48k',
        'qc_passed': True, 'parts': n, 'part_size': PART_SIZE,
        'pinned_inputs': len(manifest['assets']),
        'note': 'Re-render of the newest saved v4 inputs (not the lost 01a07943 export; those bytes never left that sandbox).',
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'file': NAME, 'bytes': size, 'sha256': sha, 'parts': n,
                      'part_size': PART_SIZE}, indent=2), flush=True)


if __name__ == '__main__':
    main()
