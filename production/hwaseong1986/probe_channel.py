#!/usr/bin/env python3
"""供应商通道探针：沙箱连不上 Agnes，只能让 Actions 代问。

2026-10-10 定位到的根因（三级）：
1. ``agnes-video-v2.0``（旧 num_frames/frame_rate/width/height 接口）已从目录下线；
2. 新模型 ``agnes-video-2.5`` 对本 key 是 HTTP 403「Insufficient user quota, $0.000000」
   ——付费模型，key 没有余额；
3. 免费档只剩 ``agnes-video-2.5-flash``（新接口：mode/seconds/size/aspect_ratio，
   size 只能 720P），但它对免费用户有速率限制（429）。

所以探针默认**只发一个请求**（flash@720P），避免自己的突发把免费档速率打满；
需要问别的组合时，在 PROBE_REQUEST 第一行写参数，例如：
    probe --models agnes-video-2.5 --sizes 1080P
    probe --models agnes-video-2.5-flash agnes-video-2.5 --sizes 720P 1080P

纯诊断：永不失败，不碰 results.json / story.json，只在分支留 probe.log。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import agnes_video as agnes  # noqa: E402


def marker_args() -> list[str]:
    """PROBE_REQUEST 第一行当作额外命令行参数（便于不改工作流就能换探测目标）。"""
    path = HERE / "PROBE_REQUEST"
    if not path.exists():
        return []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            return line.split()
    return []


def modern_payload(model: str, seconds: str, size: str, aspect: str = "16:9") -> dict:
    """按 Agnes Video 2.5 文档构造的最小可创建请求。"""
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="*", default=["agnes-video-2.5-flash"])
    parser.add_argument("--sizes", nargs="*", default=["720P"])
    parser.add_argument("--seconds", default="5")
    opts = parser.parse_args(marker_args())

    key = os.getenv("AGNES_API_KEY", "").strip()
    base = os.getenv("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).rstrip("/")
    lines: list[str] = []
    lines.append("PROBE %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    lines.append("base=%s legacy_model=%s key_present=%s targets=%s"
                 % (base, agnes.DEFAULT_MODEL, bool(key),
                    json.dumps([[m, s] for m in opts.models for s in opts.sizes])))

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
    except Exception as exc:
        lines.append("MODELS_ERROR %r" % (exc,))

    # --- 2) 逐个真实创建请求（每个之间隔 20 秒，避免自己打满免费档） --------
    if not key:
        lines.append("CREATE_SKIPPED no AGNES_API_KEY")
    else:
        for index, model in enumerate(opts.models):
            for size in opts.sizes:
                if index or size != opts.sizes[0]:
                    time.sleep(20)
                payload = modern_payload(model, opts.seconds, size)
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
    lines.append("VERDICT %s" % ("new_model_available" if ok else "no_working_combo"))

    report = "\n".join(lines) + "\n"
    (HERE / "probe.log").write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
