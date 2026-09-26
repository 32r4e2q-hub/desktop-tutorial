"""逐帧畸变体检：在 Actions runner 上对每一条 Agnes 素材的**全部帧**（7.04 s × 24 fps = 169 帧）跑一遍。

沙箱连不上 Agnes 的 CDN，素材只能在 runner 上看；所以这里把「逐帧看」变成数字 + 图，随 qa/ 一起
commit 回分支，沙箱里拿到后复审：

  qa/Sxx.jpg        原有的 4×4 接触表（2 fps，工具链其它地方引用它，保持不变）
  qa/Sxx-dense.jpg  每 6 帧一张（0.25 s 一张，共 29 张，352×198）+ 底部逐帧曲线图，红竖线 = 自动标记帧
  qa/Sxx-flags.jpg  每个自动标记事件的「前一帧 | 这一帧」对照（480×270）；没有标记时是一张说明图
  qa/Sxx.json       ffprobe 信息 + frame_qa：逐帧指标数组、事件列表、人脸抽检、auto_verdict

逐帧指标（全部 320×180 灰度 / 彩色直方图上算，只看相对变化）：
  mad        相邻帧平均绝对差（0–255）——跳切、闪烁、冻结
  tv         相邻帧 8×8×8 彩色直方图全变差（0–1）——整屏换场（Agnes 偶尔在 7 秒里硬切一次）
  luma       平均亮度——闪烁（亮度忽高忽低）、黑帧
  flow       Farneback 光流平均位移（像素）——机位突然跳
  morph      光流补偿残差：把后一帧按光流拉回前一帧后，16×16 块里残差的最大值。
             正常运动能被光流解释、残差小；物体「融化 / 变形 / 凭空长出来」解释不了，残差尖峰。
  sharp      拉普拉斯方差——突然糊掉
  oscillation mad / flow 在 0.5 s 滑窗里去掉线性趋势后，按 (-1)^k 加权求和 = 2 帧周期（奈奎斯特频率）的
             振幅（取中位数，单帧尖峰不算）。正常运镜≈0；画面「一帧一颤」会把它顶起来（S20 首版开门后 0.885）。
人脸：OpenCV Haar 正脸检测，640×360 每 3 帧抽一帧。本片镜头都是背影 / 剪影 / 手部 / 远景，
《蒙娜丽莎》正面永远不画清楚——检测到正脸不等于坏，但必须人工看一眼（露脸最容易畸变）。

阈值是保守的「值得人看」而不是「判死刑」：auto_verdict = clean / review，最终结论写在
qa-review.md（人工看 dense 图 + flags 图之后）。依赖：numpy、pillow、opencv-python-headless<5
（OpenCV 5 删掉了 Haar CascadeClassifier）。任何一步出错都不影响生成，只在 JSON 里记 frame_qa_error。
"""
import json
import subprocess
from pathlib import Path

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - runner 上一定装了；本地没装时退化成纯 numpy 指标
    cv2 = None

VERSION = 2   # v2：加 oscillation（2 帧周期的颤帧 / 抖动）
W, H = 320, 180           # 指标分辨率
FW, FH = 640, 360         # 解码分辨率（人脸、图块都从这里缩）
TILE = (352, 198)
DENSE_STEP = 6
DENSE_COLS = 6


def decode(path, w=FW, h=FH):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-threads', '2', '-i', str(path), '-map', '0:v:0',
                          '-vf', f'scale={w}:{h}:flags=area', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    if n < 2:
        raise RuntimeError(f'only {n} frames decoded')
    return np.frombuffer(raw, np.uint8)[:n * w * h * 3].reshape(n, h, w, 3)


def resize(img, size):
    if cv2 is not None:
        return cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    from PIL import Image
    return np.asarray(Image.fromarray(img).resize(size, Image.BILINEAR))


def robust_z(values):
    v = np.asarray(values, float)
    med = np.median(v)
    mad = np.median(np.abs(v - med)) * 1.4826
    return (v - med) / max(mad, 1e-6)


