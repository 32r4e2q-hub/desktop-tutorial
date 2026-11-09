#!/usr/bin/env python3
"""Extract one frame per second from the actual draft for shot-level visual QC.

These contact sheets are screening aids, not evidence of full playback or approval.
"""
import array, hashlib, json, math, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
PROJECT=ROOT/'production/nowon2021'
PREVIEW=ROOT/'work/nowon2021/review-preview'
OUT=PROJECT/'qa/preview'

def main():
    videos=list(PREVIEW.rglob('*未审片预览.mp4'))
    if len(videos)!=1: raise RuntimeError(f'expected one rendered preview, found {len(videos)}')
    video=videos[0];story=json.loads((PROJECT/'story.json').read_text(encoding='utf-8'))
    h=hashlib.sha256()
    with video.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        folder=Path(tmp)
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-vf','fps=1,scale=384:216','-q:v','3',str(folder/'frame-%03d.jpg')],check=True)
        frames=sorted(folder.glob('frame-*.jpg'))
        if len(frames)!=180: raise RuntimeError(f'expected 180 frame samples, got {len(frames)}')
        for shot in story['shots']:
            canvas=Image.new('RGB',(1152,648),(18,18,18));draw=ImageDraw.Draw(canvas)
            for i,second in enumerate(range(shot['start'],shot['end'])):
                tile=Image.open(frames[second]).convert('RGB')
                x,y=(i%3)*384,(i//3)*216
                canvas.paste(tile,(x,y));draw.rectangle((x,y,x+76,y+21),fill=(0,0,0));draw.text((x+4,y+3),f"{shot['id']} {second}s",fill=(255,255,255))
            canvas.save(OUT/f"{shot['id']}.jpg",quality=86,optimize=True)
    report={'preview_sha256':h.hexdigest(),'source':'watermarked review preview, not final film','samples_per_second':1,'shot_count':len(story['shots']),'status':'unreviewed contact sheets, not approval'}
    probe=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)],check=True,stdout=subprocess.PIPE).stdout)
    raw=subprocess.run(['ffmpeg','-v','error','-ss','179','-i',str(video),'-t','1','-map','0:a:0','-f','f32le','-acodec','pcm_f32le','-ac','2','-ar','48000','pipe:1'],check=True,stdout=subprocess.PIPE).stdout
    samples=array.array('f');samples.frombytes(raw)
    if len(samples)!=96000: raise RuntimeError(f'final second has {len(samples)} samples, expected 96000')
    report['encoded_last_second_peak']=max(map(abs,samples))
    report['encoded_last_second_rms']=math.sqrt(sum(x*x for x in samples)/len(samples))
    report['ffprobe']=probe
    for name in ('render_report.json','captions.ass','captions.srt','封面_预览.png'):
        source=video.parent/name
        if not source.is_file(): raise RuntimeError(f'missing {name}')
        shutil.copy2(source,OUT/name)
    (OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
