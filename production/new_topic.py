#!/usr/bin/env python3
"""新题目开工脚手架：以《黑色大丽花》为参考实现，开出一个可以独立编辑的项目目录。

用法::

    python3 production/new_topic.py --slug ripper1888 \
        --title "开膛手杰克：1888 年的秋天" \
        --branch arena/xxxx-desktop-tutorial

它做的事（不改参考项目一个字节）：

1. 复制流水线引擎（``media/throttle/align_audio/build_audio/render/generate/
   fetch_sources/watch_run``）到 ``production/<slug>/``；
2. 把副本里所有 ``production/dahlia``、``work/dahlia``、分支名、成片文件名、
   Actions 并发组名替换成新项目的；
3. 按参考项目的 30 镜 × 6 秒 / 6 章 × 30 秒 结构生成 ``story.json`` 骨架，
   并把 ``render.py`` 的 ``CUTS`` 剪辑表重写成对应骨架（每段解说 5 个镜头）；
4. 生成 ``screenplay.md``、``audio/manifest.json``、``README.md`` 和一份薄薄的
   ``<slug>.workflow.yml``（真正的出片步骤统一在 ``production/run_project.sh``）。

生成的项目**故意过不了** ``generate.py --validate``：镜头提示词、解说词、
配音文件与 SHA-256 都是空的，必须人来填。这是设计，不是缺陷——参考项目里
"无声成片"就是被一道只看容器字段的校验放过去的。

参考实现只在被复制时被读取，永不写入。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # production/
ROOT = HERE.parent                              # repo root
REFERENCE = HERE / "dahlia"

# 参考项目里需要复制到新项目的流水线引擎。
ENGINE_FILES = (
    "media.py",
    "throttle.py",
    "align_audio.py",
    "build_audio.py",
    "render.py",
    "generate.py",
    "fetch_sources.py",
    "watch_run.py",
)

# 参考项目的固定标识 -> 新项目标识。顺序有意义：先长串后短串。
REFERENCE_BRANCH = "arena/01a085be-desktop-tutorial"
REFERENCE_TITLE = "黑色大丽花"

SHOT_COUNT = 30
SHOT_LENGTH = 6
CHAPTER_COUNT = 6
CHAPTER_LENGTH = 30

CUTS_BLOCK = re.compile(r"^CUTS = \{.*?^\}", re.M | re.S)

# render.py 里几处**属于内容而不是流水线**的地方：参考片子的卡片文案、
# 逐镜标签覆盖、片头/片尾字幕卡、档案照片文件名。脚手架不猜内容，一律换成
# 显式 TODO，并在找不到这些位置时直接中止——宁可报错，也不要让新题目
# 悄悄顶着旧片名出片。
CARD_HEADINGS = re.compile(r"^[ \t]*headings=\{.*?^[ \t]*\}[ \t]*$", re.M | re.S)
CARD_VARIANTS = re.compile(
    r"^(?:[ \t]*if variant=='[a-z_]+':title,line1,line2=.*\n)+", re.M)
CARD_SPECIAL = re.compile(
    r"^(?P<indent>[ \t]*)if sid=='S\d+':\n(?:[ \t]+.*\n)+?[ \t]*else:(?P<tail>[^\n]*)\n", re.M)
ARCHIVE_ASSET = re.compile(r"source=HERE/'assets/[^']+'")
CAPTION_KEYWORDS = re.compile(r"^(?P<indent>[ \t]*)for key in \[.*?\]:[ \t]*$", re.M)
LABEL_OVERRIDES = re.compile(r"^(?:[ \t]*if entry\['id'\]=='S\d+':label=.*\n)+", re.M)
TITLE_CARD = re.compile(r"黑色大丽花\\\\N\{[^}]*\}消失的六天")

# 卡片上的字面文案（参考片子的内容）-> 通用占位
CONTENT_SUBSTITUTIONS = (
    ("'伊丽莎白 · 肖特'", "'TODO 人物或主题'"),
    ("'她只有二十二岁'", "'TODO 片尾第一行'"),
    ("'真实的人，不只是一个案件的名字。'", "'TODO 片尾第二行'"),
    ("'案件档案  /  LOS ANGELES · 1947'", "'TODO 卡片抬头'"),
    ("'她的名字'", "'TODO 档案卡标题'"),
    ("'22岁'", "'TODO 档案卡副标'"),
)


def _require_sub(pattern: re.Pattern, replacement, text: str, label: str) -> str:
    """替换必须命中一次；没命中说明参考项目结构变了，脚手架拒绝继续。"""
    result, hits = pattern.subn(replacement, text, count=1)
    if hits != 1:
        raise SystemExit(f"参考项目的 render.py 里找不到{label}（命中 {hits} 次），脚手架已中止")
    return result


def strip_project_content(text: str, title: str) -> str:
    """把 render.py 副本里参考项目专属的内容换成显式 TODO。"""
    text = _require_sub(CARD_HEADINGS,
                        "        headings={\n"
                        "            # TODO 本片每张信息卡的三行文案：镜头号 -> (大标题, 第一行, 第二行)\n"
                        "        }",
                        text, "信息卡文案表 headings")

    text = _require_sub(CARD_VARIANTS,
                        "        # TODO 需要具名信息卡变体时在这里加分支（参考项目有 archive / truth 两种）\n",
                        text, "信息卡变体覆盖")

    def special(match: re.Match) -> str:
        indent = match.group("indent")
        tail = match.group("tail").strip()
        return (f"{indent}# TODO 某个镜头需要特殊画法时在这里加分支"
                f"（参考项目给一个镜头画了时间轴缺口）\n{indent}{tail}\n")
    text = _require_sub(CARD_SPECIAL, special, text, "单镜头特殊画法分支")

    text = _require_sub(ARCHIVE_ASSET,
                        "source=HERE/'assets'/'TODO-你的档案照片.jpg'  # TODO 换成本片的档案照片",
                        text, "档案照片文件名")

    def keywords(match: re.Match) -> str:
        indent = match.group("indent")
        return (f"{indent}for key in [\n"
                f"{indent}    # TODO 本片要在字幕里高亮的关键词（参考项目放的是人名、数字、结论词）\n"
                f"{indent}]:")
    text = _require_sub(CAPTION_KEYWORDS, keywords, text, "字幕高亮关键词表")

    text = _require_sub(LABEL_OVERRIDES,
                        "        # TODO 按本片的镜头改写标签覆盖（参考项目给个别镜头换了更准确的说法）\n",
                        text, "逐镜标签覆盖")

    text = _require_sub(TITLE_CARD, title, text, "片头字幕卡")

    for old, new in CONTENT_SUBSTITUTIONS:
        if old in text:
            text = text.replace(old, new)
    return text



# --------------------------------------------------------------------------
# 文本替换
# --------------------------------------------------------------------------
def substitutions(slug: str, branch: str, title: str) -> tuple[tuple[str, str], ...]:
    """参考项目标识到新项目标识的替换表（长串优先，避免半截替换）。"""
    short_branch = branch.rsplit("/", 1)[-1] if branch else slug
    film = f"{title}_三分钟.mp4"
    return (
        (REFERENCE_BRANCH, branch),
        ("production/dahlia", f"production/{slug}"),
        ("work/dahlia", f"work/{slug}"),
        ("arena-dahlia-refetch", f"arena-{slug}-refetch"),
        ("dahlia-audio-arena-01a085be", f"{slug}-arena-{short_branch}"),
        ("black-dahlia-arena-01a085be", f"{slug}-arena-{short_branch}"),
        ("black-dahlia-agnes-", f"{slug}-agnes-"),
        ("Black Dahlia · 有声成片", f"{title} · 有声成片"),
        ("Black Dahlia short", f"{title} short"),
        ("'dahlia: '", f"'{slug}: '"),
        (f"{REFERENCE_TITLE}_三分钟_带声音.mp4", film),
        (f"{REFERENCE_TITLE}_三分钟_初版.mp4", f"{title}_三分钟_初版.mp4"),
        (f"{REFERENCE_TITLE}_字幕.srt", f"{title}_字幕.srt"),
        (f"{REFERENCE_TITLE}-三分钟-带声音", f"{title}-三分钟"),
        (f"{REFERENCE_TITLE} · 三分钟初版", f"{title} · 三分钟初版"),
        (f"{REFERENCE_TITLE}：消失的六天", title),
        # 参考项目的悬案专用措辞换成对所有题目都成立的说法
        ("AI情景重现并非历史影像；未证实的凶手身份没有被写成事实。",
         "AI情景重现并非历史影像；未经证实的推测没有被写成事实。"),
        ("档案照片 · 来源：警方调查通告", "档案照片 · 来源见 story.json 的 sources"),
        ("资料：FBI Black Dahlia  /  原创解说 · AI情景重现",
         "资料：来源见 story.json 的 sources / 原创解说 · AI情景重现"),
        # 最后兜底：任何漏网的旧片名都换成新片名，副本里不残留旧品牌
        ("Black Dahlia", title),
        (REFERENCE_TITLE, title),
    )


def patch(text: str, slug: str, branch: str, title: str) -> str:
    for old, new in substitutions(slug, branch, title):
        text = text.replace(old, new)
    return text


# --------------------------------------------------------------------------
# 骨架内容
# --------------------------------------------------------------------------
def starter_story(slug: str, branch: str, title: str, reference: Path) -> dict:
    """按参考项目的分镜结构生成骨架：30 镜 × 6 秒、6 章 × 30 秒。

    时间轴、分辨率、帧率这些"机械正确"的部分直接算好；提示词与解说词留空，
    留给人写——空的提示词会让 ``validate()`` 直接报错。
    """
    ref_story = json.loads((reference / "story.json").read_text())
    ref_shot = next(s for s in ref_story["shots"] if s["kind"] == "agnes")

    shots = []
    for index in range(SHOT_COUNT):
        shots.append({
            "id": f"S{index + 1:02d}",
            "kind": "agnes",
            "start": index * SHOT_LENGTH,
            "duration": SHOT_LENGTH,
            "narration_id": f"N{index // (SHOT_COUNT // CHAPTER_COUNT) + 1:02d}",
            "prompt": "",                      # TODO 人来写：这一镜画面内容
            "purpose": "",                     # TODO 人来写：这一镜的叙事职责
            "transition_out": "",              # TODO 人来写：如何接下一镜
            "graphic": "",                     # 信息卡文案（kind=graphic 时必填）
            "seed": 1000 + index,
            "seconds": ref_shot.get("seconds", 6),
            "aspect": ref_shot.get("aspect", "16:9"),
            "resolution": ref_shot.get("resolution", "1080p"),
            "frame_rate": ref_shot.get("frame_rate", 30),
        })

    chapters = []
    for index in range(CHAPTER_COUNT):
        chapters.append({
            "id": f"N{index + 1:02d}",
            "title": "",                       # TODO 章节标题
            "start": index * CHAPTER_LENGTH,
            "duration": CHAPTER_LENGTH,
            "text": "",                        # TODO 解说词（约 90–120 字）
        })

    return {
        "title": title,
        "target_duration": SHOT_COUNT * SHOT_LENGTH,
        "width": ref_story.get("width", 1920),
        "height": ref_story.get("height", 1080),
        "fps": ref_story.get("fps", 30),
        "model": ref_story.get("model", "agnes-video-v2.0"),
        "branch": branch,
        "style_prefix": "",                    # TODO 全片统一的画面风格前缀（英文）
        "negative_prompt": ref_story.get("negative_prompt", ""),
        "principles": [],                      # TODO 本片的事实边界与红线
        "chapters": chapters,
        "shots": shots,
        "sources": [],                         # TODO 每条事实的公开来源
        "_scaffold": {
            "reference": "production/dahlia",
            "generator": "production/new_topic.py",
            "slug": slug,
            "note": "30 镜 × 6 秒 / 6 章 × 30 秒 的骨架已算好；提示词、解说词、"
                    "style_prefix、principles、sources 必须填完才能通过 --validate。",
        },
    }


def cuts_skeleton(story: dict) -> str:
    """按 story.json 生成 render.py 的 CUTS 剪辑表骨架。

    参考项目里 CUTS 的时间点是**听过配音后手工对出来的**；这里只给一个均匀
    起点（每段解说 5 个镜头、每 6 秒一切），拿到配音后必须重对。
    """
    per_chapter = SHOT_COUNT // CHAPTER_COUNT
    lines = [
        "# 骨架 CUTS：均匀 6 秒一切，只是起点。",
        "# 拿到真实配音后，必须按配音里的实际停顿重新对时间点（参考项目就是这么做的）。",
        "CUTS = {",
    ]
    for cue in range(CHAPTER_COUNT):
        entries = []
        for slot in range(per_chapter):
            shot = f"S{cue * per_chapter + slot + 1:02d}"
            entries.append(f"({slot * SHOT_LENGTH},'{shot}','')")
        body = ", ".join(entries)
        lines.append(f"    'N{cue + 1:02d}': [{body}],")
    lines.append("}")
    return "\n".join(lines)


def starter_screenplay(title: str, story: dict) -> str:
    per_chapter = SHOT_COUNT // CHAPTER_COUNT
    head = [
        f"# {title}",
        "",
        "三分钟横屏解说 · 成片目标 "
        f"{story['width']}×{story['height']} / {story['fps']} fps / {story['target_duration']} 秒",
        "",
        "## 事实边界",
        "",
        "TODO 写清楚：哪些是公开资料可证的事实，哪些是情景重现，哪些坚决不写。",
        "这一段是这部片子的底线，比任何画面都重要（参考 `production/dahlia/screenplay.md`）。",
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
            "TODO 解说词。三分钟六段，每段约 90–120 字；写完把同一段文字填进 "
            "`story.json` 的 `chapters[].text` 和 `audio/manifest.json` 的 `clips[].text`，"
            "三处必须逐字一致，否则 `generate.py` 会拒绝出片。\n"
        )
    table = [
        "## 分镜与衔接",
        "",
        "| 镜头 | 时间 | 类型 | 叙事职责 | 衔接方式 |",
        "|---|---|---|---|---|",
    ]
    for index, shot in enumerate(story["shots"]):
        start = shot["start"]
        table.append(
            f"| {shot['id']} | {start:03d}—{start + shot['duration']:03d}s | "
            f"{shot['kind']} | TODO | TODO |"
        )
        if (index + 1) % per_chapter == 0:
            table.append(f"| — | — | 解说 {shot['narration_id']} 结束 | — | — |")
    return "\n".join(head + sections + table) + "\n"


def starter_manifest(story: dict) -> dict:
    return {
        "voice_id": "",
        "language": "zh-CN",
        "selection": "TODO 用户试听后选定的音色",
        "clips": [
            {"id": chapter["id"], "file": f"{chapter['id']}.mp3", "sha256": "", "text": ""}
            for chapter in story["chapters"]
        ],
    }


def starter_workflow(slug: str, title: str, branch: str) -> str:
    """每个项目自带一份工作流模板；真正的流程在 production/run_project.sh 里。

    仓库里已经有一个通用工作流（`production/commentary-render.workflow.yml`，
    复制到 `.github/workflows/commentary-render.yml` 后在 Actions 里填 slug 即可）。
    这份是给"想要一个专属按钮"的情况用的，两者不冲突。
    """
    short_branch = branch.rsplit("/", 1)[-1]
    return f"""name: {title} · 出片
