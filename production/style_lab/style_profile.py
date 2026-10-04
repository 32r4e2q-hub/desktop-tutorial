#!/usr/bin/env python3
"""把实测数值（reference_metrics.json）翻译成人读的风格档案 + 三组英文提示词候选。

输入是 ``analyze.py`` 写出的实测值，输出两份文件：

* ``风格档案.md`` —— 中文：这张参考片到底是什么调子、什么光线、什么运动；
* ``style-candidates.json`` —— 三组 ``STYLE_PREFIX`` / ``NEGATIVE_PROMPT`` 候选，
  对应手册第 3 步里 ``build_story.py`` 的两个常量。三组的差别**只**在画面定位与
  人物政策，实测出来的调色、光线、颗粒词三份共用。

为什么是三组而不是一组：手册里「真实人物只以背影、剪影、手出现」是**内容护栏**，
「超写实 3D」是**画面风格**，两者可以独立组合。把组合摆出来让人挑，比替人决定安全。

用法::

    from style_profile import build_style_profile, write_profile
    profile = build_style_profile(metrics)
    write_profile(out_dir, profile)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------- 色名

COLOR_NAMES = [
    ("near-black", "近黑", (18, 18, 20)),
    ("charcoal grey", "炭灰", (58, 58, 62)),
    ("slate grey", "石板灰", (96, 104, 112)),
    ("cool grey", "冷灰", (150, 154, 158)),
    ("warm grey", "暖灰", (168, 160, 150)),
    ("off-white", "米白", (228, 224, 214)),
    ("steel blue", "钢蓝", (70, 96, 124)),
    ("slate blue", "灰蓝", (94, 116, 138)),
    ("navy blue", "藏蓝", (28, 44, 74)),
    ("midnight blue", "午夜蓝", (18, 28, 48)),
    ("teal", "青绿", (44, 108, 110)),
    ("desaturated cyan", "灰青", (128, 168, 172)),
    ("forest green", "墨绿", (40, 66, 46)),
    ("moss green", "苔绿", (96, 112, 72)),
    ("olive", "橄榄", (116, 112, 66)),
    ("khaki", "卡其", (168, 156, 116)),
    ("ochre", "赭黄", (176, 132, 62)),
    ("sand", "沙色", (206, 186, 152)),
    ("beige", "米色", (216, 202, 178)),
    ("sepia brown", "棕褐", (106, 76, 52)),
    ("chocolate brown", "深棕", (78, 52, 38)),
    ("terracotta", "陶土红", (166, 88, 66)),
    ("brick red", "砖红", (140, 56, 44)),
    ("crimson", "深红", (112, 28, 40)),
    ("dusty rose", "灰玫瑰", (184, 140, 138)),
    ("amber", "琥珀", (214, 158, 58)),
    ("sodium orange", "钠灯橙", (232, 148, 66)),
    ("warm tan", "暖褐", (186, 148, 112)),
    ("dusty violet", "灰紫", (124, 112, 140)),
    ("plum", "暗紫", (84, 56, 84)),
    ("pale blue", "浅蓝", (186, 208, 224)),
    ("cobalt blue", "钴蓝", (24, 78, 178)),
    ("royal blue", "宝蓝", (36, 96, 208)),
    ("emerald green", "翠绿", (24, 168, 96)),
    ("magenta", "品红", (196, 40, 140)),
    ("warm gold", "暖金", (204, 168, 96)),
    ("cold steel", "冷钢", (110, 118, 126)),
    ("ash grey", "浅灰", (196, 198, 200)),
]

SETTING_PLACEHOLDER = "[本片场景：地点 + 年代 + 关键道具，开工时替换]"


def _nearest_color(rgb) -> tuple[str, str]:
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    best, best_d = ("grey", "灰"), 10 ** 9
    for en, zh, (cr, cg, cb) in COLOR_NAMES:
        d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        if d < best_d:
            best, best_d = (en, zh), d
    return best


# --------------------------------------------------------------------------- 判定


def _band(value: float, bands: list[tuple[float, str]], default: str) -> str:
    for limit, label in bands:
        if value < limit:
            return label
    return default


def describe(metrics: dict) -> dict:
    """实测值 → 一组中文判定 + 一组英文提示词片段。"""
    color = metrics.get("color", {})
    texture = metrics.get("texture", {})
    motion = metrics.get("motion", {})
    rhythm = metrics.get("rhythm", {})
    container = metrics.get("container", {})

    luma = float(color.get("mean_luma", 0) or 0)
    contrast = float(color.get("mean_contrast", 0) or 0)
    sat = float(color.get("mean_saturation", 0) or 0)
    warmth = float(color.get("warmth_r_minus_b", 0) or 0)
    sharp = float(texture.get("mean_sharpness", 0) or 0)
    grain = float(texture.get("mean_grain", 0) or 0)
    dof_raw = texture.get("dof_center_over_edge", None)
    dof = float(dof_raw) if dof_raw is not None else None
    bottom = float(texture.get("bottom_band_ratio", 1) or 1)
    motion_mean = float(motion.get("mean_interframe_diff", 0) or 0)
    median_shot = rhythm.get("estimated_median_shot_seconds")

    tone_zh = _band(luma, [(70, "暗调压倒（low-key）"), (105, "整体偏暗"), (145, "中等亮度"), (185, "整体偏亮")], "高调（high-key）")
    contrast_zh = _band(contrast, [(40, "柔和低反差"), (58, "中等反差")], "强反差、硬光")
    sat_zh = _band(sat, [(60, "低饱和、近乎褪色"), (100, "中低饱和"), (140, "中等饱和")], "高饱和")
    warm_zh = _band(warmth, [(-6, "冷调（偏蓝）"), (6, "中性色温")], "暖调（偏橙/黄）")
    sharp_zh = _band(sharp, [(300, "画面偏柔、软焦"), (1200, "常规锐度")], "锐利、边缘清晰")
    grain_zh = _band(grain, [(2.0, "干净、几乎无颗粒"), (3.5, "轻颗粒")], "明显颗粒/强锐化")
    dof_zh = (
        f"判不了：{texture.get('dof_frames_used', 0)} / {texture.get('dof_total_frames', 0)} 帧可用，"
        "其余画面边缘被暗角压黑，方差低不等于虚化"
        if dof is None
        else _band(dof, [(0.9, "边缘比中心更锐：主体常靠边，或素材本身偏平"), (1.1, "全景深，前后都清楚"), (1.35, "轻微浅景深")], "明显浅景深，背景虚化")
    )
    motion_zh = _band(motion_mean, [(0.010, "近乎静止的固定画面"), (0.030, "缓慢漂移"), (0.070, "中等运动")], "明显运动/手持感")
    shot_zh = "未检出足够切点"
    if median_shot:
        shot_zh = _band(median_shot, [(2.0, "快切（<2 秒）"), (4.0, "中速切换（2–4 秒）"), (8.0, "从容（4–8 秒）")], "长镜头（>8 秒）")

    # 英文提示词片段：跟上面每一条中文判定对应
    tone_en = _band(luma, [(70, "low-key exposure with deep crushed shadows"), (105, "dim, moody exposure"), (145, "balanced mid exposure"), (185, "bright exposure")], "bright high-key exposure")
    contrast_en = _band(contrast, [(40, "soft low-contrast grade"), (58, "medium contrast grade")], "punchy high-contrast grade")
    sat_en = _band(sat, [(60, "desaturated, almost drained colour"), (100, "muted, restrained colour"), (140, "moderately saturated colour")], "rich saturated colour")
    warm_en = _band(warmth, [(-6, "cool blue-grey colour temperature"), (6, "neutral colour temperature")], "warm amber-tungsten colour temperature")
    sharp_en = _band(sharp, [(300, "soft, gently diffused optics"), (1200, "clean crisp optics")], "razor-sharp crisp optics")
    grain_en = _band(grain, [(2.0, "clean digital rendering with only faint grain"), (3.5, "subtle fine film grain")], "visible fine 35mm film grain")
    dof_en = (
        "natural cinematic depth with a softly falling-off background"
        if dof is None
        else _band(dof, [(0.9, "flat even focus across the frame"), (1.1, "deep focus with everything readable"), (1.35, "mild shallow focus")], "shallow depth of field with the background softly defocused")
    )
    motion_en = _band(motion_mean, [(0.010, "almost locked-off static frames"), (0.030, "slow drifting camera"), (0.070, "steady moderate camera movement")], "handheld, energetic camera movement")

    palette = color.get("palette", [])[:3]
    palette_en = ", ".join(_nearest_color(p["rgb"])[0] for p in palette) or "muted neutral tones"
    palette_zh = "、".join(
        f"{_nearest_color(p['rgb'])[1]} {p['hex']}（{p['share'] * 100:.0f}%）" for p in palette
    ) or "（未取到主色）"

    return {
        "zh": {
            "影调": tone_zh, "反差": contrast_zh, "饱和": sat_zh, "色温": warm_zh,
            "锐度": sharp_zh, "颗粒": grain_zh, "景深": dof_zh, "运动": motion_zh, "节奏": shot_zh,
            "主色": palette_zh,
            "底部字幕带": "画面底部疑似压了字幕条（底部边缘密度明显高于全画面）" if bottom > 1.6 else "未发现明显的底部字幕带",
        },
        "en": {
            "tone": tone_en, "contrast": contrast_en, "saturation": sat_en, "temperature": warm_en,
            "sharpness": sharp_en, "grain": grain_en, "dof": dof_en, "motion": motion_en,
            "palette": palette_en,
        },
        "numbers": {
            "luma": luma, "contrast": contrast, "saturation": sat, "warmth": warmth,
            "sharpness": sharp, "grain": grain, "dof": dof, "motion": motion_mean,
            "median_shot": median_shot,
            "fps": container.get("fps"),
            "orientation": container.get("orientation"),
        },
    }


# --------------------------------------------------------------------------- 候选


def _prefix(words: dict, look: str, people: str) -> str:
    return (
        f"{look}, {SETTING_PLACEHOLDER}: "
        f"{words['palette']}, {words['tone']}, {words['temperature']}, {words['contrast']}, "
        f"{words['sharpness']}, {words['grain']}, {words['dof']}, {words['motion']}; "
        f"horizontal 16:9 cinematic composition, one single continuous smooth slow camera move per shot "
        f"exactly as directed; {people} "
        f"absolutely no readable text, letters, numbers, logos, license plates or brand marks anywhere "
        f"inside the frame; no gore, no blood, no corpse, no violence, no nudity. "
    )


BASE_NEGATIVE = (
    "readable text, letters, numbers, words, signage writing, invented headlines, logos, brand marks, "
    "watermark, subtitles, on-screen caption, blood, gore, wound, corpse, body bag, body parts, autopsy, "
    "violence, assault, strangling, weapon attack, gun, firearm, nudity, erotic content, horror monster, "
    "ghost, jump scare, distorted anatomy, deformed hands, extra fingers, extra limbs, duplicated people, "
    "changing face, morphing objects, teleportation, jitter, flicker, whip pan, fast zoom, jump cut, "
    "split screen, collage"
)


def build_candidates(words: dict) -> list[dict]:
    en = words["en"]
    return [
        {
            "id": "photoreal_silhouette",
            "label": "超写实 3D· 人物只给背影/剪影/手部",
            "摘要": (
                "画面按参考片的调子做成实拍级 3D CGI：材质、光线、镜头运动都往实拍靠，"
                "但沿用手册护栏——真实人物不出清晰正脸，全片常驻「AI动画情景重现 · 非新闻影像」角标。"
                "推荐度最高：既吃满参考片的质感，又不碰内容红线。"
            ),
            "风险": "无新增风险，与 production/gilgo 的护栏一致。",
            "style_prefix": _prefix(
                en,
                "Photorealistic 3D CGI cinematic recreation that reads like live-action photography, "
                "with physically plausible materials, global illumination and true-to-life scale",
                "every character is shown only from behind, in silhouette, or as hands and props - "
                "never a clear frontal face; no likeness of any real person; ",
            ),
            "negative_prompt": BASE_NEGATIVE + ", flat 2D illustration, hand-drawn cel shading, comic-book ink lines, graphic-novel texture, watercolour paper texture",
        },
        {
            "id": "photoreal_faces",
            "label": "超写实 3D· 允许清晰人脸",
            "摘要": (
                "同样按参考片做实拍级 3D，但允许画面出现清晰的普通人脸（仍然不是任何真实人物的肖像）。"
                "人物表情、眼神能大幅提升叙事密度，代价是畸变与「像真人新闻影像」的观感风险一起上升。"
            ),
            "风险": (
                "**违反手册护栏**（PRINCIPLES：真实人物只以背影、剪影、手出现）。若采用，"
                "必须改写 build_story.py 的 PRINCIPLES，并把「AI动画情景重现 · 非新闻影像」角标加粗常驻；"
                "涉受害者的镜头仍不出人像。"
            ),
            "style_prefix": _prefix(
                en,
                "Photorealistic 3D CGI cinematic recreation that reads like live-action photography, "
                "with physically plausible skin, materials, global illumination and true-to-life scale",
                "ordinary non-celebrity human faces are allowed when the story needs a face, but never a "
                "likeness of any real public figure or victim; ",
            ),
            "negative_prompt": BASE_NEGATIVE + ", flat 2D illustration, hand-drawn cel shading, comic-book ink lines, graphic-novel texture",
        },
        {
            "id": "cinematic_3d",
            "label": "写实 3D 动画电影质感",
            "摘要": (
                "偏 3D 动画长片：体积光、干净的材质、轻微风格化。比纯写实更好控——"
                "Agnes 生成人脸和手时畸变概率明显更低，复审重做的镜头数通常最少，"
                "代价是离参考片的「实拍感」差一档。"
            ),
            "风险": "无新增风险；与参考片的写实度有落差，需要你确认接受。",
            "style_prefix": _prefix(
                en,
                "Stylized-realistic 3D animated feature look with soft volumetric light, clean physically "
                "based materials and gentle stylization, rendered like a high-end 3D animated film",
                "every character is shown only from behind, in silhouette, or as hands and props - "
                "never a clear frontal face; no likeness of any real person; ",
            ),
            "negative_prompt": BASE_NEGATIVE + ", flat 2D illustration, hand-drawn cel shading, comic-book ink lines, graphic-novel texture, uncanny photoreal skin, waxy plastic skin",
        },
    ]


# --------------------------------------------------------------------------- 档案正文


def render_markdown(metrics: dict, words: dict, candidates: list[dict]) -> str:
    src = metrics.get("source", {})
    cont = metrics.get("container", {})
    samp = metrics.get("sampling", {})
    rhythm = metrics.get("rhythm", {})
    zh = words["zh"]
    num = words["numbers"]
    mins = cont.get("duration", 0) / 60.0

    lines = [
        "# 参考视频风格档案",
        "",
        f"源文件 `{src.get('file')}`（{src.get('mb')} MB）· {cont.get('width')}×{cont.get('height')} · "
        f"{cont.get('fps')} fps · {mins:.1f} 分钟 · 分析于 {src.get('analyzed_at')}（{src.get('ffmpeg')}）。",
        "",
        "## 实际读取范围",
        "",
        f"- 抽帧 **{samp.get('sampled_frames')}** 张，均匀覆盖整段（避开首尾各 0.5 %）；不是逐帧审查。",
        f"- 硬切粗检测：阈值 {samp.get('cut_detection_threshold')}，解码宽度 {samp.get('cut_scale_width')}px，"
        f"估算 **{rhythm.get('estimated_cuts')}** 次显著画面切换"
        + (f"，中位间隔 {rhythm.get('estimated_median_shot_seconds')} 秒。" if rhythm.get("estimated_median_shot_seconds") else "。")
        + "淡入淡出与机内运动可能漏检或误检，此值仅供节奏参考。",
        f"- 运动幅度：{samp.get('motion_pairs')} 组相隔 0.4 秒的帧对，算灰度平均绝对差。",
        "- 音轨只探测是否存在，**不克隆、不迁移**；参考片的画面一帧都不会进新片。",
        "- 仅从成片无法确认原作者用了哪款生成或剪辑软件，不把推测写成结论。",
    ]
    if rhythm.get("partial"):
        lines.append("- ⚠️ 切点检测超过 15 分钟上限被中断，上面的切点数是**部分结果**。")
    lines += [
        "",
        "## 量出来的画面特征",
        "",
        "| 维度 | 实测 | 判定 |",
        "|---|---|---|",
        f"| 影调 | 平均亮度 {num['luma']:.0f}/255 | {zh['影调']} |",
        f"| 反差 | 帧内标准差 {num['contrast']:.0f} | {zh['反差']} |",
        f"| 饱和 | HSV 饱和度 {num['saturation']:.0f}/255 | {zh['饱和']} |",
        f"| 色温 | R−B {num['warmth']:+.0f} | {zh['色温']} |",
        f"| 锐度 | 拉普拉斯方差 {num['sharpness']:.0f} | {zh['锐度']} |",
        f"| 颗粒 | 高频残差 {num['grain']:.2f} | {zh['颗粒']} |",
        f"| 景深 | 中心/边缘锐度 {('%.2f' % num['dof']) if num['dof'] is not None else '—'} | {zh['景深']} |",
        f"| 运动 | 帧间差 {num['motion']:.3f} | {zh['运动']} |",
        f"| 节奏 | 中位镜头 {num['median_shot'] if num['median_shot'] else '—'} 秒 | {zh['节奏']} |",
        f"| 主色 | — | {zh['主色']} |",
        "",
        f"底部字幕带：{zh['底部字幕带']}。",
        "",
        "## 迁移到新片（只迁风格，不迁素材）",
        "",
        "- 上面每一条判定都已经在 `style-candidates.json` 里翻译成英文提示词片段，"
        "三份候选共用同一套调色/光线/颗粒词，差别只在画面定位与人物政策；",
        "- 中文姓名、日期、字幕一律后期添加，不交给视频模型拼写（手册第 1 步）；",
        "- 真实人物只以背影、剪影、手出现，受害者不出人像，不展示遗体与侵害过程；",
        "- 全片常驻「AI动画情景重现 · 非新闻影像」角标，法庭/取证/搜查镜头换成更具体的标签；",
        "- 参考片的**剪辑节奏只作参考**：新片仍按手册 45 镜 × 4 秒网格与 `clause_times.py --check-cuts` 走。",
        "",
        "## 三组 STYLE_PREFIX 候选",
        "",
    ]
    for i, cand in enumerate(candidates, 1):
        lines += [
            f"### {i}. {cand['label']}（`{cand['id']}`）",
            "",
            cand["摘要"],
            "",
            f"风险：{cand['风险']}",
            "",
            "```",
            cand["style_prefix"],
            "```",
            "",
        ]
    lines += [
        "---",
        "",
        "选一组写进 `production/<slug>/build_story.py` 的 `STYLE_PREFIX`（`NEGATIVE_PROMPT` 一起换），",
        "并把 `" + SETTING_PLACEHOLDER + "` 换成本片的场景描述。",
        "",
    ]
    return "\n".join(lines)


def build_style_profile(metrics: dict) -> dict:
    words = describe(metrics)
    candidates = build_candidates(words)
    return {
        "words": words,
        "candidates": candidates,
        "markdown": render_markdown(metrics, words, candidates),
    }


def write_profile(out_dir: Path, profile: dict) -> dict:
    out_dir = Path(out_dir)
    (out_dir / "风格档案.md").write_text(profile["markdown"], encoding="utf-8")
    payload = {
        "placeholders": {"setting": SETTING_PLACEHOLDER},
        "words": profile["words"],
        "candidates": [
            {
                "id": c["id"],
                "label": c["label"],
                "摘要": c["摘要"],
                "风险": c["风险"],
                "style_prefix": c["style_prefix"],
                "negative_prompt": c["negative_prompt"],
            }
            for c in profile["candidates"]
        ],
    }
    (out_dir / "style-candidates.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def load_profile(out_dir: Path) -> Optional[dict]:
    path = Path(out_dir) / "style-candidates.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="从 reference_metrics.json 生成风格档案")
    ap.add_argument("metrics", help="reference_metrics.json 路径")
    args = ap.parse_args()
    m = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    prof = build_style_profile(m)
    write_profile(Path(args.metrics).parent, prof)
    print(prof["markdown"])
