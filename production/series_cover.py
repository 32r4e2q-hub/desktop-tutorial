#!/usr/bin/env python3
"""全系列统一的封面入口：只说期数，就自动选帧、自动拟标题、出竖版封面。

版式只有一份，在 `production/mystery-cover-template/template.py`（迷案解码人 1080×1440）。
这个模块负责三件事，供各项目的 `render.py` 和命令行共用：

1. `cover_config(story)` —— 从 `story.json` 取期数、两行标题、窗口目标帧；
2. `pick_frame(...)` —— 在成片里自动挑一帧「有信息量、没有被字幕压住」的画面；
3. `make(...)` / `render_with_frame(...)` —— 出 JPEG + 同名 PNG，并写标题记录。

命令行（用户只说「第 N 期」时 Agent 就跑这一条）：

    python3 -m production.series_cover \
        --episode 2 \
        --story production/holmes1893/story.json \
        --film 交付/H·H·霍姆斯_传说里的杀人城堡_三分钟_带声音.mp4 \
        --output 交付/H·H·霍姆斯_传说里的杀人城堡_封面.png

省略 `--output` 时会写到 `<story 所在项目>/delivery/系列封面_第N期.png`。
`--line1/--line2` 可覆盖自动拟好的标题；`--shot/--at` 可指定窗口画面（跳过自动选帧）。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "production" / "mystery-cover-template"
if str(TEMPLATE_DIR) not in sys.path:
    sys.path.insert(0, str(TEMPLATE_DIR))

import template  # noqa: E402  (需要在 sys.path 调整之后导入)

DEFAULT_SHOT = "S01"
DEFAULT_AT = 3.0
MAX_LINE = 18

# 自动选帧时的取样节奏：每 0.5 s 一帧，跳过每镜首尾各 0.8 s（转场淡入淡出）。
SAMPLE_STEP = 0.5
EDGE_GUARD = 0.8
# 字幕检测：窗口会裁掉上下，但字幕通常落在画面下方 12%～30%；用更宽的 32% 兜住两行字幕。
SUBTITLE_BAND = 0.32
SUBTITLE_LUMA = 215
SUBTITLE_INK_LIMIT = 350


# ------------------------------------------------------------------ 配置 / 标题
def cover_config(story: dict) -> dict:
    """story.json 里的 cover 段：期数、两行标题、窗口目标帧。"""
    coverage = story.get("presentation", {}).get("cover", {})
    line1, line2 = auto_title(story)
    return {
        "episode": int(coverage.get("series_episode", 1)),
        "line1": coverage.get("line1") or line1,
        "line2": coverage.get("line2") or line2,
        "shot": coverage.get("window_shot", DEFAULT_SHOT),
        "at": float(coverage.get("window_at", DEFAULT_AT)),
        "y_bias": float(coverage.get("window_y_bias", 0.5)),
    }


def _trim(text: str, limit: int = MAX_LINE) -> str:
    """按标点断句后截到 limit 字，优先在逗号/顿号处断开。"""
    text = re.sub(r"\s+", "", text or "")
    text = text.replace("：", "·").replace(":", "·")
    if len(text) <= limit:
        return text.rstrip("，。、·")
    for mark in ("；", "，", "、", "。"):
        head = text.split(mark)[0]
        if 4 <= len(head) <= limit:
            return head
    return text[:limit].rstrip("，。、·")


def auto_title(story: dict) -> tuple[str, str]:
    """没有人工标题时，从 story.json 里提炼两行封面字（各 ≤18 字）。

    规则：优先用标题里「：」前后的对照（案件名 / 悬念句），否则用第一镜的钩子。
    人工写在 presentation.cover.line1/line2 的标题永远优先——自动结果只是兜底。
    """
    coverage = story.get("presentation", {}).get("cover", {})
    text = coverage.get("text") or ""
    subtext = coverage.get("subtext") or ""
    if text and subtext:
        return _trim(text), _trim(subtext)

    title = story.get("title", "")
    head, _, tail = title.partition("：")
    if not tail:
        head, _, tail = title.partition(":")
    if tail:
        return _trim(head), _trim(tail)

    hook = ""
    shots = story.get("shots", [])
    if shots:
        hook = shots[0].get("narration", "")
    return _trim(head or title), _trim(hook)


# ------------------------------------------------------------------ 选帧
def shot_windows(story: dict) -> list[tuple[str, float, float]]:
    shots = story.get("shots", [])
    return [(shot["id"], float(shot["start"]), float(shot["duration"])) for shot in shots]


def _sample_times(story: dict, max_per_shot: int = 6,
                  only: list[str] | None = None) -> list[tuple[str, float]]:
    """每镜在安全区内均匀取几个时刻；only 给定时只看这些镜头。"""
    picks: list[tuple[str, float]] = []
    for shot_id, start, duration in shot_windows(story):
        if only and shot_id not in only:
            continue
        low, high = EDGE_GUARD, max(EDGE_GUARD, duration - EDGE_GUARD)
        if high <= low:
            low, high = duration * 0.3, duration * 0.7
        count = max(2, min(max_per_shot, int((high - low) / SAMPLE_STEP) + 1))
        for index in range(count):
            point = low + (high - low) * index / max(1, count - 1)
            picks.append((shot_id, start + point))
    return picks


def _subtitle_ink(image: Image.Image) -> int:
    """画面下方字幕带里接近纯白的像素数：成片字幕是白/金色描边，很容易测出来。"""
    gray = image.convert("L")
    height = gray.height
    band = np.asarray(gray.crop((0, int(height * (1 - SUBTITLE_BAND)), gray.width, height)))
    return int((band > SUBTITLE_LUMA).sum())


def score_frame(image: Image.Image) -> dict:
    """窗口裁切后的观感分：先判「有没有主角 / 够不够有戏」，再比细节。

    三项硬指标来自封面需求本身：画面要有主体（人物或道具中心）、要有明暗对比、
    底部不能被成片字幕压住。都过关之后才比细节量，避免选出「挂着的衣服」「空房间」。
    """
    left, top, right, bottom = template.SHOT_BOX
    width, height = right - left, bottom - top
    crop = template.fill_crop(image, width, height)
    small = crop.resize((240, int(240 * height / width)), Image.Resampling.BILINEAR)
    array = np.asarray(small, dtype=np.float32)

    luma = array @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    contrast = float(luma.std())
    brightness = float(luma.mean())
    colorfulness = float(np.abs(array[..., 0] - array[..., 2]).mean())
    edges = float(np.abs(np.diff(luma, axis=0)).mean() + np.abs(np.diff(luma, axis=1)).mean())
    ink = _subtitle_ink(image)

    # 人物：肤色像素占比。封面最需要的是「有人」，纯纹理墙纸/空走廊要排后面。
    rgb = array
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    skin = ((red > 95) & (green > 40) & (blue > 20)
            & (red > green + 12) & (red > blue + 25)
            & (np.abs(red - green) > 12))
    skin_share = float(skin.mean())

    # 主体：中间 60% 区域里，明显偏离背景亮度的像素占比（人物/道具都会推高它）。
    mid = luma[int(luma.shape[0] * 0.15):int(luma.shape[0] * 0.85),
               int(luma.shape[1] * 0.20):int(luma.shape[1] * 0.80)]
    background = float(np.median(mid))
    subject = float((np.abs(mid - background) > 32).mean()) if mid.size else 0.0

    score = (120 * min(skin_share, 0.12) / 0.12
             + 30 * subject + 0.35 * contrast + 0.6 * edges + 0.10 * colorfulness)
    if skin_share < 0.004:      # 画面里没有人
        score -= 55
    if subject < 0.10:          # 几乎是平涂的空景
        score -= 45
    if contrast < 22:           # 没有明暗层次
        score -= 20
    if brightness < 28 or brightness > 235:
        score -= 25
    if ink > SUBTITLE_INK_LIMIT:
        score -= 120
    return {"score": round(score, 2), "brightness": round(brightness, 1),
            "contrast": round(contrast, 1), "subject": round(subject, 3),
            "skin": round(skin_share, 4),
            "colorfulness": round(colorfulness, 1), "edges": round(edges, 2),
            "subtitle_ink": ink}


def pick_frame(film: Path, story: dict, work_dir: Path,
               only: list[str] | None = None) -> tuple[Image.Image, dict]:
    """在成片里取样、打分，挑出最有信息量且没有字幕压字的一帧。

    `only` 是剧情语义上值得上封面的候选镜头（写在 story.json 的
    `presentation.cover.candidates`）：语义由 Agent 判断，清晰度/字幕/亮度由这里判断。
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    probe_file = work_dir / "cover-probe.jpg"
    picks = _sample_times(story, only=only)
    if not picks:  # 候选镜 ID 写错时退回全片，不让流程断掉
        picks = _sample_times(story)
    best: tuple[float, Image.Image, dict] | None = None
    for shot_id, at in picks:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(film),
                        "-frames:v", "1", "-q:v", "3", str(probe_file)], check=True)
        with Image.open(probe_file) as opened:
            frame = opened.convert("RGB")
        stats = score_frame(frame)
    
        stats.update({"shot": shot_id, "at": round(at, 2)})
        if best is None or stats["score"] > best[0]:
            best = (stats["score"], frame.copy(), stats)
    if best is None:
        raise RuntimeError("无法在成片里取到任何一帧；检查 --film 路径与 ffmpeg")
    return best[1], best[2]



