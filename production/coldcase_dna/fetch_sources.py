#!/usr/bin/env python3
"""Restore verified generated footage from project results.json into work destination."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dest', type=Path, required=True)
    args = parser.parse_args()
    args.dest.mkdir(parents=True, exist_ok=True)
    results_path = HERE / 'results.json'
    if not results_path.exists():
        print(f"results.json not found in {HERE}; nothing to fetch")
        return 0
    results = json.loads(results_path.read_text())
    shots = results.get('shots', {})
    for sid, shot in shots.items():
        if shot.get('status') != 'completed':
            continue
        dest_file = args.dest / f"{sid}.mp4"
        sha = shot.get('sha256')
        if dest_file.exists() and digest(dest_file) == sha:
            print(f"reusing verified {dest_file}")
            continue
        url = shot.get('video_url')
        if url:
            print(f"downloading {sid} from {url}...")
            urllib.request.urlretrieve(url, dest_file)
            if sha and digest(dest_file) != sha:
                raise RuntimeError(f"Digest mismatch for {sid}: expected {sha}, got {digest(dest_file)}")
            print(f"saved {dest_file}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
