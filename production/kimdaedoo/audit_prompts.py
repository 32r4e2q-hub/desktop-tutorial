#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金大斗案 · 生成前的严格提示词闸门（不花一分钱、不调用 Agnes）。

为什么单独开这一道闸：
Agnes 免费池一次生成要排队几十分钟到几小时，重做一条的成本远高于在这里跑 0.1 秒。
所以把“会让镜头报废”的东西全部提前拦下：

* 人物 token 是否逐字节出现（交给 production/face_cast.py 的静态闸门）
* 一镜是不是只有一个场景、一个连续运镜（6 秒做不了蒙太奇）
* 有没有把血、遗体、性侵、武器、儿童危险写进画面
* 有没有现代设备、可读文字、真实人物姓名
* 模型/分辨率/秒数/模式是否踩中 agnes-video-2.5 的参数红线
* 180 秒旁白是否真的落得进去（按 4.2–5.2 字/秒估算）

用法：
    python3 production/kimdaedoo/audit_prompts.py
退出码：0 = 通过（可有 warning）；1 = 有 error，禁止开始生成。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "production"))
sys.path.insert(0, str(HERE))

import agnes_video as agnes  # noqa: E402
from model_policy import MODEL, SIZE_TIER, SUPPORTED_MODES, SUPPORTED_SIZES  # noqa: E402

STORY = HERE / "story.json"
CAST = HERE / "cast.json"
REPORT = HERE / "delivery" / "prompt-audit.json"

BANNED_VIOLENCE = (
    "blood", "bleeding", "wound", "wounded", "corpse", "dead body", "dead bodies",
    "gore", "gory", "murder", "killing", "rape", "raped", "sexual assault",
    "naked", "nude", "torture", "dismember", "behead", "child abuse", "abuse",
)
BANNED_MODERN = (
    "computer", "smartphone", "cell phone", "mobile phone", "digital screen", "monitor",
    "cctv", "surveillance camera", "led", "neon", "internet", "drone", "modern car",
    "modern building", "electric sign", "hologram",
)
BANNED_REAL_PERSON = ("kim dae-doo", "kim daedoo", "金大斗", "김대두")
BANNED_TEXT = ("readable text", "readable letter", "readable headline", "readable sign",
               "watermark", "logo", "caption", "subtitle", "on-screen text")
MULTI_SCENE = ("montage", "cut to", "hard cut", "jump cut", "meanwhile", "dissolve to")
CAMERA_WORDS = ("push-in", "pull-back", "tracking", "dolly", "crane", "pan", "drift",
                "tilt", "lateral", "orbit", "handheld", "zoom", "focus pull")

# 这些是“允许的否定句”，先删掉再查禁用词；否则 “no blood” 会把每条都判红。
SAFE_PHRASES = (
    "no bodies, no blood", "no bodies", "no blood", "no injuries", "no wounds",
    "no weapons", "no weapon", "no gore", "no violence", "no struggle",
    "no execution shown", "no readable text", "no readable letters",
    "no readable headlines", "no text", "no cameras", "no modern buildings",
    "no modern technology", "no modern vehicles", "no identifiable real person",
    "no identifiable faces", "no people", "no faces", "no dialogue",
    "after a violent crime", "after a burglary", "violent crime",
    "no on-screen text", "no sensational images", "no dramatic villain lighting",
)


def clean(text: str) -> str:
    out = text.lower()
    for phrase in sorted(SAFE_PHRASES, key=len, reverse=True):
        out = out.replace(phrase, "")
    return out


