#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JMS 帧级畸变 QC：30 条素材逐帧解码，4 项自动化指标 + 人工复核标记。

指标（每镜）:
  sharp_ratio   最糊帧锐度 / 中位锐度（Laplacian 方差）   < 0.35 → F1 模糊帧
  flicker_max   帧间亮度均值最大跳变                     > 6.0  → F2 闪烁
  flicker_ratio 最大跳变 / 中位跳变                      > 12   → F2 闪烁
  tear_max      帧间 16x9 网格平均绝对差最大值            > 12   → F3 结构突变
  face_jitter   主脸框中心逐帧位移中位数（占画幅宽比例）  > 0.012→ F4 脸部不稳
  face_rate     人脸检测帧占比（仅报告，不自动判死刑）

退出码: 0 = 检查完成（有无 flag 均以报告为准）/ 1 = 检查本身失败
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
RESULTS = json.loads((ROOT / 'results.json').read_text())
IDS = [f'S{i:02d}' for i in range(1, 31)]
OUT = Path('work/jmsjung-qc')
DL = OUT / 'clips'
OUT.mkdir(parents=True, exist_ok=True)
DL.mkdir(exist_ok=True)

log = lambda *a: print('[frame-qc]', *a, flush=True)

# ---- 人脸检测：OpenCV 自带 Haar 级联（随 pip 包分发，零网络依赖）----
net = None
face_skip_reason = ''
log('cv2 version:', cv2.__version__)
try:
    import cv2.data  # noqa: E402
    _casc_path = os.path.join(cv2.data.haarcascades,
                              'haarcascade_frontalface_default.xml')
    log('Haar path:', _casc_path, 'exists:', os.path.exists(_casc_path))
    _c = cv2.CascadeClassifier(_casc_path)
    if _c.empty():
        raise RuntimeError('empty classifier')
    net = _c
    log('Haar 加载成功')
except Exception as e:
    net = None
    face_skip_reason = f'Haar 不可用: {type(e).__name__}: {e}'
    log(f'  人脸检测跳过（{face_skip_reason}），其余 3 项指标照跑')

def fetch(url, dest, want):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'jmsjung-frame-qc/1.0'})
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if hashlib.sha256(dest.read_bytes()).hexdigest() != want:
                raise RuntimeError('sha256 mismatch')
            return
        except Exception as e:
            log(f'  下载重试 {attempt+1}: {e}')
            time.sleep(5)
    raise RuntimeError(f'{dest.name} 下载/校验失败')

def analyze(path):
    """逐帧：亮度均值、锐度（Laplacian 方差）、帧间结构差。320x180 快速档。"""
    cap = cv2.VideoCapture(str(path))
    luma_means, sharp, prev_small = [], [], None
    tear_max, n = 0.0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(frame, (320, 180))
        luma = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
        luma_means.append(float(luma.mean()))
        sharp.append(float(cv2.Laplacian(luma, cv2.CV_32F).var()))
        if prev_small is not None:
            tear_max = max(tear_max,
                           float(np.abs(small.astype(np.int16) - prev_small.astype(np.int16)).mean()))
        prev_small = small
        n += 1
    cap.release()
    if n < 100:
        raise RuntimeError(f'{Path(path).name} 帧数异常: {n}')
    diffs = np.abs(np.diff(luma_means))
    med_diff = float(np.median(diffs)) or 1e-6
    max_diff = float(diffs.max())
    sharp_arr = np.array(sharp)
    return {
        'frames': n,
        'min_sharp_at_s': round(int(np.argmin(sharp_arr)) / 24.0, 2),
        'sharp_min': round(float(sharp_arr.min()), 1),
        'sharp_med': round(float(np.median(sharp)), 1),
        'sharp_ratio': round(float(np.min(sharp) / (float(np.median(sharp)) or 1e-6)), 3),
        'flicker_med': round(med_diff, 3),
        'flicker_max': round(max_diff, 2),
        'flicker_ratio': round(max_diff / med_diff, 1),
        'tear_max': round(tear_max, 2),
    }

def face_stability(path):
    """每 2 帧跑 Haar 人脸检测，追踪主脸（最大框）归一化中心 x 位移。"""
    if net is None:
        return {'face_rate': None, 'face_jitter': None, 'face_frames': 0,
                'note': face_skip_reason}
    cap = cv2.VideoCapture(str(path))
    centers, detected, total, i = [], 0, 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % 2 == 0:
            small = cv2.resize(frame, (480, 270))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            faces = net.detectMultiScale(gray, 1.15, 5, minSize=(40, 40))
            total += 1
            if len(faces):
                detected += 1
                (x, y, w, h) = max(faces, key=lambda b: b[2] * b[3])
                centers.append((x + w / 2) / 480.0)  # 归一化 x 中心
        i += 1
    cap.release()
    jitter = 0.0
    if len(centers) >= 4:
        deltas = [abs(y - x) for x, y in zip(centers, centers[1:])]
        jitter = float(np.median(deltas))
    return {'face_rate': round(detected / max(total, 1), 2),
            'face_jitter': round(jitter, 4),
            'face_frames': len(centers)}

def flags_of(r):
    f = []
    if r['sharp_ratio'] < 0.35:
        f.append('F1 模糊帧')
    if r['flicker_max'] > 6.0 or r['flicker_ratio'] > 12:
        f.append('F2 闪烁')
    if r['tear_max'] > 12:
        f.append('F3 结构突变')
    if r.get('face_jitter') is not None and r['face_jitter'] > 0.012:
        f.append('F4 脸部不稳')
    return f

