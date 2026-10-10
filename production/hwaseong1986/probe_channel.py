#!/usr/bin/env python3
"""供应商通道探针：沙箱连不上 Agnes，只能让 Actions 代问。

2026-10-10 定位到的根因（三级）：
1. ``agnes-video-v2.0``（旧 num_frames/frame_rate/width/height 接口）已从供应商目录下线，
   任何请求都返回 ``HTTP 503 No available channel ... (code=model_not_found)``；
2. 新模型 ``agnes-video-2.5`` 对本 key 是 HTTP 403「Insufficient user quota, $0.000000」
   ——付费模型，key 没有余额；
3. 免费档只剩 ``agnes-video-2.5-flash``（新接口 mode/seconds/size/aspect_ratio，size 只能
   720P），对免费用户有速率限制（429，突发就会踩），队列满时返回 503 video queue is full。

所以本探针做两件事：
1. 打印完整模型目录；
2. 用**生产代码真正会发的 payload**（generate.py::full_payload）各做一次创建请求，
   默认取 S01（纯文本）和 S06（参考图 + <Picture 1>）两种形状，20 秒错开，避免自己打满速率。

标记文件 PROBE_REQUEST 第一行可以传参，例如：
    probe --shots S06
    probe --shots S01 S06

纯诊断：永不失败，不碰 results.json / story.json，只在分支留 probe.log。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))   # production/（agnes_video）
sys.path.insert(0, str(HERE))          # 本项目目录

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


def load_generator():
    """导入本项目的 generate.py 只用它的 full_payload（模块级无副作用）。"""
    spec = importlib.util.spec_from_file_location("hwaseong_generate", HERE / "generate.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["hwaseong_generate"] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", nargs="*", default=["S01", "S06"])
    # parse_known_args：标记文件里写什么文字都不该让探针死掉（它是诊断工具）
    opts, _unknown = parser.parse_known_args(marker_args())

    key = os.getenv("AGNES_API_KEY", "").strip()
    base = os.getenv("AGNES_BASE_URL", agnes.DEFAULT_BASE_URL).rstrip("/")
    lines: list[str] = []
    lines.append("PROBE %s" % time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    lines.append("base=%s key_present=%s shots=%s" % (base, bool(key), opts.shots))

    # --- 1) 完整模型目录 ---------------------------------------------------
    catalog: list[str] = []
    try:
        code, body, _text = agnes.http_json("GET", base + "/v1/models", key, timeout=60)
        if isinstance(body, dict):
            data = body.get("data") or body.get("models") or []
            catalog = [m.get("id") for m in data if isinstance(m, dict) and m.get("id")]
        lines.append("MODELS http=%s count=%s" % (code, len(catalog)))
        lines.append("CATALOG %s" % json.dumps(catalog, ensure_ascii=False))
    except Exception as exc:
        lines.append("MODELS_ERROR %r" % (exc,))

    # --- 2) 用生产 payload 做真实创建请求 ----------------------------------
    if not key:
        lines.append("CREATE_SKIPPED no AGNES_API_KEY")
    else:
        try:
            generator = load_generator()
            story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
            lines.append("PROJECT_MODEL %s" % story.get("model"))
        except Exception as exc:
            lines.append("SETUP_ERROR %r" % (exc,))
            story, generator = None, None
        if story is not None:
            for index, sid in enumerate(opts.shots):
                if index:
                    time.sleep(20)
                shot = next((s for s in story["shots"] if s["id"] == sid), None)
                if shot is None or shot.get("kind") != "agnes":
                    lines.append("SKIP %s (not an Agnes shot)" % sid)
                    continue
                try:
                    payload = generator.full_payload(story, shot)
                    lines.append("PAYLOAD %s %s" % (
                        sid, json.dumps({k: payload.get(k) for k in
                                         ("model", "mode", "seconds", "size",
                                          "aspect_ratio", "seed")}, ensure_ascii=False)))
                    lines.append("PAYLOAD_HAS_IMAGES %s %s" % (
                        sid, bool(payload.get("images"))))
                    created = agnes.create_task(base, key, payload, retries=1, retry_delay=0)
                    task = {k: created.get(k) for k in ("id", "video_id", "task_id", "status")}
                    lines.append("CREATE_OK %s %s" % (sid, json.dumps(task, ensure_ascii=False)))
                except Exception as exc:
                    text = str(exc).replace(key, "[redacted]") if key else str(exc)
                    lines.append("CREATE_FAIL %s %s" % (sid, text[:260]))

    ok = [l.split()[1] for l in lines if l.startswith("CREATE_OK")]
    lines.append("WORKING_SHOTS %s" % json.dumps(ok, ensure_ascii=False))
    lines.append("VERDICT %s" % ("channel_up" if ok else "channel_not_ready"))

    report = "\n".join(lines) + "\n"
    (HERE / "probe.log").write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
