"""Automated QC for the final MP4: container/stream sanity, full decode, black/frozen-frame detection,
A/V duration match, audio level & silence checks, narration alignment spot checks."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import numpy as np


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(ffmpeg, path):
    out = run([ffmpeg, "-hide_banner", "-i", path]).stderr
    info = {}
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    if m:
        info["duration"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    v = re.search(r"Stream #0:(\d+).*?: Video: (\w+).*?, (\d{2,5})x(\d{2,5})[, \[].*? (\d+(?:\.\d+)?) fps", out)
    if v:
        info["vcodec"], info["width"], info["height"], info["fps"] = v.group(2), int(v.group(3)), int(v.group(4)), float(v.group(5))
    a = re.search(r"Stream #0:(\d+).*?: Audio: (\w+).*? (\d+) Hz, (\w+)", out)
    if a:
        info["acodec"], info["arate"], info["alayout"] = a.group(2), int(a.group(3)), a.group(4)
    info["pix_fmt"] = "yuv420p" if "yuv420p" in out else None
    return info, out


def decode_check(ffmpeg, path):
    """Full decode; returns (ok, video_frames, audio_time, stderr)."""
    r = run([ffmpeg, "-hide_banner", "-v", "error", "-xerror", "-i", path, "-f", "null", "-"])
    ok = r.returncode == 0 and not r.stderr.strip()
    return ok, r.stderr


def black_and_freeze(ffmpeg, path):
    r = run([ffmpeg, "-hide_banner", "-nostats", "-i", path, "-vf", "blackdetect=d=0.4:pix_th=0.06,freezedetect=n=0.001:d=1.5", "-an", "-f", "null", "-"])
    blacks = re.findall(r"black_start:(\d+\.?\d*) black_end:(\d+\.?\d*) black_duration:(\d+\.?\d*)", r.stderr)
    freezes = re.findall(r"freeze_start: (\d+\.?\d*)", r.stderr)
    freeze_ends = re.findall(r"freeze_end: (\d+\.?\d*)", r.stderr)
    return [(float(a), float(b), float(c)) for a, b, c in blacks], [float(f) for f in freezes], [float(f) for f in freeze_ends]


def audio_stats(ffmpeg, path):
    r = run([ffmpeg, "-hide_banner", "-nostats", "-i", path, "-vn", "-af", "astats=metadata=1:reset=0,silencedetect=n=-45dB:d=2.0,ebur128=peak=true", "-f", "null", "-"])
    err = r.stderr
    peak = re.search(r"Peak level dB: (-?\d+\.?\d*)", err)
    rms = re.search(r"RMS level dB: (-?\d+\.?\d*)", err)
    lufs_all = re.findall(r"I:\s+(-?\d+\.?\d*) LUFS", err)
    lufs = lufs_all[-1] if lufs_all else None
    silences = re.findall(r"silence_start: (-?\d+\.?\d*)", err)
    sil_end = re.findall(r"silence_end: (-?\d+\.?\d*) \| silence_duration: (-?\d+\.?\d*)", err)
    return dict(peak_db=float(peak.group(1)) if peak else None, rms_db=float(rms.group(1)) if rms else None,
                lufs=float(lufs) if lufs else None, silences=[(float(s), float(e), float(d)) for s, (e, d) in zip(silences, sil_end)])


def stream_durations(ffmpeg, path):
    """Decode each stream separately to measure their true lengths."""
    def last_time(args):
        r = run([ffmpeg, "-hide_banner", "-i", path, *args, "-f", "null", "-"])
        m = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", r.stderr)
        if not m:
            return 0.0
        h, mi, s = m[-1]
        return int(h) * 3600 + int(mi) * 60 + float(s)
    return last_time(["-an"]), last_time(["-vn"])


def frame_count(ffmpeg, path):
    r = run([ffmpeg, "-hide_banner", "-i", path, "-map", "0:v:0", "-an", "-f", "null", "-"])
    m = re.findall(r"frame=\s*(\d+)", r.stderr)
    return int(m[-1]) if m else 0


def narration_alignment(ffmpeg, path, shots, tol=0.15):
    """Decode the film's audio and verify each narration actually starts within `tol` seconds of its scheduled time,
    by detecting the first onset above threshold after a quiet-ish gap."""
    r = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", path, "-vn", "-f", "f32le", "-ac", "1", "-ar", "8000", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, np.float32)
    sr = 8000
    # narration band (300-3000 Hz) short-time energy
    from scipy import signal
    b, a = signal.butter(2, [300 / (sr / 2), 3000 / (sr / 2)], "band")
    y = signal.lfilter(b, a, x)
    win = int(sr * 0.05)
    e = np.convolve(y * y, np.ones(win) / win, mode="same")
    e_db = 10 * np.log10(e + 1e-10)
    results = []
    for s in shots:
        if not s["vo"]:
            continue
        # expected onset = scheduled placement + the leading silence baked into the VO file itself
        rv = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", s["vo_path"], "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"], capture_output=True)
        v = np.frombuffer(rv.stdout, np.float32)
        nz = np.where(np.abs(v) > 0.02)[0]
        head = (nz[0] / sr) if len(nz) else 0.0
        sched = s["start"] + s["lead"] + head
        # the film track around the expected onset: compare narration-band energy just before vs just after
        pre = e_db[int((sched - 0.35) * sr):int((sched - 0.05) * sr)]
        post = e_db[int((sched + 0.02) * sr):int((sched + 0.35) * sr)]
        if len(pre) == 0 or len(post) == 0:
            results.append((s["name"], round(sched, 2), None, False))
            continue
        rise = float(np.percentile(post, 70) - np.percentile(pre, 50))
        # search the precise onset: first sample after sched-0.25 that exceeds the pre-median by 9 dB
        i0 = int((sched - 0.25) * sr)
        seg = e_db[i0:int((sched + 0.6) * sr)]
        idx = np.where(seg > np.median(pre) + 9)[0]
        onset = (i0 + idx[0]) / sr if len(idx) else None
        ok = onset is not None and abs(onset - sched) <= tol + 0.2 and rise > 3.0
        results.append((s["name"], round(sched, 2), round(onset, 2) if onset else None, ok))
    return results


def _py(o):
    """Recursively convert numpy scalars/arrays to plain python for json."""
    if isinstance(o, dict):
        return {k: _py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_py(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    return o


def count_frames(ffmpeg_bin, path):
    """Decode a video file fully and return the number of frames (0 on error)."""
    try:
        r = subprocess.run([ffmpeg_bin, "-hide_banner", "-nostats", "-i", path, "-map", "0:v:0", "-f", "null", "-"], capture_output=True, text=True, timeout=600)
    except Exception:
        return 0
    m = re.findall(r"frame=\s*(\d+)", r.stderr)
    return int(m[-1]) if m else 0


def main(ffmpeg, path, shots=None, expect_dur=None, report_path=None):
    problems = []
    info, raw = probe(ffmpeg, path)
    if not os.path.exists(path) or os.path.getsize(path) < 1_000_000:
        problems.append("file missing or suspiciously small")
    if info.get("vcodec") != "h264":
        problems.append(f"video codec is {info.get('vcodec')}, expected h264")
    if info.get("acodec") != "aac":
        problems.append(f"audio codec is {info.get('acodec')}, expected aac")
    if info.get("pix_fmt") != "yuv420p":
        problems.append("pixel format is not yuv420p (compatibility risk)")
    if (info.get("width"), info.get("height")) != (1280, 720):
        problems.append(f"resolution {info.get('width')}x{info.get('height')} != 1280x720")
    ok, err = decode_check(ffmpeg, path)
    if not ok:
        problems.append("decode errors: " + err.strip()[:400])
    vdur, adur = stream_durations(ffmpeg, path)
    if abs(vdur - adur) > 0.25:
        problems.append(f"A/V duration mismatch: video {vdur:.2f}s vs audio {adur:.2f}s")
    if expect_dur and abs(vdur - expect_dur) > 0.3:
        problems.append(f"video duration {vdur:.2f}s differs from planned {expect_dur:.2f}s")
    nframes = frame_count(ffmpeg, path)
    blacks, fz_start, fz_end = black_and_freeze(ffmpeg, path)
    # allowed: fade-in at very start / fade-out at the very end
    for (s, e, d) in blacks:
        if not (s < 0.2 or e > vdur - 0.6):
            problems.append(f"black segment at {s:.2f}-{e:.2f}s ({d:.2f}s)")
    for f in fz_start:
        if f > 0.5 and f < vdur - 3.0:
            problems.append(f"frozen picture from {f:.2f}s")
    astat = audio_stats(ffmpeg, path)
    if astat["peak_db"] is None or astat["peak_db"] > -0.1:
        problems.append(f"audio peak too hot / unreadable: {astat['peak_db']}")
    if astat["rms_db"] is not None and astat["rms_db"] < -30:
        problems.append(f"audio too quiet (RMS {astat['rms_db']} dB)")
    for (s, e, d) in astat["silences"]:
        if s > 1.0 and e < vdur - 1.0:
            problems.append(f"audio silence {s:.2f}-{e:.2f}s ({d:.1f}s)")
    align = narration_alignment(ffmpeg, path, shots) if shots else []
    for name, sched, onset, ok_ in align:
        if not ok_:
            problems.append(f"narration {name} scheduled at {sched}s, detected onset {onset}")
    report = dict(file=path, size_mb=round(os.path.getsize(path) / 1e6, 2) if os.path.exists(path) else 0, info=info, video_dur=round(vdur, 3),
                  audio_dur=round(adur, 3), frames=nframes, black_segments=blacks, freeze_starts=fz_start, audio=astat, narration_alignment=align,
                  problems=problems, passed=not problems)
    if report_path:
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(_py(report), fh, ensure_ascii=False, indent=2)
    return _py(report)
