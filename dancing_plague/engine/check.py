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
    v = re.search(r"Stream #0:(\d+).*?: Video: (\w+).*?, (\d{2,5})x(\d{2,5})[ ,\[].*? (\d+(?:\.\d+)?) fps", out)
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
    """A/V-sync check: for every narration, cross-correlate the ORIGINAL voice-over file with the film's audio
    around its scheduled start and report the measured offset (must be within `tol` seconds)."""
    sr = 8000

    def decode(p, ss=None, t=None):
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error"]
        if ss is not None:
            cmd += ["-ss", f"{ss:.3f}", "-t", f"{t:.3f}"]
        cmd += ["-i", p, "-vn", "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"]
        r = subprocess.run(cmd, capture_output=True)
        return np.frombuffer(r.stdout, np.float32)

    from scipy import signal
    b, a = signal.butter(2, [300 / (sr / 2), 3000 / (sr / 2)], "band")
    film = decode(path)
    results = []
    for s in shots:
        if not s["vo"]:
            continue
        sched = s["start"] + s["lead"]
        ref = decode(s["vo_path"])[: int(6.0 * sr)]          # first 6 s of the narration
        ref = signal.lfilter(b, a, ref)
        i0 = max(0, int((sched - 1.0) * sr))
        i1 = min(len(film), int((sched + 1.0) * sr) + len(ref))
        seg = signal.lfilter(b, a, film[i0:i1])
        if len(seg) <= len(ref) or np.abs(ref).max() < 1e-4:
            results.append((s["name"], round(sched, 2), None, False))
            continue
        # normalised cross-correlation via FFT
        n = len(seg) + len(ref)
        R = np.fft.rfft(ref, n)
        S = np.fft.rfft(seg, n)
        cc = np.fft.irfft(S * np.conj(R), n)[: len(seg) - len(ref) + 1]
        lag = int(np.argmax(cc))
        onset = (i0 + lag) / sr
        # confidence: correlation peak vs. energy
        peak = cc[lag] / (np.linalg.norm(ref) * np.linalg.norm(seg[lag:lag + len(ref)]) + 1e-9)
        ok = abs(onset - sched) <= tol and peak > 0.2
        results.append((s["name"], round(sched, 2), round(onset, 3), bool(ok), round(float(peak), 3)))
    return results


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
    for row in align:
        name, sched, onset, ok_ = row[:4]
        if not ok_:
            problems.append(f"narration {name} scheduled at {sched}s, measured onset {onset} (corr {row[4] if len(row) > 4 else 'n/a'})")
    report = dict(file=path, size_mb=round(os.path.getsize(path) / 1e6, 2) if os.path.exists(path) else 0, info=info, video_dur=round(vdur, 3),
                  audio_dur=round(adur, 3), frames=nframes, black_segments=blacks, freeze_starts=fz_start, audio=astat, narration_alignment=align,
                  problems=problems, passed=not problems)
    def _py(o):
        import numpy as _np
        if isinstance(o, dict):
            return {k: _py(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_py(v) for v in o]
        if isinstance(o, _np.generic):
            return o.item()
        return o

    report = _py(report)
    if report_path:
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
    return report
