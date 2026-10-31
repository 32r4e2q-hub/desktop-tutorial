#!/usr/bin/env python3
"""Typography over the project’s generated cover artwork; never a video substitute."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent

def make_cover(background: Path, font_path: Path, output: Path):
    if not font_path.is_file():
        raise RuntimeError('A CJK font is required: pass --font (e.g. ZCOOL XiaoWei, SIL OFL).')
    image = ImageOps.fit(Image.open(background).convert('RGB'), (1920,1080), method=Image.Resampling.LANCZOS)
    overlay = Image.new('RGBA', image.size)
    d=ImageDraw.Draw(overlay)
    # Subtle ink band keeps the type legible without concealing either main face.
    d.rounded_rectangle((105,760,1450,1020), radius=24, fill=(6,12,21,180))
    image=Image.alpha_composite(image.convert('RGBA'),overlay)
    d=ImageDraw.Draw(image)
    small=ImageFont.truetype(str(font_path),46)
    title=ImageFont.truetype(str(font_path),124)
    foot=ImageFont.truetype(str(font_path),30)
    d.text((150,780),'西口彰事件  |  78天的逃亡',font=small,fill='#e9dcc5',stroke_width=2,stroke_fill='#101015')
    d.text((145,852),'被一个小女孩认出',font=title,fill='#f4c95f',stroke_width=7,stroke_fill='#17100b')
    d.text((1450,1020),'AI动画情景复原',font=foot,fill='#f1f1ee',anchor='rb',stroke_width=2,stroke_fill='#101015')
    output.parent.mkdir(parents=True,exist_ok=True)
    image.convert('RGB').save(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--font',type=Path,required=True)
    parser.add_argument('--background',type=Path,default=HERE/'reference/cover-background.png')
    parser.add_argument('--output',type=Path,default=HERE/'cover.png')
    args=parser.parse_args()
    make_cover(args.background,args.font,args.output)
