#!/usr/bin/env python3
"""Correct AI-drawn clock hands deterministically; these are dramatized prop references.

A clock is a precision instrument: generative outputs put the short hand at 11
instead of 11:30. Redraw the face and hands over the approved clock housing.
"""
from pathlib import Path
from math import pi, sin, cos
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / 'reference'
BASE = ROOT / 'P04.png'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
SCALE = 3
CX, CY, R = 688, 385, 211

def point(degrees, distance):
    angle = degrees * pi / 180
    return ((CX + sin(angle)*distance)*SCALE, (CY - cos(angle)*distance)*SCALE)

def make(hour, minute, name):
    im = Image.open(BASE).convert('RGB').resize((1376*SCALE, 768*SCALE), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(im)
    # Restrict the alteration to the inside of the dial, leaving metal bezel and scene intact.
    draw.ellipse(((CX-R)*SCALE,(CY-R)*SCALE,(CX+R)*SCALE,(CY+R)*SCALE), fill=(202,214,216))
    for i in range(60):
        draw.line((point(i*6, 201), point(i*6, 185 if i%5==0 else 194)),
                  fill=(31,40,43), width=(4 if i%5==0 else 2)*SCALE)
    font = ImageFont.truetype(FONT, 50*SCALE)
    for n in range(1,13):
        xy = point(n*30,164)
        draw.text(xy,str(n),font=font,fill=(25,32,33),anchor='mm',stroke_width=0)
    # Radial geometry: 12 hours = 360°, 60 minutes = 360°.
    for angle, length, width, color in [((hour%12+minute/60)*30, 112, 9, (24,32,34)),
                                       (minute*6, 165, 6, (20,27,29)),
                                       (0, 173, 2, (151,36,35))]:
        draw.line((point(angle,0), point(angle,length)),fill=color,width=width*SCALE)
        draw.line((point(angle+180,0), point(angle+180,28 if width>2 else 45)),fill=color,width=width*SCALE)
    x,y=CX*SCALE,CY*SCALE
    draw.ellipse((x-7*SCALE,y-7*SCALE,x+7*SCALE,y+7*SCALE),fill=(34,31,30))
    draw.ellipse((x-4*SCALE,y-4*SCALE,x+4*SCALE,y+4*SCALE),fill=(155,43,41))
    im.resize((1376,768), Image.Resampling.LANCZOS).save(ROOT / f'{name}.png',optimize=True)

if __name__ == '__main__':
    make(5,30,'P04-1730')
    make(10,30,'P04-2230')
    make(11,30,'P04-2330')
