#!/usr/bin/env python3
"""Independent review of the exact published MP4; no regeneration or threshold overrides."""
import argparse
from collections import defaultdict
from difflib import SequenceMatcher
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(HERE), str(ROOT / 'production')]
from verbatim_check import normalize, character_error_rate, diff_spans

EXPECTED = '5946ef6151344badf20081bd26b8315c73c7e43f6fba5e25965e5c28cad274d1'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')


def decode(path, rate=8000):
    raw = subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar',str(rate),'-f','f32le','-'])
    return np.frombuffer(raw, dtype='<f4')


def font(size):
    for p in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if Path(p).is_file():
            return ImageFont.truetype(p,size)
    return ImageFont.load_default()


def compose(tiles, dest, cols=4, w=384, h=216, label_h=50):
    canvas=Image.new('RGB',(cols*w,((len(tiles)+cols-1)//cols)*(h+label_h)),(24,24,24))
    d=ImageDraw.Draw(canvas)
    for i,(label,image) in enumerate(tiles):
        x=(i%cols)*w;y=(i//cols)*(h+label_h)
        canvas.paste(image.resize((w,h),Image.Resampling.LANCZOS),(x,y+label_h))
        for j,line in enumerate(label.split('\n')[:2]):
            d.text((x+5,y+3+j*22),line,fill='white',font=font(10 if w<=128 else 16))
    canvas.save(dest,quality=88)


def visual(film, artifact, out):
    edl=read(HERE/'delivery/edit-decision-list.json')
    plan=read(HERE/'story.json')
    check=read(next(artifact.rglob('frame-distortion-audit.json')))
    sample_requests=defaultdict(list)
    shot_frames={}
    manifest=[]
    for row in edl:
        a,b=row['start_frame'],row['end_frame']-1
        indices=[round(a+(b-a)*fraction) for fraction in (.08,.35,.65,.92)]
        shot_frames[row['id']]=indices
        for i in indices:sample_requests[i].append(('shot',row['id']))
        manifest.append({**row,'sample_frames':indices,'start':a/30,'end':(b+1)/30})
    events=[]
    for kind in ('non_graphic_freeze_runs','temporal_outlier_windows'):
        for e in check['checks'][kind]:
            a,b=int(e['start_frame']),int(e['end_frame'])
            indices=sorted(set((max(0,a-2),round((a+b)/2),min(5399,b+2))))
            events.append({'kind':kind,'event':e,'sample_frames':indices})
            for i in indices:sample_requests[i].append(('event',len(events)-1))
    # Export EVERY candidate crop, rather than the first 40 full frames as in the original audit.
    face_events=check['checks']['face_review_candidates']
    hand_events=check['checks']['hand_landmark_extreme_events']
    for kind,rows in (('face',face_events),('hand',hand_events)):
        for ix,e in enumerate(rows):sample_requests[int(e['frame'])].append((kind,ix))
    frames={};face_crops=[];hand_crops=[]
    container=av.open(str(film))
    for i,frame in enumerate(container.decode(video=0)):
        if i not in sample_requests:continue
        image=frame.to_image()
        if any(k in ('shot','event') for k,_ in sample_requests[i]):
            frames[i]=image.resize((640,360),Image.Resampling.LANCZOS)
        for kind,ix in sample_requests[i]:
            if kind not in ('face','hand'):continue
            e=(face_events if kind=='face' else hand_events)[ix]
            box=e.get('bbox')
            if box is None:
                # Keep the entire frame if a detector did not expose a box; do not fabricate one.
                crop=image
            else:
                x,y,w,h=box
                pad=.25
                left=min(image.width-1,max(0,int((x-w*pad)*image.width)))
                top=min(image.height-1,max(0,int((y-h*pad)*image.height)))
                right=max(left+1,min(image.width,int((x+w*(1+pad))*image.width)))
                bottom=max(top+1,min(image.height,int((y+h*(1+pad))*image.height)))
                crop=image.crop((left,top,right,bottom))
            label=f'{e["shot"]} f{i} t{i/30:.2f}'
            size=128 if kind=='face' else 256
            (face_crops if kind=='face' else hand_crops).append((label,crop.resize((size,size),Image.Resampling.LANCZOS)))
    container.close()
    for batch in range(0,len(edl),5):
        tiles=[]
        for row in edl[batch:batch+5]:
            for i in shot_frames[row['id']]:
                tiles.append((f'{row["id"]} {i/30:.2f}s {row.get("purpose","")[:16]}',frames[i]))
        compose(tiles,out/f'shots-{batch//5+1:02}.jpg')
    for batch in range(0,len(events),6):
        tiles=[]
        for ix,e in enumerate(events[batch:batch+6],batch):
            for i in e['sample_frames']:
                tiles.append((f'E{ix:02} {e["event"].get("shot", "")} f{i} {i/30:.2f}s\n{e["kind"]}',frames[i]))
        compose(tiles,out/f'events-{batch//6+1:02}.jpg',cols=3)
    for name,tiles,w,h,cols,page in (('face-candidates',face_crops,128,128,12,144),('hand-candidates',hand_crops,256,256,5,25)):
        for batch in range(0,len(tiles),page):
            compose(tiles[batch:batch+page],out/f'{name}-{batch//page+1:02}.jpg',cols=cols,w=w,h=h,label_h=28)
    texts={c['id']:c['text'] for c in plan['chapters']}
    for row in manifest:row['chapter_script']=texts.get(row.get('narration_id'),'')
    write(out/'visual-evidence.json',{'film_sha256':EXPECTED,'edl':manifest,'temporal_events':events,
                                    'all_face_candidate_crops':len(face_crops),'all_hand_candidate_crops':len(hand_crops),
                                    'note':'4 samples per shot plus each flagged temporal event and EVERY detector candidate crop. Detection is not a defect verdict.'})


def waveform_sync(film, out, chapters, tempo):
    from scipy.signal import correlate, fftconvolve
    samples=decode(film);rate=8000;rows=[]
    for ch in chapters:
        dry=out/f'{ch["id"]}-retimed.wav'
        decoded=out/f'{ch["id"]}-decoded48.wav'
        # Production retimes decoded 48k PCM, not the original 24k MP3.
        # WSOLA at different input rates changes waveform phase; compare like-for-like.
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(HERE/'audio'/f'{ch["id"]}.mp3'),'-ac','1','-ar','48000','-c:a','pcm_s16le',str(decoded)],check=True)
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(decoded),'-af',f'atempo={tempo:.9f},highpass=f=70,lowpass=f=11000', '-ac','1','-ar',str(rate),str(dry)],check=True)
        reference=decode(dry);windows=[]
        for fraction in (.2,.5,.8):
            begin=int((len(reference)-rate*2)*fraction)
            ref=reference[begin:begin+rate*2].astype(np.float64)
            center=round(ch['start']*rate)+begin
            pad=int(rate*.5);a=center-pad;b=center+len(ref)+pad
            if a<0 or b>len(samples):continue
            seg=samples[a:b].astype(np.float64)
            corr=correlate(seg,ref,mode='valid',method='fft')
            energy=fftconvolve(seg*seg,np.ones(len(ref)),mode='valid')
            ncc=corr/np.sqrt(np.maximum(1e-15,energy*np.sum(ref*ref)))
            idx=int(np.argmax(ncc));lag=(idx-pad)/rate
            windows.append({'at':round(center/rate,4),'lag_seconds':round(lag,5),'normalized_correlation':round(float(ncc[idx]),5)})
        rows.append({'id':ch['id'],'windows':windows,'pass':bool(windows) and all(abs(w['lag_seconds'])<=.1 and w['normalized_correlation']>=.75 for w in windows)})
        dry.unlink()
        decoded.unlink(missing_ok=True)
    write(out/'waveform-sync.json',{'film_sha256':EXPECTED,'method':'Independent final-mix vs atempo-retimed clean narration, 3 windows/chapter, +/-0.5s normalized waveform correlation. This measures placement, not lip sync.', 'chapters':rows,'pass':all(r['pass'] for r in rows)})


