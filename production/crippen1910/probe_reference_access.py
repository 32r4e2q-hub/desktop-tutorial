#!/usr/bin/env python3
"""Verify public immutable image URLs from the cloud; no model calls or credentials."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import urllib.request
import urllib.error

HERE = Path(__file__).resolve().parent


def inspect_png(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Reference response is not a PNG image')
    return struct.unpack('>II', data[16:24])


def main() -> int:
    revision = os.environ.get('GITHUB_SHA', '')
    if not re.fullmatch('[a-f0-9]{40}', revision):
        raise ValueError('GITHUB_SHA must identify the immutable uploaded asset commit')
    story = json.loads((HERE/'story.json').read_text())
    report = dict(source_revision=revision, generation_submitted=False,
                  credentials_sent_to_image_host=False, assets=[], missing_local=[])
    for ref in story['reference_images']:
        local = HERE/ref['file']
        if not local.is_file():
            report['missing_local'].append(ref['id'])
            continue
        url = f"https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/{revision}/production/crippen1910/{ref['file']}"
        expected = hashlib.sha256(local.read_bytes()).hexdigest()
        row = dict(id=ref['id'], url=url, expected_sha256=expected, verified=False)
        # This request intentionally has NO Authorization header. The generator must be
        # able to give these links to an external provider without leaking GitHub tokens.
        request = urllib.request.Request(url, headers={'User-Agent':'crippen-reference-preflight/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read(15*1024*1024+1)
                row['http_status'] = response.status
            row['bytes'] = len(data)
            row['sha256'] = hashlib.sha256(data).hexdigest()
            row['dimensions'] = list(inspect_png(data))
            row['verified'] = (row['sha256'] == expected and len(data)<15*1024*1024
                               and all(256<=d<=5760 for d in row['dimensions']))
        except urllib.error.HTTPError as exc:
            row['http_status'] = exc.code
        except Exception as exc:
            row['error_type'] = type(exc).__name__
        report['assets'].append(row)
        print(ref['id'], 'verified' if row['verified'] else 'FAILED', flush=True)
    report['published_assets_verified'] = bool(report['assets']) and all(row['verified'] for row in report['assets'])
    report['story_reference_files_complete'] = not report['missing_local']
    package_path=HERE/'reference/character-packages.json'
    packages=json.loads(package_path.read_text()).get('packages', []) if package_path.is_file() else []
    report['character_views_missing']=[package['id']+'/'+view for package in packages for view,relative in package['views'].items() if not (HERE/relative).is_file()]
    report['reference_package_complete'] = (report['story_reference_files_complete'] and len(packages)==10 and not report['character_views_missing'])
    report['visual_approval_implied'] = False
    (HERE/'reference-access.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    return 0 if report['published_assets_verified'] else 1


if __name__=='__main__':
    raise SystemExit(main())
