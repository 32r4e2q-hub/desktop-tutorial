#!/usr/bin/env python3
"""生成第一期样张与可离线使用的 HTML 编辑器。

版式只有一份：`template.cover`。这里的 `cover()` 只是薄封装，保证 CLI、编辑器样张和人手
生成的封面永远同一套坐标、同一套配色。
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import argparse, base64, zipfile

import template
from template import DEFAULT_FONT, FOOTER, HERE, H, LABEL, W, fitted_font
from template import cover as _cover

PERIOD = "第一期"
LINE1 = "逃亡78天的西口彰"
LINE2 = "却被女孩一眼认出"


def plate():
    return template.plate()


def cover(font_path=DEFAULT_FONT, period=PERIOD, line1=LINE1, line2=LINE2, plate_image=None,
          shot=None, shot_y_bias=0.5):
    """保留旧签名；period 写成「第二期」这类角标文案，或直接给期数整数。"""
    if isinstance(period, int):
        return _cover(font_path, period, line1, line2, shot=shot, shot_y_bias=shot_y_bias)
    return _cover(font_path, 1, line1, line2, shot=shot, shot_y_bias=shot_y_bias, period=str(period))


def write_editor(font_woff):
    # Everything is embedded: this HTML is usable as a single file after download.
    image64 = base64.b64encode((HERE / "plate.jpg").read_bytes()).decode("ascii")
    font64 = base64.b64encode(Path(font_woff).read_bytes()).decode("ascii")
    markup = (HERE / "editor_template.html").read_text(encoding="utf8")
    markup = markup.replace("__IMAGE_DATA__", image64).replace("__FONT_DATA__", font64)
    (HERE / "封面模板_可编辑.html").write_text(markup, encoding="utf8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--woff", type=Path, required=True)
    args = parser.parse_args()
    plate().save(HERE / "plate.jpg", quality=94, subsampling=0)
    cover(args.font).save(HERE / "第一期_西口彰_封面.png", optimize=True)
    write_editor(args.woff)
    with zipfile.ZipFile(HERE / "迷案解码人_封面模板.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in ["封面模板_可编辑.html", "第一期_西口彰_封面.png", "使用说明.txt", "OFL.txt"]:
            z.write(HERE / name, arcname=name)
    print("cover, editor, and package created")


if __name__ == "__main__":
    main()
