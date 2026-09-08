#!/usr/bin/env python3
"""Reassemble + verify a delivery that is stored in Git as 45 MB parts.

Same scheme the repo already uses for `production/new_source_parts` (bailin.mp4): cat the parts, then
check the SHA-256 recorded in manifest.json. Use `--emit` to actually write the reassembled file.

Usage:
  python3 deliverable/verify_parts.py deliverable/v4_2/parts                # verify only
  python3 deliverable/verify_parts.py deliverable/v4_2/parts --emit out.mp4 # write + verify
"""
import hashlib
import json
import sys
from pathlib import Path


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        raise SystemExit(__doc__)
    parts_dir = Path(args[0])
    emit = None
    if '--emit' in sys.argv:
        i = sys.argv.index('--emit')
        emit = Path(sys.argv[i + 1]) if len(sys.argv) > i + 1 else parts_dir.parent / 'delivery.mp4'

    manifest = json.loads((parts_dir / 'manifest.json').read_text(encoding='utf-8'))
    names = manifest['parts']
    hasher, total = hashlib.sha256(), 0
    sink = open(emit, 'wb') if emit else None
    try:
        for name in names:
            data = (parts_dir / name).read_bytes()
            total += len(data)
            hasher.update(data)
            if sink:
                sink.write(data)
    finally:
        if sink:
            sink.close()
    sha = hasher.hexdigest().upper()
    expected = manifest['sha256'].upper()
    size_ok = total == manifest['size']
    sha_ok = sha == expected
    print(f'parts      : {len(names)} × ≤{manifest["part_size"]:,} B  ({total:,} bytes)')
    print(f'assembled  : {manifest["name"]}')
    print(f'size       : {"OK" if size_ok else "MISMATCH"} ({total:,} vs {manifest["size"]:,})')
    print(f'sha256     : {"OK" if sha_ok else "MISMATCH"}')
    print(f'             computed  {sha}')
    print(f'             manifest  {expected}')
    if emit:
        print(f'written    : {emit}')
    if not (size_ok and sha_ok):
        raise SystemExit(1)
    print('RESULT     : OK — byte-identical to what was rendered')


if __name__ == '__main__':
    main()
