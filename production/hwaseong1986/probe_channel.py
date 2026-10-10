#!/usr/bin/env python3
"""供应商通道探针：沙箱连不上 Agnes，只能让 Actions 代问。

2026-10-10 定位到根因：``agnes-video-v2.0``（旧的 num_frames/frame_rate/width/height
接口）已从供应商目录里下线，目录里只剩 ``agnes-video-2.5`` / ``agnes-video-2.5-flash``
（OpenAI Videos 风格接口：mode/seconds/size/aspect_ratio，且禁止传 width/height/fps）。
所以每一此提交都报 ``model_not_found``——这不是容量故障，是模型改名。

探针回答：
1. ``GET /v1/models`` 的完整目录（含原始 JSON）；
2. 用**新接口的真实 payload** 对每个候选模型各做一次创建请求，报清楚哪个能通、
   哪个尺寸档能用（本片要 1920×1080，所以 1080P 必须可用）。

设计约束：纯诊断，**永不失败**，不碰 results.json / story.json，只在分支留 probe.log。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import agnes_video as agnes  # noqa: E402

CANDIDATES = ["agnes-video-2.5", "agnes-video-2.5-flash"]


def modern_payload(model: str, seconds: str, size: str, aspect: str = "16:9") -> dict:
    """按新接口（Agnes Video 2.5 文档）构造的最小可创建请求。"""
    return {
        "model": model,
        "prompt": "Channel probe: a quiet South Korean village lane at dusk, "
                  "static camera, no people, no text.",
        "mode": "text",
        "seconds": seconds,
        "size": size,
        "aspect_ratio": aspect,
        "n": 1,
    }


def main() -> int:
    key = os.getenv("AGNES_API_KEY", "").strip()
    base = os.getenv("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).rstrip("/")
    lines: list[str] = []
    lines.append("PROBE %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    lines.append("base=%s legacy_model=%s key_present=%s"
                 % (base, agnes.DEFAULT_MODEL, bool(key)))

    # --- 1) 完整模型目录 ---------------------------------------------------
    catalog: list[str] = []
    try:
        code, body, _text = agnes.http_json("GET", base + "/v1/models", key, timeout=60)
        if isinstance(body, dict):
            data = body.get("data") or body.get("models") or []
            catalog = [m.get("id") for m in data if isinstance(m, dict) and m.get("id")]
        lines.append("MODELS http=%s count=%s" % (code, len(catalog)))
        lines.append("CATALOG %s" % json.dumps(catalog, ensure_ascii=False))
        lines.append("LEGACY_MODEL_IN_CATALOG %s" % (agnes.DEFAULT_MODEL in catalog))
        lines.append("MODELS_RAW %s" % json.dumps(body, ensure_ascii=False)[:1500])
    except Exception as exc:
        lines.append("MODELS_ERROR %r" % (exc,))

    # --- 2) 新接口真实创建请求（逐模型 × 逐尺寸档） -------------------------
    if not key:
        lines.append("CREATE_SKIPPED no AGNES_API_KEY")
    else:
        for model in CANDIDATES:
            sizes = ["720P"] if "flash" in model else ["720P", "1080P"]
            for size in sizes:
                payload = modern_payload(model, "5", size)
                tag = "%s@%s" % (model, size)
                try:
                    created = agnes.create_task(base, key, payload, retries=1, retry_delay=0)
                    task = {k: created.get(k) for k in ("id", "video_id", "task_id", "status")}
                    lines.append("CREATE_OK %s %s" % (tag, json.dumps(task, ensure_ascii=False)))
                except Exception as exc:
                    text = str(exc).replace(key, "[redacted]") if key else str(exc)
                    lines.append("CREATE_FAIL %s %s" % (tag, text[:220]))

    ok = [l.split()[1] for l in lines if l.startswith("CREATE_OK")]
    lines.append("WORKING_COMBOS %s" % json.dumps(ok, ensure_ascii=False))
    lines.append("VERDICT %s" % (
        "new_model_available" if ok else
        ("catalog_lists_new_models_but_no_channel" if catalog else "no_catalog_no_channel")))

    report = "\n".join(lines) + "\n"
    (HERE / "probe.log").write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
