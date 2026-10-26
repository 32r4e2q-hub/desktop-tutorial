# 塔玛姆·舒德：索马顿海滩无名男尸

三分钟中文悬疑短片项目：16:9 横屏、1920×1080、30fps、180 秒；29 个 **Agnes Video 2.5 Flash 连续运动片段**，源片按 Flash 支持的 720P 请求，再由后期放大至 1080P；不以静态图加推拉代替。

## 当前制作状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 角色与场景定稿参考图 | ✅ 已生成 3 张概念参考图（不是史料/证物照片） | `reference/` |
| 分镜 / 事实边界 / Agnes提示词 | ✅ 29镜、时长连续 180 秒；生成器自动拼接 STYLE、角色设定与 NEGATIVE | `story.json`、`build_story.py` |
| 逐镜中文旁白 | 🟡 正在重配：已选 `voice-01`；29句独立生成，一镜一段旁白与一条同步字幕；自然语速优先，不慢放填满时长 | `audio/S01-S29.mp3`、`audio/manifest.json` |
| 本地规则校验 | ✅ `python3 production/somerton/generate.py --validate` | `generate.py` |
| Agnes视频素材 | 🟡 上次Run #2 已验证 S01（5.184秒、1280×720）；S02 遇到 24 次 503 排队满后停止。现已改为 61 秒无限重试，下一次工作流会复用 S01 并继续其余镜头 | `results.json`、Actions 工作流 |
| 最终渲染、字幕、配乐、音效、封面 | ⏳ 29镜生成成功后自动执行 | `render.py`、`build_audio.py` |
| 人工逐镜审片 / 成片听检 | ⏳ 初版产出后必须复核，不能把技术解码通过当成视觉签收 | `qa/`、Actions artifact |

> 仓库目录与代码检索未找到字面名为“金大斗案”的 Agnes 项目；也没有把 `dbcooper` 擅自当成同一项目。按你明确给出的参数，Somerton 独立采用 61 秒共享创建间隔与无次数上限的临时错误重试。

## 先看定稿参考图

1. `reference/01-somerton-man-character.png`：虚构的索马顿男子服装与剪影造型，不是本人肖像。
2. `reference/02-somerton-beach-environment.png`：海堤、台阶、海面与晨雾的 16:9 场景参考。
3. `reference/03-evidence-world.png`：皮箱、橙线、诗集与档案桌的道具色彩参考，不是原始证物。

逝者在所有画面中仅以坐姿剪影、背影或半阴影出现；不出现尸体特写、血腥、伤口。历史画面中的人物穿着和道具按 1940 年代设定；现代DNA实验室仅出现在 2022 年段落。

## 生成与出片

1. 固定分支上的工作流文件更新会自动运行 S01 canary；若它成功，同一工作流、同一节流器会接着生成其余镜头并渲染成片；若失败则停止并记录原因。之后也可手动运行 **「塔玛姆·舒德 · Agnes动画生成与三分钟出片」**。
2. 手动完整制作的默认输入为 `{"workers":2}`；Agnes 创建请求全局至少间隔 61 秒，29 镜的理论最低请求间隔约 28 分钟（不含模型生成和渲染）。遇到排队满、无可用通道、临时网络/5xx 或 429 时，自动至少等待 61 秒（优先服从更长的 `Retry-After`）再重试，不设重试次数上限；直到该镜创建成功后才进入下一步。请求格式错误、鉴权失败或额度不足等不可重试问题会明确报错，避免无意义空转。完整素材由 SHA-256 断点续跑；单镜测试可填 `{"only":"S01","workers":1}`。
3. 工作流要求仓库已配置 `AGNES_API_KEY` secret。密钥仅注入 Actions 环境变量，不写入仓库或日志。
4. 请求遵循 Agnes 2.5 Flash schema：`model=agnes-video-2.5-flash`、`seconds` 为数字字符串、`size=720P`、`aspect_ratio=16:9`、`mode=text`、`n=1`；负面约束附在提示词内，不发送独立 `negative_prompt` 或宽高/帧率字段。全部素材生成后，工作流严格校验 29 条 Agnes 收据与 SHA-256，再将720P源片放大并渲染为180秒成片：
   - 白字黑边、底部安全区内的逐句字幕；关键词加大并金色高亮；
   - S14 的 `Tamam Shud` 与片尾中文片名由后期准确叠加，不让视频模型拼写；封面另叠加“他是谁?”，影片开场不加额外字卡；
   - 低沉大提琴/弦乐/电子氛围、海浪、钟声、海鸥、车站蒸汽、拨号与低频心跳等原创程序合成音轨；人声下配乐自动压低到约 −18 dB；
   - 由 S01 动态片段抽帧并水平翻转生成封面，男子剪影在右、左侧金色“他是谁?”；
   - 终版实测 1920×1080、30fps、180 秒、48kHz 立体声。
