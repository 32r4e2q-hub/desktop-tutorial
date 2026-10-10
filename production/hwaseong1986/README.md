# 李春才：华城连环杀人案，DNA揭开了33年的秘密

由 `production/new_topic.py` 从参考项目 `production/rabies1885`（《狂犬病疫苗：一百四十年前那场赌局》，已成片、已发布）
开出来的新项目目录。参考实现只被复制，没有被修改；本片的所有编辑都发生在这个目录里。
流程细节见仓库根目录的 `新题目开工手册.md`。

- slug：`hwaseong1986`　出片分支：`arena/6f5577f1-desktop-tutorial`　成片文件名：`李春才_华城连环杀人案，DNA揭开了33年的秘密_三分钟_带声音.mp4`
- 规格：1920×1080 / 30 fps / 180 秒；**45 镜 = 38 个 Agnes 动画镜头 + 7 张信息卡（比例可调），每个镜头只出现一次**

## 制作状态（2026-10-10）

| 步骤 | 状态 | 证据 |
|---|---|---|
| 选题与事实核查（10 条公开来源） | 已完成 | `build_story.py` 的 `SOURCES`、`史实核对.md` |
| 解说稿（6 章 794 字） | 已完成 | `story.json` 的 `chapters[].text`，与 `screenplay.md`、`audio/manifest.json` 逐字一致 |
| 分镜（45 镜 = 38 Agnes + 7 信息卡） | 已完成 | `story.json` 的 `shots`，`make_edl` 断言每镜只用一次 |
| 露脸模式（5 角色 / 9 露脸镜 / 5 张定妆照首帧） | 已完成 | `cast.json` + `cast/*.png`，`face_cast.py check-prompts` PASS |
| 配音（voice-00，收紧停顿 162.38s / 窗口 168s） | 已完成 | `audio/N0x.mp3`、`audio/tighten-report.json`、`audio/clause-times.json` |
| 闸门一（计划与配音来源） | 已完成 | `generate.py --validate`：`VALID: 180-second plan; 45 shots; 38 Agnes sources; 7 graphics` |
| 剪辑表 CUTS（按分句停顿重对） | 已完成 | `clause_times.py --check-cuts` 全部落在停顿窗内 |
| 卡片排字闸门（本地 + CI） | 已完成 | `pytest production/tests/test_card_typography.py` 真画卡片量安全带，通过 |
| 本地冒烟测试（假素材跑通整条 render.py） | 已完成 | 46 段 / 180.0s / 5400 帧 / 38 素材 / tempo 0.9666 / RMS −20.63 dBFS |
| 生成 38 个 Agnes 镜头 | 进行中 | `GEN_REQUEST` 已 push；**供应商 2026-10-10 下线了 `agnes-video-v2.0`**，已切到 `agnes-video-2.5-flash` 新接口（素材 720P，成片放大到 1920×1080） |
| 复审（逐镜接触表 + 人眼） | 待办 | `qa/Sxx.jpg` 拉回后开始 |
| 出片（RENDER_REQUEST） | 待办 | 成片回 `交付/`，报告进 `delivery/` |
| 听检（VERBATIM_REQUEST，CER ≤ 0.15） | 待办 | `delivery/verbatim-check.json` |
| 全帧视觉 QC + 人工语义签收 | 待办 | `delivery/frame-distortion-audit.*`、`qa/final-frame-review/` |
| 发布（Release + 抖音脚本/发布文案） | 待办 | `gh release` + `RELEASE_UPLOAD_REQUEST` |

## 剩余步骤（从生成素材开始）

5. **生成素材**（进行中）→ `watch_run.py` 拉回 `results.json` 与 `qa/` 接触表；逐镜初筛跑 `qc_shots.py`
   （黑帧 / 冻结 / 中途换场 / 伪文字 / 人脸 / 手部几何），看完用 `review_app.py` 把要重做的镜头勾成 `REDO.json`。
   免费视频额度 1 次/分钟、两个 worker 共享节流，38 镜排队约 48 分钟。
6. **复审** → 逐镜看 `qa/Sxx.jpg`（14 帧）：画的是不是这一镜的场景、7 秒内有没有换场、有没有脸/可读伪文字/遗体。
   坏镜头只改它的 prompt，`GEN_REQUEST` 写 `{"workers":2,"only":"S03,S08"}` 重做，其余按 SHA-256 复用。
   露脸镜头另外对照 `cast/*.png`：同一角色跨镜必须同一个人。
7. **剪辑表** → 已完成（见上表），若改动配音需重跑 `clause_times.py --check-cuts`。
8. **出片** → 写 `RENDER_REQUEST` 并 push；成片 commit 回 `交付/李春才_华城连环杀人案，DNA揭开了33年的秘密_三分钟_带声音.mp4`，报告在 `delivery/`。
   复检：按 EDL 逐段抽帧看画面/字幕/标签；按分句起点前后 0.25 s 抽帧核对字幕切换。
