#!/usr/bin/env python3
"""Restore only checksum-matching source clips from original and retake artifacts.

Artifacts expire, so render.py may still need its verified provider-URL fallback.
No filename, artifact order, or provider URL is trusted in place of receipt SHA/size.
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def restore(results, source_dirs, dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    restored, missing = [], []
    for sid, row in sorted(results.get('shots', {}).items()):
        if row.get('status') != 'completed' or not row.get('sha256') or not row.get('bytes'):
            missing.append(sid)
            continue
        candidates = [p for folder in source_dirs for p in Path(folder).rglob(f'{sid}.mp4') if p.is_file()]
        target = dest / f'{sid}.mp4'
        if target.is_file(): candidates.insert(0, target)
        match = next((p for p in candidates if p.stat().st_size == int(row['bytes']) and digest(p) == row['sha256']), None)
        if match is None:
            missing.append(sid)
        else:
            if match.resolve() != target.resolve(): shutil.copy2(match, target)
            restored.append(sid)
    return restored, missing

if __name__ == '__main__':
    results = json.loads((ROOT/'production/nowon2021/results.json').read_text(encoding='utf-8'))
    stage = ROOT/'work/nowon2021/restored-artifacts'
    done, missing = restore(results, [stage/'original', stage/'retakes', stage/'second-retakes', stage/'third-retakes', stage/'fourth-retakes'], ROOT/'work/nowon2021/clips')
    print(f'Restored {len(done)} SHA-verified clips from Actions artifacts; {len(missing)} absent, rendering will try verified provider URL fallback: {missing}')