# ------------------------------------------------------------------ 候选帧样张
def contact_sheet(film: Path, story: dict, output: Path, work_dir: Path,
                  candidates: list[str] | None = None, per_shot: int = 4,
                  columns: int = 4) -> dict:
    """给候选镜各取几帧，拼成带编号的样张，供人/Agent 看图选帧。

    「哪一帧有代表性」是剧情判断，像素分数只能排掉黑帧和压字幕的帧；所以默认流程是
    看图选，而不是让脚本自己决定。返回的 manifest 记着每格对应的镜头与时间点。
    """
    picks = _sample_times(story, max_per_shot=per_shot, only=candidates)
    if not picks:
        picks = _sample_times(story, max_per_shot=per_shot)
    work_dir.mkdir(parents=True, exist_ok=True)
    probe = work_dir / "contact-probe.jpg"
    tiles, manifest = [], []
    for index, (shot_id, at) in enumerate(picks, start=1):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at:.3f}", "-i", str(film),
                        "-frames:v", "1", "-q:v", "3", str(probe)], check=True)
        with Image.open(probe) as opened:
            frame = opened.convert("RGB")
        tile = template.fill_crop(frame, 480, 270).copy()
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, 480, 34), fill=(0, 0, 0))
        draw.text((10, 6), f"#{index}  {shot_id}  {at:.1f}s", font=_label_font(),
                  fill=(255, 236, 190))
        draw.rectangle((468, 258, 480, 270), fill=(255, 255, 255))
        tiles.append(tile)
        manifest.append({"index": index, "shot": shot_id, "at": round(at, 2)})

    rows = (len(tiles) + columns - 1) // columns
    sheet = Image.new("RGB", (480 * columns, 270 * rows), (8, 10, 12))
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % columns) * 480, (index // columns) * 270))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=90)
    manifest_path = output.with_suffix(".json")
    manifest_path.write_text(json.dumps({"film": str(film), "tiles": manifest},
                                        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"sheet": str(output), "manifest": str(manifest_path), "tiles": manifest}


def _label_font():
    try:
        return ImageFont.truetype(str(template.DEFAULT_FONT), 22)
    except OSError:
        return ImageFont.load_default()

# ------------------------------------------------------------------ 出图
def render_with_frame(story: dict, shot: Image.Image, output: Path,
                      line1: str | None = None, line2: str | None = None,
                      episode: int | None = None) -> Image.Image:
    """窗口已经有一帧时直接出封面。"""
    cfg = cover_config(story)
    episode = cfg["episode"] if episode is None else episode
    image = template.cover(template.DEFAULT_FONT, episode,
                           line1 or cfg["line1"], line2 or cfg["line2"],
                           shot=shot, shot_y_bias=cfg["y_bias"])
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=95, subsampling=0)
    image.save(output.with_suffix(".png"))
    _write_meta(output, story, cfg, episode, line1 or cfg["line1"], line2 or cfg["line2"])
    return image


def _write_meta(output: Path, story: dict, cfg: dict, episode: int,
                line1: str, line2: str, picked: dict | None = None) -> Path:
    meta = {
        "series": template.LABEL,
        "episode": episode,
        "episode_label": template.episode_text(episode),
        "cover_title_lines": [line1, line2],
        "release_title": story.get("title", ""),
        "cover_file": output.name,
        "cover_template": "production/mystery-cover-template/template.py",
        "size": [template.W, template.H],
    }
    if picked:
        meta["window_frame"] = {"shot": picked.get("shot"), "at": picked.get("at"),
                                "picked_by": picked.get("picked_by", "auto"),
                                **{k: picked[k] for k in
                                                        ("score", "brightness", "contrast",
                                                         "subtitle_ink") if k in picked}}
    else:
        meta["window_frame"] = {"shot": cfg["shot"], "at": cfg["at"], "picked_by": "story.json"}
    path = output.with_suffix(".json")
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def make(story: dict, sources: Path, output: Path, work_dir: Path) -> Image.Image:
    """抓一帧本片画面放进窗口（用 story.json 指定的镜头），按统一模板出 JPEG 和同名 PNG。"""
    cfg = cover_config(story)
    shot = grab(sources / f"{cfg['shot']}.mp4", cfg["at"], work_dir, "series-cover")
    return render_with_frame(story, shot, output)


def grab(video: Path, seconds: float, work_dir: Path, tag: str = "cover") -> Image.Image:
    work_dir.mkdir(parents=True, exist_ok=True)
    path = work_dir / f"{tag}.jpg"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{seconds:.3f}", "-i", str(video),
                    "-frames:v", "1", "-q:v", "2", str(path)], check=True)
    with Image.open(path) as opened:
        return opened.convert("RGB")


