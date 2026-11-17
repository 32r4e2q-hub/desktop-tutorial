"""One speaking pace for the whole film.

The v5 master (2026-11-16) had lines between 3.1 and 4.8 Hanzi per second of *speech*
because every TTS take is read at whatever pace the service chose, and the renderer only
ever sped clips *up* to fit their shot. Listeners heard one segment as noticeably faster.

Two mistakes are easy here, and both were made once:

1. Measuring pace against the **file** duration. Take files carry variable leading and
   trailing silence, so a perfectly normal read can look "slow" and get sped up.
2. Only allowing speed-up. A slow take then has to be rushed to fit, which is exactly
   the artefact people hear.

Rule now: measure the **voiced** duration (silence stripped), and match every line to
``TARGET_VOICED_HANZI_PER_SECOND`` by slowing or compressing it. Anything outside
``MIN_TEMPO``..``MAX_TEMPO``, or that still would not fit its shot, fails the build.
"""
from __future__ import annotations

import re

TARGET_VOICED_HANZI_PER_SECOND = 4.5
MIN_TEMPO = 0.82
MAX_TEMPO = 1.25


def hanzi_count(text: str) -> int:
    return len(re.sub(r"[^\u4e00-\u9fff]", "", text))


def voiced_rate(text: str, voiced_seconds: float) -> float:
    return round(hanzi_count(text) / voiced_seconds, 2) if voiced_seconds > 0 else 0.0


def desired_voiced_seconds(text: str, target_seconds: float, target_rate: float | None = None) -> float:
    rate = target_rate or TARGET_VOICED_HANZI_PER_SECOND
    return min(float(target_seconds), hanzi_count(text) / rate)


def tempo(text: str, voiced_seconds: float, target_seconds: float, target_rate: float | None = None) -> float:
    """How much to retime a take so its spoken pace matches the rest of the film."""
    want = desired_voiced_seconds(text, target_seconds, target_rate)
    if want <= 0 or voiced_seconds <= 0:
        raise ValueError("empty narration or clip")
    return round(min(MAX_TEMPO, max(MIN_TEMPO, voiced_seconds / want)), 4)


def delivered_rate(text: str, voiced_seconds: float, tempo_value: float) -> float:
    return voiced_rate(text, voiced_seconds / tempo_value) if tempo_value else 0.0
