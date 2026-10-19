#!/usr/bin/env python3
"""换脸前的体检：照片能不能用、视频里有几张脸、该用哪套参数。

用法:
    python3 precheck.py --photo 我.jpg --video 参考视频.mp4
    python3 precheck.py --photo 我.jpg --video 参考视频.mp4 --samples 20 --report 体检.json

只依赖 OpenCV（pip install opencv-python-headless），不下载任何模型。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖：pip install -r requirements.txt  （只需要 opencv-python-headless）")


CASCADES = {
    "frontal": "haarcascade_frontalface_alt2.xml",
    "profile": "haarcascade_profileface.xml",
}


def _cascade(name: str):
    path = Path(cv2.data.haarcascades) / CASCADES[name]
    c = cv2.CascadeClassifier(str(path))
    return None if c.empty() else c


def detect_faces(bgr, min_ratio: float = 0.04):
    """返回 [(x, y, w, h), ...]，按面积从大到小。min_ratio = 脸最短边占画面的比例下限。"""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    h, w = gray.shape[:2]
    min_side = max(24, int(min(h, w) * min_ratio))
    found = []
    for name in ("frontal", "profile"):
        c = _cascade(name)
        if c is None:
            continue
        found.extend(c.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side)))
    boxes = [tuple(int(v) for v in b) for b in found]
    # 去掉高度重叠的重复框（正脸/侧脸级联会重复报同一张脸）
    boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
    kept = []
    for b in boxes:
        x, y, ww, hh = b
        cx, cy = x + ww / 2, y + hh / 2
        if any(abs(cx - (k[0] + k[2] / 2)) < ww * 0.5 and abs(cy - (k[1] + k[3] / 2)) < hh * 0.5 for k in kept):
            continue
        kept.append(b)
    return kept


def analyse_photo(path: Path) -> dict:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        return {"ok": False, "error": f"读不了这张图：{path}（可能不是 jpg/png，或文件损坏）"}
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    faces = detect_faces(img, min_ratio=0.03)

    report = {
        "ok": True,
        "path": str(path),
        "width": w,
        "height": h,
        "long_side": max(w, h),
        "sharpness": round(laplacian, 1),
        "brightness": round(brightness, 1),
        "faces": len(faces),
        "largest_face_ratio": round((faces[0][2] * faces[0][3]) / float(w * h), 4) if faces else 0.0,
        "warnings": [],
        "verdict": "",
    }
    warn = report["warnings"]
    if not faces:
        warn.append("没检出人脸。换张正脸、光线均匀的照片；侧脸/遮挡/戴墨镜都会这样。")
    elif len(faces) > 1:
        warn.append(f"检出 {len(faces)} 张脸。FaceFusion 默认用最大的那张；建议先手动裁成只有你自己。")
    if max(w, h) < 1024:
        warn.append(f"分辨率偏低（长边 {max(w, h)}px）。目标视频是 1080p 以上时，脸部会糊。")
    if laplacian < 60:
        warn.append(f"照片偏模糊（清晰度 {laplacian:.0f}，建议 >100）。手机重拍一张比后期修更省事。")
    if brightness < 60:
        warn.append(f"照片偏暗（平均亮度 {brightness:.0f}）。换脸后容易和原片光线打架。")
    elif brightness > 200:
        warn.append(f"照片偏亮/过曝（平均亮度 {brightness:.0f}），细节可能已经没了。")
    if report["largest_face_ratio"] and report["largest_face_ratio"] < 0.03:
        warn.append("脸在画面里太小。换成半身/胸像照，脸占画面 1/3 以上。")

    report["verdict"] = "可以用" if len(warn) == 0 else ("勉强能用，建议重拍" if faces else "不能用")
    return report


def analyse_video(path: Path, samples: int = 12) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"ok": False, "error": f"打不开这个视频：{path}（换 mp4/H.264 再试）"}

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = total / fps if fps else 0.0

    counts, frame_ids = [], []
    if total > 0 and samples > 0:
        step = max(1, total // samples)
        for fid in range(0, total, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, fid)
            ok, frame = cap.read()
            if not ok:
                continue
            counts.append(len(detect_faces(frame, min_ratio=0.03)))
            frame_ids.append(fid)
    cap.release()

    report = {
        "ok": True,
        "path": str(path),
        "width": w,
        "height": h,
        "fps": round(fps, 2),
        "frames": total,
        "duration_sec": round(duration, 1),
        "sampled_frames": len(counts),
        "faces_per_sample": counts,
        "max_faces": max(counts) if counts else 0,
        "no_face_ratio": round(sum(1 for c in counts if c == 0) / len(counts), 3) if counts else 0.0,
        "warnings": [],
        "suggestion": "",
    }
    warn = report["warnings"]
    if not counts:
        warn.append("没抽到帧，可能是编解码不支持。先用 ffmpeg 转成 H.264 mp4。")
    elif report["max_faces"] == 0:
        warn.append("抽样帧里没检出人脸。可能脸太小/背对镜头/画风非写实，换脸不适合这条片子。")
    elif report["no_face_ratio"] > 0.4:
        warn.append(f"约 {report['no_face_ratio']*100:.0f}% 的抽样帧没有脸，说明镜头切换/空镜多，换脸会时有时无。")
    if report["max_faces"] > 1:
        warn.append(f"抽样最多出现 {report['max_faces']} 张脸。默认只换最大那张；要全换用 ALL_FACES=1。")
    if duration > 300:
        warn.append(f"片长 {duration/60:.1f} 分钟。建议按 60 秒切片跑，省内存、方便重跑。")
    if h and h < 720:
        warn.append(f"分辨率 {w}x{h} 偏低，换脸后脸会比原片更清晰，容易「糊脸配清脸」。")

    if report["max_faces"] > 1:
        report["suggestion"] = "多人：ALL_FACES=1 bash swap_face.sh 照片 视频 输出.mp4"
    else:
        report["suggestion"] = "单人：bash swap_face.sh 照片 视频 输出.mp4"
    return report


def print_report(photo: dict | None, video: dict | None) -> int:
    problems = 0
    if photo:
        print("── 照片 ──")
        if not photo["ok"]:
            print(f"  ✗ {photo['error']}")
            problems += 1
        else:
            print(f"  路径      {photo['path']}")
            print(f"  尺寸      {photo['width']}×{photo['height']}")
            print(f"  清晰度    {photo['sharpness']}（>100 较稳）")
            print(f"  亮度      {photo['brightness']}（60–180 较好）")
            print(f"  检出人脸  {photo['faces']} 张，最大占画面 {photo['largest_face_ratio']*100:.1f}%")
            print(f"  结论      {photo['verdict']}")
            for w in photo["warnings"]:
                print(f"  ! {w}")
            problems += len(photo["warnings"])
    if video:
        print("── 视频 ──")
        if not video["ok"]:
            print(f"  ✗ {video['error']}")
            problems += 1
        else:
            print(f"  路径      {video['path']}")
            print(f"  规格      {video['width']}×{video['height']} · {video['fps']} fps · {video['frames']} 帧")
            print(f"  时长      {video['duration_sec']} 秒（{video['duration_sec']/60:.2f} 分钟）")
            print(f"  抽样      {video['sampled_frames']} 帧，每帧人脸数 {video['faces_per_sample']}")
            print(f"  最多同框  {video['max_faces']} 张脸")
            for w in video["warnings"]:
                print(f"  ! {w}")
            print(f"  建议命令  {video['suggestion']}")
            problems += 1 if video["max_faces"] == 0 else 0
    print("── 结论 ──")
    print("  可以开跑。" if problems == 0 else "  先按上面的提示处理，再开跑。")
    return 0 if problems == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="换脸前的素材体检")
    ap.add_argument("--photo", help="人像照片路径")
    ap.add_argument("--video", help="参考视频路径")
    ap.add_argument("--samples", type=int, default=12, help="视频抽样帧数，默认 12")
    ap.add_argument("--report", help="把结果写成 JSON 到这个路径")
    args = ap.parse_args()

    if not args.photo and not args.video:
        ap.error("至少给 --photo 或 --video")

    photo = analyse_photo(Path(args.photo)) if args.photo else None
    video = analyse_video(Path(args.video), args.samples) if args.video else None
    code = print_report(photo, video)

    if args.report:
        Path(args.report).write_text(
            json.dumps({"photo": photo, "video": video}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  报告已写入 {args.report}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
