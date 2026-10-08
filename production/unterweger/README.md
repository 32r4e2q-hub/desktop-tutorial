# 杰克·翁特维格：最成功的一次伪装

三分钟横版（16:9 · 1920×1080 · 30 fps · 180 秒）中文悬疑解说短片，抖音横屏观看版本。
**画面是写实 3D CGI 动画情景重现（Agnes Video V2.0 生成的视频镜头，不是图片轮播、不是幻灯片）。**

案件：一九七四年十二月，奥地利一名十八岁女孩被勒死；凶手在狱中出书成名，被当成「改造成功」的样本，
一九九〇年五月假释。出狱后五个月起，维也纳与格拉茨接连有人失踪；一九九一年他在洛杉矶随警方出勤的同时，
当地又有三名女性遇害。一九九二年二月二十七日他在迈阿密被捕，一九九四年六月九项谋杀罪成立，判决当夜自杀。

本片由仓库根目录的 [`新题目开工手册.md`](../../新题目开工手册.md)（狂犬病模式）跑出来，
参照的上一部片子是同一条流水线最新跑通的 `production/zama2017`（《日本座间九人案》· 分支 `arena/a12ae3fa-desktop-tutorial`），
该项目的露脸模式引擎（`cast.json` 占位符注入 / `shot_seed()` / `--image` 图生视频）已原样移植到本项目。

---

## 用户的三条硬要求，怎么落实的

| 要求 | 落实 |
|---|---|
| 3D 动画（不是图片视频） | 全部 38 个 Agnes 镜头 = 写实 3D CGI 情景重现，7 秒 / 24 fps / 1080p，`render.py` 对 SHA-256 对不上的素材直接拒绝 |
| **人物要丰富，不要都是场景动画** | **六个角色 · 19 个露脸镜头**（上一部座间案是 4 角色 / 8 镜），38 镜里 32 镜画面里有人（含背影与手部），纯空镜只有 6 镜 |
| 脸要固定 | 六个角色各一条 face token（`cast.json` 唯一来源，提示词里逐字节照抄）+ 固定 seed + **6 张定妆照做图生视频首帧**；`face_cast.py` 两道闸门守着 |
| 按上传稿的反转结构 | N01–N03 先让观众相信「改造成功」，新命案第一次出现落在 N03 末尾（约 1 分 30 秒），N04 整章才翻过来 |

## 本片规格

| 项 | 值 |
|---|---|
| 成片 | 1920×1080 · 30 fps · 180.0 秒 · 5400 帧 |
| 分镜 | **45 镜 × 4 秒规划网格** = 38 个 Agnes 写实 3D 镜头 + 7 张信息卡（S02 名片 / S11 第一条人命 / S18 改造成功样本 / S24 假释之后 / S31 并案 / S37 被捕 / S40 判决）；每镜只出现一次 |
| 解说 | 6 段 · **794 字**（含标点）· TTS → `tighten_pauses.py` 收紧停顿 → 可用窗口 168 秒 |
| 配音 | `audio/manifest.json` 的 `voice_id`（用户试听后选定） |
| 字幕 | 分句字幕，切换点来自 `audio/clause-times.json`；关键词描黄；字号 60 px、描边 3.2（承自上一部） |
| 画面风格 | 写实 3D CGI 情景重现：一九七〇至九〇年代的维也纳、格拉茨、洛杉矶、迈阿密；**全片常驻「AI动画情景重现 · 非新闻影像」**，庭审/监狱/警方镜头另有更具体的标签 |
| 露脸 | 6 个虚构匿名角色（作家 / 女记者 / 出版社编辑 / 维也纳刑警 / 洛杉矶女警探 / 夜场女招待），**不做任何真实人物的肖像还原**；受害者不以人像出现 |
| 事实依据 | 每条都指到 [`史实核对.md`](史实核对.md) 的 9 条公开来源 |

## 内容边界（红线）

- 不展示遗体、血腥、性暴力与作案过程；六名已知受害者的行踪只写到「失踪」「在城郊林地被发现」这一层。
- 六名露脸角色全部是 AI 生成的**匿名年代角色**，不是任何真实个人的容貌；受害者不出现。
- 说法冲突处不挑一个当结论：一九七四年被害人遇害的日期（十一日 / 十二日）、被捕部门（美国法警 / 联邦调查局）、
  一九九一年在洛杉矶的确切周数，成片都用不会写错的写法，处理方式见 [`史实核对.md`](史实核对.md)。
- 判决与死亡的表述只用法院认定口径：九项谋杀罪成立（六比二）、终身监禁不得假释、判决当夜自杀。

## 文件说明

| 文件 | 作用 |
|---|---|
| `build_story.py` | **唯一内容源**（解说词 / 45 镜提示词 / 信息卡 / 片头片尾卡 / 发布文案）；面容 token 用 `{C1}`…`{C6}` 占位符从 `cast.json` 注入 |
| `cast.json` + `cast/*.jpg` | 角色谱与六张定妆照：face token、固定 seed、公开 URL、露脸镜头登记 |
| `story.json` / `screenplay.md` | 时间轴、剧本与逐镜提示词（由 `build_story.py` 写出） |
| `audio/` | 六段配音（`raw/` 原始 → `N0x.mp3` 收紧后）、`clause-times.json`、`manifest.json`（逐字文本 + SHA-256） |
| `render.py` | 剪辑引擎；本片只改 `CUTS`（按分句停顿重对）与看片后的 `WINDOWS` / `TIGHTER_CROPS` / `GRADE_OVERRIDES` |
| `results.json` / `qa/` | 每个 Agnes 镜头的回执（请求哈希、SHA-256、CDN 地址）与 14 帧接触表 |
| `delivery/` | 技术报告、EDL、字幕时间轴、混音实测、听检、全帧 QC、人脸接触表与相似度分诊 |
| `史实核对.md` | 逐句事实 → 公开来源；来源冲突的处理方式 |
| `抖音脚本.md` / `抖音发布文案.md` | 由 `build_story.py --script / --publish` 生成（时间轴取自真实 EDL） |

## 出片闭环（本仓库的分支）

四份工作流固定在 `arena/39414314-desktop-tutorial`，由 marker 文件 push 触发：
`GEN_REQUEST` → `RENDER_REQUEST` → `VERBATIM_REQUEST` → `VISUAL_QC_REQUEST`；Release 资产走通用的
`.github/workflows/release-upload.yml`。

```bash
python3 production/unterweger/build_story.py                                    # 内容 → story.json
python3 production/face_cast.py check-prompts --project production/unterweger   # 露脸静态闸门
python3 production/unterweger/generate.py --validate                            # 计划与配音闸门
```

## 待办（按手册往下走）

- [ ] 试音选定音色 → 六段 TTS → 收紧停顿 → 分句时间 → 填 SHA-256
- [ ] `GEN_REQUEST`（38 镜）→ 逐镜复审 → `{"only":"Sxx"}` 重做坏镜头
- [ ] `CUTS` 按分句停顿重对 → `clause_times.py --check-cuts`
- [ ] `RENDER_REQUEST` → 成片 + `delivery/` 报告 → EDL 抽帧复检
- [ ] `VERBATIM_REQUEST`（六章 CER ≤ 0.15）· `VISUAL_QC_REQUEST`（5400/5400 帧）
- [ ] `face_cast.py check-frames`（人脸接触表判决）
- [ ] `gh release` + `RELEASE_UPLOAD_REQUEST` → `build_story.py --script / --publish`
- [ ] 写 `制作过程.md`（每一步对应哪个文件、复审改了哪些镜）
