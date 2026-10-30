# 世田谷一家四口杀人案：留下无数线索，凶手为何仍未找到？

三分钟横屏（16:9 · 1920×1080 · 24fps · 180 秒）中文悬疑 3D 动画纪录片。
29 个 **Agnes Video 2.5 Flash（720P 源片后期放大到 1080P）** 连续运动镜头，一镜一句中文旁白，
字幕与配音同起止，原创程序合成 BGM 与音效。

> 画面为 AI 动画情景重现，不是历史影像；物证画面为 3D 示意性复原，不是警方原始照片。
> 不出现遗体、伤口、血腥或作案过程；凶手只以远景剪影出现，不复制任何真实人物的相貌。

## 这是新片的默认模板

本目录自 2026-10-28 起是仓库的**默认出片模板**。换题目时照
[`模板-如何复用.md`](模板-如何复用.md) 复制本目录、替换分支名与片名常量、重写 `build_story.py` 即可，
不要另起炉灶。`新题目开工手册.md` 顶部的「狂犬病模式」已降级为历史参考。

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 角色与场景定稿参考图 | ✅ 7 张（风格化形象，非真实肖像） | `reference/01–07*.png` |
| 分镜 / 事实边界 / 提示词 | ✅ 29 镜、180 秒；生成器自动拼接 STYLE、角色设定与 NEGATIVE | `build_story.py`、`story.json` |
| 一镜一句旁白 | ✅ 29 条全部完成，低沉悬疑男声（voice-00） | `audio/manifest.json`、`audio/S**.mp3` |
| 离线自检 | ✅ `python3 -m unittest production.tests.test_setagaya2000 -q`（12 项） | `production/tests/` |
| Agnes 2.5 Flash 素材 | ✅ 29/29 completed，全部 1280×720 源片 | `results.json`、`qa/*.jpg` |
| 成片 / 封面 / 字幕 | ✅ 1920×1080 · 24fps · 180.0s · 4320 帧 · h264+aac 48k | `交付/Setagaya_Case_Final.mp4` 等 | 
| 成片质检（硬闸门） | ✅ `QC PASS`，`hard_gate_failures: []`（平均亮度 57.67 · 非预期黑帧 0 · 冻结 0 · 闪烁 0 · RMS −21.04 dBFS · 峰值 −1.66 · 末秒 −120 dBFS） | `qa/qc-summary.md`、`qa/qc-report.json` |
| 原始像素抽帧复核 | ✅ 29 张 1920×1080 原生帧 + 逐批 contact sheet（查 AI 伪文字 / 面部崩坏 / 字幕遮挡） | `qa/fullres/S01–S29.jpg`、`qa/sheets/` |
| 逐镜提示词与生成记录 | ✅ 29/29 已完成 | `镜头提示词与生成记录.md`、`qa/生成记录.csv` |
| 解说词与片段等长 | ✅ 29 镜逐条实测：`fit` 11 · `needs-speedup` 10（1.01–1.33×）· `ok` 4 · `short` 4（均为刻意的片尾停顿/留白），无 `over` | `qa/narration-fit.md`、`narration_fit.py` |

## 交付清单

- `交付/Setagaya_Case_Final.mp4` — 65.4 MB · SHA-256 `976500f1103110808f204f2bdd7c94569d9c8dcf5aa9ec8833d71f43c50f683a`（与 `世田谷一家四口杀人案_留下无数线索的悬案_三分钟_带声音.mp4` 同一份字节）
- `交付/Setagaya_Cover.png` — 1920×1080 封面
- `交付/Setagaya_Subtitles.srt` — 30 条（29 条逐镜旁白 + 1 条片尾提问）
- `交付/世田谷一家四口杀人案_技术报告.json` — 规格、混音实测、风格一致性说明

## 怎么跑

```bash
python3 production/setagaya2000/build_story.py                          # 重建 story.json / 清单 / 脚本
python3 production/setagaya2000/generate.py --validate --clips-only     # 无配音也能验的分镜闸门
python3 -m unittest production.tests.test_setagaya2000 -q
```

生成与出片在 GitHub Actions（仓库 secret 里已有 `AGNES_API_KEY`）：

| 触发文件 | 作用 |
|---|---|
| `production/setagaya2000/GEN_REQUEST` | 生成 29 条 Agnes Video 2.5 Flash 片段（默认先跑 S01 金丝雀，通过后再跑全量） |
| `production/setagaya2000/RENDER_REQUEST` | 旁白齐了之后，只做 1080P 出片（拼接 / 字幕 / 混音 / 封面） |
| `production/setagaya2000/QC_REQUEST` | 只跑成片质检（容器 / 冻结 / 黑帧 / 音频 / 字幕） |

## 规格

- **模型**：`agnes-video-2.5-flash`，`size=720P`、`aspect_ratio=16:9`、`mode=text`、`n=1`；
  请求形状只有 `model/prompt/seconds/size/aspect_ratio/mode/n/seed` 八个字段，
  NEGATIVE 写在提示词正文里。
- **节流**：61 秒共享闸门、2 个 worker；「video queue is full」按 61 秒重试。
- **断点续跑**：`results.json` 记 `video_url / task_id / sha256 / bytes / request_hash`，`work/` 不入库。
- **旁白与镜头等长**：镜头时长服从旁白——先录一整句、量自然语音长度，再在 Agnes 的 4–9 秒档位里挑一个刚好装下它的；
  字幕时间直接取该镜的语音活动区间，所以切点落在句子之间。29 镜里 17 镜零加速，其余 1.01–1.33×（上限 1.55×），
  从不慢放填时长、从不截字。全片 644 个有效字，平均 3.58 字/秒。实测表：`qa/narration-fit.md`，工具：`narration_fit.py`。
