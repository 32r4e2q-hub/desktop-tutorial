"""光州胶带案默认画面文字层：共享引擎、模板脚手架与本案回归。"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "production"))
import gwangju_style  # noqa: E402
import new_topic  # noqa: E402


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_default_policy_keeps_captions_and_lower_middle_explainers():
    policy = gwangju_style.DEFAULT_CAPTION_POLICY
    assert "解说词字幕" in policy["regular"] or "旁白" in policy["regular"]
    assert "MarginV=62" in policy["regular"]
    assert "MarginV=200" in policy["explainer"]
    assert "中间偏下" in policy["explainer"]
    assert "MarginV=275" in policy["hook"]


def test_write_ass_burns_three_layers_and_validates_timing(tmp_path):
    path = tmp_path / "subtitles.ass"
    cues = [(0.0, 4.9, "2004年9月14日，光州北区，一间普通公寓。")]
    hooks = [{"id": "H1", "start": 0.0, "end": 2.0, "text": "22米胶带，留下未解疑问"}]
    explainers = [{"start": 2.1, "end": 4.8, "text": "案发于2004年9月14日 · 胶带约22米", "color": "gold"}]
    gwangju_style.write_ass(path, cues, ["22米胶带"], None, "AI动画情景重现 · 非真实影像", hooks, explainers)
    text = path.read_text(encoding="utf-8")
    assert "Style: Caption," in text and ",2,120,120,62,1" in text
    assert "Style: Hook," in text and ",2,100,100,275,1" in text
    assert "Style: Explainer," in text and ",2,120,120,200,1" in text
    assert text.count("Dialogue:") == 4  # caption + hook + explainer + label
    assert "Hook,,0,0,0" in text and "Explainer,,0,0,0" in text

    with pytest.raises(ValueError):
        gwangju_style.write_ass(tmp_path / "bad-hook.ass", cues, [], None, "",
                                [{"id": "H1", "start": 0.0, "end": 1.5, "text": "x"}], [])
    with pytest.raises(ValueError):
        gwangju_style.write_ass(tmp_path / "bad-explainer.ass", cues, [], None, "", [],
                                [{"start": 2.0, "end": 2.0, "text": "x"}])


def test_shanghai_render_uses_shared_text_layer():
    render = load_module("shanghai_render_shared", ROOT / "production/shanghai_freezer_case/render.py")
    assert render.write_ass is gwangju_style.write_ass
    assert render.ass_caption is gwangju_style.ass_caption
    template = (ROOT / "production/templates/render.py").read_text(encoding="utf-8")
    assert "from gwangju_style import" in template


def test_shanghai_story_publication_and_presentation_match_default():
    story = json.loads((ROOT / "production/shanghai_freezer_case/story.json").read_text(encoding="utf-8"))
    pres = story["presentation"]
    assert len(story["shots"]) == 30 and story["target_duration"] == 180
    assert "MarginV=200" in pres["caption_policy"]["explainer"]
    assert len(pres["hooks"]) >= 9 and len(pres["explainers"]) >= 9
    assert pres["publish_title"] == "她死了105天，丈夫用她的微信和妈妈聊了105天"
    assert pres["onscreen_label"] == "AI动画情景重现 · 非真实影像"


def test_scaffold_renders_hook_and_explainer_fields(tmp_path):
    dest = tmp_path / "production" / "styletest"
    new_topic.scaffold("styletest", "测试题目：光州默认文字层", "arena/style-test",
                       dest, ROOT / "production/shanghai_freezer_case")
    build = (dest / "build_story.py").read_text(encoding="utf-8")
    render = (dest / "render.py").read_text(encoding="utf-8")
    assert "HOOKS" in build and "EXPLAINERS" in build and "HIGHLIGHT_PHRASES" in build
    assert "gwangju_style" in render
    assert "presentation" in render and "hooks" in render and "explainers" in render
