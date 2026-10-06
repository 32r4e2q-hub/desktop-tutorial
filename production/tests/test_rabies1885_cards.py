"""卡片排字闸门：一行字不许越出画面。

2026-10-05 交付的候选成片里，片尾卡问句「医学史最该被记住的，是勇气，还是验证勇气的证据？」
按 96 px 排出来约 2304 px 宽，两端各被裁掉约两个字（成片 174–180 s 一直如此）。逐帧自动审计
只量黑帧、冻结、帧间差异和人脸/手，从不量文字有没有溢出画面 —— 于是整条流水线全绿，
画面却是坏的，只有人眼（或这条闸门）看得见。

这里守三条：

1. ``fit_size`` 必须把一行字缩到安全宽度以内，而不是让它被裁；
2. 真把 story.json 的片尾卡画出来，画面最外侧两列不许出现文字像素
   （端到端复现当初那次裁剪，缩号逻辑写错就会红）；
3. 缩号不能没有下限：主问句必须仍明显大于第二行（46 px），否则该改文案而不是一味缩号。

没有中文字体时跳过 —— 本仓库拒绝用缺字的字体出片，渲染工作流会装 ``fonts-noto-cjk``。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "production" / "rabies1885"


def load_project_render():
    """按路径加载本项目的 render.py。

    别的项目（dahlia / gilgo）也有 ``render.py`` / ``media.py`` / ``build_audio.py``，
    整套测试跑在一个进程里时 ``import render`` 会拿到先被导入的那一份。所以这里按文件加载、
    临时把同名模块挪开、再把 sys.path 复原，避免互相串味。
    """
    stashed = {name: sys.modules.pop(name) for name in ("render", "media", "build_audio")
               if name in sys.modules}
    path_snapshot = list(sys.path)
    spec = importlib.util.spec_from_file_location("rabies1885_render", PROJECT / "render.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["rabies1885_render"] = module
    try:
        spec.loader.exec_module(module)
    finally:
        for name in ("media", "build_audio"):
            sys.modules.pop(name, None)     # 本项目带进来的依赖副本不要留在全局
        sys.modules.update(stashed)         # 别的项目的同名模块原样放回
        sys.path[:] = path_snapshot
    return module


render = load_project_render()

PRESENTATION = json.loads((PROJECT / "story.json").read_text(encoding="utf-8"))["presentation"]
END_CARD = PRESENTATION["end_card"]
SUBTITLE_SIZE = 46      # 片尾卡第二行的字号；主问句必须明显大于它
LEGIBLE_FLOOR = 60


def font_available(serif: bool) -> bool:
    try:
        render.find_font(serif)
    except RuntimeError:
        return False
    return True


class CardLayoutTests(unittest.TestCase):
    def setUp(self):
        if not font_available(True) or not font_available(False):
            self.skipTest("缺少中文 Noto CJK 字体（渲染工作流会装 fonts-noto-cjk）")

    def test_long_line_is_shrunk_instead_of_clipped(self):
        question = END_CARD[0]
        draw = ImageDraw.Draw(Image.new("RGB", (1920, 1080)))
        self.assertGreater(render.text_width(draw, question, 96, serif=True),
                           render.CARD_TEXT_MAX_WIDTH,
                           "这条问句已经放得下 96 px 了？那这条闸门本身要重新看一眼")
        fitted = render.fit_size(draw, question, 96, render.CARD_TEXT_MAX_WIDTH, serif=True)
        self.assertLess(fitted, 96, "问句按 96 px 排会超出画面，必须缩号")
        self.assertLessEqual(render.text_width(draw, question, fitted, serif=True),
                             render.CARD_TEXT_MAX_WIDTH)
        self.assertGreaterEqual(fitted, LEGIBLE_FLOOR,
                                f"主问句被缩到 {fitted} px，已经不比 {SUBTITLE_SIZE} px 的副题大多少了："
                                "该改文案（build_story.py 的 END_CARD）而不是继续缩号")

    def test_end_card_keeps_text_off_the_frame_edges(self):
        """端到端：真画出片尾卡，左右各 100 px 的安全带里不许有字。

        判据用 100 px 宽的带（不是最外一列）：当初那次裁剪里，问句按 96 px 居中后
        第一二个字符整块落在画面外，第三四个字符就压在 0–96 px 这一带里、笔画发白，
        所以这条带能真的复现那次事故 —— 已验证：把 ``centered`` 换回不缩号的旧写法，
        这条断言会红（安全带最亮像素 243，阈值 120）。
        """
        with tempfile.TemporaryDirectory() as tmp:
            card = render.card_image("END", "", Path(tmp), PRESENTATION)
            pixels = np.asarray(Image.open(card).convert("L"), dtype=int)
        self.assertEqual(pixels.shape, (1080, 1920))
        self.assertGreater(pixels.max(), 200, "片尾卡上一个字都没有，闸门等于没测")
        bands = np.concatenate([pixels[:, :100].ravel(), pixels[:, -100:].ravel()])
        self.assertLess(int(bands.max()), 120,
                        "片尾卡有字落进左右 100 px 安全带：检查 render.centered / fit_size")


if __name__ == "__main__":
    unittest.main()
