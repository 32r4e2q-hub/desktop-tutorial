#!/usr/bin/env python3
"""Fallback previs renderer: 30 shots animated from the approved reference stills.

Used only if the Agnes clips cannot be produced. Motion = 2.5D camera move + parallax + procedural
particles (sakura / embers / snow / fireflies / mist) + light breathing, never a plain push-in on a
frozen frame; subtitles are drawn with Pillow so no fontconfig is needed.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/home/user/desktop-tutorial")
PROJECT = ROOT / "production" / "kinkakuji1950"
WORK = ROOT / "work" / "kinkakuji1950"
FONT = ROOT / "production" / "mystery-cover-template" / "NotoSerifCJKsc-Common.otf"
W, H, FPS = 1920, 1080, 24
RNG = np.random.default_rng(19500702)

SHOT_IMAGE = {
    "S01": "01-kinkaku-spring", "S02": "08-fire-night", "S03": "01-kinkaku-spring",
    "S04": "01-kinkaku-spring", "S05": "02-kinkaku-winter", "S06": "01-kinkaku-spring",
    "S07": "06-maizuru-temple", "S08": "04-young-ryozen", "S09": "04-young-ryozen",
    "S10": "03-ryozen-novice", "S11": "03-ryozen-novice", "S12": "03-ryozen-novice",
    "S13": "03-ryozen-novice", "S14": "03-ryozen-novice", "S15": "03-ryozen-novice",
    "S16": "07-interior-buddha", "S17": "08-fire-night", "S18": "08-fire-night",
    "S19": "08-fire-night", "S20": "08-fire-night", "S21": "08-fire-night",
    "S22": "08-fire-night", "S23": "03-ryozen-novice", "S24": "07-interior-buddha",
    "S25": "05-mother", "S26": "05-mother", "S27": "03-ryozen-novice",
    "S28": "05-mother", "S29": "01-kinkaku-spring", "S30": "01-kinkaku-spring",
}

PARTICLES = {
    "S01": "sakura", "S02": "ember", "S03": "dust", "S04": "sakura", "S05": "snow",
    "S06": "firefly", "S07": "mist", "S08": "dust", "S09": "dust", "S10": "sakura",
    "S11": "mist", "S12": "dust", "S13": "dust", "S14": "dust", "S15": "mist",
    "S16": "dust", "S17": "ember", "S18": "ember", "S19": "ember", "S20": "ember",
    "S21": "ash", "S22": "mist", "S23": "dust", "S24": "dust", "S25": "mist",
    "S26": "mist", "S27": "dust", "S28": "snow", "S29": "sakura", "S30": "sakura",
}

GRADE = {
    "sepia": (1.06, 1.00, 0.86),
    "cold": (0.88, 0.97, 1.10),
    "fire": (1.14, 0.98, 0.86),
    "normal": (1.0, 1.0, 1.0),
}
SHOT_GRADE = {sid: "normal" for sid in SHOT_IMAGE}
SHOT_GRADE.update({"S03": "sepia", "S08": "cold", "S12": "cold", "S23": "cold",
                   "S27": "cold", "S28": "cold", "S17": "fire", "S18": "fire",
                   "S19": "fire", "S20": "fire", "S21": "fire"})


def load_story():
    return json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))


def prepare_base(name: str) -> Image.Image:
    path = PROJECT / "reference" / f"{name}.png"
    with Image.open(path) as image:
        image = image.convert("RGB")
        # The first three reference sheets were delivered with thin dark bands: crop them off.
        image = image.crop((0, int(image.height * 0.035), image.width, int(image.height * 0.965)))
    scale = 1.22
    return image.resize((int(W * scale), int((W * scale) * image.height / image.width)),
                        Image.Resampling.LANCZOS)


def particle_layer(kind: str, count: int, frame_index: int, total: int) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    u = frame_index / max(1, total)
    if kind == "sakura":
        for _ in range(26):
            x = (RNG.integers(0, W) + u * 260 * (0.4 + RNG.random())) % W
            y = (RNG.integers(0, H) + u * 620 * (0.5 + RNG.random())) % H
            size = int(RNG.integers(4, 10))
            draw.ellipse([x, y, x + size * 2, y + size], fill=(255, 205, 220, 190))
    elif kind in {"ember", "ash"}:
        for _ in range(40):
            x = (RNG.integers(0, W) + math.sin(u * 6 + RNG.random() * 6) * 60) % W
            y = (H - (RNG.integers(0, H) + u * 900) % H)
            size = int(RNG.integers(2, 5 if kind == "ember" else 4))
            colour = (255, int(150 + RNG.integers(0, 80)), 60, 220) if kind == "ember" \
                else (200, 196, 190, 150)
            draw.ellipse([x, y, x + size, y + size], fill=colour)
    elif kind == "snow":
        for _ in range(48):
            x = (RNG.integers(0, W) + u * 120) % W
            y = (RNG.integers(0, H) + u * 420) % H
            size = int(RNG.integers(3, 7))
            draw.ellipse([x, y, x + size, y + size], fill=(255, 255, 255, 210))
    elif kind == "firefly":
        for _ in range(18):
            x = RNG.integers(0, W) % W
            y = (RNG.integers(200, 760) + math.sin(u * 9 + RNG.random() * 5) * 40) % H
            glow = 6 + int(4 * (0.5 + 0.5 * math.sin(u * 12 + RNG.random() * 5)))
            draw.ellipse([x, y, x + glow, y + glow], fill=(255, 240, 170, 220))
    else:  # mist / dust
        for _ in range(16):
            x = (RNG.integers(0, W) + u * 90) % W
            y = RNG.integers(120, 900)
            draw.ellipse([x, y, x + 260, y + 60], fill=(210, 220, 230, 16))
    return layer


def grade(image: Image.Image, kind: str, glow: float) -> Image.Image:
    array = np.asarray(image, dtype=np.float32) / 255.0
    tint = np.array(GRADE[kind], dtype=np.float32)
    array = np.clip(array * tint + glow, 0.0, 1.0)
    return Image.fromarray((array * 255).astype(np.uint8))


def caption_image(text: str, keywords: list[str]) -> Image.Draw:
    font_path = str(FONT)
    line_one, line_two = text, ""
    if len(text) > 26:
        best = None
        for index, char in enumerate(text):
            if char in "，；：、。？！":
                left, right = text[:index + 1], text[index + 1:]
                if len(left) <= 26 and len(right) <= 26:
                    balance = abs(len(left) - len(right))
                    if best is None or balance < best[0]:
                        best = (balance, left, right)
        if best:
            line_one, line_two = best[1], best[2]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    base = ImageFont.truetype(font_path, 62)
    big = ImageFont.truetype(font_path, 74)
    ordered = sorted(keywords, key=len, reverse=True)

    def draw_line(segment: str, y: int) -> None:
        pieces, i = [], 0
        while i < len(segment):
            hit = next((k for k in ordered if segment.startswith(k, i)), None)
            if hit:
                pieces.append((hit, True))
                i += len(hit)
            else:
                pieces.append((segment[i], False))
                i += 1
        widths = [draw.textlength(piece, font=big if flag else base) for piece, flag in pieces]
        total = sum(widths)
        x = (W - total) / 2
        for (piece, flag), width in zip(pieces, widths):
            font = big if flag else base
            draw.text((x, y), piece, font=font, fill="#f4c95f" if flag else "#ffffff",
                      stroke_width=4, stroke_fill="#08090b")
            x += width

    if line_two:
        draw_line(line_one, 900)
        draw_line(line_two, 982)
    else:
        draw_line(line_one, 946)
    return layer


def main() -> int:
    story = load_story()
    shots = story["shots"]
    keywords = story["presentation"]["highlight_keywords"]
    base_cache = {name: prepare_base(name) for name in set(SHOT_IMAGE.values())}
    yy, xx = np.mgrid[0:H, 0:W]
    distance = np.sqrt(((xx - W * 0.5) / (W * 0.62)) ** 2 + ((yy - H * 0.46) / (H * 0.78)) ** 2)
    alpha = np.clip((distance - 0.55) * 210, 0, 120).astype(np.uint8)
    vignette_array = np.zeros((H, W, 4), dtype=np.uint8)
    vignette_array[:, :, 3] = alpha
    vignette_array[:, :, 0:3] = (3, 5, 9)
    vignette = Image.fromarray(vignette_array, "RGBA")
    masks = None

    captions = {}
    audio_mix = WORK / "audiotest" / "audio" / "final-mix.wav"
    mix_report = json.loads((WORK / "audiotest" / "audio" / "mix-report.json").read_text(encoding="utf-8"))
    for row in mix_report["narration"]["shots"]:
        captions[row["id"]] = (row["speech_start"], row["speech_end"], caption_image(row["text"], keywords))

    out_video = WORK / "previs-picture.mp4"
    encoder = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(out_video),
    ], stdin=subprocess.PIPE)

    total_frames = 0
    for shot in shots:
        base = base_cache[SHOT_IMAGE[shot["id"]]]
        frames = shot["duration"] * FPS
        kind = SHOT_GRADE[shot["id"]]
        for index in range(frames):
            u = index / max(1, frames - 1)
            zoom = 1.0 + 0.06 * u
            width = int(W * zoom)
            height = int(width * base.height / base.width)
            frame = base.resize((width, height), Image.Resampling.BILINEAR)
            # 2.5D parallax: the crop drifts faster than the zoom, so the shot keeps moving.
            max_x = max(0, width - W)
            max_y = max(0, height - H)
            offset_x = int(max_x * (0.35 + 0.30 * u))
            offset_y = int(max_y * (0.45 + 0.10 * math.sin(u * math.pi)))
            frame = frame.crop((offset_x, offset_y, offset_x + W, offset_y + H))
            glow = 0.012 * math.sin(u * math.pi * 3.0) + (0.05 if kind == "fire" else 0.0)
            frame = grade(frame, kind, glow)
            frame = Image.alpha_composite(frame.convert("RGBA"),
                                          particle_layer(PARTICLES[shot["id"]], 24, index, frames))
            frame = Image.alpha_composite(frame, vignette)
            # subtitles
            clock = shot["start"] + index / FPS
            for start, end, layer in captions.values():
                if start <= clock <= end:
                    frame = Image.alpha_composite(frame, layer)
            draw = ImageDraw.Draw(frame)
            draw.text((1450, 30), "AI动画情景复原 · 非真实影像", font=ImageFont.truetype(str(FONT), 26),
                      fill=(210, 210, 206))
            encoder.stdin.write(frame.convert("RGB").tobytes())
            total_frames += 1
    encoder.stdin.close()
    encoder.wait()
    print("picture", out_video, total_frames, "frames")

    final = WORK / "Kinkakuji_Previs_1080p.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(out_video), "-i", str(audio_mix),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", "180", "-movflags", "+faststart", str(final),
    ], check=True)
    print("final", final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
