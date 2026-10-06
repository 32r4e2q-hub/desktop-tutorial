# 狂犬病疫苗：一百四十年前那场赌局

三分钟横版（16:9）中文科普解说短片 · 抖音 · AI 动画情景重现。
一八八五年七月，一个九岁的阿尔萨斯男孩被带到巴黎；一位不是医生的化学家，
用一套还只在狗身上验证过的办法，在十天里给了他十几针——那是人类第一次把
"暴露后预防"用在人身上。这部片子复盘那场赌局，也讲清它**不能**替代今天的循证医疗。

这个仓库是这部片子的**成片、脚本、发布文案**，以及把它做出来的**整条可复现流水线**
（换题目照 [`新题目开工手册.md`](新题目开工手册.md) 再做一部）。

## 成片

| 项 | 内容 |
|---|---|
| 文件 | [`交付/狂犬病疫苗_一百四十年前那场赌局_三分钟_带声音.mp4`](交付/狂犬病疫苗_一百四十年前那场赌局_三分钟_带声音.mp4)（66 MB · 1920×1080 · 30 fps · 180.0 s） |
| 下载 | [Release rabies1885-v1](https://github.com/32r4e2q-hub/desktop-tutorial/releases/tag/rabies1885-v1) → `rabies1885-vaccine-140-years-ago-3min-1080p.mp4`（与 `交付/` 里的文件字节一致，SHA-256 `f0b224cd1195f5c87413bf398be7c169311fe325ebf45fb74e3e548cb560042b`） |
| 画面 | 45 个镜头 = **38 个 Agnes Video V2.0 动画镜头 + 7 张信息卡 + 片尾卡，每个镜头只出现一次**；全片常驻「AI动画情景重现 · 非新闻影像」标签 |
| 声音 | 六段配音 786 字（TTS → 只剪静音收紧到 160.36 s）+ 原创配乐 + 合成音效；成片实测 RMS −22.15 dBFS · 峰值 −1.52 dBFS · 静音占比 1.1 % |
| 字幕 | 分句字幕、关键词描黄，切换点来自配音分句时间（`audio/clause-times.json`） |
| 听检 | whisper small 逐章字错率 0.02–0.10（上限 0.15），报告 [`delivery/verbatim-check.json`](production/rabies1885/delivery/verbatim-check.json) |
| 全帧 QC | 5400/5400 帧解码；非计划黑帧 0；人脸复核候选 0，报告 [`delivery/visual-qc-summary.json`](production/rabies1885/delivery/visual-qc-summary.json) |

## 发布用

- **题目（三选一）**
  1. 九岁男孩、十几针：巴斯德如何让暴露后预防成为可能
  2. 一八八五年巴黎：一个孩子如何改变狂犬病疫苗史
  3. 从兔脊髓到现代预防：巴斯德那场赌局，不能被浪漫化
- **提问读者一句话**：医学史最该被记住的，是勇气，还是验证勇气的证据？
- **金句**：证据要先于传奇，救治要快于病毒。
- **抖音介绍 + 话题**：[`production/rabies1885/抖音发布文案.md`](production/rabies1885/抖音发布文案.md)
- **脚本**（三个标题 / 核心爆点 / 四列分镜表：时间轴 · 口播文案 · 画面描述 · 音效备注 / 金句结尾 / 事实边界 / 资料来源）：
  [`production/rabies1885/抖音脚本.md`](production/rabies1885/抖音脚本.md)

## 史实核对（片中每一句都有公开来源，见脚本第六节）

| 时间 | 事 |
|---|---|
| 1885-07-06 | 9 岁的约瑟夫·迈斯特（Joseph Meister）从阿尔萨斯被带到巴黎；据记载被一只据报患狂犬病的狗咬了十四处。巴斯德不是执业医生，首针由医生雅克—约瑟夫·格朗谢（Joseph Grancher）执行 |
| 1880 → 1885 | 巴斯德团队先经**兔间连续传代**得到稳定的固定病毒，**再以干燥感染兔脊髓降低毒力**——两步不能倒置 |
| 十天 | 迈斯特接受由弱到强的接种；巴斯德研究所记为十三针、CDC 记为十四剂，计数不一致，成片只写「十天、十几针」 |
| 1886-11 / 1895 | 到 1886 年 11 月约 2500 人接受过这种治疗；巴斯德 1895 年去世时接近两万 |
| 1887 → 1888-11-14 | 募款启动；巴黎巴斯德研究所正式开放 |
| 今天 | 现代暴露后预防由细胞培养疫苗、免疫球蛋白与规范评估组成；潜在暴露后先以肥皂和流动水彻底清洗，再尽快联系当地医生或公共卫生机构 |

事实边界：AI 画面不冒充真实影像；巴斯德、迈斯特、母亲与医生只以背影、剪影或手出现，不生成可识别真实人物的面孔；
不展示遗体、伤口、血腥、实际注射或侵害过程；计数不一致的史实不挑一个当结论；中文姓名、日期、字幕一律后期添加；
本片是历史与公共卫生科普，**不替代医疗建议**。

## 这部片子是怎么做出来的

```
事实核查（8 条公开来源：CDC / 巴斯德研究所 / WHO / NIH）
  └─ build_story.py：六段解说 786 字 + 45 镜提示词 + 信息卡文案          ← 唯一内容源
       └─ TTS 六段 → tighten_pauses.py（只剪静音不动字）→ clause_times.py（分句对时间）
            └─ generate.py --validate → GEN_REQUEST → Actions 生成 38 镜（75 秒节流、断点续跑）
                 └─ 逐镜复审 qa/ 接触表 → {"only":"Sxx"} 重做坏镜头（按 SHA-256 复用其余）
                      └─ render.py：CUTS 按分句停顿切、信息卡（排字自适应缩号）、字幕、混音、成品复测 → RENDER_REQUEST
                           └─ VERBATIM_REQUEST 逐字听检（六章 CER ≤ 0.15）
                                └─ VISUAL_QC_REQUEST 全帧审计 5400/5400 帧 + 候选帧导出
                                     └─ 人工语义复核（逐张看候选帧）→ 修完重跑 →
                                          └─ Release 资产上传
```

全过程（含每一轮复审改了哪些镜头、**片尾卡裁字这个缺陷是怎么被发现和修掉的**）：
[`production/rabies1885/制作过程.md`](production/rabies1885/制作过程.md)。

| 路径（`production/rabies1885/`） | 内容 |
|---|---|
| `build_story.py` / `story.json` / `screenplay.md` | 解说词、45 镜分镜、信息卡、片头/片尾卡、事实边界、来源 |
| `audio/` | 六段配音（收紧后）、原始 TTS、SHA-256 收据、分句时间、收紧报告 |
| `results.json` / `qa/` | 38 镜的生成回执、接触表、`final-frame-review/` 审片证据包 |
| `render.py` / `clause_times.py` / `tighten_pauses.py` / `generate.py` … | 出片引擎（详见目录里的 README） |
| `qc_shots.py` / `audit_frame_distortions.py` / … | 逐镜初筛与成片全帧审计 |
| `delivery/` | 技术报告、EDL、字幕时间轴、混音与成品音频实测、逐字听检、全帧审计、[AI 辅助视觉复核](production/rabies1885/delivery/AI辅助视觉复核-2026-10-06.md) |
| `抖音脚本.md` / `抖音发布文案.md` | 交付给发布的脚本与文案（都由 `build_story.py` 生成，和成片同源） |

## 用同一套流程做下一部

```bash
python3 production/new_topic.py --slug <slug> --title "<片名>" --branch <分支>
```

脚手架以 `production/rabies1885/` 为参考开出新目录（45 镜 × 4 秒骨架、内容与引擎分离的
`build_story.py` / `render.py` / `script_table.py`、检验工具链、四份 marker 触发的工作流：
生成 / 出片 / 听检 / **全帧视觉 QC**），然后照 [`新题目开工手册.md`](新题目开工手册.md) 的 12 步走。
参考项目只被读取、不被修改，有测试守着。

> 2026-10-06 起参考实现从《吉尔戈海滩：披萨盒里的凶手》换成这一部：它是唯一跑通
> "全帧视觉 QC + 卡片排字闸门 + 人工语义签收"的成片，也带着两个真缺陷的修法（片尾卡裁字、S18 取景窗）。
> 更早的参考项目 `production/gilgo/`（吉尔戈模式）与 `production/dahlia/`（30 镜 × 6 秒、带档案照片）
> 仍在仓库里，`production/gilgo/` 的成片与工作流继续可用。

## 闸门（任何一道不过都不许出片）

1. `generate.py --validate` —— 时间轴 45×4、提示词非空、配音文本与剧本逐字一致、配音 SHA-256；
2. `clause_times.py --check-cuts` —— 切点落在分句停顿窗内；`render.py::make_edl` —— 每个镜头只用一次、全部用到、EDL 无缝；
3. `render.py` 开头 —— 素材必须是 `results.json` 里 SHA-256 对得上的 Agnes 片段，不用图片/幻灯片顶替；
4. `build_audio.py` —— 整体电平 / 波峰因数 / 静音占比 / **逐段**解说电平；
5. `render.py` 收尾 —— 对**最终 mp4** 复测一遍；
6. `verbatim_check.py`（Actions）—— 成片转写与剧本的字错率逐章 ≤ 0.15；
7. `test_card_typography.py`（离线自检，**通用**）—— 真画片尾卡与信息卡，左右各 100 px 安全带里不许有字
   （片尾卡问句曾按固定字号排出 2304 px 宽、两端各裁两个字，而当时所有自动闸门都是绿的）；
8. `audit_frame_distortions.py`（Actions）—— 成片 5400/5400 帧解码：黑帧 / 冻结 / 时序突变 / 人脸 / 手部；
   **它是分诊，不是签收**；
9. 人工语义复核 —— 逐张看完候选帧；自动审计量不到的（文字溢出、构图语义）只能人看。

## 出片方式

本地：`bash production/run_project.sh <slug> [skip_asr] [成片文件名]`。
Actions：在分支上写 marker 文件并 push——`production/<slug>/GEN_REQUEST`（生成）/ `RENDER_REQUEST`（出片）/
`VERBATIM_REQUEST`（听检）/ `VISUAL_QC_REQUEST`（全帧 QC）/ `RELEASE_UPLOAD_REQUEST`（传 release）。
本片的四条工作流在 [`.github/workflows/rabies1885-*.yml`](.github/workflows/)，成片与报告由工作流 commit 回分支。

```bash
python3 -m pip install -r production/requirements.txt   # 另需 ffmpeg 与中文字体（fonts-noto-cjk）
python3 -m pytest production/tests -q                   # 离线自检
```

## 仓库里还有什么

| 路径 | 内容 |
|---|---|
| [`新题目开工手册.md`](新题目开工手册.md) | 狂犬病模式的开工手册：12 步 + 闸门表 + 踩坑清单 + 文件地图 |
| [`production/new_topic.py`](production/new_topic.py) + [`production/templates/`](production/templates/) | 开新题目的脚手架与模板（四份工作流模板：生成 / 出片 / 听检 / 全帧 QC） |
| [`production/verbatim_check.py`](production/verbatim_check.py) / [`review_film.py`](production/review_film.py) | 逐字听检；黑帧 / 冻结帧 / 电平 / 语速审片初筛 |
| [`production/gilgo/`](production/gilgo/) | 上一部参考实现《吉尔戈海滩：披萨盒里的凶手》（38+7 镜、手绘 2D 风）及其[制作过程](production/gilgo/制作过程.md)；成片 `交付/吉尔戈海滩_披萨盒里的凶手_三分钟_带声音.mp4` |
| [`production/dahlia/`](production/dahlia/) | 更早的《黑色大丽花：消失的六天》（30 镜 × 6 秒、带档案照片）及其[审片记录](production/dahlia/review/) |
| [`production/dbcooper/`](production/dbcooper/) | 更早的 D.B. 库珀三分钟解说 |
| [`电影解说工具包/`](电影解说工具包/) | 更早的一套工具；`render.py` 的配乐 `generate_horror_bgm.py` 在这里 |
| [`runner/`](runner/) + [`转私有与自托管Runner手册.md`](转私有与自托管Runner手册.md) | 本地出片机：一键安装注册、自检、卸载；转私有的正确顺序与 `RUNNER_LABEL` 开关 |

### 仓库可见性与 runner（提醒）

- 所有工作流的 `runs-on` 都走 `${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}`：不设变量时用 GitHub-hosted runner
  （私有仓库按 2000 分钟/月计），设了就用自己的机器（不计分钟）。
- **自托管 runner 绝不能挂在公开仓库上**（fork PR 能在你机器上执行任意代码），顺序是**先转私有、再装 runner**。
- 注册 token 与仓库变量只有仓库主能操作（代理的 GitHub App 缺 `administration` 权限，实测 403）。
- `.github/workflows/` 里的 `commentary-render.yml` / `ci-tests.yml` / `verbatim-check.yml` 必须与 `production/*.workflow.yml`
  逐字节一致，`production/tests/test_workflows.py` 守着（2026-09-09 曾有一次把聊天正文贴进工作流文件的事故）。
