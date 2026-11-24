#!/usr/bin/env python3
"""新题目开工脚手架（上海冰柜藏尸案模式）：以《上海冰柜藏尸案》为参考实现，开出一个可以独立编辑的项目目录。

用法::

    python3 production/new_topic.py --slug jinan1998 \\
        --title "济南大明湖案：……" \\
        --branch arena/xxxx-desktop-tutorial

它做的事（不改参考项目一个字节）：

1. **复制**流水线引擎到 ``production/<slug>/``：
   ``generate``（Agnes 2.5 Flash reference 模式：断点续跑 / 节流 / 按 SHA-256 复用 / --validate 闸门）、
   ``qc``（源片与成片技术 QC）、``preflight``（开工前硬闸）、``throttle`` / ``narration_fit`` /
   ``build_audio_manifest``（配音收据）/ ``build_sfx``（逐镜音效与全片无 BGM 闸门）；
2. **替换**副本里所有 ``production/shanghai_freezer_case``、``work/shanghai_freezer_case``、
   出片分支名、片名、成片名、交付物文件名（``上海冰柜藏尸案_Cover.jpg`` 之类）；
3. 从 ``production/templates/`` **渲染**两份"内容与引擎分离"的文件：
   ``build_story.py``（唯一内容源：解说词 / 30 镜 / 钩子 / 金色注释 / 发布文案，全是 TODO）、
   ``render.py``（渲染引擎；本片专属的只有结尾渐黑表 ``END_FADES`` 属于本片）；
4. **生成**骨架：``story.json``（30 镜 × 6 秒、6 章 × 30 秒的时间轴已算好）、``screenplay.md``、
   ``audio/manifest.json``、``reference/approvals.json``（空）、``README.md``（待办清单），
   以及 ``workflows/`` 下三份工作流（合一 ``GEN_REQUEST`` 生成/出片、逐字听检、技术 QC；
   Release 上传用仓库里通用的 ``release-upload.yml``）。

生成的项目**故意过不了** ``generate.py --validate``：解说词、提示词、参考图、配音都是空的，
必须人来填（填在 ``build_story.py`` 里，跑一次 ``build_story.py`` 写进 story.json）。
这是设计，不是缺陷——参考项目的前身里"无声成片"就是被一道只看容器字段的校验放过去的。

参考实现只在被复制时被读取，永不写入（``test_new_topic.py::test_reference_project_is_untouched``）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # production/
ROOT = HERE.parent                              # repo root
REFERENCE = HERE / "shanghai_freezer_case"
TEMPLATES = HERE / "templates"

# 参考项目的固定标识 -> 新项目标识。顺序有意义：先长串后短串。
REFERENCE_SLUG = "shanghai_freezer_case"
REFERENCE_BRANCH = "arena/f9f847e0-desktop-tutorial"
REFERENCE_TITLE = "上海冰柜藏尸案：她死了105天，丈夫用她的微信聊了105天"
REFERENCE_FILM = "上海冰柜藏尸案_105天_三分钟_带声音.mp4"
REFERENCE_STEM = "上海冰柜藏尸案"   # 交付物文件名前缀：Cover.jpg / Subtitles.srt / Technical_Report.json

SHOT_COUNT = 30
GRID = 6
CHAPTER_COUNT = 6
CHAPTER_LENGTH = 30

CUTS_BLOCK = re.compile(r"^CUTS = \{.*?^\}", re.M | re.S)   # 保留给旧模板兼容，新模板不用

ENGINE_FILES = (
    "generate.py",
    "qc.py",
    # preflight.py 不再从参考项目整份拷：改走 production/templates/preflight.py
    # （角色映射从 story.json 现算，避免新题目预检被旧项目的角色代号锁死）。
    "throttle.py",
    "narration_fit.py",
    "build_audio_manifest.py",
    "build_sfx.py",
)
# production/templates/ 里"内容与引擎分离"的文件：占位符由本脚本替换。
# preflight.py 无占位符，render_template 原样拷贝（保留 GENERATED 头注释）。
TEMPLATE_FILES = ("render.py", "build_story.py", "preflight.py")
WORKFLOW_TEMPLATES = {
    "case.workflow.yml": "{slug}.yml",
    "verbatim.workflow.yml": "{slug}-verbatim.yml",
    "visual-qc.workflow.yml": "{slug}-visual-qc.yml",
}


def film_name(title: str) -> str:
    """片名 -> 成片文件名：上海冰柜藏尸案：…… -> 上海冰柜藏尸案_105天_三分钟_带声音.mp4"""
    safe = re.sub(r'[\\/:*?"<>|：]', "_", title).strip("_ ") or "untitled"
    return f"{safe}_三分钟_带声音.mp4"


def film_stem(title: str) -> str:
    return film_name(title)[: -len("_三分钟_带声音.mp4")]


# --------------------------------------------------------------------------
# 文本替换
# --------------------------------------------------------------------------
def substitutions(slug: str, branch: str, title: str) -> tuple[tuple[str, str], ...]:
    """参考项目标识到新项目标识的替换表（长串优先，避免半截替换）。"""
    short_branch = branch.rsplit("/", 1)[-1] if branch else slug
    return (
        (REFERENCE_BRANCH, branch),
        (f"production/{REFERENCE_SLUG}", f"production/{slug}"),
        (f"work/{REFERENCE_SLUG}", f"work/{slug}"),
        (REFERENCE_FILM, film_name(title)),
        (REFERENCE_STEM, film_stem(title)),     # Cover.jpg / Subtitles.srt / Technical_Report.json 等交付物名
        (REFERENCE_TITLE, title),
        (REFERENCE_SLUG, slug),
        ("f9f847e0-desktop-tutorial", short_branch),   # 兜底：并发组里的短分支名
        # 兜底：任何漏网的旧片名都换掉，副本里不残留旧品牌
        ("上海冰柜藏尸案", title),
    )


def patch(text: str, slug: str, branch: str, title: str) -> str:
    for old, new in substitutions(slug, branch, title):
        text = text.replace(old, new)
    return text


def template_substitutions(slug: str, branch: str, title: str) -> tuple[tuple[str, str], ...]:
    short_branch = branch.rsplit("/", 1)[-1] if branch else slug
    return (
        ("__SHORT_BRANCH__", short_branch),
        ("__BRANCH__", branch),
        ("__SLUG__", slug),
        ("__TITLE__", title),
        ("__FILM__", film_name(title)),
    )


def render_template(name: str, slug: str, branch: str, title: str, templates: Path) -> str:
    text = (templates / name).read_text(encoding="utf-8")
    for old, new in template_substitutions(slug, branch, title):
        text = text.replace(old, new)
    return text


# --------------------------------------------------------------------------
# 骨架内容
# --------------------------------------------------------------------------
def chapter_of(start: int) -> str:
    return f"N{min(CHAPTER_COUNT, start // CHAPTER_LENGTH + 1):02d}"


def starter_story(slug: str, branch: str, title: str, reference: Path) -> dict:
    """按参考项目的分镜结构生成骨架：30 镜 × 6 秒规划网格、6 章 × 30 秒。

    时间轴、分辨率、帧率这些"机械正确"的部分直接算好；提示词与解说词留空，
    留给人写（写在 build_story.py 里）——空的提示词会让 ``validate()`` 直接报错。
    """
    ref_story = json.loads((reference / "story.json").read_text(encoding="utf-8"))

    shots = []
    for index in range(SHOT_COUNT):
        start = index * GRID
        shots.append({
            "id": f"S{index + 1:02d}",
            "kind": "agnes",
            "start": float(start),
            "duration": GRID,
            "seconds": GRID,
            "aspect": "16:9",
            "source_size": "720P",
            "narration_id": chapter_of(start),
            "narration": "",                   # TODO 人来写（build_story.py 的 ROWS）
            "prompt": "",                      # TODO 人来写
            "purpose": "",
            "camera": "",
            "sound_design": "",
            "color_grade": "",
            "reference_ids": "",               # TODO 对应 reference/approvals.json 的批准条目
            "characters": [],
            "seed": 20260101 + index,
            "transition_in": "",
            "transition_out": "",
        })

    chapters = []
    for index in range(CHAPTER_COUNT):
        chapters.append({
            "id": f"N{index + 1:02d}",
            "title": "",                       # TODO 章节标题
            "start": index * CHAPTER_LENGTH,
            "duration": CHAPTER_LENGTH,
            "text": "",                        # TODO 解说词（六段合计自填）
        })

    return {
        "title": title,
        "film_name": film_name(title),
        "target_duration": SHOT_COUNT * GRID,
        "width": ref_story.get("width", 1920),
        "height": ref_story.get("height", 1080),
        "fps": ref_story.get("fps", 24),
        "model": ref_story.get("model", "agnes-video-2.5-flash"),
        "source_size": ref_story.get("source_size", "720P"),
        "branch": branch,
        "style_prefix": "",                    # TODO build_story.py 的 STYLE
        "style_rumor_prefix": "",              # TODO 同 STYLE（校验要求以【STYLE 开头）
        "negative_prompt": "",                 # TODO build_story.py 的 NEGATIVE
        "characters": {},
        "character_seeds": {},
        "narration_spec": {
            "voice_id": "pending_voice_selection",
            "description": "",                 # TODO 试音选定后的音色描述
            "language": "zh-CN",
            "target_characters_per_second": 4.2,
            "alignment": "一镜一句，一镜一条TTS与一条字幕",
        },
        "chapters": chapters,
        "shots": shots,
        "reference_images": [],                # build_story.py 从 reference/approvals.json 回填
        "reference_revision": "",
        "reference_designs": {"characters": [], "scenes": [], "props": [],
                              "note": "先出参考图并逐张批准，再跑 --validate；否则会按设计报错。"},
        "presentation": {
            "onscreen_label": "AI动画情景重现 · 非真实影像",
            "highlight_phrases": [],
            "hooks": [],
            "explainers": [],
            "end_title": "",
            "end_subtitle": "",
            "title_start": 174.6,
            "title_end": 179.5,
            "cover_text": "",
            "cover_concept": "",
            "publish_title": "",
            "hashtags": [],
            "caption_policy": {
                "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
                "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
                "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
                "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
            },
        },
        "sfx_only": True,
        "fact_check": {"status": "TODO", "as_of": "", "legal_note": "", "sources": [], "editorial_cautions": []},
        "production_rules": [],
        "_scaffold": {
            "reference": f"production/{REFERENCE_SLUG}",
            "generator": "production/new_topic.py",
            "slug": slug,
            "note": f"{SHOT_COUNT} 镜 × {GRID} 秒 / {CHAPTER_COUNT} 章 × {CHAPTER_LENGTH} 秒 的骨架已算好；"
                    "内容写在 build_story.py 里，跑一次 build_story.py 才会进 story.json；"
                    "提示词、解说词、style_prefix、批准参考图必须填完才能通过 --validate。",
        },
    }


def chapter_shots(story: dict) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for shot in story["shots"]:
        grouped.setdefault(shot["narration_id"], []).append(shot["id"])
    return grouped


def rows_skeleton(story: dict) -> str:
    """build_story.py 里 ROWS 的 30 行占位（按章分组，带 TODO）。"""
    lines = []
    for cue, shots in chapter_shots(story).items():
        lines.append(f"    # ---------------- {cue}（{len(shots)} 镜）----------------")
        for shot in shots:
            lines.append(
                f'    ({GRID}, "TODO 解说一句话",\n'
                f'     "TODO 这一镜的画面与运镜（中文，含机位/景别/主体/动作/环境）",\n'
                f'     "TODO 参考图编号，如 P01 或 S02+C01", [], "TODO 运镜", "TODO 音效/环境声", "TODO 色调"),'
            )
    return "\n".join(lines)


def starter_screenplay(title: str, story: dict) -> str:
    head = [
        f"# {title}",
        "",
        "三分钟横屏解说 · 成片目标 "
        f"{story['width']}×{story['height']} / {story['fps']} fps / {story['target_duration']} 秒",
        "",
        "## 事实边界",
        "",
        "TODO 写清楚：哪些是公开资料可证的事实，哪些是情景重现，哪些坚决不写。",
        "这一段是这部片子的底线，比任何画面都重要（参考 `production/shanghai_freezer_case/FACT_CHECK.md`）。",
        "",
        "## 解说稿与时间线",
        "",
    ]
    sections = []
    for chapter in story["chapters"]:
        start = chapter["start"]
        end = start + chapter["duration"]
        sections.append(
            f"### {start // 60:02d}:{start % 60:02d}—{end // 60:02d}:{end % 60:02d}"
            f"　TODO 章节标题（{chapter['id']}）\n\n"
            "TODO 解说词。写在 `build_story.py` 的 ROWS 里，跑一次 `build_story.py` 会同步进 "
            "`story.json` 的 `shots[].narration`；这里再抄一遍，两处必须逐字一致，否则渲染会拒绝出片。\n"
        )
    table = [
        "## 分镜与衔接",
        "",
        "| 镜头 | 规划时间 | 类型 | 画面与运镜 | 参考图 |",
        "|---|---|---|---|---|",
    ]
    for shot in story["shots"]:
        start = int(shot["start"])
        table.append(f"| {shot['id']} | {start:03d}—{start + shot['duration']:03d}s | Agnes | TODO | TODO |")
    return "\n".join(head + sections + table) + "\n"


def starter_manifest(story: dict) -> dict:
    return {
        "language": "zh-CN",
        "voice": "",                          # TODO：试音后的 voice_id（audio/voice.json 同步登记；build_audio_manifest.py 回填）
        "generation": "Arena TTS; one independent clip per shot",
        "alignment": "one-clip-one-shot-one-caption",
        "max_speedup_factor": 1.55,
        "slowdown_allowed": False,
        "clips": [
            {"id": shot["id"], "file": f"{shot['id']}.mp3", "text": "", "sha256": "",
             "voice_id": "", "voice_description": "", "narration_id": shot["narration_id"],
             "target_start": shot["start"], "target_duration": shot["duration"],
             "alignment": "shot-locked", "source_duration": 0.0, "atempo": 1.0,
             "tail_silence_seconds": 0.0}
            for shot in story["shots"]
        ],
    }


def starter_readme(slug: str, title: str, branch: str) -> str:
    film = film_name(title)
    return f"""# {title}