- **字幕**：白色黑边、底部安全区、关键词金色放大；`2000年 / 世田谷 / 运动衫 / 黑色手帕 / 电脑 / 真相` 等为高亮词。
- **片尾**：S29 物证与住宅剪影，后期叠金色「世田谷一家四口杀人案」与「日本 · 2000 · 至今未破」，
  最后 0.8 秒淡出至静音；右上角常驻「AI动画情景复原 · 非真实影像」。
- **封面**：左侧 S11 灰色拼接运动衫、右侧 S01 冬夜住宅、中央金色问号；
  主标题「世田谷一家四口」+ 副标题「留下无数线索，凶手为何仍未找到？」。
- **交付**：`交付/Setagaya_Case_Final.mp4`、`Setagaya_Narration.wav`、`Setagaya_Subtitles.srt`、
  `Setagaya_Cover.png`，另有仓库命名的成片 / 封面 / 字幕 / 技术报告。

## 事实边界

- 2000 年 12 月 30 日深夜至 31 日凌晨，东京都世田谷区上祖师谷三丁目宫泽家四口遇害；
  30 日傍晚一家人在千岁乌山站附近商店街购物后回家。
- 遇害者：宫泽干男（44，外资企业 CI 开发）、妻泰子（41，在家经营补习班）、
  长女妮娜（8，小学二年级，学芭蕾与钢琴）、长子礼（6，保育园年长班）。
- 31 日上午由住在隔壁的泰子母亲发现异常；警方设立特别搜查本部。
- 出入口：警视厅 2024 年 12 月首次公开见解——凶手从中二层北侧浴室窗户进入、并从同一扇窗户离开
  （发现时玄关上门锁，浴室窗开着、纱窗落在窗外；窗离地约 3.4 米）。片中 S07 只说到「从二楼浴室的窗户进去的」。
- 案发后行为：用过电脑（31 日凌晨 1:18、上午 10:00 两次痕迹）、吃掉冰箱里四个杯装冰淇淋、使用厕所、
  翻动物证与急救箱（急救箱里有沾指纹的创可贴）；现场留下凶手血迹、鞋印与指纹，DNA 型比对约 130 万件无一致。
- 凶手被判断从二楼浴室窗户侵入、从玄关离开；现场遗留浅灰身浅紫袖拉格伦运动衫（全国 130 件、都内 10 件）、
  两块无印良品黑色手帕、黑色腰包、夹克、围巾、帽子、手套、韩国制运动鞋足迹与柳刃包丁。
- 公开报道的行为痕迹：案发后有人使用电脑（媒体报道 31 日凌晨 1:18 等时间点）、
  吃掉冰箱里四个杯装冰淇淋、使用厕所。片中只作行为描述，不推断动机。
- 凶手像：较年轻、约 170cm、A 型、偏瘦、L 码、鞋 27.5cm（韩国 280）；DNA 比对累计上百万件无一致。
- 案件至今未破，2010 年修法后此类案件不再有公诉时效；悬赏金上限 2000 万日元（公的 300 万 + 私的 1700 万）。

### 来源

- 警视庁「世田谷一家４人強盗殺人事件」公开资料（PDF） — https://www.keishicho.metro.tokyo.lg.jp/jiken_jiko/ichiran/ichiran_11-20/seijo.files/Ja_2601.pdf
- 警视庁事件页面 — https://www.keishicho.metro.tokyo.lg.jp/jiken_jiko/ichiran/ichiran_11-20/seijo.html
- 日本经济新闻（2011-12-19）运动衫销售分布 — https://www.nikkei.com/article/DGXNASDG1903J_Z11C11A2CC1000/
- 每日新闻（2022-04-18）事件概要与电脑使用记录 — https://mainichi.jp/articles/20220418/osg/00m/040/001000d
- 读卖新闻（2025-12-31）四分之一世纪后仍未解决 — https://www.yomiuri.co.jp/national/20251231-GYT1T00014/
- 週刊女性PRIME（2020-12-30）28 万人次与凶手像 — https://www.jprime.jp/articles/-/19751?page=3
- HuffPost Japan（2015-03-22）遗留物清单 — https://www.huffingtonpost.jp/2015/03/22/setagaya-murder_n_6918156.html

## 文件地图

| 路径 | 内容 |
|---|---|
| `build_story.py` / `story.json` | 唯一内容源：STYLE（写实/示意两套）、NEGATIVE、8 个角色与种子、29 镜提示词、29 条旁白、九段结构、事实边界、字幕高亮、音效设计、发布文案 |
| `screenplay.md` | 完整旁白 + 29 镜分镜表 + 来源 + 后期规范 |
| `audio/` | `manifest.json` + `S01–S29.mp3`（一镜一句，含 sha256 / target_start / target_duration） |
| `generate.py` | Agnes 2.5 Flash 请求、61 秒节流、断点续跑、接触表、`--clips-only` / `--render-only` |
| `render.py` | 29 镜拼接、逐镜字幕、片尾叠加、封面、技术报告 |
| `build_audio.py` | 旁白限速与字幕对时、原创配乐与音效、响度/峰值闸门 |
| `qc.py` | 成片质检：容器 / 冻结 / 黑帧 / 闪烁 / 电平 / 静音 / 字幕时间轴 / 封面尺寸 |
| `throttle.py` | 共享创建节流（≥60 秒） |
| `reference/` | 7 张定稿参考图 |
| `qa/` / `results.json` | 逐镜接触表、QC 摘要与生成收据 |
| `workflows/` | 工作流副本（安装到 `.github/workflows/setagaya2000-gen.yml`） |
