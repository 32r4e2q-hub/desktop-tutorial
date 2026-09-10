#!/usr/bin/env python3
"""字幕对轨能量验证：文字零漏字是硬门，时间边界筛出短名单给人耳。

用法::

    python3 production/review_captions.py --film 交付/<片名>.mp4 \\
        --project production/<slug> --work work/<slug>/captions

它做两件事，性质完全不同：

1. **文字完整性（硬门）**：72 条字幕按章拼起来，去标点后必须与配音文本
   逐字一致。差一个字就非 0 退出——这是真正的 bug，不是"嫌疑"。
2. **边界筛查（软筛）**：20ms 窗能量包络 vs 字幕窗口。语音阈值取章内中位数
   -12dB（音乐 bed 通常比人声低 15dB 以上）；窗口内语音占比 < 0.5、
   边界前后 ±0.2s 没落在能量低谷（与窗内中位差 < 6dB）的条目进短名单，
   请人耳复听。字幕间隙里的语音记 info（设计 GAP/呼吸/混响尾），不进短名单。

能量法分不清念错字，只能看"这里有没有人声"——所以它筛的是边界，
替代不了逐字听检。dahlia 上它把"人工听 4 段约 110 秒"缩到了
"16 条约 33 秒 + N06 全章 30 秒"。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    import av
except ImportError as error:
    raise SystemExit(f"PyAV 未安装，跑不了字幕验证：{error}") from error

import numpy as np

RATE = 48000
HOP = 960                      # 20ms 窗
VOICE_MARGIN_DB = 12.0         # 语音阈值 = 章内中位数 - 12dB
EDGE_WINDOW_SECONDS = 0.2      # 边界前后看多宽找低谷
EDGE_DIP_DB = 6.0              # 边界低谷至少比窗内中位低这么多
MIN_SPEECH_FRACTION = 0.5      # 窗口内语音占比下限


def decode_mono(film: Path) -> np.ndarray:
    container = av.open(str(film))
    try:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=RATE)
        chunks = []
        for frame in container.decode(container.streams.audio[0]):
            for resampled in resampler.resample(frame):
                chunks.append(resampled.to_ndarray().reshape(-1))
        for resampled in resampler.resample(None):
            chunks.append(resampled.to_ndarray().reshape(-1))
    finally:
        container.close()
    return np.concatenate(chunks).astype(np.float64) / 32768.0 if chunks else np.zeros(0)


def window_db(pcm: np.ndarray) -> np.ndarray:
    pad = (-len(pcm)) % HOP
    blocks = np.pad(pcm, (0, pad)).reshape(-1, HOP)
    rms = np.sqrt(np.mean(blocks ** 2, axis=1))
    return 20 * np.log10(np.maximum(rms, 1e-9))


def index_at(seconds: float) -> int:
    return int(round(seconds * RATE / HOP))


def chapter_of(cue_start: float, narration: list[dict]) -> dict:
    """cue 按"下章起点"切分归属（别用 +2s 窗口，会把下章第一条划进来，
    dahlia 第一版脚本在这个坑里误报过"字幕多字"）。"""
    bounds = [row["start"] for row in narration] + [float("inf")]
    for i, row in enumerate(narration):
        if bounds[i] - 0.01 <= cue_start < bounds[i + 1]:
            return row
    return narration[-1]


def completeness(narration: list[dict], cues: list[dict]) -> list[dict]:
    """逐章：字幕拼合 vs 配音文本，逐字比对。"""
    def norm(text: str) -> str:
        return re.sub(r"[^\u3400-\u9fffA-Za-z0-9]", "", text)

    bounds = [row["start"] for row in narration] + [float("inf")]
    rows = []
    for i, chapter in enumerate(narration):
        owned = [c for c in cues if bounds[i] - 0.01 <= c["start"] < bounds[i + 1]]
        sub, voice = norm("".join(c["text"] for c in owned)), norm(chapter["text"])
        first_diff = None
        if sub != voice:
            for pos, (left, right) in enumerate(zip(sub, voice)):
                if left != right:
                    first_diff = {"at": pos,
                                  "subtitle": sub[max(0, pos - 8):pos + 8],
                                  "narration": voice[max(0, pos - 8):pos + 8]}
                    break
            if first_diff is None:
                first_diff = {"at": min(len(sub), len(voice)), "length_diff": len(sub) - len(voice)}
        rows.append({"id": chapter["id"], "cue_count": len(owned),
                     "subtitle_chars": len(sub), "narration_chars": len(voice),
                     "match": sub == voice, "first_diff": first_diff})
    return rows


def review(cues: list[dict], narration: list[dict], db: np.ndarray) -> list[dict]:
    edge_w = index_at(EDGE_WINDOW_SECONDS)
    results = []
    for ci, cue in enumerate(cues):
        start, end = float(cue["start"]), float(cue["end"])
        chapter = chapter_of(start, narration)
        lo, hi = index_at(chapter["start"]), index_at(chapter["end"])
        threshold = float(np.median(db[lo:hi])) - VOICE_MARGIN_DB
        active = db > threshold
        a, b = max(0, index_at(start)), min(len(db), index_at(end))
        speech_frac = float(active[a:b].mean()) if b > a else 0.0
        median = float(np.median(db[a:b])) if b > a else -99.0
        dip_s = median - float(db[max(0, a - edge_w):a + edge_w].min())
        dip_e = median - float(db[max(0, b - edge_w):min(len(db), b + edge_w)].min())
        flags = []
        if speech_frac < MIN_SPEECH_FRACTION:
            flags.append(f"窗口内语音占比仅{speech_frac:.2f}（疑似压静音/边界偏）")
        if dip_s < EDGE_DIP_DB:
            flags.append("起始边界不在能量低谷（疑似切在语音中间）")
        if dip_e < EDGE_DIP_DB:
            flags.append("结束边界不在能量低谷（疑似切在语音中间）")
        gap_note = None
        if ci + 1 < len(cues):
            nxt = index_at(float(cues[ci + 1]["start"]))
            if nxt > b + 2 and float(active[b:nxt].mean()) > 0.5:
                gap_note = (f"与下一条之间{nxt / 50 - b / 50:.2f}s 间隙内有语音"
                            "（多为设计 GAP/呼吸/混响尾，仅备查）")
        results.append({"cue": ci + 1, "chapter": chapter["id"],
                        "start": round(start, 2), "end": round(end, 2),
                        "text": cue["text"],
                        "speech_fraction": round(speech_frac, 2),
                        "edge_dip_start_db": round(dip_s, 1),
                        "edge_dip_end_db": round(dip_e, 1),
                        "flags": flags, "gap_note": gap_note})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--film", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True,
                        help="项目目录（读 delivery/narration-timing.json 等）")
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.film.is_file():
        raise SystemExit(f"找不到成片：{args.film}")
    args.work.mkdir(parents=True, exist_ok=True)
    delivery = args.project / "delivery"
    narration = json.loads((delivery / "narration-timing.json").read_text(encoding="utf-8"))
    cues = json.loads((delivery / "caption-timing.json").read_text(encoding="utf-8"))

    complete = completeness(narration, cues)
    broken = [row for row in complete if not row["match"]]
    if broken:
        for row in broken:
            print(f"文字不一致 {row['id']}：字幕 {row['subtitle_chars']} 字 vs "
                  f"配音 {row['narration_chars']} 字，首分歧 {row['first_diff']}")
        return 1

    pcm = decode_mono(args.film)
    rows = review(cues, narration, window_db(pcm))
    shortlist = [row["cue"] for row in rows if row["flags"]]

    out = args.work / "caption-energy-check.json"
    out.write_text(json.dumps(
        {"method": ("20ms 窗能量包络 vs 字幕窗口；语音阈值=章内中位-12dB；"
                    "边界±0.2s 最低能量与窗内中位比"),
         "completeness": complete, "cues": rows, "shortlist_cues": shortlist},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"字幕验证：{out}")
    print(f"  文字 {sum(r['subtitle_chars'] for r in complete)} 字逐字一致，零漏字")
    print(f"  短名单 {len(shortlist)} 条：{shortlist}" if shortlist else "  边界无警告")
    for row in rows:
        if row["flags"]:
            print(f"    #{row['cue']:>2} [{row['chapter']}] {row['start']:>7.2f}-"
                  f"{row['end']:>7.2f} {row['text']}")
    total = sum(rows[c - 1]["end"] - rows[c - 1]["start"] for c in shortlist)
    print(f"  人工复听约 {total:.0f} 秒（另建议听覆盖率最低的整章，见对轨报告）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
