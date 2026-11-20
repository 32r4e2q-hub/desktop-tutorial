#!/usr/bin/env python3
"""Submit all 30 distinct Baiyin shots (S03 reuses the current canary task).

Paid operations are checkpointed to this branch before and after each POST. A
network-ambiguous submission is never automatically retried. Each run resumes
saved task IDs; a 429 is retried at most 10 times. No automatic visual signoff.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'production'))
sys.path.insert(0, str(ROOT/'production'/'shanghai_freezer_case'))
import agnes_video as agnes
from throttle import RequestGate

BRANCH = 'arena/aa4972d2-desktop-tutorial'
MODEL = 'agnes-video-2.5-flash'
RESULT = HERE/'results.json'
SOURCES = ROOT/'work'/'baiyin_case'/'sources'
QA = HERE/'qa'/'shots'
# Reference IDs and deliberately motion-specific, text-free video actions.
BEATS = [
 ('hook','漆黑空间中冷白光束缓慢扩散又收束，空气尘粒轻轻漂移，极缓推近。'),
 ('lab','匿名透明试管微距，冷光中液面轻微起伏，镜头缓慢向前推近；没有针头与采样过程。'),
 ('city_clean','蓝调时刻西北工业城市远景，镜头缓缓下降，薄雾自然漂动。'),
 ('city_clean','老工业小城的冷色街景，镜头沿着无字建筑外墙缓缓横移。'),
 ('room','空无一人的旧式房间，窗帘被微风轻轻吹动，镜头缓慢横移。'),
 ('records','近距离拍摄一叠没有任何字迹的旧纸张，轻微翻页，镜头缓缓横移。'),
 ('city_clean','夜幕下城市轮廓，镜头缓慢横移，天空光线微微变化；保持中央开阔便于后期叠图。'),
 ('coats','无人的衣柜里红衣轻轻摆动，侧逆光，摄影机极缓推近。'),
 ('room','空室内，窗帘在夜风中自然移动，窗户逐渐合拢，镜头保持克制。'),
 ('archive','阴暗档案室的空白卷宗，灯光中尘埃漂浮，摄影机缓慢推轨。'),
 ('records','全为空白的案卷与纸张在桌面上，手部不出现，灯光闪动很轻，镜头缓推。'),
 ('evidence_clean','戴手套的双手小幅翻动没有字的指纹卡，镜头缓缓横移，手指形态自然。'),
 ('shop_clean','暖光匿名小卖部，镜头从入口平稳进入，商品均无标记，不出现人物。'),
 ('shop_clean','匿名小卖部柜台，窗外日光轻微移动，镜头缓慢横移。'),
 ('shop_clean','从店内向门口缓缓移动，窗外空街日光与暖色室内形成对比，没有人物。'),
 ('shop_clean','暖光柜台与空货架，摄影机缓慢后拉，右侧留给后期分屏，不出现人物。'),
 ('archive','无字档案堆叠、微尘下落，镜头缓慢横移，表现时间流逝。'),
 ('dna','冷青光下玻璃质感DNA双螺旋缓慢旋转，镜头平稳推进。'),
 ('dna','抽象冷青色父系遗传概念，以发光线条缓慢分叉，画面不出现任何文字数字。'),
 ('lab','一排无标记透明样本试管与柔和冷光，镜头缓缓横移，不出现屏幕字迹。'),
 ('lab','匿名戴手套的手平稳移动一支透明无标记试管，动作自然，不展示采血。'),
 ('lab','极简实验器材特写，冷色光线轻微变化，右侧保持空白供后期叠加比对图。'),
 ('dna','冷色抽象分支结构逐渐收束，缓慢横向移动，空白背景供后期标注。'),
 ('shop_clean','小卖部无字门口及室内，摄影机向门边缓慢推进，空无一人。'),
 ('cuffs','静置的手铐微距，冷光一闪，镜头缓慢推进；无人物无接触无暴力。'),
 ('room','安静空房间里的空桌与椅子，冷光透过窗户，缓慢推近，没有人物。'),
 ('court','空法庭中心对称的庄严远景，镜头缓缓推进，无任何文字标记。'),
 ('records','桌上完全空白文件与台灯，镜头平稳横移，画面右侧保留空间后期加日期。'),
 ('hook','近乎纯黑的背景与细微冷白光束慢慢收束，少量尘埃漂浮，不出现字。'),
 ('lab','匿名试管及冷光微距，镜头慢慢后拉，场景逐渐暗下，没有文字。'),
]


def digest(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.run(['git',*args],cwd=ROOT,check=True,capture_output=True,text=True).stdout

def checkpoint(doc, message, files=()):
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    paths=[str(RESULT.relative_to(ROOT))]+[str(p.relative_to(ROOT)) for p in files]
    git('add','--',*paths)
    if subprocess.run(['git','diff','--cached','--quiet','--',*paths],cwd=ROOT).returncode:
        git('commit','-m','baiyin batch: '+message,'--',*paths)
        # The canary and this job share a concurrency group, but allow independent
        # local edits to be rebased safely, never repeat the provider POST here.
        for attempt in range(3):
            try:
                git('push','origin',f'HEAD:refs/heads/{BRANCH}'); break
            except subprocess.CalledProcessError:
                if attempt == 2: raise
                git('pull','--rebase','origin',BRANCH)
    print('CHECKPOINT', message, flush=True)


def main():
    if os.getenv('GITHUB_ACTIONS') != 'true' or os.getenv('GITHUB_REF') != f'refs/heads/{BRANCH}':
        raise SystemExit('only allowed in current branch Actions')
    key=os.getenv('AGNES_API_KEY','').strip()
    if not key: raise SystemExit('AGNES_API_KEY unavailable')
    base=(os.getenv('AGNES_BASE_URL') or agnes.DEFAULT_BASE_URL).rstrip('/')
    story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    shots=story['shots']
    if len(shots)!=30 or sum(x['duration'] for x in shots)!=180 or len(BEATS)!=30:
        raise SystemExit('invalid 30-shot timeline')
    git('config','user.name','github-actions[bot]')
    git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    doc=json.loads(RESULT.read_text()) if RESULT.is_file() else {
        'model': MODEL, 'reference_revision': os.environ['GITHUB_SHA'], 'shots': {},
        'review': 'visual_review_pending', 'policy': 'reference 720P, 30 shots, no auto-approval'}
    revision=doc['reference_revision']
    if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision):
        raise SystemExit('reference revision is not an immutable commit')
    if not doc['shots'].get('S03'):
        canary=HERE/'qa'/'S03_canary_v2.json'
        if not canary.exists(): raise SystemExit('S03 v2 task is not checkpointed; do not duplicate it')
        row=json.loads(canary.read_text())
        if not row.get('video_id'): raise SystemExit('S03 v2 task ID absent; reconcile first')
        doc['shots']['S03']={**row,'source':'S03_canary_v2','reused_existing_asset':True}
        checkpoint(doc,'preserve S03 task')
    gate=RequestGate(minimum_interval=12.1)
    QA.mkdir(parents=True,exist_ok=True); SOURCES.mkdir(parents=True,exist_ok=True)
    for shot,(reference,beat) in zip(shots,BEATS):
        sid=shot['id']
        if sid=='S03': continue
        prompt=('电影级纪实情景演绎，冷峻克制，真实连续运动画面，16:9横版，镜头稳定。'
                + beat + ' 不得出现可识别当事人、儿童、性侵、暴力过程、伤口、血腥、遗体。'
                '禁止生成任何文字、汉字、数字、招牌、标志、字幕、标签、水印。'
                '所有时间、数据、字幕、地图和图表都由后期添加，禁止画面自绘。')
        payload={'model':MODEL,'prompt':prompt,'seconds':str(max(4,min(12,int(shot['duration'])))),
                 'size':'720P','aspect_ratio':'16:9','mode':'reference','n':1,
                 'seed':19880000+int(sid[1:]),
                 'images':[f'https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/{revision}/production/baiyin_case/reference/{reference}.png']}
        wanted=digest(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode())
        row=doc['shots'].get(sid)
        if row:
            if row.get('request_hash')!=wanted: raise SystemExit(f'{sid} request hash changed; reconcile first')
            if row.get('video_id'): continue
            raise SystemExit(f'{sid} previous submission unresolved: {row.get("status")}')
        row={'id':sid,'status':'submitting','request_hash':wanted,'request':payload,
             'reused_existing_asset':False,'visual_review':'pending'}
        doc['shots'][sid]=row
        checkpoint(doc,sid+' submitting')
        for attempt in range(1,11):
            gate.acquire()
            try:
                reply=agnes.http_json('POST',base+'/v1/videos',key,payload,timeout=120)
                code,body,text=reply
            except Exception as exc:
                row.update(status='create_unknown',error=str(exc).replace(key,'[redacted]')[:400])
                checkpoint(doc,sid+' submission uncertain'); raise SystemExit('No automatic retry after uncertain POST')
            if code==429:
                row.update(status='rate_limited',attempts=attempt)
                checkpoint(doc,sid+' rate limited')
                if attempt==10: raise SystemExit('10 capacity rejections; stop batch, no infinite retry')
                gate.defer(max(60.0,float(getattr(reply,'retry_after',None) or 0)))
                continue
            if not (200<=code<300 and isinstance(body,dict)):
                detail=agnes.describe_error(body,text,code).replace(key,'[redacted]')[:350]
                row.update(status='create_unknown' if code>=500 else 'rejected',http_status=code,error=detail)
                checkpoint(doc,sid+' not accepted')
                raise SystemExit(f'{sid}: HTTP {code}; stopping without a duplicate POST')
            video_id=body.get('video_id') or body.get('id') or body.get('task_id')
            if not video_id:
                row.update(status='create_unknown',error='No ID in response');checkpoint(doc,sid+' missing ID')
                raise SystemExit('reconcile before retry')
            row.update(status='queued',video_id=str(video_id),task_id=str(body.get('task_id') or body.get('id') or video_id),attempts=attempt)
            checkpoint(doc,sid+' accepted')
            break
    doc['phase']='all_tasks_submitted';checkpoint(doc,'all tasks submitted')
    failures=[]
    for shot in shots:
        sid=shot['id']; row=doc['shots'][sid]
        if row.get('status')=='completed' and row.get('sha256') and row.get('video_url'):
            print(sid,'already complete, no re-create',flush=True);continue
        try:
            final,url=agnes.poll_task(base,key,MODEL,row['video_id'],row.get('task_id'),interval=45,timeout=1800,
                                      max_failures=8,before_request=gate.acquire,rate_limit_callback=gate.defer)
            out=SOURCES/f'{sid}.mp4'; size=agnes.download(url,out,retries=3,retry_delay=5)
            probe=json.loads(subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(out)],capture_output=True,text=True,check=True).stdout)
            streams=[x for x in probe['streams'] if x['codec_type']=='video']
            if not streams or float(probe['format']['duration']) < min(4,shot['duration']):
                raise RuntimeError('Missing video or too short')
            sheet=QA/f'{sid}.jpg'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(out),'-vf','fps=1/2,scale=320:-1,tile=5x1','-frames:v','1',str(sheet)],check=True)
            row.update(status='completed',video_url=url,sha256=digest(out.read_bytes()),bytes=size,
                       duration=float(probe['format']['duration']),width=streams[0].get('width'),height=streams[0].get('height'),
                       visual_review='pending',provider_status=final.get('status'))
            checkpoint(doc,sid+' completed; review pending',files=(sheet,))
        except Exception as exc:
            row.update(status='poll_or_download_failed',error=str(exc).replace(key,'[redacted]')[:350])
            checkpoint(doc,sid+' poll/download failed')
            failures.append(sid)
    doc['phase']='review_pending' if not failures else 'incomplete';checkpoint(doc,'batch status')
    if failures: raise SystemExit('Needs recovery: '+','.join(failures))
    print('All tasks complete. Human visual and full-motion review still required.')

if __name__=='__main__': main()
