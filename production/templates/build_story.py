#!/usr/bin/env python3
"""《__TITLE__》—— 唯一内容源：解说词、30 镜分镜、参考图、钩子/注释、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
流水线出处是 production/shanghai_freezer_case/build_story.py —— 一部出片、换声、重渲都跑完的成片）。

用法::

    python3 production/__SLUG__/build_story.py            # 写 story.json + screenplay.md + 抖音脚本.md + 抖音发布文案.md

写法规则（都是前作踩出来的，别省）：

- 30 镜 × 6 秒规划网格，时间轴由本文件的 ROWS 顺序自动累加，合计必须正好 180 秒（结尾校验会卡）；
  时长只能是 2–13 秒的整数。每镜一句解说，TTS 一镜一条，字幕与音频逐字一致。
- 数字一律写成中文读法（"二零一六年十月十七日""年仅三十二岁"），TTS 和字幕才一致。
- 不写血腥/侵害过程的具体描写（TTS 审核会拒，红线也不允许）。
- STYLE 在每个提示词最前、NEGATIVE 在最后，generate.py 自动拼接；角色锚点原文插入对应镜头。
- 提示词先钉死"唯一场景"，再明确排除别的场景，最后加运镜句；否定词对视频模型基本没用，
  想去掉某样东西就别给它出现的空间。
- 参考图：每镜 __ 张（Agnes 2.5 Flash reference 模式 1–5 张），按 reference/approvals.json 登记；
  没有批准参考图，--validate 直接报错（这是设计：先开造型/场景参考，再烧视频额度）。
- 钩子 H1..Hn：白字黑边、居中偏下（MarginV=275）、每条严格 2 秒；金色注释 MarginV=200，只补可核实事实。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "__TITLE__"
BRANCH = "__BRANCH__"
FILM_NAME = "__FILM__"

# 全片统一的画面风格前缀（第 1 位拼接）。TODO：把「世界描述」换成本片的地点/年代/道具；
# 后半句（人物只给虚构演员形象、无可读文字、连续运动、16:9、底部字幕安全区）是流水线规则，别删。
# 注意：style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 30 镜全部重做。
STYLE = (
    "【STYLE】TODO：画面风格总述（渲染质感、年代、地点、色调、字幕安全区、连续运动、人物均为虚构演员式形象，"
    "不还原任何真实人物肖像）。"
)
NEGATIVE = (
    "【NEGATIVE】卡通，Q版，动漫，夸张表情，过度饱和，文字，水印，字幕，可读文字，真实姓名，真实肖像，"
    "血腥，伤口，遗体，尸体，绑缚，窒息过程，性相关内容，暴力过程，武器，畸形手指，多余肢体，"
    "人物面部崩坏，低清晰度，画面闪烁，风格突变，竖屏构图，黑边，静态图加推拉，幻灯片，拼版，伪招牌。"
)

# 角色锚点：generate.py 会把锚点原文拼到对应镜头的提示词中。TODO：按本片实际角色增删。
# 命名建议：ROLE / ROLE_BACK / ROLE_SIDE…… 每个角色一个 seed（character_seeds）。
CHARACTERS: dict[str, str] = {
    # "ROLE_BACK": "【C01锚点】TODO：背影/侧脸锚点，虚构演员式形象，不还原真实人物",
}
CHARACTER_SEEDS: dict[str, int] = {
    # "ROLE_BACK": 20260001,
}

# duration, narration, visual beat, design references, character roles, camera, sound, color
# TODO：把下面 30 行改成本片内容。reference ids 对应 reference/approvals.json 里 approved 的条目；
# characters[] 里的角色名必须在 CHARACTERS 里登记；duration 为整数秒、2–13、合计必须正好 180。
ROWS = [
__ROWS__
]

# 章节边界（start 秒, end 秒, 章名）。TODO：按解说节奏重切；章内镜头自动归章。
CHAPTER_BOUNDS = [
    (0, 30, "TODO 第一章"),
    (30, 60, "TODO 第二章"),
    (60, 90, "TODO 第三章"),
    (90, 120, "TODO 第四章"),
    (120, 150, "TODO 第五章"),
    (150, 180, "TODO 第六章"),
]

SEED_OVERRIDES: dict[int, int] = {
    # 个别镜头对种子重新抽样时登记：3: 20261020,
}

# 钩子大字（白字黑边、居中偏下 MarginV=275、每条严格 2 秒）。TODO：按本片填写；没有钩子就留 []。
HOOKS = [
    # {"id": "H1", "start": 0.0, "end": 2.0, "text": "TODO 八字以内", "style": "big_white_black_outline"},
]

# 金色注释（MarginV=200，只补可核实事实/时间线/术语）。TODO：按本片填写；没有注释就留 []。
EXPLAINERS = [
    # {"start": 2.1, "end": 4.8, "text": "TODO 可核实事实一句话", "color": "gold"},
]

HIGHLIGHT_PHRASES = [
    # "TODO 字幕金色高亮的关键词",
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> dict:
    cursor = 0.0
    shots = []
    for index, row in enumerate(ROWS, 1):
        duration, narration, visual, refs, roles, camera, sound, grade = row
        sid = f"S{index:02d}"
        start = cursor
        cursor += duration
        chapter = next(
            f"N{i:02d}" for i, (lo, hi, _) in enumerate(CHAPTER_BOUNDS, 1)
            if lo <= start < hi
        )
        prompt = (
            f"{visual} 真实连续运动贯穿全镜，镜头运镜：{camera}；构图保持16:9横屏，"
            "主体置于三分线，底部字幕安全区保持低干扰；不要任何文字、标签、时间戳或招牌。"
        )
        shots.append({
            "id": sid, "kind": "agnes", "start": start, "duration": duration,
            "seconds": duration, "aspect": "16:9", "source_size": "720P",
            "narration_id": chapter, "narration": narration,
            "prompt": prompt, "purpose": visual, "characters": roles,
            "seed": SEED_OVERRIDES.get(index, 20260101 + index),
            "camera": camera, "sound_design": sound,
            "color_grade": grade, "reference_ids": refs,
            "transition_in": "按本片色调方案执行的短促电影转场，不改变事实内容",
            "transition_out": "以悬念句与短暂停顿收束，环境保持微动",
        })
    if len(shots) != 30 or abs(cursor - 180) > 1e-6:
        raise AssertionError(f"Expected 30 shots / 180s, got {len(shots)} / {cursor}s")

    chapters = []
    for i, (start, end, name) in enumerate(CHAPTER_BOUNDS, 1):
        text = "".join(s["narration"] for s in shots if start <= s["start"] < end)
        chapters.append({"id": f"N{i:02d}", "title": name, "start": start,
                         "duration": end - start, "text": text})

    approvals_path = HERE / "reference" / "approvals.json"
    approvals = json.loads(approvals_path.read_text(encoding="utf-8")) if approvals_path.exists() else {"assets": {}}
    ref_images = []
    for asset_id, record in approvals.get("assets", {}).items():
        path = HERE / record.get("file", "")
        if record.get("status") == "approved" and path.is_file() and digest(path) == record.get("sha256"):
            ref_images.append({"id": asset_id, **record})
    revision_path = HERE / "reference" / "revision.txt"
    revision = revision_path.read_text(encoding="utf-8").strip() if revision_path.exists() else ""
    voice_path = HERE / "audio" / "voice.json"
    voice = json.loads(voice_path.read_text(encoding="utf-8")) if voice_path.exists() else {}
    voice_id = voice.get("voice_id") or "pending_voice_selection"

    presentation = {
        "onscreen_label": "AI动画情景重现 · 非真实影像",
        "highlight_phrases": HIGHLIGHT_PHRASES,
        "hooks": HOOKS,
        "explainers": EXPLAINERS,
        "end_title": "TODO 案名",
        "end_subtitle": "TODO 年份 · 一句话",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "TODO 封面大字",
        "cover_concept": "TODO 封面只用本片已生成视频截图；禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "TODO 抖音标题",
        "hashtags": ["#真实案件", "#案件解说", "#悬疑", "#普法"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "TODO：核对状态（公开资料口径 + 未实时复核项如实标注）",
        "as_of": "TODO 日期",
        "legal_note": "TODO 判决/进展口径；罪犯已被执行死刑则禁止“服刑中”类表述。",
        "sources": [
            # {"publisher": "TODO", "date": "TODO", "url": "TODO", "supports": "TODO 支撑哪一句解说"},
        ],
        "editorial_cautions": [
            "TODO：媒体口径 vs 日历口径的数字差异处理说明",
            "TODO：受害者仅用角色称谓；不使用真实肖像（AI 形象仅示意）",
            "TODO：施害过程不展示",
        ],
    }

    project = {
        "title": TITLE,
        "film_name": FILM_NAME,
        "target_duration": 180, "width": 1920, "height": 1080, "fps": 24,
        "model": "agnes-video-2.5-flash", "source_size": "720P", "branch": BRANCH,
        "style_prefix": STYLE, "negative_prompt": NEGATIVE, "style_rumor_prefix": STYLE,
        "characters": CHARACTERS, "character_seeds": CHARACTER_SEEDS,
        "narration_spec": {
            "voice_id": voice_id,
            "description": voice.get("description", "TODO 试音选定后的音色描述"),
            "language": "zh-CN", "target_characters_per_second": 4.2,
            "alignment": "一镜一句，一镜一条TTS与一条字幕；只在确有必要时加速，不慢放",
        },
        "chapters": chapters, "shots": shots,
        "reference_images": ref_images,
        "reference_revision": revision,
        "reference_designs": {
            "characters": [],
            "scenes": [],
            "props": [],
            "note": "TODO：参考图清单与审核说明；未批准任何参考图则 reference_images 为空，--validate 会报错（设计如此）。",
        },
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期高质量放大到1080P。",
            "所有Agnes提示词由generate.py自动组合：STYLE在最前，角色锚点逐字插入，NEGATIVE在末尾；文字全部禁止AI自绘，由后期烧录。",
            "镜头每5条抽查一次人物脸和服装漂移；出现漂移则以同一批准参考图只重生成对应镜头。",
            "全片无BGM；旁白与字幕逐句锁定，音效/环境声只做轻量辅助，不盖住解说。",
        ],
    }
    (HERE / "story.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [
        f"# {TITLE}", "",
        "抖音横屏｜1920×1080｜16:9｜24fps｜180秒｜30个Agnes Video 2.5 Flash动画片段｜无BGM。",
        "", "| 镜头 / 时间 | 旁白 | 画面与运镜 | 参考图 | 音效/环境声备注 |", "|---|---|---|---|---|",
    ]
    for shot, row in zip(shots, ROWS):
        _, narration, visual, refs, roles, camera, sound, grade = row
        end = shot["start"] + shot["duration"]
        ts = lambda sec: f"{int(sec) // 60:02d}:{int(sec) % 60:02d}"
        rows.append(f"| {shot['id']} / {ts(shot['start'])}–{ts(end)} | {narration} | {visual}（{camera}；{grade}） | {refs} + {','.join(roles) or '无角色'} | {sound} |")
    screenplay = "\n".join(rows) + "\n"
    (HERE / "screenplay.md").write_text(screenplay, encoding="utf-8")
    (HERE / "抖音脚本.md").write_text(screenplay, encoding="utf-8")

    publish = "\n".join([
        f"# {presentation['publish_title']}", "",
        "## 抖音标题", "", presentation["publish_title"], "",
        "## 简短介绍", "",
        "TODO：两三句话讲清案件与判决口径，末尾注明“AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md”。",
        "", "## 提问读者一句话", "", "TODO：一句把读者拽进评论区的提问。", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()