由 `production/new_topic.py` 从参考项目 `production/shanghai_freezer_case`（《上海冰柜藏尸案》，已成片、已换声重渲）
开出来的新项目目录。参考实现只被复制，没有被修改；本片的所有编辑都发生在这个目录里。
端到端流程见仓库根目录的 `新题目开工手册.md`。

- slug：`{slug}`　出片分支：`{branch}`　成片文件名：`{film}`
- 规格：1920×1080 / 24 fps / 180 秒；**30 个 Agnes Video 2.5 Flash 镜头，每个镜头只出现一次**；全片无 BGM
- 默认画面文字层：**光州胶带案风格**（`production/gwangju_style.py`）——画面内解说词字幕 + 画面中间偏下金色注释 + 钩子大字；
  在 `build_story.py` 填 `HOOKS` / `EXPLAINERS` / `HIGHLIGHT_PHRASES`，渲染时自动烧录。

## 现在还不能出片（故意的）

`generate.py --validate` 现在**会失败**，因为解说词、提示词、参考图、配音都是空的。按下面顺序填完，它才会放行。

## 待办清单（上海冰柜藏尸案模式）

1. **事实与红线** → `FACT_CHECK.md`（先写这个文件）：公开资料口径、判决/进展、媒体口径 vs 日历口径的数字差异、
   受害者称谓、施害过程不展示。每句话都要能指到一个公开来源；未实时复核的，如实写在 `story.json` 的 `fact_check.status`。
