#!/usr/bin/env python3
"""为双人剧情镜生成 CogView 场景首帧（人物在环境中，不是定妆照）。

图生视频的首帧决定构图：定妆照首帧会把视频锁成静态人像；
这里用「场景+人物动作」的剧照当首帧，让视频一开始就是剧情画面，
同时复用 cast.json 的面容描述原文，尽量保持与定妆照同一张脸。
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "qa" / "scene-frames"
SHOTS = ["S11", "S12", "S16", "S20", "S21", "S23", "S24"]


def save(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "arena-sinjeong2005-scene/1.0"})
    with urllib.request.urlopen(req, timeout=180) as response, path.open("wb") as out:
        shutil.copyfileobj(response, out, 256 * 1024)


def get(obj, key, default=None):
    return getattr(obj, key, None) or (obj.get(key, default) if isinstance(obj, dict) else default)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in story["shots"]}
    api_key = os.environ["ZHIPUAI_API_KEY"].strip()
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=api_key)

    anchors = {"created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "shots": {}}
    for sid in SHOTS:
        body = by_id[sid]["prompt"]
        body = re.split(r"，镜头|，纸面", body)[0]  # 去掉运镜类措辞，只留画面
        prompt = ("横版16:9电影剧照，2005年韩国首尔老住宅区写实真人剧情片，灰蓝低饱和，"
                  "人物身处真实环境中交谈行动，中景，三分之二侧面视角，自然生动的表情，"
                  "避免正面并排静止合影，无任何文字字幕标志：" + body)
        if len(prompt) > 1200:
            raise ValueError(f"{sid}: prompt too long {len(prompt)}")
        response = client.images.generations(model="cogview-3-flash", prompt=prompt, size="1344x768")
        rows = get(response, "data", []) or []
        url = get(rows[0], "url") if rows else None
        if not url:
            raise RuntimeError(f"{sid}: CogView 未返回 URL")
        path = OUT / f"{sid}.jpg"
        save(url, path)
        anchors["shots"][sid] = {"url": url, "file": f"qa/scene-frames/{sid}.jpg",
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "bytes": path.stat().st_size}
        print(f"SCENE_READY {sid} {path.stat().st_size} bytes", flush=True)
    (HERE / "scene_anchors.json").write_text(json.dumps(anchors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SCENE_FRAMES_DONE", flush=True)


if __name__ == "__main__":
    main()
