#!/usr/bin/env python3
"""全时长素材复审包：把「完整片段审看」里能机器化的部分做掉，产出供人工看片的证据。

沙箱连不上 Agnes CDN、也读不到 Actions 日志；``qa/`` 里 2 fps、384×216 的接触表
细节不足以排除伪文字、标签带、形状畸变、闪变与镜头中途换场。本脚本读取由
``fetch_sources.py`` 按 SHA-256 回执回填的源素材，为每个 Agnes 镜头产出：

* ``<out>/<sid>.jpg``  —— 全时长均匀抽 16 帧、640×360 拼 4×4，细节够读小伪字；
* ``<out>/<sid>.json`` —— 全时长 64×64 灰度签名逐帧差序列的判定：冻结段、单帧闪变
  尖峰、硬切候选（中途换场嫌疑），口径与 ``production/review_film.py`` 的标定一致
  （真静止中位数 ≤0.08、微动 ≥0.21，故冻结用 0.10；硬切用 40；闪变尖峰用 25）。

只产出证据，不产出结论：视觉验收仍由人工对照抽帧包与指标完成，结论登记在
``制作过程.md``。任何一项指标越界或抽帧发现问题，都只重做对应镜头的 GEN_REQUEST。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results.json"
PLAN = HERE / "story.json"

FROZEN_DELTA = 0.10      # 64x64 灰度签名逐帧差低于此视为静止（标定空档 0.08–0.21 内）
FROZEN_MIN_SECONDS = 1.0  # 连续静止超过 1 秒才报冻结段
HARD_CUT_DELTA = 40.0    # 单帧差超过此视为硬切（中途换场嫌疑）
FLICKER_DELTA = 25.0     # 超过此但低于硬切：闪变/突变尖峰，人工看帧确认

SIG = 64


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # 本地沙箱的备用静态 ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise RuntimeError("需要 ffmpeg：apt install ffmpeg 或 pip install imageio-ffmpeg")


def motion_metrics(path: Path) -> dict:
    import av
    import numpy as np

    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        fps = float(stream.average_rate)
        prev = None
        diffs: list[float] = []
        frames = 0
        for frame in container.decode(stream):
            gray = frame.reformat(width=SIG, height=SIG, format="gray").to_ndarray()
            small = gray.astype(np.float32)
            if prev is not None:
                diffs.append(float(np.mean(np.abs(small - prev))))
            prev = small
            frames += 1
    arr = [round(d, 3) for d in diffs]
    frozen, start = [], None
    for i, d in enumerate(diffs):
        if d < FROZEN_DELTA:
            if start is None:
                start = i
        else:
            if start is not None and (i - start) / fps >= FROZEN_MIN_SECONDS:
                frozen.append({"from_frame": start + 1, "to_frame": i,
                               "start_s": round(start / fps, 2), "end_s": round(i / fps, 2),
                               "seconds": round((i - start) / fps, 2)})
            start = None
    if start is not None and (len(diffs) - start) / fps >= FROZEN_MIN_SECONDS:
        frozen.append({"from_frame": start + 1, "to_frame": len(diffs),
                       "start_s": round(start / fps, 2), "end_s": round(len(diffs) / fps, 2),
                       "seconds": round((len(diffs) - start) / fps, 2)})
    spikes = [{"frame": i + 1, "t_s": round(i / fps, 2), "delta": d}
              for i, d in enumerate(diffs) if FLICKER_DELTA <= d < HARD_CUT_DELTA]
    cuts = [{"frame": i + 1, "t_s": round(i / fps, 2), "delta": d}
            for i, d in enumerate(diffs) if d >= HARD_CUT_DELTA]
    ordered = sorted(diffs)
    median = ordered[len(ordered) // 2] if ordered else 0.0
    return {"fps": round(fps, 3), "frames": frames, "delta_median": round(median, 3),
            "delta_max": round(max(diffs), 3) if diffs else 0.0,
            "frozen_runs": frozen, "flicker_spikes": spikes, "hard_cut_candidates": cuts}


def make_strip(ffmpeg: str, path: Path, out: Path, duration: float) -> None:
    fps = 16.0 / max(duration, 1e-6)
    subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(path),
                    "-vf", f"fps={fps:.4f},scale=640:360:force_original_aspect_ratio=decrease,"
                           f"pad=640:360:(ow-iw)/2:(oh-ih)/2,tile=4x4",
                    "-frames:v", "1", "-q:v", "3", str(out)], check=True)
    if not out.exists():
        raise RuntimeError(f"review strip was not produced for {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--clips", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=HERE / "qa-full")
    parser.add_argument("--only", default="")
    args = parser.parse_args()

    project = json.loads(PLAN.read_text(encoding="utf-8"))
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    args.out.mkdir(parents=True, exist_ok=True)
    ffmpeg = ffmpeg_exe()

    report = {"packed": [], "skipped": [], "flags": []}
    for shot in project["shots"]:
        if shot["kind"] != "agnes":
            continue
        sid = shot["id"]
        if only and sid not in only:
            continue
        receipt = results.get("shots", {}).get(sid, {})
        clip = args.clips / f"{sid}.mp4"
        if receipt.get("status") != "completed" or not clip.exists():
            report["skipped"].append(sid)
            print(f"SKIP {sid}: no completed receipt or missing clip", flush=True)
            continue
        found = digest(clip)
        if found != receipt.get("sha256"):
            raise RuntimeError(f"{sid}: clip SHA-256 {found} != receipt {receipt.get('sha256')}")
        info = motion_metrics(clip)
        info.update(sha256=found, duration=round(receipt.get("inspection", {}).get("duration", 0.0), 3),
                    width=receipt.get("inspection", {}).get("width"),
                    height=receipt.get("inspection", {}).get("height"))
        make_strip(ffmpeg, clip, args.out / f"{sid}.jpg", info["duration"] or 7.0)
        (args.out / f"{sid}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
        flags = []
        if info["frozen_runs"]:
            flags.append("frozen")
        if info["hard_cut_candidates"]:
            flags.append("hard_cut")
        if info["flicker_spikes"]:
            flags.append("flicker")
        report["packed"].append(sid)
        if flags:
            report["flags"].append({"id": sid, "flags": flags})
        print(f"PACKED {sid} median={info['delta_median']} max={info['delta_max']} "
              f"frozen={len(info['frozen_runs'])} cuts={len(info['hard_cut_candidates'])} "
              f"spikes={len(info['flicker_spikes'])}", flush=True)

    (args.out / "review-pack-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if report["skipped"]:
        raise RuntimeError("Missing clips for: " + ", ".join(report["skipped"])
                           + "（先跑 fetch_sources.py 或等 GEN_REQUEST 续跑完成）")
    print("REVIEW_PACK_DONE packed=" + str(len(report["packed"])), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
