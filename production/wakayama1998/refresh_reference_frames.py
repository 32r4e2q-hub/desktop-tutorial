#!/usr/bin/env python3
"""用成片里抽出的真实帧，替换 7 张定稿板里的程序绘图（离线工具）。

`make_reference_boards.py` 画的是「美术定稿板」（色板 / 构图 / 剪影），用来在生成通道不可用时
先把角色与场景定下来。等成片与 `qa/fullres/` 抽帧到齐后，这一步把同名文件换成**片子里真实的一帧**，
从此 `reference/` 里就是这部片子的定稿参考图：左边是画面，右边压一条淡金色说明栏。

    python3 production/wakayama1998/refresh_reference_frames.py            # 用 qa/fullres/
    python3 production/wakayama1998/refresh_reference_frames.py --dry-run  # 只报缺哪几张
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
QA = HERE / "qa"
FULLRES = QA / "fullres"

# 定稿板 -> 取哪一镜的那一帧（秒）
PROBES = [
    ("reference/01-hayashi-masumi.png", "S19", 3.0, "林真须美（风格化形象）· 出自 S19"),
    ("reference/02-hayashi-kenji.png", "S19", 5.2, "林健治（风格化形象）· 出自 S19"),
    ("reference/03-sonobe-street-festival.png", "S01", 2.4, "园部街区与夏祭 · 出自 S01"),
    ("reference/04-garage-big-pot.png", "S02", 2.0, "车库大锅 · 出自 S02"),
    ("reference/05-hospital-night.png", "S10", 2.2, "医院急诊走廊 · 出自 S10"),
    ("reference/06-lab-and-report.png", "S12", 3.0, "实验室与曲线 · 出自 S12"),
    ("reference/07-press-and-court.png", "S23", 3.2, "记者群与水管 · 出自 S23"),
]


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # pragma: no cover
        return "ffmpeg"


def font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def grab(shot: str, seconds: float) -> Image.Image | None:
    """Prefer the QC full-resolution stills; fall back to a frame of the delivered film."""
    still = FULLRES / f"{shot}.jpg"
    if still.is_file():
        with Image.open(still) as image:
            return image.convert("RGB")
    import subprocess
    import tempfile
    film_candidates = sorted((HERE.parents[1] / "交付").glob("*三分钟_带声音.mp4"))
    del film_candidates
    work = HERE.parents[1] / "work" / "wakayama1998" / "sources" / f"{shot}.mp4"
    if not work.is_file():
        return None
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "frame.jpg"
        subprocess.run([ffmpeg_exe(), "-y", "-v", "error", "-ss", f"{seconds:.2f}", "-i", str(work),
                        "-frames:v", "1", "-q:v", "2", str(target)], check=True)
        with Image.open(target) as image:
            return image.convert("RGB")


def build(image: Image.Image, caption: str, source: str) -> Image.Image:
    width, height = 1920, 1080
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((max(width, round(image.width * ratio)),
                            max(height, round(image.height * ratio))), Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    canvas = resized.crop((left, top, left + width, top + height)).convert("RGBA")

    shade = np.zeros((height, width, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:height, 0:width]
    distance = np.sqrt(((xx - width * 0.5) / (width * 0.70)) ** 2 + ((yy - height * 0.5) / (height * 0.85)) ** 2)
    shade[:, :, 3] = np.clip((distance - 0.75) * 200, 0, 120).astype(np.uint8)
    canvas = Image.alpha_composite(canvas, Image.fromarray(shade, "RGBA"))

    bar = Image.new("RGBA", (width, 132), (8, 8, 9, 168))
    canvas = Image.alpha_composite(canvas, bar)
    draw = ImageDraw.Draw(canvas)
    gold = (244, 201, 95)
    draw.rectangle((0, 0, 12, 132), fill=gold + (220,))
    draw.text((46, 30), "和歌山毒咖喱事件", font=font(40), fill=gold)
    draw.text((46, 84), caption, font=font(26), fill=(232, 230, 224))
    draw.text((width - 620, 54), "AI动画情景复原 · 非真实影像", font=font(24), fill=(190, 186, 176))
    draw.text((width - 620, 92), source, font=font(20), fill=(150, 146, 138))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rectangle((0, 0, 12, 132), fill=gold + (120,))
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(18)))
    return canvas.convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    missing = []
    for rel, shot, seconds, caption in PROBES:
        target = HERE / rel
        image = grab(shot, seconds)
        if image is None:
            missing.append(f"{rel} ({shot})")
            continue
        print(("would write " if args.dry_run else "wrote ") + str(target) + f"  <- {shot} @ {seconds}s")
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            build(image, caption, f"帧：{shot} · {seconds:.1f}s").convert(
                "P").save(target, format="PNG", optimize=True)
    if missing:
        print("still missing frames for: " + ", ".join(missing))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
