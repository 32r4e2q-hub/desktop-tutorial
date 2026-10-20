# 金大斗案｜55天，17条人命，一条牛仔裤揭开真相

三分钟横版（16:9 · **180.000 秒**）中文犯罪解说短片，**写实电影级 3D 动画**情景重现。
韩国 1975 年 8 月 13 日至 10 月 7 日，55 天内 17 人遇害；最后让案件转向的，
不是神探，而是一家普通洗衣店老板娘的警觉。

- slug：`kimdaedoo`　分支：`arena/b726ea5e-desktop-tutorial`
- 内容来源：用户上传脚本 [`source-script.txt`](source-script.txt)
  （原文件：`抖音文案/20261020-114231_粘贴的文案_20261020-114231.txt`）
- 事实来源：[`史实核对.md`](史实核对.md)（11 条公开来源，逐句对照）
- 模板：仓库里的 JMS 郑明析案（`production/jmsjung`，分支 `arena/929dc8b6-desktop-tutorial`）
  ——**引擎照搬，内容全部重写**

## 规格

| 项 | 值 |
|---|---|
| 生成模型 | `agnes-video-2.5-flash`（免费档，720P，单条 4–12 秒） |
| 分镜 | **30 镜 × 6 秒 = 180 秒**，与上传脚本一一对应，无信息卡 |
| 创建节奏 | **61 秒一次**（免费池 1 RPM 的 60 秒下限；`throttle.py` 硬校验 minimum≥60） |
| 排队策略 | `503 video queue is full` 时**每 61 秒抽一次签**，110 分钟没开闸才以退出码 42 收工，自动接力下一轮 |
| 断点续跑 | 每镜按请求 SHA-256 + 文件 SHA-256 记账；重跑只补没完成的 |
| 配音 | edge-tts `zh-CN-YunjianNeural`（中文男声·低沉），`pitch=-4Hz`，逐镜对位 |
| 音乐 | 程序生成的原创悬疑 BGM（`电影解说工具包/generate_horror_bgm.py`） |
| 成片 | 1920×1080 / 30fps / H.264 / AAC 48k / −16 LUFS |

## 180 秒 vs 原稿 1438 字

原稿 30 镜 × 6 秒 = 180 秒，但 30 条旁白共 **1438 字**；按中文口播 4.5–5.5 字/秒
需要 260–320 秒，和 180 秒物理矛盾（JMS 模板最后也是保留了完整旁白、成片变成 4–5 分钟）。

本片按用户“抖音爆款 / 180 秒”的要求走 **180 秒版**：

- 每镜旁白压到 **16–30 字**，30 镜共 **666 字**，按 3.7–4.5 字/秒正好落在每镜 6 秒内；
- 完整原稿逐镜保存在 `story.json` 的 `source_narration` 与 `source-script.txt`，没有丢；
- 如果之后要“完整版”，同一批 30 镜可以再出一版 4–5 分钟的，不需要重新生成画面。

## 提示词为什么能“一次过”

生成一条要排队几十分钟到几小时，重做一条的成本远高于在本地跑 0.1 秒的闸门。所以每次生成前跑三道：

1. **`build_story.py`**：从上传脚本重建 `story.json`，CI 里用 `diff` 断言仓库里的版本没有手改漂移。
2. **`production/face_cast.py check-prompts`**：主角/老板娘的 face token 必须逐字节出现在每个露脸镜头；
   两个角色的 token 不能撞脸；没登记的镜头不许夹带别人的 token。
3. **`audit_prompts.py`**：逐镜检查
   - 一镜只有一个场景、一个连续运镜（拒绝 montage / cut to / meanwhile）
   - 没有血、遗体、性侵、武器、儿童危险、现代设备、可读文字、真实姓名
   - 模型/分辨率/秒数/模式不踩 `agnes-video-2.5` 的参数红线
   - 旁白字数 16–30、全片 600–720 字，180 秒落得进去
   - 关键事实词（55天 / 17 / 9起 / 3人重伤 / 1975 / 1976 / 27岁 / 牛仔裤）必须在旁白里

