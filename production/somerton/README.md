# 塔玛姆·舒德：索马顿海滩无名男尸

三分钟中文悬疑短片项目：16:9 横屏、1920×1080、30fps、180 秒；29 个 **Agnes Video V2.0 连续运动片段**，不以静态图加推拉代替。

## 当前制作状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 角色与场景定稿参考图 | ✅ 已生成 3 张概念参考图（不是史料/证物照片） | `reference/` |
| 分镜 / 事实边界 / Agnes提示词 | ✅ 29镜、时长连续 180 秒；生成器自动拼接 STYLE、角色设定与 NEGATIVE | `story.json`、`build_story.py` |
| 中文旁白 | ✅ 9 段；用户试听选择的成熟低沉悬疑男声 `voice-00`；SHA-256 已登记 | `audio/N01-N09.mp3`、`audio/manifest.json` |
| 本地规则校验 | ✅ `python3 production/somerton/generate.py --validate` | `generate.py` |
| Agnes视频素材 | ⏳ 待 GitHub Actions 调用 Agnes API；仓库执行环境不能直连该接口 | Actions 工作流见下文 |
| 最终渲染、字幕、配乐、音效、封面 | ⏳ 29镜生成成功后自动执行 | `render.py`、`build_audio.py` |
| 人工逐镜审片 / 成片听检 | ⏳ 初版产出后必须复核，不能把技术解码通过当成视觉签收 | `qa/`、Actions artifact |

> 我在当前仓库没有找到名字为“金大斗案”的项目目录；这里沿用仓库已有的 Agnes cloud-first 出片骨架与成熟制作闸门，内容和镜头均按本次索马顿案件脚本新建，不改动其他作品。

## 先看定稿参考图

1. `reference/01-somerton-man-character.png`：虚构的索马顿男子服装与剪影造型，不是本人肖像。
2. `reference/02-somerton-beach-environment.png`：海堤、台阶、海面与晨雾的 16:9 场景参考。
3. `reference/03-evidence-world.png`：皮箱、橙线、诗集与档案桌的道具色彩参考，不是原始证物。

逝者在所有画面中仅以坐姿剪影、背影或半阴影出现；不出现尸体特写、血腥、伤口。历史画面中的人物穿着和道具按 1940 年代设定；现代DNA实验室仅出现在 2022 年段落。

## 生成与出片

1. 将本分支推送后，在 GitHub Actions 运行 **「塔玛姆·舒德 · Agnes动画生成与三分钟出片」**。
2. 默认输入 `{"workers":2}`；29 镜按 Agnes 创建节流逐条提交，预计至少约 36 分钟（不含模型生成和渲染）。单镜测试可填 `{"only":"S01","workers":1}`；失败后重跑会按请求哈希复用已完成镜头，并续接已保存任务。
3. 工作流要求仓库已配置 `AGNES_API_KEY` secret。密钥仅注入 Actions 环境变量，不写入仓库或日志。
4. 全部素材生成后，工作流会严格校验 29 条 Agnes 收据与 SHA-256，再渲染 180 秒成片：
   - 白字黑边、底部安全区内的逐句字幕；关键词加大并金色高亮；
   - S14 的 `Tamam Shud` 与片尾中文片名由后期准确叠加，不让视频模型拼写；封面另叠加“他是谁?”，影片开场不加额外字卡；
   - 低沉大提琴/弦乐/电子氛围、海浪、钟声、海鸥、车站蒸汽、拨号与低频心跳等原创程序合成音轨；人声下配乐自动压低到约 −18 dB；
   - 由 S01 动态片段抽帧并水平翻转生成封面，男子剪影在右、左侧金色“他是谁?”；
   - 终版实测 1920×1080、30fps、180 秒、48kHz 立体声。
5. 成片、封面、字幕、单镜 Agnes 素材、29 张接触表和技术报告作为 GitHub Actions artifact 下载（保留 7 天）。大视频不提交进 Git。成片默认明确标成“未人工审片初版”。

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
| `generate.py` / `throttle.py` | Agnes V2.0 提示词合成、75秒创建节流、断点续跑、素材收据与解码检查 |
| `render.py` | 29镜拼接、同步字幕、S14文字与片尾叠加、封面、技术报告 |
| `build_audio.py` | 旁白限速与停顿、分句字幕对时、原创音乐/音效合成、响度及峰值闸门 |
| `reference/` | 三张预制参考图 |
| `qa/` / `results.json` | 生成后写入的镜头接触表、Agnes task ID / URL / SHA-256 / 视觉复核状态 |
| `.github/workflows/somerton-gen.yml` | 本分支手动触发的 Agnes + 渲染流水线 |

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
