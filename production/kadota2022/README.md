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

**已重录重渲（2026-11-25），技术验收全部通过，待人工听检与逐镜签收。**

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

**v3（2026-11-25 逻辑澄清版，请用这一版）**
- 成片：https://drive.google.com/file/d/1pRZZdSfSEsAK_cWQ2wqZ95DFOW8Z-i_d/view
- 字幕：https://drive.google.com/file/d/1cvr8Z_ZSID1-8Hf9fgHU8xAPY8pRl-qS/view
- 系列封面（沿用，画面未变）：https://drive.google.com/file/d/1guvTW0nPozhrm94OcEV4v4wYxd_CQJps/view

v2（重录填满镜头，逻辑仍含糊，留档）：
- 成片：https://drive.google.com/file/d/1RdGdTEldWDGP2JudgpVOvLNooOzL2s3I/view
- 字幕：https://drive.google.com/file/d/1e4EJfPMRcTSoYTKnhGFFMjvj-HQu11DH/view
- 系列封面（沿用 v1，画面与 v2 的第 2 秒帧相同）：https://drive.google.com/file/d/1guvTW0nPozhrm94OcEV4v4wYxd_CQJps/view

v1（初版解说，留白偏多，仅留档）：
- 成片：https://drive.google.com/file/d/1P3PMx1igNqZo2pxFIqKx2wCCY97DzhLU/view
- 字幕：https://drive.google.com/file/d/1zQGAkgU1e_KYpjz1viWtkR4XxDUMjrbs/view

**GitHub Release 未完成**：本沙箱对 `uploads.github.com` 全部请求返回 EOF（api.github.com 正常），
空 Release `kadota2022-ep26-final` 已删除，避免留下没有资产的壳。如需 Release 备份，请在有上传通道的环境执行：
`gh release create kadota2022-ep26-final` 并附 `kadota2022-ep26-180s-1080p.mp4 / -cover.png / -subtitles.srt`。

**抖音上传未做**（需人工）。

## 2026-11-25 解说重写与重录

**问题**：初版解说每镜平均留白 1.84 秒，全片 55.2 秒（占 30%）无声。
根因是脚本按 4.1 字/秒估算，实测该音色为 4.77 字/秒，每句少写约 16%。

**改法**：整篇重写（584 → 725 字），按 23–27 字/镜重排，六章各有起承转合。
未采用「缩短镜头」或「放慢语音」，两者都违反项目节奏约束。

**结果**（`check_spoken.py` + 成片实测）：

| 指标 | 改版前 | 改版后 |
|---|---:|---:|
| 平均留白 | 1.84 s | 0.52 s |
| 总留白 | 55.2 s（30%） | 15.7 s（9%） |
| 最大 atempo | 1.36x（S24 曾 1.27x） | **1.023x** |
| 字数 | 584 | 725 |

**同期修掉的三个静默缺陷**

1. `audio/voice.json` 记录 `voice-02`（上一期音色），实际一直用 `voice-03`。
   因 manifest 与 render 都读同一份错的元数据，校验互相印证、一路放行。
2. `target_characters_per_second` 仍是 4.1，正是留白问题的根因，但无任何检查消费它。
3. `qc.py` 默认成片路径写死第 26 期骨架名，成片改名后 QC 步骤恒 failure；
   且 `work/` 被 gitignore，CI 里没有源片，30 镜必然全 missing → 恒 FAIL。
   现改为读 `story.json.film_name`，源片缺席记 skipped 而非硬失败。

**新增工具**：`audio/spoken.json` 记录每条配音实际送给 TTS 的文本，
`check_spoken.py` 与脚本比对 + 校验音频哈希——manifest 的 `text` 字段是从 story 复制的，
永远无法暴露「音频是旧文案」这件事。

## 交付（2026-11-25 版）

- 成片：`交付/门田典子案_她帮着埋了一个女人，三年后，她自己被埋进另一片土里_三分钟_带声音.mp4`
  71,000,518 B / 180.000 s / 4320 帧 / 音轨 180.0 s
- 字幕 30 条，`max_lead_seconds` 0.07，与语音逐条一致
- 音量 mean −23.0 dB / max −4.3 dB
- 视觉 QC：`TECHNICAL_PASS_VISUAL_REVIEW_PENDING`（`hard_failures` 为空）
- 听检：30 章中 4 章 CER 超 0.15，**全部**在干净配音对照组同样超标 → ASR 同音误识，
  中位 CER 0.091（优于初版 0.111）。见 `qa/verbatim-review.json`。
- 人工抽检记录：`qa/MANUAL_VISUAL_REVIEW_2026-11-25.md`（抽检≠签收）

## 2026-11-25 第二轮：解说逻辑澄清

**主创反馈**：听不明白「第一次是谁灭了谁、第二次是不是同一批人」。

**事实**（`FACT_CHECK.md` C 节）：2019 年同住的是石川一代、门田典子、犬饲幸子三人；
2022 年杀害门田的天池由佳理、山下克己**不是**这间屋的人，与 2019 年那批人无关，
只与门田有金钱纠纷。两案唯一切点是门田本人。2019 年谁动手致死，法院**未认定**。

**原解说的四处缺陷**

| 位置 | 问题 |
|---|---|
| S01–S05 | 只说「三个女人」，全片未点名，到 S13 才突然出现「门田」 |
| S08 / S10 | 「她的遗体被装上车」「两个女人被逮捕」主语缺失，听不出是谁 |
| S17 | 「和当时住在车里的山下克己」——既未说明这两人不在同屋，又掺入与案情无关的细节 |
| S26 | 只讲「不安的对称」，未点明两批人是不同的人 |

**改法**：开头点名三人；S08 改「同屋的另外两个女人」；S10 改「石川和门田双双因弃尸被捕」；
S17 改「带走她的**不是同屋的人**」；S26 改「两起案子只隔着一个门田典子，**其余的人不是同一批**」。
全篇 728 字，23–27 字/镜。

**结果**：180.000 s / 71,037,985 B；字幕 30 条 max_lead 0.07；音量 −22.9 / −4.3 dB；
按字幕终点实测留白 19.5 s（11%），平均 0.65 s/镜，最大 1.32 s（S04）；
视觉 QC `TECHNICAL_PASS_VISUAL_REVIEW_PENDING`（hard_failures 空）；
听检 4 章超标，全部在对照组同样超标，中位 CER 0.093。
