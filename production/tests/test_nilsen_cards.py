"""Nilsen card-text fit guard: no clipped card titles, no rebounding crops.

第 4 次出片复检抓到两类静默失败：
1. S09/S38 的大标题超出纸面被裁边（复检只量了面板、没量文字）→ render.centered 必须带 max_width 自适应；
2. S02 的裁切按接触表中间帧量、没覆盖成片实际用到的源头 → TIGHTER_CROPS 改动后必须验算不触限。

本文件只用 PIL 默认字体（load_default），不依赖中文字体，离线可跑。
"""
import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production" / "nilsen"))
# 注意：不能直接写 import render——test_dahlia_edit 先 import 过 dahlia 的 render，
# 同名模块会被 sys.modules 缓存串掉。必须用唯一名按路径加载。
_spec = importlib.util.spec_from_file_location(
    "nilsen_render_under_test", ROOT / "production" / "nilsen" / "render.py")
nilsen_render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nilsen_render)


def _default_font(size, serif=False):
    return ImageFont.load_default(size=size)


class CardFitTests(unittest.TestCase):
    def setUp(self):
        self._orig_font = nilsen_render.font
        nilsen_render.font = _default_font
        self.img = Image.new("RGB", (1920, 1080), "black")
        self.draw = ImageDraw.Draw(self.img)

    def tearDown(self):
        nilsen_render.font = self._orig_font

    def test_short_text_keeps_size(self):
        seen = []
        orig = nilsen_render.font

        def spy(size, serif=False):
            seen.append(size)
            return orig(size, serif)

        nilsen_render.font = spy
        nilsen_render.centered(self.draw, "short title", 300, 108, "#fff", max_width=1412)
        self.assertEqual(seen, [108])

    def test_long_text_shrinks_to_fit(self):
        seen = []
        orig = nilsen_render.font

        def spy(size, serif=False):
            seen.append(size)
            return orig(size, serif)

        nilsen_render.font = spy
        text = "一九八三年十一月四日·中央刑事法院" * 2 + "一九八三年"
        nilsen_render.centered(self.draw, text, 300, 108, "#fff", max_width=1412)
        self.assertGreater(len(seen), 1)
        self.assertLess(seen[-1], 108)
        box = self.draw.textbbox((0, 0), text, font=orig(seen[-1]))
        self.assertLessEqual(box[2] - box[0], 1412)

    def test_absurd_text_raises_instead_of_clipping(self):
        with self.assertRaises(RuntimeError):
            nilsen_render.centered(self.draw, "x" * 500, 300, 108, "#fff", max_width=50)

    def test_tighter_crops_never_clamp(self):
        # 对 qa/ 里有源尺寸的每一镜：裁切窗的理论位置离画面边界不得超过 8px，
        # 否则 min(max()) 会把窗夹回来、裁切静默失效（S31 第一版就差点这样：牌子在右缘露出）。
        # 8px 内容差（0.7%）无视觉影响：S04/S45 的 y0 理论值 -3px 就是这么来的，不值得为此重渲两镜。
        for sid, (zoom, cx, cy) in nilsen_render.TIGHTER_CROPS.items():
            qa = ROOT / "production" / "nilsen" / "qa" / f"{sid}.json"
            if not qa.exists():
                self.skipTest(f"no qa receipt for {sid}")
            info = json.loads(qa.read_text())
            W, H = info["width"], info["height"]
            cw = math.floor(W / zoom / 2) * 2
            ch = math.floor(H / zoom / 2) * 2
            x0 = round(W * cx - cw / 2)
            y0 = round(H * cy - ch / 2)
            self.assertGreaterEqual(x0, -8, f"{sid} 左边界触限会被夹回")
            self.assertGreaterEqual(y0, -8, f"{sid} 上边界触限会被夹回")
            self.assertLessEqual(x0 + cw, W + 8, f"{sid} 右边界触限会被夹回")
            self.assertLessEqual(y0 + ch, H + 8, f"{sid} 下边界触限会被夹回")


if __name__ == "__main__":
    unittest.main()
