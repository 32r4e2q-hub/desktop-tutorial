#!/usr/bin/env python3
"""畸变核查采样器：把"该看的东西"摆到人面前，并搭好逐段结论脚手架。

用法::

    python3 production/review_distortion.py --film 交付/<片名>.mp4 \\
        --project production/<slug> --work work/<slug>/distortion \\
        --dense-shots S02,S04,S13,S15,S17,S19,S20,S21,S22,S25,S26,S29

AI 脸/手/伪文字畸变机器判不了（至少这条流水线里判不了），但机器可以保证
"每段都被看到"。它做三层采样（dahlia 核查用过的同一套）：

1. **全覆盖**：EDL 每段取 1/3、2/3 处各一帧（原生分辨率），按章节拼对照表；
2. **密扫**：``--dense-shots`` 列出的人物/手部镜头按 0.5 秒步长再扫一遍，
   抓采样点之间的帧间突变；
3. **脚手架**：``distortion-checklist.json``，逐段 verdict=pending，人填完结论
   落盘为 ``distortion-check.json``（ verdict 只许填 pass / pass_with_note / fail）。

它只负责"摆出来 + 搭架子"，不写结论——结论永远是人看完抽样帧之后写的。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import av
except ImportError as error:
    raise SystemExit(f"PyAV 未安装，跑不了畸变采样：{error}") from error

from PIL import Image, ImageDraw

FRAME_POINTS = (1 / 3, 2 / 3)
DENSE_STEP = 0.5
THUMB_W, THUMB_H = 480, 270
LABEL_H = 22


def film_fps(film: Path) -> float:
    container = av.open(str(film))
    try:
        return float(container.streams.video[0].average_rate or 30)
    finally:
        container.close()


def extract_wanted(film: Path, wanted: dict[int, list[tuple[str, int]]],
                   frames_dir: Path) -> None:
    """单遍解码，只存要的帧（全片常驻内存会 OOM，5400 帧 1080p 约 33GB）。"""
    container = av.open(str(film))
    try:
        for idx, frame in enumerate(container.decode(container.streams.video[0])):
            if idx in wanted:
                image = frame.to_image()
                for name, quality in wanted[idx]:
                    image.save(frames_dir / name, quality=quality)
    finally:
        container.close()


def sheet(images: list[tuple[str, Image.Image]], columns: int, path: Path,
          thumb_w: int = THUMB_W, thumb_h: int = THUMB_H) -> None:
    thumbs = []
    for name, image in images:
        thumb = image.copy()
        thumb.thumbnail((thumb_w, thumb_h))
        thumbs.append((name, thumb))
    rows = (len(thumbs) + columns - 1) // columns
    canvas = Image.new("RGB", (thumb_w * columns, (thumb_h + LABEL_H) * rows), "#111")
    draw = ImageDraw.Draw(canvas)
    for pos, (name, thumb) in enumerate(thumbs):
        x, y = (pos % columns) * thumb_w, (pos // columns) * (thumb_h + LABEL_H)
        canvas.paste(thumb, (x, y))
        draw.text((x + 6, y + thumb_h + 3), name, fill="#fff")
    canvas.save(path, quality=88)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--film", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True,
                        help="项目目录（读 delivery/edit-decision-list.json）")
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--dense-shots", default="",
                        help="逗号分隔的镜头 id，做 0.5 秒密扫（如人物/手部镜头）")
    parser.add_argument("--dense-step", type=float, default=DENSE_STEP)
    args = parser.parse_args(argv)

    if not args.film.is_file():
        raise SystemExit(f"找不到成片：{args.film}")
    args.work.mkdir(parents=True, exist_ok=True)
    frames_dir = args.work / "frames"
    frames_dir.mkdir(exist_ok=True)
    edl_path = args.project / "delivery" / "edit-decision-list.json"
    if not edl_path.is_file():
        raise SystemExit(f"找不到 EDL：{edl_path}")
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    dense = {s.strip() for s in args.dense_shots.split(",") if s.strip()}

    fps = film_fps(args.film)
    total = edl[-1]["end_frame"] if edl else 0
    # 先算好要哪些帧，再单遍解码按需存
    wanted: dict[int, list[tuple[str, int]]] = {}
    plan = []
    for i, row in enumerate(edl):
        start, end = row["start_frame"], row["end_frame"]
        t0, t1 = start / fps, end / fps
        picked = []
        for k, frac in zip("ab", FRAME_POINTS):
            idx = min(total - 1, start + int((end - start) * frac))
            name = f"row{i:02d}_{row['id']}{k}_t{idx / fps:.2f}s.jpg"
            wanted.setdefault(idx, []).append((name, 90))
            picked.append(name)
        dense_names = []
        if row["id"] in dense:
            tick = (int(t0 / args.dense_step) + 1) * args.dense_step
            while tick < t1 - 0.2:
                idx = min(total - 1, int(tick * fps))
                name = f"dense_row{i:02d}_{row['id']}_t{tick:.1f}s.jpg"
                wanted.setdefault(idx, []).append((name, 88))
                dense_names.append(name)
                tick += args.dense_step
        plan.append({"row": i, "id": row["id"], "kind": row["kind"],
                     "start": round(t0, 2), "end": round(t1, 2),
                     "frames": picked, "dense_frames": dense_names,
                     "verdict": "pending", "notes": ""})
    extract_wanted(args.film, wanted, frames_dir)

    checklist, by_chapter = plan, {}
    for row in checklist:
        edl_row = edl[row["row"]]
        by_chapter.setdefault(edl_row.get("narration_id", "?"), []).extend(row["frames"])

    sheets = []
    for chapter in sorted(by_chapter):
        images = [(n, Image.open(frames_dir / n)) for n in by_chapter[chapter]]
        out = args.work / f"sheet-{chapter}.jpg"
        sheet(images, 3, out)
        sheets.append(out.name)
    dense_all = [n for row in checklist for n in row["dense_frames"]]
    for s in range((len(dense_all) + 19) // 20):
        batch = dense_all[s * 20:(s + 1) * 20]
        images = [(n, Image.open(frames_dir / n)) for n in batch]
        out = args.work / f"dense-sheet-{s + 1:02d}.jpg"
        sheet(images, 5, out, thumb_w=384, thumb_h=216)
        sheets.append(out.name)

    out = args.work / "distortion-checklist.json"
    out.write_text(json.dumps(
        {"film": args.film.name,
         "method": ("EDL 每段 1/3、2/3 处各一帧全覆盖 + "
                    f"{sorted(dense) if dense else '无密扫镜头'}按 {args.dense_step}s 密扫；"
                    "verdict 由人看完对照表后填写：pass / pass_with_note / fail"),
         "sheets": sheets, "segments": checklist},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"畸变采样：{out}")
    print(f"  {len(checklist)} 段 / {sum(len(r['frames']) for r in checklist)} 覆盖帧 / "
          f"{len(dense_all)} 密扫帧 / {len(sheets)} 张对照表")
    print(f"  密扫镜头：{sorted(dense) if dense else '无（只做了全覆盖）'}")
    print("  下一步：看对照表，逐段填 verdict，落盘为 distortion-check.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
