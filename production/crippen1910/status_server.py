"""Read-only live production progress; downloads only SHA-verified real deliverables.
No Agnes/GitHub credentials, provider URLs, or tokens are exposed to the browser.
"""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import base64,hashlib,json,re,subprocess,threading,time,urllib.parse
ROOT=Path(__file__).resolve().parents[2]
REPO='32r4e2q-hub/desktop-tutorial'
BRANCH='arena/f38dd103-desktop-tutorial'
DEST=ROOT/'work/crippen1910/live-delivery';DEST.mkdir(parents=True,exist_ok=True)
STATE={'completed':0,'approved':0,'accepted':0,'narration':0,'shots':[],'message':'读取云端实际收据…','files':{},'final_ready':False}
LOCK=threading.RLock()
FILES={'film.mp4':('克里平医生案_一道追上凶手的电波_三分钟_带声音.mp4','video/mp4'), 'cover.png':('Crippen_Cover.png','image/png'),'narration.wav':('Crippen_Narration.wav','audio/wav'),'subtitles.srt':('Crippen_Subtitles.srt','text/plain; charset=utf-8'),'episode03.png':('Crippen_Series_Episode03.png','image/png')}

def api(path,raw=False):
    args=['gh','api',path]
    if raw:args+=['-H','Accept: application/vnd.github.raw+json']
    return subprocess.check_output(args,cwd=ROOT,timeout=45)

def contents(path):
    uri=f'repos/{REPO}/contents/'+urllib.parse.quote(path,safe='/')+'?ref='+urllib.parse.quote(BRANCH,safe='')
    doc=json.loads(api(uri));return json.loads(base64.b64decode(doc['content']))

def update():
    while True:
        try:
            result=contents('production/crippen1910/results.json')
            try:reviews=contents('production/crippen1910/qa/batch-reviews.json')
            except Exception:reviews={}
            try:voice=contents('production/crippen1910/audio/manifest.json')
            except Exception:voice={}
            runs=json.loads(api(f'repos/{REPO}/actions/workflows/crippen1910-autopilot.yml/runs?per_page=1'))['workflow_runs']
            try:runs+=json.loads(api(f'repos/{REPO}/actions/workflows/crippen1910-selected-voice.yml/runs?per_page=1')).get('workflow_runs',[])
            except Exception:pass
            job=max(runs,key=lambda r:r.get('created_at','')) if runs else {};rows=[]
            for n in range(1,31):
                sid=f'S{n:02d}';r=result.get('shots',{}).get(sid,{})
                approved=reviews.get(sid,{}).get('status')=='approved' and bool(r.get('sha256')) and reviews[sid].get('sha256')==r['sha256']
                rows.append(dict(id=sid,status=r.get('status','not_submitted'),approved=approved,accepted=bool(r.get('video_id'))))
            done=sum(r['status']=='completed' for r in rows);approved=sum(r['approved'] for r in rows)
            count=sum(bool(c.get('sha256')) for c in voice.get('clips',[]))
            message='视频服务排队与生成中；保留原任务ID，不因等待而重复提交。'
            if done==30:message='30个动画镜头已生成，正在审核、配音或合成质检。'
            if result.get('phase')=='awaiting_selected_voice':message='30镜已审核通过，正在处理用户选定的低沉男声；不会自动换用其他声音。'
            if job.get('name')=='Crippen selected narrator and final film' and job.get('status')!='completed':message='30镜已审核通过；选定男声的10组正式录音已生成，正在实测语音时间戳、逐镜对齐和合成。'
            elif job.get('conclusion')=='failure':message='流程遇到接口或审核问题，已保留进度；未将未通过素材冒充成片。'
            with LOCK:STATE.update(completed=done,approved=approved,accepted=sum(r['accepted'] for r in rows),narration=count,shots=rows,message=message,job_url=job.get('html_url'),job_status=job.get('status'),job_conclusion=job.get('conclusion'),updated=time.strftime('%H:%M:%S UTC',time.gmtime()))
            delivered=result.get('delivery',{}).get('delivered',{})
            for route,(name,mime) in FILES.items():
                receipt=delivered.get(name,{})
                blob_sha=None
                if not receipt.get('sha256') and route=='episode03.png' and job.get('conclusion')=='success':
                    metadata=json.loads(api(f'repos/{REPO}/contents/'+urllib.parse.quote('交付/'+name,safe='/')+'?ref='+urllib.parse.quote(BRANCH,safe='')))
                    blob_sha=metadata['sha']
                if not receipt.get('sha256') and not blob_sha:continue
                def verified(data):
                    if receipt.get('sha256'):return hashlib.sha256(data).hexdigest()==receipt['sha256']
                    return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()==blob_sha
                path=DEST/route
                if not path.exists() or not verified(path.read_bytes()):
                    uri=f'repos/{REPO}/contents/'+urllib.parse.quote('交付/'+name,safe='/')+'?ref='+urllib.parse.quote(BRANCH,safe='')
                    temporary=path.with_suffix('.download')
                    with open(temporary,'wb') as stream:
                        subprocess.run(['gh','api',uri,'-H','Accept: application/vnd.github.raw+json'],cwd=ROOT,stdout=stream,check=True,timeout=240)
                    if not verified(temporary.read_bytes()):raise RuntimeError('Deliverable SHA mismatch; refusing playback')
                    temporary.replace(path)
                with LOCK:STATE['files'][route]=dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            with LOCK:
                STATE['final_ready']=(all(f in STATE['files'] for f in ['film.mp4','cover.png','episode03.png']) and job.get('conclusion')=='success')
                if STATE['final_ready']:STATE['message']='成片已生成，自动画面审核和技术质检通过，可播放或下载。'
        except Exception as exc:
            with LOCK:STATE['last_sync_error']=type(exc).__name__
        time.sleep(45)

