# 电影解说视频流水线

三分钟中文解说短片的**可复现流水线**：剧本与分镜计划进，实测过电平的成片出。
从选题到成片全程可在 GitHub Actions 上跑，中间产物不进 Git，成片与实测报告进 Git。

## 现在有什么

| 路径 | 内容 |
|---|---|
| [`production/gilgo/`](production/gilgo/) | **参考实现（当前标准）**：《吉尔戈海滩：披萨盒里的凶手》，2026-09-21 成片、[Release gilgo-v1](https://github.com/32r4e2q-hub/desktop-tutorial/releases/tag/gilgo-v1)；45 镜 × 4 秒、38 个 Agnes 动画镜头 + 7 张信息卡、每镜只用一次 |
| [`交付/`](交付/) | 成片 `吉尔戈海滩_披萨盒里的凶手_三分钟_带声音.mp4`（69.9 MB，1920×1080 / 30fps / 180 秒）；更早的 `黑色大丽花_三分钟_带声音.mp4` |
| [`新题目开工手册.md`](新题目开工手册.md) | **换题目做新片就照这份走**（吉尔戈模式：10 步 + 踩坑清单） |
| [`production/new_topic.py`](production/new_topic.py) + [`production/templates/`](production/templates/) | 开新题目的脚手架：复制引擎、渲染"内容与引擎分离"的 `build_story.py` / `render.py` / `script_table.py` 模板、生成 45×4 骨架与三份 marker 工作流 |
| [`production/gilgo/制作过程.md`](production/gilgo/制作过程.md) | 参考项目全过程（13 节）：事实核查、TTS 收紧、切点对齐、三轮复审、字幕修复、听检 |
| [`production/gilgo/抖音脚本.md`](production/gilgo/抖音脚本.md) / [`抖音发布文案.md`](production/gilgo/抖音发布文案.md) | 交付给发布的脚本（三标题 / 爆点 / 四列分镜表 / 金句）与发布文案（题目 / 介绍 / 提问读者 / 话题），都由 `build_story.py` 生成 |
| [`production/dahlia/`](production/dahlia/) | 上一代参考实现《黑色大丽花：消失的六天》（30 镜 × 6 秒、带档案照片），[审片记录](production/dahlia/review/) 与冻结帧阈值标定仍在用 |
| [`production/review_film.py`](production/review_film.py) | 审片工具：黑帧/冻结帧（带 64×64 复核）/逐章电平/语速，冻结帧阈值有实测标定 |
| [`production/requirements.txt`](production/requirements.txt) | 跑流水线与测试的全部 Python 依赖（ffmpeg 与中文字体仍需系统装） |
| [`production/ci-tests.workflow.yml`](production/ci-tests.workflow.yml) | 每次 push 跑离线自检的工作流模板（需手动复制一次到 `.github/workflows/`） |
| [`转私有与自托管Runner手册.md`](转私有与自托管Runner手册.md) | **要让仓库不再公开时读这份**：转私有的正确顺序、自托管 runner 怎么装、`RUNNER_LABEL` 开关 |
| [`runner/`](runner/) | 本地出片机三件套：一键安装注册 `setup-runner.sh`、只读自检 `selfcheck.sh`、卸载 `uninstall-runner.sh` |
| [`电影解说工具包/`](电影解说工具包/) | 更早的一套工具（TTS 分块、EDL、渲染脚本），与上面的流水线并行存在 |

## 仓库可见性与 runner

- **仓库现在是私有的**（2026-09-20 核对：`gh api repos/32r4e2q-hub/desktop-tutorial` → `"private": true`）。
  提醒一句：分支不等于权限——公开仓库的所有分支、提交与 **Actions 日志**对全世界可见，
  把内容挪到分支只是不在首页展示，真要藏住只能转私有。
- 私有仓库的 GitHub-hosted runner 走 **2000 分钟/月**的额度（出片一次 6~90 分钟），
  自托管 runner **不计分钟**——所以这套流水线的机器由仓库变量 `RUNNER_LABEL` 决定：
  `runs-on: ${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}`。**不设这个变量时行为与以前完全一样。**
- 🚀 **想把出片搬到你自己的机器上**：`bash runner/setup-runner.sh`（Linux / WSL2），
  装完 `bash runner/selfcheck.sh` 自检。见 [`runner/README.md`](runner/README.md)，
  原理与手工步骤见 [`转私有与自托管Runner手册.md`](转私有与自托管Runner手册.md)。
  ⚠️ 注册 token 只有仓库主能取（代理的 GitHub App 没有 `administration` 权限，
  实测 403），所以这一步**必须由你在自己的机器上完成**——也正因如此，
  token 不需要交给任何人。
- ⚠️ 自托管 runner **绝不能挂在公开仓库上**（fork PR 能在你机器上执行任意代码），
  所以顺序是**先转私有、再装 runner**。完整步骤见
  [`转私有与自托管Runner手册.md`](转私有与自托管Runner手册.md)。

## 待办（需要仓库主手动做一次）

**状态更新（2026-09-10）**：`.github/workflows/commentary-render.yml` 已经是正确 YAML，
与模板 `production/commentary-render.workflow.yml` 逐字节一致（blob `98e4e84`），
`test_workflows.py` 全绿——上面那段"贴错聊天正文"的历史问题已经修掉了。
（那次事故留下的一条经验仍然有效：离线测试当时全绿却拦不住它，所以现在
`production/tests/test_workflows.py` 守着工作流文件的形状与逐字节一致性。）

**状态更新（2026-09-18）**：上面那两件"要手动复制"的事**都已经做完了**——
`.github/workflows/ci-tests.yml` 与 `.github/workflows/verbatim-check.yml` 都在仓库里、
与模板逐字节一致、`test_workflows.py` 全绿（74 passed / 10 skipped，跳过的是要真解码的用例）。

同时，**代理（GitHub App）现在写得动 `.github/workflows/` 了**——2026-09-18 实测
`git push` 成功，不再报 `without 'workflows' permission`。历史教训仍然有效：
离线测试当时全绿却拦不住"贴错内容"，所以 `production/tests/test_workflows.py`
继续守着工作流文件的形状与逐字节一致性，别把这两份文件改成"只改一份"的状态。

**仓库可见性那件事已经做完了**（现在是 private）。**现在剩下的手动事项是装本地 runner**：
见 [`runner/README.md`](runner/README.md) 的三分钟版，或
[`转私有与自托管Runner手册.md`](转私有与自托管Runner手册.md) 的完整版——
装自托管 runner → 设 `RUNNER_LABEL`，顺序不能换（反过来会有一段把你机器敞开的时间）。
注册 token 与仓库变量**只有仓库主能操作**（代理的 GitHub App 缺 `administration` 权限，
实测 `registration-token` 与 `actions/variables` 都是 403），所以这一步得由你跑脚本完成。
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
python3 production/new_topic.py --slug ripper1888 --title "开膛手杰克：1888 年的秋天" --branch arena/<分支>
```

生成 `production/ripper1888/`：流水线引擎副本（含 `tighten_pauses.py` / `clause_times.py`）
+ 从 `production/templates/` 渲染的 `build_story.py`（唯一内容源，全是 TODO）/ `render.py` / `script_table.py`
+ `story.json` 骨架（45 镜 × 4 秒、6 章 × 30 秒）+ `screenplay.md` + 配音清单
+ `workflows/` 下三份 marker 触发的工作流（生成 / 出片 / 听检）。之后按 [`新题目开工手册.md`](新题目开工手册.md) 一步步填。

参考项目 `production/gilgo/` 只被读取、不被修改，这一条有测试守着。

## 闸门（不许出片的几种情况）

1. `generate.py --validate` —— 时间轴、提示词、配音文本与剧本逐字一致、配音 SHA-256；
2. `clause_times.py --check-cuts` —— 剪辑切点必须落在分句停顿窗内；`render.py::make_edl` —— 每个镜头只用一次、全部用到、EDL 无缝；
3. `render.py` 开头 —— 素材必须是 `results.json` 里 SHA-256 对得上的 Agnes 片段，不许用图片/幻灯片顶替；
4. `build_audio.py` —— 整体电平 / 波峰因数 / 静音占比 / **逐段**解说电平；
5. `render.py` 收尾 —— 对**最终 mp4** 复测一遍，不达标直接失败；
6. `verbatim_check.py`（Actions）—— 成片转写与剧本的字错率，逐章 ≤ 0.15。

吉尔戈成片实测：`-20.03 dBFS RMS`、峰值 `-1.43 dBFS`、静音占比 `0.55%`，逐章 CER 0.007–0.073
（见 [`production/gilgo/delivery/`](production/gilgo/delivery/)）。

## 本地跑

```bash
python3 -m pip install -r production/requirements.txt   # 另需 ffmpeg/ffprobe 与中文字体
python3 -m pytest production/tests -q                   # 离线测试
```

当前环境实测（2026-09-21，有 ffmpeg + 全部依赖）：`119 passed`。
没有 ffmpeg 时会跳过"要真解码才测得出来"的用例（电平、混音复现）；
没有本机 CJK 字体时会跳过 1 个信息卡渲染用例（Actions 运行器装了 `fonts-noto-cjk`，不会跳）。
`pyyaml` 写在 `requirements.txt` 里但不是硬依赖：不装也有 4 条工作流守卫生效。

## 复现实测（换一台机器量，还是同一组数字）

参考项目的混音在**另一台机器、另一个 ffmpeg 构建**上重跑，与云端出片时的记录
**逐项差 0.00 dB**：混音 -21.08 dBFS RMS / 峰值 -1.51，成片 -21.09 / -1.52，
逐章 N01–N06 全部一致。数据见
[`production/dahlia/delivery/reproducibility-2026-09-10.json`](production/dahlia/delivery/reproducibility-2026-09-10.json)，
并且由 `production/tests/test_dahlia_mix.py` 钉住（容差 0.05 dB）。

## 出片

本地：`bash production/run_project.sh <slug> [skip_asr] [成片文件名]`。
Actions（推荐，marker 文件触发——沙箱 token 跑不了 `workflow_dispatch`）：
在分支上写 `production/<slug>/GEN_REQUEST`（生成）/ `RENDER_REQUEST`（出片）/ `VERBATIM_REQUEST`（听检）/
`RELEASE_UPLOAD_REQUEST`（传 release）并 push，对应工作流由 `new_topic.py` 生成、复制到 `.github/workflows/` 即可。
旧的「解说短片出片」手动工作流仍在（`film_name` 留空会用 `story.json` 的标题当片名，重跑 dahlia 要填
`黑色大丽花_三分钟_带声音.mp4`）。

工作流的输入怎么传到脚本、脚本怎么用第 3 个参数，都有测试守着
（`production/tests/test_workflows.py`）。

## 事实边界

- AI 画面一律标注「AI动画情景重现 · 非新闻影像」，不冒充真实影像；
- 真实人物只以背影、剪影、手出现（或有出处的档案照片），不用 AI 生成的脸冒充本人；受害者不以人像出现；
- 不展示遗体、血腥或侵害过程；未侦破/未定论的事不指认责任人；
- 中文姓名、日期、字幕一律后期添加，不交给视频模型拼写；
- 每个镜头只出现一次，不复用；只有 Agnes 生成的视频片段算素材，不用图片幻灯片冒充动画。
