"""素材复审助手：qa/Sxx.json（clip_qa 逐帧指标）× 真实 EDL 时长 → 每镜的起动帧、定格、自动事件、
建议的 WINDOWS 时间窗。建议只是建议——最终写进 render.py 的 WINDOWS 之前，每一镜都要人看过
qa/Sxx-dense.jpg / Sxx-flags.jpg，结论记在 qa-review.md。

为什么需要：render_segment 从时间窗起点 a（默认 0.12 s）开始取「成片需要的时长」。成片里多数镜头
只用 2–4 秒，取的正好是素材开头——而 Agnes 的素材开头常有 0.3–0.7 s 的「起步定格」（运镜缓入），
紧接在硬切后面看起来像卡了一下。这里按逐帧帧差找到真正开始动的那一帧，把起点挪过去；
同时避开自动标记的硬切 / 闪帧 / 冻结 / 畸变尖峰；不允许超过 1.33× 慢放。
用法：python3 production/monalisa/review_clips.py [--json out.json]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import screenplay_gen  # noqa: E402

FPS_SRC = 24.0
EDGE = 0.12
MAX_SLOW = 1.33
AVOID = {'hard_cut', 'flash', 'black', 'morph_spike', 'jump'}


def motion_onset(mad, median):
    """第一帧「持续在动」的位置（连续 3 帧帧差 ≥ max(0.6, 35% 中位数)）。"""
    thr = max(0.6, 0.35 * median)
    for t in range(1, len(mad) - 3):
        if all(mad[k] >= thr for k in range(t, t + 3)):
            return t
    return 0


def motion_end(mad, median):
    thr = max(0.6, 0.35 * median)
    for t in range(len(mad) - 1, 3, -1):
        if all(mad[k] >= thr for k in range(t - 2, t + 1)):
            return t
    return len(mad) - 1


def suggest(entry, qa, need):
    per = qa['frame_qa']['per_frame']
    mad = np.asarray(per['mad'], float)
    med = float(np.median(mad[1:]))
    length = qa['duration']
    onset = motion_onset(mad, med) / FPS_SRC
    stop = motion_end(mad, med) / FPS_SRC
    bad = [(e['start_frame'] / FPS_SRC - 0.05, (e['end_frame'] + 1) / FPS_SRC + 0.05, e['type'])
           for e in qa['frame_qa']['events'] if e['type'] in AVOID]
    lo, hi = EDGE, length - EDGE
    take = min(need, hi - lo)
    best = None
    start = lo
    while start + take <= hi + 1e-9:
        overlap = sum(max(0.0, min(b, start + take) - max(a, start)) for a, b, _ in bad)
        still = max(0.0, min(onset, start + take) - start) + max(0.0, start + take - max(stop, start))
        score = overlap * 10 + still + 0.02 * start      # 先避事件，再避定格，最后偏早（素材越往后越容易漂）
        if best is None or score < best[0] - 1e-9:
            best = (score, start, overlap, still)
        start += 1 / FPS_SRC
    _, a, overlap, still = best
    return {'id': entry['id'], 'need': round(need, 2), 'clip': round(length, 2),
            'onset': round(onset, 2), 'motion_end': round(stop, 2),
            'window': (round(a, 2), round(a + take, 2)), 'slow': round(need / take, 3),
            'still_inside': round(still, 2), 'event_overlap': round(overlap, 2),
            'default_still': round(max(0.0, onset - EDGE), 2),
            'events': [(e['type'], e['start_frame'], e['end_frame']) for e in qa['frame_qa']['events']],
            'faces': qa['frame_qa']['faces'].get('frames_with_faces'),
            'auto': qa['frame_qa']['auto_verdict']}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', type=Path)
    args = ap.parse_args()
    story = json.loads((HERE / 'story.json').read_text())
    rows, _, _ = screenplay_gen.film_rows(story)
    edl = screenplay_gen.render.make_edl(story, rows)
    out = []
    for e in edl:
        if e['kind'] != 'agnes':
            continue
        path = HERE / 'qa' / f"{e['id']}.json"
        need = (e['end_frame'] - e['start_frame']) / 30.0
        if not path.exists():
            out.append({'id': e['id'], 'need': round(need, 2), 'missing': True})
            continue
        qa = json.loads(path.read_text())
        if 'frame_qa' not in qa:
            out.append({'id': e['id'], 'need': round(need, 2), 'no_frame_qa': qa.get('frame_qa_error')})
            continue
        out.append(suggest(e, qa, need))
    print(f"{'镜头':4} {'需要':>5} {'起动':>5} {'停':>5} {'建议窗':>13} {'慢放':>5} {'窗内定格':>6} {'默认定格':>6} 事件 / 正脸")
    for r in out:
        if r.get('missing') or 'no_frame_qa' in r:
            print(f"{r['id']:4} {r['need']:5.2f}  —— {'还没生成' if r.get('missing') else '无逐帧体检: ' + str(r['no_frame_qa'])}")
            continue
        ev = ' '.join(f'{t}@{a}-{b}' for t, a, b in r['events']) or '-'
        print(f"{r['id']:4} {r['need']:5.2f} {r['onset']:5.2f} {r['motion_end']:5.2f} "
              f"{r['window'][0]:6.2f}–{r['window'][1]:5.2f} {r['slow']:5.2f} {r['still_inside']:6.2f} "
              f"{r['default_still']:6.2f} {ev} / {r['faces']}")
    if args.json:
        args.json.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')


if __name__ == '__main__':
    main()
