# 用 Agnes Video V2.0 生成视频

`production/agnes_video.py` 封装了 Agnes AI 的异步视频接口（[官方文档](https://agnes-ai.com/en/docs/agnes-video-v20)）：
提交任务 → 轮询进度 → 下载 MP4。只依赖 Python 标准库，可以直接在 GitHub Actions 的干净 runner 上运行。

## 1. 配置 API Key（只做一次）

1. 到 <https://platform.agnes-ai.com/settings/apiKeys> 创建 API Key。
2. 打开本仓库 **Settings → Secrets and variables → Actions → New repository secret**。
3. 名称填 `AGNES_API_KEY`，值填你的 Key，保存。

> Key 只放在 GitHub Secret 里，不要贴进聊天、Issue 或代码。脚本从环境变量 `AGNES_API_KEY` 读取，日志里不会打印它。

## 2. 安装 workflow（只做一次）

GitHub 不允许 Arena 的机器人账号推送 `.github/workflows/` 下的文件，所以 workflow 以文本形式放在
`production/agnes-video.workflow.yml.txt`，需要你用自己的账号放到 `main` 分支（和 `build-commentary.yml` 当初一样）：

1. 打开 <https://github.com/32r4e2q-hub/desktop-tutorial/new/main?filename=.github/workflows/agnes-video.yml>
2. 把 `production/agnes-video.workflow.yml.txt` 的内容原样粘进去，Commit 到 `main`。

workflow 文件本身只是"遥控器"：运行时会 checkout `arena/01a06f58-desktop-tutorial` 分支上的脚本，
所以之后脚本更新不需要再改 `main`。

## 3. 在 GitHub Actions 里生成

**Actions → Generate Agnes video → Run workflow**，填写：

| 输入 | 说明 |
| --- | --- |
| `prompt` | 视频内容。推荐结构：主体 + 动作 + 场景 + 运镜 + 光线 + 风格（英文更稳定） |
| `image_urls` | 可选。1 个公网图片 URL = 图生视频；2 个以上（逗号分隔）= 关键帧动画（首张起始帧，末张结束帧） |
| `aspect` | `16:9` / `9:16` / `1:1` / `4:3` / `3:4` |
| `resolution` | `480p` / `720p` / `1080p` |
| `seconds` | 时长，最长约 18 秒（API 上限 441 帧） |
| `negative_prompt` | 可选，不希望出现的内容 |
| `seed` | 可选，固定后可复现 |

运行结束后在该次 run 页面底部的 **Artifacts** 下载 `agnes-video-<run号>`，里面是 MP4 和一份记录请求/响应的 JSON。

命令行触发也可以：

```bash
gh workflow run agnes-video.yml \
  -f prompt="A cinematic shot of a cat walking on the beach at sunset, soft waves, warm golden light" \
  -f aspect=16:9 -f resolution=720p -f seconds=5
gh run watch            # 等待完成
gh run download -n agnes-video-<run号>
```

## 4. 本地 / 其他机器上运行

```bash
export AGNES_API_KEY=...            # 或写进 .env 后 source
python3 production/agnes_video.py \
  --prompt "A young astronaut walking across a red desert planet, slow tracking shot, dramatic sunset light" \
  --aspect 16:9 --resolution 720p --seconds 5 \
  --output output/astronaut.mp4
```

常用参数：

- `--image URL`：可重复。1 张 = 图生视频；2 张以上自动进入 `keyframes` 模式。
- `--seconds` / `--frame-rate`：脚本会自动把帧数换算成 API 要求的 `8n+1` 且 `<= 441`。也可用 `--num-frames 121` 精确指定。
- `--width/--height`：自定义尺寸；API 会归一化到最近的 480p/720p/1080p 预设，实际尺寸以返回的 `size` 为准。
- `--dry-run`：只打印将要发送的 JSON，不调用接口。
- `--base-url`：如需走代理网关可覆盖（默认 `https://apihub.agnes-ai.com`）。

时长参考（24 fps）：约 3 秒 = 81 帧，5 秒 = 121 帧，10 秒 = 241 帧，18 秒 = 441 帧。

## 5. 测试

不需要网络和 Key，用内置的模拟网关跑完整流程：

```bash
python3 production/tests/test_agnes_video.py
```

## 6. 常见问题

- **401**：Key 错误或未配置 Secret。
- **400 num_frames**：帧数不满足 `8n+1`；用 `--seconds` 让脚本自动换算即可。
- **图生视频报错**：图片必须是公网可直接访问的 URL（不支持本地路径）。
- **视频在国内打不开**：Artifact 已经把 MP4 下载到 GitHub 了，直接从 Artifacts 取即可，不必访问原始视频 URL。
