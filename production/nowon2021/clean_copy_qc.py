#!/usr/bin/env python3
"""Check the explicitly requested unwatermarked but still unreviewed copy."""
import array
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'work/nowon2021/unwatermarked-review'
out=ROOT/'production/nowon2021/qa/unwatermarked'
videos=list(source.rglob('*未审片无水印.mp4'))
if len(videos)!=1: raise RuntimeError(f'expected one requested review copy, found {len(videos)}')
video=videos[0]
report=json.loads((video.parent/'render_report.json').read_text(encoding='utf-8'))
ass=(video.parent/'captions.ass').read_text(encoding='utf-8-sig')
if report.get('draft') is not True or report.get('review_watermark') is not False:
    raise RuntimeError('incorrect draft/watermark provenance')
if '未审片预览 · 画面与字幕待复核' in ass or 'AI动画情景重现 · 非新闻影像' not in ass:
    raise RuntimeError('wrong preview watermark or missing reenactment disclosure')
probe=json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)],check=True,stdout=subprocess.PIPE).stdout)
v=next(x for x in probe['streams'] if x['codec_type']=='video')
a=next(x for x in probe['streams'] if x['codec_type']=='audio')
if (v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames']),a['sample_rate'],a['channels']) != (1920,1080,'24/1',4320,'48000',2):
    raise RuntimeError('media specifications do not match')
raw=subprocess.run(['ffmpeg','-v','error','-ss','179','-i',str(video),'-t','1','-map','0:a:0','-f','f32le','-acodec','pcm_f32le','-ar','48000','-ac','2','pipe:1'],check=True,stdout=subprocess.PIPE).stdout
samples=array.array('f');samples.frombytes(raw)
if len(samples)!=96000 or max(map(abs,samples))>1e-12: raise RuntimeError('encoded final second is not silent')
h=hashlib.sha256()
with video.open('rb') as f:
    for chunk in iter(lambda:f.read(1<<20),b''): h.update(chunk)
out.mkdir(parents=True,exist_ok=True)
shutil.copy2(video.parent/'封面_未审片无水印.png',out/'封面_未审片无水印.png')
subprocess.run(['ffmpeg','-v','error','-y','-ss','2.5','-i',str(video),'-frames:v','1',str(out/'画面抽检.png')],check=True)
result={'draft':True,'review_watermark_removed':True,'ai_reenactment_disclosure_retained':True,'visual_review_pending':report.get('visual_review_pending',[]),'sha256':h.hexdigest(),'width':v['width'],'height':v['height'],'fps':v['r_frame_rate'],'frames':int(v['nb_frames']),'duration':probe['format']['duration'],'audio_sample_rate':int(a['sample_rate']),'audio_channels':a['channels'],'decoded_last_second_peak':max(map(abs,samples)),'limitation':'Video and audio not fully reviewed; captions are estimated.'}
(out/'technical-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
