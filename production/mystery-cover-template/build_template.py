#!/usr/bin/env python3
"""Build the first cover and a standalone offline browser editor from one background.

Requires Pillow and a CJK font for the sample; the generated editor embeds a subset
of Noto Serif CJK (SIL OFL) and runs without Python, network, or external assets.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import argparse,base64,html,json,zipfile

HERE=Path(__file__).resolve().parent
W,H=1080,1440
LABEL='迷案解码人'
PERIOD='第一期'
LINE1='逃亡78天的西口彰'
LINE2='却被女孩一眼认出'
FOOTER='真实案件 · 动画情景复原'


def plate():
    im=ImageOps.fit(Image.open(HERE/'background.png').convert('RGB'),(W,H),method=Image.Resampling.LANCZOS).convert('RGBA')
    overlay=Image.new('RGBA',(W,H)); pix=overlay.load()
    for y in range(H):
        if y<110: alpha=185
        elif y<560: alpha=int(185-(y-110)*0.10)
        elif y<790: alpha=int(140*(790-y)/230)
        elif y<1120: alpha=0
        else: alpha=int(180*min(1,(y-1120)/240))
        for x in range(W): pix[x,y]=(3,9,17,alpha)
    return Image.alpha_composite(im,overlay).convert('RGB')

def fitted_font(font_path,draw,text,max_size,max_width):
    for size in range(max_size,29,-1):
        f=ImageFont.truetype(str(font_path),size)
        if draw.textlength(text,font=f)<=max_width:return f
    return ImageFont.truetype(str(font_path),30)

def cover(font_path):
    im=plate().convert('RGBA');d=ImageDraw.Draw(im)
    font=lambda size:ImageFont.truetype(str(font_path),size)
    d.rectangle((62,76,68,126),fill='#b83d36')
    d.text((84,72),LABEL,font=font(45),fill='#f0dfbd',anchor='lt')
    d.rounded_rectangle((786,72,1016,136),radius=7,fill='#871e20',outline='#c65c51',width=2)
    d.text((901,84),PERIOD,font=font(33),fill='#fff2d9',anchor='mt')
    d.line((62,168,1018,168),fill='#a55c4c',width=2)
    d.text((66,207),'真实案件',font=font(30),fill='#cd7f65',anchor='lt')
    d.text((260,209),'CASE FILE  /  TRUE STORY',font=font(21),fill='#c4b9a8',anchor='lt')
    for y,text,color in [(285,LINE1,'#fff0d0'),(425,LINE2,'#efd19b')]:
        f=fitted_font(font_path,d,text,106,940)
        d.text((66,y+5),text,font=f,fill='#140d0c',stroke_width=5,stroke_fill='#140d0c',anchor='lt')
        d.text((66,y),text,font=f,fill=color,stroke_width=2,stroke_fill='#241914',anchor='lt')
    d.line((65,585,290,585),fill='#a53330',width=5)
    d.text((65,1275),'真相，藏在细节里',font=font(39),fill='#f0dfbd',anchor='lt')
    d.text((65,1352),FOOTER,font=font(25),fill='#b8a996',anchor='lt')
    d.text((1014,1352),'MYSTERY DECODER',font=font(20),fill='#a68a7d',anchor='rt')
    return im.convert('RGB')

def write_editor(font_woff):
    # Everything is embedded: this HTML is usable as a single file after download.
    image64=base64.b64encode((HERE/'plate.jpg').read_bytes()).decode('ascii')
    font64=base64.b64encode(Path(font_woff).read_bytes()).decode('ascii')
    markup=(HERE/'editor_template.html').read_text(encoding='utf8')
    markup=markup.replace('__IMAGE_DATA__',image64).replace('__FONT_DATA__',font64)
    (HERE/'封面模板_可编辑.html').write_text(markup,encoding='utf8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--font',type=Path,required=True);parser.add_argument('--woff',type=Path,required=True);args=parser.parse_args()
    plate().save(HERE/'plate.jpg',quality=94,subsampling=0)
    cover(args.font).save(HERE/'第一期_西口彰_封面.png',optimize=True)
    write_editor(args.woff)
    with zipfile.ZipFile(HERE/'迷案解码人_封面模板.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in ['封面模板_可编辑.html','第一期_西口彰_封面.png','使用说明.txt','OFL.txt']:
            z.write(HERE/name,arcname=name)
    print('cover, editor, and package created')

if __name__=='__main__': main()
