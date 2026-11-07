#!/usr/bin/env python3
"""扫描 audio/voice02/Sxx.mp3，逐镜量出语音活动窗口，写 audio/manifest.json 并报告"解说与片段等长"。

一镜一句：mp3 ↔ story.shots[Sxx] ↔ 字幕一条。镜头时长服从旁白：只允许轻微加速（<=1.18x），绝不慢放、绝不截字。
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import av
import numpy as np

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
VOICE_DIR = "voice02"
LEAD = 0.25      # 镜头开始后语音起点
TAIL = 0.20      # 镜头结束前留白
MAX_TEMPO = 1.18


def decode_mono(path: Path, rate=16000) -> np.ndarray:
    c = av.open(str(path)); r = av.AudioResampler(format="s16", layout="mono", rate=rate); out = []
    for fr in c.decode(audio=0):
        for o in r.resample(fr):
            out.append(o.to_ndarray().ravel())
    c.close()
    return np.concatenate(out).astype(np.float64) / 32768.0


def active_window(path: Path, rate=16000, thresh=0.01):
    x = decode_mono(path, rate); w = rate // 100
    e = np.sqrt(np.convolve(x ** 2, np.ones(w) / w, "same"))
    idx = np.where(e > thresh)[0]
    return len(x) / rate, idx[0] / rate, idx[-1] / rate


def main() -> int:
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    clips, rows, missing = [], [], []
    for shot in story["shots"]:
        sid = shot["id"]; f = AUDIO / VOICE_DIR / f"{sid}.mp3"
        if not f.is_file():
            missing.append(sid); continue
        raw, a, b = active_window(f)
        active = b - a + 0.08
        avail = shot["duration"] - LEAD - TAIL
        need = max(1.0, active / avail)
        status = "over" if need > MAX_TEMPO else "needs-speedup" if need > 1.0 else ("fit" if active / avail >= .85 else "ok" if active / avail >= .65 else "short")
        clips.append({
            "id": sid, "file": f"audio/{VOICE_DIR}/{sid}.mp3", "text": shot["narration"], "tts_text": shot["tts_text"],
            "voice_id": story["voice"], "narration_id": sid, "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "target_start": shot["start"], "target_duration": shot["duration"],
            "raw_duration": round(raw, 3), "active_start": round(a - 0.03, 3), "active_end": round(b + 0.05, 3),
            "tempo": round(need, 4), "fit": status,
        })
        rows.append((sid, shot["duration"], len(shot["tts_text"]), round(active, 2), round(active / avail, 2), round(need, 2), status))
    manifest = {"voice": story["voice"], "alignment": "one-clip-one-shot-one-caption", "slowdown_allowed": False,
                "planned": 30, "completed": len(clips), "missing": missing, "clips": clips}
    (AUDIO).mkdir(parents=True, exist_ok=True)
    (AUDIO / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 解说词与片段等长 · 实测表\n", "| 镜头 | 时长 | 字数 | 语音活动(s) | 占比 | 加速 | 判定 |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]:.0%} | {r[5]}x | {r[6]} |" for r in rows]
    lines.append(f"\n已录 {len(clips)}/30；缺：{', '.join(missing) or '无'}")
    (AUDIO / "narration-fit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    bad = [r for r in rows if r[6] == "over"]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
