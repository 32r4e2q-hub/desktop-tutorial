#!/usr/bin/env python3
"""Build the first cover and a standalone offline browser editor from one background.

Requires Pillow and a CJK font for the sample; the generated editor embeds a subset
of Noto Serif CJK (SIL OFL) and runs without Python, network, or external assets.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
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

def fitted_font(font_path,draw,text,max_size,max_width,min_size=30):
    for size in range(max_size,min_size-1,-1):
        f=ImageFont.truetype(str(font_path),size)
        left,_,right,_=draw.textbbox((0,0),text,font=f)
        if max(draw.textlength(text,font=f),right)-min(0,left)<=max_width:return f
    raise ValueError(f'文字无法适配宽度 {max_width}: {text}')

def cover(font_path, period=PERIOD, line1=LINE1, line2=LINE2, plate_image=None, screenshot=None, episode=1):
    im=(plate() if plate_image is None else plate_image).convert('RGBA');d=ImageDraw.Draw(im)
    font=lambda size:ImageFont.truetype(str(font_path),size)
    d.rectangle((62,76,68,126),fill='#b83d36')
    d.text((84,72),LABEL,font=font(45),fill='#f0dfbd',anchor='lt')
    d.rounded_rectangle((786,72,1016,136),radius=7,fill='#871e20',outline='#c65c51',width=2)
    d.text((901,84),period,font=fitted_font(font_path,d,period,33,190,min_size=16),fill='#fff2d9',anchor='mt')
    d.line((62,168,1018,168),fill='#a55c4c',width=2)
    d.text((66,207),'真实案件',font=font(30),fill='#cd7f65',anchor='lt')
    d.text((260,209),'CASE FILE  /  TRUE STORY',font=font(21),fill='#c4b9a8',anchor='lt')
    for y,text,color in [(285,line1,'#fff0d0'),(425,line2,'#efd19b')]:
        f=fitted_font(font_path,d,text,106,940)
        d.text((66,y+5),text,font=f,fill='#140d0c',stroke_width=5,stroke_fill='#140d0c',anchor='lt')
        d.text((66,y),text,font=f,fill=color,stroke_width=2,stroke_fill='#241914',anchor='lt')
    d.line((65,585,290,585),fill='#a53330',width=5)
    d.text((65,1275),'真相，藏在细节里',font=font(39),fill='#f0dfbd',anchor='lt')
    d.text((65,1352),FOOTER,font=font(25),fill='#b8a996',anchor='lt')
    d.text((1014,1352),'MYSTERY DECODER',font=font(20),fill='#a68a7d',anchor='rt')
    if screenshot is not None:
        x,y,w,h=126,622,828,405
        shadow=Image.new('RGBA',im.size);sd=ImageDraw.Draw(shadow)
        sd.rounded_rectangle((x-3,y+12,x+w+3,y+h+12),radius=8,fill=(0,0,0,220))
        im=Image.alpha_composite(im,shadow.filter(ImageFilter.GaussianBlur(20)))
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((x,y,x+w,y+h),radius=5,fill='#15191d',outline='#b7966a',width=2)
        d.rectangle((x+7,y+7,x+w-7,y+h-7),outline='#574536',width=1)
        shot=ImageOps.fit(screenshot.convert('RGB'),(w-20,h-64),method=Image.Resampling.LANCZOS)
        im.paste(shot,(x+10,y+10));d=ImageDraw.Draw(im)
        d.line((x+10,y+h-49,x+w-10,y+h-49),fill='#725a43',width=1)
        d.text((x+20,y+h-41),'本片画面  ·  动画情景复原',font=font(22),fill='#e5d3b6')
        d.text((x+w-22,y+h-38),f'CASE FILE  /  {episode:02d}',font=font(17),fill='#a79176',anchor='ra')
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
    with Image.open(HERE/'第一期_视频截图示例.jpg') as screenshot:
        cover(args.font, screenshot=screenshot).save(HERE/'第一期_西口彰_封面.png',optimize=True)
    write_editor(args.woff)
    with zipfile.ZipFile(HERE/'迷案解码人_封面模板.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in ['封面模板_可编辑.html','第一期_西口彰_封面.png','第一期_视频截图示例.jpg','使用说明.txt','OFL.txt']:
            z.write(HERE/name,arcname=name)
    print('cover, editor, and package created')

if __name__=='__main__': main()
