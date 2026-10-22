# 玛丽·赛勒斯特号：海上最大的未解之谜

三分钟横版（16:9 · 1920×1080 · 30 fps · 180 秒）中文悬疑解说短片，抖音横屏观看版。
**画面是皮克斯级 3D 动画 × 暗黑童话的动态镜头（智谱 CogVideoX-Flash 免费档生成，不是图片轮播）。**

- slug：`maryceleste1872`　出片分支：`arena/63ceeca2-desktop-tutorial`　成片：`交付/玛丽赛勒斯特号_海上最大的未解之谜_三分钟_带声音.mp4`
- 规格：**31 个 CogVideoX 动态镜头 + 片尾标题卡**（用户 29 镜脚本；镜头 5/7/18 各含一次内部硬切，拆成 5A/5B、7A/7B、18A/18B），每镜只出现一次
- 内容源：用户提供的 29 镜脚本（`build_story.py` 为唯一内容源），事实按 [`史实核对.md`](史实核对.md) 核对
- 配音：`voice-00` 悬疑低沉男声（用户试听选定）· 八段解说 551 字 · **pacing.py 按分句铺进八段窗口**（句间悬疑停顿 0.26–3.2 s，口播不硬变速）

## 一句话流程

```
用户 29 镜脚本 + 【STYLE/NEGATIVE/角色与船体设定】
  └─> cast.json 角色谱（4 角色 face token + seed）+ cast/ 定稿参考图（4 角 + 3 船 + 1 场景）
        └─> build_story.py 唯一内容源：八段解说 / 31 镜提示词 / 横幅大字 / 红叉 / 片头片尾卡
              └─> TTS（voice-00）→ tighten_pauses.py → clause_times.py → pacing.py（铺进段落窗口）
                    └─> generate.py --validate + face_cast.py check-prompts      ← 闸门一
                          └─> COGVIDEOX_GEN_REQUEST → Actions 跑 CogVideoX-Flash 免费档 31 镜
                                └─> 复审 qa/ 接触表 → {"only":"Sxx","force":"Sxx"} 重做坏镜
                                      └─> tools/plan_cuts.py 按分句排 CUTS → clause_times.py --check-cuts ← 闸门二
                                            └─> RENDER_REQUEST → 成片 + delivery/ 报告 ← 闸门三
                                                  └─> VERBATIM_REQUEST · VISUAL_QC_REQUEST → 人工语义签收
```

## 本片与模板（production/kitakyushu2002 北九州案）的关系

引擎（render.py / build_audio.py / generate_cogvideox.py / QC 工具链）由北九州案模板移植，
路径、分支名、片名全部替换；内容、分镜、角色谱、来源全部重写。生成侧只走智谱 CogVideoX-Flash
免费档（`model_policy.COGVIDEOX_MODEL`），零费用。

## 本片的引擎改动（相对模板，均记录在 制作过程.md）

1. **pacing.py（新增）**：口播按分句拆开、均匀铺进用户八段窗口（句间停顿即悬疑呼吸），
   clause-times.json 由它按拼装位置精确写出；`clause_times.align` 改为「比例 + 停顿吸附」
   （旧能量 DP 在本片配音上会挤出 10–15 字/秒的分句）；
2. **逐章窗口排版**：`render.chapter_layout` 逐章 tempo（本片全 1.000），CUTS 切点可落在
   「分句起点」或「停顿中点」（check-cuts 窗口按各句实际停顿自适应）；
3. **横幅大字 / 红色大叉 / 金色放大关键词**（用户规格）：ASS 层实现，横幅钉 `\pos` 防碰撞挤掉；
   ASS 转义统一用 chr(92) 拼装（`\f` 吃字事故见 制作过程.md）；
4. **分段 BGM（score.py）**：大提琴/弦乐/诡异钢琴/鼓点/管弦/悬疑钢琴/收尾逐段落实用户音乐设计，
   S17『嘭』后静音、S23 爆燃『咚』+ 耳鸣、片尾最后一秒静音；
5. **音效扩展**：bell / wave / creak / wind / boom / snap / ding / gull（船钟、海浪、木头吱呀、风声……）；
6. **face_cast.py 修 bug**：多角色同框（S04/S24 家庭三人）时「已声明的其他角色」不再误判为偷带。

## 文件说明

| 文件 | 作用 |
|---|---|
| `build_story.py` | **唯一内容源**（解说 / 31 镜提示词 / 横幅 / 红叉 / 片头片尾卡 / 发布文案）；token 用 `{C1}–{C4}` 占位符从 cast.json 注入 |
| `cast.json` + `cast/*.png` | 角色谱与定稿参考图（4 角色 + 完好/幽灵态玛丽号 + 上帝的恩典号 + 夜雾钩子场景） |
| `story.json` / `screenplay.md` | 时间轴、剧本与逐镜提示词（build_story.py 写出） |
| `audio/` | 八段配音（raw → 收紧 → pacing 铺开）、`clause-times.json`、`pacing-report.json`、`manifest.json` |
| `pacing.py` / `score.py` | 配音排版（句间停顿铺窗口）/ 原创分段配乐 |
| `generate_cogvideox.py` | 智谱 CogVideoX-Flash 生成引擎（SHA-256 收据、断点续跑、force 真重抽、QA 接触表） |
| `render.py` | 剪辑引擎：`CUTS`（plan_cuts 排出）+ `WINDOWS` / `GRADE_OVERRIDES` / `VIGNETTE_SHOTS` / `FADE_OUT` |
| `results.json` / `qa/` | 每镜生成收据与接触表 |
| `delivery/` | 技术报告、EDL、字幕、混音实测、听检、全帧 QC、复核文档 |

## 本地命令

```bash
python3 production/maryceleste1872/build_story.py           # 写 story.json
python3 production/face_cast.py check-prompts --project production/maryceleste1872
python3 production/maryceleste1872/generate.py --validate
python3 production/maryceleste1872/clause_times.py --check-cuts
bash production/run_project.sh maryceleste1872              # 出片（Actions 上由 RENDER_REQUEST 触发）
```