2. **解说稿** → `build_story.py` 的 `ROWS`：30 句、一镜一句、数字中文读法、不写血腥细节；
   每句都要能对上参考图与 `FACT_CHECK.md` 的条目。
3. **分镜与参考图** → `ROWS` 的 visual / refs / characters / camera：提示词先钉死唯一场景，
   再明确排除别的场景，最后加运镜句。参考图批准后放 `reference/` 并登记 `reference/approvals.json`
   （`status=approved` + sha256）与 `reference/revision.txt`（git 里的 reference 快照 commit）。
4. **角色锚点** → `CHARACTERS` / `CHARACTER_SEEDS`：每个反复出现的角色一个锚点一句（虚构演员式形象），每角色固定 seed。
5. 写完跑：

   ```bash
   python3 production/{slug}/build_story.py          # 写 story.json + screenplay.md + 抖音脚本.md + 抖音发布文案.md
   python3 production/{slug}/generate.py --validate  # 闸门一（空内容会被它拦住）
   ```

6. **配音** → `add_voice`（先让用户试听并选定）→ 30 条 TTS 放 `audio/Sxx.mp3` → 写 `audio/voice.json` →
   `python3 production/{slug}/build_audio_manifest.py` 回填 sha256/时长。
7. **生成素材** → 把 `workflows/` 下三份复制到 `.github/workflows/`（需要 workflows 写权限），写 `GEN_REQUEST`
   （`{{"mode":"clips","workers":2}}`）并 push；逐镜看 `qa/Sxx.jpg`，坏镜头只改它的 prompt 后
   `{{"mode":"clips","only":"S03,S08"}}` 重做，其余按 SHA-256 复用。
