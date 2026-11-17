"""One speaking pace for the whole film.

The 2026-11-16 v5 master had lines between 3.1 and 4.4 Hanzi per second because every
TTS clip is read at whatever pace the service chose and the renderer only ever sped
clips *up* to fit their shot. Listeners heard one segment as noticeably faster.

Rule: keep every line near ``TARGET_HANZI_PER_SECOND``. Clips read too fast are slowed
down (atempo < 1), clips read too slowly are compressed, and anything that would need
more than ``MAX_TEMPO`` (or would still overflow its shot) fails the build instead of
being rushed through.
"""
from __future__ import annotations

import re

TARGET_HANZI_PER_SECOND = 3.45
MIN_TEMPO = 0.84
MAX_TEMPO = 1.12


def hanzi_count(text: str) -> int:
    return len(re.sub(r"[^\u4e00-\u9fff]", "", text))


def desired_seconds(text: str, target_seconds: float) -> float:
    """How long this line should take, never longer than its own shot."""
    return min(float(target_seconds), hanzi_count(text) / TARGET_HANZI_PER_SECOND)


def tempo(text: str, source_seconds: float, target_seconds: float) -> float:
    want = desired_seconds(text, target_seconds)
    if want <= 0:
        raise ValueError("empty narration")
    return round(min(MAX_TEMPO, max(MIN_TEMPO, source_seconds / want)), 4)


def speech_seconds(text: str, source_seconds: float, target_seconds: float) -> float:
    return round(source_seconds / tempo(text, source_seconds, target_seconds), 3)


def rate(text: str, seconds: float) -> float:
    return round(hanzi_count(text) / seconds, 2) if seconds else 0.0
