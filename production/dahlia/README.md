# 黑色大丽花 · 三分钟悬疑纪实

## 当前状态

已接收并抽帧分析参考视频，已完成原创解说、30个叙事单元、24段 Agnes 画面提示词、6段后期信息图和离线接口测试。

用户已于2026年9月9日在当前制作分支手动保存正确的 Actions 工作流，提交为 `c60b6fe202a4ead68aaa8322e6c3c1522de9929e`。

**尚未启动实际视频生成，也未生成最终 MP4。** 尝试调用 workflow dispatch 时，GitHub 返回 HTTP 403 `Resource not accessible by integration`。这是当前连接缺少启动 Actions 的权限，并非工作流未保存或 GitHub 未连接。

源视频不提交到 Git。生成视频也不自动提交到 Git，仅把任务状态、校验信息和模型返回的素材地址保存到当前制作分支；视频本体使用 Actions artifacts。

## 只需手动启动一次

无需再改工作流，无需向代理发送密码、令牌或 API 密钥。

1. 打开 [Generate AI video shots](https://github.com/32r4e2q-hub/desktop-tutorial/actions/workflows/ai-shots.yml)。
2. 点击 **Run workflow**，分支选择 **`arena/01a083bb-desktop-tutorial`**。
3. `payload` 输入 `{"only":"","workers":2}`，然后点击绿色 **Run workflow**。
4. 回到 Arena 告诉代理「已启动」。

空的 `only` 表示完整的已审核镜头计划。程序先生成 S01，然后最多等待30分钟的人工画面验收。代理将批准记录写入当前分支的 `production/dahlia/review.json` 后，已经运行的同一个任务继续生成剩余镜头，不需要再次点 Run workflow。若首镜头失败、被否决或等待超时，不会继续提交其余镜头。

**不要选择 main 或任何历史分支。** 历史工作流指向别的项目，不是本次黑色大丽花制作。

工作流内部使用已有的 `secrets.AGNES_API_KEY`；代理不需要也不会读取密钥值。

## 文件

- `reference_analysis.md` / `reference_metrics.json`：读取范围、抽帧观察和剪辑节奏粗测。
- `screenplay.md`：原创剧本、证据边界、资料来源与镜头衔接。
- `story.json`：180秒规划时间线、连续性约束、英文正负向提示词。
- `generate.py`：只调用 `agnes-video-v2.0`；保存任务编号，并在全量任务中先等待首镜头验收。
- `ai-shots.workflow.yml`：工作流备份文本，本普通文件不会自行触发 Actions。

## 后续制作

1. 首镜头验收：模型、实际画幅、时长、动态效果及历史质感。
2. 其余镜头最多两个请求并行，不自动改用其他提供商。
3. 检查人物、服装、道具、动作方向和明显畸变。
4. 配音选择与录制，按真实录音对齐字幕，不截断句子。
5. 使用信息图、视觉匹配切换和声音桥；参考约3.2秒中位切换间隔调整景别，6秒叙事单元不等于强制6秒不切镜头。
6. 混音并输出1920×1080、180秒MP4；验收时长、音画同步、字幕安全区与可播放性。

## 离线检查

```bash
python3 production/dahlia/generate.py --validate
python3 production/tests/test_agnes_video.py
python3 production/tests/test_dahlia.py
```

## 人工验收记录格式（由代理在真实检查后填写）

```json
{
  "decision": "approved",
  "first_shot_id": "S01",
  "request_hash": "与results.json中该镜头请求摘要一致",
  "video_sha256": "与实际下载并检查的首镜头文件摘要一致"
}
```

未实际检查画面时，不创建批准记录。请求、镜头编号或文件摘要不匹配的记录不能放行后续生成。
