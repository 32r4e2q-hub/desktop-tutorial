"""Explainer annotations must stay readable on bright frames.

2026-11-16 审核发现：金色说明字幕在 10–17 秒（白天的街道）和 85–91 秒（浅色厨房）几乎糊在
背景里。系列共用样式保持原样，shibuya2006 改用带半透明底板的 ExplainerPlate。
"""
import importlib.util
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1] / "shibuya2006"
sys.path.insert(0, str(PROJECT.parent))

spec = importlib.util.spec_from_file_location("gwangju_style_plate", PROJECT.parent / "gwangju_style.py")
style = importlib.util.module_from_spec(spec)
spec.loader.exec_module(style)

EXPLAINERS = [{"start": 10, "end": 17, "text": "时间倒回：2006年12月30日"}]


def _ass(plate: bool) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "s.ass"
        style.write_ass(path, [], [], None, "", [], EXPLAINERS, explainer_plate=plate)
        return path.read_text(encoding="utf-8")


def test_plated_explainer_draws_a_dark_box():
    text = _ass(True)
    line = next(l for l in text.splitlines() if l.startswith("Style: ExplainerPlate"))
    fields = line.split(",")
    assert fields[15] == "3", "BorderStyle 3 才会画底板"
    assert fields[16] >= "5", "Outline 即底板内边距"
    assert "&H99" in fields[5].upper() and "&H99" in fields[6].upper(), "底板必须半透明深色"


def test_series_default_style_is_unchanged():
    text = _ass(False)
    assert "ExplainerPlate" not in text
    line = next(l for l in text.splitlines() if l.startswith("Style: Explainer,"))
    assert line.split(",")[15] == "1", "其它期数仍用原来的描边样式"


def test_render_uses_the_plate():
    source = (PROJECT / "render.py").read_text(encoding="utf-8")
    assert "explainer_plate=True" in source
