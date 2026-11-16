#!/usr/bin/env python3
"""Assemble reviewed source views; never generate faces or autoapprove boards."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageOps
HERE = Path(__file__).resolve().parent
REF = HERE / 'reference'

def build():
    out = REF / 'boards'
    out.mkdir(exist_ok=True)
    records = []
    roles = [f'C{i:02}' for i in range(1,9)] + ['C07-prosecutor', 'C07-lawyer']
    for role in roles:
        base = role[:3]
        if role == 'C07':
            front = Image.open(REF / 'C07.png').convert('RGB').crop((560,40,860,760))
            paths = ['C07.png', 'views/C07-judge-side.png', 'views/C07-judge-close.png']
        elif role.startswith('C07-'):
            paths = [f'views/{role}-front.png', f'views/{role}-side.png', f'views/{role}-close.png']
            front = Image.open(REF / paths[0]).convert('RGB')
        else:
            paths = [f'{base}.png', f'views/{base}-side.png', f'views/{base}-close.png']
            front = Image.open(REF / paths[0]).convert('RGB')
        images = [front] + [Image.open(REF / p).convert('RGB') for p in paths[1:]]
        board = Image.new('RGB', (1920, 1080), (160,160,160))
        for i, im in enumerate(images):
            # Contain preserves all source pixels and does not stretch faces.
            tile = ImageOps.contain(im, (624,1048), Image.Resampling.LANCZOS)
            board.paste(tile, (i*640 + (640-tile.width)//2, (1080-tile.height)//2))
        dest = out / f'{role}.png'
        board.save(dest)
        records.append(dict(role=role, file=str(dest.relative_to(HERE)), status='pending_board_visual_review',
                            sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                            sources=[dict(file=p,sha256=hashlib.sha256((REF/p).read_bytes()).hexdigest()) for p in paths],
                            front_crop=[560,40,860,760] if role=='C07' else None))
    (out/'manifest.json').write_text(json.dumps({'boards':records},ensure_ascii=False,indent=2)+'\n')
if __name__ == '__main__': build()
