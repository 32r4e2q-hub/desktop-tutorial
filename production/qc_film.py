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

六条踩过的坑写在这里，别改回去：
1. 全帧统计量必须先排除「片子本来就该变」的位置（切点、淡入淡出），否则量到的是剪辑；
2. 任何在全幅上量的指标都要先剔除上下黑边与字幕带，否则画框自己的硬边会被当成"8 像素对齐"；
3. 8-bit 素材里"相邻像素差恰为 1 灰阶"占多数是**抖动/颗粒**的正常表现，不能当假轮廓判据
   —— 所以 banding 只作参考，不给判定；
4. 没有未处理的原始帧就没有几何 ground truth，本脚本**不能**宣布"无畸变"，
   只能给出对照量；畸变的判定证据是 review/ 下的密扫表与裁放图（人工逐格）。
5. 采样必须按**帧序号**精确抽取（`select='not(mod(n,15))'`），不许用 `fps=2` 滤镜：
   实测 `fps=2` 输出的第 m 帧是输入第 15m+7 帧（恒定 +7 帧滞后，framemd5 逐帧对过，
   360/360 吻合）——用它采样，分段归因在切点附近会错位 0.23 秒，"S02 的峰值"实际是
   S03 首帧，"S27 的峰值"实际是 S28 的第 5 帧。select 采样已用同一方法验证为精确映射。
6. 块效应**比值**必须配一个**绝对强度**：比值在平滑暗场里分母趋零，0.18 灰阶的
   不可见起伏也能算出 1.0 的"超标"。尾部门限只看比值，等于给每个夜戏镜头发红牌。
   所以尾部改判绝对强度（8px 边界梯度超过内部的灰阶数），比值只留中位数守编码链。
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
    # 块效应比值中位数：守编码链（旧均值口径精确采样：旧双压管线 0.174、新管线 0.115；
    # 截尾口径下新片 0.085、旧片 0.102——0.14 在两种口径下都有裕量）
    "blocking_p50_max": 0.14,
    # 块效应绝对强度上限（灰阶）：守"某一帧出现肉眼可见的强网格"。
    # 实测（round-6 起截尾口径）：全对齐 JPEG 网格 0.54–0.65、自带竖线结构的
    # 干净内容（S25 试剂架）0.38、PNG 卡面 ≤0.22、平滑暗场 0.05–0.26。
    # 0.5 落在"干净 ≤0.38"与"强网格 ≥0.54"之间；0.38–0.5 是未验证带，
    # 落进去必须先看裁放图再下结论。旧均值口径的 0.41–2.23 卡面数是纸沿误报，
    # 见 review/qc-round6-paper-edge-2026-09-14.md。
    "blocking_abs_max_allow": 0.5,
    "overexposed_fraction_max": 0.06,
    "overexposed_frame_count_max": 0,
    "underexposed_p95_reference": 0.80,
    "saturation_mean_min": 0.02,
    "saturation_mean_max": 0.42,
    "flash_reversal_spikes_max": 0,
    "flash_reversal_amp_min": 0.045,      # 小于此幅度的反向不算异常（颗粒/电平噪声）
    "letterbox_min_frame_fraction": 0.80,   # 遮幅必须"整段都在"才算，个别帧的暗构图不算
    "letterbox_static_px_tol": 2,           # 真遮幅钉在画框边上，宽度在段内几乎不变；
                                            # 场景暗部（S14 的机舱壁）随运镜漂移，15 个采样帧里
                                            # 量到 0–40px。宽度极差超过 2px 的不算遮幅。
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


