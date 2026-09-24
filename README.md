# 长岛吉尔戈海滩连环案：披萨盒里的凶手

三分钟横版（16:9）悬疑解说短片 · 抖音 · AI 动画情景重现。
一个在曼哈顿写字楼上班、有妻有孩子的建筑咨询师，在自家地下室作案十七年、至少八名受害者，
警方一无所获三十年——最后暴露他的，是他随手扔进街头垃圾桶的一个披萨盒。

这个仓库是这部片子的**成片、脚本、发布文案**，以及把它做出来的**整条可复现流水线**（换题目照 [`新题目开工手册.md`](新题目开工手册.md) 再做一部）。

## 成片

| 项 | 内容 |
|---|---|
| 文件 | [`交付/吉尔戈海滩_披萨盒里的凶手_三分钟_带声音.mp4`](交付/吉尔戈海滩_披萨盒里的凶手_三分钟_带声音.mp4)（69.9 MB · 1920×1080 · 30 fps · 180.0 s） |
| 下载 | [Release gilgo-v1](https://github.com/32r4e2q-hub/desktop-tutorial/releases/tag/gilgo-v1) → `gilgo-v1-3min-1080p.mp4`（与 `交付/` 里的文件字节一致，SHA-256 `d9f2290473e9ca3b…`） |
| 画面 | 45 个镜头 = **38 个 Agnes Video V2.0 动画镜头 + 7 张信息卡 + 片尾卡，每个镜头只出现一次**；全片常驻「AI动画情景重现 · 非新闻影像」标签 |
| 声音 | 六段配音 785 字（TTS → 只剪静音收紧到 176 s）+ 原创配乐 + 合成音效；成片实测 RMS −20.03 dBFS · 峰值 −1.43 dBFS · 静音占比 0.55 % |
| 字幕 | 分句字幕、关键词描黄，切换点来自配音分句时间（`audio/clause-times.json`） |
| 听检 | whisper small 逐章字错率 0.007–0.073（上限 0.15），报告 [`delivery/verbatim-check.json`](production/gilgo/delivery/verbatim-check.json) |

## 新片：大卫·史密斯：无罪之后

本分支新增一部按本项目方法制作的英国案件三分钟横版动画：
[`production/davidsmith/抖音脚本.md`](production/davidsmith/抖音脚本.md)（786 字口播、45 镜、38 Agnes + 7 信息卡、字幕/音画同步闸门）和
[`production/davidsmith/README.md`](production/davidsmith/README.md)。案件口径特别区分了二零零三年法律例外、二零二二年准许重审与二零二三年五月定罪，不把“一罪不二审”写成完全废除。

## 发布用

- **题目（三选一）**
  1. 他是模范爸爸，也是连环杀手：30年悬案，栽在一个披萨盒上
  2. 警察跟了他一年半，只为等他扔垃圾｜长岛吉尔戈海滩连环案
  3. 电脑里藏着一份「作案清单」：写于2000年，2026年当庭认罪
- **提问读者一句话**：你觉得，是他太蠢，还是警察太耐心？
- **抖音介绍 + 话题**：[`production/gilgo/抖音发布文案.md`](production/gilgo/抖音发布文案.md)
- **脚本**（三个标题 / 核心爆点 / 四列分镜表：时间轴 · 口播文案 · 画面描述 · 音效备注 / 金句结尾 / 事实边界 / 资料来源）：
  [`production/gilgo/抖音脚本.md`](production/gilgo/抖音脚本.md)

## 案件时间线（片中每一句都有公开来源，见脚本第六节）

| 时间 | 事 |
|---|---|
| 1993 — 2010 | 至少 8 名年轻女性遇害，遗体以麻布包裹弃于长岛海洋公园大道沿线 |
| 2010-12 | 搜寻 Shannan Gilbert 时在吉尔戈海滩发现「吉尔戈四人」 |
| 2022-02 → 03-14 | 萨福克县重组专案组；目击证词里的墨绿色雪佛兰 Avalanche 皮卡查到车主：雷克斯·赫曼 |
| 2022 — 2023 | 门口摄像头监控约一年半；从家门口垃圾里取到 11 个瓶子（妻子毛发对上三名受害者身上的毛发） |
| 2023-01-26 | 跟踪小组在曼哈顿回收他扔掉的披萨盒：披萨边 DNA 与 2010 年麻布上的男性毛发线粒体 DNA 一致（排除 99.96 % 北美人口） |
| 2023-07-13 | 逮捕；搜家 12 天 |
| 2024 | 地下室硬盘里恢复出写于 2000 年的「作案清单」Word 文档（Problems / Supplies / DS / TRG，「small is good」） |
| 2026-04-08 | 当庭认罪：7 项谋杀 + 承认第 8 名受害者 |
| 2026-06-17 | 终身监禁、不得假释 |

事实边界：AI 画面不冒充真实影像；真实人物只以背影、剪影、手出现，受害者不以人像出现；不展示遗体、血腥或侵害过程；
未起诉的事（Shannan Gilbert 之死）不写成结论；中文姓名、日期、字幕一律后期添加。

## 这部片子是怎么做出来的

```
事实核查（13 条公开来源）
  └─ build_story.py：六段解说 785 字 + 45 镜提示词 + 信息卡文案          ← 唯一内容源
       └─ TTS 六段 → tighten_pauses.py（201.7 s → 176.1 s，只剪静音不动字）→ clause_times.py（分句对时间）
            └─ generate.py --validate → GEN_REQUEST → Actions 生成 38 镜（75 秒节流、断点续跑）
                 └─ 三轮复审 qa/ 接触表（16 → 15 → 3 镜重做，只改提示词，按 SHA-256 复用其余）
                      └─ render.py：CUTS 按分句停顿切、信息卡、字幕、混音、成品复测 → RENDER_REQUEST
                           └─ 抽帧复检 → 字幕时间轴修复 → 第二版成片 → VERBATIM_REQUEST 逐字听检 → Release
```

全过程（含每一轮复审改了哪些镜头、为什么）：[`production/gilgo/制作过程.md`](production/gilgo/制作过程.md)。

| 路径（`production/gilgo/`） | 内容 |
|---|---|
| `build_story.py` / `story.json` / `screenplay.md` | 解说词、45 镜分镜、信息卡、事实边界、来源 |
| `audio/` | 六段配音（收紧后）、原始 TTS、SHA-256 收据、分句时间、收紧报告 |
| `results.json` / `qa/` | 38 镜的生成回执与 14 帧接触表 |
| `render.py` / `clause_times.py` / `tighten_pauses.py` / `generate.py` … | 出片引擎（详见目录里的 README） |
| `delivery/` | 技术报告、EDL、字幕时间轴、混音与成品音频实测、逐字听检 |
| `抖音脚本.md` / `抖音发布文案.md` | 交付给发布的脚本与文案（都由 `build_story.py` 生成，和成片同源） |

## 用同一套流程做下一部

```bash
python3 production/new_topic.py --slug <slug> --title "<片名>" --branch <分支>
```

脚手架以 `production/gilgo/` 为参考开出新目录（45 镜 × 4 秒骨架、内容与引擎分离的 `build_story.py` / `render.py` /
`script_table.py`、三份 marker 触发的工作流），然后照 [`新题目开工手册.md`](新题目开工手册.md) 的 10 步走。
参考项目只被读取、不被修改，有测试守着。

## 闸门（任何一道不过都不许出片）

1. `generate.py --validate` —— 时间轴 45×4、提示词非空、配音文本与剧本逐字一致、配音 SHA-256；
2. `clause_times.py --check-cuts` —— 切点落在分句停顿窗内；`render.py::make_edl` —— 每个镜头只用一次、全部用到、EDL 无缝；
3. `render.py` 开头 —— 素材必须是 `results.json` 里 SHA-256 对得上的 Agnes 片段，不用图片/幻灯片顶替；
4. `build_audio.py` —— 整体电平 / 波峰因数 / 静音占比 / **逐段**解说电平；
5. `render.py` 收尾 —— 对**最终 mp4** 复测一遍；
6. `verbatim_check.py`（Actions）—— 成片转写与剧本的字错率逐章 ≤ 0.15。

## 出片方式

本地：`bash production/run_project.sh <slug> [skip_asr] [成片文件名]`。
Actions：在分支上写 marker 文件并 push——`production/<slug>/GEN_REQUEST`（生成）/ `RENDER_REQUEST`（出片）/
`VERBATIM_REQUEST`（听检）/ `RELEASE_UPLOAD_REQUEST`（传 release）。吉尔戈的三条工作流在
[`.github/workflows/gilgo-*.yml`](.github/workflows/)，成片与报告由工作流 commit 回分支。

```bash
python3 -m pip install -r production/requirements.txt   # 另需 ffmpeg 与中文字体（fonts-noto-cjk）
python3 -m pytest production/tests -q                   # 离线自检（2026-09-21：119 passed）
```

## 仓库里还有什么

| 路径 | 内容 |
|---|---|
| [`新题目开工手册.md`](新题目开工手册.md) | 吉尔戈模式的开工手册：10 步 + 踩坑清单 + 文件地图 |
| [`production/new_topic.py`](production/new_topic.py) + [`production/templates/`](production/templates/) | 开新题目的脚手架与模板 |
| [`production/verbatim_check.py`](production/verbatim_check.py) / [`review_film.py`](production/review_film.py) | 逐字听检；黑帧 / 冻结帧 / 电平 / 语速审片初筛 |
| [`production/dahlia/`](production/dahlia/) | 上一部片子《黑色大丽花：消失的六天》（30 镜 × 6 秒、带档案照片）及其[审片记录](production/dahlia/review/)；成片 `交付/黑色大丽花_三分钟_带声音.mp4` |
| [`电影解说工具包/`](电影解说工具包/) | 更早的一套工具；`render.py` 的配乐 `generate_horror_bgm.py` 在这里 |
| [`runner/`](runner/) + [`转私有与自托管Runner手册.md`](转私有与自托管Runner手册.md) | 本地出片机：一键安装注册、自检、卸载；转私有的正确顺序与 `RUNNER_LABEL` 开关 |

### 仓库可见性与 runner（提醒）

- 所有工作流的 `runs-on` 都走 `${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}`：不设变量时用 GitHub-hosted runner
  （私有仓库按 2000 分钟/月计），设了就用自己的机器（不计分钟）。
- **自托管 runner 绝不能挂在公开仓库上**（fork PR 能在你机器上执行任意代码），顺序是**先转私有、再装 runner**。
  2026-09-22 核对 `gh api repos/32r4e2q-hub/desktop-tutorial` → `"private": false`，也就是**现在是公开的**，装 runner 前要先转私有。
- 注册 token 与仓库变量只有仓库主能操作（代理的 GitHub App 缺 `administration` 权限，实测 403）。
- `.github/workflows/` 里的 `commentary-render.yml` / `ci-tests.yml` / `verbatim-check.yml` 必须与 `production/*.workflow.yml`
  逐字节一致，`production/tests/test_workflows.py` 守着（2026-09-09 曾有一次把聊天正文贴进工作流文件的事故）。