8. **出片** → `GEN_REQUEST` 写 `{{"mode":"render"}}` 并 push；成片 commit 回 `交付/{film}`；
   复检：按 EDL 逐段抽帧看画面/字幕/标签。
9. **听检** → 写 `VERBATIM_REQUEST` 并 push（或 Actions 手动触发 `{slug}-verbatim.yml`）；
   `delivery/verbatim-check.json` 每镜 CER 都要 ≤ 0.15，否则人工听。
10. **技术 QC** → 写 `VISUAL_QC_REQUEST` 并 push（或手动触发 `{slug}-visual-qc.yml`）；
    工作流跑 `qc.py` 并把 `qa/qc-report.json` / `qa/qc-summary.md` commit 回分支。**自动结果只是分诊，不是签收。**
11. **人工语义签收** → 逐镜完整播放：伪文字、面部/手部形变、字幕与画面冲突、钩子/注释有没有被裁、片尾卡是否完整。
    发现问题回对应步骤修完重渲。
12. **发布** → 抖音发布由主创手动上传（本仓库不自动发布）；`build_story.py` 已生成 `抖音发布文案.md`；
    系列封面走 `production/mystery-cover-template/`；需要 Release 时写 `RELEASE_UPLOAD_REQUEST`。

## 目录

| 路径 | 作用 |
|---|---|
| `FACT_CHECK.md` | 事实边界与来源（先写它） |
| `build_story.py` | **唯一内容源**：解说词、30 镜、STYLE/NEGATIVE、角色锚点、钩子、注释、发布文案 |
| `story.json` | 分镜计划（由 build_story.py 写入，含 `presentation` 块） |
| `screenplay.md` / `抖音脚本.md` | 解说稿 + 分镜表（生成物，禁手改） |
| `抖音发布文案.md` | 标题/介绍/提问/话题（生成物，禁手改） |
| `reference/` + `reference/approvals.json` + `revision.txt` | 批准的参考图 + sha256 登记 + git 快照 commit |
| `audio/Sxx.mp3` / `audio/voice.json` / `audio/manifest.json` | 每镜配音 / 选定音色 / 收据 |
| `generate.py` | Agnes 生成（节流、断点续跑、--validate 闸门、--render-only 出片） |
| `render.py` | 剪辑引擎：逐镜归一化、字幕/钩子/注释烧录、混音、成品测量 |
| `qc.py` / `preflight.py` | 源片与成片技术 QC；开工前硬闸 |
| `build_audio_manifest.py` / `build_sfx.py` / `narration_fit.py` / `throttle.py` | 配音收据 / 逐镜音效（无 BGM）/ TTS 适配 / 节流 |
| `workflows/` | 三份工作流（合一出片 / 逐字听检 / 技术 QC），复制到 `.github/workflows/` 才生效 |
| `GEN_REQUEST` / `CANCEL_REQUEST` / `VERBATIM_REQUEST` / `VISUAL_QC_REQUEST` / `RELEASE_UPLOAD_REQUEST` | push 触发工作流的 marker 文件（按需创建） |
| `qa/` | 接触表、QC 报告（CI 写回） |

