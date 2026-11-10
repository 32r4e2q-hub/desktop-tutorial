# 汽车旅馆连环命案：AI警告过她

三分钟横屏（16:9 · 1920×1080 · 24fps · 180 秒）中文悬疑 3D 动画短片。
30 个 **Agnes Video 2.5 Flash（720P 源片后期放大到 1080P）** 连续运动镜头，一镜一句中文旁白，
字幕与配音同起止，原创程序合成 BGM 与音效。

> 画面为 AI 3D动画情景重现，不是新闻影像；手机界面为抽象示意，不出现可读文字。
> 不出现药物细节、遗体、血腥；受害者只以背影、剪影与白菊花出现。

## 这是世田谷模板的复用

本目录照 [`production/setagaya2000/模板-如何复用.md`](../setagaya2000/模板-如何复用.md) 复制：
29 镜 → 30 镜，其余引擎（Agnes 2.5 Flash 720P、61 秒节流、断点续跑、一镜一句、只快不慢、
24fps、1080P 出片、QC 硬闸门）原样复用。分支已换为 `arena/4d042fa6-desktop-tutorial`。

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 角色与场景定稿参考图 | ✅ 8 张（风格化形象，非真实肖像） | `reference/01–08*.png` |
| 分镜 / 事实边界 / 提示词 | ✅ 30 镜、180 秒；生成器自动拼接 STYLE、角色设定与 NEGATIVE | `build_story.py`、`story.json` |
| 一镜一句旁白 | ⏳ 待录（悬疑低沉男声，一镜一条 mp3） | `audio/manifest.json`、`audio/S**.mp3` |
| 离线自检 | ✅ `python3 -m unittest production.tests.test_motel2026 -q`（14 项） | `production/tests/` |
| Agnes 2.5 Flash 素材 | ⏳ 生成中（30/30 排队，61 秒节流） | `results.json`、`qa/*.jpg` |
| 成片 / 封面 / 字幕 | ⏳ 待旁白齐后出片 | `交付/Motel_Case_Final.mp4` 等 |

## 怎么跑

```bash
python3 production/motel2026/build_story.py                          # 重建 story.json / 清单 / 脚本
python3 production/motel2026/generate.py --validate --clips-only     # 无配音也能验的分镜闸门
python3 -m unittest production.tests.test_motel2026 -q
```

生成与出片在 GitHub Actions（仓库 secret 里已有 `AGNES_API_KEY`）：

| 触发文件 | 作用 |
|---|---|
| `production/motel2026/GEN_REQUEST` | 生成 30 条 Agnes Video 2.5 Flash 片段（`{"mode":"clips","workers":2}`） |
| `production/motel2026/RENDER_REQUEST` | 旁白齐了之后，只做 1080P 出片（拼接 / 字幕 / 混音 / 封面） |
| `production/motel2026/QC_REQUEST` | 只跑成片质检（容器 / 冻结 / 黑帧 / 音频 / 字幕） |

## 规格

- **模型**：`agnes-video-2.5-flash`，`size=720P`、`aspect_ratio=16:9`、`mode=text`、`n=1`；
  请求形状只有 `model/prompt/seconds/size/aspect_ratio/mode/n/seed` 八个字段，
  NEGATIVE 写在提示词正文里。
- **节流**：61 秒共享闸门、2 个 worker；「video queue is full」按 61 秒重试（满足每分钟最多五次的额度上限）。
- **断点续跑**：`results.json` 记 `video_url / task_id / sha256 / bytes / request_hash`，`work/` 不入库。
- **旁白与镜头等长**：镜头时长服从旁白——先录一整句、量自然语音长度，再在 Agnes 的 4–9 秒档位里挑一个刚好装下它的；
  字幕时间直接取该镜的语音活动区间，所以切点落在句子之间。只加速（≤1.55×），从不慢放填时长、从不截字。
  全片 570 个有效字，平均 3.17 字/秒。S29 为刻意停顿（`short`），其余均在 `fit/ok/needs-speedup` 内。
- **字幕**：白色黑边、底部安全区、关键词金色放大。
- **片尾**：S30 黑场红色警告图标，后期叠金色「汽车旅馆连环命案」与「首尔江北区 · 2025—2026 · AI警告过她」，
  最后 1 秒静音；右上角常驻「AI动画情景复原 · 非真实影像」。
- **封面**：中央手机红色警告图标、四周紫红霓虹旅馆夜景；主标题「AI警告过她」。
- **交付**：`交付/Motel_Case_Final.mp4`、`Motel_Narration.wav`、`Motel_Subtitles.srt`、
  `Motel_Cover.png`，另有仓库命名的成片 / 封面 / 字幕 / 技术报告。

## 事实边界

- 案件一审已判，双方均已上诉；片中一律使用“被判”“检方要求”口径，嫌疑人称“金某”，法院认定写“法院认为”。
- 时间节点：2025年12月第一次；2026年1月28日晚九点半水踰洞汽车旅馆；2月9日十二天后；
  2月11日被捕；2月12日手机取证；2026年3月提起公诉；8月27日一审被判无期徒刑。
- 不出现药物名称、药片、剂量、调配过程；厨房镜头只允许玻璃杯与光影；不出现遗体、血腥；
  受害者只以背影、剪影与白菊花出现；嫌疑人以平静空洞形象呈现，不美化。
- 手机聊天界面一律用抽象线条与图标表示，不出现可读文字；片中文字全部由后期叠加。

## 文件地图

| 路径 | 内容 |
|---|---|
| `build_story.py` / `story.json` | 唯一内容源：STYLE（写实/示意两套）、NEGATIVE、10 个角色与种子、30 镜提示词、30 条旁白、九段结构、事实边界、字幕高亮、音效设计、发布文案 |
| `screenplay.md` | 完整旁白 + 30 镜分镜表 + 来源 + 后期规范 |
| `audio/` | `manifest.json` + `S01–S30.mp3`（一镜一句，含 sha256 / target_start / target_duration） |
| `generate.py` | Agnes 2.5 Flash 请求、61 秒节流、断点续跑、接触表、`--clips-only` / `--render-only` |
| `render.py` | 30 镜拼接、逐镜字幕、片尾叠加、封面、技术报告 |
| `build_audio.py` | 旁白限速与字幕对时、原创配乐与音效、响度/峰值闸门 |
| `qc.py` | 成片质检：容器 / 冻结 / 黑帧 / 闪烁 / 电平 / 静音 / 字幕时间轴 / 封面尺寸 |
| `throttle.py` | 共享创建节流（≥60 秒） |
| `reference/` | 8 张定稿参考图 |
| `qa/` / `results.json` | 逐镜接触表、QC 摘要与生成收据 |
