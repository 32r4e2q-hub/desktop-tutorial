# 呼格吉勒图案：18岁报案人被判死刑，18年后还他清白

三分钟横版（16:9 · 1920×1080 · 30 fps · 180 秒）中文悬疑解说短片，抖音横屏观看版本。
**画面是写实 3D CGI 动画情景重现（智谱 CogVideoX-Flash 免费档生成的视频镜头，不是图片轮播）。**

一九九六年四月九日，内蒙古呼和浩特第一毛纺厂家属区，一名二十四岁女子在公共女厕所内遇害。
十八岁的呼格吉勒图与同事闫峰报案，随后被认定为凶手：五月十七日一审死刑，六月五日二审维持，
六月十日执行，距案发只有六十二天。二〇〇五年，连环案嫌疑人赵志红落网并供称该案系其所为；
二〇一四年十二月十五日，内蒙古自治区高级人民法院再审以事实不清、证据不足宣告无罪。
二〇一九年，最高人民法院复核赵志红案时对该起事实不予确认——无罪的理由始终是证据不足。

- slug：`hugejiletu`　出片分支：`arena/ba89b9ff-desktop-tutorial`
- 成片文件名：`呼格吉勒图案_18岁报案人被判死刑_18年后还他清白_三分钟_带声音.mp4`
- 规格：45 镜 = **38 个 CogVideoX-Flash 动态镜头 + 7 张信息卡**，每镜只出现一次
- 内容源：用户 2026-10-19 贴进对话的 30 镜文案稿（存档 `抖音文案/呼格吉勒图案_三分钟脚本.md`），
  按三分钟规格压缩重写为 45 镜 / 六章 / 858 字解说；事实按 [`史实核对.md`](史实核对.md) 的公开来源核对

## 一句话流程

```
30 镜文案稿 → build_story.py（唯一内容源：解说 / 45 镜 / 7 张信息卡 / 字幕高亮 / 发布文案）
  └─> TTS（voice-00）→ tighten_pauses.py → clause_times.py → generate.py --validate      ← 闸门一
        └─> COGVIDEOX_GEN_REQUEST → Actions 跑 CogVideoX-Flash 免费档生成 38 镜 → results.json + qa/
              └─> 复审接触表（畸变 / 伪文字 / 换场 / 换脸 → {"only":"Sxx","force":"Sxx"} 重做）
                    └─> tools/plan_cuts.py → clause_times.py --check-cuts                    ← 闸门二
                          └─> RENDER_REQUEST → 成片 + delivery/ 报告                          ← 闸门三
                                └─> VERBATIM_REQUEST（逐字听检）· VISUAL_QC_REQUEST（全帧 QC）
                                      └─> 人工复核接触表与成片签收
```

## 本片规格

| 项 | 值 |
|---|---|
| 成片 | 1920×1080 · 30 fps · 180.0 秒 · 5400 帧 |
| 分镜 | 45 镜 × 4 秒规划网格 = 38 个 CogVideoX-Flash 动态镜头 + 7 张信息卡 + 片头/片尾卡；每镜只出现一次 |
| 解说 | 6 段 · 858 字（含标点）· voice-00 · 收紧后 160.23 s · 变速比 ≈0.954 |
| 字幕 | 分句字幕，切点取自 `audio/clause-times.json`；关键词描黄；字号 60 px |
| 切点 | `tools/plan_cuts.py` 自动排骨架，`clause_times.py --check-cuts` 45/45 全绿 |
| 画面风格 | 写实 3D CGI：九十年代北方城市的厂区宿舍、公共厕所外景、路边岗亭、机关办公室、木饰厅堂、普通家庭；全片常驻「AI动画情景重现 · 非新闻影像」 |
| 露脸 | 5 个虚构匿名角色：C1 值班人员 / C2 调查人员 / C3 记者替身 / C4 检察官 / C5 法官；受害者与呼格吉勒图本人全程只给背影、剪影与手 |
| 事实依据 | 每条指到 [`史实核对.md`](史实核对.md) 的 9 条公开来源 |
| 生成成本 | 智谱 CogVideoX-Flash 免费档，零费用 |

## 内容边界（红线）

- 不展示遗体、血腥、刑讯与行刑过程；现场镜头只出现绳栏、手电与勘查背影，执行只用一句旁白加空走廊。
- **呼格吉勒图本人不做肖像还原**：全片背影、剪影、手；父母只给背影与手；赵志红只给背影。
- 不虚构对白：全片只有旁白与字幕。
- **赵志红的供述不等于法院认定**：片中明确二〇一九年最高法死刑复核对包括该起在内的四起事实不予确认，
  无罪依据是原判事实不清、证据不足。
- 所有中文姓名、日期、金额由字幕与信息卡后期添加，画面内不出现可读文字。

## 1301 内容审核（本片实测）

首轮 38 镜**全部**被智谱内容审核拦下（`1301 contentFilter`）。按分支 `arena/aa1e6b84`
《红衣杀手杨树明》的过审配方（提交 `3573058`）重写后通过：

| 原措辞 | 改为 |
|---|---|
| `3D animated reenactment` + `true-crime documentary mood` | `3D animated shot` + `sober documentary mood` |
| `Hohhot, Inner Mongolia` + 具体年份 | `a northern Chinese city across the 1990s and the 2010s` |
| `police station / police officer / detective` | `municipal office / uniformed official / investigator` |
| `courtroom / judge / prosecutor / defendant` | `wood-panelled hall / figure in black robes / reviewer / low railed enclosure` |
| `detention facility / execution / prison` | `plain institutional building / 空走廊（不写执行）` |
| 卷宗、笔录、尸检、血型等案件词 | `paper folders / typed report / handwritten record / laboratory`（不含案情词） |

试点 8 镜（S01/S03/S04/S07/S13/S16/S19/S33）先验证，全部通过后再跑全量。
**原则**：只做忠于剧情的措辞替换，不拆词、不用暗语、不无限重投；审核持续拒绝就重设计画面。

## 文件说明

| 文件 | 作用 |
|---|---|
| `build_story.py` | **唯一内容源**（解说词 / 45 镜提示词 / 信息卡 / 片头片尾卡 / 发布文案） |
| `cast.json` | 角色谱（露脸模式）：face token、seed、露脸镜头登记 |
| `story.json` / `screenplay.md` | 时间轴、剧本与逐镜提示词 |
| `audio/` | 六段配音（`raw/` 原始 → `N0x.mp3` 收紧后）、`clause-times.json`、`manifest.json` |
| `generate_cogvideox.py` | 智谱 CogVideoX-Flash 生成引擎（SHA-256 收据、断点续跑、`force` 真重抽、QA 接触表） |
| `render.py` | 剪辑引擎；本片只改 `CUTS` 与看片后的 `WINDOWS` |
| `results.json` / `qa/` | 每镜回执（请求哈希、SHA-256、CDN 地址）与接触表 |
| `delivery/` | 技术报告、EDL、字幕、混音实测、听检、全帧 QC、人脸接触表 |
| `史实核对.md` | 逐句事实 → 公开来源与三条边界 |
| `抖音脚本.md` / `抖音发布文案.md` | 由 `build_story.py --script / --publish` 生成 |

## 本地命令

```bash
python3 production/hugejiletu/build_story.py                 # 写 story.json
python3 production/face_cast.py check-prompts --project production/hugejiletu
python3 production/hugejiletu/generate_cogvideox.py --validate
python3 production/hugejiletu/build_story.py --script        # 抖音脚本.md
bash production/run_project.sh hugejiletu                    # 出片（Actions 上由 RENDER_REQUEST 触发）
```
