#!/usr/bin/env python3
"""迷案解码人系列封面的唯一版式：1080×1440，固定底板 + 期数角标 + 两行标题 + 片中截图窗口。

所有封面都走这一个函数，只换三样东西：期数、两行标题、窗口里的一张成片截图。
截图可以是本地图片路径，也可以是 Image 对象；不传时窗口留空（用于预览底板）。

版式坐标全部来自用户认可的第一期封面（IMG_0070.png），单位是像素：

    窗口外框  x 126–954, y 622–1027，奶油色描边 #b796 6a（2px）
    截图区    x 130–950, y 626–974
    字幕条    y 980–1025，底色 #15191d
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
W, H = 1080, 1440
# 仓库自带的 Noto Serif CJK 常用字子集：生成封面不依赖网络，也不需要系统字体。
DEFAULT_FONT = HERE / "NotoSerifCJKsc-Common.otf"

LABEL = "迷案解码人"
SERIES_EN = "MYSTERY DECODER"
FOOTER = "真实案件 · 动画情景复原"
TAGLINE = "真相，藏在细节里"
KICKER = "真实案件"
KICKER_EN = "CASE FILE  /  TRUE STORY"

# 窗口几何（左, 上, 右, 下）
WINDOW = (126, 622, 954, 1027)
SHOT_BOX = (130, 626, 950, 974)
CAPTION_TOP, CAPTION_BOTTOM = 980, 1025
BORDER = (183, 150, 106)
CAPTION_FILL = (21, 25, 29)
CAPTION_LEFT = "本片画面 · 动画情景复原"

INK = "#140d0c"
LINE1_COLOR = "#fff0d0"
LINE2_COLOR = "#efd19b"
CREAM = "#f0dfbd"
RED_BAR = "#b83d36"
BADGE_FILL = "#871e20"
BADGE_EDGE = "#c65c51"
BADGE_TEXT = "#fff2d9"
RULE = "#a55c4c"
DASH = "#a53330"
FOOTER_COLOR = "#b8a996"
SERIES_EN_COLOR = "#a68a7d"

DIGITS = "零一二三四五六七八九"


def episode_text(number: int) -> str:
    """1 → 第一期, 12 → 第十二期, 20 → 第二十期。"""
    if not 1 <= number <= 9999:
        raise ValueError("期数必须是 1 到 9999 的整数")
    result = ""
    zero_pending = False
    for divisor, unit in ((1000, "千"), (100, "百"), (10, "十"), (1, "")):
        digit, number = divmod(number, divisor)
        if digit:
            if zero_pending:
                result += "零"
                zero_pending = False
            if not (divisor == 10 and digit == 1 and not result):
                result += DIGITS[digit]
            result += unit
        elif result and number:
            zero_pending = True
    return f"第{result}期"


def plate() -> Image.Image:
    """固定底板：雨巷书房照 + 上下的深色压暗，中间留出截图窗口的位置。"""
    im = ImageOps.fit(Image.open(HERE / "background.png").convert("RGB"), (W, H),
                      method=Image.Resampling.LANCZOS).convert("RGBA")
    overlay = Image.new("RGBA", (W, H))
    pix = overlay.load()
    for y in range(H):
        if y < 110:
            alpha = 185
        elif y < 560:
            alpha = int(185 - (y - 110) * 0.10)
        elif y < 790:
            alpha = int(140 * (790 - y) / 230)
        elif y < 1120:
            alpha = 0
        else:
            alpha = int(180 * min(1, (y - 1120) / 240))
        alpha = max(0, min(255, alpha))
        for x in range(W):
            pix[x, y] = (3, 9, 17, alpha)
    return Image.alpha_composite(im, overlay).convert("RGB")


def fill_crop(image: Image.Image, width: int, height: int, y_bias: float = 0.5,
              x_bias: float = 0.5) -> Image.Image:
    """等比铺满并裁切；y_bias 控制竖向取景（0 顶 / 1 底）。"""
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((max(width, round(image.width * ratio)),
                            max(height, round(image.height * ratio))), Image.Resampling.LANCZOS)
    left = int((resized.width - width) * x_bias)
    top = int((resized.height - height) * y_bias)
    return resized.crop((left, top, left + width, top + height))


def fitted_font(font_path, draw, text, max_size, max_width, min_size=30):
    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(str(font_path), size)
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        if max(draw.textlength(text, font=font), right) - min(0, left) <= max_width:
            return font
    raise ValueError(f"文字无法适配宽度 {max_width}: {text}")


def window_frame(shot: Image.Image | None) -> Image.Image:
    """把截图和它的外框、字幕条画成一块贴图，坐标为全图坐标。"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    left, top, right, bottom = WINDOW
    inner_l, inner_t, inner_r, inner_b = SHOT_BOX

    # 窗口外的一圈投影，让照片从桌面上浮起来。
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((left - 6, top - 4, right + 6, bottom + 12), fill=(0, 0, 0, 190))
    layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(16)))

    draw = ImageDraw.Draw(layer)
    draw.rectangle((left - 4, top - 4, right + 4, bottom + 4), fill=(12, 14, 16, 255))
    draw.rectangle((left, top, right, bottom), fill=(*BORDER, 255))
    draw.rectangle((inner_l - 2, inner_t - 2, inner_r + 2, inner_b + 2), fill=(9, 10, 11, 255))

    if shot is not None:
        cropped = fill_crop(shot.convert("RGB"), inner_r - inner_l, inner_b - inner_t)
        mask = Image.new("L", cropped.size, 255)
        layer.paste(cropped, (inner_l, inner_t), mask)
    else:
        placeholder = Image.new("RGB", (inner_r - inner_l, inner_b - inner_t), (18, 22, 27))
        layer.paste(placeholder, (inner_l, inner_t))

    # 截图底部压一条渐变，字幕条不会显得硬切。
    fade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fade_draw = ImageDraw.Draw(fade)
    fade_h = 90
    for i in range(fade_h):
        alpha = int(200 * (i / fade_h) ** 1.6)
        fade_draw.line([(inner_l, inner_b - fade_h + i), (inner_r, inner_b - fade_h + i)],
                       fill=(10, 12, 14, alpha))
    layer = Image.alpha_composite(layer, fade)

    draw = ImageDraw.Draw(layer)
    draw.rectangle((inner_l, CAPTION_TOP, inner_r, CAPTION_BOTTOM), fill=(*CAPTION_FILL, 255))
    draw.line((inner_l, CAPTION_TOP, inner_r, CAPTION_TOP), fill=(*BORDER, 255), width=2)
    return layer


