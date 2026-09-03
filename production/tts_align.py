#!/usr/bin/env python3
"""Align generate_speech chunk wavs to narration cues, slice per-cue mp3s,
rebuild spans from measured audio durations, emit narration_aligned.json."""
import json
import subprocess
import wave
import sys
from pathlib import Path

import numpy as np
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
TTS_SRC = ROOT / "work" / "tts_src"
PROD_TTS = ROOT / "work" / "production" / "tts"
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 16000
HOP = int(0.01 * SR)


def chars(text: str) -> int:
    return sum(1 for ch in text if "\u3400" <= ch <= "\u9fff" or ch.isalnum())


def decode(path: Path) -> np.ndarray:
    out = subprocess.run(
        [FF, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
         "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype="<i2").astype(np.float32) / 32768.0


def frame_mask(x: np.ndarray):
    n = len(x) // HOP
    frames = x[:n * HOP].reshape(n, HOP)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    floor = np.percentile(db, 15)
    thr = max(floor + 6.0, -45.0)
    act = db > thr
    k = np.ones(7)
    # two majority-filter passes (close then open) to remove single-frame spikes
    closed = (np.convolve(act.astype(np.float32), k, mode="same") >= 3)
    opened = np.convolve(closed.astype(np.float32), k, mode="same") >= 3
    return opened


def silence_candidates(mask: np.ndarray, a: int, b: int, min_sil=0.08):
    cuts = []
    i = a
    while i < b:
        if not mask[i]:
            j = i
            while j < b and not mask[j]:
                j += 1
            if (j - i) * 0.01 >= min_sil and i > a and j < b:
                cuts.append((i + j) / 2 * 0.01)
            i = j
        else:
            i += 1
    return cuts


def align_chunk(mask, a, b, groups, weights):
    """groups: list of (cue, [sent_idx...]); weights per sentence. Returns K-1 boundary times."""
    total = sum(weights)
    cum = np.concatenate([[0.0], np.cumsum(weights)])
    K = len(groups)
    if K < 2:
        return []
    t0, t1 = a * 0.01, b * 0.01
    bounds_exp = []
    for gi in range(K - 1):
        end_char = cum[groups[gi][1][-1] + 1]
        bounds_exp.append(t0 + (end_char / total) * (t1 - t0))
    all_cuts = silence_candidates(mask, a, b)
    cand_sets = []
    for j, exp in enumerate(bounds_exp):
        nxt = bounds_exp[j + 1] if j + 1 < K - 1 else t1
        gap = max(nxt - exp, 0.5)
        win = max(0.8, min(2.4, 0.5 * gap))
        cs = sorted({round(t, 3) for t in all_cuts if abs(t - exp) <= win})
        if not cs or (cs and min(abs(t - exp) for t in cs) > 0.3):
            cs = sorted(set(cs + [exp]))
        cand_sets.append(cs)
    # DP: dp[i] = cost of picking candidate i at boundary 0
    dp = [(t - bounds_exp[0]) ** 2 for t in cand_sets[0]]
    back = [[-1] * len(cand_sets[0])]
    for j in range(1, K - 1):
        cur = [float("inf")] * len(cand_sets[j])
        bk = [-1] * len(cand_sets[j])
        for i, t in enumerate(cand_sets[j]):
            for pi, pt in enumerate(cand_sets[j - 1]):
                if pt >= t - 0.28 or dp[pi] == float("inf"):
                    continue
                c = dp[pi] + (t - bounds_exp[j]) ** 2
                if c < cur[i]:
                    cur[i], bk[i] = c, pi
        if all(v == float("inf") for v in cur):  # relax monotonicity penalty
            for i, t in enumerate(cand_sets[j]):
                best = min(range(len(cand_sets[j - 1])),
                           key=lambda pi: (t - cand_sets[j - 1][pi], abs(t - bounds_exp[j])))
                cur[i] = dp[best] + (t - bounds_exp[j]) ** 2 + 1.0
                bk[i] = best
        dp = cur
        back.append(bk)
    end = int(np.argmin(dp))
    ts = []
    j = K - 2
    while j >= 0:
        ts.append(cand_sets[j][end])
        end = back[j][end]
        j -= 1
    return ts[::-1]


def trim_slice(mask, i0, i1, pad=3):
    seg = mask[i0:i1]
    idx = np.flatnonzero(seg)
    if len(idx) == 0:
        return i0, i1
    s = i0 + max(0, int(idx[0]) - pad)
    e = i0 + min(i1 - i0, int(idx[-1]) + pad + 1)
    return s, e


def write_mp3(x: np.ndarray, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp.wav")
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FF, "-y", "-v", "error", "-i", str(tmp), "-codec:a",
                    "libmp3lame", "-b:a", "128k", str(path)], check=True)
    tmp.unlink()


def main():
    spoken = json.load(open(TTS_SRC / "spoken.json"))
    narr = json.load(open(ROOT / "production" / "narration.json"))
    flat = [(si, ci, c) for si, s in enumerate(narr, 1) for ci, c in enumerate(s["cues"], 1)]
    assert len(flat) == 154

    durs = {}
    for ch in spoken["chunks"]:
        wav_path = TTS_SRC / ch["wav"]
        if not wav_path.exists():
            print(f"!! missing {wav_path.name} — skipped, rerun after generating it")
            continue
        sents = [t for t, _ in ch["sentences"]]
        marks = [m for _, m in ch["sentences"]]
        w = [max(chars(t), 4) for t in sents]
        # build groups
        groups = []  # (cue, [sent_idx]), order preserved
        pending_next = []
        for k, m in enumerate(marks):
            if isinstance(m, int):
                groups.append((m, pending_next + [k]))
                pending_next = []
            elif m == "prev":
                if groups:
                    groups[-1][1].append(k)
                else:
                    pending_next.append(k)
            elif m == "next":
                pending_next.append(k)
            elif m == "drop":
                groups.append((-1, [k]))  # virtual group: forces a boundary here, audio discarded later
        assert not pending_next, f"chunk {ch['id']}: dangling next markers"
        cues_in = [g[0] for g in groups if g[0] >= 0]
        assert cues_in == sorted(cues_in) and len(set(cues_in)) == len(cues_in)

        x = decode(wav_path)
        mask = frame_mask(x)
        ai = np.flatnonzero(mask)
        a, b = int(ai[0]), int(ai[-1]) + 1
        ts = align_chunk(mask, a, b, groups, w)
        bounds = [a] + [int(t * 100) for t in ts] + [b]
        print(f"chunk_{ch['id']:02d}: {len(sents)} sents -> {len(groups)} cues, "
              f"speech {(b-a)*0.01:.1f}s")
        for gi, (cue, sidx) in enumerate(groups):
            i0, i1 = trim_slice(mask, bounds[gi] + (6 if gi else 2), bounds[gi + 1] - 4)
            seg = x[i0 * HOP: min(i1 * HOP, len(x))]
            if cue < 0:
                continue
            si, ci, c = flat[cue]
            out = PROD_TTS / f"section_{si:02d}_cue_{ci:02d}_clip_01.mp3"
            write_mp3(seg, out)
            durs[cue] = (i1 - i0) * 0.01

    # coverage check
    missing = [i for i in range(154) if i not in durs]
    print(f"cues done {154-len(missing)}/154; missing idx: {missing}")
    if missing:
        json.dump(durs, open(TTS_SRC / "durations_partial.json", "w"))
        print("partial durations saved; rerun script after remaining chunks are generated")
        return

    json.dump(durs, open(TTS_SRC / "durations.json", "w"))
    # ---- rebuild spans from measured audio ----
    src_dur = 2351.11
    placed = []  # (in, out, cue)
    for cue in range(154):
        si, ci, c = flat[cue]
        Ain, Aout = c["clips"][0]
        A = durs[cue]
        span = max(2.0, A * 0.925 + 0.10)
        in_t = Ain
        out_t = in_t + span
        if out_t > src_dur - 0.2:
            in_t = max(0.0, src_dur - 0.2 - span)
            out_t = in_t + span
        placed.append([in_t, out_t, cue, si, ci])
    placed.sort(key=lambda r: (r[0], r[1]))
    # resolve overlaps greedily
    for i in range(1, len(placed)):
        pin, pout, pcue, _, _ = placed[i - 1]
        n = placed[i]
        if n[0] < pout + 0.05:
            n[0] = pout + 0.06
            n[1] = max(n[1], n[0] + durs[n[2]] * 0.62 + 0.05)
    bad = []
    for in_t, out_t, cue, si, ci in placed:
        f = durs[cue] / (out_t - in_t)
        if not 0.55 <= f <= 1.70:
            bad.append((cue, round(f, 3)))
    if bad:
        print("FACTOR VIOLATIONS:", bad)
        raise SystemExit(2)
    # rewrite narration
    ranges = {cue: (in_t, out_t) for in_t, out_t, cue, _, _ in placed}
    out_secs = []
    idx = 0
    for s in narr:
        cues = []
        for c in s["cues"]:
            in_t, out_t = ranges[idx]
            cues.append({"text": c["text"], "clips": [[round(in_t, 3), round(out_t, 3)]],
                         "clip_texts": [c["text"]]})
            idx += 1
        out_secs.append({"title": s["title"], "cues": cues})
    total = sum(durs[i] for i in range(154))
    span_total = sum(o - i_ for i_, o, *_ in placed)
    tgt = PROD_TTS.parent / "narration_aligned.json"
    json.dump(out_secs, open(tgt, "w"), ensure_ascii=False, indent=1)
    print(f"audio total {total:.1f}s, video total {span_total:.1f}s ({span_total/60:.2f}min)")
    print(f"WROTE {tgt}")
    facs = sorted((durs[c]/(ranges[c][1]-ranges[c][0]), c) for c in range(154))
    print("factor range:", round(facs[0][0],3), "..", round(facs[-1][0],3))


if __name__ == "__main__":
    main()
