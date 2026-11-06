#!/usr/bin/env python3
"""Verified 180-second Hakamada assembly: motion clips, aligned narration, captions, score and foley."""
from __future__ import annotations
import argparse, hashlib, json, math, random, shutil, subprocess, sys, time, urllib.error, urllib.request, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RATE=48000; FPS=24; SLOT=6.0; DURATION=180.0; TOTAL=RATE*180
PROJECT='袴田事件：58年'

def run(cmd,capture=False):
    return subprocess.run([str(x) for x in cmd],check=True,capture_output=capture,text=capture)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def probe(path):
    raw=run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate','-show_entries','format=duration','-of','json',path],capture=True).stdout
    d=json.loads(raw);s=d['streams'][0]
    return {'width':int(s['width']),'height':int(s['height']),'fps':s.get('avg_frame_rate'),'duration':float(d['format']['duration'])}

def audio_duration(path):
    # Count MPEG Layer III frames directly so plan validation does not depend on
    # an installed media probe. Decode/render still uses FFmpeg in the workflow.
    data=Path(path).read_bytes();pos=0
    if data[:3]==b'ID3' and len(data)>=10:
        size=((data[6]&0x7f)<<21)|((data[7]&0x7f)<<14)|((data[8]&0x7f)<<7)|(data[9]&0x7f)
        pos=10+size+(10 if data[5]&0x10 else 0)
    bitrate_v1=[0,32,40,48,56,64,80,96,112,128,160,192,224,256,320]
    bitrate_v2=[0,8,16,24,32,40,48,56,64,80,96,112,128,144,160]
    rates=[44100,48000,32000];seconds=0.0;frames=0
    while pos+4<=len(data):
        h=int.from_bytes(data[pos:pos+4],'big')
        if (h>>21)!=0x7ff:
            pos+=1;continue
        version=(h>>19)&3;layer=(h>>17)&3;bi=(h>>12)&15;si=(h>>10)&3
        if version==1 or layer!=1 or bi in (0,15) or si==3:
            pos+=1;continue
        sr=rates[si]//(1 if version==3 else 2 if version==2 else 4)
        kbps=(bitrate_v1 if version==3 else bitrate_v2)[bi]
        length=(144 if version==3 else 72)*kbps*1000//sr+((h>>9)&1)
        if length<24 or pos+length>len(data):
            pos+=1;continue
        seconds+=(1152 if version==3 else 576)/sr;frames+=1;pos+=length
    if frames:return seconds
    return float(run(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',path],capture=True).stdout.strip())

def download(url,dest,expected_sha,expected_bytes):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.is_file() and dest.stat().st_size==expected_bytes and sha(dest)==expected_sha:return
    err=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'hakamada58-film-render/1.0'})
            with urllib.request.urlopen(req,timeout=300) as r,dest.with_suffix('.part').open('wb') as f:shutil.copyfileobj(r,f,1<<18)
            part=dest.with_suffix('.part')
            if part.stat().st_size!=expected_bytes or sha(part)!=expected_sha:raise RuntimeError('clip checksum/byte count mismatch')
            part.replace(dest);return
        except Exception as e:
            err=e
            dest.with_suffix('.part').unlink(missing_ok=True)
            if attempt<3:time.sleep(2**attempt)
    raise RuntimeError(f'could not fetch verified clip {dest.name}: {err}')

