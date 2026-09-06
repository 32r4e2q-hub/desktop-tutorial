#!/usr/bin/env python3
"""Restore pinned, existing video/voice assets. Does not generate or buy new media.

Requires the user's existing `gh` GitHub connection. Binary files live in .cache,
not Git; this script verifies Git blob hashes and recreates local symlinks.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CACHE = ROOT / '.cache' / 'ripper-resume'


def git_hash(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def restore(item, repository):
    relative = Path(item['path'])
    if relative.is_absolute() or '..' in relative.parts or relative.parts[0] != 'ripper':
        raise ValueError(f'Unsafe asset path: {relative}')
    cached = CACHE / 'assets' / relative
    if not cached.exists() or cached.stat().st_size != item['size'] or git_hash(cached.read_bytes()) != item['sha']:
        data = subprocess.check_output([
            'gh', 'api', '-H', 'Accept: application/vnd.github.raw+json',
            f"repos/{repository}/git/blobs/{item['sha']}",
        ])
        if len(data) != item['size'] or git_hash(data) != item['sha']:
            raise RuntimeError(f'Asset verification failed: {relative}')
        cached.parent.mkdir(parents=True, exist_ok=True)
        tmp = cached.with_suffix(cached.suffix + '.part')
        tmp.write_bytes(data)
        tmp.replace(cached)
    local = ROOT / relative
    local.parent.mkdir(parents=True, exist_ok=True)
    if local.is_symlink():
        if local.resolve() == cached.resolve():
            return str(relative)
        raise RuntimeError(f'Refusing to replace existing symlink: {local}')
    if local.exists():
        if git_hash(local.read_bytes()) == item['sha']:
            return str(relative)
        raise RuntimeError(f'Refusing to overwrite changed asset: {local}')
    local.symlink_to(cached)
    return str(relative)


def restore_fonts():
    fonts = CACHE / 'fonts'
    fonts.mkdir(parents=True, exist_ok=True)
    wheel = fonts / 'mplfonts-0.0.11-py3-none-any.whl'
    if not wheel.exists():
        subprocess.run([sys.executable, '-m', 'pip', 'download', 'mplfonts==0.0.11', '--no-deps', '-d', str(fonts)], check=True)
    with zipfile.ZipFile(wheel) as archive:
        for name in ['NotoSansCJKsc-Regular.otf', 'NotoSerifCJKsc-Regular.otf']:
            cached = fonts / name
            cached.write_bytes(archive.read('mplfonts/fonts/' + name))
            local = HERE / 'assets' / 'fonts' / name
            local.parent.mkdir(parents=True, exist_ok=True)
            if not local.exists():
                local.symlink_to(cached)


def main():
    manifest = json.loads((HERE / 'source_manifest.json').read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name in pool.map(lambda item: restore(item, manifest['repository']), manifest['assets']):
            print('VERIFIED', name, flush=True)
    restore_fonts()
    print('Ready: 28 clips, 10 narration MP3s, 2 Chinese fonts.', flush=True)


if __name__ == '__main__':
    main()
