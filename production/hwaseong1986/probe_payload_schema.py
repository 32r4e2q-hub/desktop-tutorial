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
# 免费额度约 1 次/分钟：第一轮探针用 8 秒间隔连发，第三发就撞上
# 「You've reached the API rate limit for free users」，后面 6 个候选全被 429 挡住、
# 一个答案都没问到。间隔必须按分钟算。
GAP_SECONDS = float(os.environ.get("AGNES_PROBE_GAP", "80"))


def candidates(base: dict) -> dict:
    """按「最可能是对的」排序；键名就是要写回 generate.py 的形状名。

    第一轮探针已经问出三件事（收据 delivery/payload-schema-probe.json）：
      * `size` 收 —— 那一发的报错跳到了 num_frames，说明 size 本身没被拒；
      * `aspect_ratio` 收、`resolution` 不收（"resolution is not an allowed request field"）；
      * `num_frames` 不收 —— 时长要换字段表达（duration / seconds 二选一，这一轮问出来）。
    所以本轮候选都带 `size`，只在「时长字段叫什么」上做变化；最后留一个已知会 400 的对照组，
    用来确认报错路径没变、也确认 429 不是把一切都挡住了。
    """
    core = {k: v for k, v in base.items() if k not in ("width", "height", "num_frames", "frame_rate")}
    size = f"{base['width']}x{base['height']}"
    seconds = round(base["num_frames"] / base["frame_rate"], 3)
    return {
        "size_frame_rate_duration": {**core, "size": size, "frame_rate": base["frame_rate"],
                                     "duration": seconds},
        "size_duration": {**core, "size": size, "duration": seconds},
        "size_frame_rate_seconds": {**core, "size": size, "frame_rate": base["frame_rate"],
                                    "seconds": seconds},
        "size_seconds": {**core, "size": size, "seconds": seconds},
        "size_aspect_ratio_duration": {**core, "size": size, "aspect_ratio": "16:9",
                                       "duration": seconds},
        "size_frame_rate_num_frames": {**core, "size": size, "frame_rate": base["frame_rate"],
                                       "num_frames": base["num_frames"]},
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
                 "body_excerpt": " ".join(str(text or "").split())[:1500]}
        if isinstance(response_body, dict):
            entry["video_id"] = response_body.get("video_id") or response_body.get("id")
            entry["task_id"] = response_body.get("task_id")
        if code == 429:
            # 429 是限流，不是「这个形状不行」：等一个间隔原地重试一次，别把两者混为一谈。
            print(f"PROBE_RATE_LIMITED {name}; waiting {GAP_SECONDS:g}s then retrying once", flush=True)
            time.sleep(GAP_SECONDS)
            entry["retried"] = True
            try:
                code, response_body, text = agnes.http_json(
                    "POST", base_url + "/v1/videos", key, body, timeout=120)
            except Exception as exc:
                code, response_body, text = None, None, f"{type(exc).__name__}: {exc}"
            entry.update(http_status=code, body_excerpt=" ".join(str(text or "").split())[:1500])
        receipt["attempts"].append(entry)
        print(f"PROBE_SHAPE {name} -> HTTP {code}: {entry['body_excerpt'][:200]}", flush=True)
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
