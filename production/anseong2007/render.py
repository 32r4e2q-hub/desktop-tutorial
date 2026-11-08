#!/usr/bin/env python3
"""安城双尸案：144天，一台发动机 —— 180 秒成片渲染（1920×1080 / 24fps）。

输入：Agnes 2.5 Flash 生成的 30 段 720P 原片（results.json 里有 SHA 回执）+ voice-01 的 30 句配音。
输出：交付/<片名>_1080p24.mp4 + .ass/.srt + qa/ 报告与时间线接触表。

规则（与制作手册、setagaya/iguchi 教训一致）：
  * 原片逐字节核对回执（sha256 / bytes / 提示词与回执 payload 一致），不接受静帧兜底。
  * 原片多出的部分裁到镜头精确帧数；原片偏短时最多 12% 慢放补足，绝不冻结/补黑帧。
  * 一句话 = 一个 TTS 文件 = 一个镜头 = 一条字幕；只允许加速（≤1.15×），永不减速。
  * 声音只有旁白 + 按分镜 SFX 合成的环境声/拟音，没有 BGM；最后 1 秒数字静音。
  * 画面文字只出现在 S30（片名卡）；其余镜头只有烧录字幕。
  * S14 在暮色中压到全黑，黑场之后才出现铁锹挖土声（暗示，不呈现行凶）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import urllib.request
import wave
from io import BytesIO
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

FPS = 24
RATE = 48_000
DURATION = 180
TOTAL_FRAMES = FPS * DURATION
TOTAL_SAMPLES = RATE * DURATION
SILENT_TAIL_SECONDS = 1.0
VOICE_ID = "voice-01"
MAX_SPEEDUP = 1.15
MAX_SLOWMO = 1.12          # 原片偏短时允许的最大慢放倍数（>1 表示变慢）
VOICE_LEAD = 0.12          # 句子在镜头内的起点
VOICE_GUARD = 0.12         # 句子距离镜头结尾的最小留白
GOLD = "&H005FC9F4"        # ASS BGR：金色关键词
MAX_DELIVERY_BYTES = 95_000_000   # 成片要推回分支：GitHub 单文件上限 100MB
OUTPUT_NAME = "安城双尸案_144天一台发动机_三分钟_1080p24.mp4"
TITLE_MAIN = "安城双尸案"
TITLE_SUB = "144天，一台发动机"
SERIES_LINE = "迷案解码人 · 第九期"
AI_LABEL = "AI情景复原 · 非真实影像"

# 色彩分区：暖青（日常）→ 冷青（债务/犯罪）→ 冷蓝（侦破/山中）→ 埃及强暖 → 黄昏收尾。
GRADES = {
    "warm_teal": "eq=contrast=1.04:saturation=0.92:gamma=0.98,"
                 "colorbalance=rs=0.02:bs=0.04:rm=0.04:gm=0.01:bm=-0.03:rh=0.03:bh=-0.04",
    "cold_teal": "eq=contrast=1.06:saturation=0.82:gamma=0.96,"
                 "colorbalance=rs=-0.04:gs=0.01:bs=0.06:rm=-0.03:bm=0.03:rh=-0.02:bh=0.02",
    "cold_blue": "eq=contrast=1.05:saturation=0.78:gamma=0.97,"
                 "colorbalance=rs=-0.05:bs=0.08:rm=-0.04:bm=0.05:bh=0.02",
    "harsh_warm": "eq=contrast=1.08:saturation=1.0,"
                  "colorbalance=rs=0.05:bs=-0.06:rm=0.05:bm=-0.04:rh=0.04:bh=-0.05",
    "dusk": "eq=contrast=1.04:saturation=0.88,"
            "colorbalance=rs=0.02:bs=0.03:rm=0.04:bm=-0.02:rh=0.05:bh=-0.03",
}
FILM_FINISH = "noise=alls=5:allf=t,vignette=angle=PI/5"

# 每镜声音设计：(环境底, [(拟音, 起点占比, 强度), ...])。全部由滤波噪声/衰减分音合成，没有音乐。
SFX_PLAN: dict[str, tuple[str, list[tuple[str, float, float]]]] = {
    "S01": ("mountain_wind", [("engine", 0.0, 1.0)]),
    "S02": ("mountain_wind", [("shovel_stone", 0.55, 0.8)]),
    "S03": ("kitchen", [("chop", 0.12, 0.7), ("sizzle", 0.0, 0.8), ("chop", 0.55, 0.6)]),
    "S04": ("room", [("card_slap", 0.18, 0.9), ("card_slap", 0.52, 0.7), ("cough", 0.78, 0.5)]),
    "S05": ("kitchen", [("phone_ring", 0.05, 0.6), ("sizzle", 0.0, 0.5), ("door_close", 0.62, 0.9)]),
    "S06": ("rain", [("drips", 0.0, 0.7)]),
    "S07": ("office", [("clock", 0.0, 0.6), ("pen", 0.2, 0.6)]),
    "S08": ("office", [("phone_ring", 0.1, 0.5), ("paper", 0.6, 0.7)]),
    "S09": ("mountain_wind", [("march", 0.0, 0.8), ("grass", 0.3, 0.6)]),
    "S10": ("crowd", [("chime", 0.08, 0.45)]),
    "S11": ("room", [("card_slap", 0.2, 0.7), ("lighter", 0.6, 0.8)]),
    "S12": ("room", [("clock", 0.0, 0.6)]),
    "S13": ("mountain_wind", [("engine_approach", 0.0, 0.9)]),
    "S14": ("mountain_wind", [("birds_flush", 0.12, 1.0), ("dig", 0.66, 0.9)]),
    "S15": ("night_yard", [("gate_slide", 0.05, 0.9), ("murmur", 0.45, 0.5)]),
    "S16": ("workshop", [("impact_wrench", 0.05, 0.9), ("metal", 0.35, 0.8),
                         ("impact_wrench", 0.55, 0.8), ("metal", 0.82, 0.7)]),
    "S17": ("harbor", [("crane", 0.0, 0.8), ("horn", 0.6, 0.6)]),
    "S18": ("night_room", [("keypad", 0.15, 0.7), ("beep", 0.78, 0.7)]),
    "S19": ("room", [("tick_fast", 0.0, 0.6), ("paper", 0.4, 0.7), ("paper", 0.75, 0.6)]),
    "S20": ("rain", [("splash_steps", 0.0, 0.8)]),
    "S21": ("rain_tin", [("murmur", 0.25, 0.4)]),
    "S22": ("workshop_quiet", [("wipe", 0.1, 0.8), ("cut_to_silence", 0.72, 1.0)]),
    "S23": ("office", [("paper", 0.1, 0.6), ("pen_line", 0.35, 0.7)]),
    "S24": ("market", []),
    "S25": ("room", [("door_break", 0.05, 1.0), ("rush_steps", 0.2, 0.8), ("phone_drop", 0.7, 0.8)]),
    "S26": ("mountain_wind", [("shovel_stone", 0.25, 0.6), ("steps", 0.55, 0.6)]),
    "S27": ("mountain_morning", [("birdsong", 0.1, 0.5)]),
    "S28": ("kitchen_fade", [("sizzle", 0.0, 0.35)]),
    "S29": ("evening_wind", [("bag_seal", 0.35, 0.8)]),
    "S30": ("evening_wind", []),
}

BEDS = {  # (低切 Hz, 高切 Hz, RMS)
    "mountain_wind": (60, 1800, 0.020), "mountain_morning": (90, 2600, 0.012),
    "evening_wind": (70, 1600, 0.012), "kitchen": (120, 5000, 0.010),
    "kitchen_fade": (120, 4200, 0.008), "room": (90, 3500, 0.007),
    "night_room": (60, 2400, 0.005), "office": (110, 4500, 0.008),
    "rain": (300, 9000, 0.020), "rain_tin": (500, 10000, 0.022),
    "crowd": (180, 3200, 0.016), "night_yard": (60, 2600, 0.010),
    "workshop": (100, 6000, 0.012), "workshop_quiet": (100, 4000, 0.006),
    "harbor": (40, 1500, 0.020), "market": (160, 4200, 0.022),
}


# ───────────────────────────── helpers ─────────────────────────────

def run(command: list, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in command], check=True, capture_output=capture, text=capture)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def request_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def probe(path: Path) -> dict:
    return json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], text=True))


def video_stream(info: dict) -> dict:
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if v is None:
        raise RuntimeError("no video stream")
    return v


def count_frames(path: Path) -> int:
    data = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
        "-show_entries", "stream=nb_read_frames", "-of", "json", str(path)], text=True))
    return int(data["streams"][0]["nb_read_frames"])


def frame_rate(value: str | None) -> float:
    if not value:
        return 0.0
    if "/" in value:
        a, b = value.split("/", 1)
        return float(a) / float(b) if float(b) else 0.0
    return float(value)


def load_story() -> dict:
    return json.loads((HERE / "story.json").read_text(encoding="utf-8"))


def grade_for(story: dict, sid: str) -> str:
    for zone, ids in story["grade_zones"].items():
        if sid in ids:
            return zone
    raise ValueError(f"{sid} has no grade zone")


def validate_timeline(story: dict) -> None:
    shots = story["shots"]
    if [s["id"] for s in shots] != [f"S{i:02d}" for i in range(1, 31)]:
        raise ValueError("expected S01–S30 in order")
    cursor = 0
    for s in shots:
        if int(s["start"]) != cursor or int(s["duration"]) != int(s["seconds"]):
            raise ValueError(f"non-contiguous timeline at {s['id']}")
        cursor += int(s["duration"])
        grade_for(story, s["id"])
        if s["id"] not in SFX_PLAN:
            raise ValueError(f"{s['id']} has no SFX plan")
    if cursor != DURATION or story["target_duration"] != DURATION:
        raise ValueError(f"timeline is {cursor}s, expected {DURATION}s")
    if tuple(story["resolution"]) != (1920, 1080) or story["fps"] != FPS:
        raise ValueError("delivery must be 1920x1080 @ 24fps")


# ───────────────────────────── sources ─────────────────────────────

def load_results() -> dict:
    results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    if results.get("model") != "agnes-video-2.5-flash" or results.get("mode") != "reference":
        raise RuntimeError("only Agnes Video 2.5 Flash reference-mode receipts are accepted")
    return results


def check_receipt(shot: dict, row: dict) -> None:
    sid = shot["id"]
    p = row.get("request_payload") or {}
    if row.get("status") != "completed" or not row.get("sha256"):
        raise RuntimeError(f"{sid}: no completed receipt (status={row.get('status')})")
    if request_hash(p) != row.get("request_hash"):
        raise RuntimeError(f"{sid}: receipt payload does not match its request_hash")
    if p.get("prompt") != shot["prompt"] or p.get("seconds") != str(shot["duration"]) \
            or p.get("model") != "agnes-video-2.5-flash" or p.get("size") != "720P":
        raise RuntimeError(f"{sid}: clip was generated from a different prompt/duration than story.json")


def fetch_sources(results: dict, story: dict, sources: Path) -> None:
    """Artifact 缺失时的兜底：按 results.json 的 video_url 重新下载并核对 SHA。"""
    sources.mkdir(parents=True, exist_ok=True)
    for shot in story["shots"]:
        sid, row = shot["id"], results["shots"].get(shot["id"], {})
        target = sources / f"{sid}.mp4"
        if target.is_file() and sha256(target) == row.get("sha256"):
            continue
        url = row.get("video_url") or row.get("url")
        if not url:
            raise RuntimeError(f"{sid}: no source file and no video_url to fetch")
        with urllib.request.urlopen(url, timeout=120) as r, target.open("wb") as f:
            shutil.copyfileobj(r, f)
        if sha256(target) != row.get("sha256"):
            raise RuntimeError(f"{sid}: fetched bytes do not match the receipt SHA")
        print(f"fetched {sid}")


def collect_sources(results: dict, story: dict, candidates: list[Path], sources: Path) -> list[str]:
    """从 生成 artifact + 返工 artifact 里，按回执 SHA 为每镜挑出正确的那一份（字节不变地复制）。"""
    sources.mkdir(parents=True, exist_ok=True)
    found = {}
    for root in candidates:
        if not Path(root).is_dir():
            continue
        for f in sorted(Path(root).rglob("S[0-3][0-9].mp4")):
            found.setdefault(f.stem, []).append(f)
    missing = []
    for shot in story["shots"]:
        sid, want = shot["id"], results["shots"].get(shot["id"], {}).get("sha256")
        hit = next((f for f in found.get(sid, []) if want and sha256(f) == want), None)
        if hit:
            shutil.copyfile(hit, sources / f"{sid}.mp4")
        else:
            missing.append(sid)
    return missing


def verify_sources(story: dict, results: dict, sources: Path) -> dict:
    verified = {}
    for shot in story["shots"]:
        sid = shot["id"]
        row = results["shots"].get(sid, {})
        check_receipt(shot, row)
        src = sources / f"{sid}.mp4"
        if not src.is_file():
            raise RuntimeError(f"{sid}: source mp4 missing in {sources}")
        if sha256(src) != row["sha256"] or (row.get("bytes") and int(row["bytes"]) != src.stat().st_size):
            raise RuntimeError(f"{sid}: source bytes differ from the receipt")
        info = probe(src)
        v = video_stream(info)
        duration = float(v.get("duration") or info["format"]["duration"])
        frames = count_frames(src)
        fps = frame_rate(v.get("avg_frame_rate"))
        verified[sid] = {"sha256": row["sha256"], "width": int(v["width"]), "height": int(v["height"]),
                         "duration": duration, "frames": frames, "fps": fps}
    return verified


def timing_plan(shot: dict, src: dict) -> dict:
    """决定裁剪/慢放与快剪跳切。返回 setpts 因子与需要丢弃的帧区间。"""
    target = float(shot["duration"])
    target_frames = round(target * FPS)
    usable = src["duration"]
    if usable + 1e-3 >= target:
        stretch = 1.0
    else:
        stretch = target / usable
        if stretch > MAX_SLOWMO:
            raise RuntimeError(f"{shot['id']}: source {usable:.2f}s is too short for {target}s "
                               f"(would need {stretch:.2f}× slow motion; regenerate instead)")
    cuts: list[tuple[float, float]] = []
    if shot.get("fast_montage"):
        spare = usable - target
        if spare >= 0.4:
            # 两处跳切，各丢掉一小段原片，制造快剪节奏（每段 ≤0.5s）
            gap = min(0.5, spare / 2)
            for frac in (1 / 3, 2 / 3):
                at = usable * frac
                cuts.append((round(at, 3), round(at + gap, 3)))
    return {"stretch": round(stretch, 4), "cuts": cuts, "target_frames": target_frames}


def video_graph(story: dict, shot: dict, src: dict, plan: dict) -> str:
    sid = shot["id"]
    chain = []
    if plan["cuts"]:
        keep = "+".join(f"between(t,{a},{b})" for a, b in plan["cuts"])
        chain.append(f"select='not({keep})',setpts=N/FRAME_RATE/TB")
    if plan["stretch"] != 1.0:
        chain.append(f"setpts={plan['stretch']}*PTS")
    chain += ["fps=24",
              "scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos",
              "crop=1920:1080", "setsar=1", GRADES[grade_for(story, sid)], FILM_FINISH]
    if plan["cuts"]:
        # 跳切处 2 帧轻微闪白，强化快剪
        target = float(shot["duration"])
        for i, frac in enumerate((1 / 3, 2 / 3)):
            t = round(target * frac, 3)
            chain.append(f"eq=brightness=0.18:enable='between(t,{t},{t + 2 / FPS:.3f})'")
    d = float(shot["duration"])
    if sid == "S14":
        chain.append(f"fade=t=out:st={d * 0.44:.3f}:d={d * 0.2:.3f}")   # 2.2s 起 1s 压到全黑，之后黑场
    if sid == "S15":
        chain.append("fade=t=in:st=0:d=0.5")                             # 从黑场里亮起
    if sid == "S30":
        chain.append("fade=t=in:st=0:d=0.5")
        chain.append(f"fade=t=out:st={d - 1:.3f}:d=1")
    chain.append("format=yuv420p")
    return ",".join(chain)


def normalize_clip(story: dict, shot: dict, src_path: Path, src: dict, out: Path) -> dict:
    plan = timing_plan(shot, src)
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-v", "error", "-threads", "2", "-i", src_path,
         "-vf", video_graph(story, shot, src, plan), "-an",
         "-frames:v", plan["target_frames"], "-r", FPS, "-fps_mode", "cfr",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", out])
    got = count_frames(out)
    if got != plan["target_frames"]:
        raise RuntimeError(f"{shot['id']}: normalized clip has {got} frames, expected {plan['target_frames']}")
    return {"id": shot["id"], "grade": grade_for(story, shot["id"]), "source_seconds": round(src["duration"], 3),
            "target_seconds": shot["duration"], "frames": got, **plan}


# ───────────────────────────── voice ─────────────────────────────

def decode_audio(path: Path, tempo: float = 1.0) -> np.ndarray:
    af = ([f"atempo={tempo:.6f}"] if abs(tempo - 1) > 1e-4 else []) + ["aresample=48000"]
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-af", ",".join(af),
                                   "-ac", "2", "-ar", str(RATE), "-f", "f32le", "pipe:1"])
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()


def active_bounds(samples: np.ndarray) -> tuple[int, int]:
    mono = samples.mean(axis=1)
    hop = RATE // 100
    n = len(mono) // hop * hop
    rms = np.sqrt(np.mean(mono[:n].reshape(-1, hop) ** 2, axis=1))
    active = np.flatnonzero(rms >= max(0.0025, float(rms.max()) * 0.035))
    if not len(active):
        raise RuntimeError("no voice activity")
    return (max(0, int(active[0]) * hop - int(0.04 * RATE)),
            min(len(samples), (int(active[-1]) + 1) * hop + int(0.07 * RATE)))


def voice_rows(story: dict) -> dict:
    manifest = json.loads((HERE / "audio" / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("voice_id") != VOICE_ID:
        raise RuntimeError(f"narration must use the selected voice {VOICE_ID}")
    rows = {c["id"]: c for c in manifest["clips"]}
    for shot in story["shots"]:
        row = rows.get(shot["id"])
        if not row or row["text"] != shot["narration"] or row["target_start"] != shot["start"] \
                or row["target_duration"] != shot["duration"]:
            raise RuntimeError(f"{shot['id']}: manifest text/timing differs from story.json")
    return rows


def voice_plan(story: dict, strict: bool = True) -> list[dict]:
    """每句的语速因子（只加速）与可用窗口；--plan-only 也能跑。"""
    rows = voice_rows(story)
    plans = []
    for shot in story["shots"]:
        row = rows[shot["id"]]
        path = HERE / row["file"]
        if not path.is_file() or not row.get("sha256") or sha256(path) != row["sha256"]:
            if strict:
                raise RuntimeError(f"{shot['id']}: voice clip missing or stale (re-record with {VOICE_ID})")
            plans.append({"id": shot["id"], "status": "missing"})
            continue
        samples = decode_audio(path)
        a, b = active_bounds(samples)
        speech = (b - a) / RATE
        window = shot["duration"] - VOICE_LEAD - VOICE_GUARD
        if shot["id"] == "S30":
            window = shot["duration"] - VOICE_LEAD - SILENT_TAIL_SECONDS - 0.2
        tempo = 1.0 if speech <= window else speech / window * 1.005
        status = "ok" if tempo <= MAX_SPEEDUP + 0.005 else "too_long"
        if strict and status != "ok":
            raise RuntimeError(f"{shot['id']}: narration {speech:.2f}s needs {tempo:.2f}× (> {MAX_SPEEDUP}); rewrite the line")
        plans.append({"id": shot["id"], "status": status, "speech_seconds": round(speech, 3),
                      "window_seconds": round(window, 3), "tempo": round(tempo, 4)})
    return plans


def build_voice(story: dict) -> tuple[np.ndarray, list[dict], list[dict]]:
    plans = {p["id"]: p for p in voice_plan(story)}
    rows = voice_rows(story)
    voice = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    captions, report = [], []
    for shot in story["shots"]:
        sid, plan = shot["id"], plans[shot["id"]]
        samples = decode_audio(HERE / rows[sid]["file"], plan["tempo"])
        a, b = active_bounds(samples)
        clip = samples[a:b]
        start = int((shot["start"] + VOICE_LEAD) * RATE)
        limit = int((shot["start"] + shot["duration"] - VOICE_GUARD) * RATE)
        if start + len(clip) > min(limit, TOTAL_SAMPLES - RATE):
            raise RuntimeError(f"{sid}: narration crosses its shot boundary after tempo {plan['tempo']}")
        rms = float(np.sqrt(np.mean(clip.mean(axis=1) ** 2)))
        gain = min(1.8, max(0.65, 0.115 / max(rms, 1e-7)))
        clip = clip * gain
        peak = float(np.abs(clip).max())
        if peak > 0.82:
            clip *= 0.82 / peak
        fade = min(int(0.012 * RATE), len(clip) // 2)
        ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
        clip[:fade] *= ramp
        clip[-fade:] *= ramp[::-1]
        voice[start:start + len(clip)] += clip
        seconds = len(clip) / RATE
        cue = {"id": sid, "start": round(start / RATE + 0.04, 3), "end": round(start / RATE + seconds - 0.05, 3),
               "text": shot["subtitle"], "keywords": shot.get("highlight_keywords", [])}
        if captions and cue["start"] < captions[-1]["end"]:
            raise RuntimeError(f"subtitle overlap at {sid}")
        captions.append(cue)
        report.append({**plan, "gain": round(gain, 3), "cue_start": cue["start"], "cue_end": cue["end"]})
    return voice, captions, report


# ───────────────────────────── sound design ─────────────────────────────

def shaped_noise(n: int, rng: np.random.Generator, low: float, high: float) -> np.ndarray:
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    spec = np.fft.rfft(rng.standard_normal(n))
    hz = np.fft.rfftfreq(n, 1 / RATE)
    spec *= 1 / np.sqrt(1 + (hz / high) ** 6)
    spec *= (hz / low) / np.sqrt(1 + (hz / low) ** 2)
    spec *= 1 / np.sqrt(np.maximum(hz, 30))
    out = np.fft.irfft(spec, n=n).astype(np.float32)
    r = float(np.sqrt(np.mean(out ** 2)))
    return out / r if r > 1e-9 else out


def env_decay(n: int, k: float) -> np.ndarray:
    return np.exp(-np.linspace(0, k, n, dtype=np.float32))


def tone(freqs: list[float], seconds: float, decay: float = 0.0) -> np.ndarray:
    t = np.arange(int(seconds * RATE), dtype=np.float32) / RATE
    out = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
    if decay:
        out *= np.exp(-decay * t)
    return out.astype(np.float32)


def burst(rng, seconds, low, high, k=5.0):
    n = max(1, int(seconds * RATE))
    return shaped_noise(n, rng, low, high) * env_decay(n, k)


def event_audio(kind: str, rng: np.random.Generator, room: float) -> np.ndarray:
    """单个拟音事件（单声道），room = 该镜剩余秒数，长事件会被截短。"""
    r = rng
    if kind == "engine":
        n = int(room * RATE)
        t = np.arange(n) / RATE
        rumble = shaped_noise(n, r, 35, 260) * (0.7 + 0.3 * np.sin(2 * np.pi * 31 * t))
        return (rumble * np.linspace(1.0, 0.25, n)).astype(np.float32) * 0.9
    if kind == "engine_approach":
        n = int(room * RATE)
        t = np.arange(n) / RATE
        rumble = shaped_noise(n, r, 35, 300) * (0.7 + 0.3 * np.sin(2 * np.pi * 28 * t))
        return (rumble * np.linspace(0.1, 1.0, n) ** 1.5).astype(np.float32)
    if kind in ("shovel_stone", "dig"):
        hits = 1 if kind == "shovel_stone" else 4
        out = np.zeros(int(min(room, 0.72 * hits + 0.4) * RATE), dtype=np.float32)
        for i in range(hits):
            at = int((i * 0.72 + r.uniform(0, 0.06)) * RATE)
            piece = burst(r, 0.32, 300, 3500, 3.5)              # 铲进泥土的摩擦
            if kind == "shovel_stone":
                clink = tone([2100, 3370, 4710], 0.18, 25) * 0.5  # 碰到石头的金属声（非谐分音）
                piece[:len(clink)] += clink
            end = min(len(out), at + len(piece))
            out[at:end] += piece[:end - at]
        return out
    if kind == "chop":
        out = np.zeros(int(min(room, 1.6) * RATE), dtype=np.float32)
        for i in range(5):
            at = int((i * 0.29 + r.uniform(0, 0.05)) * RATE)
            hit = burst(r, 0.05, 600, 6000, 9)
            out[at:at + len(hit)] += hit[:max(0, len(out) - at)]
        return out
    if kind == "sizzle":
        n = int(room * RATE)
        crackle = shaped_noise(n, r, 2500, 11000) * 0.4
        pops = (r.random(n) < 0.0006).astype(np.float32) * r.uniform(0.5, 1.5, n)
        return (crackle + np.convolve(pops, env_decay(200, 6), "same")).astype(np.float32) * 0.6
    if kind in ("card_slap", "phone_drop"):
        return burst(r, 0.09, 400, 7000, 10) * (1.2 if kind == "phone_drop" else 1.0)
    if kind == "cough":
        return np.concatenate([burst(r, 0.16, 200, 2200, 6), np.zeros(int(0.08 * RATE), np.float32),
                               burst(r, 0.12, 200, 2200, 7) * 0.7])
    if kind == "phone_ring":
        seg = []
        for _ in range(2):
            trill = tone([1000], 0.9) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 20 * np.arange(int(0.9 * RATE)) / RATE)))
            seg += [trill * 0.5, np.zeros(int(0.45 * RATE), np.float32)]
        return np.concatenate(seg)[:int(room * RATE)].astype(np.float32)
    if kind in ("door_close", "door_break"):
        thump = burst(r, 0.35, 40, 600, 6) * 1.4
        if kind == "door_break":
            thump = thump + np.pad(burst(r, 0.25, 800, 8000, 8), (0, len(thump) - int(0.25 * RATE)))
        return thump
    if kind == "drips":
        n = int(room * RATE)
        out = np.zeros(n, np.float32)
        for at in sorted(r.uniform(0, room - 0.1, 9)):
            d = tone([r.uniform(1400, 2600)], 0.05, 70) * 0.4
            i = int(at * RATE)
            out[i:i + len(d)] += d[:n - i]
        return out
    if kind in ("clock", "tick_fast"):
        n = int(room * RATE)
        out = np.zeros(n, np.float32)
        step = 1.0 if kind == "clock" else 0.18
        t = 0.2
        while t < room - 0.05:
            c = burst(r, 0.012, 2000, 9000, 12) * 0.8
            i = int(t * RATE)
            out[i:i + len(c)] += c[:n - i]
            t += step * (1 if kind == "clock" else r.uniform(0.85, 1.0))
        return out
    if kind in ("pen", "pen_line"):
        n = int(min(room, 1.8 if kind == "pen" else 1.2) * RATE)
        t = np.arange(n) / RATE
        return (shaped_noise(n, r, 2500, 9000) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 3.1 * t)))
                * 0.35).astype(np.float32)
    if kind in ("paper", "grass", "wipe"):
        n = int(min(room, 0.7) * RATE)
        w = np.hanning(n).astype(np.float32)
        lo, hi = {"paper": (1500, 9000), "grass": (800, 6000), "wipe": (1200, 7000)}[kind]
        return shaped_noise(n, r, lo, hi) * w * 0.6
    if kind in ("march", "steps", "rush_steps", "splash_steps"):
        n = int(room * RATE)
        out = np.zeros(n, np.float32)
        step = {"march": 0.5, "steps": 0.55, "rush_steps": 0.22, "splash_steps": 0.42}[kind]
        t = 0.1
        while t < room - 0.2:
            if kind == "splash_steps":
                s = burst(r, 0.14, 700, 9000, 6) * 0.9
            else:
                s = burst(r, 0.08, 80, 1500, 8) * (1.2 if kind == "march" else 1.0)
            i = int(t * RATE)
            out[i:i + len(s)] += s[:n - i]
            t += step * r.uniform(0.92, 1.08)
        return out
    if kind == "chime":
        return tone([880], 0.5, 6) * 0.35
    if kind == "lighter":
        return np.concatenate([burst(r, 0.03, 2000, 9000, 10), burst(r, 0.4, 300, 2500, 2) * 0.5])
    if kind == "birds_flush":
        n = int(min(room, 1.6) * RATE)
        out = np.zeros(n, np.float32)
        for at in sorted(r.uniform(0, 1.0, 26)):
            f = burst(r, 0.04, 400, 3000, 6) * 0.7
            i = int(at * RATE)
            out[i:i + len(f)] += f[:n - i]
        return out * np.linspace(1, 0.3, n).astype(np.float32)
    if kind == "gate_slide":
        n = int(min(room, 1.4) * RATE)
        t = np.arange(n) / RATE
        return (shaped_noise(n, r, 150, 3000) * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t)) * np.hanning(n)).astype(np.float32)
    if kind == "murmur":
        n = int(min(room, 2.5) * RATE)
        t = np.arange(n) / RATE
        return (shaped_noise(n, r, 180, 1600) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 2.3 * t)))
                * np.hanning(n) * 0.5).astype(np.float32)
    if kind == "impact_wrench":
        n = int(min(room, 0.9) * RATE)
        t = np.arange(n) / RATE
        return (shaped_noise(n, r, 300, 6000) * (np.sin(2 * np.pi * 45 * t) > 0) * np.hanning(n)).astype(np.float32)
    if kind == "metal":
        return tone([523.0, 1311.0, 2187.0, 3401.0], 0.6, 7) * 0.6
    if kind == "crane":
        n = int(room * RATE)
        return shaped_noise(n, r, 30, 220) * 0.9
    if kind == "horn":
        n = int(min(room, 1.6) * RATE)
        h = tone([92.5, 185, 277.5], n / RATE) * np.hanning(n).astype(np.float32)
        return h * 0.5
    if kind == "keypad":
        out = []
        for f in ([697, 1209], [770, 1336], [852, 1477], [697, 1336], [941, 1336]):
            out += [tone(f, 0.08) * 0.35, np.zeros(int(0.17 * RATE), np.float32)]
        return np.concatenate(out)
    if kind == "beep":
        return tone([1650], 0.22) * np.hanning(int(0.22 * RATE)).astype(np.float32) * 0.45
    if kind == "birdsong":
        out = np.zeros(int(min(room, 4.0) * RATE), np.float32)
        for at in sorted(r.uniform(0, 3.5, 7)):
            n = int(0.09 * RATE)
            t = np.arange(n) / RATE
            f0 = r.uniform(3200, 4800)
            chirp = np.sin(2 * np.pi * (f0 * t + 9000 * t * t)) * np.hanning(n)
            i = int(at * RATE)
            out[i:i + n] += chirp[:max(0, len(out) - i)].astype(np.float32) * 0.25
        return out
    if kind == "bag_seal":
        n = int(0.5 * RATE)
        out = np.zeros(n, np.float32)
        for k in range(14):
            c = burst(r, 0.01, 2000, 9000, 12) * 0.6
            i = int(k * 0.033 * RATE)
            out[i:i + len(c)] += c[:n - i]
        return out
    if kind == "cut_to_silence":
        return np.zeros(1, np.float32)   # 处理见 build_sfx
    raise KeyError(kind)


def build_sfx(story: dict) -> tuple[np.ndarray, list[dict]]:
    rng = np.random.default_rng(2007_0301)
    out = np.zeros((TOTAL_SAMPLES, 2), dtype=np.float32)
    report = []
    for shot in story["shots"]:
        sid, d = shot["id"], float(shot["duration"])
        bed_kind, events = SFX_PLAN[sid]
        n = int(d * RATE)
        lo, hi, level = BEDS[bed_kind]
        seg = np.column_stack([shaped_noise(n, rng, lo, hi), shaped_noise(n, rng, lo, hi)]) * level
        if bed_kind == "kitchen_fade":
            seg *= np.linspace(1, 0.05, n, dtype=np.float32)[:, None]
        silence_from = None
        for kind, frac, strength in events:
            if kind == "cut_to_silence":
                silence_from = int(frac * n)
                continue
            at = int(frac * n)
            mono = event_audio(kind, rng, (n - at) / RATE)[: n - at] * 0.06 * strength
            pan = float(rng.uniform(-0.25, 0.25))
            seg[at:at + len(mono), 0] += mono * (1 - pan)
            seg[at:at + len(mono), 1] += mono * (1 + pan)
        if sid == "S14":
            # 画面 2.2–3.2s 压黑：鸟惊飞之后环境声随画面收掉，黑场里只剩铁锹声
            dark = int(0.44 * n)
            bed_fade = np.ones(n, np.float32)
            bed_fade[dark:] = np.linspace(1, 0.15, n - dark)
            seg *= bed_fade[:, None]
        if silence_from is not None:
            seg[silence_from:] = 0
        edge = int(0.03 * RATE)
        ramp = np.linspace(0, 1, edge, dtype=np.float32)[:, None]
        seg[:edge] *= ramp
        seg[-edge:] *= ramp[::-1]
        s = int(shot["start"] * RATE)
        out[s:s + n] += seg
        report.append({"id": sid, "bed": bed_kind, "events": [e[0] for e in events], "script_sfx": shot["sfx"]})
    out[-RATE:] = 0
    return out, report


def duck(sfx: np.ndarray, voice: np.ndarray) -> np.ndarray:
    """旁白出声时环境声压低约 6dB（50ms 攻击 / 300ms 释放的平滑包络）。"""
    mono = np.abs(voice).max(axis=1)
    hop = RATE // 100
    n = len(mono) // hop
    env = (mono[:n * hop].reshape(n, hop).max(axis=1) > 0.02).astype(np.float32)
    smooth = np.convolve(env, np.ones(30) / 30, "same")
    gain = 1 - 0.5 * np.clip(smooth * 1.5, 0, 1)
    gain = np.repeat(gain, hop)
    gain = np.pad(gain, (0, len(sfx) - len(gain)), constant_values=1)
    return sfx * gain[:, None]


def write_wav(path: Path, audio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.round(np.clip(audio, -0.98, 0.98) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


# ───────────────────────────── subtitles ─────────────────────────────

def ass_clock(t: float) -> str:
    c = int(round(t * 100))
    h, c = divmod(c, 360000)
    m, c = divmod(c, 6000)
    s, c = divmod(c, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def srt_clock(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_subtitle(text: str, limit: int = 22) -> list[str]:
    lines, rest = [], text.strip()
    while len(rest) > limit:
        floor = int(limit * 0.5)
        breaks = [i + 1 for i, ch in enumerate(rest[:limit]) if i + 1 >= floor and ch in "，；：、。？！"]
        cut = max(breaks) if breaks else limit
        lines.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        lines.append(rest)
    return lines


def highlight(text: str, keywords: list[str]) -> str:
    keys = sorted((k for k in keywords if k), key=len, reverse=True)
    out, i = [], 0
    while i < len(text):
        hit = next((k for k in keys if text.startswith(k, i)), None)
        if hit:
            out.append("{\\c" + GOLD + "&\\b1}" + hit + "{\\rCaption}")
            i += len(hit)
        else:
            ch = text[i]
            out.append({"{": "（", "}": "）", "\\": "/"}.get(ch, ch))
            i += 1
    return "".join(out)


def write_subtitles(captions: list[dict], story: dict, ass_path: Path, srt_path: Path) -> None:
    s30 = next(s for s in story["shots"] if s["id"] == "S30")
    t0, t1 = s30["start"] + 0.5, DURATION - SILENT_TAIL_SECONDS - 0.05
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 2",
        "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "", "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,Noto Sans CJK SC,58,&H00FFFFFF,&H0000FFFF,&H00000000,&H7F000000,1,0,0,0,100,100,1,0,1,3.4,1.2,2,120,120,70,1",
        f"Style: Title,Noto Serif CJK SC,120,{GOLD},&H0000FFFF,&H00101010,&H99000000,1,0,0,0,100,100,6,0,1,4,3,5,100,100,0,1",
        "Style: TitleSub,Noto Sans CJK SC,54,&H00F2F2F2,&H0000FFFF,&H00101010,&H99000000,0,0,0,0,100,100,4,0,1,3,2,5,100,100,0,1",
        "Style: Small,Noto Sans CJK SC,26,&H00E6E6E6,&H0000FFFF,&H00000000,&H7F000000,0,0,0,0,100,100,1,0,1,2,0.8,9,48,48,36,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        # 画面文字只放在 S30：片名卡 + 系列名 + AI 复原标注
        f"Dialogue: 3,{ass_clock(t0)},{ass_clock(t1)},Title,,0,0,0,,{{\\fad(500,700)\\pos(960,420)}}{TITLE_MAIN}",
        f"Dialogue: 3,{ass_clock(t0 + 0.3)},{ass_clock(t1)},TitleSub,,0,0,0,,{{\\fad(500,700)\\pos(960,540)}}{TITLE_SUB}",
        f"Dialogue: 3,{ass_clock(t0 + 0.6)},{ass_clock(t1)},TitleSub,,0,0,0,,{{\\fad(500,700)\\pos(960,620)\\fs34\\c{GOLD}&}}{SERIES_LINE}",
        f"Dialogue: 4,{ass_clock(t0)},{ass_clock(t1)},Small,,0,0,0,,{{\\fad(300,500)}}{AI_LABEL}",
    ]
    srt = []
    for i, cue in enumerate(captions, 1):
        parts = split_subtitle(cue["text"])
        body = r"\N".join(highlight(p, cue["keywords"]) for p in parts)
        lines.append(f"Dialogue: 1,{ass_clock(cue['start'])},{ass_clock(cue['end'])},Caption,,0,0,0,,{{\\fad(60,80)}}{body}")
        srt.append(f"{i}\n{srt_clock(cue['start'])} --> {srt_clock(cue['end'])}\n" + "\n".join(parts) + "\n")
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    srt_path.write_text("\n".join(srt), encoding="utf-8")


# ───────────────────────────── QA ─────────────────────────────

def frame_at(video: Path, t: float):
    from PIL import Image
    data = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video),
                                    "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"])
    return Image.open(BytesIO(data)).convert("RGB")


def contact_sheet(video: Path, story: dict, target: Path) -> None:
    from PIL import Image, ImageDraw
    tw, th, cols = 320, 180, 6
    sheet = Image.new("RGB", (tw * cols, th * 5), (8, 10, 14))
    draw = ImageDraw.Draw(sheet)
    for i, shot in enumerate(story["shots"]):
        im = frame_at(video, shot["start"] + shot["duration"] * 0.5).resize((tw, th))
        x, y = (i % cols) * tw, (i // cols) * th
        sheet.paste(im, (x, y))
        draw.rectangle((x, y, x + 46, y + 20), fill=(0, 0, 0))
        draw.text((x + 6, y + 4), shot["id"], fill=(244, 201, 95))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, quality=88)


def tail_silence(video: Path) -> dict:
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-sseof", "-1", "-i", str(video), "-vn", "-ac", "2",
                                   "-ar", str(RATE), "-t", "1", "-f", "f32le", "pipe:1"])
    s = np.frombuffer(raw, dtype="<f4")
    rms, peak = float(np.sqrt(np.mean(s ** 2))), float(np.abs(s).max())
    if rms > 0.001 or peak > 0.01:
        raise RuntimeError(f"final second not silent (rms {rms:.5f}, peak {peak:.5f})")
    return {"rms": round(rms, 6), "peak": round(peak, 6)}


# ───────────────────────────── main ─────────────────────────────

def plan_only() -> dict:
    story = load_story()
    validate_timeline(story)
    vp = voice_plan(story, strict=False)
    results_path = HERE / "results.json"
    receipts = {}
    if results_path.is_file():
        rows = json.loads(results_path.read_text(encoding="utf-8")).get("shots", {})
        receipts = {sid: rows.get(sid, {}).get("status", "missing") for sid in (s["id"] for s in story["shots"])}
    report = {"timeline": "S01–S30 contiguous, 180 s", "voice": vp, "receipts": receipts,
              "voice_ready": sum(1 for p in vp if p["status"] == "ok"),
              "voice_too_long": [p["id"] for p in vp if p["status"] == "too_long"],
              "clips_completed": sum(1 for v in receipts.values() if v == "completed")}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def render(sources: Path, work: Path, output: Path, fetch: bool, candidates: list[Path] | None = None) -> dict:
    story = load_story()
    validate_timeline(story)
    results = load_results()
    if candidates:
        missing = collect_sources(results, story, candidates, sources)
        print(f"collected {30 - len(missing)}/30 clips from artifacts; missing {missing}")
    if fetch:
        fetch_sources(results, story, sources)
    verified = verify_sources(story, results, sources)
    voice, captions, voice_report = build_voice(story)   # 先查配音，免得白渲染 30 段

    norm_dir = work / "normalized"
    clips, entries = [], ["ffconcat version 1.0"]
    for shot in story["shots"]:
        out = norm_dir / f"{shot['id']}.mp4"
        clips.append(normalize_clip(story, shot, sources / f"{shot['id']}.mp4", verified[shot["id"]], out))
        entries.append("file '" + str(out.resolve()) + "'")
        print(f"normalized {shot['id']}: {clips[-1]}")
    concat = work / "clips.ffconcat"
    concat.write_text("\n".join(entries) + "\n", encoding="utf-8")

    sfx, sfx_report = build_sfx(story)
    mix = voice + duck(sfx, voice)
    mix[-RATE:] = 0
    peak = float(np.abs(mix).max())
    if peak > 0.95:
        mix *= 0.95 / peak
    mix_path = work / "final-mix.wav"
    write_wav(mix_path, mix)

    output.parent.mkdir(parents=True, exist_ok=True)
    ass, srt = output.with_suffix(".ass"), output.with_suffix(".srt")
    write_subtitles(captions, story, ass, srt)
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", concat, "-i", mix_path,
         "-vf", f"ass={ass.as_posix()}", "-map", "0:v:0", "-map", "1:a:0",
         "-frames:v", TOTAL_FRAMES, "-r", FPS, "-fps_mode", "cfr",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "3800k", "-bufsize", "7600k",
         "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", RATE, "-ac", 2, "-t", DURATION, "-movflags", "+faststart",
         "-metadata", f"title={story['title']}", "-metadata", "comment=AI情景复原，非真实影像；案件回顾",
         output])
    info = probe(output)
    v = video_stream(info)
    frames = count_frames(output)
    duration = float(info["format"]["duration"])
    if (int(v["width"]), int(v["height"]), frames) != (1920, 1080, TOTAL_FRAMES) or abs(duration - DURATION) > 0.05:
        raise RuntimeError(f"delivery gate failed: {v['width']}x{v['height']} {frames}f {duration:.3f}s")
    if output.stat().st_size > MAX_DELIVERY_BYTES:
        raise RuntimeError(f"delivery is {output.stat().st_size/1e6:.1f} MB; GitHub rejects files over 100 MB")
    tail = tail_silence(output)
    sheet = HERE / "qa" / "final_timeline.jpg"
    contact_sheet(output, story, sheet)
    report = {"title": story["title"], "output": output.name, "bytes": output.stat().st_size,
              "delivery": {"width": 1920, "height": 1080, "fps": FPS, "frames": frames,
                           "duration_seconds": round(duration, 3)},
              "voice_id": VOICE_ID, "voice": voice_report, "clips": clips, "sound_design": sfx_report,
              "music": False, "silent_tail": tail, "silent_tail_seconds": SILENT_TAIL_SECONDS,
              "on_screen_text": "subtitles + S30 title card only", "timeline_contact_sheet": str(sheet.relative_to(ROOT)),
              "human_review": "pending full playback"}
    (HERE / "qa").mkdir(exist_ok=True)
    (HERE / "qa" / "render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                   encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("output", "delivery", "silent_tail")}, ensure_ascii=False))
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan-only", action="store_true", help="只校验时间线与配音窗口，不需要原片")
    ap.add_argument("--sources", type=Path, default=ROOT / "work" / "anseong2007" / "sources")
    ap.add_argument("--work", type=Path, default=ROOT / "work" / "anseong2007" / "render")
    ap.add_argument("--output", type=Path, default=HERE / "交付" / OUTPUT_NAME)
    ap.add_argument("--from", dest="candidates", type=Path, action="append", default=[],
                    help="artifact 下载目录（可多次）：按回执 SHA 为每镜挑选原片")
    ap.add_argument("--fetch", action="store_true", help="原片不全时按 results.json 的 video_url 下载（核对 SHA）")
    args = ap.parse_args()
    if args.plan_only:
        report = plan_only()
        return 0 if not report["voice_too_long"] else 1
    render(args.sources, args.work, args.output, args.fetch, args.candidates)
    return 0


if __name__ == "__main__":
    sys.exit(main())
