# 黑色大丽花 · 三分钟悬疑纪实

## 当前状态

已接收并抽帧分析参考视频，已完成原创解说、30个叙事单元、24段 Agnes 画面提示词、6段后期信息图，以及 Agnes 客户端的13项离线测试。

**尚未启动实际视频生成，也未生成最终 MP4。** 当前 Arena 的 GitHub App 连接不能更新 `.github/workflows/ai-shots.yml`：GitHub 返回缺少 `workflows` 权限。

源视频不提交到 Git。生成视频也不自动提交到 Git，仅把任务状态、校验信息和模型返回的素材地址保存到当前制作分支；视频本体使用 Actions artifacts。

## 文件

- `reference_analysis.md` / `reference_metrics.json`：可核查的读取范围、抽帧观察和自动剪辑节奏粗测。
- `screenplay.md`：原创剧本、证据边界、资料来源与镜头衔接。
- `story.json`：精确180秒的时间线、人物/场景连续性约束、英文正负向提示词。
- `generate.py`：只调用 `agnes-video-v2.0` 的生成程序；任务编号会被记录，避免对已提交任务盲目重建。
- `ai-shots.workflow.yml`：等待授权后启用的完整工作流文本。该普通文件本身不会触发 Actions。

## 解除权限阻碍

首选：在 Arena 中重新连接 GitHub，并在 GitHub 授权界面允许更新 Actions 工作流。无需向代理发送任何密码、令牌或 API 密钥。

也可以由仓库所有者在 GitHub 网页中，**仅在 `arena/01a083bb-desktop-tutorial` 分支**，手动用本目录 `ai-shots.workflow.yml` 的内容替换 `.github/workflows/ai-shots.yml`。

不要直接运行未经替换的旧工作流；旧版本固定签出另一个历史分支，不是本次项目。

工作流内部使用已有的 `secrets.AGNES_API_KEY`；代理不需要也不会读取密钥值。

## 权限恢复后的执行顺序

1. 在本次固定分支启用工作流。
2. 先生成 `S01`，检查模型、返回画幅、实际时长和基本质感。
3. 首个镜头通过后生成其余镜头，最多两个请求并行；不自动改用其他提供商。
4. 对生成片段做人物、服装、道具、动作方向和画面畸变检查。
5. 配音选择与录制；按真实录音对齐字幕，不截断句子。
6. 使用信息图、视觉匹配切换和声音桥剪辑；依据参考片约3.2秒的中位切换间隔调整景别，叙事单元不等于强制6秒不切镜头。
7. 混音并输出1920×1080、180秒MP4；验收实际时长、音画同步、字幕安全区和可播放性。

## 本地离线检查

```bash
python3 production/dahlia/generate.py --validate
python3 production/tests/test_agnes_video.py
```

## 工作流调用（启用后）

```bash
gh workflow run ai-shots.yml --ref arena/01a083bb-desktop-tutorial \
  -f payload='{"only":"S01","workers":1}'
```

首镜头验收后才运行全量任务。该运行会保留相同提示词已有的完成记录，并恢复已存在的任务编号。