def esc_ass(s):return s.replace('\\','\\\\').replace('{','\\{').replace('}','\\}')
def ass_time(seconds):
    cs=max(0,round(seconds*100));h,rem=divmod(cs,360000);m,rem=divmod(rem,6000);s,cs=divmod(rem,100)
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'
def srt_time(seconds):
    ms=max(0,round(seconds*1000));h,rem=divmod(ms,3600000);m,rem=divmod(rem,60000);s,ms=divmod(rem,1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

def wrap_cn(text,limit=18):
    text=text.strip();
    if len(text)<=limit:return text
    # Prefer grammatical pauses while keeping each line visually balanced.
    candidates=[i+1 for i,c in enumerate(text) if c in '，；：、,;:']
    candidates=[i for i in candidates if 7<=i<=len(text)-6]
    cut=min(candidates,key=lambda i:abs(i-len(text)/2)) if candidates else len(text)//2
    return text[:cut]+'\\N'+text[cut:]

def highlight_ass(text,keywords):
    wrapped=wrap_cn(text)
    for word in sorted(keywords,key=len,reverse=True):
        if not word:continue
        tag=r'{\c&H0066D1FF&\fs58\b1}'+esc_ass(word)+r'{\rDefault}'
        wrapped=wrapped.replace(esc_ass(word),tag)
    return wrapped

def speech_plan(story,manifest):
    by={x['id']:x for x in manifest['clips']}
    if set(by)!={f'S{i:02d}' for i in range(1,31)}:raise RuntimeError('need all 30 narration clips')
    rows=[];srt=[];ass=[];previous_end=0.0
    header='''[Script Info]\nScriptType: v4.00+\nWrapStyle: 2\nScaledBorderAndShadow: yes\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Noto Sans CJK SC,46,&H00FFFFFF,&H000000FF,&HAA000000,&H64000000,0,0,0,0,100,100,0,0,1,2.4,1.4,2,100,100,92,1\nStyle: Title,Noto Sans CJK SC,76,&H00F3E3BC,&H000000FF,&H90000000,&H50000000,1,0,0,0,100,100,1,0,1,3,1.5,8,120,120,0,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'''
    for shot in story['shots']:
        sid=shot['id'];entry=by[sid];p=HERE/entry['file']
        if not p.is_file() or sha(p)!=entry['sha256']:raise RuntimeError(f'{sid}: narration hash mismatch')
        if entry['text']!=shot['narration']:raise RuntimeError(f'{sid}: narration text changed')
        raw=audio_duration(p);maxdur=5.8
        speed=max(1.0,raw/maxdur)
        if speed>1.20:raise RuntimeError(f'{sid}: speech needs excessive speed-up ({speed:.2f}x)')
        eff=raw/speed;start=max(shot['start']+0.20,previous_end+0.12);end=start+eff
        if end>shot['start']+6.0+1e-3 or end>DURATION:raise RuntimeError(f'{sid}: speech does not fit its 6-second visual slot')
        previous_end=end
        rows.append({'id':sid,'file':str(p),'start':start,'end':end,'raw_duration':raw,'tempo':speed,'text':shot['narration']})
        plain=wrap_cn(shot['narration']).replace('\\N','\n')
        srt.append(f"{len(srt)+1}\n{srt_time(start)} --> {srt_time(end)}\n{plain}\n")
        ass.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{highlight_ass(shot['narration'],shot['highlight_keywords'])}")
    # Separate final title from the final sentence caption; keep it in the permitted S30 text shot.
    ass.append(f"Dialogue: 1,{ass_time(177.7)},{ass_time(179.8)},Title,,0,0,0,,{{\\an8}}他等了58年，才等来一个无罪\\N袴田事件")
    return rows,header+'\n'.join(ass)+'\n','\n'.join(srt)+'\n'

def make_score(path,rate=RATE,duration=DURATION):
    chords=[[73.42,110.00,146.83,174.61],[58.27,87.31,116.54,146.83],[87.31,130.81,174.61,220.00],[65.41,98.00,130.81,164.81],[73.42,110.00,146.83,174.61],[58.27,87.31,116.54,146.83],[65.41,98.00,130.81,164.81],[73.42,110.00,146.83,174.61]]
    # Slow minor-key pad with a few soft, widely spaced plucks; no percussion or dramatic stings.
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate)
        block=rate*4
        for base in range(0,int(rate*duration),block):
            n=min(block,int(rate*duration)-base);t=(np.arange(n,dtype=np.float32)+base)/rate
            chord=chords[min(7,int((base/rate)//22.5))];x=np.zeros(n,dtype=np.float32)
            for j,f in enumerate(chord):
                vibrato=np.sin(2*np.pi*(0.08+0.015*j)*t+j)*0.0015
                phase=2*np.pi*f*t+vibrato
                x+=(np.sin(phase)+0.22*np.sin(2*phase+0.3*j))/len(chord)
            lfo=0.72+0.18*np.sin(2*np.pi*0.045*t)+0.10*np.sin(2*np.pi*0.071*t+0.7)
            fade=np.minimum(1,np.minimum(t/4,(duration-t)/6)).clip(0,1)
            x*=0.065*lfo*fade
            # A sparse, gentle upper note at long intervals adds continuity without a beat.
            for onset_idx,onset in enumerate(range(8,180,18)):
                local=t-onset
                mask=(local>=0)&(local<2.6)
                if mask.any():
                    f=[293.66,261.63,349.23,329.63][onset_idx%4]
                    x[mask]+=0.009*np.sin(2*np.pi*f*local[mask])*np.exp(-local[mask]*1.55)
            stereo=np.column_stack((x*0.96,x*1.04))
            w.writeframes(np.int16(np.clip(stereo,-0.98,0.98)*32767).tobytes())

def make_sfx(path,story,rate=RATE,duration=DURATION):
    rng=np.random.default_rng(58058);shots=story['shots'];total=int(rate*duration)
    data=np.zeros((total,2),dtype=np.float32)
    outside={'S01','S03','S04','S05','S15','S20','S22','S25','S29','S30'}
    paper={'S06','S10','S19','S21','S23'}
    for shot in shots:
        sid=shot['id'];start=int(shot['start']*rate);end=start+int(SLOT*rate);n=end-start;t=np.arange(n,dtype=np.float32)/rate
        noise=rng.normal(0,1,n).astype(np.float32)
        # Soft, filtered ambience: exterior wind or enclosed room tone.
        drift=np.cumsum(noise);drift-=drift.mean();drift/=max(float(np.max(np.abs(drift))),1e-6)
        bed=drift*0.0035+noise*0.0009
        if sid in outside:bed=drift*0.006+noise*0.0005
        data[start:end,0]+=bed;data[start:end,1]+=bed*0.92
        def thump(at,amp=0.035,f=62,decay=16):
            ix=int(at*rate);length=min(int(.28*rate),n-ix)
            if ix<0 or length<=0:return
            q=np.arange(length,dtype=np.float32)/rate
            z=amp*np.sin(2*np.pi*f*q)*np.exp(-decay*q)
            data[start+ix:start+ix+length,0]+=z;data[start+ix:start+ix+length,1]+=z*0.9
        def rustle(at,dur=.55,amp=.014):
            ix=int(at*rate);length=min(int(dur*rate),n-ix)
            if ix<0 or length<=0:return
            q=np.arange(length,dtype=np.float32)/rate;z=rng.normal(0,1,length).astype(np.float32)
            env=np.sin(np.pi*np.clip(q/max(dur,1e-3),0,1))**2
            z=z*env*amp
            data[start+ix:start+ix+length,0]+=z;data[start+ix:start+ix+length,1]+=z*0.8
        if sid in paper:
            for at in (1.2,3.7):rustle(at,.65,.012)
        if sid in {'S03','S04'}:
            for at in np.arange(.4,5.8,.34):
                rustle(float(at),.11,float(rng.uniform(.003,.009)))
        if sid in {'S08','S16','S18','S22','S29'}:
            thump(1.4,.016,58);thump(3.7,.014,55)
        if sid=='S09':
            for at in np.arange(.5,5.8,1.0):
                ix=int(at*rate);length=int(.045*rate);q=np.arange(length,dtype=np.float32)/rate
                z=.008*np.sin(2*np.pi*1100*q)*np.exp(-95*q)
                data[start+ix:start+ix+length,0]+=z;data[start+ix:start+ix+length,1]+=z
        if sid=='S14':thump(4.1,.07,48,24)
        if sid=='S16':
            q=np.arange(int(.45*rate),dtype=np.float32)/rate;z=.009*(np.sin(2*np.pi*880*q)+.5*np.sin(2*np.pi*1320*q))*np.exp(-7*q)
            ix=int(3.4*rate);data[start+ix:start+ix+len(q),0]+=z;data[start+ix:start+ix+len(q),1]+=z*.8
        if sid=='S24':
            for at in (2.0,4.2):
                q=np.arange(int(.18*rate),dtype=np.float32)/rate;z=.009*np.sin(2*np.pi*1900*q)*np.exp(-22*q);ix=int(at*rate)
                data[start+ix:start+ix+len(q),0]+=z;data[start+ix:start+ix+len(q),1]+=z*.75
        if sid=='S27':
            for at in np.arange(1.0,5.8,.32):rustle(float(at),.16,float(rng.uniform(.002,.005)))
        if sid in {'S29','S30'}:
            # Two faint high bird calls, designed as subtle ambience rather than a loud effect.
            for at,f in ((2.2,1800),(4.5,2100)):
                q=np.arange(int(.35*rate),dtype=np.float32)/rate;z=.003*np.sin(2*np.pi*(f-300*q)*q)*np.sin(np.pi*q/.35)**2;ix=int(at*rate)
                data[start+ix:start+ix+len(q),0]+=z;data[start+ix:start+ix+len(q),1]+=z*.9
    data=np.clip(data,-.95,.95)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate);w.writeframes(np.int16(data*32767).tobytes())

def decode_voice(row,rate=RATE):
    cmd=['ffmpeg','-v','error','-i',row['file'],'-af',f"atempo={row['tempo']:.6f},aresample={rate},apad=pad_dur=0.05",'-ac','2','-ar',str(rate),'-f','f32le','pipe:1']
    raw=subprocess.run(cmd,check=True,stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw,dtype='<f4').reshape(-1,2)

def build_mix(rows,bgm_path,sfx_path,out_path,rate=RATE,duration=DURATION):
    total=int(rate*duration);voice=np.zeros((total,2),dtype=np.float32)
    voice_segments=[]
    for row in rows:
        samples=decode_voice(row,rate);start=int(row['start']*rate);end=min(total,start+len(samples));samples=samples[:end-start]
        fade=min(int(.025*rate),len(samples)//2)
        if fade:
            samples[:fade]*=np.linspace(0,1,fade,dtype=np.float32)[:,None];samples[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)[:,None]
        voice[start:end]+=samples;voice_segments.append((start,end))
    def read_stereo(path):
        with wave.open(str(path),'rb') as f:
            if f.getframerate()!=rate or f.getnchannels()!=2:raise RuntimeError('audio stem format mismatch')
            return np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32).reshape(-1,2)/32768
    score=read_stereo(bgm_path);fx=read_stereo(sfx_path)
    if len(score)<total or len(fx)<total:raise RuntimeError('audio stems too short')
    score=score[:total];fx=fx[:total]
    # Duck the score under speech with short attack/release ramps.
    active=np.zeros(total,dtype=np.float32)
    for a,b in voice_segments:active[a:b]=1
    hop=rate//100;small=active[:total//hop*hop].reshape(-1,hop).max(axis=1)
    kernel=np.ones(19,dtype=np.float32)/19
    smooth=np.convolve(small,kernel,mode='same')
    duck=1-.62*np.repeat(smooth,hop)[:total]
    mix=voice+score*(.33*duck[:,None])+fx*.85
    rms=float(np.sqrt(np.mean(mix.astype(np.float64)**2)));peak=float(np.max(np.abs(mix)))
    if rms>1e-9:
        gain=min(10**((-20-math.log10(rms)*20)/20),10**((-1.5-20*math.log10(max(peak,1e-9)))/20),8)
        mix*=gain
    peak=float(np.max(np.abs(mix)))
    ceiling=10**(-1.5/20)
    if peak>ceiling:mix*=ceiling/peak
    fade=int(2*rate);mix[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)[:,None]
    with wave.open(str(out_path),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate);w.writeframes(np.int16(np.clip(mix,-.99,.99)*32767).tobytes())
    return {'rms_dbfs':round(20*math.log10(float(np.sqrt(np.mean(mix**2)))),2),'peak_dbfs':round(20*math.log10(max(float(np.max(np.abs(mix))),1e-9)),2),'duration_seconds':duration}

def font_path():
    candidates=[Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'),Path('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc')]
    for p in candidates:
        if p.exists():return p
    raise RuntimeError('Noto CJK fonts are required for the Chinese cover')

def make_cover(clip,cover):
    raw=Path(cover).with_suffix('.source.jpg')
    run(['ffmpeg','-v','error','-y','-ss','2.5','-i',clip,'-frames:v','1',raw])
    im=Image.open(raw).convert('RGB').resize((1920,1080));raw.unlink(missing_ok=True)
    overlay=Image.new('RGBA',im.size,(0,0,0,0));d=ImageDraw.Draw(overlay)
    for y in range(1080):
        alpha=int(118*max(0,1-y/1080))
        d.line((0,y,1920,y),fill=(7,11,14,alpha))
    im=Image.alpha_composite(im.convert('RGBA'),overlay);d=ImageDraw.Draw(im)
    f=ImageFont.truetype(str(font_path()),74);small=ImageFont.truetype(str(font_path()),34)
    title='他等了58年，才等来一个无罪';subtitle='袴田事件 · 58年'
    d.text((120,125),title,font=f,fill=(246,235,211,255),stroke_width=2,stroke_fill=(0,0,0,160))
    d.text((126,230),subtitle,font=small,fill=(229,215,180,255),stroke_width=1,stroke_fill=(0,0,0,140))
    Path(cover).parent.mkdir(parents=True,exist_ok=True);im.convert('RGB').save(cover,quality=92)

def make_delivery_note(path):
    Path(path).write_text('''# 《袴田事件：58年》交付说明\n\n片名：他等了58年，才等来一个无罪：袴田事件\n简介：以虚构演员式写实重现呈现袴田事件的漫长司法历程。影像为生成式戏剧化再现，不是真实人物肖像或档案影像。\n话题：#袴田事件 #司法正义 #冤案 #再审 #纪录短片\n\n旁白按逐镜台词生成；字幕逐句随旁白出现，关键词使用金色强调；BGM 为克制的程序化氛围配乐，SFX 为低音量程序化环境声设计。\n''',encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--work',default='work/hakamada58/render');ap.add_argument('--out',default='work/hakamada58/delivery');ap.add_argument('--plan-only',action='store_true');args=ap.parse_args()
    work=ROOT/args.work;out=ROOT/args.out;work.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    story=json.loads((HERE/'story.json').read_text(encoding='utf-8'));results=json.loads((HERE/'results.json').read_text(encoding='utf-8'));manifest=json.loads((HERE/'audio'/'manifest.json').read_text(encoding='utf-8'))
    if results.get('phase')!='clips_ready' or len(results.get('shots',{}))!=30 or any(results['shots'][f'S{i:02d}'].get('status')!='completed' or results['shots'][f'S{i:02d}'].get('visual_review')!='passed' for i in range(1,31)):
        raise RuntimeError('all 30 motion clips must be completed and visually passed before assembly')
    if manifest.get('completed')!=30 or len(manifest.get('clips',[]))!=30:raise RuntimeError('all 30 voiceover tracks are required')
    rows,ass,srt=speech_plan(story,manifest)
    if args.plan_only:
        print(json.dumps({'shots':30,'voiceovers':30,'duration':180,'speech_cues':len(rows),'output':str(out)},ensure_ascii=False));return 0
    captions=out/'captions.ass';captions.write_text(ass,encoding='utf-8-sig');(out/'captions.srt').write_text(srt,encoding='utf-8')
    rawdir=work/'raw';rawdir.mkdir(parents=True,exist_ok=True);segments=work/'segments';segments.mkdir(parents=True,exist_ok=True)
    concat=[]
    for i in range(1,31):
        sid=f'S{i:02d}';row=results['shots'][sid];raw=rawdir/f'{sid}.mp4';download(row['video_url'],raw,row['sha256'],int(row['bytes']))
        meta=probe(raw)
        if meta['width']<640 or meta['height']<360 or meta['duration']<5.9:raise RuntimeError(f'{sid}: invalid source {meta}')
        seg=segments/f'{sid}.mp4'
        run(['ffmpeg','-v','error','-y','-i',raw,'-an','-vf',f'trim=duration={SLOT},setpts=PTS-STARTPTS,fps={FPS},scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,setsar=1,format=yuv420p','-frames:v',str(int(SLOT*FPS)),'-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',seg])
        concat.append(seg)
    listfile=work/'concat.txt';listfile.write_text(''.join(f"file '{p.as_posix()}'\n" for p in concat),encoding='utf-8')
    silent=work/'silent.mp4';run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',listfile,'-an','-c','copy','-movflags','+faststart',silent])
    bgm=work/'bgm.wav';sfx=work/'sfx.wav';mix=work/'mix.wav';make_score(bgm);make_sfx(sfx,story);mix_report=build_mix(rows,bgm,sfx,mix)
    report_path=out/'audio_report.json';report_path.write_text(json.dumps(mix_report,indent=2)+'\n',encoding='utf-8')
    delivery=out/'delivery.md';make_delivery_note(delivery)
    result=out/'Hakamada58_Final.mp4';fontdir='/usr/share/fonts/opentype/noto'
    filt=f"subtitles={captions.as_posix()}:fontsdir={fontdir}"
    run(['ffmpeg','-v','error','-y','-i',silent,'-i',mix,'-vf',filt,'-map','0:v:0','-map','1:a:0','-t',str(DURATION),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','256k','-ar',str(RATE),'-movflags','+faststart',result])
    final=probe(result)
    if final['width']!=1920 or final['height']!=1080 or abs(final['duration']-DURATION)>.08:raise RuntimeError(f'final master failed spec: {final}')
    make_cover(silent,out/'cover.jpg')
    report={'project':PROJECT,'video':final,'shots':30,'narrations':30,'audio_mix':mix_report,'source_sha256':{f'S{i:02d}':results['shots'][f'S{i:02d}']['sha256'] for i in range(1,31)}}
    (out/'render_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
