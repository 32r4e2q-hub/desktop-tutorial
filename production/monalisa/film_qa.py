"""成片终检（本地，对 git 里交付的 mp4 跑）：把「逐帧、音画同步、字幕对轨」变成可复查的数字。

与 production/review_film.py 互补（它管黑帧 / 冻结 / 静音 / 电平 / 抽样帧），这里管：

1. **全部 5400 帧**逐帧解码（320×180），每一个 EDL 切点上必须真的有一次换画面（±1 帧），
   切点之外不许出现硬切 / 闪帧（= 素材里的中途换场漏网，或者拼接出错）；黑帧只许出现在片头淡入 / 片尾淡出；
   每段内部不许有 ≥ 0.4 s 的完全静止（tpad 克隆尾帧 = 素材不够长）——24→30 fps 每 5 帧一张重复帧是正常节奏，不报。
2. Haar 正脸抽检（640×360，5 fps），按 EDL 段归属。
3. **音画同步**：按 narration-timing.json 把六段配音各自 atempo 后，与成片音轨做波形互相关，
   求每章的实际偏移（应为 0 ± 20 ms）。字幕、切点都挂在同一张时间表上，这一步证明声音真的在表上说的位置。
4. **字幕对轨**：caption-timing.json 的每条字幕，起点与该句在配音里的起音（clause-times × 变速 + 章节起点）比，
   应在 [-0.25, +0.10] s 内（设计值是提前 0.09 s 出字）；字幕之间不重叠。
5. 切点对照图：每个切点前一帧 | 后一帧，一张图看完 45 个切点（sheets/cuts-*.jpg）。

用法：python3 production/monalisa/film_qa.py --film 交付/xxx.mp4 --delivery production/monalisa/delivery --out work/monalisa/film-qa
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FPS = 30
W, H = 320, 180


def frames_stream(film, w, h, fps=None):
    vf = f'scale={w}:{h}:flags=area' + (f',fps={fps}' if fps else '')
    proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(film), '-map', '0:v:0', '-vf', vf,
                             '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    size = w * h * 3
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(h, w, 3)
    proc.wait()


def scan_frames(film):
    mad, tv, luma, thumbs = [], [], [], []
    prev_g = prev_h = None
    for f in frames_stream(film, W, H):
        g = f[..., 0] * 0.299 + f[..., 1] * 0.587 + f[..., 2] * 0.114
        q = (f // 32).astype(np.int32)
        hist = np.bincount((q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]).ravel(), minlength=512) / (W * H)
        mad.append(0.0 if prev_g is None else float(np.abs(g - prev_g).mean()))
        tv.append(0.0 if prev_h is None else float(0.5 * np.abs(hist - prev_h).sum()))
        luma.append(float(g.mean()))
        thumbs.append(f[::2, ::2].copy())      # 160×90，做切点对照图
        prev_g, prev_h = g, hist
    return np.array(mad), np.array(tv), np.array(luma), thumbs


def check_cuts(edl, mad, tv, luma):
    n = len(mad)
    bounds = [e['start_frame'] for e in edl[1:]]
    found, weak = [], []
    for b in bounds:
        window = range(max(1, b - 1), min(n, b + 2))
        peak = max(window, key=lambda t: mad[t] + 40 * tv[t])
        strength = {'frame': b, 'peak_frame': int(peak), 'mad': round(float(mad[peak]), 2), 'tv': round(float(tv[peak]), 3)}
        (found if (mad[peak] > 6 or tv[peak] > 0.15) else weak).append(strength)
    near = {t for b in bounds for t in range(b - 2, b + 3)}
    # 设计好的淡入淡出不算「硬切」：片头 0.25 s 淡入、最后一个镜头 0.18 s 淡出进片尾卡、片尾卡自身淡入淡出
    end_start = edl[-1]['start_frame']
    near |= set(range(0, 10)) | set(range(end_start - 7, n))
    local = np.array([np.median(mad[max(1, t - 15):t + 16]) for t in range(n)])
    stray = [{'frame': t, 'time': round(t / FPS, 3), 'mad': round(float(mad[t]), 2), 'tv': round(float(tv[t]), 3)}
             for t in range(1, n) if t not in near and tv[t] > 0.25 and mad[t] > max(12.0, 5 * local[t])]
    black = [t for t in range(n) if luma[t] < 8]
    allowed_black = set(range(0, 8)) | set(range(edl[-1]['start_frame'], n))
    bad_black = [t for t in black if t not in allowed_black]
    stills = []
    for e in edl:
        if e['kind'] != 'agnes':
            continue
        run = 0
        for t in range(e['start_frame'] + 1, e['end_frame']):
            run = run + 1 if mad[t] < 0.05 else 0
            if run == 12:
                stills.append({'id': e['id'], 'from_frame': t - 11, 'time': round((t - 11) / FPS, 2)})
    return {'edl_cuts': len(bounds), 'cuts_confirmed': len(found), 'weak_cuts': weak,
            'stray_cuts_inside_shots': stray, 'black_frames_outside_fades': bad_black[:50],
            'frozen_runs_in_agnes_segments': stills}


def faces_by_segment(film, edl):
    try:
        import cv2
    except ImportError:
        return {'checked': False}
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    hits = {}
    for k, f in enumerate(frames_stream(film, 640, 360, fps=5)):
        t = k / 5.0
        det = casc.detectMultiScale(cv2.cvtColor(f, cv2.COLOR_RGB2GRAY), scaleFactor=1.1, minNeighbors=6, minSize=(30, 30))
        if len(det):
            frame = int(round(t * FPS))
            seg = next((e['id'] for e in edl if e['start_frame'] <= frame < e['end_frame']), '?')
            hits.setdefault(seg, []).append(round(t, 1))
    return {'checked': True, 'sample_fps': 5, 'segments_with_hits': {k: v[:10] for k, v in hits.items()}}


def pcm(path, rate=8000, tempo=None):
    af = ['-af', f'atempo={tempo:.9f}'] if tempo else []
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), *af, '-ac', '1', '-ar', str(rate),
                          '-f', 's16le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, '<i2').astype(np.float32) / 32768


def _xcorr(seg, ref):
    n = 1 << int(np.ceil(np.log2(len(seg) + len(ref))))
    return np.fft.irfft(np.fft.rfft(seg, n) * np.conj(np.fft.rfft(ref, n)), n)[:len(seg) - len(ref) + 1]


def _envelope(x, rate, hop):
    h = int(rate * hop); n = len(x) // h * h
    e = np.sqrt((x[:n].reshape(-1, h) ** 2).mean(1))
    return e - e.mean()


def audio_sync(film, narration, audio_dir, rate=8000, search=0.5):
    """两种独立估计：波形互相关（采样级）+ 10 ms 能量包络互相关；peak_ratio = 主峰 / 主峰 ±20 ms 以外的最大旁瓣。
    重建的配音用 ffmpeg atempo，与出片时的变速波形不会逐样本一致（相关系数本来就不高），
    所以看的是「峰在哪、峰够不够尖、两种估计是否一致」，不是相关系数本身。"""
    mix = pcm(film, rate)
    rows = []
    for row in narration:
        voice = pcm(audio_dir / f"{row['id']}.mp3", rate, tempo=row['tempo'])
        lo = max(0, int((row['start'] - search) * rate))
        seg = mix[lo: lo + len(voice) + int(2 * search * rate)]
        corr = _xcorr(seg, voice)
        lag = int(np.argmax(corr))
        guard = int(0.02 * rate)
        side = np.concatenate([corr[:max(0, lag - guard)], corr[lag + guard:]])
        ratio = float(corr[lag] / (np.max(np.abs(side)) + 1e-9)) if len(side) else float('inf')
        hop = 0.01
        env_corr = _xcorr(_envelope(seg, rate, hop), _envelope(voice, rate, hop))
        env_lag = int(np.argmax(env_corr))
        rows.append({'id': row['id'], 'expected_start': round(row['start'], 3),
                     'measured_offset_ms': round(((lo + lag) / rate - row['start']) * 1000, 1),
                     'peak_ratio': round(ratio, 2),
                     'envelope_offset_ms': round((lo / rate + env_lag * hop - row['start']) * 1000, 1)})
    return rows


def caption_check(cues, narration, clause_table):
    strip = lambda t: re.sub(r'[^\u3400-\u9fffA-Za-z0-9]', '', t)
    onsets = []
    for row in narration:
        for c in clause_table[row['id']]['clauses']:
            onsets.append((strip(c['text']), row['start'] + c['start'] / row['tempo']))
    out, k = [], 0
    for cue in cues:
        key = strip(cue['text'])
        while k < len(onsets) and not key.startswith(onsets[k][0][:max(1, min(len(key), len(onsets[k][0])))]):
            k += 1
        if k >= len(onsets):
            out.append({'text': cue['text'], 'error': 'no matching clause'})
            k = 0
            continue
        delta = cue['start'] - onsets[k][1]
        out.append({'text': cue['text'], 'cue_start': round(cue['start'], 3), 'voice_onset': round(onsets[k][1], 3),
                    'delta': round(delta, 3)})
        consumed = ''
        while k < len(onsets) and len(consumed) < len(key):
            consumed += onsets[k][0]
            k += 1
    overlaps = [i for i in range(1, len(cues)) if cues[i]['start'] < cues[i - 1]['end'] - 1e-3]
    deltas = [r['delta'] for r in out if 'delta' in r]
    return {'cues': len(cues), 'matched': len(deltas), 'delta_min': min(deltas), 'delta_max': max(deltas),
            'outside_window': [r for r in out if 'delta' in r and not -0.25 <= r['delta'] <= 0.10],
            'unmatched': [r for r in out if 'error' in r], 'overlaps': overlaps}


def cut_sheets(edl, thumbs, out):
    from PIL import Image, ImageDraw
    bounds = [(edl[i - 1]['id'], edl[i]['id'], edl[i]['start_frame']) for i in range(1, len(edl))]
    per = 16
    for s in range(0, len(bounds), per):
        chunk = bounds[s:s + per]
        img = Image.new('RGB', (4 * 330, ((len(chunk) + 1) // 2) * 112), (0, 0, 0))
        d = ImageDraw.Draw(img)
        for k, (a, b, f) in enumerate(chunk):
            x, y = (k % 2) * 660, (k // 2) * 112
            img.paste(Image.fromarray(thumbs[f - 1]), (x, y + 18))
            img.paste(Image.fromarray(thumbs[min(f, len(thumbs) - 1)]), (x + 165, y + 18))
            d.text((x + 2, y + 2), f'{a}|{b} f{f} {f / FPS:.2f}s', fill=(255, 220, 120))
        img.save(out / f'cuts-{s // per + 1}.jpg', quality=85)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--film', type=Path, required=True)
    ap.add_argument('--delivery', type=Path, default=HERE / 'delivery')
    ap.add_argument('--audio', type=Path, default=HERE / 'audio')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    edl = json.loads((args.delivery / 'edit-decision-list.json').read_text())
    narration = json.loads((args.delivery / 'narration-timing.json').read_text())
    cues = json.loads((args.delivery / 'caption-timing.json').read_text())
    clause_table = json.loads((args.audio / 'clause-times.json').read_text())
    mad, tv, luma, thumbs = scan_frames(args.film)
    report = {'film': str(args.film), 'frames_decoded': len(mad)}
    report['frames'] = check_cuts(edl, mad, tv, luma)
    report['faces'] = faces_by_segment(args.film, edl)
    report['audio_sync'] = audio_sync(args.film, narration, args.audio)
    report['captions'] = caption_check(cues, narration, clause_table)
    cut_sheets(edl, thumbs, args.out)
    np.savez_compressed(args.out / 'per-frame.npz', mad=mad, tv=tv, luma=luma)
    (args.out / 'film-qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    fr, cap = report['frames'], report['captions']
    print(f"frames {len(mad)} | cuts {fr['cuts_confirmed']}/{fr['edl_cuts']} weak {len(fr['weak_cuts'])} "
          f"| stray {len(fr['stray_cuts_inside_shots'])} | black {len(fr['black_frames_outside_fades'])} "
          f"| frozen {len(fr['frozen_runs_in_agnes_segments'])}")
    print('audio sync (waveform ms / peak ratio / envelope ms):',
          [(r['id'], r['measured_offset_ms'], r['peak_ratio'], r['envelope_offset_ms']) for r in report['audio_sync']])
    print(f"captions {cap['matched']}/{cap['cues']} delta {cap['delta_min']}..{cap['delta_max']} "
          f"outside {len(cap['outside_window'])} overlaps {len(cap['overlaps'])}")
    print('faces:', report['faces'].get('segments_with_hits'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
