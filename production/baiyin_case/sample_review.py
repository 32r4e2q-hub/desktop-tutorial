#!/usr/bin/env python3
"""Generate 3 evenly spaced stills per shot; not a substitute for playback review."""
import io, json, os, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
film=ROOT/'交付'/'白银案_审片初剪_待复核.mp4'
shots=json.loads((HERE/'story.json').read_text())['shots']
ffmpeg=os.getenv('FFMPEG','ffmpeg')
out=HERE/'qa'/'visual_samples';out.mkdir(parents=True,exist_ok=True)
for group in range(5):
    canvas=Image.new('RGB',(960,6*205),'#151515');d=ImageDraw.Draw(canvas)
    for row,shot in enumerate(shots[group*6:group*6+6]):
        for col,frac in enumerate((.2,.5,.8)):
            t=shot['start']+shot['duration']*frac
            b=subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-ss',str(t),'-i',str(film),'-frames:v','1','-vf','scale=320:180','-f','image2pipe','-vcodec','mjpeg','-'],stdout=subprocess.PIPE,check=True).stdout
            im=Image.open(io.BytesIO(b));canvas.paste(im,(col*320,row*205+25))
            d.text((col*320+5,row*205+4),f"{shot['id']}  {t:.1f}s",fill='white')
    canvas.save(out/f'group_{group+1}.jpg',quality=88)
print('Wrote 90 sampled frames, 3 per shot. Playback and listening remain required.')