def blocking_parts(gray: np.ndarray) -> tuple:
    """8×8 块边界上的水平梯度 vs 块内部：返回 (比值, 绝对强度灰阶, 内部梯度)。

    只在画面区内量：黑边与字幕带自己的硬边界就是"8 像素对齐的强边缘"，
    全幅量会量到画框而不是画质。

    比值 = (边界-内部)/内部：编码链退化（二次压缩）会把它推高，适合守中位数。
    绝对强度 = 边界-内部（灰阶）：比值在平滑暗场里分母趋零时会虚高，
    尾部必须看绝对值——0.2 灰阶的起伏肉眼不可见，2 灰阶的网格在 2× 裁放下可辨。

    2026-09-14 round-6：边界/内部都改用"列均值的双侧 2% 截尾均值"，不再用全体均值。
    起因：信息卡的纸面左右沿（两条约 190 灰阶的竖直台阶）恰好落在 8k+7 列上，
    单帧就能把均值口径的绝对强度推高 +0.8——漂移相位不同，此起彼伏，
    seq15/seq16 的绝对强度 FLAG（0.56–0.88）几乎全是它，不是什么编码网格。
    真网格是遍布全帧的周期结构，截尾 2% 照样量得到（全对齐 JPEG 网格截尾后
    仍有 0.54–0.65，照样超 0.5 门限）；孤立的画面强边缘只占个位数列，
    被截尾吃掉。门限数字不动（0.5/0.14），动的是统计量本身。
    证据：production/dbcooper/review/qc-round6-paper-edge-2026-09-14.md。
    """
    pic = gray[PICTURE_ROWS[0]:PICTURE_ROWS[1]]
    gx = np.abs(np.diff(pic.astype(float), axis=1)).mean(axis=0)
    edge = _trimmed_mean(gx[7::8])
    inner = _trimmed_mean(np.delete(gx, np.arange(7, len(gx), 8)))
    numer = float(edge - inner)
    return float(numer / max(inner, 1e-6)), numer, float(inner)


def _trimmed_mean(values: np.ndarray, fraction: float = 0.02) -> float:
    """双侧截尾均值：掐掉最热/最冷的各 `fraction` 列再平均。

    列是按"整列 800 行的平均梯度"排的：画面里的孤立强边缘（卡纸沿、
    门框、试剂架竖杆）只占个位数列，必然落在被掐掉的两头；真正的 8px
    周期网格遍布全帧，掐 2% 不伤筋骨。"""
    ordered = np.sort(np.asarray(values, dtype=float).ravel())
    if ordered.size == 0:
        return 0.0
    cut = int(ordered.size * fraction)
    core = ordered[cut:ordered.size - cut] if cut else ordered
    return float(core.mean())


def blocking_index(gray: np.ndarray) -> float:
    """比值部分（兼容旧口径；新闸门同时看 `blocking_parts` 的绝对强度）。"""
    ratio, _, _ = blocking_parts(gray)
    return ratio


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


def is_static_mat(widths, frac_min: float, tol_px: float) -> bool:
    """这段量到的"纯黑宽度"是不是钉在画框边上的 mat。

    widths：段内各采样帧的 lead() 值。真遮幅/模型自拼 mat 同时满足三条：
    出现比例够高（整段都在）、中位数 >0（真有宽度）、极差 ≤ tol（静止不动）。
    场景暗部（S14 机舱壁：[0,7,…,40]）过不了"静止"这一条——随运镜漂移的
    黑不是 mat。单元测试直接测这个函数，不需要 ffmpeg。
    """
    vals = [int(v) for v in widths]
    if not vals:
        return False
    present = sum(1 for v in vals if v > 0) / len(vals)
    pos = [v for v in vals if v > 0]
    if not pos or present < frac_min:
        return False
    return (max(pos) - min(pos)) <= tol_px


def load_edl(project: Path) -> list:
    """读 delivery/edit-decision-list.json → [(id, kind, start_s, end_s)]，用于分段归因。"""
    path = project / "delivery" / "edit-decision-list.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = data if isinstance(data, list) else data.get("segments", [])
    return [(s.get("id", "?"), s.get("kind", ""), s["start_frame"] / FPS, s["end_frame"] / FPS)
            for s in segs if "start_frame" in s and "end_frame" in s]


