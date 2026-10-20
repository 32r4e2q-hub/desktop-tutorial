#!/usr/bin/env python3
"""动作合理性闸门：拦住「走过去又走回来」这类倒放/回摆。

背景：CogVideoX-Flash 每镜素材固定 5.108 s。旧版出片在槽位超过 1.33× 时用
「正放 + 倒放补差」凑时长，空镜没事，但画面里一旦有人在走，倒放就等于人物
先往前走、再原路退回——观众一眼就能看出来。2026-10-20 起 render.py 用
0.62–1.0 倍速的轻度慢放替代倒放，本闸门负责把这类问题挡在交付前：

1. 结构检查（硬失败）：EDL 里任何一段带 ``pingpong`` 就是倒放，直接 FAIL；
2. 实测检查（硬失败）：逐镜测光流，把每一镜切成前后两半，比较两半的平均位移
   方向；只要两半的位移足够大（|a|,|b| ≥ 0.15 px/帧）且夹角接近 180°
   （cos ≤ −0.55），说明画面里的东西先往一边走、又往另一边走，判为 REVERSE。

用法：
    python3 production/zhoukehua2012/tools/check_motion.py --film <成片> \
        --out production/zhoukehua2012/delivery/motion-report.json
退出码 1 表示 FAIL（结构或实测任一不过）。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
FPS = 30.0
W, H = 480, 270
SAMPLE_FPS = 10.0          # 每 100 ms 取一帧，够看行走方向
MIN_MAG = 0.15             # px/帧：低于这个数当作静止，不做方向判定
COS_LIMIT = -0.55          # 夹角 > 123° 视为「往回走」


def decode(film: Path, start: float, end: float) -> np.ndarray:
    cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(film),
        "-vf", f"fps={SAMPLE_FPS},scale={W}:{H},format=gray", "-f", "rawvideo", "-",
    ]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (W * H)
    return np.frombuffer(raw, dtype=np.uint8).reshape(n, H, W)


def flow_vectors(frames: np.ndarray) -> np.ndarray:
    out = []
    for a, b in zip(frames[:-1], frames[1:]):
        f = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 21, 3, 5, 1.2, 0)
        # 只看中间一半，避开边框裁切与镜头运动残留
        c = f[H // 4:3 * H // 4, W // 4:3 * W // 4]
        out.append((float(c[..., 0].mean()), float(c[..., 1].mean())))
    return np.array(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--film", type=Path, required=True)
    ap.add_argument("--project", type=Path, default=PROJ)
    ap.add_argument("--out", type=Path, default=PROJ / "delivery" / "motion-report.json")
    args = ap.parse_args()

    edl = json.loads((args.project / "delivery" / "edit-decision-list.json").read_text(encoding="utf-8"))
    if not args.film.is_file():
        raise SystemExit(f"missing film: {args.film}")

    pingpong = [s["id"] for s in edl if s.get("pingpong")]
    frames_checked = 0
    reversals = []
    rows = []
    for seg in edl:
        t0, t1 = seg["start_frame"] / FPS, seg["end_frame"] / FPS
        frames = decode(args.film, t0, t1)
        frames_checked += len(frames)
        if len(frames) < 6:
            continue
        v = flow_vectors(frames)
        k = len(v) // 2
        a, b = v[:k].mean(0), v[k:].mean(0)
        na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
        cos = float(a @ b / (na * nb + 1e-9))
        row = {"shot": seg["id"], "start": round(t0, 2), "end": round(t1, 2),
               "mag_first": round(na, 3), "mag_second": round(nb, 3), "cos": round(cos, 3),
               "time_stretch": seg.get("time_stretch")}
        if na >= MIN_MAG and nb >= MIN_MAG and cos <= COS_LIMIT:
            row["verdict"] = "REVERSE"
            reversals.append(row["shot"])
        else:
            row["verdict"] = "ok"
        rows.append(row)

    status = "PASS" if not pingpong and not reversals else "FAIL"
    report = {
        "film": args.film.name,
        "status": status,
        "policy": "禁止乒乓倒放；槽位不足只能用 1.0–1.60× 轻度慢放（render.py 已硬编码）",
        "edl_segments": len(edl),
        "frames_sampled": frames_checked,
        "pingpong_segments": pingpong,
        "reversals": reversals,
        "shots": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"motion {status}: {len(edl)} 段 / 采样 {frames_checked} 帧 / 倒放段 {len(pingpong)} / 反向段 {len(reversals)}")
    for sid in pingpong:
        print(f"  pingpong: {sid}")
    for r in rows:
        if r["verdict"] != "ok":
            print(f"  reverse: {r['shot']} {r['start']}–{r['end']} |a|={r['mag_first']} |b|={r['mag_second']} cos={r['cos']}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
