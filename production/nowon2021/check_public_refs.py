#!/usr/bin/env python3
"""Fail closed before paid video requests if an immutable reference URL isn't public."""
import hashlib
import json
from pathlib import Path
import urllib.request
import generate_clips as gen

project = json.loads(gen.PLAN.read_text(encoding='utf-8'))
gen.validate(project, require_refs=True)
revision = gen.revision()
refs = sorted({rid for shot in project['shots'] for rid in shot['reference_images']})
for rid in refs:
    url = gen.image_urls({'reference_images': [rid]}, revision)[0]
    req = urllib.request.Request(url, headers={'User-Agent': 'Nowon-reference-preflight/1.0'})
    with urllib.request.urlopen(req, timeout=45) as response:
        content = response.read()
    expected = hashlib.sha256((gen.REF / f'{rid}.png').read_bytes()).hexdigest()
    if hashlib.sha256(content).hexdigest() != expected:
        raise RuntimeError(f'{rid}: public reference content differs from approved image')
    print(f'{rid}: public URL and SHA verified', flush=True)
print(f'{len(refs)} immutable public images verified; no Agnes request sent.')
