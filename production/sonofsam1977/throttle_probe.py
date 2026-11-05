#!/usr/bin/env python3
"""Print the plan-derived creation pacing so it can be audited without calling the API."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from throttle import FAST_MINIMUM_INTERVAL, RequestGate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pacing", action="store_true")
    args = parser.parse_args()
    gate = RequestGate(minimum_interval=FAST_MINIMUM_INTERVAL, allow_fast_plan=True)
    print(json.dumps({
        "plan": "paid monthly key: 5 video creations per minute, 500 video-seconds per day",
        "creation_interval_seconds": gate.interval,
        "creations_per_minute": round(60.0 / gate.interval, 1),
        "workers": 5,
        "poll_timeout_seconds": 5400,
        "story_seconds_total": sum(s["duration"] for s in json.loads(
            (HERE / "story.json").read_text(encoding="utf-8"))["shots"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
