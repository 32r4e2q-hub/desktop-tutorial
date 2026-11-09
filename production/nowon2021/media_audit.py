#!/usr/bin/env python3
"""Independent technical screening of an encoded preview. Not human review."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
STORY=ROOT/'production/nowon2021/story.json'

def command(args):
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

def ts(s):
    h,m,v=s.replace(',','.').split(':')
    return int(h)*3600+int(m)*60+float(v)

def captions_audit(path,story):
    blocks=re.split(r'\n\s*\n',path.read_text(encoding='utf-8-sig').strip())
    groups={s['id']:[] for s in story['shots']}
    prior=0
    for i,b in enumerate(blocks,1):
        lines=b.splitlines()
        if len(lines)!=3 or lines[0]!=str(i) or ' --> ' not in lines[1]: raise ValueError(f'malformed SRT cue {i}')
        a,b=map(ts,lines[1].split(' --> '))
        if a<prior-0.001 or not a<b: raise ValueError(f'overlapping/invalid SRT cue {i}')
        shots=[s for s in story['shots'] if a>=s['start']-0.001 and b<=s['end']+0.001]
        if len(shots)!=1: raise ValueError(f'cue {i} crosses a shot boundary')
        groups[shots[0]['id']].append(lines[2]);prior=b
    for s in story['shots']:
        if ''.join(groups[s['id']])!=s['narration']: raise ValueError(f"{s['id']}: subtitles do not match narration text")
    return {'cue_count':len(blocks),'text_matches_all_narration':True,'no_overlaps_or_shot_crossings':True,'timing':'estimated; human listening still required'}

def inspect(path):
    from PIL import Image, ImageStat
    story=json.loads(STORY.read_text(encoding='utf-8'))
    dig=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):dig.update(chunk)
    info=json.loads(command(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]).stdout)
    video=next(s for s in info['streams'] if s['codec_type']=='video')
    audio=next(s for s in info['streams'] if s['codec_type']=='audio')
    if (video['width'],video['height'],video['r_frame_rate'],int(video['nb_frames']),audio['sample_rate'],audio['channels']) != (1920,1080,'24/1',4320,'48000',2):
        raise ValueError('Unexpected final media specifications')
    # Six and one frames before each cut, sampling the central area only: labels and
    # subtitles may legitimately remain visible over a black frame.
    positions=[(s['id'],s['end']*24-back) for s in story['shots'] if s['id'] in ('SH18','SH22','SH25') for back in (6,1)]
    with tempfile.TemporaryDirectory() as tmp:
        target=Path(tmp)
        select='+'.join(f'eq(n\\,{n})' for _,n in positions)
        command(['ffmpeg','-v','error','-i',str(path),'-vf',f'select={select},scale=320:180','-fps_mode','passthrough',str(target/'cut-%02d.png')])
        images=sorted(target.glob('cut-*.png'))
        if len(images)!=len(positions): raise ValueError('Could not decode all cut samples')
        cuts=[]
        for (sid,n),im in zip(positions,images):
            gray=Image.open(im).convert('L').crop((0,25,320,135))
            cuts.append({'id':sid,'frame':n,'mean_luma':round(ImageStat.Stat(gray).mean[0],4)})
    loud=command(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-map','0:a:0','-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-']).stderr.decode('utf-8','replace')
    match=re.search(r'\{\s*"input_i".*?\}',loud,re.S)
    if not match: raise ValueError('loudness analysis missing')
    loudness=json.loads(match.group())
    freeze=command(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-an','-vf','freezedetect=n=-50dB:d=2','-f','null','-']).stderr.decode('utf-8','replace')
    markers=[line.strip() for line in freeze.splitlines() if 'freeze_start:' in line or 'freeze_end:' in line or 'freeze_duration:' in line]
    return {'sha256':dig.hexdigest(),'video':{'width':video['width'],'height':video['height'],'fps':video['r_frame_rate'],'frames':int(video['nb_frames']),'duration':video['duration']},'audio':{'rate':int(audio['sample_rate']),'channels':audio['channels'],'integrated_lufs':float(loudness['input_i']),'true_peak_dbtp':float(loudness['input_tp']),'loudness_range_lu':float(loudness['input_lra'])},'cut_black_center_samples':cuts,'freeze_detection_candidates':markers,'captions':captions_audit(path.parent/'captions.srt',story),'limitations':'Auto indicators only; cannot assess motion plausibility, diction, synchronization, character continuity or hearing quality.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('video',type=Path);ap.add_argument('output',type=Path);args=ap.parse_args()
    report=inspect(args.video);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
