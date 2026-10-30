#!/usr/bin/env python3
"""画 7 张「角色与场景定稿板」（离线工具，不参与出片）。

本机的图像生成通道不可用时，定稿板用程序绘制：色板 + 三分线构图 + 剪影示意 + 美术要点，
不冒充渲染帧。等 Agnes 片段到齐后，``refresh_reference_frames.py`` 会用成片里的真实帧
覆盖同名文件，那时这 7 张才是「定稿参考图」的最终形态。

    python3 production/wakayama1998/make_reference_boards.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "reference"
W, H = 1600, 900

BOARDS = [
    ("01", "MASUMI · CHARACTER FINALS", "reference/01-hayashi-masumi.png",
     ["37, petite, short permed curly hair", "floral summer blouse, apron in the kitchen",
      "two states: bright laugh / stubborn silence"],
     [(28, 24, 20), (196, 92, 54), (232, 176, 116), (244, 201, 95), (120, 96, 84), (206, 198, 186)], "figure"),
    ("02", "KENJI · CHARACTER FINALS", "reference/02-hayashi-kenji.png",
     ["early fifties, thin, slightly stooped", "work shirt, faded jacket, cigarette",
      "silent, avoids the lens"],
     [(18, 20, 22), (58, 62, 66), (96, 92, 84), (176, 150, 112), (222, 210, 190), (244, 201, 95)], "figure"),
    ("03", "SONOBE STREET · SUMMER FESTIVAL", "reference/03-sonobe-street-festival.png",
     ["narrow lane, two-storey houses, overhead wires", "red paper lanterns, bunting, folding tables",
      "amber-orange dusk, cicada haze"],
     [(20, 22, 26), (48, 40, 40), (196, 62, 44), (240, 138, 62), (248, 206, 130), (120, 140, 132)], "street"),
    ("04", "GARAGE · THE BIG POT", "reference/04-garage-big-pot.png",
     ["aluminium pot wide as a bathtub, steam", "lantern light mirrored on polished metal",
      "cold gust tears the steam apart"],
     [(16, 16, 18), (64, 66, 70), (140, 140, 142), (198, 66, 40), (238, 168, 96), (96, 116, 118)], "pot"),
    ("05", "HOSPITAL · EMERGENCY NIGHT", "reference/05-hospital-night.png",
     ["pale green walls, cold fluorescent tubes", "polished floor, curtained bays",
      "cyan-grey night, one warm spill"],
     [(12, 18, 20), (36, 58, 60), (96, 128, 128), (168, 196, 194), (236, 240, 238), (206, 132, 72)], "corridor"),
    ("06", "LABORATORY · THE TRACE", "reference/06-lab-and-report.png",
     ["steel benches, old instrument, CRT screen", "white coat, glasses, latex gloves",
      "abstract unreadable curve spiking"],
     [(10, 12, 14), (30, 38, 44), (70, 92, 104), (140, 176, 186), (226, 236, 238), (244, 201, 95)], "lab"),
    ("07", "PRESS & COURT · TWO ROOMS", "reference/07-press-and-court.png",
     ["1998 shoulder cameras, flashguns, garden hose", "2002 dark wood courtroom, black robe",
      "left warm dusk, right cold grey"],
     [(18, 16, 16), (120, 46, 34), (232, 160, 88), (60, 64, 66), (140, 146, 148), (226, 226, 222)], "split"),
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                      "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def grain(image: Image.Image, strength: int = 3) -> Image.Image:
    array = np.asarray(image).astype(np.int16)
    noise = np.random.default_rng(1998).normal(0, strength, array.shape[:2])[:, :, None]
    return Image.fromarray(np.clip(array + noise, 0, 255).astype(np.uint8))


def glow(draw_image: Image.Image, centre, radius, colour, alpha=150) -> Image.Image:
    layer = Image.new("RGBA", draw_image.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x, y = centre
    d.ellipse((x - radius, y - radius, x + radius, y + radius), fill=colour + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.55))
    return Image.alpha_composite(draw_image.convert("RGBA"), layer)


def draw_figure(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, colour) -> None:
    head_r = int(46 * scale)
    draw.ellipse((x - head_r, y - int(300 * scale), x + head_r, y - int(300 * scale) + head_r * 2), fill=colour)
    draw.rounded_rectangle((x - int(80 * scale), y - int(250 * scale), x + int(80 * scale), y + int(60 * scale)),
                           radius=int(36 * scale), fill=colour)
    draw.rounded_rectangle((x - int(70 * scale), y + int(40 * scale), x + int(70 * scale), y + int(300 * scale)),
                           radius=int(26 * scale), fill=colour)


def build_board(index: str, title: str, path: Path, notes: list[str], palette, motif: str) -> None:
    base = Image.new("RGB", (W, H), (14, 15, 17))
    d = ImageDraw.Draw(base)
    for y in range(H):  # subtle vertical gradient
        shade = int(14 + 26 * (1 - y / H))
        d.line([(0, y), (W, y)], fill=(shade, shade + 1, shade + 3))
    frame = (120, 236, 1800, 846)
    d.rectangle(frame, outline=(70, 72, 78), width=3)
    for x in (frame[0] + (frame[2] - frame[0]) // 3, frame[0] + 2 * (frame[2] - frame[0]) // 3):
        for yy in range(frame[1], frame[3], 18):
            d.line([(x, yy), (x, yy + 9)], fill=(64, 66, 72), width=1)
    for y in (frame[1] + (frame[3] - frame[1]) // 3, frame[1] + 2 * (frame[3] - frame[1]) // 3):
        for xx in range(frame[0], frame[2], 18):
            d.line([(xx, y), (xx + 9, y)], fill=(64, 66, 72), width=1)

    warm, gold = (232, 160, 88), (244, 201, 95)
    if motif == "figure":
        colour = (58, 56, 62)
        draw_figure(d, 660, 800, 1.0, colour)
        draw_figure(d, 1180, 800, 0.86, (44, 44, 50))
        base = glow(base, (660, 520), 210, warm, 90)
        d = ImageDraw.Draw(base)
    elif motif == "street":
        for i, x in enumerate(range(260, 1720, 200)):
            d.rectangle((x, 470, x + 150, 780), fill=(40, 40, 46) if i % 2 else (34, 36, 42))
        for i, x in enumerate(range(220, 1760, 130)):
            base = glow(base, (x, 420 + (i % 2) * 26), 46, (228, 96, 62), 120)
        d = ImageDraw.Draw(base)
        d.line([(120, 780), (1800, 780)], fill=(58, 58, 62), width=4)
        for i, x in enumerate(range(320, 1600, 240)):
            draw_figure(d, x, 800, 0.34, (30, 28, 30))
    elif motif == "pot":
        base = glow(base, (960, 620), 320, warm, 80)
        d = ImageDraw.Draw(base)
        d.rounded_rectangle((640, 500, 1280, 790), radius=60, fill=(86, 88, 92), outline=(140, 142, 146), width=4)
        d.ellipse((640, 470, 1280, 560), fill=(52, 50, 52), outline=(150, 152, 156), width=3)
        for i, x in enumerate(range(720, 1240, 90)):
            d.arc((x, 330 + (i % 3) * 20, x + 70, 470), 250, 290, fill=(226, 226, 228), width=3)
    elif motif == "corridor":
        for i in range(8):
            inset = i * 58
            top = 236 + inset // 2
            bottom = 846 - max(inset // 2, inset // 2)
            if bottom - top < 40:
                break
            d.rectangle((120 + inset, top, 1800 - inset, bottom),
                        outline=(46 + i * 6, 56 + i * 6, 58 + i * 6), width=2)
        base = glow(base, (960, 300), 260, (206, 236, 238), 110)
        d = ImageDraw.Draw(base)
        draw_figure(d, 1120, 760, 0.5, (22, 28, 30))
    elif motif == "lab":
        d.rectangle((300, 560, 1620, 600), fill=(58, 66, 70))
        d.rounded_rectangle((760, 380, 1180, 560), radius=18, fill=(40, 48, 54), outline=(96, 120, 128), width=3)
        base = glow(base, (970, 470), 130, (176, 226, 226), 120)
        d = ImageDraw.Draw(base)
        trace = [(820 + i * 22, 520 - int(90 * np.sin(i * 0.7) * (0.3 + i / 12))) for i in range(17)]
        d.line(trace, fill=(226, 246, 246), width=3)
        draw_figure(d, 1480, 800, 0.6, (28, 32, 36))
    elif motif == "split":
        d.rectangle((120, 236, 960, 846), fill=(30, 24, 22))
        d.rectangle((960, 236, 1800, 846), fill=(26, 28, 30))
        for i, x in enumerate(range(200, 900, 130)):
            d.rectangle((x, 620, x + 92, 700), fill=(58, 46, 40))
            d.line([(x + 20, 620), (x + 70, 560)], fill=(150, 120, 96), width=4)
        base = glow(base, (420, 470), 150, (232, 140, 70), 90)
        d = ImageDraw.Draw(base)
        d.rectangle((260, 380, 900, 760), outline=(120, 120, 124), width=3)
        for x in range(1000, 1780, 90):
            d.line([(x, 236), (x, 846)], fill=(36, 40, 44), width=2)
        d.rectangle((1180, 300, 1580, 420), fill=(52, 44, 38))
        draw_figure(d, 1380, 820, 0.5, (16, 18, 20))

    d = ImageDraw.Draw(base)
    title_font = font(46)
    small = font(30)
    micro = font(24)
    d.text((120, 90), f"{index} / 07", font=small, fill=gold)
    d.text((120, 132), title, font=title_font, fill=(238, 236, 230))
    d.text((120, 196), "STYLE BIBLE · WAKAYAMA 1998 · 3D CINEMATIC REENACTMENT · 16:9",
           font=micro, fill=(150, 150, 154))

    y = 886
    for note in notes:
        d.text((120, y), "· " + note, font=small, fill=(198, 198, 200))
        y += 44
    # palette strip
    for i, colour in enumerate(palette):
        x0 = 1180 + i * 100
        d.rectangle((x0, 886, x0 + 88, 960), fill=colour, outline=(70, 72, 76))
        d.text((x0, 966), "#%02X%02X%02X" % colour, font=font(18), fill=(150, 150, 154))
    d.text((1180, 1014), "no readable text · stylized people, never real likenesses",
           font=font(22), fill=(160, 148, 120))

    image = grain(base, 3).filter(ImageFilter.GaussianBlur(0.4))
    OUT.mkdir(parents=True, exist_ok=True)
    image.convert("P", palette=Image.ADAPTIVE, colors=192).save(path, format="PNG", optimize=True)
    print("wrote", path, image.size)


def main() -> None:
    for index, title, rel, notes, palette, motif in BOARDS:
        build_board(index, title, HERE / rel, notes, palette, motif)


if __name__ == "__main__":
    main()