三道闸门全绿才允许推送 `GEN_REQUEST`。报告落在
[`delivery/prompt-audit.json`](delivery/prompt-audit.json) 与
[`delivery/face-cast-prompts.json`](delivery/face-cast-prompts.json)。

## 怎么跑

```bash
# 0) 本地校验（不花额度、不连 Agnes）
python3 production/kimdaedoo/build_story.py
python3 production/face_cast.py check-prompts --project production/kimdaedoo
python3 production/kimdaedoo/audit_prompts.py
python3 production/kimdaedoo/generate.py --validate --clips-only

# 1) 触发 Agnes 生成（push 本文件即触发工作流）
#    GEN_REQUEST 里 round=1；工作流自动接力，直到 30 镜全成
git add production/kimdaedoo/GEN_REQUEST && git commit -m "kimdaedoo: 开始生成" && git push

# 2) 单镜重做
echo '{"only":"S07"}' > production/kimdaedoo/GEN_REQUEST

# 3) 30 镜全成后，generate 工作流自动 dispatch 出片工作流；
#    也可以手动 push FINAL_REQUEST。
```

生成结果：

- `results.json`：每镜状态、video_url、字节数、SHA-256、解码检查
- `qa/Sxx.jpg` + `qa/Sxx.json`：每镜 14 帧接触表（人工查畸变、换脸、伪文字）
- 脚本与分镜表：[`抖音脚本.md`](抖音脚本.md)（30 镜完整旁白 + 完整提示词 + 六幕结构）
- 发布文案：[`抖音发布文案.md`](抖音发布文案.md)
- 大视频不进 Git：只在 Actions artifact `kimdaedoo-agnes-<run>` 的 `work/kimdaedoo/clips/`
- 成片：Release `kimdaedoo-v1-*` + artifact `kimdaedoo-final`

## 内容红线（写在每次请求里）

- **不虚构真实对白**：画面里不写台词，只呈现环境、动作、光影与物件。
- **不展示血腥与遗体**：受害者不出现在暴力画面里，只用空椅、书包、衣物、调查现场暗示。
- **不做真实人物肖像还原**：金大斗只是虚构重建形象，固定 face token 保持跨镜头一致，不冒充真人照片。
- **不美化犯罪**：不展示作案过程、不展示武器使用、不把贫困或前科写成犯罪的必然原因。
- **文字一律后期添加**：画面本身不出现可读文字、标语、水印或字幕；成片常驻「AI动画情景重现」。

## 与 JMS 模板的差异

| | JMS 郑明析案 | 本片 |
|---|---|---|
| 分镜 | 30 镜 × 6 秒 | 30 镜 × 6 秒 |
| 成片 | 保留完整 1366 字旁白，实际 4–5 分钟 | **180 秒版**，666 字；完整原稿留在 `source_narration` |
| 配音 | edge-tts `Yunyang` | edge-tts **`Yunjian` + pitch −4Hz**（更低沉、更悬疑） |
| 画面 | 无真人露脸 / 无 cast | **有控制的露脸**：C1/C2 两个角色、7 个露脸镜头，face token 闸门 |
| 提示词 | 脚本原样搬运 | 生产稿：一镜一场景一运镜，附原稿 `source_prompt` 对照 |
| 生成 | 61 秒排队抽签 | 同左（用户指定） |

## 目检记录（逐镜，按完成顺序）

| 镜 | 时间 | 结论 | 备注 |
|---|---|---|---|
| S02 | 2026-10-20 12:59Z | ✅ 可用 | 航拍稻田村落、白墙黑瓦、土路、远处旧客车；构图与提示词一致。唯一小瑕疵：客车造型偏“90 年代旅游大巴”，远景里可接受；若要更严谨，收尾时用 `{"only":"S02"}` 重做一次即可（不重跑其他镜头）。 |

## 失败记录

- 2026-10-20 12:02Z 起：Agnes 免费池 `video queue is full` 连续命中 56 次，第 57 次左右抽中 S02。
  生成器按设计每 61 秒抽一次签、不熔断；这是免费池的正常排队，不是流水线故障。
