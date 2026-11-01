#!/usr/bin/env python3
"""本地干跑：用参考图合成 30 段「假片段」，把渲染管线整条跑一遍。

只用来在真实素材回来之前找出滤镜图、ASS 字幕、混音、封面上的错误——
它**不能**代替真实素材的视听审校，也不产生任何交付物（全部写在被忽略的 work/ 里）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import importlib.util

spec = importlib.util.spec_from_file_location("holmes_render", ROOT / "production/holmes1893/render.py")
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)
spec2 = importlib.util.spec_from_file_location("holmes_audio", ROOT / "production/holmes1893/build_audio.py")
audio = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(audio)

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
WORK = ROOT / "work" / "holmes1893" / "dryrun"
SOURCES = WORK / "sources"
PICTURE_DIR = WORK / "edit"
REF = ROOT / "production" / "holmes1893" / "reference"


def make_fake_clip(shot: dict, image: Path, target: Path) -> None:
    """A moving (zooming) 1280x720 clip so frame-to-frame differences are non-zero."""
    frames = int(shot["duration"] * 24)
    zoom = "zoompan=z='min(zoom+0.0016,1.22)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'" \
           f":d={frames}:s=1280x720:fps=24"
    subprocess.run([
        FFMPEG, "-y", "-v", "error", "-loop", "1", "-i", str(image),
        "-vf", f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,{zoom}",
        "-t", f"{shot['duration']:.3f}", "-r", "24", "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", str(target),
    ], check=True)


def main() -> int:
    story = json.loads((ROOT / "production" / "holmes1893" / "story.json").read_text(encoding="utf-8"))
    SOURCES.mkdir(parents=True, exist_ok=True)
    PICTURE_DIR.mkdir(parents=True, exist_ok=True)
    refs = sorted(REF.glob("*.png"))
    for index, shot in enumerate(story["shots"]):
        target = SOURCES / f"{shot['id']}.mp4"
        if not target.is_file():
            make_fake_clip(shot, refs[index % len(refs)], target)
    print("fake clips ready", flush=True)

    picture, reports = render.build_picture(story, SOURCES, PICTURE_DIR)
    summary = render.media_summary(picture)
    print("picture:", summary, flush=True)

    # 字幕与混音：用「整镜就是一句话」的时间窗做干跑（真实出片时窗口来自语音活动）。
    cues = [{"shot_id": shot["id"], "narration_id": shot["narration_id"],
             "start": round(shot["start"] + 0.15, 3),
             "end": round(shot["start"] + shot["duration"] - 0.12, 3),
             "text": shot["narration"]} for shot in story["shots"]]
    ass_path = PICTURE_DIR / "dryrun.ass"
    srt_path = PICTURE_DIR / "dryrun.srt"
    render.write_subtitles(ass_path, cues, story, srt_path)
    print("captions:", ass_path.stat().st_size, "bytes", flush=True)

    music, effects = audio.synthesize_beds(PICTURE_DIR, story)
    print("beds:", music.shape, effects.shape, flush=True)
    voice = np.zeros(len(music), dtype=np.float32)
    for cue in cues:
        a, b = int(cue["start"] * audio.RATE), int(cue["end"] * audio.RATE)
        voice[a:b] = 0.02
    mix = voice[:, None] + music * 0.5 + effects * 0.5
    audio.write_wave(PICTURE_DIR / "dryrun-mix.wav", mix.astype(np.float32), channels=2)

    font_dir = ROOT / ".cache" / "fonts"
    out = PICTURE_DIR / "dryrun-film.mp4"
    subprocess.run([
        FFMPEG, "-y", "-v", "error", "-i", str(picture), "-i", str(PICTURE_DIR / "dryrun-mix.wav"),
        "-vf", f"ass={ass_path.as_posix()}:fontsdir={font_dir.as_posix()}",
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-t", "180", str(out),
    ], check=True)
    print("film:", render.media_summary(out), flush=True)

    render.compose_cover(render.grab_frame(SOURCES / "S02.mp4", 2.0, PICTURE_DIR, "dry-castle"),
                         render.grab_frame(SOURCES / "S01.mp4", 1.5, PICTURE_DIR, "dry-city"),
                         PICTURE_DIR / "dryrun-cover.png", story)
    print("cover ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
