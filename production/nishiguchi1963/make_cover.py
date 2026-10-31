#!/usr/bin/env python3
"""Typography over the project’s generated cover artwork; never a video substitute."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent

def make_cover(background: Path, font_path: Path, output: Path):
    if not font_path.is_file():
        raise RuntimeError('A CJK font is required: pass --font (e.g. ZCOOL XiaoWei, SIL OFL).')
    image = ImageOps.fit(Image.open(background).convert('RGB'), (1920,1080), method=Image.Resampling.LANCZOS)
    # The wanted portrait is a fictional illustration, intentionally defocused.
    mask = Image.new('L', image.size, 0)
    ImageDraw.Draw(mask).ellipse((210, 100, 625, 675), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(35))
    image = Image.composite(image.filter(ImageFilter.GaussianBlur(22)), image, mask)
    overlay = Image.new('RGBA', image.size)
    d=ImageDraw.Draw(overlay)
    # Subtle ink band keeps the type legible without concealing either main face.
    d.rounded_rectangle((105,745,1450,1050), radius=24, fill=(6,12,21,200))
    image=Image.alpha_composite(image.convert('RGBA'),overlay)
    d=ImageDraw.Draw(image)
    small=ImageFont.truetype(str(font_path),46)
    title=ImageFont.truetype(str(font_path),128)
    foot=ImageFont.truetype(str(font_path),30)
    note=ImageFont.truetype(str(font_path),28)
    d.text((150,780),'西口彰事件  |  78天的逃亡',font=small,fill='#e9dcc5',stroke_width=2,stroke_fill='#101015')
    d.text((145,835),'十岁小女孩',font=title,fill='#f4c95f',stroke_width=7,stroke_fill='#17100b')
    d.text((150,1000),'年龄另有十一岁说法，资料记载存在差异',font=note,fill='#f1f1ee',stroke_width=2,stroke_fill='#101015')
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
