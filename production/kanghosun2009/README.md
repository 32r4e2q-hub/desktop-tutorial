# 姜浩顺：一滴袖口的血，十名女人

三分钟横版（16:9 · 1920×1080 · 30 fps · 180 秒）中文悬疑解说短片，抖音横屏观看版本。
**画面是写实 3D CGI 动画情景重现（智谱 CogVideoX-Flash 免费档生成的视频镜头，不是图片轮播）。**

案件：二〇〇五至二〇〇九年，韩国京畿道西南部。一场没有报警的火灾（妻子与岳母死亡、约四亿八千万韩元人寿理赔），
之后三十个月里八名女性在公交站、夜路和家门口消失（年龄十九至五十二岁），案子一直没有并案；
最后把线连起来的，是一台自动取款机的摄像头、一辆被烧掉的黑色轿车，和国科搜从夹克袖口检出的一滴血。

- slug：`kanghosun2009`　出片分支：`arena/22fb2ea1-desktop-tutorial`　成片文件名：`姜浩顺_一滴袖口的血，十名女人_三分钟_带声音.mp4`
- 规格：45 镜 = **38 个 CogVideoX 动态镜头 + 7 张信息卡**，每镜只出现一次
- 内容源：用户上传的 40 镜文案稿 `抖音文案/20261012-004930_粘贴的文案_20261012-004930.txt` 为骨架，
  事实按 [`史实核对.md`](史实核对.md) 的 13 条公开来源重写（口径冲突处见该文件第二节）

## 一句话流程

```
用户上传的 40 镜文案稿（抖音文案/20261012-004930_粘贴的文案_20261012-004930.txt）
  └─> build_story.py       唯一内容源：859 字解说 / 45 镜 / 7 张信息卡 / 字幕高亮 / 发布文案
        └─> TTS（voice，用户试听选定）→ tighten_pauses.py → clause_times.py → generate.py --validate  ← 闸门一
              └─> COGVIDEOX_GEN_REQUEST → Actions 跑 CogVideoX-Flash 免费档生成 38 镜 → results.json + qa/ 接触表
                    └─> 复审接触表（露脸 / 畸变 / 伪文字 / 换场 → {"only":"Sxx"} 重做）
                          └─> CUTS 按分句停顿重对 → clause_times.py --check-cuts                          ← 闸门二
                                └─> RENDER_REQUEST → 成片 + delivery/ 报告                             ← 闸门三
                                      └─> VERBATIM_REQUEST（逐字听检）· VISUAL_QC_REQUEST（全帧 QC）
                                            └─> face_cast.py check-frames（露脸闸门）→ 人工语义签收
```

## 本片与模板（`production/hwaseong1986`）的关系

引擎（`render.py` / `build_audio.py` / `generate_cogvideox.py` / QC 工具链）由该项目的
模板移植而来，路径、分支名、片名已全部替换；**内容、分镜、角色谱、来源全部重写**。
生成侧只走智谱 CogVideoX-Flash 免费档（`model_policy.COGVIDEOX_MODEL`），不调用 Agnes、不产生费用。

## 本片规格