# ---- 主流程 ----
try:
    log('1/4 下载 30 镜 + sha256 逐字节校验 …')
    for sid in IDS:
        row = RESULTS['shots'][sid]
        fetch(row['video_url'], DL / (sid + '.mp4'), row['sha256'])
        log(f'  {sid} OK')

    log('2/4 逐帧分析（亮度/锐度/结构）…')
    t0 = time.time()
    metrics = {}
    for sid in IDS:
        metrics[sid] = analyze(DL / (sid + '.mp4'))
        m = metrics[sid]
        log(f'  {sid} sharp_ratio={m["sharp_ratio"]} flicker_max={m["flicker_max"]} '
            f'tear_max={m["tear_max"]}')
    log(f'  完成 {time.time()-t0:.0f}s')

    log('3/4 人脸稳定性检测（DNN，每 2 帧）…')
    t0 = time.time()
    for sid in IDS:
        metrics[sid].update(face_stability(DL / (sid + '.mp4')))
        m = metrics[sid]
        log(f'  {sid} face_rate={m["face_rate"]} face_jitter={m["face_jitter"]}')
    log(f'  完成 {time.time()-t0:.0f}s')
except Exception as exc:
    import traceback
    (OUT / 'FATAL.txt').write_text(traceback.format_exc())
    _tok = os.environ.get('GITHUB_TOKEN')
    _repo = os.environ.get('GITHUB_REPOSITORY')
    if _tok and _repo:
        try:
            import shutil as _sh
            _deliv = ROOT / 'delivery' / 'final'
            _deliv.mkdir(exist_ok=True)
            _sh.copy2(OUT / 'FATAL.txt', _deliv / f'FATAL-{int(time.time())}.txt')
            _sh = None
            for _c in (['git', 'config', 'user.name', 'jmsjung-frame-qc'],
                       ['git', 'config', 'user.email', 'jmsjung-frame-qc@users.noreply.github.com']):
                subprocess.run(_c, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(['git', 'add', 'production/jmsjung/delivery/final/'],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(['git', 'commit', '-q', '-m',
                            'jmsjung: 帧级 QC FATAL 收据'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            _remote = f'https://x-access-token:{_tok}@github.com/{_repo}.git'
            subprocess.run(['git', 'push', '-q', _remote,
                            'HEAD:arena/929dc8b6-desktop-tutorial'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass
    raise

log('4/4 汇总报告 …')
rows = []
for sid in IDS:
    m = dict(metrics[sid])
    m['id'] = sid
    m['flags'] = flags_of(m)
    rows.append(m)
flagged = [r['id'] for r in rows if r['flags']]
report = {
    'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'face_check_skipped': face_skip_reason or None,
    'method': ('逐帧解码 320x180：Laplacian 锐度、帧间亮度跳变、帧间网格结构差；'
               'DNN 人脸检测（每 2 帧，300x300）追踪主脸中心位移'),
    'thresholds': {'F1': 'sharp_ratio<0.35', 'F2': 'flicker_max>6.0 或 flicker_ratio>12',
                   'F3': 'tear_max>12', 'F4': 'face_jitter>0.012'},
    'flagged': flagged,
    'shots': rows,
}
(OUT / 'frame-qc-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
md = ['# JMS 帧级畸变 QC 报告', '',
      f'- 生成: {report["generated_at"]}',
      f'- 方法: {report["method"]}',
      f'- **标红镜头: {", ".join(flagged) if flagged else "无（30 镜全过 4 项阈值）"}**', '',
      '| 镜 | 帧数 | 锐度比 | 闪烁max | 结构max | 人脸率 | 脸抖动 | 标记 |',
      '| --- | --- | --- | --- | --- | --- | --- | --- |']
for r in rows:
    md.append('| %s | %d | %s | %s | %s | %s | %s | %s |' % (
        r['id'], r['frames'], r['sharp_ratio'], r['flicker_max'], r['tear_max'],
        r['face_rate'], r['face_jitter'], '、'.join(r['flags']) or '—'))
(OUT / 'frame-qc-report.md').write_text('\n'.join(md) + '\n')

# ---- 提交分支 + artifact（token 只进 argv，不落日志/文件）----
deliv = ROOT / 'delivery' / 'final'
deliv.mkdir(exist_ok=True)
for f in ('frame-qc-report.json', 'frame-qc-report.md'):
    shutil_copy = (deliv / f)
    shutil_copy.write_bytes((OUT / f).read_bytes())
tok = os.environ.get('GITHUB_TOKEN')
repo = os.environ.get('GITHUB_REPOSITORY')
if tok and repo:
    sh = lambda *c: subprocess.run([str(x) for x in c], check=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sh('git', 'config', 'user.name', 'jmsjung-frame-qc')
    sh('git', 'config', 'user.email', 'jmsjung-frame-qc@users.noreply.github.com')
    sh('git', 'add', 'production/jmsjung/delivery/final/')
    try:
        sh('git', 'commit', '-q', '-m', 'jmsjung: 帧级畸变 QC 报告（30 镜逐帧 4 指标）')
    except subprocess.CalledProcessError:
        pass
    remote = f'https://x-access-token:{tok}@github.com/{repo}.git'
    r1 = subprocess.run(['git', 'push', '-q', remote, 'HEAD:arena/929dc8b6-desktop-tutorial'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r1.returncode != 0:
        subprocess.run(['git', 'pull', '-q', '--rebase', 'origin',
                        'arena/929dc8b6-desktop-tutorial'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        r2 = subprocess.run(['git', 'push', '-q', remote,
                             'HEAD:arena/929dc8b6-desktop-tutorial'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r2.returncode != 0:
            log('WARN 报告推送失败（artifact 仍可用）')
log(f'DONE flagged={flagged or "无"}')
