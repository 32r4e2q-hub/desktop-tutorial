# 金阁寺纵火案：美，为何被烧成灰

三分钟横屏（16:9 · 1920×1080 · 24fps · 180 秒）中文悬疑 3D 动画短片。
30 个 **Agnes Video 2.5 Flash（720P 源片后期放大到 1080P）** 连续运动镜头，一镜一句中文旁白，
字幕与配音同起止，原创程序合成 BGM 与音效。

> 画面为 AI 动画情景重现，不是历史影像。真实人物一律为风格化形象，非真实肖像。
> 全片不出现自杀、自残的方法与过程，不出现遗体、伤口或血腥；林养贤与其母亲的结局只用空镜、
> 物件与环境表现（S22 只拍到有人赶来，S26 只拍空座位与小布包）。

本目录按 `production/setagaya2000/`（仓库默认出片模板）复用而来：分镜与旁白写在
`build_story.py` 里，`generate.py` 负责 Agnes 生成与断点续跑，`render.py` 出 1080P 成片与封面，
`build_audio.py` 负责旁白对时、原创配乐与混音，`qc.py` 做成片硬闸门。

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 角色与场景定稿参考图 | ✅ 8 张（风格化形象，非真实肖像） | `reference/01–08*.png`、`reference/prompts.md` |
| 分镜 / 事实边界 / 提示词 | ✅ 30 镜、180 秒；生成器自动拼接 STYLE、角色设定与 NEGATIVE | `build_story.py`、`story.json` |
| 一镜一句旁白 | ✅ 30 条（低沉悬疑男声，voice-02；10 条母带按句末停顿切成 30 条） | `audio/manifest.json`、`audio/S**.mp3`、`audio/raw/G**.mp3` |
| 离线自检 | ✅ `python3 -m unittest production.tests.test_kinkakuji1950 -q`（15 项） | `production/tests/` |
| Agnes 2.5 Flash 素材 | ⏳ 见 `results.json` 与 `run.log` | `results.json`、`qa/*.jpg` |
| 成片 / 封面 / 字幕 | ⏳ 出片后见「交付清单」 | `交付/` |
| 第三期系列封面 | ⏳ 用成片真实帧生成 | `交付/金阁寺纵火案_第三期封面.png` |

## 怎么跑

```bash
python3 production/kinkakuji1950/build_story.py                    # 重建 story.json / 清单 / 脚本
python3 production/kinkakuji1950/reference_prompts.py              # 重建定稿参考图提示词
python3 production/kinkakuji1950/split_narration.py                # 10 条母带 → 30 条一镜一句
python3 production/kinkakuji1950/generate.py --validate --clips-only
python3 -m unittest production.tests.test_kinkakuji1950 -q
```

生成与出片在 GitHub Actions（仓库 secret 里已有 `AGNES_API_KEY`）：

| 触发文件 | 作用 |
|---|---|
| `production/kinkakuji1950/GEN_REQUEST` | 生成 30 条 Agnes Video 2.5 Flash 片段（默认先跑 S01 金丝雀，通过后再跑全量） |
| `production/kinkakuji1950/RENDER_REQUEST` | 旁白齐了之后，只做 1080P 出片（拼接 / 字幕 / 混音 / 封面） |
| `production/kinkakuji1950/QC_REQUEST` | 只跑成片质检（容器 / 冻结 / 黑帧 / 音频 / 字幕） |

## 规格

- **模型**：`agnes-video-2.5-flash`，`size=720P`、`aspect_ratio=16:9`、`mode=text`、`n=1`；
  请求形状只有 `model/prompt/seconds/size/aspect_ratio/mode/n/seed` 八个字段，NEGATIVE 写在提示词正文里。
- **节流**：61 秒共享闸门、2 个 worker；「video queue is full」按 61 秒重试。
- **断点续跑**：`results.json` 记 `video_url / task_id / sha256 / bytes / request_hash`，`work/` 不入库。
- **旁白与镜头等长**：先录整段，再按句末停顿切成 30 条；镜头时长取「实测语音 + 0.3 秒」并归一到 180 秒，
  字幕直接取该镜的语音活动区间。全片 575 个有效字，实测平均 3.2 字/秒，30 镜中 29 镜零加速（S30 为 1.13×）。
- **字幕**：白色黑边、底部安全区、关键词金色放大；`五百多年 / 僧人 / 镜湖池 / 林养贤 / 口吃 / 警报器 /
  没有响 / 国宝 / 供词 / 母亲 / 七年 / 1956年 / 1955年 / 重建 / 三岛由纪夫` 等为高亮词。
- **声音**：尺八、筝、低音弦乐、太鼓（只在起火段进入）、梵钟与风铃；音效含风、水波、蝉鸣、木头燃烧、
  水柱与蒸汽、铁轨、法槌。BGM 压在旁白下约 −18dB（实测 −19.9dB），峰值 −1.5dBFS。
