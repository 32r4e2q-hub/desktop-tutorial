# H·H·霍姆斯：传说里的杀人城堡（第二期）

三分钟横屏（16:9 · 1920×1080）中文悬疑 3D 动画短片 · 30 个镜头 · 一镜一句旁白 ·
「传说 vs 真相」双层画面 · 全部镜头由 Agnes Video 2.5 Flash 生成真实运动片段（720P 源片，
后期放大 1080P · 24fps）。

> 画面为 AI 动画情景复原，不是历史影像；人物一律为风格化形象，不对应任何真人相貌。
> 不出现遗体、伤口、血腥、武器、暴力过程或绞刑场面；孩子只以剪影、背影与遗物出现。

## 状态

| 环节 | 状态 |
|---|---|
| 角色与场景定稿参考图（8 张） | ✅ `reference/01–08*.png` |
| 分镜与旁白（30 镜 / 180 秒） | ✅ `build_story.py` → `story.json` / `screenplay.md` |
| 离线自检（16 项） | ✅ `python3 -m unittest production.tests.test_holmes1893 -q` |
| 计划闸门 | ✅ `python3 production/holmes1893/generate.py --validate` |
| 片段生成 | 🔄 进行中（Agnes 队列限流，按 61 秒闸门断点续跑；进度看 `results.json` 的 `phase` 与 `qa/`） |
| 旁白 S01–S09 | ✅ 已录（悬疑低沉男声 voice-01）；实测语音占比 0.67–1.12×，需加速的镜头 ≤1.12× |
| 旁白 S10–S30 | ⏳ 待录（每轮 TTS 上限 10 条，需分三轮） |
| 出片 / 质检 | ⏳ 见下方 marker 说明 |

## 一镜一句，镜头跟着旁白走（与世田谷模板同一套规矩）

30 条旁白共 575 个有效字（3.19 字/秒），逐镜 5–7 秒：一句话 = 一个镜头 = 一条字幕，
三者同起止。`build_audio.py` 只在必要时轻微加速（≤1.55×），**绝不慢放、绝不截字**，
字幕时间取自语音活动窗口，`qa/narration-fit.md` 逐镜给出占比。

## 双层画面（本期新增）

| 层 | 镜头 | 风格 | 后期标签 |
|---|---|---|---|
| 传说想象 | S09 剖面暗道 / S12 走廊引路 / S13 失踪启事 | 泛黄旧报纸版画（`STYLE_PRINT_PREFIX`） | 左上「传说画面 · 泛黄报纸版画」 |
| 写实 3D | 其余 27 镜 | 1890 年代写实 3D 情景复原 | 左上「史实复原 · 3D情景动画」 |
| 撕裂转场 | S14 | 版画被一双手撕开，露出写实冷色内景 | — |

转场：版画↔版画用 0.35 秒纸张翻页擦除；写实↔写实用 0.3 秒雾气叠化；
进入撕裂镜头用 0.12 秒极短叠化。所有切点仍落在旁白句与句之间。

## 事实边界（片中原句与来源）

- 赫尔曼·韦伯斯特·马吉特 1861-05-16 生于新罕布什尔州吉尔曼顿，1884 年毕业于密歇根大学医学系。
- 1886 年起在芝加哥英格尔伍德经营街角药店，并在对面建起三层大楼（后被称作 World's Fair Hotel）。
- 1894 年与同伙本杰明·皮泰泽尔合谋以一万美元寿险假死骗保；皮泰泽尔身故，三个孩子
  艾丽斯（15）、内莉（11）、霍华德（8）随他辗转多伦多与印第安纳波利斯后失踪。
- 费城侦探弗兰克·盖耶沿铁路追查，在多伦多与印第安纳波利斯查获遗物。
- 1895 年霍姆斯因谋杀皮泰泽尔受审并被判死刑；供述二十七人，其中数人被证实仍然活着。
- 1896-05-07 在费城莫亚门辛监狱被处以绞刑，并要求以水泥封棺、深埋。
- 「两百人」「毒气管」「焚尸炉」属于当时的报纸与后世传说，片中一律用泛黄版画呈现，
  旁白以「传说」限定；现代研究认为可确认的受害者约为九人（含皮泰泽尔与三个孩子）。

来源见 `story.json` 的 `sources`（Wikipedia: H. H. Holmes / Moyamensing Prison / Frank Geyer、
Adam Selzer 2017 年考据、NPR 与芝加哥公共图书馆资料）。

## 运行

```bash
python3 production/holmes1893/build_story.py                      # 唯一内容源 → story.json 等
python3 production/holmes1893/generate.py --validate --clips-only # 计划闸门（无配音也能验）
python3 -m unittest production.tests.test_holmes1893 -q
python3 production/holmes1893/prompts_report.py                   # 提示词与生成记录
```

| marker | payload | 行为 |
|---|---|---|
| `GEN_REQUEST` | `{"mode":"clips","workers":2}` / `{"only":"S22"}` | 生成 720P 片段（默认先跑 S01 金丝雀） |
| `RENDER_REQUEST` | `{"mode":"render","workers":1}` | 1080P 出片（拼接 / 字幕 / 混音 / 封面 / 交付） |
| `QC_REQUEST` | `{"mode":"qc"}` | 只跑成片质检（优先级最高） |

## 交付

`交付/Holmes_Castle_Final.mp4`、`Holmes_Castle_Cover.png`、`Holmes_Castle_Subtitles.srt`、
`Holmes_Castle_Narration.wav`，另有仓库命名的成片 / 封面 / 字幕 / 技术报告。

发布标题：**传说中杀了200人的“杀人城堡”，真相比传说更让人不安**
话题：`#真实事件 #HH霍姆斯 #芝加哥 #杀人城堡 #悬疑 #3D动画 #历史真相`
