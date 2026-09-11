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
| [`production/dahlia/review/`](production/dahlia/review/) | 审片记录：2026-09-09 首审 + 2026-09-10 复核（换机器复现、35 处"冻结"的定性） |
| [`production/review_film.py`](production/review_film.py) | 审片工具：黑帧/冻结帧（带 64×64 复核）/逐章电平/语速，冻结帧阈值有实测标定 |
| [`production/requirements.txt`](production/requirements.txt) | 跑流水线与测试的全部 Python 依赖（ffmpeg 与中文字体仍需系统装） |
| [`production/ci-tests.workflow.yml`](production/ci-tests.workflow.yml) | 每次 push 跑离线自检的工作流模板（需手动复制一次到 `.github/workflows/`） |
| [`电影解说工具包/`](电影解说工具包/) | 更早的一套工具（TTS 分块、EDL、渲染脚本），与上面的流水线并行存在 |

## 待办（需要仓库主手动做一次）

**状态更新（2026-09-10）**：`.github/workflows/commentary-render.yml` 已经是正确 YAML，
与模板 `production/commentary-render.workflow.yml` 逐字节一致（blob `98e4e84`），
`test_workflows.py` 全绿——上面那段"贴错聊天正文"的历史问题已经修掉了。
（那次事故留下的一条经验仍然有效：离线测试当时全绿却拦不住它，所以现在
`production/tests/test_workflows.py` 守着工作流文件的形状与逐字节一致性。）

还剩**两件**需要你手动做的事（都是复制一个文件，复制完我就能远程触发）：

1. **启用每次 push 自动跑离线自检**；
2. **启用逐字听检**（`production/verbatim_check.py`，把成片里的解说转写成文字与剧本逐字比对——
   ASR 模型要从 Hugging Face 下载，本地沙箱连不上，只有 runner 上跑得了）。


代理（GitHub App）写不了 `.github/workflows/`——今天又实测了一次，
`git push` 报 `refusing to allow a GitHub App to create or update workflow ... without 'workflows' permission`。
给我权限的办法：仓库 **Settings → GitHub Apps（<https://github.com/32r4e2q-hub/desktop-tutorial/settings/installations>）
→ Arena 应用 → Configure → Repository permissions → Workflows: Read and write → Save**；
或者换成开了 **Actions: Read and write** 的 fine-grained PAT。给不给都行，不想授权就复制一次：

```bash
cp production/ci-tests.workflow.yml .github/workflows/ci-tests.yml
python3 -m pytest production/tests/test_workflows.py -q    # 必须全绿
```

```bash
cp production/ci-tests.workflow.yml       .github/workflows/ci-tests.yml
cp production/verbatim-check.workflow.yml .github/workflows/verbatim-check.yml
python3 -m pytest production/tests/test_workflows.py -q    # 必须全绿
```

没启用不会让测试变红（会跳过 2 个用例），只是没人替你在每次 push 时跑闸门、
也没人把"配音念的字和剧本一字不差"这件事验掉。
自检查什么见 [`production/ci-tests.workflow.yml`](production/ci-tests.workflow.yml)：
装依赖 → `pytest production/tests`（含工作流形状、混音复现、冻结帧阈值标定）。

### 逐字听检（第四道闸门，只能跑在 Actions 上）

前三道闸门证明"有声、电平正常、每段都有声"，**证明不了配音念的字与剧本一字不差**。
`production/verbatim_check.py` 补的就是这一道：解码成片 → 按章节切段 →
faster-whisper 转写（**不给 `initial_prompt`**，否则等于先把答案告诉模型再让它复述）
→ 与剧本逐字算字错率（CER），超阈值就点名要人耳听那一段。

```bash
# 放好 verbatim-check.yml 之后，Actions → 「逐字听检」→ 填 project（默认 dahlia）
# 或本地（要有能下载模型的网络）：
python3 production/verbatim_check.py --film 交付/<片名>.mp4 \
    --project production/<slug> --work work/<slug>/verbatim --model small
```

报告 commit 回 `production/<slug>/delivery/verbatim-check.json`。

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

外加一道**固定音色闸门**（`production/check_voice.py`，出片脚本第 2 步自动跑）：
解说必须是《黑色大丽花》同款普通话男音（每章中位基频 95–155 Hz、与参考音色偏差 ≤ 25%），
音色不对直接拒绝出片。规格、参考样本与实测数字见
[`production/voice_reference/`](production/voice_reference/)——换配音时照着选，不用再问用户。

参考项目成片实测：`-21.09 dBFS RMS`、峰值 `-1.52 dBFS`、静音占比 `1.1%`
（见 [`production/dahlia/delivery/final-audio-report.json`](production/dahlia/delivery/final-audio-report.json)）。

## 本地跑

```bash
python3 -m pip install -r production/requirements.txt   # 另需 ffmpeg/ffprobe 与中文字体
python3 -m pytest production/tests -q                   # 离线测试
```

当前环境实测（2026-09-10）：

| 环境 | 结果 |
|---|---|
| 有 ffmpeg（装了 `imageio-ffmpeg` 也行） | `61 passed, 1 skipped` |
| 没有 ffmpeg | `54 passed, 8 skipped` |

跳过的都是"要真解码才测得出来"的用例：7 个需要 ffmpeg（电平、混音复现），
1 个是 CI 自检模板还没手动放进 `.github/workflows/`。
`pyyaml` 写在 `requirements.txt` 里但不是硬依赖：不装也有 4 条工作流守卫生效。

## 复现实测（换一台机器量，还是同一组数字）

参考项目的混音在**另一台机器、另一个 ffmpeg 构建**上重跑，与云端出片时的记录
**逐项差 0.00 dB**：混音 -21.08 dBFS RMS / 峰值 -1.51，成片 -21.09 / -1.52，
逐章 N01–N06 全部一致。数据见
[`production/dahlia/delivery/reproducibility-2026-09-10.json`](production/dahlia/delivery/reproducibility-2026-09-10.json)，
并且由 `production/tests/test_dahlia_mix.py` 钉住（容差 0.05 dB）。

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
