# 世田谷一家四口杀人案：留下无数线索，凶手为何仍未找到？

三分钟横屏（16:9 · 1920×1080 · 24fps · 180 秒）中文悬疑 3D 动画纪录片。
29 个 **Agnes Video 2.5 Flash（720P 源片后期放大到 1080P）** 连续运动镜头，一镜一句中文旁白，
字幕与配音同起止，原创程序合成 BGM 与音效。

> 画面为 AI 动画情景重现，不是历史影像；物证画面为 3D 示意性复原，不是警方原始照片。
> 不出现遗体、伤口、血腥或作案过程；凶手只以远景剪影出现，不复制任何真实人物的相貌。

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 角色与场景定稿参考图 | ✅ 7 张（风格化形象，非真实肖像） | `reference/01–07*.png` |
| 分镜 / 事实边界 / 提示词 | ✅ 29 镜、180 秒；生成器自动拼接 STYLE、角色设定与 NEGATIVE | `build_story.py`、`story.json` |
| 一镜一句旁白 | 🚧 低沉悬疑男声（voice-00）逐镜录制中 | `audio/manifest.json`、`audio/S**.mp3` |
| 离线自检 | ✅ `python3 -m unittest production.tests.test_setagaya2000 -q`（12 项） | `production/tests/` |
| Agnes 2.5 Flash 素材 | 🚧 由 `GEN_REQUEST` / 工作流默认金丝雀触发 | `results.json`、`qa/*.jpg` |
| 成片 / 封面 / 字幕 / 质检 | 🚧 `RENDER_REQUEST` 出片后跑 `qc.py` | `交付/`、`qa/qc-summary.md` |

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
- **旁白**：一镜一句（29 条，voice-00 低沉悬疑男声），字幕 = 该镜旁白，时间 = 该镜内声音活动区间；
  只允许加速（≤1.55×），禁止慢放填时长。全片 656 个有效字，平均 3.64 字/秒。
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
