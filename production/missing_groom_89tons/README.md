# 消失的未婚夫：一个月八十九吨水（30 镜 / 180 秒 / Agnes Video 2.5 Flash）

抖音横屏 16:9、1920×1080、24fps、180 秒、30 个真实连续运动的**写实 3D 动画**镜头。
模板沿用仓库默认的 `production/setagaya2000`（世田谷模式）＋已交付先例
`production/honeymoon_nicotine`（30 镜 / reference 模式 / 12.1 秒共享闸门）。

## 事实口径（红线）

- 金明哲官方身份**至今仍为失踪**；全片只用“警方怀疑”“没有尸体，法院无法认定杀人”的口径，
  绝不下“已被杀害”的定论。
- 不出现遗体、血腥、伤口、行凶过程、肢体处理；痕迹只用水表、水流、油漆、沙发、门缝光暗示。
- 李某以“表面平静、眼神冷静”呈现，不美化、不渲染心理；“舞蹈教室掩盖声响”只在旁白里标为推测。
- 所有人物为写实演员式虚构形象，非真实肖像；成片全程标注“AI动画情景重现 · 非真实影像”。

## 目录

| 文件 | 作用 |
|---|---|
| `build_story.py` | **唯一内容源**：STYLE / NEGATIVE / 10 个角色锚点 / 30 行镜头表 / 9 章 / 发布信息 |
| `story.json`、`screenplay.md`、`抖音脚本.md`、`抖音发布文案.md` | 由 `build_story.py` 生成，不要手改 |
| `reference/` | 30 张定稿参考图（C01–C10 / S01–S13 / P01–P07）+ `REFERENCE_PACK.md` + `approvals.json` + `revision.txt` |
| `generate.py` | Agnes 2.5 Flash 调用、reference 模式 payload、闸门、断点续跑、出片、发布 |
| `render.py` | 24fps 合成、字幕（36px 白字 + 金色 42px 关键词）、封面、技术报告 |
| `qc.py` / `narration_fit.py` | 成片硬闸门与逐镜旁白语速闸门 |
| `build_audio_manifest.py` | 把 `audio/S01.mp3…S30.mp3` 绑成 shot-locked manifest |
| `throttle.py` | 12.1 秒共享请求闸门（POST/GET 同一条时间线） |
| `audio/` | 30 条逐镜旁白 + `manifest.json` |

## 关键参数

- 模型 `agnes-video-2.5-flash`，源片 `720P`，`seconds` 为字符串且只取 5/6/7；
  后期 Lanczos 放大到 1920×1080，24fps，libx264 crf20，AAC 192k 48k。
- payload 只允许：`model, prompt, seconds, size, aspect_ratio, mode, n, seed, images`；
  `mode=reference`，`images` 为 1–4 张经 `approvals.json` 校验的不可变 raw 链接。
- 请求闸门 12.1 秒/次（月卡 5 次/分钟），429 队列满 60s 退避、容量 120s，`workers≤2`。
- 旁白一镜一句、只快不慢（atempo ≤ 1.55×，不删字），字幕时间 = 语音活动区间。
- 镜头平均 6 秒；每段以悬念句 + 定格收束；镜头 1 与镜头 8 形成“欢呼 vs 孤独走入”对比。

## 运行

```bash
python3 build_story.py                 # 生成 story.json / 脚本 / 发布文案
python3 generate.py --validate --clips-only
# 触发（Actions 里跑，分支 pin 在 arena/fa517800-desktop-tutorial）
printf '{"mode":"clips","workers":2}' > GEN_REQUEST && git commit -am "queue clips" && git push
printf '{"mode":"render","workers":1}' > GEN_REQUEST && git commit -am "render" && git push
```

`GEN_REQUEST` 支持 `status` / `retrieve` / `clips` / `render` / `qc`；工作流
`.github/workflows/missing-groom-gen.yml` 监听它的 push。

## 进度

- [x] 仓库勘察 / 模板比对（setagaya2000 + honeymoon_nicotine）
- [x] `build_story.py`：30 镜 / 180 秒 / 9 章 / 605 字旁白（3.0–4.0 字/秒）
- [x] 30 张参考图定稿（C01–C10 / S01–S13 / P01–P07，逐张审批 + SHA-256 + 不可变 revision）
- [x] Agnes 30 片段排队生成（720P 源片，全部解码校验，run 43134776967 success）
- [x] 旁白 TTS（voice-01，30 条一镜一句，最大 1.28×）+ 烧录字幕（44px 白字 / 50px 金色关键词 / 左上 AI 标注）
- [x] 出片 / QC / 交付：`交付/消失的未婚夫_一个月89吨水_三分钟_带声音.mp4`（74.6MB，180.000s / 4320 帧 / 24fps / 1080p，QC 硬失败 0 项）
