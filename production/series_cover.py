#!/usr/bin/env python3
"""全系列统一的封面入口：任何一部片子出片时都调用这里的 `make()`。

版式本身只有一份，在 `production/mystery-cover-template/template.py`（迷案解码人竖版
1080×1440）。这里负责从 `story.json` 读期数、两行标题和窗口截图的位置，并把 PNG/JPEG
一起写到交付目录，避免每个项目的 render.py 各写一套封面。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "production" / "mystery-cover-template"
if str(TEMPLATE_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATE_DIR))

import template  # noqa: E402  (需要在 sys.path 调整之后导入)

DEFAULT_SHOT = "S01"
DEFAULT_AT = 3.0


def grab(video: Path, seconds: float, work_dir: Path, tag: str = "cover") -> Image.Image:
    work_dir.mkdir(parents=True, exist_ok=True)
    path = work_dir / f"{tag}.jpg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(video),
                    "-frames:v", "1", "-q:v", "2", str(path)], check=True)
    with Image.open(path) as opened:
        return opened.convert("RGB")


def cover_config(story: dict) -> dict:
    """story.json 里的 cover 段：line1 / line2 / series_episode / window_shot / window_at。"""
    coverage = story.get("presentation", {}).get("cover", {})
    line1 = coverage.get("line1") or coverage.get("text") or story["title"]
    line2 = coverage.get("line2") or coverage.get("subtext") or ""
    return {
        "episode": int(coverage.get("series_episode", 1)),
        "line1": line1,
        "line2": line2,
        "shot": coverage.get("window_shot", DEFAULT_SHOT),
        "at": float(coverage.get("window_at", DEFAULT_AT)),
        "y_bias": float(coverage.get("window_y_bias", 0.5)),
    }


def render_with_frame(story: dict, shot: Image.Image, output: Path) -> Image.Image:
    """窗口已经有一帧时直接出封面（本地补出交付图、或截图不是来自 Sxx.mp4 时用）。"""
    cfg = cover_config(story)
    image = template.cover(template.DEFAULT_FONT, cfg["episode"], cfg["line1"], cfg["line2"],
                           shot=shot, shot_y_bias=cfg["y_bias"])
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=95, subsampling=0)
    image.save(output.with_suffix(".png"))
    return image


def make(story: dict, sources: Path, output: Path, work_dir: Path) -> Image.Image:
    """抓一帧本片画面放进窗口，按统一模板出 JPEG 和同名 PNG。"""
    cfg = cover_config(story)
    shot = grab(sources / f"{cfg['shot']}.mp4", cfg["at"], work_dir, "series-cover")
    return render_with_frame(story, shot, output)
