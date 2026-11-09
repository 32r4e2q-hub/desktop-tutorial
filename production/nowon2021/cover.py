#!/usr/bin/env python3
"""Generate a cover from an actual frame of the current rendered film, never a reference image."""
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

TITLE = '他只是按了门铃'

def make_cover(video, output, font_path=None):
    video, output = Path(video), Path(output)
    if not video.is_file(): raise FileNotFoundError(f'final film required: {video}')
    if font_path is None:
        result = subprocess.run(['fc-match','-f','%{file}', 'Noto Sans CJK SC:style=Bold'],check=True,text=True,capture_output=True)
        font_path=result.stdout.strip()
    if not font_path or not Path(font_path).is_file(): raise RuntimeError('Chinese font not found')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        frame=Path(folder)/'final-film-frame.png'
        subprocess.run(['ffmpeg','-v','error','-y','-ss','0.25','-i',str(video),'-frames:v','1',str(frame)],check=True)
        image=Image.open(frame).convert('RGB')
        if image.size != (1920,1080): raise RuntimeError(f'expected final film 1920x1080, got {image.size}')
        overlay=Image.new('RGBA', image.size, (0,0,0,0));draw=ImageDraw.Draw(overlay)
        draw.rectangle((0,0,1920,192),fill=(0,0,0,180))
        font=ImageFont.truetype(str(font_path),110)
        draw.text((960,89), TITLE,font=font,fill=(255,219,122,255),stroke_width=4,stroke_fill=(0,0,0,255),anchor='mm')
        Image.alpha_composite(image.convert('RGBA'),overlay).convert('RGB').save(output,optimize=True)
    return output
