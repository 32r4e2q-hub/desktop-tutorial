# 蒙娜丽莎失窃案：一枚左手拇指印

三分钟横版（16:9）抖音悬疑科普动画：1911 年，一个在卢浮宫装过玻璃罩的意大利油漆工，裹着白大褂把《蒙娜丽莎》
带出了大门；他留在玻璃罩上的左手拇指印，警方档案里早就有——只因档案只按右手拇指分类，让他逍遥了 28 个月；
最后揭穿一切的，是白杨木画板背面的卢浮宫印章，和一张谁也伪造不了的裂纹网。

由 `production/new_topic.py` 从参考项目 `production/gilgo`（《吉尔戈海滩：披萨盒里的凶手》）开出来，按
`新题目开工手册.md` 的吉尔戈模式制作；参考实现只被复制、没有被修改。

- 规格：1920×1080 / 30 fps / 180 秒；**45 镜 = 38 个 Agnes Video V2.0 动画镜头 + 7 张信息卡，每镜只用一次，不慢放**
- 配音：voice-00（用户试听选定的男声），六段 875 字（含标点），收紧停顿后 177.59 s，整体变速 1.057×
- 画风：与吉尔戈同一套 STYLE_PREFIX（stylized 2D 手绘 graphic-novel、slate-blue / steel-grey），只换时代与地点
- 成片：`交付/蒙娜丽莎失窃案_一枚左手拇指印_三分钟_带声音.mp4`

## 交付物

| 文件 | 内容 |
|---|---|
| `抖音脚本.md` | 3 个标题 / 一句话核心爆点 / 四列脚本表（时间轴 · 口播文案 · 画面描述 · 音效/备注，由真实切点生成）/ 金句 / 事实边界 / 来源 |
| `抖音发布文案.md` | 标题、抖音介绍、话题、置顶提问 |
| `screenplay.md` | 事实边界（每条标来源编号）+ 六段解说（与配音逐字一致）+ 45 镜分镜表（成片真实时间）+ 信息卡文案 + 18 条来源 |
| `制作过程.md` | 每一步的做法、实测数字、踩过的坑 |
| `qa-review.md` | 38 个 Agnes 镜头的逐镜复审结论与成片用窗 |
| `delivery/` | 出片报告：EDL、配音时间表、字幕时间表、对轨报告、技术报告、逐字听检报告 |

## 目录

| 路径 | 作用 |
|---|---|
| `build_story.py` | **唯一内容源**：解说、分镜与提示词、信息卡、来源、标题/爆点/金句；`--script` / `--publish` 生成抖音文档 |
| `story.json` · `audio/manifest.json` | 由 build_story.py 写出；manifest 里每段配音有文字 + SHA-256 收据 |
| `audio/` | 原始 TTS（raw/）、收紧后的六段、`clause-times.json`（分组 DP 分句时间）、`asr-probe.json`（出片前 ASR 探针） |
| `clause_times.py` | 分句 → 语音块的**分组 DP**（一句可跨多块、多句可共一块）；`--check-cuts` 核对切点都在停顿窗内 |
| `render.py` | 出片：CUTS（按分句起点切）、WINDOWS（每镜用素材哪一段）、字幕（分句 DP 优先，whisper 只做交叉核对） |
| `generate.py` · `media.py` · `clip_qa.py` | runner 上生成 Agnes 素材；每条素材全部 169 帧逐帧体检，`qa/Sxx-dense.jpg` / `-flags.jpg` / `.json` |
| `review_clips.py` | 逐帧数据 × 真实 EDL → 每镜的建议用窗（避开运镜缓入定格与自动事件） |
| `asr_probe.py` | 出片前对配音做无提示转写（small + medium）：吞字 / 多字 / 无声调音节错误率 / 分句起点复核 |
| `film_qa.py` | 成片终检：5400 帧逐帧、切点 vs EDL、正脸、音画同步（波形与包络互相关）、字幕 vs 起音 |
| `screenplay_gen.py` | 从 story.json + 真实 EDL 生成 screenplay.md |
| `workflows/` | `monalisa-{gen,render,verbatim,asr}.yml`（已装到 `.github/workflows/`，marker 文件 push 触发） |

## 复现

```bash
python3 production/monalisa/build_story.py              # story.json + manifest 逐字文本
python3 production/monalisa/tighten_pauses.py           # raw/ → audio/N0x.mp3
python3 production/monalisa/clause_times.py             # audio/clause-times.json（分组 DP）
python3 production/monalisa/clause_times.py --check-cuts
python3 production/monalisa/generate.py --validate      # 三处逐字一致 + 180 秒计划
# runner（marker 文件 push 触发）：
#   production/monalisa/ASR_REQUEST       → audio/asr-probe.json
#   production/monalisa/GEN_REQUEST       {"workers":2} / {"workers":1,"only":"S07,S12"} → 素材 + qa/
#   production/monalisa/RENDER_REQUEST    → 交付/*.mp4 + delivery/
#   production/monalisa/VERBATIM_REQUEST  {"model":"medium"} → delivery/verbatim-check.json
python3 production/monalisa/review_clips.py             # 每镜建议用窗
python3 production/monalisa/film_qa.py --film 交付/蒙娜丽莎失窃案_一枚左手拇指印_三分钟_带声音.mp4 --out work/monalisa/film-qa
python3 production/monalisa/build_story.py --script     # 抖音脚本.md
python3 production/monalisa/build_story.py --publish    # 抖音发布文案.md
python3 -m pytest production/tests -q                   # 离线自检（含 test_monalisa.py）
```
