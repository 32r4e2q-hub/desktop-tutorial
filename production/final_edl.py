#!/usr/bin/env python3
"""剪辑决策（EDL）：为每句解说确定画面起止点。

规则：
1. 起点固定在被审核过的画面对应时间码上（内容锚点，不挪动）。
2. 终点优先吸附到电影真实镜头切换点（scenes.csv），保证切在镜头之间。
3. 若吸附导致画面变速超出 [0.70, 1.32]（会听感变快/变慢），改为在
   旁白节拍处卡拍切（1.0 倍速），并保留句间停顿缓冲。
4. 每句输出时长 = 语音时长 + 0.15s 停顿（GAP）。
"""
import csv
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARR = ROOT / "production" / "narration.json"
DURS = ROOT / "work" / "tts_src" / "durations.json"
TTS = ROOT / "work" / "production" / "tts"
OUT = ROOT / "work" / "production" / "narration_aligned.json"
SRC_DUR = 2351.11
MIN_AUDIO = 1.5
GAP = 0.15
FF = "/usr/local/bin/ffmpeg"


def wav_dur(p):
    out = subprocess.run([FF, "-hide_banner", "-i", str(p)],
                         capture_output=True, text=True).stderr
    m = re.search(r"Duration:\s*(\d+):(\d+):([0-9.]+)", out)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def load_bounds():
    lines = (ROOT / "production" / "scenes.csv").read_text(encoding="utf-8-sig").splitlines()
    h = next(i for i, l in enumerate(lines) if l.startswith("Scene Number,"))
    scenes = [(float(r["Start Time (seconds)"]), float(r["End Time (seconds)"]))
              for r in csv.DictReader(lines[h:])]
    return sorted({s for s, _ in scenes} | {scenes[-1][1]})


def main():
    narr = json.load(open(NARR, encoding="utf-8"))
    flat = [(si, ci, c) for si, s in enumerate(narr, 1) for ci, c in enumerate(s["cues"], 1)]
    assert len(flat) == 154
    speech = {int(k): float(v) for k, v in json.load(open(DURS, encoding="utf-8")).items()}
    bounds = load_bounds()

    A = []
    for i in range(154):
        si, ci = flat[i][0], flat[i][1]
        wav = TTS / f"section_{si:02d}_cue_{ci:02d}_clip_01.wav"
        a = wav_dur(wav)
        if a < MIN_AUDIO:
            tmp = wav.with_suffix(".pad.wav")
            subprocess.run([FF, "-y", "-v", "error", "-i", str(wav),
                            "-af", f"apad=whole_dur={MIN_AUDIO}", "-t", f"{MIN_AUDIO}",
                            str(tmp)], check=True)
            tmp.replace(wav)
            a = MIN_AUDIO
        A.append(a)
    out_durs = [a + GAP for a in A]

    spans, modes = [], []
    for i in range(154):
        si, ci, c = flat[i]
        Ain, Aout = c["clips"][0]
        nextAin = flat[i + 1][2]["clips"][0][0] if i + 1 < 154 else SRC_DUR
        od = out_durs[i]
        lo = Ain + 0.6
        hi_cap = min(Aout, nextAin - 0.10)
        cand = [b for b in bounds if lo - 0.01 <= b <= hi_cap + 0.01]
        best, bestscore, bestmode = None, float("inf"), "beat"
        for b in cand:
            f = od / (b - Ain)
            if 0.70 <= f <= 1.32:
                score = abs((b - Ain) - od)
                if score < bestscore:
                    bestscore, best, bestmode = score, b, "boundary"
        if best is None:
            for b in bounds:
                if hi_cap < b <= nextAin + 0.01:
                    if 0.70 <= od / (b - Ain) <= 1.32:
                        best, bestmode = b, "boundary-extend"
                        break
        if best is None:
            best = min(Ain + od, hi_cap)
            best = max(best, Ain + 0.8)
            bestmode = "beat"
        spans.append((Ain, best))
        modes.append(bestmode)

    bad = [i for i in range(154) if not 0.60 <= out_durs[i] / (spans[i][1] - spans[i][0]) <= 1.45]
    if bad:
        print("FACTOR VIOLATIONS:", bad)
        raise SystemExit(2)

    out = []
    idx = 0
    for s in narr:
        cues = []
        for c in s["cues"]:
            a, b = spans[idx]
            cues.append({"text": c["text"], "clips": [[round(a, 3), round(b, 3)]],
                         "clip_texts": [c["text"]]})
            idx += 1
        out.append({"title": s["title"], "cues": cues})

    from collections import Counter
    onb = sum(1 for a, b in spans if min(abs(b - x) for x in bounds) < 0.02)
    facs = sorted((out_durs[i] / (spans[i][1] - spans[i][0]), i) for i in range(154))
    total = sum(out_durs)
    print("mode:", dict(Counter(modes)))
    print(f"ends on shot boundary: {onb}/154 | beat cuts: {modes.count('beat')}")
    print(f"retime factor {facs[0][0]:.3f}..{facs[-1][0]:.3f} median {facs[77][0]:.3f}")
    print(f"video {total:.1f}s = {total/60:.2f} min")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
