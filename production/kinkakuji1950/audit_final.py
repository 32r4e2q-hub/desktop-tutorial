#!/usr/bin/env python3
"""Final audit of the delivered Kinkakuji film.

Everything here measures the *delivered file*, not the plan: container specs, shot-boundary
registration, per-frame geometric/blocking distortion outliers, freezes, real-motion proof,
narration-versus-window equality, subtitle/voice alignment, chapter-to-chapter brightness
continuity, audio levels, plus text-level compliance (safety words, on-screen-text rule).

Run:  python3 production/kinkakuji1950/audit_final.py
Out:  production/kinkakuji1950/qa/final-audit.json
      production/kinkakuji1950/qa/final-audit.md
      production/kinkakuji1950/qa/audit/montage.jpg
      production/kinkakuji1950/qa/audit/frames/Sxx_mid.jpg
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FILM = ROOT / "交付" / "金阁寺纵火案_美为何被烧成灰_三分钟_带声音.mp4"
SRT = ROOT / "交付" / "金阁寺纵火案_字幕.srt"
QA = HERE / "qa"
AUDIT_DIR = QA / "audit"
FRAMES = AUDIT_DIR / "frames"

EXPECTED = {"width": 1920, "height": 1080, "fps": 24.0, "duration": 180.0, "frames": 4320,
            "sample_rate": 48000, "channels": 2}
SCAN_FPS = 8.0
SCAN_W, SCAN_H = 320, 180
BLACK_MEAN = 18.0
FREEZE_EPS = 0.6          # mean |diff| below this counts as a frozen sample
MOTION_FLOOR = 1.2        # every shot must move more than this on average
FIT_CEILING = 1.55        # narration_fit policy: speech may need at most 1.55x
CUT_SEARCH = 0.32         # 0.3s 交叉叠化会把差分峰值推后，容差按叠化时长给
LOCAL_FLOOR = 1.0         # 单块（8x8）平均差超过它就算“画面里有东西在动”


def probe(path: Path) -> dict:
    import av
    with av.open(str(path)) as container:
        v = container.streams.video[0]
        out = {"width": v.codec_context.width, "height": v.codec_context.height,
               "fps": float(v.average_rate) if v.average_rate else 0.0,
               "vcodec": v.codec_context.name, "duration_seconds": float(container.duration or 0) / 1e6,
               "frames": int(v.frames or 0)}
        if container.streams.audio:
            a = container.streams.audio[0]
            out.update(acodec=a.codec_context.name, sample_rate=a.codec_context.sample_rate,
                       channels=a.codec_context.channels)
        else:
            out.update(acodec=None, sample_rate=0, channels=0)
        return out


def scan_gray(path: Path) -> tuple[np.ndarray, float]:
    """Decode the whole film once as a small grayscale stack for per-frame metrics."""
    import av
    frames = []
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        acc, n = 0.0, 0
        step = max(1, round(float(stream.average_rate) / SCAN_FPS))
        for frame in container.decode(stream):
            if n % step == 0:
                img = frame.to_ndarray(format="gray")
                if img.shape[:2] != (SCAN_H, SCAN_W):
                    img = np.asarray(Image.fromarray(img).resize((SCAN_W, SCAN_H), Image.BILINEAR))
                frames.append(img.astype(np.float32))
            n += 1
    return np.stack(frames), SCAN_FPS


def laplacian_var(img: np.ndarray) -> float:
    lap = (-4 * img[1:-1, 1:-1] + img[:-2, 1:-1] + img[2:, 1:-1]
           + img[1:-1, :-2] + img[1:-1, 2:])
    return float(lap.var())


def blockiness(img: np.ndarray, block: int = 16) -> float:
    """Mean |gradient| on a block grid minus the same inside blocks.

    A rising gap means block/quantisation seams or a squeezed, re-encoded frame.
    """
    gx = np.abs(np.diff(img, axis=1))
    cols = np.arange(gx.shape[1])
    seam = gx[:, (cols + 1) % block == 0].mean() if gx.shape[1] > block else 0.0
    inner = gx[:, (cols + 1) % block != 0].mean() if gx.shape[1] > block else 0.0
    return float(seam - inner)


def smear_ratio(img: np.ndarray) -> float:
    """Horizontal smearing (a classic video-model failure) shows up as lost vertical detail."""
    gx = float(np.abs(np.diff(img, axis=1)).mean())
    gy = float(np.abs(np.diff(img, axis=0)).mean())
    return float(gy / (gx + 1e-6))


def per_frame_metrics(stack: np.ndarray) -> dict:
    n = len(stack)
    sharp = np.array([laplacian_var(f) for f in stack])
    block = np.array([blockiness(f) for f in stack])
    smear = np.array([smear_ratio(f) for f in stack])
    luma = stack.mean(axis=(1, 2))
    clip_hi = np.array([float((f >= 250).mean()) for f in stack])
    clip_lo = np.array([float((f <= 5).mean()) for f in stack])
    diff = np.array([0.0] + [float(np.abs(stack[i] - stack[i - 1]).mean()) for i in range(1, n)])
    local = np.zeros(n, dtype=np.float32)
    for i in range(1, n):
        d = np.abs(stack[i] - stack[i - 1])
        bh, bw = d.shape[0] // 8, d.shape[1] // 8
        local[i] = d[:bh * 8, :bw * 8].reshape(8, bh, 8, bw).mean(axis=(1, 3)).max()
    return {"sharp": sharp, "block": block, "smear": smear, "luma": luma,
            "clip_hi": clip_hi, "clip_lo": clip_lo, "diff": diff, "local": local}


def mad_flags(values: np.ndarray, multiple: float = 5.0, floor: float = 0.0,
              two_sided: bool = False) -> np.ndarray:
    med = float(np.median(values))
    mad = float(np.median(np.abs(values - med))) * 1.4826
    if mad < 1e-9:
        return np.zeros(len(values), dtype=bool)
    if two_sided:  # 清晰度既要抓“过锐的噪点闪”，也要抓“糊掉/融化的崩坏”
        return np.abs(values - med) > max(multiple * mad, floor)
    return (values > med + max(multiple * mad, floor))


def find_cuts(diff: np.ndarray, fps: float) -> list[float]:
    """Local maxima clearly above the local background = hard cuts in the delivered film."""
    cuts = []
    win = int(round(fps * 1.0))
    for i in range(1, len(diff) - 1):
        lo, hi = max(1, i - win), min(len(diff) - 1, i + win)
        neighbourhood = np.delete(diff[lo:hi + 1], i - lo)
        base = float(np.median(neighbourhood)) if len(neighbourhood) else 0.0
        peak = float(diff[i])
        if peak > max(3.0, base * 2.5) and peak >= diff[i - 1] and peak >= diff[i + 1]:
            if not cuts or (i / fps) - cuts[-1] > 0.4:
                cuts.append(i / fps)
    return cuts


def parse_srt(path: Path) -> list[dict]:
    def stamp(value: str) -> float:
        h, m, rest = value.split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
        lines = [line for line in block.splitlines() if line.strip()]
        if len(lines) < 2 or "-->" not in lines[1]:
            continue
        start, end = [stamp(x.strip()) for x in lines[1].split("-->")]
        cues.append({"index": int(lines[0].strip()) if lines[0].strip().isdigit() else len(cues) + 1,
                     "start": round(start, 3), "end": round(end, 3),
                     "lines": [line.strip() for line in lines[2:]]})
    return cues


def audio_levels(path: Path) -> dict:
    import av
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        chunks = []
        for frame in container.decode(stream):
            arr = frame.to_ndarray().astype(np.float32)
            if arr.ndim == 2:
                arr = arr.mean(axis=0)
            chunks.append(arr.reshape(-1))
    samples = np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
    if np.issubdtype(samples.dtype, np.floating) and np.abs(samples).max() > 1.5:
        samples = samples / 32768.0
    rms = float(np.sqrt(np.mean(samples ** 2)) + 1e-12)
    return {"rms_dbfs": round(20 * np.log10(rms + 1e-12), 2),
            "peak_dbfs": round(float(20 * np.log10(np.abs(samples).max() + 1e-12)), 2),
            "samples": int(samples.size)}


def grab_stills(path: Path, times: list[float], out_dir: Path, width: int = 960) -> list[str]:
    """One frame per shot, scaled for review."""
    import av
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    wanted = sorted(range(len(times)), key=lambda i: times[i])
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        cursor = 0
        container.seek(int(times[wanted[0]] * 1e6), any_frame=False, backward=True)
        for frame in container.decode(stream):
            if cursor >= len(wanted):
                break
            t = float(frame.pts * stream.time_base) if frame.pts is not None else 0.0
            idx = wanted[cursor]
            if t >= times[idx] - 1e-3:
                h = round(width * frame.height / frame.width)
                img = Image.fromarray(frame.to_ndarray(format="rgb24")).resize((width, h), Image.LANCZOS)
                dest = out_dir / f"S{idx + 1:02d}_mid.jpg"
                img.save(dest, quality=88)
                written.append(str(dest.relative_to(ROOT)))
                cursor += 1
    return written


def montage(frames: list[Path], dest: Path, cols: int = 6) -> None:
    thumbs = [Image.open(p).resize((320, 180), Image.LANCZOS) for p in frames if p.is_file()]
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 320, rows * 180), "black")
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * 320, (i // cols) * 180))
    dest.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest, quality=90)


def main() -> int:
    if not FILM.is_file():
        raise SystemExit(f"missing film: {FILM}")
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    shots = story["shots"]
    split = json.loads((QA / "narration-split.json").read_text(encoding="utf-8"))["clips"]
    split_by_id = {row["id"]: row for row in split}

    report: dict = {"film": str(FILM.relative_to(ROOT)), "failures": [], "warnings": []}
    fails, warns = report["failures"], report["warnings"]

    # 1. container ---------------------------------------------------------
    meta = probe(FILM)
    report["container"] = meta
    if (meta["width"], meta["height"]) != (EXPECTED["width"], EXPECTED["height"]):
        fails.append(f"分辨率 {meta['width']}x{meta['height']} 不是 1920x1080")
    if abs(meta["fps"] - EXPECTED["fps"]) > 1e-6:
        fails.append(f"帧率 {meta['fps']} 不是 24")
    if abs(meta["duration_seconds"] - EXPECTED["duration"]) > 0.04:
        fails.append(f"时长 {meta['duration_seconds']}s 不是 180s")
    if meta["frames"] not in (0, EXPECTED["frames"]):
        fails.append(f"帧数 {meta['frames']} 不是 4320")
    if meta["sample_rate"] != EXPECTED["sample_rate"] or meta["channels"] != EXPECTED["channels"]:
        fails.append(f"音轨 {meta['sample_rate']}Hz/{meta['channels']}ch 不是 48kHz 立体声")

    # 2. per-frame distortion scan ----------------------------------------
    stack, fps = scan_gray(FILM)
    m = per_frame_metrics(stack)
    report["scan"] = {"fps": fps, "samples": int(len(stack))}
    times = np.arange(len(stack)) / fps

    black = [round(float(t), 2) for t, lum in zip(times, m["luma"]) if lum < BLACK_MEAN]
    unexpected_black = [t for t in black if t > 0.5 and all(abs(t - (s["start"] + s["duration"])) > 0.5
                                                           for s in shots) and not (175.0 <= t <= 180.0)]
    report["black_frames"] = {"count": len(black), "unexpected": unexpected_black[:12]}
    if unexpected_black:
        fails.append(f"出现 {len(unexpected_black)} 处非计划的纯黑帧：{unexpected_black[:6]}")

    freeze_runs, start = [], None
    for i, d in enumerate(m["diff"]):
        if d < FREEZE_EPS and i > 0:
            start = i if start is None else start
        elif start is not None:
            if (i - start) / fps >= 1.0:
                freeze_runs.append({"start": round(start / fps, 2), "end": round(i / fps, 2)})
            start = None
    report["freeze_runs"] = freeze_runs
    long_freeze = [row for row in freeze_runs if row["end"] - row["start"] >= 2.5]
    if long_freeze:
        fails.append(f"画面冻结 ≥2.5s：{long_freeze}")

    # distortion outliers (geometry melt / smear / block seams)
    suspect = {}
    for key, threshold, floor, two_sided in (("sharp", 5.0, 0.0, True), ("block", 5.0, 0.6, False),
                                             ("smear", 5.0, 0.15, False), ("diff", 6.0, 0.0, False)):
        flag = mad_flags(m[key], threshold, floor, two_sided)
        idx = np.where(flag & (times > 0.2))[0]
        if len(idx):
            suspect[key] = [round(float(times[i]), 2) for i in idx[:20]]
    report["distortion_suspects"] = suspect
    if suspect.get("sharp"):
        warns.append(f"清晰度异常帧 {len(suspect['sharp'])} 处（可能是运动模糊/画面崩坏）：{suspect['sharp'][:8]}")
    if suspect.get("block"):
        warns.append(f"块状/压缩痕异常帧 {len(suspect['block'])} 处：{suspect['block'][:8]}")
    if suspect.get("smear"):
        warns.append(f"横向拖影异常帧 {len(suspect['smear'])} 处：{suspect['smear'][:8]}")

    # 3. shot registration + per-shot motion ------------------------------
    cuts = find_cuts(m["diff"], fps)
    report["cuts_detected"] = [round(c, 2) for c in cuts]
    planned = [s["start"] + s["duration"] for s in shots[:-1]]
    unmatched = []
    for boundary in planned:
        if not any(abs(cut - boundary) <= CUT_SEARCH for cut in cuts):
            unmatched.append(round(boundary, 2))
    report["boundaries"] = {"planned": [round(b, 2) for b in planned],
                            "unmatched": unmatched,
                            "extra_cuts": [round(c, 2) for c in cuts
                                           if all(abs(c - b) > CUT_SEARCH for b in planned)]}
    if unmatched:
        fails.append(f"{len(unmatched)} 个镜头切换点没有在成片里找到：{unmatched[:8]}")
    extras = report["boundaries"]["extra_cuts"]
    if extras:
        warns.append(f"成片里出现了分镜表之外的多余剪辑点：{extras[:8]}")

    per_shot = []
    for shot in shots:
        lo = int(shot["start"] * fps)
        hi = int((shot["start"] + shot["duration"]) * fps)
        seg = slice(lo, min(hi, len(stack)))
        seg_diff = m["diff"][seg][1:]
        entry = {
            "id": shot["id"], "window": [shot["start"], shot["start"] + shot["duration"]],
            "motion_mean": round(float(seg_diff.mean()) if seg_diff.size else 0.0, 2),
            "motion_max": round(float(seg_diff.max()) if seg_diff.size else 0.0, 2),
            "luma_mean": round(float(m["luma"][seg].mean()), 1),
            "sharp_mean": round(float(m["sharp"][seg].mean()), 1),
            "local_motion": round(float(m["local"][seg][1:].mean()), 2) if seg_diff.size else 0.0,
            "moving_frame_share": round(float((m["local"][seg][1:] > LOCAL_FLOOR).mean()), 2) if seg_diff.size else 0.0,
        }
        # 慢镜头常常整体帧间差很低，只要画面里始终有局部在动（烛火、涟漪、衣角），
        # 就不是“静态图加推拉”。两者都低才算真缺陷。
        if entry["motion_mean"] < MOTION_FLOOR and entry["moving_frame_share"] < 0.30:
            fails.append(f"{shot['id']} 全局帧间差 {entry['motion_mean']} 且局部在动帧仅 "
                         f"{entry['moving_frame_share']:.0%}，疑似静帧/几乎不动")
        elif entry["motion_mean"] < MOTION_FLOOR:
            warns.append(f"{shot['id']} 运动偏慢（帧间差 {entry['motion_mean']}），但 "
                         f"{entry['moving_frame_share']:.0%} 的帧有局部运动，按慢镜头保留")
        per_shot.append(entry)
    report["shots"] = per_shot
    static = [row["id"] for row in per_shot if row["motion_mean"] < MOTION_FLOOR]
    report["static_shots"] = static

    # 4. brightness continuity across cuts --------------------------------
    jumps = []
    for prev, nxt in zip(per_shot, per_shot[1:]):
        delta = abs(nxt["luma_mean"] - prev["luma_mean"])
        jumps.append({"cut": prev["id"] + "->" + nxt["id"], "delta_luma": round(delta, 1)})
    report["luma_jumps"] = jumps
    chapters = story.get("chapters", [])
    chapter_starts = {round(float(ch.get("start", -1)), 2) for ch in chapters}
    harsh = []
    for row in jumps:
        if row["delta_luma"] <= 45:
            continue
        at = float(row["cut"].split("->")[1].replace("S", ""))
        boundary = shots[int(at) - 1]["start"] if 0 < at <= len(shots) else -1
        row["chapter_break"] = boundary in chapter_starts
        harsh.append(row)
    if harsh:
        intended = [row for row in harsh if row.get("chapter_break")]
        warns.append(f"{len(harsh)} 处接缝亮度跳变 >45，其中 {len(intended)} 处正好是章节分界（日→夜/暖→冷，属设计）")

    # 5. subtitles --------------------------------------------------------
    cues = parse_srt(SRT)
    report["subtitles"] = {"cues": len(cues)}
    if len(cues) != len(shots):
        fails.append(f"字幕 {len(cues)} 条，分镜 {len(shots)} 镜，数量不一致")
    mix_report = None
    for candidate in (QA / "mix-report.json", ROOT / "work" / "kinkakuji1950" / "audiotest" / "audio" / "mix-report.json"):
        if candidate.is_file():
            mix_report = json.loads(candidate.read_text(encoding="utf-8"))
            break
    mix_shots = {row["id"]: row for row in (mix_report or {}).get("narration", {}).get("shots", [])}
    report["subtitle_baseline"] = ("mix-report" if mix_shots else "shot-window-only")

    sub_problems = []
    for cue, shot in zip(cues, shots):
        text = "".join(cue["lines"])
        if text != shot["narration"]:
            sub_problems.append(f"{shot['id']} 字幕文字与旁白不一致")
        if cue["start"] < shot["start"] - 0.05 or cue["end"] > shot["start"] + shot["duration"] + 0.05:
            sub_problems.append(f"{shot['id']} 字幕越出本镜时间窗 "
                                f"({cue['start']}-{cue['end']} vs {shot['start']}-{shot['start'] + shot['duration']})")
        if len(cue["lines"]) > 2:
            sub_problems.append(f"{shot['id']} 字幕超过两行")
        if any(len(line) > 26 for line in cue["lines"]):
            sub_problems.append(f"{shot['id']} 单行超过 26 字")
        voice = mix_shots.get(shot["id"])
        if voice:
            head, tail = cue["start"] - voice["speech_start"], cue["end"] - voice["speech_end"]
            if abs(head) > 0.12 or abs(tail) > 0.12:
                sub_problems.append(f"{shot['id']} 字幕与语音活动区间偏差 头{head:+.2f}s/尾{tail:+.2f}s")
    for a, b in zip(cues, cues[1:]):
        if b["start"] < a["end"] - 0.01:
            sub_problems.append(f"字幕重叠 {a['index']}/{b['index']}")
    report["subtitles"]["problems"] = sub_problems
    fails.extend(sub_problems[:10])

    # 6. narration vs shot window (片段与解说等长) ------------------------
    fit = []
    for shot in shots:
        row = split_by_id.get(shot["id"], {})
        speech = float(row.get("speech_seconds") or 0.0)
        window = float(shot["duration"])
        ratio = speech / window if window else 0.0
        fit.append({"id": shot["id"], "speech": round(speech, 2), "window": window,
                    "ratio": round(ratio, 3), "chars": row.get("chars")})
        if ratio > FIT_CEILING:
            fails.append(f"{shot['id']} 旁白 {speech:.2f}s 装不进 {window}s 窗口（{ratio:.2f}×）")
        if ratio < 0.35:
            warns.append(f"{shot['id']} 旁白只占窗口 {ratio:.0%}，画面留白偏多")
    report["narration_fit"] = {"per_shot": fit,
                               "max_ratio": round(max(r["ratio"] for r in fit), 3),
                               "min_ratio": round(min(r["ratio"] for r in fit), 3),
                               "total_speech": round(sum(r["speech"] for r in fit), 2)}

    # 7. audio ------------------------------------------------------------
    report["audio"] = audio_levels(FILM)
    if report["audio"]["rms_dbfs"] < -30:
        fails.append(f"整体响度过低 {report['audio']['rms_dbfs']} dBFS")
    if report["audio"]["peak_dbfs"] > -0.5:
        fails.append(f"峰值过高 {report['audio']['peak_dbfs']} dBFS，有削波风险")

    # 8. text compliance --------------------------------------------------
    banned = {"自杀", "自尽", "切腹", "割腕", "遗骨", "遗体", "尸", "血", "カルモチン", "安眠药"}
    hits = []
    for shot in shots:
        blob = shot.get("narration", "") + " " + shot.get("prompt", "")
        for word in banned:
            if word in blob:
                hits.append({"id": shot["id"], "word": word})
    report["safety"] = {"banned_hits": hits}
    if hits:
        fails.append(f"出现平台风险词：{hits[:6]}")
    text_shots = [s["id"] for s in shots if "readable text" not in s.get("prompt", "").lower()]
    report["on_screen_text"] = {"shots_without_text_clause": text_shots}
    if text_shots not in ([], ["S30"]):
        warns.append(f"非镜头 30 的提示词缺少 “no readable text” 约束：{text_shots}")

    # 9. stills + montage for the human pass ------------------------------
    mids = [s["start"] + s["duration"] * 0.5 for s in shots]
    stills = grab_stills(FILM, mids, FRAMES)
    montage([ROOT / p for p in stills], AUDIT_DIR / "montage.jpg")
    report["stills"] = stills
    report["montage"] = str((AUDIT_DIR / "montage.jpg").relative_to(ROOT))

    report["verdict"] = "PASS" if not fails else "FAIL"
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    (QA / "final-audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")

    lines = ["# 成片终审 · 金阁寺纵火案（第三期）", "",
             f"判定：**{report['verdict']}**  ·  失败 {len(fails)} 项 / 警告 {len(warns)} 项", "",
             "## 容器规格", "",
             f"- 画面 {meta['width']}×{meta['height']} @ {meta['fps']:.0f}fps，{meta['vcodec']}",
             f"- 时长 {meta['duration_seconds']:.3f}s，帧数 {meta['frames']}",
             f"- 音轨 {meta['acodec']} / {meta['sample_rate']}Hz / {meta['channels']}ch，"
             f"RMS {report['audio']['rms_dbfs']} dBFS，峰值 {report['audio']['peak_dbfs']} dBFS", "",
             "## 畸变扫描", "",
             f"- 采样 {len(stack)} 帧 @ {fps:g}fps；纯黑帧 {len(black)} 处（计划外 {len(unexpected_black)}）",
             f"- 冻结段 {len(freeze_runs)} 段 {freeze_runs[:4]}；清晰度/块状/拖影异常 "
             f"{ {k: len(v) for k, v in suspect.items()} }", "",
             "## 镜头与节奏", "",
             f"- 计划切点 {len(planned)} 个，成片检出未对位 {len(unmatched)} 个，多余剪辑点 {len(extras)} 个",
             f"- 静止/几乎不动镜头：{static or '无（慢镜头均已通过局部运动核验）'}",
             f"- 亮度跳变 >45 的接缝：{len(harsh)} 处", "",
             "## 解说与画面等长", "",
             f"- 旁白总语音 {report['narration_fit']['total_speech']}s，占比区间 "
             f"{report['narration_fit']['min_ratio']:.0%}–{report['narration_fit']['max_ratio']:.0%}（上限 155%）",
             f"- 字幕 {len(cues)} 条，问题 {len(sub_problems)} 项", ""]
    for problem in sub_problems[:12]:
        lines.append(f"  - {problem}")
    if fails:
        lines += ["", "## 失败项", ""] + [f"- {item}" for item in fails]
    if warns:
        lines += ["", "## 警告项", ""] + [f"- {item}" for item in warns]
    lines += ["", "## 每镜实测", "", "| 镜头 | 窗口 | 帧间运动 | 平均亮度 | 清晰度 | 旁白占比 |",
              "|---|---|---|---|---|---|"]
    for row, f in zip(per_shot, fit):
        lines.append(f"| {row['id']} | {row['window'][0]}–{row['window'][1]}s | {row['motion_mean']} | "
                     f"{row['luma_mean']} | {row['sharp_mean']} | {f['ratio']:.0%} |")
    lines += ["", "---", "",
              "画面与旁白对位、剧情逻辑、史实核对、平台安全、待拍板事项见 "
              "[`semantic-review.md`](semantic-review.md)。"]
    (QA / "final-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines[:40]))
    print(f"\nverdict={report['verdict']} fails={len(fails)} warns={len(warns)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