| 项 | 值 |
|---|---|
| 成片 | 1920×1080 · 30 fps · 180.0 秒 · 5400 帧 |
| 分镜 | **45 镜 × 4 秒规划网格** = 38 个 CogVideoX-Flash 动态镜头 + 7 张信息卡 + 片尾卡；每镜只出现一次 |
| 解说 | 6 段 · **859 字**（含标点）· voice-00（用户试听选定）· 原始 TTS 165.89s → 收紧静音 163.51s（只剪静音不动字）· 变速比 0.973 |
| 字幕 | 分句字幕，切换点来自 `audio/clause-times.json`（DP 分句对时间，实测 0.00s 对齐）；关键词描黄；字号 60 px |
| 切点 | `CUTS` 由 [`tools/plan_cuts.py`](tools/plan_cuts.py) 按分句停顿自动排出（DP 最小化与 4 秒网格的偏差，每镜 1.8–6.5s）；`clause_times.py --check-cuts` 全绿 |
| 画面风格 | 写实 3D CGI 情景重现：二〇〇五至二〇〇九年的京畿道公寓区、雨夜公交站、警局、国科搜实验室、法庭、江原道山道与农家牛棚；全片常驻「AI动画情景重现 · 非新闻影像」 |
| 露脸 | 5 个虚构匿名角色：C1 姜浩顺（情景重现替身，非本人容貌）/ C2 老刑警 / C3 女鉴定员 / C4 检察官 / C5 法官。每人一条 face token + 一个 seed，**同一角色跨镜头逐字节复用**；首次露脸镜头（S04 / S05 / S12 / S14 / S39）用定妆照做图生视频首帧 |
| 事实依据 | 每条都指到 [`史实核对.md`](史实核对.md) 的来源（13 条公开报道） |
| 生成成本 | 智谱 CogVideoX-Flash 免费档，**零费用**（每约 60 秒一镜，38 镜一轮约 45 分钟） |
| 本地冒烟 | `tools/smoke_render.sh`（38 假镜 + 真实配音）：180.0s / 5400 帧 / 混音 −20.61 dBFS / `caption_alignment: clause-times DP` |

## 内容边界（红线）

- 不展示遗体、血腥或作案过程；作案手法只写到「在车内作案」这一层；现场镜头只出现警戒线、编号标记与勘查背影。
- **不做真实人物的肖像还原**：姜浩顺由虚构匿名角色 C1 扮演，片内标签与片尾卡写明「非本人容貌」；
  受害者全程不给可辨识面容（只有背影、剪影与物件）。
- 不美化犯罪者：不写「天才罪犯」视角，落点是十名受害者与失踪统计的缺口。
- 判决表述：二〇〇九年四月二十二日一审死刑、七月二十三日二审维持、放弃上告后确定；
  韩国自一九九七年十二月三十日起未再执行死刑，他至今仍在首尔拘留所。

## 文件说明

| 文件 | 作用 |
|---|---|
| `build_story.py` | **唯一内容源**（解说词 / 45 镜提示词 / 信息卡 / 片头片尾卡 / 发布文案）；面容 token 用 `{C1}`…`{C5}` 占位符从 `cast.json` 注入 |
| `cast.json` + `cast/*.png` | 角色谱与定妆照（露脸模式）：face token、seed、公开 URL、露脸镜头登记 |
| `story.json` / `screenplay.md` | 时间轴、剧本与逐镜提示词（由 `build_story.py` 写出） |
| `audio/` | 六段配音（`raw/` 原始 → `N0x.mp3` 收紧后）、`clause-times.json`、`manifest.json` |
| `generate_cogvideox.py` | 智谱 CogVideoX-Flash 生成引擎（免费档；SHA-256 收据、断点续跑、定妆照探测、QA 接触表） |
| `render.py` | 剪辑引擎；本片只改 `CUTS`（按分句停顿重对）与 `WINDOWS` / `TIGHTER_CROPS`（看片后的镜头修正） |
| `results.json` / `qa/` | 每个镜头的回执（请求哈希、SHA-256、CDN 地址）与接触表 |
| `delivery/` | 技术报告、EDL、字幕时间轴、混音实测、听检、全帧 QC、人脸接触表 |
| `史实核对.md` | 逐句事实 → 公开来源；来源冲突的处理方式 |
| `抖音脚本.md` / `抖音发布文案.md` | 由 `build_story.py --script / --publish` 生成的发布用文档 |

## 本地命令

```bash
python3 production/kanghosun2009/build_story.py --script    # 生成抖音脚本.md（时间轴取自真实 EDL）
python3 production/face_cast.py check-prompts --project production/kanghosun2009
python3 production/kanghosun2009/generate_cogvideox.py --validate
bash production/run_project.sh kanghosun2009                # 出片（Actions 上由 RENDER_REQUEST 触发）
```
