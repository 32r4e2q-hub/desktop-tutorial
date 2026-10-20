# 周克华案：逃亡八年，最后四天

三分钟横版（16:9 · 1920×1080 · 30 fps · 180 秒）中文悬疑解说短片，抖音横屏观看版。
**画面是写实 3D CGI 动画情景重现（智谱 CogVideoX-Flash 免费档生成的视频镜头，不是图片轮播）。**
解说配音：悬疑低沉男声。

案件：二〇〇四至二〇一二年，重庆、长沙、南京三地之间，苏湘渝系列持枪抢劫杀人案。
二〇一二年八月十日重庆沙坪坝凤鸣山一家银行储蓄所门前再次发生持枪抢劫，一死两伤；
铁路民警朱彦超在盘查中牺牲。八月十四日清晨六时五十分，周克华在沙坪坝童家桥被民警当场击毙，
系列案件告破。警方公布统计：十起案件、十人死亡、六人受伤。

- slug：`zhoukehua2012`　出片分支：`arena/a2b4456e-desktop-tutorial`
- 成片文件名：`周克华案_逃亡八年，最后四天_三分钟_带声音.mp4`
- 规格：45 镜 = **38 个 CogVideoX 动态镜头 + 7 张信息卡**，每镜只出现一次
- 内容源：用户上传的 30 镜文案稿 `抖音文案/20261020-000310_粘贴的脚本_20261020-000310.txt` 为骨架，
  事实按 [`史实核对.md`](史实核对.md) 的 8 条公开来源重写

## 一句话流程

```
用户上传的 30 镜文案稿
  └─> build_story.py       唯一内容源：六段解说 / 45 镜 / 7 张信息卡 / 字幕高亮 / 发布文案
        └─> TTS（悬疑低沉男声）→ tighten_pauses.py → clause_times.py → generate.py --validate  ← 闸门一
              └─> COGVIDEOX_GEN_REQUEST → Actions 跑 CogVideoX-Flash 免费档生成 38 镜 → results.json + qa/ 接触表
                    └─> 复审接触表（人脸 / 畸变 / 伪文字 / 换场 → {"only":"Sxx"} 重做）
                          └─> CUTS 按分句停顿重对（tools/plan_cuts.py）→ clause_times.py --check-cuts    ← 闸门二
                                └─> RENDER_REQUEST → 成片 + delivery/ 报告                            ← 闸门三
                                      └─> VERBATIM_REQUEST（逐字听检）· VISUAL_QC_REQUEST（全帧 QC）
```

## 内容边界（红线）

- **不做真实人物肖像还原**：周克华全片只以背影、剪影、手、远处轮廓出现，没有一张可辨识的脸；
  办案民警同样只给背影与侧后方。片内常驻「AI动画情景重现 · 非新闻影像」。
- 不展示遗体、血腥与枪击伤害：枪击只用远景、声音、墙面闪光与地面反射表现。
- 受害者不出现可辨识面容与真实姓名：只以空座位、翻扣的相框、白花与聚合数字致意。
- 不提供任何可模仿的作案细节（枪支构造、装弹、踩点、反侦查手法）。
- 不美化、不神化：落点是受害者、牺牲的民警与那些年普通人的恐惧。

## 文件说明

| 文件 | 作用 |
|---|---|
| `build_story.py` | **唯一内容源**（解说词 / 45 镜提示词 / 信息卡 / 片头片尾卡 / 发布文案） |
| `story.json` / `screenplay.md` | 时间轴、剧本与逐镜提示词（由 `build_story.py` 写出） |
| `audio/` | 六段配音（`raw/` 原始 → `N0x.mp3` 收紧后）、`clause-times.json`、`manifest.json` |
| `generate_cogvideox.py` | 智谱 CogVideoX-Flash 生成引擎（免费档；SHA-256 收据、断点续跑、QA 接触表） |
| `render.py` | 剪辑引擎；本片只改 `CUTS`（由 plan_cuts.py 写入）与 `WINDOWS` / `TIGHTER_CROPS` |
| `results.json` / `qa/` | 每个镜头的回执（请求哈希、SHA-256、CDN 地址）与接触表 |
| `delivery/` | 技术报告、EDL、字幕时间轴、混音实测、听检、全帧 QC |
| `史实核对.md` | 逐句事实 → 公开来源；来源冲突的处理方式 |

## 本地命令

