import json,subprocess as s
from pathlib import Path
P=Path(__file__).parent;plan=json.loads((P/'edit_plan.json').read_text());shots={x['id']:x for x in json.loads((P/'story.json').read_text())['shots']};src='base.mp4';order=plan['order'];media=Path('media');media.mkdir(exist_ok=True)
def ff(*args):s.run(['ffmpeg','-nostdin','-y','-loglevel','error','-filter_complex_threads','2',*map(str,args)],check=True)
for sid in order:
 sh=shots[sid];n=sh['duration'];args=['-ss',sh['start'],'-t',n,'-i',src];out=['-map','0:v:0'];r=plan['replacements'].get(sid)
 if r:
  clip=media/(sid+'.mp4');animated=clip.is_file() and s.run(['ffprobe','-v','error',str(clip)]).returncode==0
  args+=['-i',clip] if animated else ['-i',P/'reference_v4'/(r[0]+'.jpg')];vf=('fps=24,tpad=stop_mode=clone:stop_duration=2' if animated else f"scale=2400:-2,zoompan=z='1.01+0.00055*on':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={24*n}:s=1920x1080:fps=24")
  vf+=',scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:804,setsar=1[scene];[0:v][scene]overlay=0:138[out]';out=['-filter_complex','[1:v]'+vf,'-map','[out]'];print(sid,'moving reenactment' if animated else 'illustrated insert',flush=True)
 ff(*args,*out,'-map','0:a:0','-t',n,'-c:v','libx264','-preset','veryfast','-crf','17','-threads','3','-pix_fmt','yuv420p','-r','24','-c:a','pcm_s16le',media/(sid+'.mkv'))
(media/'list.txt').write_text(''.join(f"file '{sid}.mkv'\n" for sid in order));out='Baiyin-E21-People-Cut.mp4';ff('-f','concat','-safe','0','-i',media/'list.txt','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',out)
m=json.loads(s.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',out]));v=next(i for i in m['streams'] if i['codec_type']=='video');assert (v['width'],v['height'])==(1920,1080) and any(i['codec_type']=='audio' for i in m['streams']);assert abs(float(m['format']['duration'])-sum(shots[i]['duration'] for i in order))<.5,m['format'];print('verified',m['format']['duration'])
