#!/usr/bin/env python3
"""Restore verified Agnes source clips from their generation receipts, never stills."""
from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'production'))
sys.path.insert(0,str(HERE))
import agnes_video as agnes
from generate import digest, request_hash


def restore(story: dict, results: dict, dest: Path) -> list[Path]:
    dest.mkdir(parents=True,exist_ok=True)
    files=[]
    for shot in story['shots']:
        sid=shot['id']; row=results.get('shots',{}).get(sid,{})
        if row.get('status') != 'completed' or row.get('request_hash') != request_hash(story,shot):
            raise RuntimeError(f'{sid}: missing verified current-prompt completion')
        url=row.get('video_url'); expected=row.get('sha256'); size=row.get('bytes')
        if not url or not expected or not size:
            raise RuntimeError(f'{sid}: incomplete source provenance')
        target=dest/f'{sid}.mp4'
        if not target.is_file() or target.stat().st_size != size or digest(target) != expected:
            temp=target.with_suffix('.download')
            temp.unlink(missing_ok=True)
            try:
                agnes.download(url,temp,retries=3,retry_delay=5)
                if temp.stat().st_size != size or digest(temp) != expected:
                    raise RuntimeError(f'{sid}: source failed size/hash verification')
                temp.replace(target)
            finally:
                temp.unlink(missing_ok=True)
        files.append(target)
        print(f'{sid} restored and verified',flush=True)
    return files

if __name__=='__main__':
    story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    results=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    restore(story,results,ROOT/'work'/'nishiguchi1963'/'sources')