def pinned_frame(story: dict, film: Path, work_dir: Path):
    """story.json 里已经用样张看脸选定的窗口帧：有就用它，别再自动重选。

    约定（见 mystery-cover-template/README.md）：先出候选帧样张、人眼挑一格，把
    `window_shot` / `window_at`（镜内秒数，渲染时按镜头起始换算成成片绝对秒数）写回
    `presentation.cover`。自动评分挑不出「代表性」——空走廊、空衣架常常分最高，
    所以一旦定过帧，就必须尊重它。
    """
    coverage = (story.get("presentation", {}) or {}).get("cover", {}) or {}
    if not coverage.get("window_shot") or coverage.get("window_at") is None:
        return None
    cfg = cover_config(story)
    starts = {shot.get("id"): float(shot.get("start", 0)) for shot in story.get("shots", [])}
    if cfg["shot"] not in starts:
        return None
    at = starts[cfg["shot"]] + cfg["at"]
    frame = grab(film, at, work_dir, "cover-pinned")
    return frame, {"shot": cfg["shot"], "at": round(at, 3), "picked_by": "story.json（样张看图选定）"}


def make_auto(story: dict, film: Path, output: Path, work_dir: Path,
              episode: int | None = None, line1: str | None = None,
              line2: str | None = None, at: float | None = None,
              shot_id: str | None = None) -> tuple[Image.Image, dict]:
    """一句话出封面：自动选帧（或按 --shot/--at 指定）+ 自动拟标题。"""
    candidates = list(story.get("presentation", {}).get("cover", {}).get("candidates") or []) or None
    pinned = None if (shot_id and at is not None) else pinned_frame(story, film, work_dir)
    if shot_id and at is not None:
        frame = grab(film, at, work_dir, "cover-fixed")
        picked = {"shot": shot_id, "at": at, "picked_by": "cli"}
    elif pinned:
        frame, picked = pinned
    else:
        frame, picked = pick_frame(film, story, work_dir, only=candidates)
    image = render_with_frame(story, frame, output, line1=line1, line2=line2, episode=episode)
    cfg = cover_config(story)
    episode_value = cfg["episode"] if episode is None else episode
    _write_meta(output, story, cfg, episode_value, line1 or cfg["line1"], line2 or cfg["line2"], picked)
    return image, picked


