"""配音 ASR 探针：成片出来之前，先对收紧后的六段配音 audio/N0x.mp3 做一次**不给提示**的转写。

为什么要在出片前做（production/verbatim_check.py 只能听成片）：
1. 逐字：TTS 有没有吞字 / 改字。N01「而是一个意大利油漆工」对出来 7.3 字/秒，比全片均速 5.4 快三成——
   可能只是念得快，也可能吞了字。沙箱连不上任何 ASR 模型源（huggingface / modelscope 都被挡），
   只能在 runner 上转写；有问题现在重录只花一次 TTS，成片后再发现就要重新出片。
2. 分句起点复核：whisper 词级时间戳给出每个分句第一个字的时刻，和 clause_times.py（分组 DP，
   停顿边界）逐句比对。切点和字幕都挂在 DP 的分句起点上——两个独立方法相差 > 0.35 s 的分句要人看。

复用 verbatim_check.py 的 normalize（繁转简、数字转汉字）/ CER / diff；**不给 initial_prompt**
（模型不该事先知道剧本），不开 VAD（短词不许被当静音切掉），condition_on_previous_text=False
（防止幻觉复读）。输出 production/monalisa/audio/asr-probe.json，由 monalisa-asr.yml commit 回分支。
用法：python3 production/monalisa/asr_probe.py [--model small] [--work work/monalisa/asr]
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'production'))
sys.path.insert(0, str(HERE))
import verbatim_check as vc  # noqa: E402
from clause_times import PUNCT  # noqa: E402

MAX_CER = 0.15
MAX_START_DELTA = 0.35


def align_indices(expected, heard):
    """编辑距离回溯：expected 的每个字 → heard 里对应的字（匹配 'eq' / 替换 'sub'），删掉的字没有对应。"""
    n, m = len(expected), len(heard)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1,
                           dp[i - 1][j - 1] + (expected[i - 1] != heard[j - 1]))
    mapping = {}
    i, j = n, m
    while i > 0 and j > 0:
        if dp[i][j] == dp[i - 1][j - 1] + (expected[i - 1] != heard[j - 1]):
            mapping[i - 1] = (j - 1, 'eq' if expected[i - 1] == heard[j - 1] else 'sub')
            i, j = i - 1, j - 1
        elif dp[i][j] == dp[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1
    return mapping


def char_times(words):
    """词级时间戳 → 逐字时间（一个「词」里的字在词的起止之间均分）。"""
    chars, times = [], []
    for w in words:
        text = vc.normalize(w['word'])
        if not text:
            continue
        span = max(w['end'] - w['start'], 0.01)
        for k, ch in enumerate(text):
            chars.append(ch)
            times.append(w['start'] + span * k / len(text))
    return ''.join(chars), times


def clause_starts(script, words, dp_rows):
    clauses = [c for c in re.split(PUNCT, script) if c]
    heard, times = char_times(words)
    expected = ''.join(vc.normalize(c) for c in clauses)
    mapping = align_indices(expected, heard)
    rows, at = [], 0
    for k, clause in enumerate(clauses):
        norm = vc.normalize(clause)
        found = None
        for off in range(len(norm)):                       # 这一句第一个「听对了」的字
            hit = mapping.get(at + off)
            if hit and hit[1] == 'eq':
                found = (off, times[hit[0]])
                break
        dp = dp_rows[k]['start'] if k < len(dp_rows) else None
        row = {'i': k, 'text': clause, 'dp_start': dp}
        if found is not None:
            off, t = found
            row.update(asr_start=round(t, 3), offset_chars=off,
                       delta=round(t - dp, 3) if dp is not None and off == 0 else None)
        else:
            row.update(asr_start=None, offset_chars=None, delta=None)
        rows.append(row)
        at += len(norm)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', default='small')
    ap.add_argument('--work', type=Path, default=ROOT / 'work/monalisa/asr')
    ap.add_argument('--out', type=Path, default=HERE / 'audio' / 'asr-probe.json')
    args = ap.parse_args(argv)
    story = json.loads((HERE / 'story.json').read_text(encoding='utf-8'))
    manifest = json.loads((HERE / 'audio' / 'manifest.json').read_text(encoding='utf-8'))
    receipts = {c['id']: c for c in manifest['clips']}
    dp_table = json.loads((HERE / 'audio' / 'clause-times.json').read_text(encoding='utf-8'))
    args.work.mkdir(parents=True, exist_ok=True)
    cache = vc.model_cache_dir(args.work); cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('HF_HOME', str(cache))
    from faster_whisper import WhisperModel
    model = WhisperModel(args.model, device='cpu', compute_type='int8', cpu_threads=4, download_root=str(cache))
    chapters = []
    for ch in story['chapters']:
        cid = ch['id']; path = HERE / 'audio' / f'{cid}.mp3'
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if receipts[cid]['text'] != ch['text'] or receipts[cid]['sha256'] != sha:
            raise SystemExit(f'{cid}: 配音清单与 story.json / 音频文件不一致，先修再探')
        segments, info = model.transcribe(str(path), language='zh', beam_size=5, vad_filter=False,
                                          word_timestamps=True, condition_on_previous_text=False)
        words, text = [], ''
        for seg in segments:
            text += seg.text
            for w in (seg.words or []):
                words.append({'word': w.word, 'start': round(w.start, 3), 'end': round(w.end, 3)})
        expected = vc.normalize(ch['text']); heard = vc.normalize(text)
        cer = vc.character_error_rate(expected, heard)
        clauses = clause_starts(ch['text'], words, dp_table[cid]['clauses'])
        deltas = [abs(c['delta']) for c in clauses if c.get('delta') is not None]
        chapters.append({'id': cid, 'sha256': sha, 'script_chars': len(expected), 'heard_chars': len(heard),
                         'character_error_rate': cer, 'match_coverage': vc.match_coverage(expected, heard),
                         'verdict': 'ok' if cer <= MAX_CER else 'needs_human_listen',
                         'diff': vc.diff_spans(expected, heard, limit=12), 'transcript': text,
                         'transcript_simplified': vc.to_simplified(text),
                         'clauses': clauses,
                         'max_start_delta': round(max(deltas), 3) if deltas else None,
                         'clauses_off': [c['i'] for c in clauses
                                         if c.get('delta') is not None and abs(c['delta']) > MAX_START_DELTA],
                         'words': words})
        print(f"{cid}: CER {cer:.3f}  heard {len(heard)}/{len(expected)}  "
              f"max |ASR-DP| {chapters[-1]['max_start_delta']}  off {chapters[-1]['clauses_off']}", flush=True)
        for d in chapters[-1]['diff']:
            print('    diff', d, flush=True)
    report = {'method': f'faster-whisper {args.model}，无 initial_prompt、无 VAD、word_timestamps；'
                        '转写对象为收紧后的配音 audio/N0x.mp3（不是成片）',
              'max_cer_allowed': MAX_CER, 'max_start_delta_allowed': MAX_START_DELTA,
              'max_cer': max(c['character_error_rate'] for c in chapters),
              'failing': [c['id'] for c in chapters if c['verdict'] != 'ok'],
              'clauses_off': {c['id']: c['clauses_off'] for c in chapters if c['clauses_off']},
              'chapters': chapters}
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('written', args.out, '| failing', report['failing'], '| clauses_off', report['clauses_off'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
