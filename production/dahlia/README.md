# 黑色大丽花 · 三分钟悬疑纪实

## 已确认的状态

- 参考视频已在此前完成抽帧观察和镜头节奏粗测；读取范围见 `reference_analysis.md`。
- 用户已选定中文配音，六段实际录音及对应文本/摘要保存在 `audio/`。
- 用户启动的 [首次运行 34304398402](https://github.com/32r4e2q-hub/desktop-tutorial/actions/runs/34304398402) 成功生成了 S01（Agnes 返回约7秒、1920×1088，约1.8MB）。
- 首次运行等待首镜头验收30分钟后超时结束。**其余镜头没有在该次运行中提交，也没有生成三分钟成片。**
- 当前工作环境无法直连 Agnes 视频存储，也无法下载 GitHub 的 Azure artifact 文件；没有据此伪造画面验收或批准记录。

## 本次修复：生成、检查图与剪辑都在 GitHub 中完成

原来的阻塞式首镜头等待已移除。新的完整运行会：

1. 校验录音文本和文件摘要，复用已完成且提示词摘要匹配的 S01，不重新请求它。
2. 继续使用 **Agnes Video V2.0** 生成其余镜头，最多两个请求并行，不自动换模型。
3. 在 GitHub runner 上下载并解码检查每条素材，生成每秒2帧的抽样检查图。
4. 只把必要的小尺寸检查图、参数和状态保存到当前分支，以便代理通过正常 GitHub 接口读取。**大视频不提交到 Git。**
5. 在云端使用真实录音和35段剪辑时间线合成：中文字幕、少量黄色关键词、原创程序配乐及物件音效桥。
6. 尝试在 runner 本地进行中文 ASR 辅助字幕对齐；若模型下载或匹配失败，明确记录为停顿估算，不冒充逐字强制对齐。
7. 输出严格180秒、1920×1080、30fps的 **初版 MP4**，连同字幕和技术报告保存在 Actions artifact。

自动技术检查**不是**人工画面/听感审核。输出和报告会保留“初版、待审核”标记，只有真正检查后才另行记录审核结论。不会把静态图或测试视频冒充 Agnes 成片。

## 重新启动完整任务

无需再次修改 `.github/workflows/ai-shots.yml`，也无需提供密钥。当前 Arena 连接仍不能代用户启动 Actions，因此需要用户在网页启动一次新运行。

1. 打开 [Generate AI video shots](https://github.com/32r4e2q-hub/desktop-tutorial/actions/workflows/ai-shots.yml)。
2. 点击 **Run workflow**，分支选择 **`arena/01a083bb-desktop-tutorial`**。
3. `payload` 输入：
   ```json
   {"only":"","workers":2}
   ```
4. 点击绿色 **Run workflow**，回到对话告知「已重新启动」。

请使用 **Run workflow 创建新运行**，不要对旧运行使用 Re-run jobs：旧运行的 artifact 名称已经存在，新运行可避免同名冲突。

空的 `only` 表示完整项目。只填写 `S01` 会仅处理首镜头，不合成全片。

## 主要文件

- `story.json`：30个初始叙事素材单元、英文正负向提示词、连续性约束与史料来源。
- `screenplay.md`：原创解说、证据边界与镜头衔接。
- `audio/manifest.json`：用户选定的 `voice-00`、实际录音、文本和 SHA-256 绑定。
- `generate.py`：云端生成、复用素材、保存检查图与触发剪辑。
- `media.py`：真实文件的技术探测和抽帧；不把 API 请求值当作实测值。
- `render.py`：按实际录音重分配时间，35段连续剪辑覆盖5400帧，配音适度调速、保留完整句子。
- `align_audio.py`：可选 ASR 辅助字幕对齐，保留正确剧本文字，低匹配率时明确回退。
- `watch_run.py`：只读监控，从 GitHub 接收小尺寸检查图，不再依赖视频存储直连。
- `qa/`、`delivery/`：后续真实云端运行产生的检查图和报告，未生成前不预填。

## 已执行的离线检查

```bash
python3 production/dahlia/generate.py --validate
python3 production/tests/test_agnes_video.py
python3 production/tests/test_dahlia.py
.venv/bin/python production/tests/test_dahlia_edit.py
```

还使用隔离的 FFmpeg 彩条测试素材完成了 **320×180、180秒、5400帧、H.264/AAC** 的端到端编码测试，验证录音、字幕、配乐、衔接时间线和最终解码。该测试不是实际 Agnes 影片，不会交付为成片；测试文件只位于被忽略的 `.cache/`。

## 当前限制

启动 Actions 需要用户点击；素材生成、云端剪辑和 artifact 上传会在 GitHub 中继续，不需要保持浏览器预览打开。实际完成时间取决于 Agnes 排队与 GitHub runner。若某镜头缺失或摘要不匹配，剪辑会停止而不是用占位图填补。