def metrics(frames):
    small = np.stack([resize(f, (W, H)) for f in frames])
    gray = (small[..., 0] * 0.299 + small[..., 1] * 0.587 + small[..., 2] * 0.114).astype(np.float32)
    n = len(gray)
    luma = gray.mean((1, 2))
    mad = np.r_[0.0, np.abs(np.diff(gray, axis=0)).mean((1, 2))]
    q = (small // 32).astype(np.int32)
    idx = q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]
    hists = np.stack([np.bincount(i.ravel(), minlength=512) for i in idx]).astype(np.float64)
    hists /= hists.sum(1, keepdims=True)
    tv = np.r_[0.0, 0.5 * np.abs(np.diff(hists, axis=0)).sum(1)]
    flow = np.zeros(n); morph = np.zeros(n); sharp = np.zeros(n)
    g8 = np.clip(gray, 0, 255).astype(np.uint8)
    if cv2 is not None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        for t in range(n):
            sharp[t] = cv2.Laplacian(g8[t], cv2.CV_32F).var()
            if t == 0:
                continue
            f = cv2.calcOpticalFlowFarneback(g8[t - 1], g8[t], None, 0.5, 3, 15, 3, 5, 1.2, 0)
            flow[t] = float(np.hypot(f[..., 0], f[..., 1]).mean())
            warped = cv2.remap(g8[t], xx + f[..., 0], yy + f[..., 1], cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE)
            res = np.abs(warped.astype(np.float32) - g8[t - 1].astype(np.float32))[6:-6, 6:-6]
            hh, ww = res.shape[0] // 16 * 16, res.shape[1] // 16 * 16
            morph[t] = float(res[:hh, :ww].reshape(hh // 16, 16, ww // 16, 16).mean((1, 3)).max())
    else:
        lap = np.abs(4 * gray[:, 1:-1, 1:-1] - gray[:, :-2, 1:-1] - gray[:, 2:, 1:-1]
                     - gray[:, 1:-1, :-2] - gray[:, 1:-1, 2:])
        sharp = lap.var((1, 2))
        morph = mad.copy()
    return {'mad': mad, 'tv': tv, 'luma': luma, 'flow': flow, 'morph': morph, 'sharp': sharp}, hists


def group_runs(frames, gap=1):
    runs = []
    for f in sorted(frames):
        if runs and f - runs[-1][1] <= gap:
            runs[-1][1] = f
        else:
            runs.append([f, f])
    return runs


OSC_W = 12          # 0.5 s 滑窗
OSC_MAD = 0.15      # 前 19 条素材里正常镜头最高 0.14（S02 单帧起步）；S20 首版颤帧最高 0.885、连续 34 帧
OSC_FLOW = 0.015
OSC_MIN_FRAMES = 6


def oscillation(series, w=OSC_W):
    """每一帧附近 w 帧滑窗里，2 帧周期（奈奎斯特）锯齿的振幅。先去掉线性趋势（匀加速不算），再取
    「相邻差 × (-1)^k」的**中位数**：真正的一帧一颤每一对相邻帧都在交替、中位数就是振幅；单独一帧的
    尖峰（突然起步、一帧跳变）只影响 2 个差值，中位数≈0——那些由 jump / flash / freeze 负责。"""
    x = np.asarray(series, float)
    out = np.zeros(len(x))
    alt = np.array([(-1) ** k for k in range(w - 1)], float)
    t = np.arange(w)
    for i in range(1, len(x) - w + 1):
        seg = x[i:i + w]
        r = seg - np.polyval(np.polyfit(t, seg, 1), t)
        out[i + w // 2] = abs(float(np.median((r[:-1] - r[1:]) * alt))) / 2
    return out


def find_events(m, fps, hists=None):
    n = len(m['mad'])
    mad, tv, luma, flow, morph, sharp = (m[k] for k in ('mad', 'tv', 'luma', 'flow', 'morph', 'sharp'))
    body = slice(1, n)
    med_mad = float(np.median(mad[body])); med_flow = float(np.median(flow[body]))
    med_sharp = float(np.median(sharp)); med_morph = float(np.median(morph[body]))
    events = []

    def add(kind, a, b, peak, severity, detail):
        events.append({'type': kind, 'start_frame': int(a), 'end_frame': int(b), 'peak_frame': int(peak),
                       'time': round(peak / fps, 3), 'severity': severity, **detail})

    cand = [t for t in range(1, n) if tv[t] > 0.25 and mad[t] > max(10.0, 4 * med_mad)]
    cut, flash, skip_until = [], [], -1
    for t in cand:
        if t <= skip_until:
            continue
        back = None                     # 1–4 帧内画面回到跳变前的样子 = 闪一下（闪白/闪黑），不是换场
        if hists is not None:
            for k in range(1, 5):
                if t + k < n and 0.5 * np.abs(hists[t + k] - hists[t - 1]).sum() < 0.12:
                    back = t + k
                    break
        if back:
            flash.append((t, back - 1)); skip_until = back
        else:
            cut.append(t)
    for a, b in group_runs(cut):
        p = max(range(a, b + 1), key=lambda t: tv[t])
        add('hard_cut', a, b, p, 'high', {'tv': round(float(tv[p]), 3), 'mad': round(float(mad[p]), 2)})
    for a, b in flash:
        add('flash', a, b, a, 'high', {'frames': int(b - a + 1), 'tv': round(float(tv[a]), 3)})
    in_flash = {t for a, b in flash for t in range(a, b + 2)}
    cut = cut + sorted(in_flash)
    jump = [t for t in range(1, n) if t not in cut and flow[t] > max(4.0, 5 * med_flow)
            and mad[t] > max(4.0, 2.5 * med_mad)]
    for a, b in group_runs(jump):
        p = max(range(a, b + 1), key=lambda t: flow[t])
        add('jump', a, b, p, 'high', {'flow_px': round(float(flow[p]), 2), 'median_flow_px': round(med_flow, 2)})
    local = np.array([np.median(luma[max(0, t - 3):t + 4]) for t in range(n)])
    flick = [t for t in range(n) if abs(luma[t] - local[t]) > 5.0 and t not in in_flash]
    for a, b in group_runs(flick):
        p = max(range(a, b + 1), key=lambda t: abs(luma[t] - local[t]))
        add('flicker', a, b, p, 'medium', {'luma_jump': round(float(luma[p] - local[p]), 2)})
    # 冻结：相邻帧差低于本片中位数的 30%（夹在 0.08–0.6）。重编码后的重复帧 mad 0.0–0.3（x264 刚冻住的
    # 几帧还在收敛），正常运动 0.8–4；min_mad≈0 是真重复帧，0.3 上下多半是刻意的慢速定格（提示词末尾的 HOLD）。
    still_thr = min(0.6, max(0.08, 0.3 * med_mad))
    still = [t for t in range(1, n) if mad[t] < still_thr]
    for a, b in group_runs(still, gap=1):
        if b - a + 1 >= 4:
            seg = mad[a:b + 1]
            # 真正的「卡帧」：画面停住、恢复时一下子跳过去（恢复那一帧的帧差 > 3× 中位数）；
            # Agnes 的运镜缓入 / 缓出是平滑起步或停在最后构图上——记为 hold（info），剪辑时由
            # review_clips.py 把时间窗挪到起动帧之后即可，不算素材缺陷。
            resume = float(mad[b + 1]) if b + 1 < n else 0.0
            jolt = b + 1 < n and resume > max(2.5, 3 * med_mad)
            detail = {'frames': int(b - a + 2), 'seconds': round((b - a + 2) / fps, 2),
                      'min_mad': round(float(seg.min()), 3), 'mean_mad': round(float(seg.mean()), 3),
                      'resume_mad': round(resume, 2), 'threshold': round(float(still_thr), 3)}
            if jolt:
                add('freeze', a - 1, b, a, 'medium' if a <= 2 else 'high', detail)
            else:
                add('hold', a - 1, b, a, 'info', detail)
    black = [t for t in range(n) if luma[t] < 12]
    for a, b in group_runs(black):
        add('black', a, b, a, 'high', {'luma': round(float(luma[a]), 1)})
    if cv2 is not None:
        z = robust_z(morph[body])
        spikes = [t for t in range(1, n) if t not in cut and z[t - 1] > 6 and morph[t] > max(25.0, 2.5 * med_morph)]
        for a, b in group_runs(spikes):
            p = max(range(a, b + 1), key=lambda t: morph[t])
            add('morph_spike', a, b, p, 'medium', {'morph': round(float(morph[p]), 1),
                                                  'median_morph': round(med_morph, 1)})
    blur = [t for t in range(n) if sharp[t] < 0.45 * med_sharp]
    for a, b in group_runs(blur):
        if b - a + 1 >= 3:
            p = min(range(a, b + 1), key=lambda t: sharp[t])
            add('blur_dip', a, b, p, 'medium', {'sharp_ratio': round(float(sharp[p] / max(med_sharp, 1e-6)), 2)})
    # 颤帧：相邻帧差以 2 帧为周期忽大忽小。mad 与 flow 同时出现锯齿、且连续 ≥6 帧才算（单帧的起步 / 停步不算）。
    osc_mad, osc_flow = oscillation(mad), oscillation(flow)
    shaky = [t for t in range(n) if osc_mad[t] > OSC_MAD and osc_flow[t] > OSC_FLOW]
    for a, b in group_runs(shaky, gap=2):
        if b - a + 1 >= OSC_MIN_FRAMES:
            p = max(range(a, b + 1), key=lambda t: osc_mad[t])
            add('oscillation', max(1, a - OSC_W // 2), min(n - 1, b + OSC_W // 2 - 1), p, 'high',
                {'mad_amplitude': round(float(osc_mad[p]), 3), 'flow_amplitude': round(float(osc_flow[p]), 4),
                 'frames': int(b - a + 1)})
    events.sort(key=lambda e: (e['start_frame'], e['type']))
    return events


def faces(frames, step=3):
    if cv2 is None:
        return {'checked': False, 'reason': 'opencv not installed'}
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if casc.empty():
        return {'checked': False, 'reason': 'haar cascade missing'}
    hits = []
    sampled = list(range(0, len(frames), step))
    for t in sampled:
        g = cv2.cvtColor(frames[t], cv2.COLOR_RGB2GRAY)
        det = casc.detectMultiScale(g, scaleFactor=1.1, minNeighbors=6, minSize=(30, 30))
        if len(det):
            hits.append({'frame': int(t), 'boxes_640x360': [[int(v) for v in d] for d in det]})
    return {'checked': True, 'detector': 'opencv haar frontalface_default, 640x360, minNeighbors=6',
            'sampled_frames': len(sampled), 'frames_with_faces': len(hits),
            'max_faces': max((len(h['boxes_640x360']) for h in hits), default=0), 'hits': hits[:12]}


def _font(size):
    from PIL import ImageFont
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pillow < 10.1
        return ImageFont.load_default()


def chart(m, events, width, height=210):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (width, height), (18, 18, 22)); d = ImageDraw.Draw(img)
    n = len(m['mad']); pad = 8; plot_h = height - 34
    def xs(t): return pad + (width - 2 * pad) * t / max(1, n - 1)
    for e in events:
        for t in range(e['start_frame'], e['end_frame'] + 1):
            d.line([(xs(t), 4), (xs(t), plot_h)], fill=(120, 20, 20), width=2)
    series = [('mad', (240, 200, 60)), ('tv', (90, 200, 250)), ('morph', (250, 90, 200)),
              ('flow', (120, 240, 120)), ('luma', (200, 200, 200)), ('sharp', (255, 140, 60))]
    f = _font(15)
    for i, (key, color) in enumerate(series):
        v = np.asarray(m[key], float); top = max(float(np.percentile(v, 99.5)) * 1.1, 1e-6)
        if key == 'tv':
            top = max(top, 0.3)
        pts = [(xs(t), plot_h - (plot_h - 6) * min(1.0, v[t] / top)) for t in range(n)]
        d.line(pts, fill=color, width=2)
        d.text((pad + i * 150, plot_h + 8), f'{key} max {v.max():.1f}', fill=color, font=f)
    for s in range(0, int(n / 24) + 1):
        d.text((xs(s * 24) + 2, 6), f'{s}s', fill=(150, 150, 150), font=f)
    return img


def dense_sheet(frames, m, events, fps, out):
    from PIL import Image, ImageDraw
    idx = list(range(0, len(frames), DENSE_STEP))
    if idx[-1] != len(frames) - 1:
        idx.append(len(frames) - 1)
    rows = (len(idx) + DENSE_COLS - 1) // DENSE_COLS
    tw, th = TILE; width = tw * DENSE_COLS
    flagged = {t for e in events for t in range(e['start_frame'], e['end_frame'] + 1)}
    sheet = Image.new('RGB', (width, th * rows + 210), (0, 0, 0)); d = ImageDraw.Draw(sheet); f = _font(16)
    for k, t in enumerate(idx):
        x, y = (k % DENSE_COLS) * tw, (k // DENSE_COLS) * th
        sheet.paste(Image.fromarray(resize(frames[t], TILE)), (x, y))
        near = any(abs(t - g) <= DENSE_STEP // 2 for g in flagged)
        d.rectangle([x, y, x + 118, y + 22], fill=(160, 0, 0) if near else (0, 0, 0))
        d.text((x + 5, y + 3), f'f{t:03d} {t / fps:4.2f}s', fill=(255, 255, 255), font=f)
    sheet.paste(chart(m, events, width), (0, th * rows))
    sheet.save(out, quality=80)


def flags_sheet(frames, events, fps, out, sid):
    from PIL import Image, ImageDraw
    fw, fh = 480, 270; f = _font(18)
    if not events:
        img = Image.new('RGB', (fw * 2, 90), (16, 40, 16)); d = ImageDraw.Draw(img)
        d.text((16, 30), f'{sid}: no automatic frame flags (still needs a human look at {sid}-dense.jpg)',
               fill=(220, 255, 220), font=f)
        img.save(out, quality=85); return
    order = {'high': 0, 'medium': 1, 'info': 2}
    shown = sorted(events, key=lambda e: (order.get(e['severity'], 3), e['start_frame']))[:8]
    img = Image.new('RGB', (fw * 2, (fh + 30) * len(shown)), (0, 0, 0)); d = ImageDraw.Draw(img)
    for r, e in enumerate(shown):
        a = max(0, e['peak_frame'] - 1) if e['type'] != 'freeze' else e['start_frame']
        b = e['peak_frame'] if e['type'] != 'freeze' else e['end_frame']
        y = r * (fh + 30)
        d.text((8, y + 5), f"{e['type']} ({e['severity']})  f{a:03d} -> f{b:03d}  t={b / fps:.2f}s  "
               + ', '.join(f'{k}={v}' for k, v in e.items() if k not in
                           ('type', 'severity', 'start_frame', 'end_frame', 'peak_frame', 'time')),
               fill=(255, 210, 120), font=f)
        img.paste(Image.fromarray(resize(frames[a], (fw, fh))), (0, y + 30))
        img.paste(Image.fromarray(resize(frames[b], (fw, fh))), (fw, y + 30))
    img.save(out, quality=82)


def analyze(path, qa_dir, sid, fps=24.0):
    """返回 (summary, full)。summary 写进 results.json，full（含逐帧数组）写进 qa/Sxx.json。"""
    qa_dir = Path(qa_dir)
    frames = decode(path)
    m, hists = metrics(frames)
    events = find_events(m, fps, hists)
    face = faces(frames)
    dense = qa_dir / f'{sid}-dense.jpg'; flags = qa_dir / f'{sid}-flags.jpg'
    dense_sheet(frames, m, events, fps, dense)
    flags_sheet(frames, events, fps, flags, sid)
    review = any(e['severity'] != 'info' for e in events) or (face.get('checked') and face['frames_with_faces'] > 0)
    stats = {k: {'median': round(float(np.median(v[1:] if k in ('mad', 'tv', 'flow', 'morph') else v)), 3),
                 'max': round(float(np.max(v)), 3)} for k, v in m.items()}
    summary = {'version': VERSION, 'frames_analyzed': int(len(frames)), 'opencv': bool(cv2 is not None),
               'auto_verdict': 'review' if review else 'clean',
               'events': events,
               'faces': {k: v for k, v in face.items() if k != 'hits'},
               'stats': stats,
               'dense_sheet': f'production/monalisa/qa/{sid}-dense.jpg',
               'flags_sheet': f'production/monalisa/qa/{sid}-flags.jpg'}
    full = dict(summary, faces=face,
                per_frame={k: [round(float(x), 3) for x in v] for k, v in m.items()})
    return summary, full


if __name__ == '__main__':  # 本地：python3 clip_qa.py clip.mp4 [SID] [qa_dir]
    import sys
    clip = sys.argv[1]; sid = sys.argv[2] if len(sys.argv) > 2 else Path(clip).stem
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('/tmp/clip_qa'); out.mkdir(parents=True, exist_ok=True)
    s, full = analyze(clip, out, sid)
    (out / f'{sid}.frame_qa.json').write_text(json.dumps(full, ensure_ascii=False, indent=1))
    print(json.dumps(s, ensure_ascii=False, indent=1))
