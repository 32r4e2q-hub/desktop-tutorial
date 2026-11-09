#!/usr/bin/env python3
"""Temporarily bridge a verified Actions artifact through GitHub blob storage.

Only small blob identifiers are committed, not the 113 MB video or chunks. The
receiving side must verify each chunk and the complete video SHA before serving.
"""
import base64, hashlib, json, subprocess, sys, tempfile
from pathlib import Path

EXPECTED='ee5342f6ad68fdcf5749d356ea740f41551304fcc077113e4c0e1e020a702b78'
CHUNK=8*1024*1024
REPO='32r4e2q-hub/desktop-tutorial'
OUT=Path('production/nowon2021/video-transfer-manifest.json')
files=list(Path('video').rglob('*未审片无水印.mp4'))
if len(files)!=1: raise RuntimeError('Expected exactly one MP4 in the artifact')
video=files[0]
h=hashlib.sha256()
with video.open('rb') as stream:
    for data in iter(lambda:stream.read(1024*1024),b''):h.update(data)
if h.hexdigest()!=EXPECTED: raise RuntimeError('MP4 source checksum mismatch')
manifest={'state':'uploading','source_run':42596892607,'filename':'episode10_review.mp4','bytes':video.stat().st_size,'sha256':EXPECTED,'parts':[]}
def save():OUT.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save()
with tempfile.TemporaryDirectory() as folder,video.open('rb') as stream:
    request=Path(folder)/'request.json'
    for i in range((video.stat().st_size+CHUNK-1)//CHUNK):
        data=stream.read(CHUNK)
        request.write_text(json.dumps({'content':base64.b64encode(data).decode('ascii'),'encoding':'base64'}),encoding='ascii')
        proc=subprocess.run(['gh','api','-X','POST',f'repos/{REPO}/git/blobs','--input',str(request)],capture_output=True,text=True)
        if proc.returncode: raise RuntimeError(f'blob {i} upload failed: {proc.stderr[:500]}')
        blob=json.loads(proc.stdout)['sha']
        manifest['parts'].append({'index':i,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob':blob})
        save();print(f'Uploaded verified chunk {i+1}, {len(data)} bytes',flush=True)
manifest['state']='complete';save();print(f'Uploaded {len(manifest["parts"])} chunks; source SHA matches',flush=True)
