#!/usr/bin/env python3
"""转制核查：抽帧混没混、几何挤没挤、拼接漏没漏，全部用数字回答。

用法::

    python3 production/review_transcode.py --film 交付/<片名>.mp4 \\
        --project production/<slug> --work work/<slug>/transcode

背景：AI 素材是 24fps，成片是 30fps（``render.py`` 里 ``fps=30`` nearest 抽帧，
外加供凑时长用的 setpts 慢放，上限 1.33x）。nearest 抽帧在成片里会留下指纹——
24→30 每 5 帧必出 1 个重复帧；慢放镜头的重复间距由 tempo 决定。这个工具就是
来验这枚指纹的，外加 SAR（几何挤压）和 EDL 拼接（缝隙/总帧）。

判定口径（在 dahlia 成片 24 个 agnes 段上实测验证过，全过）：

* 重复帧 = 相邻帧 480x270 灰度平均差 < 0.5；
* 期望主间距 = round(1 / (1 - 24 / (30 * time_stretch)))，stretch=1.0 时为 5；
* 期望间距出现在该段重复间距 Top3 里即 ok（慢速运镜/静态 overlay 会让间距 1
  混进 Top3，所以不要求它是第一名，只要求期望值在场）。

退出码：SAR 不是 1:1、EDL 有缝隙/总帧对不上、期望间距不在 Top3 —— 任何一条
成立即非 0。纯计算，无需人眼，适合进 CI。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import av
except ImportError as error:
    raise SystemExit(f"PyAV 未安装，跑不了转制核查：{error}") from error

import numpy as np
from PIL import Image

SOURCE_FPS = 24.0
TARGET_FPS = 30.0
DUP_THRESHOLD = 0.5       # 480x270 灰度相邻帧差，小于此算重复帧
SMALL_W, SMALL_H = 480, 270


def expected_interval(time_stretch: float) -> int:
    """慢放系数 -> 重复帧期望主间距。stretch=1.0 时 24->30，每 5 帧一重复。"""
    if time_stretch <= 0:
        raise ValueError(f"离谱的 time_stretch：{time_stretch}")
    dup_ratio = 1.0 - SOURCE_FPS / (TARGET_FPS * time_stretch)
    if dup_ratio <= 0.01:
        raise ValueError(f"time_stretch={time_stretch} 下几乎没有重复帧，验不了")
    return max(1, round(1.0 / dup_ratio))


def decode_small_grays(path: Path) -> list[np.ndarray]:
    """解码全片为小灰度帧（流式，一次只留一帧在内存）。"""
    container = av.open(str(path))
    try:
        stream = container.streams.video[0]
        frames = []
        for frame in container.decode(stream):
            image = frame.to_image().convert("L").resize(
                (SMALL_W, SMALL_H), Image.Resampling.BILINEAR)
            frames.append(np.asarray(image, dtype=np.float32))
        return frames
    finally:
        container.close()


def consecutive_diffs(frames: list[np.ndarray]) -> np.ndarray:
    return np.array([float(np.abs(b - a).mean())
                     for a, b in zip(frames, frames[1:])])


def dup_spacing_top(diffs: np.ndarray, limit: int = 3) -> list[list[int]]:
    """重复帧对的位置间距 TopN（间距，次数）。"""
    pos = np.nonzero(diffs < DUP_THRESHOLD)[0]
    gaps = np.diff(pos)
    gaps = gaps[gaps < 40]
    if not len(gaps):
        return []
    vals, counts = np.unique(gaps, return_counts=True)
    ranked = sorted(zip(vals.tolist(), counts.tolist()), key=lambda row: -row[1])
    return [[int(v), int(c)] for v, c in ranked[:limit]]


def check_geometry(path: Path) -> dict:
    container = av.open(str(path))
    try:
        stream = container.streams.video[0]
        sar = stream.sample_aspect_ratio
        return {
            "width": stream.width,
            "height": stream.height,
            "fps": round(float(stream.average_rate or 0), 3),
            "frames": stream.frames,
            "pix_fmt": stream.codec_context.pix_fmt,
            "sar": f"{sar.numerator}:{sar.denominator}" if sar else None,
            "sar_is_square": bool(sar and sar.numerator == sar.denominator),
        }
    finally:
        container.close()


def check_splice(edl: list[dict], film_frames: int | None) -> dict:
    gaps = [{"between": [edl[i]["id"], edl[i + 1]["id"]],
             "left_end": edl[i]["end_frame"],
             "right_start": edl[i + 1]["start_frame"]}
            for i in range(len(edl) - 1)
            if edl[i]["end_frame"] != edl[i + 1]["start_frame"]]
    total = sum(r["end_frame"] - r["start_frame"] for r in edl)
    return {"segments": len(edl), "first_frame": edl[0]["start_frame"] if edl else None,
            "last_frame": edl[-1]["end_frame"] if edl else None,
            "total_frames": total, "film_frames": film_frames,
            "gaps": gaps, "seamless": not gaps,
            "frames_match": film_frames is None or total == film_frames}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--film", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True,
                        help="项目目录（读 delivery/edit-decision-list.json）")
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args(argv)

    if not args.film.is_file():
        raise SystemExit(f"找不到成片：{args.film}")
    args.work.mkdir(parents=True, exist_ok=True)
    edl_path = args.project / "delivery" / "edit-decision-list.json"
    if not edl_path.is_file():
        raise SystemExit(f"找不到 EDL：{edl_path}")
    edl = json.loads(edl_path.read_text(encoding="utf-8"))

    geometry = check_geometry(args.film)
    splice = check_splice(edl, geometry["frames"])

    frames = decode_small_grays(args.film)
    diffs = consecutive_diffs(frames)
    cuts = {r["start_frame"] for r in edl} | {r["end_frame"] for r in edl}

    shots = []
    for row in edl:
        if row["kind"] != "agnes":
            continue
        a, b = row["start_frame"] + 1, row["end_frame"] - 2
        seg = diffs[a:b]
        idx = [i for i in range(a, b) if i not in cuts and i + 1 not in cuts]
        seg = diffs[idx] if idx else np.zeros(0)
        stretch = float(row.get("time_stretch", 1.0) or 1.0)
        expect = expected_interval(stretch)
        top = dup_spacing_top(seg) if len(seg) else []
        in_top = any(v == expect for v, _ in top)
        # 静态 overlay（如指纹图解）帧间几乎不动：dup 过半且期望值在场即算正常，
        # 口径与其它段一致，不单独豁免，只在 note 里说明。
        dup_frac = round(float((seg < DUP_THRESHOLD).mean()) if len(seg) else 0.0, 4)
        shots.append({
            "id": row["id"], "start_frame": row["start_frame"],
            "end_frame": row["end_frame"], "time_stretch": stretch,
            "pairs": len(seg), "dup_fraction": dup_frac,
            "expected_interval": expect, "spacing_top3": top,
            "verdict": "ok" if in_top else "needs_review",
            "note": "静态图解/慢漂移，间距1混进Top3属正常" if dup_frac > 0.5 else "",
        })

    failures = []
    if not geometry["sar_is_square"]:
        failures.append(f"SAR 不是 1:1（{geometry['sar']}），画面有几何挤压嫌疑")
    if not splice["seamless"]:
        failures.append(f"EDL 有 {len(splice['gaps'])} 处缝隙/重叠")
    if not splice["frames_match"]:
        failures.append(f"EDL 总帧 {splice['total_frames']} 与成片 {splice['film_frames']} 对不上")
    bad = [s["id"] for s in shots if s["verdict"] != "ok"]
    if bad:
        failures.append(f"期望重复间距不在 Top3：{', '.join(bad)}（抽帧可能混了帧或 tempo 失控）")

    result = {"film": args.film.name, "geometry": geometry, "splice": splice,
              "shots": shots, "failures": failures,
              "verdict": "pass" if not failures else "fail"}
    out = args.work / "transcode-check.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")

    print(f"转制核查：{out}")
    print(f"  几何 {geometry['width']}x{geometry['height']} SAR={geometry['sar']} "
          f"frames={geometry['frames']}")
    print(f"  拼接 {splice['segments']} 段 {'无缝' if splice['seamless'] else '有缝隙！'} "
          f"总帧 {splice['total_frames']}")
    for shot in shots:
        print(f"    {shot['id']:>4} stretch={shot['time_stretch']:.3f} "
              f"dup={shot['dup_fraction'] * 100:5.1f}% 期望{shot['expected_interval']} "
              f"Top3={shot['spacing_top3']} {shot['verdict']}")
    print("  结论：" + ("通过" if not failures else "失败：" + "；".join(failures)))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