# ------------------------------------------------------------------ 命令行
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="迷案解码人系列封面：给期数和 story.json，自动选帧 + 自动拟标题出竖版封面。")
    parser.add_argument("--episode", type=int, required=True, help="期数，1–9999")
    parser.add_argument("--story", type=Path, required=True, help="该期案件的 story.json")
    parser.add_argument("--film", type=Path, help="成片 mp4；不给就用 --shot/--at 或 story.json 的窗口帧")
    parser.add_argument("--output", type=Path, help="输出 PNG；默认 项目/delivery/系列封面_第N期.png")
    parser.add_argument("--line1", help="覆盖第一行标题（默认自动拟）")
    parser.add_argument("--line2", help="覆盖第二行标题（默认自动拟）")
    parser.add_argument("--shot", help="指定窗口镜头 ID，例如 S11（跳过自动选帧）")
    parser.add_argument("--at", type=float, help="指定窗口时间点（秒，绝对时间）")
    parser.add_argument("--contacts", type=Path,
                        help="只出候选帧样张到这里（带编号），看完再带 --shot/--at 正式出封面")
    parser.add_argument("--per-shot", type=int, default=4, help="样张里每个候选镜取几帧")
    parser.add_argument("--work", type=Path, help="临时目录；默认系统临时目录")
    args = parser.parse_args(argv)

    story = json.loads(args.story.read_text(encoding="utf-8"))
    if not 1 <= args.episode <= 9999:
        print("期数必须是 1 到 9999 的整数", file=sys.stderr)
        return 2
    output = args.output or (args.story.parent / "delivery" / f"系列封面_{template.episode_text(args.episode)}.png")
    work = args.work or Path(tempfile.mkdtemp(prefix="series-cover-"))
    try:
        if args.contacts:
            if not args.film or not args.film.is_file():
                raise ValueError("出样张需要 --film")
            candidates = list((story.get("presentation", {}).get("cover", {}) or {})
                              .get("candidates") or []) or None
            info = contact_sheet(args.film, story, args.contacts, work, candidates,
                                 per_shot=args.per_shot)
            cfg = cover_config(story)
            print(f"候选帧样张：{info['sheet']}（{len(info['tiles'])} 格）")
            print(f"编号目录：{info['manifest']}")
            print(f"拟定标题：{cfg['line1']} / {cfg['line2']}（第 {args.episode} 期）")
            return 0
        if args.film:
            if not args.film.is_file():
                raise ValueError(f"成片不存在：{args.film}")
            image, picked = make_auto(story, args.film, output, work, episode=args.episode,
                                      line1=args.line1, line2=args.line2,
                                      at=args.at, shot_id=args.shot)
        else:
            if not (args.shot and args.at is not None):
                raise ValueError("没有 --film 时请同时给 --shot 和 --at")
            raise ValueError("没有 --film 时无法取帧；请给出成片路径，或改用 render_with_frame")
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"无法生成封面：{error}", file=sys.stderr)
        return 1

    meta = output.with_suffix(".json")
    print(f"封面：{output}")
    print(f"标题记录：{meta}")
    if picked:
        how = picked.get("picked_by", "auto")
        detail = f"，得分 {picked['score']}" if "score" in picked else ""
        print(f"窗口画面：{picked['shot']} @ {picked['at']}s（{how}{detail}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
