#!/usr/bin/env python3
"""把用户上传的 JMS 脚本（30 镜 × 6 秒）转成 story.json。

脚本是内容唯一来源：旁白、英文画面提示词、运镜、音效全部原样搬运，
不做"我来润色一下"的改写。改内容请改上传的 txt 与本文件的 PARSER 契约，
而不是手改 story.json——手改会让"成片到底照哪份稿子做的"变成一个谜。

用法：
    python3 production/jmsjung/build_story.py <脚本.txt> [--out production/jmsjung/story.json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# 全片统一画面风格：来自脚本《统一画面风格提示词》，只去掉 Agnes 2.5 不接受的东西。
STYLE_PREFIX = (
    "Cinematic realistic 3D animation, Korean investigative documentary, physically based rendering, "
    "natural skin textures, realistic facial expressions, restrained acting, low-saturation blue-gray palette, "
    "dramatic but believable lighting, shallow depth of field, smooth cinematic camera movement, "
    "16:9 horizontal composition, "
)

CHAPTER_RE = re.compile(r"^## 第(?P<num>[一二三四五六七八九十]+)幕：(?P<title>.*?)（(?P<start>\d{2}:\d{2})—(?P<end>\d{2}:\d{2})）", re.M)
SHOT_RE = re.compile(r"^### 镜头(?P<num>\d+)｜(?P<start>\d{2}:\d{2})—(?P<end>\d{2}:\d{2})", re.M)

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def clock(value: str) -> int:
    minutes, seconds = value.split(":")
    return int(minutes) * 60 + int(seconds)


def field(block: str, label: str) -> str:
    """取 **标签：** 后面那段（可能跨行）。"""
    pattern = re.compile(r"\*\*" + re.escape(label) + r"[：:]\*\*\s*(.+?)(?=\n\*\*|\Z)", re.S)
    match = pattern.search(block)
    return match.group(1).strip() if match else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("script")
    parser.add_argument("--out", default=str(Path(__file__).with_name("story.json")))
    args = parser.parse_args()

    text = Path(args.script).read_text(encoding="utf-8")
    chapters = list(CHAPTER_RE.finditer(text))
    shots_marks = list(SHOT_RE.finditer(text))
    if not chapters or not shots_marks:
        raise SystemExit("脚本里没找到「## 第X幕」或「### 镜头NN」段落")

    shots = []
    for index, mark in enumerate(shots_marks):
        block_end = shots_marks[index + 1].start() if index + 1 < len(shots_marks) else len(text)
        block = text[mark.end():block_end]
        narration = field(block, "中文旁白")
        prompt_match = re.search(r"\*\*English Visual Prompt[:：]?\*\*\s*`(.+?)`", block, re.S)
        prompt = " ".join(prompt_match.group(1).split()) if prompt_match else ""
        camera = field(block, "运镜")
        sfx = field(block, "音效")
        if not narration:
            raise SystemExit(f"镜头 {mark.group('num')} 没有中文旁白")
        if not prompt:
            raise SystemExit(f"镜头 {mark.group('num')} 没有 English Visual Prompt")
        start = clock(mark.group("start"))
        end = clock(mark.group("end"))
        if end - start != 6:
            raise SystemExit(f"镜头 {mark.group('num')} 不是 6 秒（{start}–{end}）")
        shots.append({
            "id": f"S{int(mark.group('num')):02d}",
            "kind": "agnes",
            "start": start,
            "duration": 6,
            "narration": narration,
            "prompt": prompt,
            "purpose": camera,
            "camera": camera,
            "sfx_note": sfx,
            "seed": 20230000 + int(mark.group("num")),
            "seconds": 6,
            "aspect": "16:9",
            "resolution": "720p",
            "frame_rate": 24,
            "cast": [],
        })

    # 章节：按幕的起止时间切分，旁白按镜头原样拼接（后面做 TTS 时按幕分段）。
    chapter_rows = []
    for index, mark in enumerate(chapters):
        start, end = clock(mark.group("start")), clock(mark.group("end"))
        body = text[mark.end(): chapters[index + 1].start() if index + 1 < len(chapters) else len(text)]
        numbers = [int(n) for n in re.findall(r"^### 镜头(\d+)｜", body, re.M)]
        chapter_shots = [s for s in shots if int(s["id"][1:]) in numbers]
        chapter_rows.append({
            "id": f"N{index + 1:02d}",
            "title": mark.group("title").strip(),
            "start": start,
            "duration": end - start,
            "text": "".join(s["narration"] for s in chapter_shots),
            "shots": [s["id"] for s in chapter_shots],
        })

    total = sum(c["duration"] for c in chapter_rows)
    if total != 180:
        raise SystemExit(f"章节总时长 {total} 秒，不是 180 秒")
    if len(shots) != 30:
        raise SystemExit(f"镜头数 {len(shots)}，不是 30")

    story = {
        "title": "JMS郑明析案｜自称救世主的人，为什么最终站上被告席？",
        "target_duration": 180,
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "model": "agnes-video-2.5-flash",
        "style_prefix": STYLE_PREFIX,
        "principles": [
            "不虚构真实对白：录音内容不写成台词，只做证据物件呈现",
            "不展示性侵或暴力画面：只用环境、光影、人物反应暗示",
            "不做真实人物肖像还原：被告只以背影、剪影、手或远景出现",
            "受害者不给可辨识面容：只有背影、侧影、手，或不出现",
            "未证实的指控不当成定罪事实：已判决事实与仍在审理的指控分开表述",
        ],
        "chapters": chapter_rows,
        "shots": shots,
        "source_script": Path(args.script).name,
    }
    Path(args.out).write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"story.json 已写出：{len(shots)} 镜 × 6 秒 = {len(shots) * 6} 秒；{len(chapter_rows)} 章")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
