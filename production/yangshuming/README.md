# 红衣杀手杨树明：14年，9名女性遇害，警方如何撕开他的伪装？

三分钟横版（16:9 · 1920×1080 · 30 fps · 180 秒）中文悬疑解说短片，抖音横屏观看版本。
**画面是写实 3D CGI 动画情景重现（智谱 CogVideoX-Flash 免费档生成的视频镜头，不是图片轮播）。**

案件：一九九二年起，山西阳泉矿区马家坪一带接连发生针对女性的袭击，十四年间十二起案件、
九死三伤，媒体称之为「红衣杀手」。二〇〇五年警方重组专案力量并案比对，二〇〇六年三月起
对重点对象展开核查（询问、比对资料、心理测试），四月案件告破；同年八月十日一审判决死刑，
十一月二十一日被执行死刑。

- slug：`yangshuming`　出片分支：`arena/aa1e6b84-desktop-tutorial`　成片文件名：`红衣杀手杨树明_14年，9名女性遇害，警方如何撕开他的伪装？_三分钟_带声音.mp4`
- 规格：45 镜 = **38 个 CogVideoX 动态镜头 + 7 张信息卡**，每镜只出现一次
- 内容源：用户上传的 30 镜文案稿 `抖音文案/20261018-005748_粘贴的文案_20261018-005748.txt` 为骨架
  （原稿 1642 字口播超出 180 秒容量，按模板六章结构压缩到 788 字，剧情骨架与关键事实全部保留），
  事实按 [`史实核对.md`](史实核对.md) 的 7 条公开来源核对（口径冲突处见该文件第三节）

## 当前交付：严格畸变修订版（2026-10-18）

- **新版已出片并复检**：重做 S14/S26/S28，修剪 S06/S41 的模型内溶解串镜；旧版宽松接受结论已撤销。
- 成片 SHA-256：`222e92833da8d536b799dbaaebcaa09d00055c664a1e7c0bd732b4ae42d78817`，62,248,094 字节。
- 新版全帧分析 5400/5400、非计划黑帧 0、PTS 异常 0；六章 ASR 重新比对均 ok。
- 46 条剪辑时序、字幕、解说不变；前后成片解码 PCM 音轨哈希完全一致。
- 复核范围与保留限制见 [`delivery/STRICT_REVIEW.md`](delivery/STRICT_REVIEW.md)，回归证据见 `delivery/strict-revision-regression.json`。

## 一句话流程

```
用户上传的 30 镜文案稿（抖音文案/20261018-005748_粘贴的文案_20261018-005748.txt）
  └─> build_story.py       唯一内容源：解说词 / 45 镜 / 7 张信息卡 / 字幕高亮 / 发布文案
        └─> TTS（voice-00）→ tighten_pauses.py → clause_times.py → generate.py --validate  ← 闸门一
              └─> COGVIDEOX_GEN_REQUEST → Actions 跑 CogVideoX-Flash 免费档生成 38 镜 → results.json + qa/ 接触表
                    └─> 复审接触表（露脸 / 畸变 / 伪文字 / 换场 → {"only":"Sxx"} 重做）
                          └─> CUTS 按分句停顿重对（tools/plan_cuts.py）→ clause_times.py --check-cuts      ← 闸门二
                                └─> RENDER_REQUEST → 成片 + delivery/ 报告                               ← 闸门三
                                      └─> VERBATIM_REQUEST（逐字听检）· VISUAL_QC_REQUEST（全帧 QC）
                                            └─> face_cast.py check-frames（露脸闸门）→ 人工语义签收
```

## 本片与模板（`production/kitakyushu2002` 北九州）的关系

引擎（`render.py` / `build_audio.py` / `generate_cogvideox.py` / QC 工具链）由北九州模板整套移植，
路径、分支名、片名已全部替换；**内容、分镜、角色谱、来源全部重写**。
生成侧只走智谱 CogVideoX-Flash 免费档（`model_policy.COGVIDEOX_MODEL`，仓库 secret
`ZHIPUAI_API_KEY`），不调 Agnes、不产生费用。

## 本片规格

| 项 | 值 |
|---|---|
| 成片 | 1920×1080 · 30 fps · 180.0 秒 · 5400 帧（目标） |
| 分镜 | **45 镜 × 4 秒规划网格** = 38 个 CogVideoX-Flash 动态镜头 + 7 张信息卡；每镜只出现一次 |
| 解说 | 6 段 · 788 字（含标点）· voice-00 · 原始 183.3s → 收紧静音 170.4s · 变速比 1.014 |
| 字幕 | 分句字幕，切换点来自 `audio/clause-times.json`（DP 分句对时间）；关键词描黄；字号 60 px |
| 画面风格 | 写实 3D CGI 情景重现：一九九二—二〇〇六年的山西阳泉矿区、马家坪街巷、警务办公室、法庭；全片常驻「AI动画情景重现 · 非新闻影像」 |
| 露脸 | 3 个虚构匿名角色：C1 杨树明（情景重现替身，非本人容貌）/ C2 老刑警 / C3 法官。每人一条 face token + 一个 seed，**同一角色跨镜头逐字节复用**；九名受害者全程只以物件、空椅、聚合数字出现 |
| 事实依据 | 每条都指到 [`史实核对.md`](史实核对.md) 的来源（新华社 / 人民公安报 / 山西晚报 / 公开报道） |
| 生成成本 | 智谱 CogVideoX-Flash 免费档，**零费用** |

## 内容边界（红线）

- 不展示遗体、血腥或作案过程：袭击只通过警戒线、勘查标记、背影与物件暗示。
- **不做真实人物的肖像还原**：杨树明由虚构匿名角色 C1 扮演，片内标签写明「非本人容貌」；
  受害者全程不给可辨识面容、不写真实姓名（只有物件、空椅与信息卡致意）。
- 测谎只写作侦查措施之一，不当作定罪依据；不编造真实人物对白、供述词与庭审原声。
- 不美化犯罪者：落点是九名受害者与「对旧线索的不放弃」。
- 来源冲突（首案受害者年龄、末案日期）用「不会写错的写法」，见 `史实核对.md` 第三节。

## 文件说明

| 文件 | 作用 |
|---|---|
| `build_story.py` | **唯一内容源**（解说词 / 45 镜提示词 / 信息卡 / 片头片尾卡 / 发布文案）；面容 token 用 `{C1}`…`{C3}` 占位符从 `cast.json` 注入 |
| `cast.json` | 角色谱（露脸模式）：face token、seed、露脸镜头登记 |
| `story.json` / `audio/` | 时间轴、配音收据（manifest 含 SHA-256）、分句时间 |
| `generate_cogvideox.py` | 智谱 CogVideoX-Flash 生成引擎（免费档；SHA-256 收据、断点续跑、force 重投、QA 接触表） |
| `render.py` | 剪辑引擎；本片的 `CUTS` 由 `tools/plan_cuts.py` 排骨架后按分句精排，`WINDOWS`/`TIGHTER_CROPS` 为看片后修正 |
| `史实核对.md` | 逐句事实 → 公开来源；来源冲突的处理方式 |

## 本地命令

```bash
python3 production/yangshuming/build_story.py --script    # 生成抖音脚本.md
python3 production/face_cast.py check-prompts --project production/yangshuming
python3 production/yangshuming/generate_cogvideox.py --validate
bash production/run_project.sh yangshuming                # 出片（Actions 上由 RENDER_REQUEST 触发）
```
