#!/usr/bin/env python3
"""Download verified motion sources and make dense, time-labelled all-frame QA sheets."""
from __future__ import annotations
import argparse, hashlib, json, shutil, time, urllib.request
from pathlib import Path
import av
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FPS=24
SECONDS=6
FRAMES=FPS*SECONDS
COLS=6
ROWS=6
PER_PAGE=COLS*ROWS
CELL_W=320
FRAME_H=180
LABEL_H=20
CELL_H=FRAME_H+LABEL_H

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def download(row,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.is_file() and dest.stat().st_size==int(row['bytes']) and sha(dest)==row['sha256']:
        return
    last=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(row['video_url'],headers={'User-Agent':'hakamada58-frame-audit/1.0'})
            with urllib.request.urlopen(req,timeout=180) as r,dest.with_suffix('.part').open('wb') as f:
                shutil.copyfileobj(r,f,1<<18)
            part=dest.with_suffix('.part')
            if part.stat().st_size!=int(row['bytes']) or sha(part)!=row['sha256']:
                raise RuntimeError('source clip checksum/size mismatch')
            part.replace(dest)
            return
        except Exception as e:
            last=e;dest.with_suffix('.part').unlink(missing_ok=True)
            if attempt<3:time.sleep(2**attempt)
    raise RuntimeError(f'{dest.name}: download failed: {last}')

def font():
    candidates=[Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),Path('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf')]
    for p in candidates:
        if p.exists():return ImageFont.truetype(str(p),12)
    return ImageFont.load_default()

def page_image(cells,page_no,sid):
    sheet=Image.new('RGB',(COLS*CELL_W,ROWS*CELL_H),(9,12,16));d=ImageDraw.Draw(sheet);f=font()
    for i,(frame_no,t,im) in enumerate(cells):
        x=(i%COLS)*CELL_W;y=(i//COLS)*CELL_H
        sheet.paste(im,(x,y))
        d.rectangle((x,y+FRAME_H,x+CELL_W,y+CELL_H),fill=(9,12,16))
        d.text((x+5,y+FRAME_H+3),f'{sid}  f{frame_no:03d}  {t:05.2f}s',fill=(244,229,194),font=f)
        d.rectangle((x,y,x+CELL_W-1,y+CELL_H-1),outline=(105,89,67),width=1)
    d.rectangle((0,0,380,22),fill=(9,12,16));d.text((8,4),f'{sid} · ALL FRAMES · page {page_no:02d}',fill=(255,236,190),font=f)
    return sheet

def audit_one(sid,row,rawdir,outdir):
    dest=rawdir/f'{sid}.mp4';download(row,dest)
    container=av.open(str(dest));stream=next((s for s in container.streams if s.type=='video'),None)
    if stream is None:raise RuntimeError(f'{sid}: missing video stream')
    source_width,source_height=int(stream.width),int(stream.height)
    if source_width<640 or source_height<360:raise RuntimeError(f'{sid}: source resolution unexpectedly small')
    cells=[];pages=[];frame_metrics=[];prev_small=None;frame_no=0;black=[];cuts=[]
    for frame in container.decode(stream):
        if frame_no>=FRAMES:break
        t=frame_no/FPS
        im=ImageOps.fit(frame.to_image().convert('RGB'),(CELL_W,FRAME_H),method=Image.Resampling.LANCZOS)
        small=im.convert('L').resize((80,45),Image.Resampling.BILINEAR)
        mean=sum(i*n for i,n in enumerate(small.histogram()))/(80*45*255)
        if mean<0.025:black.append(frame_no)
        if prev_small is not None:
            diff=ImageChops.difference(prev_small,small)
            hist=diff.histogram();mad=sum(i*n for i,n in enumerate(hist))/(80*45*255)
            frame_metrics.append(mad)
            if mad>0.25:cuts.append({'frame':frame_no,'time':round(t,3),'normalized_mean_difference':round(mad,4)})
        prev_small=small
        cells.append((frame_no,t,im));frame_no+=1
        if len(cells)==PER_PAGE:
            page_no=len(pages)+1;pages.append(page_image(cells,page_no,sid));cells=[]
    container.close()
    if frame_no!=FRAMES:
        raise RuntimeError(f'{sid}: expected {FRAMES} frames in first {SECONDS}s, decoded {frame_no}')
    if cells:pages.append(page_image(cells,len(pages)+1,sid))
    outdir.mkdir(parents=True,exist_ok=True)
    page_names=[]
    for i,page in enumerate(pages,1):
        name=f'{sid}_P{i:02d}.jpg';page.save(outdir/name,quality=88,optimize=True);page_names.append(name)
    sorted_diffs=sorted(frame_metrics);median=sorted_diffs[len(sorted_diffs)//2] if sorted_diffs else 0
    report={'id':sid,'source_sha256':row['sha256'],'source_bytes':int(row['bytes']),'source_resolution':[source_width,source_height],'expected_fps':FPS,'audited_frames':frame_no,'audited_seconds':SECONDS,'frames_per_page':PER_PAGE,'pages':page_names,'black_frame_indices':black,'large_frame_changes':cuts,'adjacent_frame_difference_median':round(median,5),'review_status':'pending_manual_review'}
    return report

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--only',default='');ap.add_argument('--work',default='work/hakamada58/frame-audit');args=ap.parse_args()
    results=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    ids=[f'S{i:02d}' for i in range(1,31)]
    if args.only:
        selected=[x.strip() for x in args.only.split(',') if x.strip()]
        if not set(selected)<=set(ids):raise RuntimeError('unknown shot ID in --only')
        ids=[x for x in ids if x in set(selected)]
    base=ROOT/args.work;rawdir=base/'raw';outdir=HERE/'qa'/'frame_audit'
    summaries=[]
    for sid in ids:
        row=results['shots'][sid]
        if row.get('status')!='completed' or not row.get('video_url') or not row.get('sha256'):
            raise RuntimeError(f'{sid}: no completed, hash-verified source receipt')
        report=audit_one(sid,row,rawdir,outdir);summaries.append(report)
        print(f"{sid}: audited {report['audited_frames']} frames -> {len(report['pages'])} pages; diff alerts={len(report['large_frame_changes'])}; dark frames={len(report['black_frame_indices'])}",flush=True)
    summary={'project':'袴田事件：58年','audit_type':'all-frame visual contact sheets','fps':FPS,'frames_per_shot':FRAMES,'seconds_per_shot':SECONDS,'shots_audited':len(summaries),'total_frames':sum(x['audited_frames'] for x in summaries),'shots':summaries}
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'shots':len(summaries),'frames':summary['total_frames'],'pages':sum(len(x['pages']) for x in summaries),'output':str(outdir)},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
