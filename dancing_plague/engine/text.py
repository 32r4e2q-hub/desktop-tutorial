"""Text rendering (titles, subtitles, captions) with the bundled Noto CJK fonts, via Pillow."""
from __future__ import annotations

import os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from .common import W, H, AH, BAR, blit, clamp01

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERIF = os.path.join(ROOT, "assets", "fonts", "NotoSerifCJKsc-Regular.otf")
SANS = os.path.join(ROOT, "assets", "fonts", "NotoSansCJKsc-Regular.otf")
_fonts = {}
_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def render_text(text, size=40, serif=True, color=(255, 255, 255), stroke=0, stroke_color=(0, 0, 0), spacing=0, pad=8):
    """Return (rgb uint8, alpha float32) of the rendered text with soft edges."""
    key = (text, size, serif, color, stroke, stroke_color, spacing)
    if key in _cache:
        return _cache[key]
    f = font(SERIF if serif else SANS, size)
    dummy = Image.new("L", (4, 4))
    d = ImageDraw.Draw(dummy)
    # letter spacing: draw char by char
    chars = list(text)
    widths = [d.textlength(c, font=f) for c in chars]
    total = int(sum(widths) + spacing * max(0, len(chars) - 1)) + 2 * pad + 2 * stroke
    asc, desc = f.getmetrics()
    hgt = asc + desc + 2 * pad + 2 * stroke
    img = Image.new("RGBA", (max(1, total), hgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad + stroke
    for c, w in zip(chars, widths):
        d.text((x, pad + stroke), c, font=f, fill=color + (255,), stroke_width=stroke, stroke_fill=stroke_color + (255,))
        x += w + spacing
    a = np.asarray(img, np.uint8)
    rgb = np.ascontiguousarray(a[..., :3])
    alpha = a[..., 3].astype(np.float32) / 255.0
    if len(_cache) > 64:
        _cache.pop(next(iter(_cache)))
    _cache[key] = (rgb, alpha)
    return rgb, alpha


def draw_text(canvas, text, cx, cy, size=40, serif=True, color=(255, 255, 255), opacity=1.0, stroke=0,
              stroke_color=(0, 0, 0), spacing=0, anchor="center", shadow=True):
    if opacity <= 0.001 or not text:
        return
    rgb, alpha = render_text(text, size, serif, color, stroke, stroke_color, spacing)
    h, w = alpha.shape
    if anchor == "center":
        x, y = cx - w / 2, cy - h / 2
    elif anchor == "left":
        x, y = cx, cy - h / 2
    else:
        x, y = cx - w, cy - h / 2
    if shadow:
        sh = cv2.GaussianBlur(alpha, (0, 0), max(1, size / 14)) * 0.85 * opacity
        blit(canvas, np.zeros_like(rgb), sh, int(x) + 2, int(y) + 3)
    blit(canvas, rgb, alpha * opacity, int(x), int(y))


def wrap_cjk(text, max_chars):
    """Greedy wrap for CJK text at punctuation when possible."""
    if len(text) <= max_chars:
        return [text]
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= max_chars:
            # try to break after the last punctuation within the line
            cut = max(cur.rfind(p) for p in "，。；：、！？—")
            if cut >= max_chars * 0.45:
                lines.append(cur[:cut + 1])
                cur = cur[cut + 1:]
            else:
                lines.append(cur)
                cur = ""
    if cur:
        lines.append(cur)
    return lines


def draw_subtitle(canvas, text, t_in_line, dur, size=30):
    """Subtitle in the lower letterbox area/bottom of the frame, fade in/out."""
    op = clamp01(t_in_line / 0.25) * clamp01((dur - t_in_line) / 0.35)
    if op <= 0:
        return
    lines = wrap_cjk(text, 26)
    y = H - BAR / 2 - (len(lines) - 1) * (size + 6) / 2
    for ln in lines:
        draw_text(canvas, ln, W / 2, y, size=size, serif=False, color=(236, 232, 224), opacity=op, stroke=2, stroke_color=(10, 10, 12), spacing=1)
        y += size + 6
