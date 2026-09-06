"""Measure pauses in the narration MP3s and derive subtitle line boundaries.

Writes build/vo_pauses.json and build/subtitle_bounds.json (consumed by assemble.py).
A boundary snaps to the nearest measured pause when one exists near the expected position;
otherwise (the speaker read across the line break) the proportional estimate is used.
"""
import json, os, re, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assemble as A  # noqa: E402

NUM = {"1888": 5, "2014": 4, "Jack the Ripper": 4, "DNA": 3, "31": 3, "43": 3, "29": 3, "27": 3, "45": 3,
       "30": 2, "11": 2, "13": 2, "9": 1, "8": 1}


def weight(line):
    s, w = line, 0.0
    for k, v in sorted(NUM.items(), key=lambda kv: -len(kv[0])):
        c = s.count(k)
        w += c * v
        s = s.replace(k, "")
    for ch in s:
        if ch in "，、；：":
            w += 1.4
        elif ch in "。？！——":
            w += 2.2
        elif re.match(r"[\u4e00-\u9fff]", ch):
            w += 1.0
        elif ch.isalnum():
            w += 0.6
    return w


def load_mono(path, sr=16000):
    raw = subprocess.run([A.FFMPEG, "-v", "quiet", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768, sr


def pauses(path, hop=0.02, thr_db=-38, min_gap=0.22):
    x, sr = load_mono(path)
    h = int(sr * hop)
    n = len(x) // h
    e = np.array([np.sqrt(np.mean(x[i * h:(i + 1) * h] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(e + 1e-9)
    sil = db < np.percentile(db, 95) + thr_db
    runs, i = [], 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            if (j - i) * hop >= min_gap:
                runs.append((i * hop, j * hop))
            i = j
        else:
            i += 1
    onset = next((i * hop for i in range(n) if not sil[i]), 0.0)
    end = next((i * hop for i in range(n - 1, -1, -1) if not sil[i]), n * hop)
    return runs, onset, end, n * hop


def align(lines, onset, end, gaps, tol=1.3, fallback_pen=0.9):
    mids = [(a + b) / 2 for a, b in gaps if a > onset + 0.3 and b < end - 0.3]
    w = np.array([weight(l) for l in lines])
    cum = np.cumsum(w) / w.sum()
    targets = onset + (end - onset) * cum[:-1]
    # DP over boundaries: candidates = nearby pause mids (cost = distance²) or the target itself (penalty)
    best = {(): 0.0}
    for t in targets:
        nxt = {}
        for path, cost in best.items():
            last = path[-1] if path else onset
            cands = [(m, (m - t) ** 2) for m in mids if abs(m - t) <= tol and m > last + 0.4]
            cands.append((float(t), fallback_pen ** 2))
            for c, cc in cands:
                if c <= last + 0.4:
                    continue
                key = path + (round(c, 3),)
                if key not in nxt or nxt[key] > cost + cc:
                    nxt[key] = cost + cc
        best = nxt
    path = min(best.items(), key=lambda kv: kv[1])[0]
    return [onset] + list(path) + [end], targets


def main():
    os.makedirs(A.BUILD, exist_ok=True)
    pinfo, bounds = {}, {}
    for vo in sorted(A.NARRATION):
        runs, onset, end, dur = pauses(os.path.join(A.VO, f"{vo}.mp3"))
        inner = [(round(a, 2), round(b, 2)) for a, b in runs if a > 0.05 and b < dur - 0.05]
        pinfo[vo] = {"onset": round(onset, 2), "end": round(end, 2), "dur": round(dur, 2), "pauses": inner}
        b, t = align(A.NARRATION[vo], onset, end, runs)
        bounds[vo] = [round(x, 2) for x in b]
        print(vo, "bounds", bounds[vo], " est", [round(x, 2) for x in t])
    json.dump(pinfo, open(os.path.join(A.BUILD, "vo_pauses.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(bounds, open(os.path.join(A.BUILD, "subtitle_bounds.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
