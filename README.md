# 电影解说视频流水线

三分钟中文解说短片的**可复现流水线**：剧本与分镜计划进，实测过电平的成片出。
从选题到成片全程可在 GitHub Actions 上跑，中间产物不进 Git，成片与实测报告进 Git。

## 现在有什么

| 路径 | 内容 |
|---|---|
| [`production/dahlia/`](production/dahlia/) | **参考实现**：《黑色大丽花：消失的六天》，已成片、已实测 |
| [`交付/`](交付/) | 成片 `黑色大丽花_三分钟_带声音.mp4`（48.1 MB，1920×1080 / 30fps / 180 秒） |
| [`新题目开工手册.md`](新题目开工手册.md) | **换题目做新片就照这份走** |
| [`production/new_topic.py`](production/new_topic.py) | 开新题目的脚手架：复制流水线、生成骨架、把上一部片子的内容标成 TODO |
| [`production/dahlia/制作过程.md`](production/dahlia/制作过程.md) | 参考项目全过程，含"第一版为什么没声音"的根因与修复 |
| [`电影解说工具包/`](电影解说工具包/) | 更早的一套工具（TTS 分块、EDL、渲染脚本），与上面的流水线并行存在 |

## 开一个新题目

```bash
python3 production/new_topic.py --slug ripper1888 --title "开膛手杰克：1888 年的秋天"
```

生成 `production/ripper1888/`：流水线引擎副本 + `story.json` 骨架（30 镜 × 6 秒、6 章 × 30 秒）
+ `screenplay.md` + 配音清单 + 出片工作流。之后按 [`新题目开工手册.md`](新题目开工手册.md) 一步步填。

参考项目只被读取、不被修改，这一条有测试守着。

## 三道闸门（不许出片的三种情况）

1. `generate.py --validate` —— 时间轴、提示词、配音文本与剧本逐字一致、配音 SHA-256；
2. `build_audio.py` —— 整体电平 / 波峰因数 / 静音占比 / **逐段**解说电平；
3. `render.py` 收尾 —— 对**最终 mp4** 复测一遍，不达标直接失败。

参考项目成片实测：`-21.09 dBFS RMS`、峰值 `-1.52 dBFS`、静音占比 `1.1%`
（见 [`production/dahlia/delivery/final-audio-report.json`](production/dahlia/delivery/final-audio-report.json)）。

## 本地跑

```bash
python3 -m pip install pillow numpy            # 另需 ffmpeg/ffprobe 与中文字体
python3 -m pytest production/tests -q          # 离线测试
```

当前环境实测：`39 passed, 4 skipped`（跳过的 4 个用例需要 ffmpeg 解码测电平）。

## 出片

把项目目录里的 `<slug>.workflow.yml` 复制到 `.github/workflows/<slug>.yml`，
再在 Actions 里 Run workflow。当前 GitHub 授权没有 `workflows` 权限，这一步需要手动做一次。

## 事实边界

- AI 画面一律标注「AI情景重现 · 非历史影像」，不冒充真实影像；
- 真实人物只用有出处的档案照片，不用 AI 生成的脸冒充本人；
- 未侦破/未定论的事不指认责任人；
- 中文姓名、日期、字幕一律后期添加，不交给视频模型拼写。
