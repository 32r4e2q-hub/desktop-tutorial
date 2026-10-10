#!/usr/bin/env python3
"""问出后继视频模型的 payload 形状：一次运行试完所有候选，把每个的 HTTP 状态与原文写回分支。

为什么需要它（2026-10-10 实测）：`agnes-video-v2.0` 被网关下线后换用 `agnes-video-2.5`，
创建请求立刻报

    HTTP 400: width is a forbidden field

共享实现 `production/agnes_video.py::build_payload()` 总是把 `width` / `height` 填进 payload
（由 aspect + resolution 换算而来），而新模型不收这两个字段。沙箱连不上 Agnes API，
只能在 runner 上试；一个一个试要一轮 Actions（约 6 分钟）才有一个答案，所以这里一次试完。

    AGNES_API_KEY=... python3 production/hwaseong1986/probe_payload_schema.py

输出 `production/hwaseong1986/delivery/payload-schema-probe.json`，
`winner` 就是 `generate.py::full_payload()` 该用的形状。400 不创建任务、不花额度；
一旦某个候选返回 2xx 就停下（那说明形状对了，任务留给正式生成那一轮去建）。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "production"))
sys.path.insert(0, str(HERE))

import agnes_video as agnes  # noqa: E402
import generate  # noqa: E402

RECEIPT = HERE / "delivery" / "payload-schema-probe.json"
GAP_SECONDS = 8.0


def candidates(base: dict) -> dict:
    """按「最可能是对的」排序；键名就是要写回 generate.py 的形状名。"""
    no_wh = {k: v for k, v in base.items() if k not in ("width", "height")}
    return {
        "size": {**no_wh, "size": f"{base['width']}x{base['height']}"},
        "aspect_ratio_resolution": {**no_wh, "aspect_ratio": "16:9", "resolution": "1080p"},
        "resolution_only": {**no_wh, "resolution": "1080p"},
        "aspect_ratio_only": {**no_wh, "aspect_ratio": "16:9"},
        "no_size_fields": no_wh,
        "frames_as_duration": {**{k: v for k, v in no_wh.items()
                                  if k not in ("num_frames", "frame_rate")},
                               "duration": round(no_wh["num_frames"] / no_wh["frame_rate"], 3)},
        "minimal": {k: base[k] for k in ("model", "prompt") if k in base},
        "legacy_width_height": base,   # 对照组：已知会 400，用来确认报错路径没变
    }


def main() -> int:
    key = os.environ.get("AGNES_API_KEY", "").strip()
    base_url = os.environ.get("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).rstrip("/")
    project = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    model = os.environ.get("AGNES_VIDEO_MODEL", generate.MODEL).strip() or generate.MODEL
    shot = next(s for s in project["shots"] if s["id"] == os.environ.get("PROBE_SHOT", "S01"))
    payload = generate.full_payload(project, shot)
    payload["model"] = model

    receipt = {"model": model, "base": base_url, "shot": shot["id"],
               "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "api_key_present": bool(key), "attempts": [], "winner": None}
    if not key:
        receipt["error"] = "AGNES_API_KEY is unavailable"
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("PROBE_NO_KEY")
        return 1

    for name, body in candidates(payload).items():
        fields = sorted(body)
        try:
            code, response_body, text = agnes.http_json("POST", base_url + "/v1/videos", key, body, timeout=120)
        except Exception as exc:  # 网络层失败也要记下来，别把整轮探针弄丢
            code, response_body, text = None, None, f"{type(exc).__name__}: {exc}"
        entry = {"shape": name, "fields": fields, "http_status": code,
                 "body_excerpt": " ".join(str(text or "").split())[:500]}
        if isinstance(response_body, dict):
            entry["video_id"] = response_body.get("video_id") or response_body.get("id")
            entry["task_id"] = response_body.get("task_id")
        receipt["attempts"].append(entry)
        print(f"PROBE_SHAPE {name} -> HTTP {code}: {entry['body_excerpt'][:160]}", flush=True)
        if code is not None and 200 <= code < 300:
            receipt["winner"] = name
            print(f"PROBE_WINNER {name}", flush=True)
            break
        time.sleep(GAP_SECONDS)

    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PROBE_RECEIPT " + str(RECEIPT.relative_to(ROOT)))
    return 0 if receipt["winner"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