run-name: {title} · 出片（含音量实测）

# 真正的流程在 production/run_project.sh，改流程只改脚本，不必再动 workflows。

on:
  workflow_dispatch:
    inputs:
      skip_asr:
        description: '跳过 ASR 对轨（离线时用停顿估算字幕时间）'
        type: boolean
        default: false

permissions:
  contents: write

concurrency:
  group: {slug}-arena-{short_branch}
  cancel-in-progress: false

jobs:
  render:
    if: github.ref == 'refs/heads/{branch}'
    runs-on: ubuntu-latest
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Install media tools and CJK fonts
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y -qq ffmpeg fonts-noto-cjk
          ffmpeg -hide_banner -version | head -1

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install render dependencies
        run: |
          python -m pip install "pillow>=10,<13" "numpy>=1.26,<3" "faster-whisper>=1.1,<2" || \\
          python -m pip install --break-system-packages "pillow>=10,<13" "numpy>=1.26,<3" "faster-whisper>=1.1,<2"

      - name: Validate, restore footage, render, publish reports
        env:
          SKIP_ASR: ${{{{ inputs.skip_asr }}}}
          BRANCH: {branch}
        run: bash production/run_project.sh {slug} "$SKIP_ASR"

      - name: Upload the finished film
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: {title}-成片
          path: work/{slug}/*.mp4
          if-no-files-found: warn
          compression-level: 0
          retention-days: 30
"""


def starter_readme(slug: str, title: str, branch: str) -> str:
    return f"""# {title}

由 `production/new_topic.py` 从参考项目 `production/dahlia` 开出来的新项目目录。
参考实现只被复制，没有被修改；本片的所有编辑都发生在这个目录里。

- slug：`{slug}`
- 出片分支：`{branch}`

## 现在还不能出片（故意的）

`generate.py --validate` 现在**会失败**，因为提示词、解说词、配音都是空的。
按下面顺序填完，它才会放行。

## 待办清单

1. **事实与红线** → `story.json` 的 `principles` / `sources`，`screenplay.md` 的「事实边界」。
   每一条要说的话都得有公开来源；没有来源的推测不写。
2. **解说稿** → 六段各 90–120 字。同一段文字要**逐字一致**地出现在三处：
   `screenplay.md`、`story.json` 的 `chapters[].text`、`audio/manifest.json` 的 `clips[].text`。
3. **分镜提示词** → `story.json` 的 `shots[].prompt`（英文，前面会自动拼 `style_prefix`）、
   `purpose`、`transition_out`。信息卡镜头把 `kind` 改成 `graphic` 并写 `graphic` 文案；
   用真实档案照片的镜头改成 `archive`，并补 `archive_asset` / `archive_sha256`。
4. **配音** → 六段 mp3 放进 `audio/`，把每段的 `sha256` 和 `text` 填进 `audio/manifest.json`：

   ```bash
   sha256sum audio/N01.mp3
   ```

5. **剪辑表与字幕内容** → `render.py` 的 `CUTS` 骨架是均匀 6 秒一切，**必须**听完配音后按真实停顿重对。
   副本里已经用 `TODO` 标出三处参考项目专属内容：字幕高亮关键词、逐镜标签覆盖、片头字幕卡。
   需要具名信息卡（参考项目的 `portrait_a` / `archive` / `truth` 那类）时，
   在本目录副本的 `card_image()` / `archive_image()` 里加分支，别去改参考项目。
6. **校验** → `python3 production/{slug}/generate.py --validate` 必须通过。
7. **出片** → 本地：`bash production/run_project.sh {slug}`；
   Actions：用仓库里那个通用工作流（`production/commentary-render.workflow.yml`
   复制到 `.github/workflows/commentary-render.yml` 一次，之后在 Actions 里填
   `{slug}` 即可），或者把本目录的 `{slug}.workflow.yml` 复制成 `.github/workflows/{slug}.yml`
   要一个专属按钮。当前 GitHub 授权缺 workflows 权限，复制到 `.github/workflows/`
   这一步只能你手动做。

## 目录

| 路径 | 作用 |
|---|---|
| `story.json` | 分镜计划：30 镜 × 6 秒、6 章 × 30 秒（骨架已算好，内容待填） |
| `screenplay.md` | 解说稿 + 事实边界 + 分镜表 |
| `audio/manifest.json` | 六段配音的文件名、SHA-256 与逐字文本 |
| `generate.py` | 生成 AI 素材（75 秒节流、断点续跑）+ `--validate` 闸门 |
| `fetch_sources.py` | 按 `results.json` 的 SHA-256 回填素材，不重新生成 |
| `build_audio.py` | numpy 混音 + 静音闸门（整体/逐段电平不达标就报错） |
| `render.py` | 剪辑、字幕、信息卡、封装，并对**最终 mp4** 复测电平 |
| `align_audio.py` | 字幕对轨（ASR 或停顿估算） |
| `media.py` / `throttle.py` | 探测与节流的公共实现（副本） |
| `{slug}.workflow.yml` | 本项目专属的出片工作流模板（放到 `.github/workflows/` 才能用） |
| `../run_project.sh` | **所有项目共用**的出片脚本：`bash production/run_project.sh {slug}` |

## 红线（继承自参考项目，不要删）

- AI 画面一律标注「AI情景重现 · 非历史影像」，不冒充真实影像；
- 真实人物只用有出处的档案照片，不用 AI 生成的脸冒充本人；
- 未侦破的案件不指认凶手，推测不写成结论；
- 中文姓名、日期、字幕一律后期添加，不交给视频模型拼写；
- 成片必须实测电平（`--validate` 之后还有 `render.py` 的成品复测），无声不许交付。
"""


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def scaffold(slug: str, title: str, branch: str, dest: Path, reference: Path) -> Path:
    if not reference.is_dir():
        raise SystemExit(f"参考项目不存在：{reference}")
    missing = [name for name in ENGINE_FILES if not (reference / name).is_file()]
    if missing:
        raise SystemExit(f"参考项目缺少引擎文件：{', '.join(missing)}")
    if dest.exists():
        raise SystemExit(f"目标目录已存在，先删掉或换一个 slug：{dest}")

    dest.mkdir(parents=True)
    (dest / "audio").mkdir()

    for name in ENGINE_FILES:
        text = (reference / name).read_text()
        if name == "render.py":
            text = strip_project_content(text, title)
            skeleton = cuts_skeleton(starter_story(slug, branch, title, reference))
            text, hits = CUTS_BLOCK.subn(lambda _m: skeleton, text, count=1)
            if hits != 1:
                raise SystemExit("参考项目的 render.py 里找不到 CUTS 剪辑表，脚手架已中止")
        (dest / name).write_text(patch(text, slug, branch, title))

    story = starter_story(slug, branch, title, reference)
    (dest / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")
    (dest / "screenplay.md").write_text(starter_screenplay(title, story))
    (dest / "audio" / "manifest.json").write_text(
        json.dumps(starter_manifest(story), ensure_ascii=False, indent=2) + "\n")
    (dest / "README.md").write_text(starter_readme(slug, title, branch))

    # 出片流程统一走仓库里的 production/run_project.sh，所以这里只给一份薄薄的
    # 工作流模板（真正的步骤不在 workflows 里，改流程不必再动 workflows）。
    (dest / f"{slug}.workflow.yml").write_text(starter_workflow(slug, title, branch))
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--slug", required=True, help="新项目目录名，小写字母数字，如 ripper1888")
    parser.add_argument("--title", required=True, help="中文片名，如 开膛手杰克：1888 年的秋天")
    parser.add_argument("--branch", default="", help="出片分支（默认取当前 git 分支）")
    parser.add_argument("--dest", type=Path, default=None,
                        help="项目目录（默认 production/<slug>）")
    parser.add_argument("--reference", type=Path, default=REFERENCE,
                        help="参考项目目录（默认 production/dahlia）")
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
    created = scaffold(args.slug, args.title, branch, dest, args.reference)

    print(f"已开出新项目：{created.relative_to(ROOT) if created.is_relative_to(ROOT) else created}")
    print(f"  出片分支：{branch}")
    print(f"  下一步：填 {created.name}/story.json 与 screenplay.md，")
    print(f"        再跑 python3 production/{args.slug}/generate.py --validate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
