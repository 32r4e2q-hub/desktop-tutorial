"""One speaking pace across all 30 lines.

2026-11-16 用户反馈：某个片段语速明显快过其它段。根因有两条——渲染只允许加速、不允许放慢，
而且语速是按「文件时长」估的，文件首尾静音长度不一，于是一条正常朗读也可能被当成「太慢」
而硬加速。现在按「实际发声时长」把 30 条统一到 4.5 字/秒。
"""
import importlib.util
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1] / "shibuya2006"
spec = importlib.util.spec_from_file_location("narration_pace", PROJECT / "narration_pace.py")
pace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pace)


def test_fast_take_is_slowed_down():
    text = "要讲清这一天，得回到十二月三十日，那个普通的下午。"   # 22 字
    tempo = pace.tempo(text, voiced_seconds=4.49, target_seconds=7)
    assert tempo < 1.0, "读快了就应该放慢"
    assert abs(pace.delivered_rate(text, 4.49, tempo) - 4.5) < 0.05


def test_slow_take_is_compressed_within_the_limit():
    text = "长子读牙科，勇贵二十一岁，还在复读备考。"               # 17 字
    tempo = pace.tempo(text, voiced_seconds=5.46, target_seconds=6)
    assert tempo == pace.MAX_TEMPO
    assert pace.delivered_rate(text, 5.46, tempo) <= 4.6


def test_line_never_spills_past_its_shot():
    text = "门开了。第二天一早，刑警在集训地找到勇贵。"
    for voiced in (3.0, 3.9, 4.4):
        tempo = pace.tempo(text, voiced, 6)
        assert voiced / tempo <= 6 + 0.02, (voiced, tempo)


def test_hopeless_take_is_reported_not_hidden():
    """压缩到上限仍装不进镜头时，manifest 必须报错，而不是悄悄冲进镜头。"""
    text = "一" * 24
    tempo = pace.tempo(text, voiced_seconds=9.0, target_seconds=5)
    assert tempo == pace.MAX_TEMPO
    assert 9.0 / tempo > 5.02


def test_manifest_declares_one_pace_for_all_thirty_lines():
    manifest = json.loads((PROJECT / "audio" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["slowdown_allowed"] is True
    spec_row = manifest["pace"]
    rates = [clip["hanzi_per_second"] for clip in manifest["clips"]]
    tempos = [clip["atempo"] for clip in manifest["clips"]]
    assert len(rates) == 30
    assert max(rates) - min(rates) <= 0.25, (min(rates), max(rates))
    assert min(tempos) >= spec_row["min_tempo"] - 1e-6
    assert max(tempos) <= spec_row["max_tempo"] + 1e-6
    assert spec_row["measured_on"].startswith("spoken time")
