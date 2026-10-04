#!/usr/bin/env python3
"""参考视频风格分析引擎：把用户上传的参考片量成一份「风格档案」。

设计原则（跟仓库其它流水线一致）：

* **只分析，不复制**：参考片只用来量测（色调、影调、光线、运动、节奏），
  一帧都不会进成片，音轨也不参与任何输出；
* **可以离线跑**：只依赖 ffmpeg + Pillow + numpy，不联网、不需要 ASR；
* **量出来的才算数**：所有结论都由实测数值经阈值判定生成，档案里会写明
  采样规模与已知误差（硬切检测基于画面差值，淡入淡出会漏检）。
  阈值 0.24 沿用 ``production/dahlia/reference_metrics.json`` 里那一套。

产出（写到 ``--out`` 目录）::

    reference.mp4        参考片的副本（不进 git，见 .gitignore）
    frames/Sxx.jpg       抽帧（不进 git）
    contact-sheet.jpg    接触表（8×6，带时间码）
    reference_metrics.json   机器可读的实测值
    风格档案.md           人读的中文风格档案
    style-candidates.json    三组英文 STYLE_PREFIX / NEGATIVE_PROMPT 候选

用法::

    python3 production/style_lab/analyze.py --video ~/bailin.mp4 \\
        --out production/style_lab/runs/manual-001 --samples 48
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from ffmpeg_tool import ffmpeg_version, find_ffmpeg  # type: ignore

HERE = Path(__file__).resolve().parent

DEFAULT_SAMPLES = 48
DEFAULT_THRESHOLD = 0.24
DEFAULT_CONTACT_COLS = 8
CUT_SCALE_WIDTH = 320          # 切点检测时的解码宽度（越小越快）
CUT_WALL_LIMIT = 900.0         # 切点检测最长跑 15 分钟，超时按部分结果处理
MOTION_PAIRS = 10              # 运动幅度的采样对数
MOTION_GAP = 0.40              # 每对帧相隔的秒数
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


# --------------------------------------------------------------------------- 进度


def _noop(stage: str, pct: float, detail: str = "") -> None:
    return None


ProgressFn = Callable[[str, float, str], None]


# --------------------------------------------------------------------------- 探测


_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_VIDEO_RE = re.compile(r"Stream #\d+:\d+.*?Video:\s*([^,]+).*?,\s*(\d{2,5})x(\d{2,5})", re.S)
_FPS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:fps|tbr)")
_AUDIO_RE = re.compile(r"Stream #\d+:\d+.*?Audio:\s*([^,]+).*?(\d+)\s*Hz", re.S)


def parse_hms(hms: str) -> float:
    m = _DURATION_RE.search(hms)
    if not m:
        return 0.0
    h, mi, s = m.groups()
    return int(h) * 3600 + int(mi) * 60 + float(s)


def probe(ffmpeg: str, path: Path) -> dict:
    """只读探测：时长 / 分辨率 / 帧率 / 编码 / 是否有音轨。"""
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    text = (proc.stderr or b"").decode("utf-8", "replace")
    info: dict = {"raw_duration_line": (_DURATION_RE.search(text).group(0) if _DURATION_RE.search(text) else "")}
    info["duration"] = parse_hms(text)
    v = _VIDEO_RE.search(text)
    if v:
        info["video_codec"] = v.group(1).strip()
        info["width"] = int(v.group(2))
        info["height"] = int(v.group(3))
        fps_matches = _FPS_RE.findall(text[v.start(): v.start() + 400])
        fps = 0.0
        for cand in fps_matches:
            try:
                val = float(cand)
            except ValueError:
                continue
            if 1.0 <= val <= 120.0:
                fps = val
                break
        info["fps"] = round(fps, 3)
    a = _AUDIO_RE.search(text)
    info["has_audio"] = bool(a)
    if a:
        info["audio_codec"] = a.group(1).strip()
        info["audio_hz"] = int(a.group(2))
    info["orientation"] = "landscape"
    if info.get("width") and info.get("height"):
        if info["height"] > info["width"]:
            info["orientation"] = "portrait"
        elif info["height"] == info["width"]:
            info["orientation"] = "square"
    return info


# --------------------------------------------------------------------------- 抽帧


def grab_frame(ffmpeg: str, path: Path, at: float, out: Path, width: int) -> bool:
    """在 ``at`` 秒抽一帧，缩放到 ``width`` 宽，存 jpg。成功返回 True。"""
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-ss", f"{max(at, 0.0):.3f}", "-i", str(path),
        "-frames:v", "1", "-q:v", "3",
        "-vf", f"scale={width}:-2", "-y", str(out),
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except subprocess.SubprocessError:
        return False
    return out.exists() and out.stat().st_size > 0


def sample_frames(
    ffmpeg: str,
    path: Path,
    duration: float,
    count: int,
    outdir: Path,
    width: int = 960,
    progress: ProgressFn = _noop,
) -> list[Path]:
    """在整段视频上均匀抽 ``count`` 帧（避开首尾各 0.5 % 的黑场/片尾）。"""
    outdir.mkdir(parents=True, exist_ok=True)
    frames: list[Path] = []
    for i in range(count):
        frac = (i + 0.5) / count
        t = duration * (0.005 + frac * 0.99)
        out = outdir / f"S{i + 1:02d}.jpg"
        if grab_frame(ffmpeg, path, t, out, width):
            frames.append(out)
        progress("抽帧", 10 + 25 * (i + 1) / count, f"{i + 1}/{count} 帧")
    return frames


# --------------------------------------------------------------------------- 画面统计


def _gray(arr: np.ndarray) -> np.ndarray:
    return 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]


def _laplacian_var(gray: np.ndarray) -> float:
    core = 4.0 * gray[1:-1, 1:-1] - gray[:-2, 1:-1] - gray[2:, 1:-1] - gray[1:-1, :-2] - gray[1:-1, 2:]
    return float(core.var())


def _region_sharpness(gray: np.ndarray) -> tuple[float, float, float, float]:
    """返回 (中心区锐度, 边缘区锐度, 中心区亮度, 边缘区亮度)。

    中心高、边缘低 = 浅景深；但**暗角会骗过这个指标**——边缘一片黑时拉普拉斯
    方差本来就接近 0，所以调用方要拿亮度判断一次，暗角太重就老实说"判不了"。
    """
    h, w = gray.shape
    cy0, cy1 = int(h * 0.30), int(h * 0.70)
    cx0, cx1 = int(w * 0.30), int(w * 0.70)
    center = _laplacian_var(gray[cy0:cy1, cx0:cx1])
    center_luma = float(gray[cy0:cy1, cx0:cx1].mean())
    bands = [
        gray[: int(h * 0.18), :],
        gray[int(h * 0.82):, :],
        gray[:, : int(w * 0.18)],
        gray[:, int(w * 0.82):],
    ]
    edge = float(np.mean([_laplacian_var(b) for b in bands if b.size > 100]))
    edge_luma = float(np.mean([b.mean() for b in bands if b.size > 100]))
    return center, edge, center_luma, edge_luma


def _grain_score(pil: Image.Image) -> float:
    """高频残差：原图减去轻微模糊后残差的标准差，粗略代表颗粒/锐化强度。"""
    gray = np.asarray(pil.convert("L"), dtype=np.float32)
    blurred = np.asarray(pil.convert("L").filter(ImageFilter.GaussianBlur(1.4)), dtype=np.float32)
    return float((gray - blurred).std())


def _bottom_band_ratio(gray: np.ndarray) -> float:
    """底部 12 % 的边缘密度 / 全画面边缘密度，>1.6 提示可能是压在画面上的字幕条。"""
    h, w = gray.shape
    band = gray[int(h * 0.88):, :]
    if band.size < 100:
        return 1.0
    def edge_density(region: np.ndarray) -> float:
        gy, gx = np.diff(region, axis=0), np.diff(region, axis=1)
        return float(np.abs(gy).mean() + np.abs(gx).mean())
    whole = edge_density(gray)
    if whole <= 1e-6:
        return 1.0
    return edge_density(band) / whole


def _kmeans(pixels: np.ndarray, k: int = 6, iters: int = 12, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    n = pixels.shape[0]
    if n == 0:
        return np.zeros((0, 3)), np.zeros((0,))
    idx = rng.choice(n, size=min(k, n), replace=False)
    centers = pixels[idx].astype(np.float32).copy()
    for _ in range(iters):
        dist = ((pixels[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = dist.argmin(axis=1)
        for j in range(centers.shape[0]):
            mask = labels == j
            if mask.any():
                centers[j] = pixels[mask].mean(axis=0)
    dist = ((pixels[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    labels = dist.argmin(axis=1)
    counts = np.bincount(labels, minlength=centers.shape[0]).astype(float)
    order = np.argsort(-counts)
    return centers[order], counts[order] / counts.sum()


def frame_stats(paths: list[Path]) -> dict:
    """逐帧统计：亮度 / 饱和度 / 色温 / 锐度 / 颗粒 / 景深 / 底部字幕带。"""
    lums, sats, temps, sharp, grain, dof, bottom, contrast = [], [], [], [], [], [], [], []
    pixel_pool = []
    for p in paths:
        with Image.open(p) as im:
            rgb = im.convert("RGB")
            small = rgb.copy()
            small.thumbnail((160, 160))
            arr_small = np.asarray(small, dtype=np.float32).reshape(-1, 3)
            if arr_small.size:
                pixel_pool.append(arr_small[:: max(1, arr_small.shape[0] // 4000)])
            arr = np.asarray(rgb, dtype=np.float32)
            hsv = np.asarray(rgb.convert("HSV"), dtype=np.float32)
        g = _gray(arr)
        lums.append(float(g.mean()))
        contrast.append(float(g.std()))
        sats.append(float(hsv[..., 1].mean()))
        temps.append(float(arr[..., 0].mean() - arr[..., 2].mean()))
        sharp.append(_laplacian_var(g))
        center, edge, center_luma, edge_luma = _region_sharpness(g)
        # 边缘被暗角压黑时，方差低不代表虚化，而是没有信息——这种帧不计入景深统计
        if edge > 1e-6 and center_luma > 12.0 and edge_luma >= 0.40 * center_luma:
            dof.append(center / edge)
        with Image.open(p) as im:
            grain.append(_grain_score(im))
        bottom.append(_bottom_band_ratio(g))
    pool = np.vstack(pixel_pool) if pixel_pool else np.zeros((0, 3), dtype=np.float32)
    centers, shares = _kmeans(pool, k=6)
    hist, _ = np.histogram(np.asarray(lums) / 255.0, bins=[0.0, 0.2, 0.45, 0.8, 1.01])
    total = max(int(hist.sum()), 1)
    return {
        "frames_measured": len(paths),
        "mean_luma": round(float(np.mean(lums)), 1) if lums else 0.0,
        "luma_std": round(float(np.std(lums)), 1) if lums else 0.0,
        "mean_contrast": round(float(np.mean(contrast)), 1) if contrast else 0.0,
        "mean_saturation": round(float(np.mean(sats)), 1) if sats else 0.0,
        "warmth_r_minus_b": round(float(np.mean(temps)), 1) if temps else 0.0,
        "mean_sharpness": round(float(np.mean(sharp)), 1) if sharp else 0.0,
        "mean_grain": round(float(np.mean(grain)), 2) if grain else 0.0,
        "dof_center_over_edge": round(float(np.mean(dof)), 3) if dof else None,
        "dof_frames_used": len(dof),
        "bottom_band_ratio": round(float(np.mean(bottom)), 2) if bottom else 1.0,
        "tone_split": {
            "shadow": round(hist[0] / total, 3),
            "low_mid": round(hist[1] / total, 3),
            "high_mid": round(hist[2] / total, 3),
            "highlight": round(hist[3] / total, 3),
        },
        "palette": [
            {
                "hex": "#%02x%02x%02x" % tuple(int(v) for v in center),
                "rgb": [int(v) for v in center],
                "share": round(float(share), 3),
            }
            for center, share in zip(centers, shares)
        ],
    }


# --------------------------------------------------------------------------- 运动与切点


def motion_samples(
    ffmpeg: str,
    path: Path,
    duration: float,
    tmpdir: Path,
    pairs: int = MOTION_PAIRS,
    gap: float = MOTION_GAP,
) -> list[float]:
    """在若干时间点取相隔 ``gap`` 秒的两帧，算灰度平均绝对差（0–1）。"""
    values: list[float] = []
    for i in range(pairs):
        frac = (i + 0.5) / pairs
        t0 = duration * (0.02 + frac * 0.94)
        t1 = min(t0 + gap, max(duration - 0.05, 0.05))
        a, b = tmpdir / f"m{i}a.jpg", tmpdir / f"m{i}b.jpg"
        if not (grab_frame(ffmpeg, path, t0, a, 320) and grab_frame(ffmpeg, path, t1, b, 320)):
            a.unlink(missing_ok=True)
            b.unlink(missing_ok=True)
            continue
        with Image.open(a) as ia, Image.open(b) as ib:
            ga = np.asarray(ia.convert("L"), dtype=np.float32)
            gb = np.asarray(ib.convert("L"), dtype=np.float32)
        if ga.shape != gb.shape:
            a.unlink(missing_ok=True)
            b.unlink(missing_ok=True)
            continue
        values.append(float(np.abs(ga - gb).mean() / 255.0))
        a.unlink(missing_ok=True)
        b.unlink(missing_ok=True)
    return values


def detect_cuts(
    ffmpeg: str,
    path: Path,
    duration: float,
    threshold: float = DEFAULT_THRESHOLD,
    progress: ProgressFn = _noop,
) -> dict:
    """画面差值硬切粗检测（阈值沿用 production/dahlia 的 0.24）。"""
    cmd = [
        ffmpeg, "-hide_banner", "-nostats", "-progress", "pipe:1",
        "-i", str(path), "-an", "-sn", "-dn",
        "-filter:v", f"scale={CUT_SCALE_WIDTH}:-2,select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    err_file = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
    err_file.close()
    result = {
        "threshold": threshold,
        "estimated_cuts": 0,
        "cut_times": [],
        "estimated_median_shot_seconds": None,
        "estimated_mean_shot_seconds": None,
        "partial": False,
        "scanned_seconds": 0.0,
    }
    started = time.time()
    try:
        with open(err_file.name, "wb") as errfh:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errfh)
        assert proc.stdout is not None
        scanned = 0.0
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("out_time_us="):
                try:
                    scanned = int(line.split("=", 1)[1]) / 1_000_000.0
                except ValueError:
                    pass
                pct = min(scanned / duration, 1.0) if duration else 0.0
                progress("切点检测", 60 + 28 * pct, f"扫到 {scanned:.0f} / {duration:.0f} 秒")
            if time.time() - started > CUT_WALL_LIMIT:
                proc.kill()
                result["partial"] = True
                break
        proc.stdout.close()
        proc.wait(timeout=60)
    except subprocess.SubprocessError:
        result["partial"] = True
    finally:
        log = Path(err_file.name).read_text(errors="replace")
        Path(err_file.name).unlink(missing_ok=True)

    times = [float(m) for m in re.findall(r"pts_time:(\d+(?:\.\d+)?)", log)]
    times = sorted(t for t in times if 0.0 <= t <= max(duration, 0.0))
    result["cut_times"] = [round(t, 3) for t in times]
    result["estimated_cuts"] = len(times)
    if times and duration:
        spans = np.diff([0.0] + times + [duration])
        spans = spans[spans > 0.05]
        if spans.size:
            result["estimated_median_shot_seconds"] = round(float(np.median(spans)), 2)
            result["estimated_mean_shot_seconds"] = round(float(np.mean(spans)), 2)
    return result


# --------------------------------------------------------------------------- 接触表


def _font(size: int):
    for cand in FONT_CANDIDATES:
        if os.path.exists(cand):
            try:
                return ImageFont.truetype(cand, size)
            except OSError:
                continue
    return ImageFont.load_default()


def contact_sheet(frames: list[Path], duration: float, out: Path, cols: int = DEFAULT_CONTACT_COLS) -> Optional[Path]:
    if not frames:
        return None
    cell_w, label_h = 240, 22
    cell_h = int(cell_w * 9 / 16)
    rows = math.ceil(len(frames) / cols)
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + label_h)), (16, 16, 18))
    draw = ImageDraw.Draw(sheet)
    font = _font(13)
    for i, fp in enumerate(frames):
        with Image.open(fp) as im:
            im = im.convert("RGB")
            im.thumbnail((cell_w, cell_h))
        r, c = divmod(i, cols)
        x, y = c * cell_w, r * (cell_h + label_h)
        sheet.paste(im, (x + (cell_w - im.width) // 2, y + (cell_h - im.height) // 2))
        t = duration * (0.005 + ((i + 0.5) / len(frames)) * 0.99)
        draw.text((x + 6, y + cell_h + 3), f"{t / 60:.0f}:{t % 60:05.2f}", fill=(210, 210, 210), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=82)
    return out


# --------------------------------------------------------------------------- 主流程


def analyze_video(
    video: Path,
    out_dir: Path,
    samples: int = DEFAULT_SAMPLES,
    threshold: float = DEFAULT_THRESHOLD,
    progress: ProgressFn = _noop,
    keep_reference: bool = True,
    sha256: Optional[str] = None,
) -> dict:
    """跑完整套分析，返回 metrics 字典并把产物写进 ``out_dir``。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    progress("准备", 2, "定位 ffmpeg")

    info = probe(ffmpeg, video)
    duration = float(info.get("duration") or 0.0)
    if duration <= 0:
        raise ValueError(f"读不到时长，可能不是视频文件：{video}")

    frames_dir = out_dir / "frames"
    frames = sample_frames(ffmpeg, video, duration, samples, frames_dir, width=960, progress=progress)
    if not frames:
        raise ValueError(f"抽不到任何帧，ffmpeg 可能无法解码这个文件：{video}")

    progress("画面统计", 40, f"{len(frames)} 帧")
    stats = frame_stats(frames)

    with tempfile.TemporaryDirectory() as tmp:
        progress("运动采样", 52, "")
        motion = motion_samples(ffmpeg, video, duration, Path(tmp))
        progress("切点检测", 60, "开始扫描")
        cuts = detect_cuts(ffmpeg, video, duration, threshold=threshold, progress=progress)

    motion_vals = motion or [0.0]
    metrics = {
        "source": {
            "file": video.name,
            "bytes": video.stat().st_size,
            "mb": round(video.stat().st_size / 1_048_576, 1),
            "analyzed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sha256": sha256,
            "ffmpeg": ffmpeg_version(ffmpeg),
        },
        "container": {
            "duration": round(duration, 3),
            "fps": info.get("fps", 0.0),
            "width": info.get("width"),
            "height": info.get("height"),
            "orientation": info.get("orientation"),
            "video_codec": info.get("video_codec"),
            "has_audio": info.get("has_audio", False),
            "audio_codec": info.get("audio_codec"),
            "audio_hz": info.get("audio_hz"),
            "estimated_frames": int(round(duration * (info.get("fps") or 0))),
        },
        "sampling": {
            "sampled_frames": len(frames),
            "cut_detection_threshold": threshold,
            "cut_scale_width": CUT_SCALE_WIDTH,
            "motion_pairs": len(motion_vals),
        },
        "color": {
            "mean_luma": stats["mean_luma"],
            "luma_std": stats["luma_std"],
            "mean_contrast": stats["mean_contrast"],
            "mean_saturation": stats["mean_saturation"],
            "warmth_r_minus_b": stats["warmth_r_minus_b"],
            "tone_split": stats["tone_split"],
            "palette": stats["palette"],
        },
        "texture": {
            "mean_sharpness": stats["mean_sharpness"],
            "mean_grain": stats["mean_grain"],
            "dof_center_over_edge": stats["dof_center_over_edge"],
            "dof_frames_used": stats["dof_frames_used"],
            "dof_total_frames": stats["frames_measured"],
            "bottom_band_ratio": stats["bottom_band_ratio"],
        },
        "motion": {
            "mean_interframe_diff": round(float(np.mean(motion_vals)), 4),
            "max_interframe_diff": round(float(np.max(motion_vals)), 4),
            "samples": [round(v, 4) for v in motion_vals],
        },
        "rhythm": {
            "estimated_cuts": cuts["estimated_cuts"],
            "estimated_median_shot_seconds": cuts["estimated_median_shot_seconds"],
            "estimated_mean_shot_seconds": cuts["estimated_mean_shot_seconds"],
            "cut_times": cuts["cut_times"],
            "partial": cuts["partial"],
        },
    }

    progress("写报告", 92, "接触表 / 风格档案")
    sheet = contact_sheet(frames, duration, out_dir / "contact-sheet.jpg")
    metrics["artifacts"] = {
        "contact_sheet": str(sheet.relative_to(out_dir)) if sheet else None,
        "frames_dir": str(frames_dir.relative_to(out_dir)),
        "frames_kept": len(frames),
    }
    if keep_reference:
        ref = out_dir / ("reference" + video.suffix.lower())
        if ref.resolve() != video.resolve():
            shutil.copyfile(video, ref)
        metrics["artifacts"]["reference_copy"] = ref.name

    (out_dir / "reference_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    progress("完成", 100, "风格档案已生成")
    return metrics


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="分析参考视频，产出风格档案")
    ap.add_argument("--video", required=True, help="参考视频路径")
    ap.add_argument("--out", required=True, help="输出目录")
    ap.add_argument("--samples", type=int, default=DEFAULT_SAMPLES, help=f"抽帧数量（默认 {DEFAULT_SAMPLES}）")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help=f"硬切阈值（默认 {DEFAULT_THRESHOLD}）")
    ap.add_argument("--no-copy", action="store_true", help="不复制参考视频到输出目录")
    ap.add_argument("--sha256", default=None, help="上传时算好的 SHA-256，写进报告当收据")
    args = ap.parse_args(argv)

    video = Path(args.video).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()

    def progress(stage: str, pct: float, detail: str = "") -> None:
        bar = "#" * int(pct / 4)
        sys.stderr.write(f"\r[{stage}] {pct:5.1f}% {bar:<25} {detail}")
        sys.stderr.flush()

    metrics = analyze_video(
        video, out_dir, samples=args.samples, threshold=args.threshold,
        progress=progress, keep_reference=not args.no_copy, sha256=args.sha256,
    )
    sys.stderr.write("\n")
    try:
        from style_profile import build_style_profile, write_profile  # type: ignore

        profile = build_style_profile(metrics)
        write_profile(out_dir, profile)
        print(json.dumps({"out": str(out_dir), "candidates": len(profile["candidates"])}, ensure_ascii=False))
    except Exception as exc:  # pragma: no cover - 风格档案失败不掩盖实测值
        print(f"风格档案生成失败（实测值已落盘）：{exc}")
    print(f"完成：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
