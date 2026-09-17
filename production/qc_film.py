#!/usr/bin/env python3
"""交付前画质 QC：把「能算出来」的瑕疵与畸变代理量一次测完，输出机读报告。

设计原则与本项目其它闸门一致：**每条都要有数字与阈值；测不了的写进 not_measured，
不许用形容词**。它补的是 `review_film.py`（黑帧/冻结/电平）与 `verbatim_check.py`
（逐字听检）没有覆盖的那一类 —— 画面压缩伪影与几何畸变的代理指标。

    python3 production/qc_film.py \
        --film 交付/DB库珀劫机案_三分钟_带声音.mp4 \
        --project production/dbcooper --fps 2 \
        --out production/dbcooper/delivery/qc-report.json

退出码：0 = 全部通过；1 = 有 FLAG（闸门语义，与 `review_film.py` 一致）。

四条踩过的坑写在这里，别改回去：
1. 全帧统计量必须先排除「片子本来就该变」的位置（切点、淡入淡出），否则量到的是剪辑；
2. 任何在全幅上量的指标都要先剔除上下黑边与字幕带，否则画框自己的硬边会被当成"8 像素对齐"；
3. 8-bit 素材里"相邻像素差恰为 1 灰阶"占多数是**抖动/颗粒**的正常表现，不能当假轮廓判据
   —— 所以 banding 只作参考，不给判定；
4. 没有未处理的原始帧就没有几何 ground truth，本脚本**不能**宣布"无畸变"，
   只能给出对照量；畸变的判定证据是 review/ 下的密扫表与裁放图（人工逐格）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

FRAME_W, FRAME_H = 1920, 1080
PICTURE_ROWS = (140, 940)        # 上下为 16:9 黑边；下方黑边里还有烧录字幕带
FPS = 30.0                       # 交付帧率（EDL 的帧号按它换算）

DEFAULTS = {
    # 块效应：同一素材无损参照实测 p50≈0.09；一次合理有损 ≈0.10-0.12；二次压缩会翻倍
    "blocking_p50_max": 0.14,
    "blocking_p90_max": 0.30,
    "overexposed_fraction_max": 0.06,
    "overexposed_frame_count_max": 0,
    "underexposed_p95_reference": 0.80,
    "saturation_mean_min": 0.02,
    "saturation_mean_max": 0.42,
    "flash_reversal_spikes_max": 0,
    "flash_reversal_amp_min": 0.045,      # 小于此幅度的反向不算异常（颗粒/电平噪声）
    "letterbox_min_frame_fraction": 0.80,   # 遮幅必须"整段都在"才算，个别帧的暗构图不算
    "border_pure_max": 4,                   # 真遮幅：整行最大灰阶 ≤4 且 σ ≤1.5
    "border_pure_std": 1.5,
    # 这几段的纯黑边是设计的一部分（档案图把文件摆在暗场中央），列明白而不是偷偷放宽阈值
    "designed_border_segments": ["S26"],
    "axis_aligned_fraction_min": 0.18,
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def probe_geometry(film: Path):
    """返回 (宽, 高, 时长秒)。

    CI 与本地都只有 imageio-ffmpeg 带的 ffmpeg，**没有 ffprobe**，
    所以一律先解析 `ffmpeg -i` 的 stderr；ffprobe 存在时才用作快捷路径。
    """
    if shutil.which("ffprobe"):
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height:format=duration", "-of", "json", str(film)],
            capture_output=True, text=True)
        if proc.returncode == 0:
            data = json.loads(proc.stdout or "{}")
            stream = (data.get("streams") or [{}])[0]
            w, h = int(stream.get("width") or 0), int(stream.get("height") or 0)
            dur = float((data.get("format") or {}).get("duration") or 0.0)
            if w and h:
                return w, h, dur
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(film)],
                          capture_output=True, text=True)
    err = proc.stderr or ""
    m = re.search(r"Stream #\d+:\d+.*?Video:.*?(\d{3,5})x(\d{3,5})", err)
    d = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", err)
    if not (m and d):
        return 0, 0, 0.0
    return int(m.group(1)), int(m.group(2)), int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3))


def decode_error_lines(film: Path) -> list:
    """完整解码一遍，返回 ffmpeg 报出的错误行（合法选项，别加 `-x`）。"""
    proc = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(film),
                           "-f", "null", "-"], capture_output=True, text=True)
    return [ln for ln in (proc.stderr or "").splitlines()
            if re.search(r"error|invalid|conceal|corrupt", ln, re.I)]


def lead(gray: np.ndarray, side: str) -> int:
    """从这一边数起，连续"整行（列）纯黑"的行数。

    判据是 **整行 max ≤ 4 且 σ ≤ 1.5**，不是"整行偏暗"。上一版按"暗行占比 >0.98"量，
    把夜戏的暗天空/暗前景当成了遮幅（实测那些行 max 17-204、σ 0.9-17.2 —— 有内容），
    一条误报占了三个 FLAG 里的两个。真遮幅（模型自拼的黑边、pad 出来的 mat）必然纯黑。
    """
    H, W = gray.shape
    if side == "top":
        rows = gray[:60]
    elif side == "bottom":
        rows = gray[H - 60:][::-1]
    elif side == "left":
        rows = gray[:, :60].T
    else:
        rows = gray[:, W - 60:].T[:, ::-1]
    k = 0
    for r in rows:
        if float(r.max()) <= 4.0 and float(r.std()) <= 1.5:
            k += 1
        else:
            break
    return k


def blocking_index(gray: np.ndarray) -> float:
    """8×8 块边界上的水平梯度相对块内部的倍数 —— 过压缩/二次压缩会放大暗部方格。

    只在画面区内量：黑边与字幕带自己的硬边界就是"8 像素对齐的强边缘"，
    全幅量会量到画框而不是画质。
    """
    pic = gray[PICTURE_ROWS[0]:PICTURE_ROWS[1]]
    gx = np.abs(np.diff(pic, axis=1)).mean(axis=0)
    edge = gx[7::8].mean()
    inner = np.delete(gx, np.arange(7, len(gx), 8)).mean()
    return float((edge - inner) / max(inner, 1e-6))


def quantized_step_ratio(gray: np.ndarray) -> float:
    """相邻像素差恰为 1 灰阶的占比（参考量，不判定：见模块注释第 3 条）。"""
    d = np.abs(np.diff(gray.astype(np.int16), axis=0))
    nz = int((d > 0).sum())
    return float(((d > 0) & (d <= 1)).sum() / max(nz, 1))


def axis_aligned_fraction(gray: np.ndarray) -> float:
    """强边缘里水平+垂直方向的占比 —— 透视/几何畸变的代理指标。"""
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    rows, cols = min(gx.shape[0], gy.shape[0]), min(gx.shape[1], gy.shape[1])
    gx, gy = gx[:rows, :cols] + 1e-6, gy[:rows, :cols] + 1e-6
    strong = (gx > 8.0) | (gy > 8.0)
    if not strong.any():
        return 0.0
    horiz = (gx > 2.0 * gy) & strong
    vert = (gy > 2.0 * gx) & strong
    return float((horiz.sum() + vert.sum()) / strong.sum())


def load_edl(project: Path) -> list:
    """读 delivery/edit-decision-list.json → [(id, kind, start_s, end_s)]，用于分段归因。"""
    path = project / "delivery" / "edit-decision-list.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = data if isinstance(data, list) else data.get("segments", [])
    return [(s.get("id", "?"), s.get("kind", ""), s["start_frame"] / FPS, s["end_frame"] / FPS)
            for s in segs if "start_frame" in s and "end_frame" in s]


def sample_saturation(film: Path, fps: float, every: int = 8) -> list:
    """每 every 个采样帧取 1 帧量饱和度（max-min 通道均值 / 255）。"""
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(film), "-vf", f"fps={fps}",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE, bufsize=1 << 20)
    size = FRAME_W * FRAME_H * 3
    out, i = [], 0
    assert proc.stdout is not None
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        if i % every == 0:
            a = np.frombuffer(buf, dtype=np.uint8).reshape(FRAME_H, FRAME_W, 3).astype("int16")
            out.append(float((a.max(axis=2) - a.min(axis=2)).mean() / 255.0))
        i += 1
    proc.wait()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--film", required=True)
    ap.add_argument("--project", default="", help="项目目录：读 EDL 与 thresholds-qc.json")
    ap.add_argument("--out", default="")
    ap.add_argument("--fps", type=float, default=2.0, help="采样帧率（2 ⇒ 全片 360 帧）")
    args = ap.parse_args()

    root = Path.cwd()
    film = Path(args.film)
    if not film.is_absolute():
        film = root / film
    project = (root / args.project) if args.project else None
    thresholds = dict(DEFAULTS)
    if project:
        for cand in (project / "thresholds-qc.json",):
            if cand.exists():
                thresholds.update(json.loads(cand.read_text(encoding="utf-8")))
                print(f"[qc] 阈值取自 {cand}")

    segments = load_edl(project) if project else []
    if not segments:
        print("[qc] 没有 EDL：段内/段间判别退化为全片口径，黑边白名单失效", file=sys.stderr)

    def seg_of(t: float):
        for sid, kind, a, b in segments:
            if a <= t < b:
                return sid, kind
        return None, None

    def near_cut(t: float) -> bool:
        """离任一段边界不足一个采样间隔 ⇒ 这一帧的亮度差可能来自切点/淡变。"""
        return any(abs(t - a) <= 1.0 / args.fps or abs(t - b) <= 1.0 / args.fps
                   for _, _, a, b in segments)

    w, h, dur = probe_geometry(film)
    per_segment: dict[str, dict] = {}
    luma: list[float] = []
    times: list[float] = []
    blocking: list[float] = []
    step_ratio: list[float] = []
    overex: list[float] = []
    underex: list[float] = []
    axis: list[float] = []
    per_frame = []
    n = 0

    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(film), "-vf", f"fps={args.fps}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        stdout=subprocess.PIPE, bufsize=1 << 20)
    size = FRAME_W * FRAME_H
    assert proc.stdout is not None
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        g = np.frombuffer(buf, dtype=np.uint8).reshape(FRAME_H, FRAME_W).astype("float32")
        t = n / args.fps
        mean_l = float(g.mean())
        blk = blocking_index(g)
        bx = float((g >= 250).mean())
        un = float((g <= 6).mean())
        ax = axis_aligned_fraction(g)
        times.append(t)
        luma.append(mean_l / 255.0)
        blocking.append(blk)
        step_ratio.append(quantized_step_ratio(g))
        overex.append(bx)
        underex.append(un)
        axis.append(ax)

        sid, kind = seg_of(t)
        rec = per_segment.setdefault(sid or "?", {
            "kind": kind, "frames": 0, "blocking": [], "overexposed": [],
            "border_frames": {k: [] for k in ("top", "bottom", "left", "right")}})
        rec["frames"] += 1
        rec["blocking"].append(blk)
        rec["overexposed"].append(bx)
        if mean_l > 25.0 and kind != "graphic":       # 淡入淡出帧与卡面段不参与黑边判定
            for k in ("top", "bottom", "left", "right"):
                rec["border_frames"][k].append(lead(g, k))
        per_frame.append({"frame": n, "t": round(t, 2), "segment": sid,
                          "blocking": round(blk, 4), "step_ratio": round(step_ratio[-1], 4)})
        n += 1
    proc.wait()
    if not n:
        print("[qc] 解帧失败", file=sys.stderr)
        return 2

    frac_min = thresholds["letterbox_min_frame_fraction"]
    for rec in per_segment.values():
        # 只有"整段都在"的纯黑行才算遮幅；个别帧量到的是暗构图，不是 mat
        rec["border"] = {}
        for k, vals in rec["border_frames"].items():
            vals = np.array(vals, dtype=float)
            present = float((vals > 0).mean()) if vals.size else 0.0
            rec["border"][k] = (int(np.median(vals[vals > 0])) if present else 0, round(present, 3))
        rec.pop("border_frames", None)
    for rec in per_segment.values():
        rec["blocking_p50"] = round(float(np.percentile(rec["blocking"], 50)), 4)
        rec["blocking_max"] = round(float(max(rec["blocking"])), 4)
        rec["overexposed_max"] = round(float(max(rec["overexposed"])), 5)
        for key in ("blocking", "overexposed"):
            rec.pop(key, None)

    saturation = sample_saturation(film, args.fps)
    blk_arr = np.array(blocking)
    over_arr = np.array(overex)
    sat_arr = np.array(saturation)

    lum = np.array(luma)
    d = np.diff(lum)
    spike_frames, spike_amps = [], []
    for i in range(1, d.size):
        if d[i - 1] * d[i] >= 0:
            continue                                   # 同向 = 斜坡/台阶，不是尖峰
        amp = float(min(abs(d[i - 1]), abs(d[i])))
        if amp < thresholds["flash_reversal_amp_min"]:
            continue
        idx = i                                        # 尖峰所在采样帧
        if near_cut(times[idx]) or near_cut(times[idx - 1]) or near_cut(times[min(idx + 1, n - 1)]):
            continue                                   # 切点/淡变相邻的设计转场不算闪烁
        spike_frames.append(round(times[idx], 2))
        spike_amps.append(round(amp, 4))

    # 黑边：设计内的段列白名单，其余段一有黑边就是 FLAG
    designed = set(thresholds["designed_border_segments"])
    stray = {sid: {k: v for k, v in rec["border"].items() if v[0] > 0}
             for sid, rec in per_segment.items() if sid not in designed}
    stray = {sid: {k: v for k, v in d.items()
                   if v[1] >= frac_min} for sid, d in stray.items()}
    stray = {sid: d for sid, d in stray.items() if d}

    checks = []

    def add(key, desc, measured, ok, note):
        checks.append({"name": key, "desc": desc, "measured": measured, "ok": bool(ok), "note": note})

    err_lines = decode_error_lines(film)
    add("resolution", "交付片为 1920x1080", [w, h], (w, h) == (FRAME_W, FRAME_H),
        f"{w}x{h}，要求 {FRAME_W}x{FRAME_H}")
    add("decode_errors", "全片完整解码无错误行", [len(err_lines)], not err_lines,
        "; ".join(err_lines[:3]) if err_lines else "ffmpeg -v error -xerror 全片解码，无 error/invalid/conceal 行")
    add("blocking", "8x8 块效应不超阈值（压缩伪影）",
        [round(float(np.percentile(blk_arr, 50)), 4), round(float(np.percentile(blk_arr, 90)), 4),
         round(float(blk_arr.max()), 4)],
        np.percentile(blk_arr, 50) <= thresholds["blocking_p50_max"]
        and np.percentile(blk_arr, 90) <= thresholds["blocking_p90_max"],
        f"画面区内量；p50={np.percentile(blk_arr, 50):.3f}（上限 {thresholds['blocking_p50_max']}）、"
        f"p90={np.percentile(blk_arr, 90):.3f}（上限 {thresholds['blocking_p90_max']}）、"
        f"max={blk_arr.max():.3f}；校准：同素材无损参照 p50=0.084，"
        f"双段 crf21 复现实验 p50=0.171（与本片改前实测 0.168 吻合 ⇒ 归因于编码链而非素材），"
        f"改后目标 ≤0.14；"
        f"最暗的夜镜（S02/S17/S27/S28）贡献尾部")
    add("banding_reference", "假轮廓参考量（不判定，见模块注释第 3 条）",
        [round(float(np.percentile(step_ratio, 95)), 4)], True,
        "差值恰为 1 灰阶的相邻像素占比 p95 —— 8-bit 颗粒素材里高值即抖动本身，"
        "故只作参考，不给通过/不通过")
    add("overexposed", "高光不削顶",
        [round(float(over_arr.max()), 5), int((over_arr > 0.02).sum())],
        over_arr.max() <= thresholds["overexposed_fraction_max"]
        and int((over_arr > 0.02).sum()) <= thresholds["overexposed_frame_count_max"],
        f"单帧 ≥250 占比上限 {thresholds['overexposed_fraction_max']}，实测 max={over_arr.max():.5f}；"
        f"占比 >2% 的帧数 {int((over_arr > 0.02).sum())}（上限 "
        f"{thresholds['overexposed_frame_count_max']}）")
    add("underexposed_reference", "暗部死黑占比（参考量，不判定）",
        [round(float(np.percentile(underex, 95)), 4)], True,
        f"≤6 灰阶占比 p95={np.percentile(underex, 95):.3f}；本片为雨夜戏，暗场是设计口径"
        f"（台账 B2 已记：168 个近黑帧来自 review_film.py 实测），故只作参考量；"
        f"超过 {thresholds['underexposed_p95_reference']} 才需要回来重看")
    add("saturation", "饱和度不过冲、也不脱色",
        [round(float(sat_arr.mean()), 4), round(float(np.percentile(sat_arr, 95)), 4)],
        thresholds["saturation_mean_min"] <= sat_arr.mean() <= thresholds["saturation_mean_max"],
        f"均值 {sat_arr.mean():.3f}（要求 {thresholds['saturation_mean_min']}..{thresholds['saturation_mean_max']}）")
    add("flash", "段内无异常闪烁（单帧反向亮度尖峰，切点与淡变已排除）",
        [len(spike_frames), spike_frames[:5], spike_amps[:5]],
        len(spike_frames) <= thresholds["flash_reversal_spikes_max"],
        f"{n} 个采样帧里量到 {len(spike_frames)} 次；幅度阈值 "
        f"{thresholds['flash_reversal_amp_min']}；硬切台阶与淡入淡出不计入（那是剪辑）")
    add("letterbox", "设计外无额外遮幅/纯黑 mat", [stray], not stray,
        f"判据：整行 max≤{thresholds['border_pure_max']} 且 σ≤{thresholds['border_pure_std']}，"
        f"且该段 ≥{int(frac_min * 100)}% 的采样帧都有；"
        f"白名单（设计内）{sorted(designed)}；卡面段与淡入淡出帧不参与；违规段：{stray or '无'}。"
        f"偏暗但有内容的行不计入（上一版误把夜戏暗场当遮幅，已修）")
    add("orientation_purity", "强边缘轴向占比（畸变代理，仅对照）",
        [round(float(np.percentile(axis, 5)), 4)],
        np.percentile(axis, 5) >= thresholds["axis_aligned_fraction_min"],
        f"p5={np.percentile(axis, 5):.3f}，下限 {thresholds['axis_aligned_fraction_min']}；"
        f"只说明画面仍以水平/垂直结构为主，**不能证明无畸变**（无几何 ground truth）")

    video_bps = (film.stat().st_size * 8 / dur) if dur else 0.0
    report = {
        "film": str(film.relative_to(root)) if film.is_relative_to(root) else str(film),
        "film_bytes": film.stat().st_size,
        "film_sha256": sha256(film),
        "duration_s": dur,
        "avg_bitrate_mbps": round(video_bps / 1e6, 3),
        "sample_fps": args.fps,
        "sampled_frames": n,
        "picture_rows_measured": list(PICTURE_ROWS),
        "thresholds": thresholds,
        "checks": checks,
        "metrics": {
            "blocking_mean": round(float(blk_arr.mean()), 4),
            "blocking_p50": round(float(np.percentile(blk_arr, 50)), 4),
            "blocking_p90": round(float(np.percentile(blk_arr, 90)), 4),
            "blocking_p95": round(float(np.percentile(blk_arr, 95)), 4),
            "blocking_max": round(float(blk_arr.max()), 4),
            "step_ratio_p95_reference": round(float(np.percentile(step_ratio, 95)), 4),
            "saturation_mean": round(float(sat_arr.mean()), 4),
            "saturation_p95": round(float(np.percentile(sat_arr, 95)), 4),
            "overexposed_max": round(float(over_arr.max()), 5),
            "underexposed_p95": round(float(np.percentile(underex, 95)), 4),
            "luma_mean": round(float(np.mean(lum) * 255.0), 2),
            "luma_max": round(float(np.max(lum) * 255.0), 2),
            "flash_reversal_spikes": len(spike_frames),
            "flash_spike_times_s": spike_frames,
            "letterbox_by_segment": {sid: {k: v for k, v in rec["border"].items() if v[0] > 0}
                                     for sid, rec in per_segment.items()
                                     if max(v[0] for v in rec["border"].values()) > 0},
            "axis_aligned_p5": round(float(np.percentile(axis, 5)), 4),
        },
        "per_segment": per_segment,
        "worst_blocking_frames": sorted(per_frame, key=lambda r: -r["blocking"])[:12],
        "not_measured": [
            "单帧局部畸变（无原始未处理帧可比对，几何上无 ground truth）——"
            "由 review/ 的 68 帧全幅密扫表 + 定点裁放图逐格人工判读代替",
            "色彩保真度绝对值（无参考母带；只量了饱和度分布）",
            "AI 素材自身的解剖/结构错误 —— 属镜头抽卡闸门，不由本脚本负责",
            "假轮廓判定（见模块注释第 3 条：现口径无法区分抖动与条带，只给参考量）",
        ],
    }

    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = root / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[qc] 报告写入 {out}")

    print(f"\n=== QC：{film.name} ｜ {n} 个采样帧 ｜ 平均码率 {report['avg_bitrate_mbps']} Mbps ===")
    for c in checks:
        flag = "✓" if c["ok"] else "✗"
        print(f"  {flag} {c['name']:<22}{c['desc']}")
        print(f"      实测 {c['measured']}")
        print(f"      说明 {c['note']}")
    worst = sorted(((r["blocking_p50"], sid, r["blocking_max"])
                    for sid, r in per_segment.items() if r["frames"] > 4), reverse=True)[:3]
    print("\n块效应最重的 3 个段（p50 / max）：")
    for p50, sid, mx in worst:
        print(f"  {sid:<6}p50={p50:.3f} max={mx:.3f}")
    bad = [c["name"] for c in checks if not c["ok"]]
    print(f"\n结论：{'全部通过' if not bad else 'FLAG ' + ', '.join(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