5. 每个 Actions job 在 330 分钟触发内部续跑守卫，为 artifact 与清理留出时间；若仍是可恢复的生成状态，使用 `workflow_dispatch` 自动续跑并复用已完成镜头。单个 GitHub job 的 360 分钟是平台硬上限；鉴权、无效请求等致命状态不会自动盲目重试。
6. 成片、封面、字幕、单镜 Agnes 素材、29 张接触表和技术报告作为 GitHub Actions artifact 下载（保留 7 天）。大视频不提交进 Git。成片默认明确标成“未人工审片初版”。

## 本地校验

```bash
python3 production/somerton/build_story.py
python3 production/somerton/generate.py --validate
python3 -m unittest production.tests.test_somerton -v
```

Agnes 生成与 `render.py` 必须在有 `AGNES_API_KEY`、FFmpeg、Noto CJK 字体、NumPy 和 Pillow 的环境运行；缺少任何素材时拒绝渲染，不会拿参考图或静态占位片顶替视频。

## 文件地图

| 路径 | 内容 |
|---|---|
| `build_story.py` / `story.json` | 唯一内容源：STYLE、NEGATIVE、角色设定、9段旁白、29条镜头提示词、研究事实边界、字幕高亮词和音效设计 |
| `screenplay.md` | 完整旁白、逐镜时间轴、来源与后期规范 |
| `audio/` | 9段用户选定男声 TTS、逐字稿与 SHA-256 清单 |
| `generate.py` / `throttle.py` | Agnes Video 2.5 Flash 720P payload、61秒无限循环重试、断点续跑、素材收据与解码检查 |
| `render.py` | 29镜拼接、同步字幕、S14文字与片尾叠加、封面、技术报告 |
| `build_audio.py` | 旁白限速与停顿、分句字幕对时、原创音乐/音效合成、响度及峰值闸门 |
| `reference/` | 三张预制参考图 |
| `qa/` / `results.json` | 生成后写入的镜头接触表、Agnes task ID / URL / SHA-256 / 视觉复核状态 |
| `.github/workflows/somerton-gen.yml` | 固定分支更新触发 S01 canary，成功后自动继续全片；亦支持手动触发 |

## 事实边界与更新

- 1948 年 12 月 1 日，男子在阿德莱德索马顿海滩被发现；无证件、衣物身份标签被剪除，指纹与牙齿档案没有及时给出身份。
- 1949 年 1 月，火车站寄存处找到一只被认为与男子有关的旧皮箱；橙色线索与衣裤修补处相合。诗集与纸片的文字统一由后期准确叠加。
- 2022 年 Derek Abbott 与 Colleen Fitzpatrick 提出身份为 Carl “Charles” Webb，DNA家谱研究使用的是石膏死亡面模中留存的头发；研究者的高置信度不是法定确认。
- 我在 2026-10-22 复核了公开更新；能找到的最新直接警方状态报道仍是 ABC 于 2026-07-06 的报道：当时警方称调查复杂且仍在进行，尚未提交报告给验尸官。影片将 Webb 身份表述为研究团队判断，不说警方已正式确认；片中结论按该报道时点限定，正式发布前仍应再查南澳警方/验尸官是否有新公告。
- “间谍 / 情杀 / 毒杀后抛尸”仅作为传闻画面，不写成事实。护士与电话号码关联也不作定论。

### 主要公开来源

- [South Australian State Records — ‘But what poison?’ Mystery of the Somerton Man](https://archives.sa.gov.au/finding-information/discover-our-collection/stories-from-the-archive/but-what-poison-mystery-of-the-somerton-man)
- [ABC — Unlocking the secrets of the Somerton Man](https://www.abc.net.au/news/2018-12-01/will-the-mystery-of-the-somerton-man-ever-be-solved/10420794)
- [ABC — Somerton Man identified as Melbourne electrical engineer, researcher says (2022)](https://www.abc.net.au/news/2022-07-26/somerton-man-identified-melbourne-born-engineer-researcher-says/101272182)
- [ABC — Somerton Man Charles Webb's true identity revealed in family photographs and divorce papers (2022)](https://www.abc.net.au/news/2022-11-21/somerton-manfamily-photographs-revealed-/101643524)
- [ABC — SA Police report to coroner into Somerton Man case complete ‘very soon’ (2026-07)](https://www.abc.net.au/news/2026-07-06/sa-police-report-coroner-into-somerton-man-case-very-soon/106869302)