9. **听检** → 写 `VERBATIM_REQUEST` 并 push；`delivery/verbatim-check.json` 六章 CER 都要 ≤ 0.15。
10. **全帧视觉 QC** → 写 `VISUAL_QC_REQUEST` 并 push；工作流解码成片**每一帧**（5400/5400），
    输出 `delivery/frame-distortion-audit.md`、`visual-qc-summary.json` 与 `qa/final-frame-review/`。
11. **人工语义签收** → 逐张看完候选帧再决定：片尾卡与信息卡**有没有字被画面裁掉**（自动审计不量这个）、
    人脸是不是误检、手部是否畸变、有没有可读伪文字；露脸角色对照 `cast/*.png` 与 `delivery/face-cast/` 接触表。
    确认无问题才动 Release；有问题回对应步骤修完重渲。
12. **发布** → `gh release create <tag>` + 写 `RELEASE_UPLOAD_REQUEST`（tag / src / asset）；
    `build_story.py --script` 生成 `抖音脚本.md`，`build_story.py --publish` 生成 `抖音发布文案.md`。

## 目录

| 路径 | 作用 |
|---|---|
| `build_story.py` | **唯一内容源**：解说词、45 镜、信息卡文案、片头/片尾卡、字幕高亮词、标签、音效事件、发布文案 |
| `story.json` | 分镜计划：45 镜 × 4 秒、6 章 × 30 秒（由 build_story.py 写入，含 `presentation` 块） |
| `screenplay.md` | 解说稿 + 事实边界 + 分镜表 |
| `script_table.py` | 由 story.json + CUTS + 分句时间生成 `抖音脚本.md` / `抖音发布文案.md` |
| `audio/raw/` → `audio/N0x.mp3` | TTS 原始输出 → 收紧停顿后的配音（manifest 的 SHA-256 记的是后者） |
| `audio/manifest.json` / `clause-times.json` / `tighten-report.json` | 配音收据、分句时间、收紧报告 |
| `tighten_pauses.py` / `clause_times.py` | 收紧停顿；分句对时间 + `--check-cuts` |
| `generate.py` | 生成 Agnes 素材（75 秒节流、断点续跑、`--prune-failed`）+ `--validate` 闸门 |
| `fetch_sources.py` / `watch_run.py` | 按 SHA-256 回填素材；从分支拉回 results/qa/delivery |
| `render.py` | 剪辑引擎：CUTS（每镜只用一次，有断言）、信息卡（排字自适应缩号）、字幕（ASR → clause-times → 估算）、混音、成品复测 |
| `build_audio.py` / `align_audio.py` / `media.py` / `throttle.py` | 公共实现（副本） |
| `qc_shots.py` | 逐镜初筛：黑帧 / 冻结 / 中途换场 / 伪文字 / 人脸 / 手部几何 / 色温颗粒 |
| `audit_frame_distortions.py` / `compose_all_frame_sheets.py` / `export_visual_review_candidates.py` / `publish_visual_review_bundle.py` | 成片全帧审计 → 全帧接触表 → 候选帧 → 审片证据写回仓库 |
| `review_app.py` / `progress_app.py` | 本地页面：勾选要重做的镜头（`REDO.json`）；一屏看制作进度 |
| `workflows/` | 四份 marker 触发的工作流（生成 / 出片 / 听检 / 全帧视觉 QC），复制到 `.github/workflows/` 才生效 |
| `GEN_REQUEST` / `RENDER_REQUEST` / `VERBATIM_REQUEST` / `VISUAL_QC_REQUEST` / `RELEASE_UPLOAD_REQUEST` | push 触发工作流的 marker 文件（按需创建） |
| `../run_project.sh` | **所有项目共用**的出片脚本：`bash production/run_project.sh hwaseong1986` |

## 红线（继承自参考项目，不要删）

- AI 画面一律标注「AI动画情景重现 · 非新闻影像」，不冒充真实影像；
- 真实人物只以背影、剪影、手出现，不用 AI 生成的脸冒充本人；受害者不以人像出现；
- 不展示遗体、血腥或侵害过程；未定论的事不写成结论；
- 中文姓名、日期、字幕一律后期添加，不交给视频模型拼写；
- 成片必须实测电平（`--validate` 之后还有 `render.py` 的成品复测），无声不许交付；
- 每个镜头只出现一次，不复用（`render.py` 的 `make_edl` 有断言）；
- **卡片上的一行字不许越出画面**：`render.py` 的 `centered()` 会按 `max_width` 缩号，放不下直接报错。
  狂犬病那部的片尾卡问句曾按固定 96 px 排出 2304 px 宽、两端各裁掉两个字，而三道自动闸门全是绿的
  —— 自动审计只量黑帧、冻结、帧间差异和人脸/手，**从不量文字溢出**。