- **转场**：1–14 镜樱花花瓣，15–22 镜火星，23 镜之后雾气叠化（0.3 秒）。
- **片尾**：S30 画面渐白，后期叠金色「金阁寺纵火案」与「京都 · 1950 · 美与毁灭」；
  右上角常驻「AI动画情景复原 · 非真实影像」。
- **封面（16:9）**：左侧 S01 的金阁与完美倒影，右侧 S18 的燃烧倒影，中间一条后期绘制的水面分界线；
  主标题「最美的建筑」，副标题「被一个21岁的僧人烧成了灰」。

## 事实边界

- 1950 年 7 月 2 日凌晨三点前后，京都市上京区（今北区）鹿苑寺（通称金阁寺）舍利殿（金阁）起火全烧，
  无人死亡；当时寺内七处火灾报警器在 6 月 30 日因电池失效而不能工作。
- 烧失文物包括足利义满木像、观音菩萨像、阿弥陀如来像与佛教经卷等六件；片中只提到足利义满木像。
- 林养贤（本名林承贤）1929 年 3 月 19 日生于京都府舞鹤市成生，大谷大学学生、鹿苑寺见习僧，事件时 21 岁；
  父亲是僧侣，已因结核去世。
- 当天傍晚他在寺后左大文字山被发现并因放火嫌疑被逮捕，送医后保住性命；片中不表现任何自伤方法与过程。
- 动机方面公开记录有「对美的嫉妒」「想轰动世间」「对寺方的不满」等，前后并不一致；片中只保留「供词前后不一」。
- 其母在京都接受问询后，于返回途中在保津峡附近身亡；片中只用站台、空座位与布包表现。
- 1950 年 12 月 28 日京都地方法院判处有期徒刑七年；狱中结核与精神疾病恶化，后提前获释，
  1956 年 3 月 7 日病死，年仅 26 岁。
- 金阁于 1955 年重建；三岛由纪夫 1956 年出版小说《金阁寺》，片中只提及书名，不复述小说情节。

### 来源

- Japanese Wiki Corpus「金閣寺放火事件」 — https://www.japanesewiki.com/jp/history/%E9%87%91%E9%96%A3%E5%AF%BA%E6%94%BE%E7%81%AB%E4%BA%8B%E4%BB%B6.html
- 百科事典「金閣寺放火事件」（出火时刻、烧失文物、火灾报警器、林养贤生平与身后事） — https://ja.wikid.org/%E9%87%91%E9%96%A3%E5%AF%BA%E6%94%BE%E7%81%AB%E4%BA%8B%E4%BB%B6
- 「今日は何の日：7/2 金閣寺放火事件」（1397 年建立、动机供述、母亲之死与文学作品） — https://note.com/nt_univ/n/n03f12e9e8887
- NHK「アナザーストーリーズ 運命の分岐点 金閣炎上」（2023-10-20）相关记录 — https://plaza.rakuten.co.jp/sinoblog/diary/202111240000/
- 鹿苑寺（金阁寺）公式サイト — https://www.shokoku-ji.jp/kinkakuji/
- 三島由紀夫『金閣寺』（新潮社、1956） — https://www.shinchosha.co.jp/book/105002/

## 文件地图

| 路径 | 内容 |
|---|---|
| `build_story.py` / `story.json` | 唯一内容源：STYLE（写实/示意两套）、NEGATIVE、10 个角色与种子、30 镜提示词、30 条旁白、九段结构、事实边界、字幕高亮、音效设计、发布文案 |
| `screenplay.md` | 完整旁白 + 30 镜分镜表 + 来源 + 事实边界 |
| `reference_prompts.py` / `reference/` | 8 张定稿参考图与自动拼接后的提示词 |
| `split_narration.py` | 10 条配音母带按句末停顿切成 30 条，并输出 `qa/narration-split.json` |
| `audio/` | `manifest.json` + `S01–S30.mp3` + `raw/G01–G10.mp3`（含 sha256 / target_start / target_duration） |
| `generate.py` | Agnes 2.5 Flash 请求、61 秒节流、断点续跑、接触表、`--clips-only` / `--render-only` |
| `render.py` | 30 镜拼接、逐镜字幕、片尾叠加、封面、技术报告 |
| `build_audio.py` | 旁白限速与字幕对时、原创配乐（尺八/筝/太鼓/梵钟）与音效、响度与峰值闸门 |
| `qc.py` | 成片质检：容器 / 冻结 / 黑帧 / 闪烁 / 电平 / 静音 / 字幕时间轴 / 封面尺寸 |
| `throttle.py` | 共享创建节流（≥60 秒） |
| `qa/` / `results.json` | 逐镜接触表、试装表、QC 摘要与生成收据 |
| `workflows/` | 工作流副本（安装到 `.github/workflows/kinkakuji1950-gen.yml`） |
