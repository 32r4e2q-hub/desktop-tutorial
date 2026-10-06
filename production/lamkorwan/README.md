# 雨夜屠夫林过云：一卷菲林里的四条人命

由 `production/new_topic.py` 从参考项目 `production/rabies1885`（《狂犬病疫苗：一百四十年前那场赌局》，已成片、已发布）
开出来的新项目目录。参考实现只被复制，没有被修改；本片的所有编辑都发生在这个目录里。
流程细节见仓库根目录的 `新题目开工手册.md`。

- slug：`lamkorwan`　出片分支：`arena/050152c3-desktop-tutorial`　成片文件名：`雨夜屠夫林过云_一卷菲林里的四条人命_三分钟_带声音.mp4`
- 规格：1920×1080 / 30 fps / 180 秒；**45 镜 = 38 个 Agnes 动画镜头 + 7 张信息卡（比例可调），每个镜头只出现一次**

## 现在还不能出片（故意的）

`generate.py --validate` 现在**会失败**，因为解说词、提示词、配音都是空的。按下面顺序填完，它才会放行。

## 待办清单（狂犬病模式）

1. **事实与红线** → `build_story.py` 的 `SOURCES` / `PRINCIPLES`，`screenplay.md` 的「事实边界」。每句话都要有公开来源。
2. **解说稿** → `build_story.py` 的 `CHAPTERS`：六段合计 ≈ 760–800 字，数字写中文读法，每段末尾留钩子，不写血腥细节。
3. **分镜** → `build_story.py` 的 `SHOTS`（45 个元组）：哪几镜是信息卡（`kind="graphic"`）由你定，信息卡文案写进 `CARDS`；
   提示词先钉死唯一场景、再排除别的场景、最后加 HOLD 句。`TITLE_CARD` / `END_CARD` / `CAPTION_KEYWORDS` /
   `LABEL_OVERRIDES` / `SFX_EVENTS` 也在这里。写完跑：

   ```bash
   python3 production/lamkorwan/build_story.py          # 写 story.json + audio/manifest.json 的逐字文本
   ```

4. **配音** → 试音选定音色 → 六段 TTS 放 `audio/raw/N0x.mp3` → 收紧停顿、对分句时间、填 SHA-256：

   ```bash
   python3 production/lamkorwan/tighten_pauses.py       # raw/ -> audio/N0x.mp3，写 audio/tighten-report.json
   python3 production/lamkorwan/clause_times.py         # 写 audio/clause-times.json
   sha256sum production/lamkorwan/audio/N0*.mp3         # 填进 audio/manifest.json 的 sha256，voice_id 也要填
   python3 production/lamkorwan/generate.py --validate  # 闸门一
   ```

5. **生成素材** → 把 `workflows/` 下四份（`lamkorwan-gen.yml` / `-render.yml` / `-verbatim.yml` / `-visual-qc.yml`）复制到
   `.github/workflows/`（需要 workflows 写权限），然后写 `GEN_REQUEST`（`{"workers":2}`）并 push；
   `watch_run.py` 拉回 `results.json` 与 `qa/` 接触表；逐镜初筛可跑 `qc_shots.py`（黑帧 / 冻结 / 中途换场 /
   伪文字 / 人脸 / 手部几何），看完再用 `review_app.py` 把要重做的镜头勾成 `REDO.json`。
6. **复审** → 逐镜看 `qa/Sxx.jpg`（14 帧）：画的是不是这一镜的场景、7 秒内有没有换场、有没有脸/可读伪文字/遗体。
   坏镜头只改它的 prompt，`GEN_REQUEST` 写 `{"workers":2,"only":"S03,S08"}` 重做，其余按 SHA-256 复用。
7. **剪辑表** → `render.py` 的 `CUTS` 骨架是 4 秒均匀一切，**必须**按 `audio/clause-times.json` 重对
   （切点落在分句起点前 0.15 s 左右），然后：

   ```bash
   python3 production/lamkorwan/clause_times.py --check-cuts   # 每个切点都要在停顿窗内
   ```

8. **出片** → 写 `RENDER_REQUEST` 并 push；成片 commit 回 `交付/雨夜屠夫林过云_一卷菲林里的四条人命_三分钟_带声音.mp4`，报告在 `delivery/`。
   复检：按 EDL 逐段抽帧看画面/字幕/标签；按分句起点前后 0.25 s 抽帧核对字幕切换。
9. **听检** → 写 `VERBATIM_REQUEST` 并 push；`delivery/verbatim-check.json` 六章 CER 都要 ≤ 0.15。
10. **全帧视觉 QC** → 写 `VISUAL_QC_REQUEST` 并 push；工作流解码成片**每一帧**（5400/5400），
    输出 `delivery/frame-distortion-audit.md`、`visual-qc-summary.json` 与 `qa/final-frame-review/`
    （全帧接触表 + 手部动态表 + 原始分辨率候选帧）。自动结果是**分诊**，不是签收。
11. **人工语义签收** → 逐张看完候选帧再决定：片尾卡与信息卡**有没有字被画面裁掉**
    （自动审计不量这个！本部就是在这一步发现片尾卡问句两端缺字的）、人脸是不是误检、
    手部是否畸变、有没有可读伪文字。确认无问题才动 Release；有问题回对应步骤修完重渲。
    卡片排字有闸门守着：`production/tests/test_card_typography.py`（**通用**，自动扫 production/*/，
    有 `presentation.end_card` 的项目都会被真画一遍卡片、量左右 100 px 安全带，不用照抄）。
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
| `../run_project.sh` | **所有项目共用**的出片脚本：`bash production/run_project.sh lamkorwan` |

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
