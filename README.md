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

## 待办（需要仓库主手动做一次）

`.github/workflows/commentary-render.yml` 现在是**一段中文聊天正文**，不是 YAML——
2026-09-10 手动放置时贴错了内容。后果：main 上每次 push 都产生一次 0 秒失败的 Actions 运行
（[run 34421881730](https://github.com/32r4e2q-hub/desktop-tutorial/actions/runs/34421881730)，
GitHub 报 "This run likely failed because of a workflow file issue."）。
代理改不了这个目录（`git push` 与 Contents API 均实测 403，缺 `workflows` 权限），只能你来做：

```bash
cp production/commentary-render.workflow.yml .github/workflows/commentary-render.yml
python3 -m pytest production/tests/test_workflows.py -q    # 必须全绿
```

或在 GitHub 网页编辑器里把该文件内容整体替换成
[`production/commentary-render.workflow.yml`](production/commentary-render.workflow.yml) 的内容。
修好之前 `production/tests` 会有 7 项失败——那是测试在如实报告，不是测试坏了。

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

当前环境实测（工作流文件放对之后）：装 `pyyaml` 时 `46 passed, 4 skipped`，
不装时 `45 passed, 5 skipped`（多跳过的那 1 个是工作流的完整 YAML 解析）。
4 个跳过的用例需要 ffmpeg 解码测电平，本沙箱没有 ffmpeg。
`pyyaml` 不是必需依赖：不装也有 4 条工作流守卫生效。

## 出片

本地：`bash production/run_project.sh <slug> [skip_asr] [成片文件名]`。
Actions：「解说短片出片」→ 填 `project`（slug）、`skip_asr`、`film_name`。
**`film_name` 留空会用 `story.json` 的标题当片名**，重跑已交付的片子会多出一个副本，
所以重跑 dahlia 要填 `黑色大丽花_三分钟_带声音.mp4`。

工作流的三个输入怎么传到脚本、脚本怎么用第 3 个参数，都有测试守着
（`production/tests/test_workflows.py`）。

## 事实边界

- AI 画面一律标注「AI情景重现 · 非历史影像」，不冒充真实影像；
- 真实人物只用有出处的档案照片，不用 AI 生成的脸冒充本人；
- 未侦破/未定论的事不指认责任人；
- 中文姓名、日期、字幕一律后期添加，不交给视频模型拼写。