def payload_for(shot: dict) -> dict:
    """与 generate.py::full_payload 同形状，避免闸门和实际请求漂移。"""
    seconds = max(4, min(12, int(round(shot["seconds"]))))
    return {
        "model": MODEL,
        "prompt": "AUDIT",
        "seconds": str(seconds),
        "size": SIZE_TIER,
        "aspect_ratio": shot["aspect"],
        "mode": "text",
        "n": 1,
        "seed": shot["seed"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="金大斗案提示词闸门")
    parser.add_argument("--story", default=str(STORY))
    parser.add_argument("--cast", default=str(CAST))
    parser.add_argument("--report", default=str(REPORT))
    args = parser.parse_args(argv)
    story_path, cast_path, report_path = Path(args.story), Path(args.cast), Path(args.report)

    errors: list[str] = []
    warnings: list[str] = []
    story = json.loads(story_path.read_text(encoding="utf-8"))
    cast = json.loads(cast_path.read_text(encoding="utf-8"))
    shots = story.get("shots") or []

    if len(shots) != 30:
        errors.append(f"镜头数 {len(shots)}，必须是 30")
    if story.get("target_duration") != 180:
        errors.append("target_duration 不是 180")
    if sum(s.get("duration", 0) for s in shots) != 180:
        errors.append("30 镜时长相加不是 180 秒")
    if sum(c.get("duration", 0) for c in story.get("chapters") or []) != 180:
        errors.append("章节时长相加不是 180 秒")

    ids = [s.get("id") for s in shots]
    if ids != [f"S{i:02d}" for i in range(1, 31)]:
        errors.append("镜头 ID 必须是 S01…S30 连续")

    cast_shots = cast.get("shots") or {}
    character_faces = {c["id"]: c.get("face", "") for c in cast.get("characters") or []}

    total_chars = 0
    for index, shot in enumerate(shots):
        sid = shot.get("id", f"#{index}")
        prompt = shot.get("prompt") or ""
        narration = shot.get("narration") or ""
        cast_ids = [str(x) for x in shot.get("cast") or []]

        if shot.get("kind") != "agnes":
            errors.append(f"{sid}: kind 不是 agnes")
        if shot.get("start") != index * 6 or shot.get("duration") != 6:
            errors.append(f"{sid}: 时间轴不是 6 秒网格")
        if shot.get("seconds") != 6:
            errors.append(f"{sid}: seconds 不是 6")
        if shot.get("aspect") != "16:9":
            errors.append(f"{sid}: aspect 不是 16:9")

        # ---- 提示词长度与结构 ----
        if not 200 <= len(prompt) <= 1000:
            errors.append(f"{sid}: 提示词 {len(prompt)} 字符，超出 200–1000 的生产区间")
        if "{{" in prompt or "}}" in prompt:
            errors.append(f"{sid}: 还有未替换的占位符")
        if not re.search(r"\b(1975|1976)\b", prompt):
            errors.append(f"{sid}: 没有写明年份（1975/1976）")
        if not any(word in prompt.lower() for word in CAMERA_WORDS):
            errors.append(f"{sid}: 没有明确运镜（push-in / tracking / dolly / crane 等）")

        # ---- 内容红线 ----
        stripped = clean(prompt)
        for word in BANNED_VIOLENCE:
            if word in stripped:
                errors.append(f"{sid}: 画面提示词出现暴力/血腥词 {word!r}（即使是否定句也请换写法）")
        for word in BANNED_MODERN:
            pattern = r"\b" + re.escape(word) + r"\b" if " " not in word else re.escape(word)
            if re.search(pattern, stripped):
                errors.append(f"{sid}: 画面提示词出现现代设备 {word!r}")
        for word in BANNED_TEXT:
            if word in stripped:
                errors.append(f"{sid}: 画面提示词可能生成可读文字 {word!r}")
        for word in BANNED_REAL_PERSON:
            if word in prompt.lower():
                errors.append(f"{sid}: 不要在画面提示词里写真实姓名（{word}）")
        for word in MULTI_SCENE:
            if word in stripped:
                errors.append(f"{sid}: 一镜里出现 {word!r}，6 秒做不了多场景/跳切")

        # ---- 露脸 token ----
        if cast_ids:
            if cast_shots.get(sid) != cast_ids:
                errors.append(f"{sid}: story.cast 与 cast.json.shots 不一致")
            for cid in cast_ids:
                face = character_faces.get(cid, "")
                if face and face not in prompt:
                    errors.append(f"{sid}: 缺角色 {cid} 的 face token")
            for cid in character_faces:
                if cid not in cast_ids and character_faces[cid] and character_faces[cid] in prompt:
                    errors.append(f"{sid}: 带了未声明的角色 {cid} 的 face token")
        elif cast_shots.get(sid):
            errors.append(f"{sid}: cast.json 声明了露脸，但 story.cast 是空的")

        # ---- 旁白长度 ----
        chars = len(re.sub(r"[，。、；：“”《》（）\s]", "", narration))
        total_chars += chars
        if not 14 <= chars <= 34:
            errors.append(f"{sid}: 旁白 {chars} 字，超出 14–34 字（6 秒镜头的安全区间）")

        # ---- payload 红线 ----
        payload = payload_for(shot)
        if payload["model"] != "agnes-video-2.5-flash":
            errors.append(f"{sid}: 模型不是 agnes-video-2.5-flash")
        if payload["size"] != "720P":
            errors.append(f"{sid}: 免费档只认 720P，现在是 {payload['size']}")
        if payload["seconds"] != "6":
            errors.append(f"{sid}: seconds 必须是字符串 \"6\"")
        if payload["mode"] not in SUPPORTED_MODES:
            errors.append(f"{sid}: mode 不在 {SUPPORTED_MODES}")
        if payload["size"] not in SUPPORTED_SIZES:
            errors.append(f"{sid}: size 不在 {SUPPORTED_SIZES}")
        for banned in ("width", "height", "fps", "num_frames", "frame_rate", "duration",
                       "resolution", "negative_prompt", "quality", "num_inference_steps"):
            if banned in payload:
                errors.append(f"{sid}: payload 里不应出现 {banned}")

    # ---- 全片级检查 ----
    # 2026-10-22 CI 实测：Yunjian 在 +0% 约 3.49 字/秒，每镜 6 秒窗口放不下 20 字以上的句子
    # （原稿 666 字、平均 22 字/镜，S01 念了 8.59 秒）。旁白按每镜 ≤22 字重写后共 556 字，
    # 约 185 字/分钟——这是慢节奏悬疑旁白的正常密度，不是漏写。
    if not 500 <= total_chars <= 620:
        errors.append(f"180 秒版旁白共 {total_chars} 字，应在 500–620 字（每镜 ≤22 字）")
    joined = "".join(s.get("narration", "") for s in shots)
    for must in ("55天", "17", "9起", "3人重伤", "1975", "1976", "27岁", "牛仔裤"):
        if must not in joined:
            errors.append(f"旁白缺少关键事实/关键词：{must}")
    if "出狱" not in joined and "释放" in joined:
        errors.append("不要写“已释放/已出狱”这类可能被误读为现状的表述")

    # 非露脸镜头的 seed 必须唯一；露脸镜头用角色 seed，允许重复。
    plain_seeds = [s["seed"] for s in shots if not s.get("cast")]
    if len(plain_seeds) != len(set(plain_seeds)):
        errors.append("非露脸镜头的 seed 有重复")
    for s in shots:
        if len(s.get("cast") or []) > 1:
            warnings.append(f"{s['id']}: 一镜登记了多个角色，模型可能撞脸，建议改成单人特写")

    report = {
        "gate": "kimdaedoo-prompt-audit",
        "status": "PASS" if not errors else "FAIL",
        "model": MODEL,
        "size": SIZE_TIER,
        "shots": len(shots),
        "narration_chars": total_chars,
        "errors": errors,
        "warnings": warnings,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if errors:
        print(f"提示词闸门：FAIL（{len(errors)} 个 error）")
        for item in errors:
            print("  ×", item)
        for item in warnings:
            print("  !", item)
        print(f"报告：{report_path}")
        return 1
    print(f"提示词闸门：PASS（{len(shots)} 镜 · {total_chars} 字 · {len(warnings)} 个 warning）")
    for item in warnings:
        print("  !", item)
    print(f"报告：{report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