def cover(font_path=DEFAULT_FONT, episode: int = 1, line1: str = "", line2: str = "",
          shot: Image.Image | Path | None = None, shot_y_bias: float = 0.5,
          period: str | None = None) -> Image.Image:
    """生成一张 1080×1440 的系列封面；这是全系列唯一的封面版式。

    period 用来直接给角标文案（例如「第一期」），不传就按 episode 数字换算。
    """
    font_path = Path(font_path or DEFAULT_FONT)
    period = period or (episode_text(episode) if isinstance(episode, int) else str(episode))
    if isinstance(shot, (str, Path)):
        with Image.open(shot) as opened:
            shot = opened.convert("RGB").copy()

    im = plate().convert("RGBA")
    d = ImageDraw.Draw(im)
    font = lambda size: ImageFont.truetype(str(font_path), size)

    # 顶部：栏目名 + 期数角标 + 分隔线
    d.rectangle((62, 76, 68, 126), fill=RED_BAR)
    d.text((84, 72), LABEL, font=font(45), fill=CREAM, anchor="lt")
    d.rounded_rectangle((786, 72, 1016, 136), radius=7, fill=BADGE_FILL, outline=BADGE_EDGE, width=2)
    d.text((901, 84), period, font=fitted_font(font_path, d, period, 33, 190, min_size=16),
           fill=BADGE_TEXT, anchor="mt")
    d.line((62, 168, 1018, 168), fill=RULE, width=2)

    d.text((66, 207), KICKER, font=font(30), fill="#cd7f65", anchor="lt")
    d.text((260, 209), KICKER_EN, font=font(21), fill="#c4b9a8", anchor="lt")

    # 两行主标题
    for y, text, color in [(285, line1, LINE1_COLOR), (425, line2, LINE2_COLOR)]:
        f = fitted_font(font_path, d, text, 106, 940)
        d.text((66, y + 5), text, font=f, fill=INK, stroke_width=5, stroke_fill=INK, anchor="lt")
        d.text((66, y), text, font=f, fill=color, stroke_width=2, stroke_fill="#241914", anchor="lt")
    d.line((65, 585, 290, 585), fill=DASH, width=5)

    # 截图窗口
    im = Image.alpha_composite(im, window_frame(shot))
    d = ImageDraw.Draw(im)
    d.text((152, 1002), CAPTION_LEFT, font=font(25), fill=CREAM, anchor="lt")
    case_no = episode if isinstance(episode, int) else 1
    d.text((930, 1004), "CASE FILE  /  %02d" % case_no,
           font=font(19), fill=CREAM, anchor="rt")

    # 底部
    d.text((65, 1275), TAGLINE, font=font(39), fill=CREAM, anchor="lt")
    d.text((65, 1352), FOOTER, font=font(25), fill=FOOTER_COLOR, anchor="lt")
    d.text((1014, 1352), SERIES_EN, font=font(20), fill=SERIES_EN_COLOR, anchor="rt")
    return im.convert("RGB")


def validate_line(value: str, name: str) -> None:
    if value != value.strip() or not value or len(value) > 18 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f"{name}须为 1–18 字的单行文字，首尾不能有空格")


def validate_glyphs(font_path, text: str) -> None:
    from fontTools.ttLib import TTFont

    with TTFont(font_path, fontNumber=0, lazy=True) as font:
        cmap = font.getBestCmap() or {}
    missing = sorted({char for char in text if not char.isspace() and ord(char) not in cmap})
    if missing:
        raise ValueError("字体缺字：" + " ".join(missing) + "；可用 --font 指定包含这些字的 OTF/TTF 字体")


__all__ = ["DEFAULT_FONT", "cover", "plate", "episode_text", "fill_crop", "fitted_font", "window_frame",
           "validate_line", "validate_glyphs", "W", "H", "np"]
