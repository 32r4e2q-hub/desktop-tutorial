# 名古屋主妇杀害事件：丈夫守着血迹公寓二十六年，终于等来凶手落网

> **状态（2026-11-24）：已出片，等技术签收后交付。**
> 30 镜 Agnes 素材（`results.json` 全部 completed、`reused_existing_asset=false`）、30 条 `voice-02` 旁白、
> 180 秒成片与封面均已生成；`generate.py --validate` / `preflight.py` / `verify_master.py` /
> `narration_fit.py` / `qc.py` 全绿。
>
> - 成片：`交付/名古屋主妇杀害事件_丈夫守着血迹公寓二十六年，终于等来凶手落网_三分钟_带声音.mp4`
>   （180.000 s / 4320 帧 / 1920×1080 / 24 fps / 48 kHz，max_lead 0.02 s，volumedetect 均值 −23.2 dB、峰值 −3.9 dB）
> - 系列封面：`交付/第二十五期_名古屋主妇杀害事件_系列封面.png`（1080×1440，取自本片 4.0 s 门厅帧）
> - 听检：`delivery/verbatim-check.json` 10 镜 CER > 0.15，复核结论见 `qa/verbatim-review.json`——
>   9/10 在「干净配音」对照组同样超标，差异集中在人名/数字/专有名词，属 ASR 误识；
>   30 镜包络互相关 0.947–0.995、中位 0.972，客观证明成片音轨就是各自的旁白。
> - **仍待人工**：主创完整逐字听一遍 + 逐镜完整播放签收（自动采样与包络对齐都不等于听感/画面签收）。

## 流程说明（脚手架保留的原文）

> 注意：下面 1–4 步已经完成（剧本、参考图、角色锚点、事实核查表），5–12 步是出片与验收流程。

流程闸门：`generate.py --validate` 只有等 30 条旁白按新剧本重录、manifest 回填之后才会放行。

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
   python3 production/nagoya1999/build_story.py          # 写 story.json + screenplay.md + 抖音脚本.md + 抖音发布文案.md
   python3 production/nagoya1999/generate.py --validate  # 闸门一（空内容会被它拦住）
   ```

6. **配音** → `add_voice`（先让用户试听并选定）→ 30 条 TTS 放 `audio/Sxx.mp3` → 写 `audio/voice.json` →
   `python3 production/nagoya1999/build_audio_manifest.py` 回填 sha256/时长。
7. **生成素材** → 把 `workflows/` 下三份复制到 `.github/workflows/`（需要 workflows 写权限），写 `GEN_REQUEST`
   （`{"mode":"clips","workers":2}`）并 push；逐镜看 `qa/Sxx.jpg`，坏镜头只改它的 prompt 后
   `{"mode":"clips","only":"S03,S08"}` 重做，其余按 SHA-256 复用。
8. **出片** → `GEN_REQUEST` 写 `{"mode":"render"}` 并 push；成片 commit 回 `交付/名古屋主妇杀害事件_丈夫守着血迹公寓二十六年，终于等来凶手落网_三分钟_带声音.mp4`；
   复检：按 EDL 逐段抽帧看画面/字幕/标签。
9. **听检** → 写 `VERBATIM_REQUEST` 并 push（或 Actions 手动触发 `nagoya1999-verbatim.yml`）；
   `delivery/verbatim-check.json` 每镜 CER 都要 ≤ 0.15，否则人工听。
10. **技术 QC** → 写 `VISUAL_QC_REQUEST` 并 push（或手动触发 `nagoya1999-visual-qc.yml`）；
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
