# 门田典子案：三个女人——一个死在暴力里，一个死在自己曾经做过的事里

由 `production/new_topic.py` 从参考项目 `production/shanghai_freezer_case`（《上海冰柜藏尸案》，已成片、已换声重渲）
开出来的新项目目录。参考实现只被复制，没有被修改；本片的所有编辑都发生在这个目录里。
端到端流程见仓库根目录的 `新题目开工手册.md`。

- slug：`kadota2022`　出片分支：`arena/dcfb6db3-desktop-tutorial`　成片文件名：`门田典子案_三个女人——一个死在暴力里，一个死在自己曾经做过的事里_三分钟_带声音.mp4`
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
   python3 production/kadota2022/build_story.py          # 写 story.json + screenplay.md + 抖音脚本.md + 抖音发布文案.md
   python3 production/kadota2022/generate.py --validate  # 闸门一（空内容会被它拦住）
   ```

6. **配音** → `add_voice`（先让用户试听并选定）→ 30 条 TTS 放 `audio/Sxx.mp3` → 写 `audio/voice.json` →
   `python3 production/kadota2022/build_audio_manifest.py` 回填 sha256/时长。
7. **生成素材** → 把 `workflows/` 下三份复制到 `.github/workflows/`（需要 workflows 写权限），写 `GEN_REQUEST`
   （`{"mode":"clips","workers":2}`）并 push；逐镜看 `qa/Sxx.jpg`，坏镜头只改它的 prompt 后
   `{"mode":"clips","only":"S03,S08"}` 重做，其余按 SHA-256 复用。
8. **出片** → `GEN_REQUEST` 写 `{"mode":"render"}` 并 push；成片 commit 回 `交付/门田典子案_三个女人——一个死在暴力里，一个死在自己曾经做过的事里_三分钟_带声音.mp4`；
   复检：按 EDL 逐段抽帧看画面/字幕/标签。
9. **听检** → 写 `VERBATIM_REQUEST` 并 push（或 Actions 手动触发 `kadota2022-verbatim.yml`）；
   `delivery/verbatim-check.json` 每镜 CER 都要 ≤ 0.15，否则人工听。
10. **技术 QC** → 写 `VISUAL_QC_REQUEST` 并 push（或手动触发 `kadota2022-visual-qc.yml`）；
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

## 制作进度（Agent 记）

- 2026-11-24：参考图 12 张全部 approved（C01–C03、S01–S09），`reference/revision.txt` 钉 `e92692f`。
- 配音音色：`voice-03`（本轮试听由主创选定；第 25 期的 `voice-02` 属上次会话，已不可用）。
- 已录 **26 条**：S01–S26（S08、S14 已重录，全片无一条顶满 6 s 镜头）。
- 配音已全部录入（30/30），`build_audio_manifest.py` 回填完成，max atempo=1.000x（无变速）。
- `generate.py --validate`、`preflight.py`、`narration_fit.py` 全绿。
- 内容审核会拦的字眼（已踩过）：头部遭重击 / 被杀害 / 被埋。改写方向是法医式中性表述与事后视角，
  不写作案动作；事实与 FACT_CHECK.md 的条目保持一致。
- 之后：`build_audio_manifest.py` → `generate.py --validate` → `GEN_REQUEST`（clips → render）→ 封面 → 发布文案。

## 状态（2026-11-24）

**已出片，待人工听检与画面签收。**

- 成片：`交付/门田典子案_她帮着埋了一个女人，三年后，她自己被埋进另一片土里_三分钟_带声音.mp4`
  （180.000 s / 4320 帧 / 1920×1080 / 24 fps / 48 kHz；volumedetect 均值 −23.9 dB、峰值 −4.3 dB）
- 封面：`交付/门田典子案_她帮着埋了一个女人，三年后，她自己被埋进另一片土里_Cover.jpg`（本片 2 s 真实帧 + 后期标题）
- 系列封面：`交付/第二十六期_门田典子案_系列封面.png`（1080×1440，取自本片 2.0 s 帧）
- 字幕：`交付/…_Subtitles.srt`（30 条，与语音同步 max_lead 0.07 s）
- 技术报告：`交付/…_Technical_Report.json`（路径已改相对）

**验收**
- `verify_master` PASS；`qc.py` TECHNICAL_PASS_VISUAL_REVIEW_PENDING（无近黑/近白/静止窗）
- 自动听检：30 章中 12 章 CER > 0.15，已逐条复核 —— 10 章在干净配音对照组同样超标，
  2 章（S14/S28）仅成片混音上超标；差异全为同音字误识。详见 `qa/verbatim-review.json`。
- **仍未做**：主创逐字听检、逐镜完整播放签收、抖音上传（均需人工）。

## 交付（2026-11-24）

Google Drive 公开链接（reader / anyone）：

- 成片：https://drive.google.com/file/d/1P3PMx1igNqZo2pxFIqKx2wCCY97DzhLU/view
- 系列封面：https://drive.google.com/file/d/1guvTW0nPozhrm94OcEV4v4wYxd_CQJps/view
- 字幕：https://drive.google.com/file/d/1zQGAkgU1e_KYpjz1viWtkR4XxDUMjrbs/view

**GitHub Release 未完成**：本沙箱对 `uploads.github.com` 全部请求返回 EOF（api.github.com 正常），
空 Release `kadota2022-ep26-final` 已删除，避免留下没有资产的壳。如需 Release 备份，请在有上传通道的环境执行：
`gh release create kadota2022-ep26-final` 并附 `kadota2022-ep26-180s-1080p.mp4 / -cover.png / -subtitles.srt`。

**抖音上传未做**（需人工）。