def audio(film,out,caption_plan=None,edl_path=None):
    from faster_whisper import WhisperModel
    from verbatim_check import load_chapters, write_wav, decode_audio, compare
    import render
    chapters=load_chapters(HERE,None)
    tempo=read(HERE/'delivery/technical-report.json')['narration_tempo']
    waveform_sync(film,out,chapters,tempo)
    model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4,download_root='work/review-model')
    samples=decode_audio(film,out)
    trans={};word_rows={};control={}
    for ch in chapters:
        cid=ch['id'];pad=.25;start=max(0,ch['start']-pad);end=ch['end']+pad
        path=write_wav(out/f'{cid}-film.wav',samples[int(start*48000):int(end*48000)])
        segments,_=model.transcribe(str(path),language='zh',beam_size=5,vad_filter=False,word_timestamps=True,condition_on_previous_text=False)
        segs=list(segments);trans[cid]=''.join(s.text for s in segs)
        words=[{'text':w.word,'start':w.start+start,'end':w.end+start,'probability':w.probability} for s in segs for w in s.words or []]
        word_rows[cid]=words
        segs,_=model.transcribe(str(HERE/'audio'/f'{cid}.mp3'),language='zh',beam_size=5,vad_filter=False,condition_on_previous_text=False)
        control[cid]=''.join(s.text for s in segs)
        print('ASR',cid,trans[cid],flush=True)
        path.unlink()
    result=compare(chapters,trans,.15);dry=compare(chapters,control,.15)
    write(out/'verbatim-check.json',{'film_sha256':EXPECTED,'method':'faster-whisper small final mix AND clean chapter control, no initial_prompt or script fed to recognizer', 'film_pass':result,'narration_control':dry,'word_timestamps':word_rows})
    clause=read(HERE/'audio/clause-times.json');caption_rows=[]
    for ch in chapters:
        cid=ch['id'];expected=normalize(ch['text']); heard='';timestamps=[]
        for word in word_rows[cid]:
            text=normalize(word['text'])
            for i,char in enumerate(text):
                heard+=char;timestamps.append((word['start']+(word['end']-word['start'])*i/max(1,len(text)),word['start']+(word['end']-word['start'])*(i+1)/max(1,len(text))))
        mapping={}
        for block in SequenceMatcher(None,expected,heard,autojunk=False).get_matching_blocks():
            for i in range(block.size):mapping[block.a+i]=block.b+i
        row={**ch,'tempo':tempo,'raw_duration':clause[cid]['duration']}
        cues=([c for c in read(caption_plan) if ch['start']-.2<=c['start']<ch['end']]
              if caption_plan else render.captions_from_clause_times(row))
        if not cues:raise RuntimeError(f'{cid}: cannot reconstruct exact caption cues')
        pointer=0
        for cue in cues:
            text=normalize(cue['text']);loc=expected.find(text,pointer)
            if loc<0:raise ValueError('Caption reconstruction does not match script')
            pointer=loc+len(text)
            matched=[mapping[k] for k in range(loc,pointer) if k in mapping]
            coverage=len(matched)/max(1,len(text))
            item={**cue,'chapter':cid,'asr_match_coverage':round(coverage,4)}
            if matched and coverage>=.7:
                a=timestamps[matched[0]][0];b=timestamps[matched[-1]][1]
                item.update(asr_start=round(a,4),asr_end=round(b,4),start_delta=round(cue['start']-a,4),end_delta=round(cue['end']-b,4))
                item['verdict']='within_review_tolerance' if abs(item['start_delta'])<=.35 and abs(item['end_delta'])<=.5 else 'review_timing'
            else:item['verdict']='insufficient_asr_match'
            caption_rows.append(item)
    # Attach actual words spoken during every picture segment, for manual semantic review.
    edl=read(edl_path or HERE/'delivery/edit-decision-list.json');allwords=[w for words in word_rows.values() for w in words]
    shot_audio=[]
    for row in edl:
        start=row['start_frame']/30;end=row['end_frame']/30
        words=[w['text'] for w in allwords if w['end']>start and w['start']<end]
        cues=[c['text'] for c in caption_rows if c['end']>start and c['start']<end]
        shot_audio.append({'id':row['id'],'start':start,'end':end,'purpose':row.get('purpose'), 'actual_asr_overlap':''.join(words),'visible_caption_overlap':cues})
    write(out/'caption-sync.json',{'film_sha256':EXPECTED,'method':'Exact renderer cue reconstruction vs independent ASR word timestamps; >350ms start or >500ms end flagged. ASR timestamps remain estimates; flags are not a human listening verdict.', 'captions':caption_rows,'flagged':[c for c in caption_rows if c['verdict']!='within_review_tolerance']})
    write(out/'shot-spoken-content.json',shot_audio)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--artifact',type=Path,required=True);ap.add_argument('--mode',choices=('visual','audio','sync'),required=True);args=ap.parse_args()
    films=list(args.artifact.rglob('李亨浩_四十四天的电话_三分钟.mp4'))
    assert len(films)==1,films
    film=films[0];h=hashlib.sha256()
    with film.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    assert h.hexdigest()==EXPECTED,'The review must use exact release bytes'
    out=HERE/'review-2026-10-16';out.mkdir(exist_ok=True)
    if args.mode=='visual':
        visual(film,args.artifact,out)
    elif args.mode=='sync':
        from verbatim_check import load_chapters
        waveform_sync(film,out,load_chapters(HERE,None),read(HERE/'delivery/technical-report.json')['narration_tempo'])
    else:
        audio(film,out)

if __name__=='__main__':main()