## 红线（继承自参考项目，不要删）

- AI 画面一律标注「AI动画情景重现 · 非真实影像」，不冒充真实影像；
- 真实人物只以 AI 虚构演员式形象出现，不用 AI 生成的脸冒充本人；受害者不以人像出现；
- 不展示遗体、血腥或侵害过程；未定论的事不写成结论；
- 中文姓名、日期、字幕一律后期烧录，不交给视频模型拼写；
- 成片必须实测电平与时长（`python3 production/verify_master.py ...`），无声/时长不对不许交付；
- 每个镜头只出现一次，不复用；
- **成片交付前必须人工完整播放**：QC 绿 ≠ 可交付。
"""


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def scaffold(slug: str, title: str, branch: str, dest: Path, reference: Path,
             templates: Path = TEMPLATES) -> Path:
    if not reference.is_dir():
        raise SystemExit(f"参考项目不存在：{reference}")
    if not templates.is_dir():
        raise SystemExit(f"模板目录不存在：{templates}")
    missing = [name for name in ENGINE_FILES if not (reference / name).is_file()]
    if missing:
        raise SystemExit(f"参考项目缺少引擎文件：{', '.join(missing)}")
    missing = [name for name in (*TEMPLATE_FILES, *WORKFLOW_TEMPLATES) if not (templates / name).is_file()]
    if missing:
        raise SystemExit(f"模板目录缺少：{', '.join(missing)}")
    if dest.exists():
        raise SystemExit(f"目标目录已存在，先删掉或换一个 slug：{dest}")

    dest.mkdir(parents=True)
    (dest / "audio").mkdir()
    (dest / "reference").mkdir()
    (dest / "workflows").mkdir()

    story = starter_story(slug, branch, title, reference)

    for name in ENGINE_FILES:
        text = (reference / name).read_text(encoding="utf-8")
        (dest / name).write_text(patch(text, slug, branch, title), encoding="utf-8")

    for name in TEMPLATE_FILES:
        text = render_template(name, slug, branch, title, templates)
        if name == "build_story.py":
            if "__ROWS__" not in text:
                raise SystemExit("模板 build_story.py 里找不到 __ROWS__ 占位，脚手架已中止")
            text = text.replace("__ROWS__", rows_skeleton(story))
        (dest / name).write_text(text, encoding="utf-8")

    for name, target in WORKFLOW_TEMPLATES.items():
        (dest / "workflows" / target.format(slug=slug)).write_text(
            render_template(name, slug, branch, title, templates), encoding="utf-8")

    (dest / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dest / "screenplay.md").write_text(starter_screenplay(title, story), encoding="utf-8")
    (dest / "audio" / "manifest.json").write_text(
        json.dumps(starter_manifest(story), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dest / "reference" / "approvals.json").write_text(
        json.dumps({"assets": {}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dest / "README.md").write_text(starter_readme(slug, title, branch), encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", required=True, help="新项目目录名，小写字母数字，如 jinanforum")
    parser.add_argument("--title", required=True, help="中文片名，如 某某案：一句钩子")
    parser.add_argument("--branch", default="", help="出片分支（默认取当前 git 分支）")
    parser.add_argument("--dest", type=Path, default=None,
                        help="项目目录（默认 production/<slug>）")
    parser.add_argument("--reference", type=Path, default=REFERENCE,
                        help="参考项目目录（默认 production/shanghai_freezer_case）")
    parser.add_argument("--templates", type=Path, default=TEMPLATES,
                        help="模板目录（默认 production/templates）")
    args = parser.parse_args(argv)

    if not re.fullmatch(r"[a-z][a-z0-9_]{1,31}", args.slug):
        raise SystemExit("slug 只能是小写字母、数字、下划线，且以字母开头")

    branch = args.branch
    if not branch:
        import subprocess
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
    if not branch:
        raise SystemExit("取不到当前分支，请用 --branch 指定出片分支")

    dest = args.dest or (HERE / args.slug)
    created = scaffold(args.slug, args.title, branch, dest, args.reference, args.templates)

    print(f"已开出新项目：{created.relative_to(ROOT) if created.is_relative_to(ROOT) else created}")
    print(f"  出片分支：{branch}")
    print(f"  成片文件名：{film_name(args.title)}")
    print(f"  下一步：先写 FACT_CHECK.md，再填 {created.name}/build_story.py（ROWS / STYLE / 钩子），")
    print(f"        跑 python3 production/{args.slug}/build_story.py 写入 story.json，")
    print(f"        再跑 python3 production/{args.slug}/generate.py --validate")
    print(f"  工作流：把 {created.name}/workflows/*.yml 复制到 .github/workflows/ 才能用 marker 文件触发")
    return 0


if __name__ == "__main__":
    sys.exit(main())
