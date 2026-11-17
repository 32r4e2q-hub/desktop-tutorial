"""One speaking pace across all 30 lines.

2026-11-16 用户反馈：某个片段语速明显快过其它段。原因是渲染只允许加速、不允许放慢，
每条合成语音按服务商随机语速念完再被硬塞进镜头窗口。现在统一到 3.45 字/秒。
"""
import importlib.util
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1] / "shibuya2006"
spec = importlib.util.spec_from_file_location("narration_pace", PROJECT / "narration_pace.py")
pace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pace)


def test_fast_reading_is_slowed_down():
    text = "要讲清这一天，得回到十二月三十日，那个普通的下午。"   # 22 字, 7 秒镜头
    tempo = pace.tempo(text, source_seconds=5.15, target_seconds=7)
    assert tempo < 1.0, "读快了就应该放慢"
    assert 3.4 <= pace.rate(text, 5.15 / tempo) <= 3.9


def test_slow_reading_is_compressed():
    text = "长子读牙科，勇贵二十一岁，还在复读备考。"               # 17 字, 6 秒镜头
    tempo = pace.tempo(text, source_seconds=6.5, target_seconds=6)
    assert tempo > 1.0
    assert pace.rate(text, 6.5 / tempo) <= 3.9


def test_line_is_never_stretched_past_its_shot():
    text = "门开了。第二天一早，刑警在集训地找到勇贵。"
    for source in (4.0, 5.0, 5.9):
        seconds = pace.speech_seconds(text, source, 6)
        assert seconds <= 6 + 0.02, (source, seconds)


def test_absurdly_slow_clip_is_reported_not_hidden():
    """1.12x 已经压不进去时，manifest 必须报错，而不是悄悄冲进镜头。"""
    text = "一" * 24
    seconds = pace.speech_seconds(text, 9.0, 5)
    assert seconds > 5 + 0.02
