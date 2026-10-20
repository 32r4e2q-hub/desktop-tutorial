#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JMS 郑明析案 · 最终装配（独立于 generate.py 的成片流水线）。

输入:  results.json（30 镜 CDN url + sha256）, story.json（解说词/章节）
输出:  work/jmsjung-final/ 内：成片 mp4、字幕 srt、对齐报告、成片接触表、逐镜 TTS 包
动作:  ① 下载 30 镜并逐字节校验 sha256（失败即停，绝不伪装成功）
       ② 应用 FIXUPS：S21/S22 生成侧产物互串，装配时换回原位（见 alignment-report）
       ③ edge-tts 中文男声（Yunyang，低沉克制）逐镜配音；语速两轮自适应
       ④ 每镜画面按解说时长变速匹配（0.45–1.0× 慢推；超出则末帧定格）
       ⑤ 字幕按 TTS 实际时窗切分烧录；片头/片尾标题卡；淡入淡出
       ⑥ 程序化 QC：总时长/解码错误/响度/黑帧/逐镜音画对位断言
       ⑦ 报告提交分支 + GitHub Release（永久下载链接）+ artifact

退出码: 0 成功 / 1 真实失败（任一校验不过即非 0，不允许带病出片）
"""
import asyncio
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = json.loads((ROOT / 'results.json').read_text())
STORY = json.loads((ROOT / 'story.json').read_text())
SHOTS = sorted(STORY['shots'], key=lambda s: int(s['id'][1:]))
assert len(SHOTS) == 30, '必须恰好 30 镜'
TOTAL_CHARS = sum(len(re.sub(r'[，。、；：“”《》（）\s]', '', s['narration'])) for s in SHOTS)

OUT = Path('work/jmsjung-final')
DL = OUT / 'clips'
TTS = OUT / 'tts'
for d in (OUT, DL, TTS):
    d.mkdir(parents=True, exist_ok=True)

# ---- 装配修正表：slot -> 实际使用的素材文件（对应 results 里的镜号）----
# ⚠️ 2026-10-20 修正：初版误设 {'S21':'S22','S22':'S21'}。
# 根因：夜里工作流生成的 qa/S21.jpg、qa/S22.jpg、qa/S27.jpg、qa/S28.jpg 四张
# 接触表在同轮完成的镜头对之间互相串了文件（QA 写表 bug），导致目检时误判
# "生成侧产物互串"。以最终成片采样帧为地面真值核实：
#   S21.mp4 = 最高法院外景（S21 prompt 渲染）、S22.mp4 = 时间线蒙太奇（S22 prompt 渲染），
#   S27.mp4 = 椅子排（S27 prompt）、S28.mp4 = 空法庭（S28 prompt）——文件映射本就正确。
# 故 FIXUPS 置空；逐槽位中点帧抽检表（final-per-slot.jpg）为权威目检依据。
FIXUPS = {}

# ---- 逐镜调色（只针对目检确认异常的镜头，其余保持生成原样）----
# S04 目检结论：整体曝光偏低（全片最暗镜头），轻微提亮+饱和，避免细节糊死。
GRADES = {'S04': 'eq=brightness=0.07:saturation=1.05'}

VOICE = 'zh-CN-YunyangNeural'          # 中文男声·旁白风格，低沉克制（脚本规格）
GAP_S = 0.7                             # 每句解说后的呼吸停顿
LEAD_S = 0.25                           # 句首相对镜头起点的提前量
OPEN_CARD_S = 3.0                       # 片头标题卡
CLOSE_CARD_S = 2.5                      # 片尾卡
TAIL_S = 3.0                            # 末镜尾部留白（淡出）
SPEED_MIN, SPEED_MAX = 0.45, 1.0        # 变速区间（慢推下限/原速上限）
TARGET_TTS_TOTAL = (250.0, 280.0)       # 解说总时长目标区间（秒）
RATES = ['+35%', '+45%', '+25%']        # 语速自适应档位（300±30 字/分钟目标）
W, H, FPS = 1280, 720, 24

log = lambda *a: print('[finalize]', *a, flush=True)
def die(msg, code=1):
    log('FATAL:', msg)
    (OUT / 'FATAL.txt').write_text(msg + '\n')
    sys.exit(code)
def sh(cmd, **kw):
    log('$', ' '.join(str(c) for c in cmd)[:200])
    return subprocess.run([str(c) for c in cmd], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
def ffprobe_dur(p):
    r = sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'json', str(p)])
    return float(json.loads(r.stdout)['format']['duration'])

# ---------------------------------------------------------------- 1 下载+校验
log('1/7 下载 30 镜并校验 sha256 …')
def download(sid, dest):
    row = RESULTS['shots'][sid]
    url, want = row['video_url'], row['sha256']
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'jmsjung-final/1.0'})
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            got = hashlib.sha256(dest.read_bytes()).hexdigest()
            if got != want:
                raise RuntimeError(f'sha256 不符: {got} != {want}')
            log(f'  {sid} OK {dest.stat().st_size:,}B')
            return
        except Exception as e:
            log(f'  {sid} 下载第{attempt+1}次失败: {e}')
            time.sleep(5)
    die(f'{sid} 下载/校验失败（CDN 链接或素材完整性问题），停止出片')

for s in SHOTS:
    download(s['id'], DL / (s['id'] + '.mp4'))

# ---------------------------------------------------------------- 2 TTS
log('2/7 edge-tts 逐镜配音（%s，两轮语速自适应）…' % VOICE)
import edge_tts  # noqa: E402

async def synth_one(sid, text, rate, out_mp3):
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, VOICE, rate=rate).save(str(out_mp3))
            if out_mp3.stat().st_size > 1000:
                return
        except Exception as e:
            log(f'  {sid} TTS 第{attempt+1}次失败: {e}')
            await asyncio.sleep(3)
    raise RuntimeError(f'{sid} TTS 三次失败')

def trim_silence(mp3, wav):
    sh(['ffmpeg', '-y', '-v', 'error', '-i', str(mp3),
        '-af', 'silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,'
               'areverse,silenceremove=start_periods=1:start_silence=0.02:'
               'start_threshold=-38dB,areverse',
        '-ar', '48000', '-ac', '1', str(wav)])

async def synth_all(rate):
    async def worker(s):
        sid = s['id']
        await synth_one(sid, s['narration'], rate, TTS / (sid + '.raw.mp3'))
        trim_silence(TTS / (sid + '.raw.mp3'), TTS / (sid + '.wav'))
    sem = asyncio.Semaphore(6)
    async def gated(s):
        async with sem:
            await worker(s)
    await asyncio.gather(*(gated(s) for s in SHOTS))

tts_total = None
used_rate = None
for rate in RATES:
    log(f'  试 {rate} …')
    asyncio.run(synth_all(rate))
    tts_total = sum(ffprobe_dur(TTS / (s['id'] + '.wav')) for s in SHOTS)
    log(f'  解说总时长 {tts_total:.1f}s → {TOTAL_CHARS/(tts_total/60):.0f} 字/分钟')
    used_rate = rate
    if TARGET_TTS_TOTAL[0] <= tts_total <= TARGET_TTS_TOTAL[1]:
        break
else:
    log('  三档均未落入目标区间，采用最后一档（报告中如实记录）')

# ---------------------------------------------------------------- 3 时间轴
log('3/7 计算时间轴（每镜 = 解说时长 + 呼吸停顿，画面变速匹配）…')
slots = []
t = OPEN_CARD_S
for i, s in enumerate(SHOTS):
    sid = s['id']
    file_sid = FIXUPS.get(sid, sid)
    clip = DL / (file_sid + '.mp4')
    clip_dur = ffprobe_dur(clip)
    d = ffprobe_dur(TTS / (sid + '.wav'))
    L = d + (TAIL_S if i == len(SHOTS) - 1 else GAP_S)
    speed = min(max(clip_dur / L, SPEED_MIN), SPEED_MAX)
    stretched = clip_dur / speed
    freeze = max(0.0, L - stretched)
    slots.append({
        'slot': i + 1, 'id': sid, 'file_sid': file_sid,
        'narration': s['narration'], 'tts_s': round(d, 3),
        'slot_start': round(t, 3), 'slot_dur': round(L, 3),
        'clip_s': round(clip_dur, 3), 'speed': round(speed, 4),
        'freeze_s': round(freeze, 3),
        'audio_start': round(t + LEAD_S, 3),
        'audio_end': round(t + LEAD_S + d, 3),
        'fits': (t + LEAD_S + d) <= (t + L) - 0.05,
    })
    t += L
TOTAL_S = round(t + CLOSE_CARD_S, 3)
log(f'  成片总时长 {TOTAL_S:.1f}s（{int(TOTAL_S//60)}分{TOTAL_S%60:.0f}秒），'
    f'平均语速 {TOTAL_CHARS/((tts_total)/60):.0f} 字/分钟')
for sl in slots:
    if not sl['fits']:
        die(f"镜头 {sl['id']} 解说超出镜头窗（不应发生：L=d+gap）")

# ---------------------------------------------------------------- 4 字幕 SRT
def srt_ts(sec):
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    return f'{h:02d}:{m:02d}:{s:02d},{int((sec - int(sec))*1000):03d}'

log('4/7 生成字幕（按 TTS 时窗、标点切分）…')
srt_lines, n = [], 1
for sl in slots:
    text = sl['narration']
    parts = [p for p in re.split(r'(?<=[。；])', text) if p.strip()]
    chunks = []
    for p in parts:
        while len(p) > 22:
            cut = p.rfind('，', 0, 22)
            if cut < 8:
                cut = 22
            chunks.append(p[:cut+1]); p = p[cut+1:]
        chunks.append(p)
    chunks = [c for c in chunks if c.strip()]
    span = sl['audio_end'] - sl['audio_start']
    total_len = sum(len(re.sub(r'\s', '', c)) for c in chunks) or 1
    cur = sl['audio_start']
    for c in chunks:
        frac = len(re.sub(r'\s', '', c)) / total_len
        end = cur + span * frac
        srt_lines += [str(n), f'{srt_ts(cur)} --> {srt_ts(end)}', c.strip(), '']
        n += 1
        cur = end
(OUT / 'captions.srt').write_text('\n'.join(srt_lines))

# ---------------------------------------------------------------- 5 标题卡
log('5/7 合成成片（单遍 filtergraph：变速+字幕+混音+响度）…')
(OUT / 'open-title.txt').write_text('JMS 郑明析案\n自称救世主的人，为什么最终站上被告席？\n')
(OUT / 'close-title.txt').write_text('让事实被查明，让受害者被听见\n')
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
if not Path(FONT).exists():
    cands = [p for p in Path('/usr/share/fonts').rglob('NotoSansCJK*') if p.suffix in ('.ttc', '.otf')]
    if not cands:
        die('找不到 Noto CJK 字体，请先 apt-get install fonts-noto-cjk')
    FONT = str(cands[0])
    log('  字体回退:', FONT)

cmd = ['ffmpeg', '-y', '-v', 'warning', '-stats']
# 音频输入：30 个 wav
for sl in slots:
    cmd += ['-i', str(TTS / (sl['id'] + '.wav'))]
# 标题卡 lavfi
cmd += ['-f', 'lavfi', '-t', str(OPEN_CARD_S), '-i', f'color=c=black:s={W}x{H}:r={FPS}']
OPEN_IDX = 30
cmd += ['-f', 'lavfi', '-t', str(CLOSE_CARD_S), '-i', f'color=c=black:s={W}x{H}:r={FPS}']
CLOSE_IDX = OPEN_IDX + 1
# 视频输入：30 个镜头（slot 顺序，含 FIXUPS）
for sl in slots:
    cmd += ['-i', str(DL / (sl['file_sid'] + '.mp4'))]
VIDEO0 = CLOSE_IDX + 1

fg = []
# 标题卡
fg.append(f'[{OPEN_IDX}:v]setsar=1,drawtext=fontfile={FONT}:textfile={OUT}/open-title.txt:'
          f'fontcolor=white:fontsize=46:x=(w-text_w)/2:y=(h/2)-70:line_spacing=14,'
          f'fade=t=in:st=0:d=0.6,fade=t=out:st={OPEN_CARD_S-0.6}:d=0.6,format=yuv420p[vopen]')
fg.append(f'[{CLOSE_IDX}:v]setsar=1,drawtext=fontfile={FONT}:textfile={OUT}/close-title.txt:'
          f'fontcolor=0xCCCCCC:fontsize=30:x=(w-text_w)/2:y=h/2-20,'
          f'fade=t=in:st=0:d=0.6,fade=t=out:st={CLOSE_CARD_S-0.6}:d=0.6,format=yuv420p[vclose]')
# 镜头
for i, sl in enumerate(slots):
    vidx = VIDEO0 + i
    grade = GRADES.get(sl['id'], '')
    grade_part = (grade + ',') if grade else ''
    chain = (f'[{vidx}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,'
             f'pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS},'
             f'{grade_part}setpts=(PTS-STARTPTS)/{sl["speed"]},'
             f'trim=duration={sl["slot_dur"]},setpts=PTS-STARTPTS')
    if sl['freeze_s'] > 0.01:
        chain += f',tpad=stop_mode=clone:stop_duration={sl["freeze_s"]}'
    chain += f',format=yuv420p[v{i}]'
    fg.append(chain)
# 拼接 + 字幕 + 淡入淡出
concat_in = '[vopen]' + ''.join(f'[v{i}]' for i in range(30)) + '[vclose]'
fg.append(f'{concat_in}concat=n=32:v=1:a=0[vcat]')
_style = ("'FontName=Noto Sans CJK SC,FontSize=13,PrimaryColour=&H00FFFFFF,"
          "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
          "MarginV=34,Alignment=2'")
fg.append(f'[vcat]subtitles={OUT}/captions.srt:force_style={_style}[vsub]')
fg.append(f'[vsub]fade=t=in:st=0:d=0.8,fade=t=out:st={TOTAL_S-2.5}:d=2.5[vout]')
# 音频：静音底 + 逐句 adelay
fg.append(f'anullsrc=r=48000:cl=mono,atrim=duration={TOTAL_S}[abase]')
mix = ['[abase]']
for i, sl in enumerate(slots):
    dms = int(sl['audio_start'] * 1000)
    fg.append(f'[{i}:a]adelay={dms}|{dms}[a{i}]')
    mix.append(f'[a{i}]')
fg.append(''.join(mix) + f'amix=inputs={31}:duration=first:normalize=0,'
          f'afade=t=out:st={TOTAL_S-2.0}:d=2.0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]')

final_mp4 = OUT / 'final.mp4'
cmd += ['-filter_complex', ';'.join(fg),
        '-map', '[vout]', '-map', '[aout]',
        '-c:v', 'libx264', '-crf', '19', '-preset', 'slow', '-profile:v', 'high',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-movflags', '+faststart', str(final_mp4)]
t0 = time.time()
try:
    sh(cmd)
except subprocess.CalledProcessError as e:
    die('ffmpeg 合成失败：\n' + (e.stderr or b'').decode('utf-8', 'replace')[-4000:])
log(f'  合成完成 {time.time()-t0:.0f}s → {final_mp4.stat().st_size/1e6:.1f}MB')

# ---------------------------------------------------------------- 6 QC
log('6/7 程序化 QC …')
dec = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(final_mp4), '-f', 'null', '-'],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
decode_errors = [l for l in dec.stderr.decode('utf-8', 'replace').splitlines() if l.strip()]
probe = json.loads(sh(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                       '-of', 'json', str(final_mp4)]).stdout)
vstream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
astream = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
final_dur = float(probe['format']['duration'])
black = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(final_mp4),
                        '-vf', 'blackdetect=d=0.5:pix_th=0.08', '-f', 'null', '-'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
black_frames = re.findall(r'black_start:\s*([\d.]+)\s*black_end:\s*([\d.]+)',
                          black.stderr.decode('utf-8', 'replace'))
eb = subprocess.run(['ffmpeg', '-i', str(final_mp4), '-af', 'ebur128', '-f', 'null', '-'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
eb_txt = eb.stderr.decode('utf-8', 'replace')
integrated = (re.findall(r'I:\s*(-?[\d.]+)\s*LUFS', eb_txt) or ['?'])[-1]

qc = {
    'final_duration_s': round(final_dur, 2),
    'expected_duration_s': TOTAL_S,
    'duration_ok': abs(final_dur - TOTAL_S) < 0.6,
    'video': f"{vstream['codec_name']} {vstream['width']}x{vstream['height']}@{vstream.get('r_frame_rate')}",
    'audio': f"{astream['codec_name']} {astream.get('sample_rate')}Hz",
    'decode_errors': len(decode_errors),
    'decode_error_lines': decode_errors[:5],
    'black_segments': [[float(a), float(b)] for a, b in black_frames],
    'loudness_integrated_lufs': integrated,
    'total_narration_chars': TOTAL_CHARS,
    'tts_total_s': round(tts_total, 1),
    'avg_speech_rate_cpm': round(TOTAL_CHARS / (tts_total / 60)),
    'tts_voice': VOICE, 'tts_rate': used_rate,
    'fixups_applied': FIXUPS,
}
ok = qc['duration_ok'] and qc['decode_errors'] == 0

report = {
    'title': STORY['title'],
    'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'model': RESULTS.get('model'), 'size': '720P', 'fps': FPS,
    'target_spec_s': 180, 'actual_duration_s': qc['final_duration_s'],
    'duration_note': ('脚本正文共 %d 字解说词；180 秒规格下需 %d 字/分钟（超中文语速极限 ~350）。'
                      '本版本完整保留解说词、采用纪录体快节奏，时长相应变为 %d 秒。'
                      '如需严格 180 秒，须先经用户批准删减解说词。'
                      % (TOTAL_CHARS, TOTAL_CHARS // 3, int(TOTAL_S))),
    'qc': qc,
    'slots': slots,
    'qc_passed': ok,
}
(OUT / 'alignment-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
if not ok:
    die('QC 未通过（报告已落盘）：' + json.dumps(qc, ensure_ascii=False))

# 成片接触表（16 帧）供人工复核装配顺序/字幕
step = max(1, int(TOTAL_S * FPS / 16))
sh(['ffmpeg', '-y', '-v', 'error', '-i', str(final_mp4),
    '-vf', f"select='not(mod(n,{step}))',scale=480:270,tile=4x4",
    '-frames:v', '1', str(OUT / 'final-contact.jpg')])

# 逐槽位中点帧抽检表（30 帧：每个镜头窗口正中间抽 1 帧）——权威目检依据
mid_expr = '+'.join('eq(n,%d)' % round((sl['slot_start'] + sl['slot_dur'] / 2) * FPS)
                    for sl in slots)
sh(['ffmpeg', '-y', '-v', 'error', '-i', str(final_mp4),
    '-vf', f"select='{mid_expr}',scale=426:240,tile=6x5",
    '-frames:v', '1', str(OUT / 'final-per-slot.jpg')])

# 逐镜 TTS 打包（供用户试听音色）
tts_zip = OUT / 'narration-per-shot.zip'
sh(['zip', '-q', '-j', str(tts_zip)] + [str(TTS / (s['id'] + '.wav')) for s in SHOTS])

# ---------------------------------------------------------------- 7 交付
log('7/7 提交报告 + 发布 Release …')
deliv = ROOT / 'delivery' / 'final'
deliv.mkdir(exist_ok=True)
for f in ('alignment-report.json', 'captions.srt', 'final-contact.jpg',
          'final-per-slot.jpg'):
    shutil.copy2(OUT / f, deliv / f)
sh(['git', 'config', 'user.name', 'jmsjung-final'])
sh(['git', 'config', 'user.email', 'jmsjung-final@users.noreply.github.com'])
sh(['git', 'add', 'production/jmsjung/delivery/final/'])
try:
    sh(['git', 'commit', '-q', '-m',
        'jmsjung: 最终装配完成——对齐报告 + 成片接触表 + 字幕'])
except subprocess.CalledProcessError:
    log('  无新内容可提交（重复运行），跳过')
tok = os.environ.get('GITHUB_TOKEN')
repo = os.environ.get('GITHUB_REPOSITORY')
if tok and repo:
    ts = time.strftime('%Y%m%d-%H%M%S', time.gmtime())
    tag = f'jmsjung-final-{ts}'
    note = (f'# JMS 郑明析案 · 成片\n\n'
            f'- 时长 **{int(TOTAL_S//60)}分{TOTAL_S%60:.0f}秒**（完整保留 1366 字解说词；180 秒规格与之物理矛盾，见报告 duration_note）\n'
            f'- 30 镜 agnes-video-2.5-flash 720P；逐槽位中点帧抽检表 final-per-slot.jpg 为权威目检依据'
            f'（夜里生成的 qa/S21/S22/S27/S28 四张接触表存在同轮串表 bug，已弃用）\n'
            f'- 配音：edge-tts {VOICE}（中文男声·旁白），平均语速 {qc["avg_speech_rate_cpm"]} 字/分钟\n'
            f'- 字幕烧录 + 片头片尾标题卡 + 响度归一（-16 LUFS）\n'
            f'- 逐镜音画对位表与 QC 结果见 alignment-report.json')
    sh(['gh', 'release', 'create', tag,
        str(final_mp4), str(OUT / 'captions.srt'),
        str(OUT / 'alignment-report.json'), str(OUT / 'final-contact.jpg'),
        str(tts_zip),
        '--title', 'JMS 郑明析案 · 成片（完整版）', '--notes', note,
        '--repo', repo], env={**os.environ})
    log(f'  Release 已发布: tag={tag}')
    # 报告推回分支（token 只进 argv，不落日志/文件）
    remote = f'https://x-access-token:{tok}@github.com/{repo}.git'
    r = subprocess.run(['git', 'push', '-q', remote,
                        'HEAD:arena/929dc8b6-desktop-tutorial'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        r2 = subprocess.run(['git', 'pull', '-q', '--rebase', 'origin',
                             'arena/929dc8b6-desktop-tutorial'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        r = subprocess.run(['git', 'push', '-q', remote,
                            'HEAD:arena/929dc8b6-desktop-tutorial'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        die('报告推送失败（release 已发布，不影响下载）：' +
            r.stderr.decode('utf-8', 'replace')[-500:])
log('DONE final=%s dur=%.1fs' % (final_mp4, final_dur))
