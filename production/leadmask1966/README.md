# 铅面具事件：山顶上的神秘字条

三分钟横屏（16:9 · 1920×1080 · 30fps · 180 秒）中文悬疑动画短片。
29 个 **Agnes Video 2.5 Flash（免费档，720P 源片后期放大到 1080P）** 连续运动片段，
一镜一句中文旁白，字幕与配音同起止，原创程序合成 BGM/音效。

> 画面为 AI 动画情景重现，不是历史影像；逝者只以远景剪影与草地人形轮廓出现，
> 不出现遗体、伤口或血腥。「外星人 / 药物 / 团体」三类说法全部是传闻，使用泛黄手绘风格，
> 与现实重现画面明确区分。

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 角色与场景定稿参考图 | ✅ 6 张（风格化形象，非真实肖像） | `reference/01–06*.png` |
| 分镜 / 事实边界 / 提示词 | ✅ 29 镜、180 秒；生成器自动拼接 STYLE、角色设定与 NEGATIVE | `build_story.py`、`story.json` |
| 一镜一句旁白 | ✅ 29/29 已录（voice-00），每镜都无需加速、留足呼吸位 | `audio/manifest.json`、`audio/S01–S29.mp3` |
| 离线自检 | ✅ `python3 -m pytest production/tests/test_leadmask1966.py -q`（8 passed） | `production/tests/` |
| Agnes 2.5 Flash 素材 | ✅ 29/29 已完成（720P 源片，全部通过解码与 sha256 校验）；S07/S08/S22 已按画面复原重生成 | `results.json`、`qa/*.jpg` |
| 成片 / 封面 / 字幕 | ✅ 已出片并入 `交付/`：180.000 秒、5400 帧、1080p30、AAC 48kHz 立体声、57.5 MB | `交付/铅面具事件_*` |

## 怎么跑

```bash
python3 production/leadmask1966/build_story.py          # 重建 story.json / 清单 / 脚本
python3 production/leadmask1966/generate.py --validate --clips-only   # 无配音也能验的分镜闸门
python3 -m pytest production/tests/test_leadmask1966.py -q
```

生成与出片在 GitHub Actions（仓库 secret 里已有 `AGNES_API_KEY` 时）：

| 触发文件 | 作用 |
|---|---|
| `production/leadmask1966/GEN_REQUEST` | 生成 29 条 Agnes Video 2.5 Flash 片段（默认先跑 S01 canary，通过后再跑全量） |
| `production/leadmask1966/RENDER_REQUEST` | 旁白齐了之后，只做 1080P 出片（拼接 / 字幕 / 混音 / 封面） |

两个 marker 的 push 都会触发 `.github/workflows/leadmask1966-gen.yml`；结果由工作流 commit 回分支，
成片与 `work/leadmask1966/clips/` 一起进入 Actions artifact（7 天）。

## 规格

- **模型**：`agnes-video-2.5-flash`，`size=720P`、`aspect_ratio=16:9`、`mode=text`、`n=1`；
  请求形状只有 `model/prompt/seconds/size/aspect_ratio/mode/n/seed` 八个字段，
  `width/height/fps/num_frames/negative_prompt` 等字段会被新网关拒绝，因此 NEGATIVE 写在提示词正文里。
- **节流**：62 秒共享闸门、2 个 worker；「video queue is full」按 62 秒重试，直到被接受或被 job timeout 收口。
- **断点续跑**：`results.json` 记 `video_url / task_id / sha256 / bytes / request_hash`，
  提示词或种子变了才算新请求；`work/` 不入库。
- **旁白**：一镜一句（29 条），字幕 = 该镜旁白，时间 = 该镜内声音活动区间；只允许加速（≤1.55×），禁止慢放填时长。
- **字幕**：白色黑边、底部安全区、关键词金色放大；`十六点三十 / 十八点三十 / 等待信号` 是高亮词。
- **片尾**：S29 铅面具旋转，后期叠金色「铅面具事件」与「巴西 · 1966 · 至今未解」，最后一秒静音。
- **封面**：左侧 S13 眼罩特写 + 右侧 S01 山顶红橙色光，金色「铅面具」加黑边。

## 事实边界

- 1966-08-17，米格尔·若泽·维亚纳（34）与曼努埃尔·佩雷拉·达克鲁斯（32）离开坎普斯市；
  家人称他们去圣保罗买车与电子设备，当天下午却出现在尼泰罗伊。
- 1966-08-20 下午，一名 18 岁少年在文廷山放风筝时发现两人；山路难走，警方与消防次日才到现场。
- 现场有西装、雨衣、空水瓶、毛巾、手工铅眼罩与一页笔记本；笔记大意：
  16:30 到达指定地点，18:30 服下胶囊，药效发作后保护金属、等待信号、戴上面具
  （各家转写在单复数与标点上并不一致）。
- 无枪伤、刀伤或打斗痕迹；正式尸检未确定死因；因遗体腐败，毒理检测未能可靠完成。
- 1967 年检验报告：铅板约 225/240 克、2 毫米厚、20 厘米长，有锤痕、**无眼孔、无系带**；
  另有报告称未检出放射性物质。
- 外星人、药物、团体指引、被骗上山均为未证实传闻；案件至今未定论。

### 来源

- Wikipedia: Lead masks case — https://en.wikipedia.org/wiki/Lead_masks_case
- Rede Globo · Linha Direta: Máscaras de Chumbo — https://redeglobo.globo.com/Linhadireta/0,26665,GIJ0-5257-215829,00.html
- O Globo 2026-08-16（六十年后再看） — https://oglobo.globo.com/rio/bairros/niteroi/noticia/2026/08/16/mascaras-de-chumbo-apos-60-anos-misterio-envolvendo-corpos-e-luzes-no-ceu-ainda-intriga-niteroi.ghtml
- The Cold File（1966 现场与尸检） — https://thecoldfile.com/articles/1966-lead-masks/
- StrangeHappen（1967 年铅板检验报告） — https://strangehappen.com/lead-masks-case/
- Mental Floss（发现经过） — https://www.mentalfloss.com/article/70161/bizarre-lead-mask-deaths-1966
- pmig96 案件档案（笔记歧义与传闻来源） — https://pmig96.wordpress.com/2021/05/10/the-lead-masks-case/

## 文件地图

| 路径 | 内容 |
|---|---|
| `build_story.py` / `story.json` | 唯一内容源：STYLE（现实/传闻两套）、NEGATIVE、角色与种子、29 镜提示词、29 条旁白、九段结构、事实边界、字幕高亮、音效设计、发布文案 |
| `screenplay.md` | 完整旁白 + 29 镜分镜表 + 来源 + 后期规范 |
| `audio/` | `manifest.json` + `S01–S29.mp3`（一镜一句，含 sha256 / target_start / target_duration / alignment） |
| `generate.py` | Agnes 2.5 Flash 请求、62 秒节流、断点续跑、接触表、`--clips-only` / `--render-only` |
| `render.py` | 29 镜拼接、逐镜字幕、片尾叠加、封面、技术报告 |
| `build_audio.py` | 旁白限速与字幕对时、原创配乐与音效、响度/峰值闸门 |
| `throttle.py` | 共享创建节流（≥60 秒） |
| `reference/` | 6 张定稿参考图 |
| `qa/` / `results.json` | 生成后的接触表与收据 |
| `workflows/` | 工作流副本（安装到 `.github/workflows/leadmask1966-gen.yml`） |
