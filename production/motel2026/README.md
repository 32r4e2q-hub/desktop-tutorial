# 汽车旅馆连环命案：金素英为什么带他们去旅馆？（V2 修订版）

三分钟横屏中文悬疑 3D 动画短片：**16:9、1920×1080、24fps、精确 180 秒、30 个镜头**。所有镜头由 Agnes Video 2.5 Flash 生成连续动态画面；一镜一句中文低沉男声旁白，字幕与配音逐镜对齐，并配原创程序合成 BGM 与音效。

> 画面为 AI 3D 动画情景复原，不是新闻影像。人物都是虚构演员形象；手机界面只用抽象线条和图标，不出现可读文字。
>
> 不出现药物名称、药片、剂量或制备细节；不出现尸体、血腥或真实受害者身份。受害者只以背影、剪影与白菊呈现。

## 修订版叙事口径

- 被告为检方依法公开身份的**金素英，案发时 20 岁**；不再以“金某”让人物悬空。
- 三名男性必须清晰区分：2025 年 12 月南杨州事件的是她当时的男友，幸存、分手后报案；2026 年 1 月 28 日和 2 月 9 日在水踰洞汽车旅馆死亡的是两名不同的、近期认识的二十多岁男性，均非其男友，姓名与职业未见可靠公开资料。
- 对“主动提出入住汽车旅馆”“消费利用”“冲突回避或控制”等内容一律归因于警方/检方调查判断；旅馆被解释为约会后进入的封闭私密空间，而不是男性无缘无故进入后死亡。
- “只想让人睡着”“防止不受欢迎的身体接触”是被告辩解；一审法院认定没有相应性侵或强迫迹象，未予采信。
- 结果：2026-08-27 一审无期徒刑、30 年电子定位监管；检方曾求处死刑。被告于 8 月 28 日、检方于 9 月 2 日分别上诉，案件仍在二审中。

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 分镜 / 事实边界 / 提示词 | ✅ 30 镜、180 秒、V2 人物关系与动机口径 | `build_story.py`、`story.json` |
| 文案源与导出 | ✅ 已刷新，573 个可见旁白字符（3.18 字/秒）；每镜有画面锚点 | `revised-narration-v2.json`、`story.json`、`screenplay.md`、`抖音脚本.md` |
| 离线计划自检 | ✅ 15 项通过（含“每镜口播—画面锚点”检查） | `python3 -m unittest production.tests.test_motel2026 -q` |
| V2 旁白 | ✅ 30/30 已以用户选定的低沉男声 `voice-03` 重录并做文本/音频哈希登记；自然语音无过长或过短镜头，最大安全加速 1.0746× | `audio/manifest.json`、`qa/narration-fit-v3.txt` |
| V2 Agnes 素材 | ⏳ 仅重生 S03、S04、S11、S13、S17、S23；其他镜头可复用 | `results.json`、`qa/` |
| V2 成片 / 字幕 / 配音 | ⏳ 待素材和旁白齐备后渲染 | `交付/Motel_Case_Revised_V2.*` |
| 原版交付 | 🔒 保留，不会被 V2 流程覆盖 | `交付/Motel_Case_Final.mp4` 等 |

## 本地计划检查

```bash
python3 production/motel2026/build_story.py
python3 production/motel2026/generate.py --validate --clips-only
python3 -m unittest production.tests.test_motel2026 -q
```

完整渲染前，必须先以用户已选的 Arena 声线重录 `S01–S30.mp3`，并在 `audio/manifest.json` 中写入对应的 `sha256` 与 `audio_text_sha256`；随后运行：

```bash
python3 production/motel2026/narration_fit.py
```

清单完整性闸门会拒绝旧音频或未按当前解说词重新生成的音频，避免将原版旁白误混入修订版。

## GitHub Actions 生产流程

| 触发文件 | V2 作用 |
|---|---|
| `production/motel2026/GEN_REQUEST` | 仅重生改过提示词的片段。建议内容：`{"only":"S03,S04,S11,S13,S17,S23","workers":2}` |
| `production/motel2026/RENDER_REQUEST` | 在 30 条 V2 旁白与所需视频齐全后出片；输出使用独立 V2 文件名 |
| `production/motel2026/QC_REQUEST` | 仅对 V2 成片做容器、冻结、黑帧、音频、字幕和封面检查 |

请求采用 Agnes Video 2.5 Flash、720P 源片、16:9、连续真实运动；创建速率受共享 12 秒闸门限制（每分钟最多五次），最多两个 worker。生成收据保存在 `results.json`，可断点续跑。

## V2 输出命名与旧版保护

V2 发布包统一使用 `Motel_Case_Revised_V2` 前缀：

- `交付/Motel_Case_Revised_V2.mp4`
- `交付/Motel_Case_Revised_V2_Cover.png`
- `交付/Motel_Case_Revised_V2_Subtitles.srt`
- `交付/Motel_Case_Revised_V2_Narration.wav`
- `交付/Motel_Case_Revised_V2_Technical_Report.json`
- `交付/Motel_Case_Revised_V2_Release.md`

因此不会覆盖既有 `Motel_Case_Final.mp4`、`Motel_Cover.png`、`Motel_Subtitles.srt` 或 `Motel_Narration.wav`。第十一期竖版封面仍沿用仓库中的固定 `迷案解码人` 模板，不以自由生成封面替代。

## 规格与安全闸门

- **视频模型**：`agnes-video-2.5-flash`，`size=720P`、`aspect_ratio=16:9`、`mode=text`、`n=1`；后期输出 1920×1080/24fps/180 秒。
- **旁白**：一镜一条独立配音、一镜一条字幕；只可轻微加速（≤1.55×）以避免跨越镜头切点，禁止慢放填时长、禁止截断。
- **字幕**：白色黑边，底部安全区，关键词金色放大。
- **片尾**：S30 黑场与红色警告图标，读取 `presentation` 的 V2 标题、副标题和讨论问题；最后 1 秒静音。
- **封面**：横版工作封面由镜头合成；对外第十一期封面使用固定模板。
- **质检**：检查 1920×1080、24fps、180 秒、4320 帧、H.264/AAC、48kHz 立体声、黑帧、冻结、音频电平、字幕和封面尺寸；语义、人脸与文字伪影仍须人工复核。

## 文件地图

| 路径 | 内容 |
|---|---|
| `revised-narration-v2.json` | V2 的逐镜旁白内容源 |
| `build_story.py` / `story.json` | 唯一生产计划：提示词、角色、30 镜、事实边界、配音清单、发布字段与 V2 交付命名 |
| `解说词修订稿_人物关系与动机补全.md` | 供人工审阅的人物关系与动机口径 |
| `screenplay.md` / `抖音脚本.md` / `抖音发布文案.md` | 从生产计划导出的脚本和发布文案 |
| `audio/manifest.json` | 每镜 TTS 文本、文本哈希、音频哈希及镜头时间轴 |
| `build_audio.py` / `narration_fit.py` | 配音对时、混音、自然语音时长与速度闸门 |
| `generate.py` | Agnes 请求、收据复用、V2 命名交付、断点续跑 |
| `render.py` | 30 镜拼接、字幕、片尾、工作封面与技术报告 |
| `qc.py` | V2 成片质检 |
| `reference/` / `qa/` / `results.json` | 参考图、逐镜接触表及生成收据 |
