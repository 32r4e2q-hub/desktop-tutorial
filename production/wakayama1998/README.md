# 和歌山毒咖喱事件：一锅咖喱，四条人命

三分钟横屏（16:9 · 1920×1080 · 24fps · 180 秒）中文悬疑 **3D 动画**短片。
29 个 **Agnes Video 2.5 Flash（720P 源片，后期放大到 1080P）** 连续运动镜头，一镜一句中文旁白，
字幕与配音同起止，原创程序合成 BGM 与音效。流程沿用仓库的「世田谷模式」模板
（[`../setagaya2000/模板-如何复用.md`](../setagaya2000/模板-如何复用.md)）。

> 画面为 AI 动画情景重现，不是历史影像、不是新闻画面、不是警方证物照片。
> 不出现遗体、伤口、血腥、呕吐或受害儿童本人；受害过程用打翻的桌椅、救护车灯光、一双小鞋等间接画面表现。
> 真实人物一律为风格化形象，非真实肖像。案件争议一律中立表述：「法院认定」「检方说」「辩方质疑」。

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 角色与场景定稿 | ✅ 7 张（先程序绘制定稿板，成片后用真实帧替换） | `reference/01–07*.png` |
| 分镜 / 事实边界 / 提示词 | ✅ 29 镜、180 秒；生成器自动拼接 STYLE、角色设定与 NEGATIVE | `build_story.py`、`story.json`、`screenplay.md` |
| 一镜一句旁白 | ✅ 29 条；沉稳磁性男声（voice-00）；10 段录音在句子间切开 | `audio/manifest.json`、`audio/S**.mp3`、`audio/raw/` |
| 离线自检 | ✅ `python3 -m unittest production.tests.test_wakayama1998 -q`（14 项） | `production/tests/` |
| Agnes 2.5 Flash 素材 | ⏳ 生成中（`results.json` 记 video_url / task_id / sha256 / bytes） | `results.json`、`qa/*.jpg` |
| 成片 / 封面 / 字幕 | ⏳ 待 `RENDER_REQUEST` | `交付/` |

## 交付清单（出片后）

- `交付/和歌山毒咖喱事件_一锅咖喱四条人命_三分钟_带声音.mp4` — 1920×1080 · 24fps · 180 秒 · h264 + aac 48k
- `交付/Wakayama_Case_Final.mp4` / `Wakayama_Cover.png` / `Wakayama_Subtitles.srt` / `Wakayama_Narration.wav`
- `交付/和歌山毒咖喱事件_封面.jpg` / `_字幕.srt` / `_技术报告.json`

## 怎么跑

```bash
python3 production/wakayama1998/build_story.py                      # 重建 story.json / 清单 / 脚本
python3 production/wakayama1998/split_narration.py                  # 10 段录音 → 29 条 Sxx.mp3
python3 production/wakayama1998/generate.py --validate              # 结构 + 配音 SHA 闸门
python3 -m unittest production.tests.test_wakayama1998 -q           # 离线自检（14 项）
```

生成与出片在 GitHub Actions 上跑（仓库 secret 里已有 `AGNES_API_KEY`），靠 marker 文件触发：

| 触发文件 | 作用 |
|---|---|
| `production/wakayama1998/GEN_REQUEST` | `{"mode":"clips","workers":2}`：生成 29 条片段（断点续跑） |
| `production/wakayama1998/RENDER_REQUEST` | `{"mode":"render","workers":1}`：拼接 / 字幕 / 混音 / 封面 / 交付 |
| `production/wakayama1998/QC_REQUEST` | `{"mode":"qc"}`：成片质检（容器 / 冻结 / 黑帧 / 音频 / 字幕 / 抽帧） |

> `QC_REQUEST` 优先级最高——想重渲必须先把它删掉。

## 规格

- **模型**：`agnes-video-2.5-flash`，`size=720P`、`aspect_ratio=16:9`、`mode=text`、`n=1`；
  请求形状只有 `model/prompt/seconds/size/aspect_ratio/mode/n/seed` 八个字段，NEGATIVE 写在提示词正文里。
- **节流**：61 秒共享闸门、2 个 worker；「video queue is full」按 61 秒重试。
- **旁白与镜头等长**：镜头时长服从旁白——先写整句、再录音、量自然语音长度，落在 Agnes 的 4–9 秒档位里；
  字幕时间取该镜语音活动区间。全片 557 个有效字，平均 3.09 字/秒（实测 2.8–3.4）。
