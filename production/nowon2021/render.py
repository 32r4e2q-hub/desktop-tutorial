#!/usr/bin/env python3
"""Render the Nowon film only from reviewed Agnes footage and recorded per-shot narration.

No still-image substitute, fabricated receipt, background score, or silent narration fallback.
The script is deliberately gated until all material and visual reviews exist.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, shutil, subprocess, urllib.request, wave
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FPS=24; RATE=48000; DURATION=180


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()


def run(command, *, capture=False):
    return subprocess.run([str(x) for x in command],check=True,text=True,capture_output=capture)


def probe(path):
    import av
    with av.open(str(path)) as container:
        stream=next((s for s in container.streams if s.type=='video'),None)
        if stream is None: raise RuntimeError(f'{path}: no video stream')
        duration=(container.duration / av.time_base if container.duration else
                  float(stream.duration * stream.time_base))
        audio=next((s for s in container.streams if s.type=='audio'),None)
        return dict(width=stream.width,height=stream.height,duration=float(duration),
                    fps=float(stream.average_rate) if stream.average_rate else None,
                    frames=int(stream.frames) if stream.frames else None,
                    audio_rate=int(audio.rate) if audio and audio.rate else None,
                    audio_channels=int(audio.channels) if audio and audio.channels else None)


def duration_audio(path):
    import av
    with av.open(str(path)) as container:
        stream=next((s for s in container.streams if s.type=='audio'),None)
        if stream is None: raise RuntimeError(f'{path}: no audio stream')
        if container.duration: return float(container.duration/av.time_base)
        if stream.duration is not None and stream.time_base is not None:
            return float(stream.duration*stream.time_base)
        raise RuntimeError(f'{path}: cannot determine audio duration')


def voice_activity(path,duration):
    """Measure leading/trailing silence; sentence-level cues still need listening QC."""
    proc=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af',
                         'silencedetect=noise=-40dB:d=0.10','-f','null','-'],
                        text=True,capture_output=True,check=True)
    events=[]
    for line in proc.stderr.splitlines():
        start=re.search(r'silence_start:\s*(-?[\d.]+)',line)
        end=re.search(r'silence_end:\s*(-?[\d.]+)',line)
        if start: events.append(('start',max(0.0,float(start.group(1)))))
        if end: events.append(('end',float(end.group(1))))
    lead=events[1][1] if len(events)>=2 and events[0][0]=='start' and events[0][1]<0.06 and events[1][0]=='end' else 0.0
    tail=duration
    if events and events[-1][0]=='start': tail=events[-1][1]
    elif len(events)>=2 and events[-2][0]=='start' and events[-1][0]=='end' and events[-1][1]>=duration-0.08:
        tail=events[-2][1]
    if tail-lead<0.15: raise RuntimeError(f'{path}: no meaningful detected narration')
    return max(0.0,lead),min(duration,tail)


def srt_time(seconds):
    ms=max(0,round(seconds*1000));h,rem=divmod(ms,3600000);m,rem=divmod(rem,60000);s,ms=divmod(rem,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'


def ass_time(seconds):
    cs=max(0,round(seconds*100));h,rem=divmod(cs,360000);m,rem=divmod(rem,6000);s,cs=divmod(rem,100)
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def ass_escape(text):
    return text.replace('\\',r'\\').replace('{',r'\{').replace('}',r'\}')


def highlight(text,keywords):
    """Escape text before wrapping disjoint keyword spans in ASS tags."""
    terms=sorted({x for x in keywords if x and x in text},key=len,reverse=True)
    output=[];pos=0
    while pos<len(text):
        match=next((term for term in terms if text.startswith(term,pos)),None)
        if match:
            output.append(r'{\c&H0066D1FF&\fs55\b1}'+ass_escape(match)+r'{\rDefault}')
            pos+=len(match)
        else:
            output.append(ass_escape(text[pos]));pos+=1
    return ''.join(output)


def verify_inputs(story,results,manifest):
    shots=story['shots']
    if len(shots)!=30 or shots[-1]['end']!=DURATION: raise RuntimeError('plan must be exactly 30 shots / 180 seconds')
    if results.get('phase')!='clips_ready': raise RuntimeError('Agnes clips are not yet all ready')
    entries=results.get('shots',{})
    clips={c['id']:c for c in manifest.get('clips',[])}
    if len(clips)!=30 or len(manifest.get('clips',[]))!=30 or manifest.get('completed')!=30: raise RuntimeError('all 30 recorded voice clips are required')
    expected_voice=json.loads((HERE/'voice-selection.json').read_text(encoding='utf-8'))['voice_id']
    for shot in shots:
        sid=shot['id']; result=entries.get(sid,{})
        if result.get('status')!='completed' or result.get('visual_review')!='passed' or not result.get('video_id'):
            raise RuntimeError(f'{sid}: completed provider receipt and human visual approval required')
        if not result.get('sha256') or not result.get('bytes') or not result.get('video_url'):
            raise RuntimeError(f'{sid}: provider media provenance is incomplete')
        v=clips.get(sid,{})
        path=(HERE/v.get('file','')).resolve()
        if not path.is_relative_to(HERE) or not path.is_file() or not v.get('sha256') or sha(path)!=v['sha256']:
            raise RuntimeError(f'{sid}: recorded narration file missing or SHA mismatch')
        if v.get('text')!=shot['narration']: raise RuntimeError(f'{sid}: narration text changed')
        if v.get('voice_id')!=expected_voice: raise RuntimeError(f'{sid}: narrator differs from selected voice')
    return clips


def speech_plan(story,clips):
    rows=[]
    for shot in story['shots']:
        sid=shot['id']; path=(HERE/clips[sid]['file']).resolve()
        raw=duration_audio(path);lead,tail=voice_activity(path,raw)
        # Leave a brief leading and trailing buffer and the requested final second of silence.
        start=shot['start']+0.12
        limit=min(shot['end']-0.10,178.85)
        window=limit-start
        if window<=0: raise RuntimeError(f'{sid}: no time for voice')
        tempo=max(1.0,raw/window)
        if tempo>1.12: raise RuntimeError(f'{sid}: narration requires {tempo:.2f}x; rewrite/re-record instead')
        end=start+raw/tempo
        caption_start=start+lead/tempo;caption_end=start+tail/tempo
        if caption_end>limit+0.001: raise RuntimeError(f'{sid}: narration overruns the shot')
        rows.append(dict(id=sid,file=str(path),start=start,end=end,tempo=tempo,
                         caption_start=caption_start,caption_end=caption_end,
                         text=shot['narration'],keywords=shot.get('highlight_keywords',[])))
    return rows


def subtitles(rows):
    header='''[Script Info]\nScriptType: v4.00+\nWrapStyle: 2\nScaledBorderAndShadow: yes\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Noto Sans CJK SC,46,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,3,1,2,120,120,96,1\nStyle: Label,Noto Sans CJK SC,25,&H00E5E5E5,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,7,52,52,35,1\nStyle: Title,Noto Sans CJK SC,76,&H0066D1FF,&H000000FF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,3,1,5,120,120,0,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
    ass=[f'Dialogue: 0,{ass_time(0)},{ass_time(180)},Label,,0,0,0,,AI动画情景重现 · 非新闻影像']
    srt=[]
    for i,r in enumerate(rows,1):
        a,b=r['caption_start'],r['caption_end']
        ass.append(f"Dialogue: 1,{ass_time(a)},{ass_time(b)},Default,,0,0,0,,{highlight(r['text'],r['keywords'])}")
        srt.append(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{r['text']}\n")
    ass.append(r'Dialogue: 2,0:02:54.30,0:02:59.00,Title,,0,0,0,,{\fad(300,300)}芦原区三母女案\N{\fs40}首尔 · 2021 · 一次门铃')
    return header+'\n'.join(ass)+'\n','\n'.join(srt)+'\n'


def fetch_verified(row,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    def valid(p): return p.is_file() and p.stat().st_size==int(row['bytes']) and sha(p)==row['sha256']
    if valid(dest): return
    part=dest.with_suffix('.mp4.part')
    try:
        with urllib.request.urlopen(urllib.request.Request(row['video_url'],headers={'User-Agent':'nowon2021-render/1.0'}),timeout=300) as response,part.open('wb') as out:
            shutil.copyfileobj(response,out,1<<20)
        if not valid(part): raise RuntimeError(f'{dest.name}: checksum/size mismatch')
        os.replace(part,dest)
    finally:
        part.unlink(missing_ok=True)


def make_foley(path,story):
    import numpy as np
    rng=np.random.default_rng(20210323)
    total=RATE*DURATION
    # Low, continuous room tone only; no score or soundtrack instruments.
    mono=rng.normal(0,0.00065,total).astype('float32')
    for shot in story['shots']:
        sid=shot['id']; start=shot['start']
        events=[]
        if sid in {'SH01','SH17','SH29'}: events=[(0.85,880,.28),(1.14,660,.38)]
        if sid in {'SH02','SH18','SH20'}: events=[(1.7,180,.07)]
        if sid in {'SH10','SH12','SH19','SH23'}: events=[(t,1400,.035) for t in (1,2,3,4)]
        for offset,hz,dur in events:
            begin=round((start+offset)*RATE); n=min(round(dur*RATE),total-begin)
            if n<=0: continue
            t=np.arange(n,dtype='float32')/RATE
            mono[begin:begin+n]+=0.009*np.sin(2*np.pi*hz*t)*np.exp(-8*t)
    mono[-RATE:]=0
    stereo=np.column_stack((mono,mono*.95))
    with wave.open(str(path),'wb') as out:
        out.setnchannels(2);out.setsampwidth(2);out.setframerate(RATE)
        out.writeframes(np.int16(np.clip(stereo,-.99,.99)*32767).tobytes())


def mix_voice(rows,foley,mix):
    cmd=['ffmpeg','-v','error','-y','-i',foley]
    for row in rows: cmd+=['-i',row['file']]
    filters=['[0:a]aresample=48000[a0]']
    for i,row in enumerate(rows,1):
        delay=round(row['start']*1000)
        filters.append(f'[{i}:a]aresample=48000,atempo={row["tempo"]:.8f},adelay={delay}|{delay}[a{i}]')
    ins=''.join(f'[a{i}]' for i in range(len(rows)+1))
    filters.append(f'{ins}amix=inputs={len(rows)+1}:duration=first:normalize=0,alimiter=limit=0.84,atrim=0:179,apad=pad_dur=1,atrim=0:180[a]')
    cmd+=['-filter_complex',';'.join(filters),'-map','[a]','-ar',str(RATE),'-ac','2','-c:a','pcm_s16le',mix]
    run(cmd)



def audit_mix(path,rows):
    """Check format, overall level, each speech window and the requested final second."""
    import numpy as np
    with wave.open(str(path),'rb') as audio:
        if audio.getframerate()!=RATE or audio.getnchannels()!=2 or audio.getsampwidth()!=2 or audio.getnframes()!=RATE*DURATION:
            raise RuntimeError('mix is not 180 seconds / 48kHz / stereo PCM')
        samples=np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2').reshape(-1,2).astype('float32')/32768
    rms=float(np.sqrt(np.mean(samples.astype('float64')**2)))
    peak=float(np.max(np.abs(samples)))
    db=lambda x: 20*math.log10(max(x,1e-9))
    if not -35 <= db(rms) <= -8 or db(peak)>-0.5:
        raise RuntimeError(f'unsafe overall narration mix rms={db(rms):.1f} peak={db(peak):.1f} dBFS')
    if np.max(np.abs(samples[-RATE:])) > 1/32768:
        raise RuntimeError('last second of mix must be silent')
    windows=[]
    for r in rows:
        a=round(r['caption_start']*RATE);b=round(r['caption_end']*RATE)
        if b<=a: raise RuntimeError(f"{r['id']}: invalid voice window")
        segment=samples[a:b].astype('float64')
        level=db(float(np.sqrt(np.mean(segment**2))))
        if level < -42: raise RuntimeError(f"{r['id']}: voice window is too quiet ({level:.1f} dBFS)")
        windows.append({'id':r['id'],'rms_dbfs':round(level,2)})
    return {'duration':180,'sample_rate':RATE,'channels':2,'rms_dbfs':round(db(rms),2),
            'peak_dbfs':round(db(peak),2),'last_second_silent':True,'speech_window_levels':windows}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan-only',action='store_true')
    parser.add_argument('--work',default='work/nowon2021/edit');parser.add_argument('--out',default='work/nowon2021/delivery')
    args=parser.parse_args();work=ROOT/args.work;out=ROOT/args.out
    story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    results=json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    manifest=json.loads((HERE/'audio'/'manifest.json').read_text(encoding='utf-8'))
    clips=verify_inputs(story,results,manifest); rows=speech_plan(story,clips)
    if args.plan_only:
        print(json.dumps({'shots':30,'duration':180,'voiceovers':len(rows),'speech_windows':rows},ensure_ascii=False,indent=2));return 0
    work.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    ass,srt=subtitles(rows);(out/'captions.ass').write_text(ass,encoding='utf-8-sig');(out/'captions.srt').write_text(srt,encoding='utf-8')
    source=ROOT/'work/nowon2021/clips'; source.mkdir(parents=True,exist_ok=True)
    segdir=work/'segments';segdir.mkdir(parents=True,exist_ok=True);segments=[]
    for index,shot in enumerate(story['shots'],1):
        sid=shot['id'];row=results['shots'][sid];raw=source/f'{sid}.mp4';fetch_verified(row,raw)
        info=probe(raw); dur=shot['duration']
        if info['width']<640 or info['height']<360 or info['duration']<dur: raise RuntimeError(f'{sid}: source too small or short: {info}')
        effects=[f'trim=duration={dur}','setpts=PTS-STARTPTS',f'fps={FPS}','scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos','crop=1920:1080','setsar=1','format=yuv420p']
        if index<=14: effects += ['fade=t=in:st=0:d=0.16',f'fade=t=out:st={dur-0.16}:d=0.16']
        elif index in (18,22,25): effects += [f"drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='gte(t,{dur-1/FPS:.6f})'"]
        elif index==30: effects += ['fade=t=in:st=0:d=0.3']
        seg=segdir/f'{sid}.mp4'
        run(['ffmpeg','-v','error','-y','-i',raw,'-an','-vf',','.join(effects),'-frames:v',str(dur*FPS),'-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',seg])
        segment_info=probe(seg)
        if segment_info['frames'] != dur*FPS or segment_info['fps'] != FPS:
            raise RuntimeError(f'{sid}: normalized segment has incorrect frame count/rate: {segment_info}')
        segments.append(seg)
    concat=work/'concat.txt';concat.write_text(''.join(f"file '{x.as_posix()}'\n" for x in segments),encoding='utf-8')
    silent=work/'silent.mp4';run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',concat,'-an','-c','copy',silent])
    foley=work/'foley.wav';mix=work/'mix.wav';make_foley(foley,story);mix_voice(rows,foley,mix)
    mix_report=audit_mix(mix,rows)
    final=out/'芦原区三母女案_一次门铃_初剪.mp4'
    # libass reads the ASS file; output path does not enter the filter expression.
    run(['ffmpeg','-v','error','-y','-i',silent,'-i',mix,'-vf',f"subtitles='{(out/'captions.ass').as_posix()}'",'-map','0:v:0','-map','1:a:0','-t','180','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','256k','-ar',str(RATE),'-movflags','+faststart',final])
    info=probe(final)
    if (info['width']!=1920 or info['height']!=1080 or abs(info['duration']-180)>.08
        or info['fps']!=FPS or info['frames']!=FPS*DURATION or info['audio_rate']!=RATE or info['audio_channels']!=2):
        raise RuntimeError(f'final spec mismatch: {info}')
    report={'note':'待人工画面/字幕/听觉复审的初剪；不是历史影像。','film':str(final),'video':info,'shots':30,'voiceovers':30,'audio':'无BGM，仅旁白与合成音效','audio_mix':mix_report,'voice_windows':rows,'sources':{s['id']:results['shots'][s['id']]['sha256'] for s in story['shots']}}
    (out/'render_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'film':str(final),'video':info},ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