```bash
python3 production/zhoukehua2012/build_story.py            # 重写 story.json
python3 production/zhoukehua2012/build_story.py --script   # 重写 抖音脚本.md
python3 production/zhoukehua2012/build_story.py --publish  # 重写 抖音发布文案.md
python3 production/zhoukehua2012/generate.py --validate    # 闸门一
python3 production/zhoukehua2012/generate_cogvideox.py --validate
python3 production/zhoukehua2012/tools/plan_alignment.py   # 按 alignment.json 重写 CUTS
python3 production/zhoukehua2012/tools/render_screenplay.py # 重排 screenplay.md 的解说与分镜
python3 production/zhoukehua2012/clause_times.py --check-cuts
python3 production/zhoukehua2012/tools/check_av_sync.py    # 音画同步闸门（量成片）
bash production/run_project.sh zhoukehua2012               # 出片（Actions 上由 RENDER_REQUEST 触发）
```

### 音画同步是怎么保证的（不是「我按计划排的」）

1. `alignment.json` 逐条写死「这一镜在说什么」——`[镜头号, 分句序号]`，切点从分句起点取，
   `tools/plan_alignment.py` 写成 `render.py` 的 `CUTS`（提前 50 ms，帧对齐后仍在气口里）。
2. `clause_times.py --check-cuts` 核对切点都落在 `[分句起点-0.35s, 分句起点]` 的停顿窗内，
   并把「画面职责 / 口播分句」并排打出来，人眼一眼能看出这镜讲的是不是这件事。
3. `tools/check_av_sync.py` 拿**成片**和**配音原轨**对：每个切点前 100 ms 是否已经静下来、
   每条字幕是否与人声起点对齐（上限 ±0.30 s）、人声在混音里是否比停顿段高出至少 2.5 dB。
   结果写 `delivery/av-sync-report.json`。

## 1301（供应商内容审核拦截）怎么处理

免费档对暴力、武器、真实案件的提示词审核很敏感。命中时接口返回 `1301`（或「敏感内容」），
这是**单镜**故障，不是整批失败。本项目的处理方式（与手册一致）：

1. 引擎捕获 1301 后记 `status=failed`，**跳过这一镜继续生成下一镜**，不让一镜掐掉整批；
2. 从 `results.json` 找出失败的镜头号，读它的提示词，把**触发审核的具体词**改掉
   （枪、血、尸体、追捕、警察制服特写等 → 换成「远景 / 剪影 / 警戒线 / 雨夜街道 / 勘查设备的静物」），
   并把场景整体往「环境与氛围」上挪，不写动作；
3. 用 `{"only":"Sxx"}` 只重投这几镜；同一提示词想真重抽要带 `{"only":"Sxx","force":"Sxx"}`
   （否则会命中旧收据、一镜都不重投）；
4. 若同一镜连续两轮被拦，换构图（俯拍桌面 / 空镜 / 静物）而不是继续换形容词。

## 闸门总表（交付版 SHA `6048abc9…`）

| 闸门 | 结果 |
|---|---|
| 计划 / 配音来源 validate | PASS（45 镜 = 38 动态 + 7 信息卡；六段配音 SHA-256 对得上） |
| 切点 check-cuts | PASS（45/45 落在分句停顿窗内，差 −0.05 s） |
| 出片与混音 | RMS −20.53 dBFS · 峰值 −1.57 · 静音 1.1 %（片尾收黑） |
| 音画同步 `check_av_sync.py` | PASS（44/44 切点在停顿；字幕中位 0.019 s / P95 0.035 s / 最大 0.154 s；对比 13.31 dB） |
| 逐字听检 | PASS（六章 CER 0.042 / 0.130 / 0.077 / 0.064 / 0.080 / 0.000） |
| 全帧 QC | 5400/5400 帧 · 非计划黑帧 0 · 人脸候选 0 · 手部越界 0 |
| 角色脸闸门 | SKIP by design（`cast.json` 声明 `mode=silhouette`，全片不做肖像还原） |
| 人工语义复核 | [AI 辅助复核记录](delivery/AI辅助视觉复核-2026-10-20.md)；发布前请用户本人看片签收 |
| 交付文件 | 68,234,966 B · 180.0 s · 1920×1080 · 30 fps · SHA-256 `6048abc9…` |

全过程与 1301 的实测处理见 [`制作过程.md`](制作过程.md)。