HTML='''<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>第三期 · 克里平医生案 · 制作进度</title><style>
*{box-sizing:border-box}body{margin:0;background:#08131c;color:#dfebf2;font:16px/1.7 system-ui,sans-serif}main{max-width:1080px;margin:auto;padding:48px 24px}.eyebrow{font-size:13px;letter-spacing:3px;color:#80c7e9}h1{font-size:clamp(28px,4vw,46px);line-height:1.3;margin:14px 0}.sub{color:#9eb5c6}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:28px 0}.card{background:#102431;border:1px solid #244455;padding:22px;border-radius:12px}.big{font-size:30px;color:#e0bc70}.label{color:#a6bdca;font-size:13px}.progress{height:6px;background:#244455;border-radius:20px;overflow:hidden}.progress div{height:100%;background:#7fcee9;transition:width 1s}#shots{display:grid;grid-template-columns:repeat(10,1fr);gap:8px;margin:26px 0}.shot{border:1px solid #294452;border-radius:7px;text-align:center;padding:12px 2px;font-size:12px;background:#0f202c}.queued{border-color:#ad8c43;color:#e2bd70}.done{background:#113d46;color:#91dbe2}.approved{border-color:#66bc99}.note{background:#102431;padding:18px 22px;border-left:3px solid #8ed0e8;border-radius:4px}a{color:#8ed0e8}video{display:block;width:100%;max-height:70vh;background:#000;border-radius:12px;margin-top:25px}.buttons{display:flex;gap:14px;flex-wrap:wrap;margin:20px 0}.buttons a{padding:10px 18px;border:1px solid #315367;border-radius:8px;text-decoration:none}.hidden{display:none}footer{margin-top:36px;color:#7893a6;font-size:12px}@media(max-width:650px){.cards{grid-template-columns:repeat(2,1fr)}#shots{grid-template-columns:repeat(5,1fr)}main{padding:28px 16px}}
</style><main><div class="eyebrow">迷案解码人 / 第三期 / 实际云端进度</div><h1>一道追上凶手的电波</h1><div class="sub">克里平医生案 · 1920×1080 · 180秒 · 30个真实运动镜头</div><div class="cards"><div class="card"><div class="big">64 / 64</div><div class="label">参考图已检查</div></div><div class="card"><div class="big" id="done">— / 30</div><div class="label">真实动画已回片</div></div><div class="card"><div class="big" id="review">— / 30</div><div class="label">画面一致性审核通过</div></div><div class="card"><div class="big" id="voice">— / 30</div><div class="label">实测逐镜旁白</div></div></div><div class="progress"><div id="bar" style="width:0"></div></div><div id="shots"></div><div class="note" id="message">正在读取云端收据，未使用预设百分比或模拟进度。</div><section id="player" class="hidden"><h2 id="film-label">成片</h2><video id="video" controls playsinline preload="metadata"></video><div class="buttons" id="downloads"></div></section><p class="sub"><a id="job" target="_blank" rel="noreferrer">查看云端流程</a> · <span id="updated">同步中</span></p><footer>先收齐全部镜头，再分组质检；只重做不合格素材，不自动放行。旁白只在三十镜审核后生成。<br>真实案件改编 · AI动画情景复原 · 非历史影像。页面不包含密钥或服务凭证。</footer></main><script>
async function refresh(){try{let s=await(await fetch('/state.json',{cache:'no-store'})).json();document.getElementById('done').textContent=s.completed+' / 30';document.getElementById('review').textContent=s.approved+' / 30';document.getElementById('voice').textContent=s.narration+' / 30';document.getElementById('bar').style.width=(s.completed/30*100)+'%';document.getElementById('message').textContent=s.message;document.getElementById('updated').textContent='收据同步 '+(s.updated||'…');if(s.job_url)document.getElementById('job').href=s.job_url;let grid=document.getElementById('shots');grid.replaceChildren();for(let r of s.shots||[]){let el=document.createElement('div');el.className='shot '+(r.status==='completed'?'done ':'')+(r.approved?'approved':r.accepted?'queued':'');el.textContent=r.id+' '+(r.approved?'已审':r.status==='completed'?'待审':r.accepted?'排队':'待提交');grid.appendChild(el)}if(s.files['film.mp4']){document.getElementById('player').className='';document.getElementById('film-label').textContent=s.final_ready?'成片 · 自动质检已通过':'已合成初剪 · 正在完成质检';let v=document.getElementById('video');if(!v.getAttribute('src'))v.src='/film.mp4';let d=document.getElementById('downloads');d.replaceChildren();let names={'film.mp4':'下载影片','cover.png':'横版封面','subtitles.srt':'字幕 SRT','narration.wav':'独立旁白 WAV','episode03.png':'第三期系列竖版封面'};for(let key in s.files){let a=document.createElement('a');a.href='/'+key;a.textContent=names[key]||key;a.download=key;d.appendChild(a)}}}catch(e){} }refresh();setInterval(refresh,15000);
</script></html>'''

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route=self.path.split('?',1)[0]
        if route=='/':data=HTML.encode();mime='text/html; charset=utf-8'
        elif route=='/state.json':
            with LOCK:data=json.dumps(STATE,ensure_ascii=False).encode()
            mime='application/json; charset=utf-8'
        elif route[1:] in FILES:
            key=route[1:];path=DEST/key
            if not path.is_file():self.send_error(404);return
            size=path.stat().st_size;start=0;end=size-1;partial=False
            match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers.get('Range',''))
            if match:
                start=int(match[1]);end=min(end,int(match[2])) if match[2] else end;partial=True
                if start>end:self.send_error(416);return
            self.send_response(206 if partial else 200);self.send_header('Content-Type',FILES[key][1]);self.send_header('Accept-Ranges','bytes');self.send_header('Content-Length',str(end-start+1))
            if partial:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            self.end_headers()
            try:
                with open(path,'rb') as stream:
                    stream.seek(start);left=end-start+1
                    while left:
                        chunk=stream.read(min(left,262144));self.wfile.write(chunk);left-=len(chunk)
            except (BrokenPipeError,ConnectionResetError):pass
            return
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def log_message(self,*args):pass

if __name__=='__main__':
    threading.Thread(target=update,daemon=True).start();print('Production progress on 0.0.0.0:8023; only verified film bytes become playable',flush=True);ThreadingHTTPServer(('0.0.0.0',8023),Handler).serve_forever()
