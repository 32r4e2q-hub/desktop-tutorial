#!/usr/bin/env python3
"""为需要跨镜保持面容的虚构演员生成 CogView 静态参考人像（不生成视频）。"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "qa" / "portrait-anchors"


def save(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "arena-sinjeong2005-anchor/1.0"})
    with urllib.request.urlopen(req, timeout=180) as response, path.open("wb") as out:
        shutil.copyfileobj(response, out, 256 * 1024)


def get(obj, key, default=None):
    return getattr(obj, key, None) or (obj.get(key, default) if isinstance(obj, dict) else default)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cast = json.loads((HERE / "cast.json").read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in cast["characters"]}
    api_key = os.environ["ZHIPUAI_API_KEY"].strip()
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=api_key)

    prompts = {
        "C1C2": ("横版16:9，电影真人双人定妆照，两位韩国男性调查员并肩站立，胸像构图，左边是" +
                 by_id["C1"]["face"] + "；右边是" + by_id["C2"]["face"] +
                 "。两张脸必须明显不同，左右位置固定，彼此不遮挡，正面清晰，自然严肃的表情，灰蓝低饱和电影布光，旧办公室虚化背景，无文字无标志。"),
        "C8": ("横版16:9，单人韩国女性调查员电影定妆照，胸像，" + by_id["C8"]["face"] +
               "，正面清晰，自然坚定的表情，灰蓝低饱和电影布光，旧办公室虚化背景，无文字无标志。"),
        "C9": ("横版16:9，单人韩国女性法医电影定妆照，胸像，" + by_id["C9"]["face"] +
               "，正面清晰，自然专注的表情，灰蓝低饱和电影布光，实验室虚化背景，无文字无标志。"),
    }
    report = {"created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "portraits": {}}
    for key, prompt in prompts.items():
        if len(prompt) > 1200:
            raise ValueError(f"{key}: CogView prompt unusually long ({len(prompt)})")
        response = client.images.generations(model="cogview-3-flash", prompt=prompt, size="1344x768")
        rows = get(response, "data", []) or []
        url = get(rows[0], "url") if rows else None
        if not url:
            raise RuntimeError(f"{key}: CogView 未返回 URL")
        path = OUT / f"{key}.jpg"
        save(url, path)
        row = {"url": url, "file": path.name,
               "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
        report["portraits"][key] = row
        print(f"PORTRAIT_READY {key} {row['bytes']} bytes sha={row['sha256']}", flush=True)
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PORTRAITS_DONE", flush=True)


if __name__ == "__main__":
    main()