- **字幕**：白色黑边、底部安全区、关键词金色放大（`presentation.highlight_keywords` 共 58 个词）。
- **转场**：同段内硬切；段与段之间 0.3 秒淡入淡出——前半段收在红灯笼暖光里，后半段收在冷蓝雾气里。
- **音量**：BGM 实时侧链压在旁白下约 −18dB；全片 RMS ≈ −21 dBFS、峰值 ≈ −1.5 dBFS；最后一秒静音。
- **片尾**：S29 狱中小窗与白花，后期叠金色「和歌山毒咖喱事件」+「和歌山 · 1998 · 至今争议」+ 提问
  「你觉得，凶手是她吗？」
- **封面**：左侧 S02 大锅、右侧 S14 警戒线与灯笼，金色「一锅咖喱」+「四条人命，直到今天还在争」。

## 九段结构

| 段 | 时间 | 镜头 | 内容 |
|---|---|---|---|
| N01 黄金 3 秒钩子 | 0:00–0:10 | S01–S02 | 夏祭红灯笼航拍 → 车库大锅特写，「一锅咖喱，让四个人再也没有回家」 |
| N02 祭典 | 0:10–0:35 | S03–S06 | 主妇煮咖喱、居民排队、母亲喂孩子、夕阳与云影 |
| N03 突变 | 0:35–1:00 | S07–S10 | 老人放下勺子、人群蹲下、救护车、医院走廊 |
| N04 砒霜 | 1:00–1:25 | S11–S14 | 一双小鞋、实验室曲线飙升、毒瓶示意、警戒线 |
| N05 谁靠近过那口锅 | 1:25–1:50 | S15–S18 | 白板与时间线、泛黄回忆、红线连到名字、街坊偷看 |
| N06 家中的砒霜与保险单 | 1:50–2:15 | S19–S22 | 林家客厅、柜子里的白色粉末、保单与红线、两条重合的曲线 |
| N07 水管与逮捕 | 2:15–2:35 | S23–S25 | 记者围门、水管喷水、全国电视、回头看的一眼 |
| N08 判决与争议 | 2:35–2:52 | S26–S28 | 法庭、天平、最高法院与红印 |
| N09 余音 | 2:52–3:00 | S29 | 狱中小窗的白花 → 片名卡与提问 |

## 事实边界（摘要，全文见 `史实核对.md` 与 `screenplay.md`）

- 1998-07-25 傍晚，和歌山市园部第 14 自治会夏祭，咖喱被混入亚砷酸（砒霜）：67 人中毒，4 人死亡
  （自治会长 64 岁、副会长 53 岁、小学四年级男生 10 岁、高一女生 16 岁）。
- 1998-10-04 林真须美与丈夫因保险金诈骗嫌疑被捕；12-09 因本案再逮捕；2002-12-11 和歌山地裁死刑；
  2005-06-28 大阪高裁维持；2009-04-21 最高裁驳回上告、同年 5 月死刑确定。
- 确定判决依据：家中同种亚砷酸、毛发检出砷、单独看管锅的机会与目击证词；**动机未查明**。
- 辩方质疑鉴定方法与证词；第 2 次再审请求 2025-11-11 被最高裁驳回；第 3 次再审请求（2024-02）审理中。
- 她一贯主张无罪，死刑未执行。片中不下结论。

## 文件地图

| 路径 | 内容 |
|---|---|
| `build_story.py` / `story.json` / `screenplay.md` | 唯一内容源：STYLE（写实/示意两套）、NEGATIVE、10 个角色与种子、29 镜提示词、29 条旁白、九段结构、来源、字幕高亮、音效设计、发布文案 |
| `audio/` | `manifest.json` + `S01–S29.mp3`（一镜一句）+ `raw/C01–C10.mp3`（10 段原始录音） |
| `split_narration.py` | 把 10 段录音按句子间的静音切成 29 条（动态规划对齐字数与语速） |
| `generate.py` | Agnes 2.5 Flash 请求、61 秒节流、断点续跑、接触表、`--validate` / `--clips-only` / `--render-only` |
| `render.py` | 24fps 合成、ASS 字幕、片尾卡、封面、技术报告 |
| `build_audio.py` | 旁白限速与字幕对时、原创配乐（祭典太鼓/笛 → 低音弦乐 → 悬疑钢琴 → 大提琴）与音效、响度闸门 |
| `qc.py` / `narration_fit.py` | 成片质检；解说词与片段等长度量 |
| `make_reference_boards.py` / `refresh_reference_frames.py` | 定稿板程序绘制；成片后用真实帧替换 |
| `reference/` | 7 张角色与场景定稿 |
| `史实核对.md` | 逐条事实与来源、争议表述规范、不写不拍的清单 |
| `抖音脚本.md` / `抖音发布文案.md` | 发布用脚本与文案（由 `build_story.py` 生成） |