def sample_saturation(film: Path, step: int, every: int = 8) -> list:
    """每 every×step 帧取 1 帧量饱和度（max-min 通道均值 / 255）。

    与主采样同一口径：按帧序号精确抽取，不用 fps 滤镜（见模块注释第 5 条）。
    """
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(film),
         "-vf", f"select='not(mod(n,{step * every}))'", "-vsync", "0",
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
    # 精确采样：第 m 个输出 = 输入第 m×step 帧（framemd5 验证过 360/360 精确；
    # fps 滤镜有恒定 +7 帧滞后，见模块注释第 5 条）。默认 fps=2 ⇒ step=15。
    step = max(1, round(FPS / args.fps))
    per_segment: dict[str, dict] = {}
    luma: list[float] = []
    times: list[float] = []
    blocking: list[float] = []
    blocking_abs: list[float] = []
    step_ratio: list[float] = []
    overex: list[float] = []
    underex: list[float] = []
    axis: list[float] = []
    per_frame = []
    n = 0

    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(film),
         "-vf", f"select='not(mod(n,{step}))'", "-vsync", "0",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        stdout=subprocess.PIPE, bufsize=1 << 20)
    size = FRAME_W * FRAME_H
    assert proc.stdout is not None
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        g = np.frombuffer(buf, dtype=np.uint8).reshape(FRAME_H, FRAME_W).astype("float32")
        t = n * step / FPS
        mean_l = float(g.mean())
        blk, numer, _ = blocking_parts(g)
        bx = float((g >= 250).mean())
        un = float((g <= 6).mean())
        ax = axis_aligned_fraction(g)
        times.append(t)
        luma.append(mean_l / 255.0)
        blocking.append(blk)
        blocking_abs.append(numer)
        step_ratio.append(quantized_step_ratio(g))
        overex.append(bx)
        underex.append(un)
        axis.append(ax)

        sid, kind = seg_of(t)
        rec = per_segment.setdefault(sid or "?", {
            "kind": kind, "frames": 0, "blocking": [], "blocking_abs": [], "overexposed": [],
            "border_frames": {k: [] for k in ("top", "bottom", "left", "right")}})
        rec["frames"] += 1
        rec["blocking"].append(blk)
        rec["blocking_abs"].append(numer)
        rec["overexposed"].append(bx)
        if mean_l > 25.0 and kind != "graphic":       # 淡入淡出帧与卡面段不参与黑边判定
            for k in ("top", "bottom", "left", "right"):
                rec["border_frames"][k].append(lead(g, k))
        # frame 记的是输入流里的真帧号（select 精确采样，可直接 select 复现），
        # 不是采样序号——旧版 fps 采样把两者混为一谈，错位 7 帧都没人发现。
        per_frame.append({"frame": n * step, "t": round(t, 2), "segment": sid,
                          "blocking": round(blk, 4), "blocking_abs": round(numer, 4),
                          "step_ratio": round(step_ratio[-1], 4)})
        n += 1
    proc.wait()
    if not n:
        print("[qc] 解帧失败", file=sys.stderr)
        return 2

    frac_min = thresholds["letterbox_min_frame_fraction"]
    for rec in per_segment.values():
        # 只有"整段都在 + 宽度静止"的纯黑行才算遮幅；个别帧量到的是暗构图，
        # 随运镜漂移的是场景暗部，都不是 mat。widths 原样存进报告，
        # 测试用同一谓词 is_static_mat 从原始宽度重新判定，不读这里的结论。
        rec["border"] = {}
        for k, vals in rec["border_frames"].items():
            arr = np.array(vals, dtype=float)
            present = float((arr > 0).mean()) if arr.size else 0.0
            pos = arr[arr > 0]
            rec["border"][k] = {
                "median": int(np.median(pos)) if present else 0,
                "presence": round(present, 3),
                "min": int(pos.min()) if present else 0,
                "max": int(pos.max()) if present else 0,
                "static": bool(is_static_mat(vals, frac_min, thresholds["letterbox_static_px_tol"])),
                "widths": [int(v) for v in vals],
            }
        rec.pop("border_frames", None)
    for rec in per_segment.values():
        rec["blocking_p50"] = round(float(np.percentile(rec["blocking"], 50)), 4)
        rec["blocking_max"] = round(float(max(rec["blocking"])), 4)
        rec["blocking_abs_max"] = round(float(max(rec["blocking_abs"])), 4)
        rec["overexposed_max"] = round(float(max(rec["overexposed"])), 5)
        for key in ("blocking", "blocking_abs", "overexposed"):
            rec.pop(key, None)

    saturation = sample_saturation(film, step)
    blk_arr = np.array(blocking)
    abs_arr = np.array(blocking_abs)
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

    # 黑边：设计内的段列白名单；其余段同时满足"整段都在 + 宽度静止"才是 FLAG。
    # "静止"是关键：真遮幅/mat 钉在画框边上，宽度在段内几乎不变；场景暗部
    # （S14 的机舱壁被 eq 压成纯黑）随运镜漂移，15 个采样帧里量到 0–40px。
    designed = set(thresholds["designed_border_segments"])
    static_tol = thresholds["letterbox_static_px_tol"]
    stray = {sid: {k: {"median": v["median"], "presence": v["presence"],
                       "min": v["min"], "max": v["max"]}
                   for k, v in rec["border"].items() if v["static"]}
             for sid, rec in per_segment.items() if sid not in designed}
    stray = {sid: d for sid, d in stray.items() if d}

    checks = []

    def add(key, desc, measured, ok, note):
        checks.append({"name": key, "desc": desc, "measured": measured, "ok": bool(ok), "note": note})

    err_lines = decode_error_lines(film)
    add("resolution", "交付片为 1920x1080", [w, h], (w, h) == (FRAME_W, FRAME_H),
        f"{w}x{h}，要求 {FRAME_W}x{FRAME_H}")
    add("decode_errors", "全片完整解码无错误行", [len(err_lines)], not err_lines,
        "; ".join(err_lines[:3]) if err_lines else "ffmpeg -v error -xerror 全片解码，无 error/invalid/conceal 行")
    p50 = float(np.percentile(blk_arr, 50))
    abs_max = float(abs_arr.max())
    add("blocking", "8x8 块效应不超阈值（压缩伪影）",
        [round(p50, 4), round(abs_max, 4)],
        p50 <= thresholds["blocking_p50_max"]
        and abs_max <= thresholds["blocking_abs_max_allow"],
        f"画面区内量；比值 p50={p50:.3f}（上限 {thresholds['blocking_p50_max']}，守编码链）"
        f"、绝对强度 max={abs_max:.3f} 灰阶（上限 {thresholds['blocking_abs_max_allow']}，"
        f"守单帧强网格）。校准（精确采样）：旧双压管线比值 p50=0.174、新管线 0.115；"
        f"全对齐 JPEG 网格绝对强度 0.54–0.65（截尾口径，照样超标）、"
        f"干净竖线内容（S25 试剂架）0.37、平滑暗场 ≤0.26。"
        f"比值 p90={np.percentile(blk_arr, 90):.3f} 只作参考——"
        f"它在平滑暗场里是分母噪声（0.18 灰阶起伏 ⇒ 比值 1.0），不判定。")
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
        f"且该段 ≥{int(frac_min * 100)}% 的采样帧都有，且宽度极差 ≤{static_tol}px（静止）；"
        f"白名单（设计内）{sorted(designed)}；卡面段与淡入淡出帧不参与；违规段：{stray or '无'}。"
        f"偏暗但有内容的行不计入；随运镜漂移的场景暗部（S14 机舱壁 0–40px）"
        f"不算遮幅——真 mat 钉在画框边上，不会漂。")
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
        "sampler": f"select='not(mod(n,{step}))' + vsync 0（按帧序号精确抽取；"
                   "旧版 fps 滤镜有恒定 +7 帧滞后，2026-09-14 起弃用）",
        "sampled_frames": n,
        "picture_rows_measured": list(PICTURE_ROWS),
        "thresholds": thresholds,
        "checks": checks,
        "metrics": {
            "blocking_mean": round(float(blk_arr.mean()), 4),
            "blocking_p50": round(float(np.percentile(blk_arr, 50)), 4),
            "blocking_p90_reference": round(float(np.percentile(blk_arr, 90)), 4),
            "blocking_p95_reference": round(float(np.percentile(blk_arr, 95)), 4),
            "blocking_max": round(float(blk_arr.max()), 4),
            "blocking_abs_max": round(float(abs_arr.max()), 4),
            "blocking_abs_p99": round(float(np.percentile(abs_arr, 99)), 4),
            "step_ratio_p95_reference": round(float(np.percentile(step_ratio, 95)), 4),
            "saturation_mean": round(float(sat_arr.mean()), 4),
            "saturation_p95": round(float(np.percentile(sat_arr, 95)), 4),
            "overexposed_max": round(float(over_arr.max()), 5),
            "underexposed_p95": round(float(np.percentile(underex, 95)), 4),
            "luma_mean": round(float(np.mean(lum) * 255.0), 2),
            "luma_max": round(float(np.max(lum) * 255.0), 2),
            "flash_reversal_spikes": len(spike_frames),
            "flash_spike_times_s": spike_frames,
            "letterbox_by_segment": {sid: {k: v for k, v in rec["border"].items()
                                                 if v["median"] > 0}
                                     for sid, rec in per_segment.items()
                                     if max(v["median"] for v in rec["border"].values()) > 0},
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
