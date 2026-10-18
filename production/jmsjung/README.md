# JMS 郑明析案｜自称救世主的人，为什么最终站上被告席？

三分钟横版（16:9 · 180 秒）中文犯罪解说短片，**写实电影级 3D 动画**情景重现。
本目录目前产出的是**视频片段**（30 镜 × 6 秒 = 180 秒），配音与剪辑是下一阶段。

- slug：`jmsjung`　分支：`arena/929dc8b6-desktop-tutorial`
- 内容来源：用户上传的脚本 `抖音文案/20261017-111910_粘贴的文案_20261017-111910.txt`
  （本目录留了一份 `source-script.txt`，防止原稿被后续上传覆盖后无法追溯）
- 事实来源：[`史实核对.md`](史实核对.md)（10 条公开来源，逐句对照）
- 模板：仓库里的 `production/kitakyushu2002`（北九州案）——**引擎照搬，内容全部重写**

## 规格

| 项 | 值 |
|---|---|
| 生成模型 | `agnes-video-2.5-flash`（免费档，720P，单条 4–12 秒） |
| 分镜 | **30 镜 × 6 秒 = 180 秒**，与上传脚本一一对应，无信息卡 |
| 画面 | 统一风格前缀 + 每镜脚本里的 English Visual Prompt + 红线约束 |
| 排队策略 | 免费池 `503 video queue is full` 时 **每 180 秒试探一次**（2026-10-16 本仓库探针实测：60 秒间隔 6 次全灭，180 秒间隔第 5 次成交） |
| 创建间隔 | 75 秒（免费档视频 1 RPM，`throttle.py` 全局限流，不做任何绕过） |
| 断点续跑 | 每镜按请求 SHA-256 + 文件 SHA-256 记账，重跑只补没完成的 |

## 怎么跑

```bash
# 只校验时间轴（不花额度）
python3 production/jmsjung/generate.py --validate --clips-only

# 触发 Actions 生成（改这一行再 push，工作流按路径触发）
echo '{"workers":2}' > production/jmsjung/GEN_REQUEST
git add -A && git commit -m "jmsjung: 生成" && git push

# 单镜重做
echo '{"only":"S07"}' > production/jmsjung/GEN_REQUEST
```

生成结果：

- `results.json`：每镜的状态、video_url、字节数、SHA-256、解码检查结果
- `qa/Sxx.jpg` + `qa/Sxx.json`：每镜 14 帧接触表，用来人工查畸变、换脸、伪文字
- 大视频不进 Git，只在 Actions artifact `jmsjung-agnes-<run>` 的 `work/jmsjung/clips/` 里

## 内容红线（写在每次请求里）

- 不虚构真实对白：录音只做物件与波形，不给内容。
- 不展示性侵、暴力、遗体：只用环境、光影、人物反应暗示。
- 不做真实人物肖像还原：被告只以背影、剪影、手、远景出现。
- 受害者不给可辨识面容：背影、侧影、手，或不出现。
- 画面里不出现可读文字、标志、水印、字幕（文字一律后期添加）。

## 与北九州模板的差异

| | 北九州（kitakyushu2002） | 本片 |
|---|---|---|
| 分镜网格 | 45 镜 × 4 秒（38 动态 + 7 信息卡） | 30 镜 × 6 秒（全动态） |
| 排队满冷却 | 90 秒 | **180 秒**（按用户指定 & 本仓库实测） |
| 生成路线 | 智谱 CogVideoX-Flash | **Agnes `agnes-video-2.5-flash`** |
| 本阶段产出 | 成片 + 全帧 QC | **视频片段**（`--clips-only`，不做 TTS/剪辑） |

## 失败记录：2026-10-17 11:36Z（run 39028605641）

第一轮跑 11 分 33 秒就停了，**0 镜、0 秒素材**。原因不是模型下线，也不是 key 有问题，是**我移植模板时留下的一个判错**：

- 模板的 `ChannelBreaker` 把「`503 video queue is full`」和「`503 no available channel`」当成同一类，
  共用 `error_limit=3`：连续 3 轮容量报错就放弃整轮。
- 但这两件事性质完全相反：
  - `no available channel` = 模型没有通道，**永久**，等多久都不会好；
  - `queue is full` = 免费池排队满，**每一次请求都是一次抽签**。
- 按 2026-10-16 本仓库探针的真实时间线（07:36 / 07:39 / 07:42 / 07:45 全满，07:48 受理），
  旧熔断器会在**第 3 次（07:42）**就放弃——**那次最终成功的运行也会被它掐死**。

修法：`capacity_problem()` 现在返回「性质」，`ChannelBreaker.observe(kind=...)` 分两条路：

| 性质 | 策略 |
|---|---|
| `channel`（没有可用通道） | 照旧：连续 3 轮 → 冷却 300 秒 → 放弃 |
| `queue`（排队满） | **不熔断**：每 180 秒抽一次，直到墙钟预算 `queue_wait_minutes`（默认 110 分钟）用完 |

回归测试：`production/tests/test_jmsjung.py::QueueLotteryTests`——用 10-16 的真实时间线，
断言「第 5 次必须能走到」，另有一条断言「没有通道仍要 3 轮就放弃」。

## 失败记录：2026-10-17 16:42Z（run 39037939402）——接力链断在「误判真 bug」

第 2 轮跑了 2 小时 56 分，**57 次抽签抽中了 S01**（15:15 建任务、15:26 出片，
720P/6.6 秒/24fps，本片第一个真实镜头）。但收工时其余 29 镜的失败文案是
`Provider cooldown would exceed the generation budget`——**排队冷却把生成预算顶穿了**，
是「免费池还没开闸」，却被旧代码当成普通失败：`phase=generation_incomplete`、退出码 1。
`auto_resume` 按「退出码 1 = 真 bug，不接力」的契约停摆，自动接力链就此断裂。

顺带发现一个排障陷阱：`record_outage` 对排队满也写「provider channel unavailable」
标签，57 次全是排队满，日志却像通道故障——这次把标签改回实际性质
（`video queue is full (抽签 N)`）。

修法：`classify_incomplete_round()` 把「轮末没跑完」分成两出口——

| 情形 | 判定 |
|---|---|
| 本轮撞过免费池（breaker 容量事件 > 0）**且**没有镜头的报错落在容量文案之外 | `provider_capacity` + 退出码 **42** → 自动接力 |
| 有一个镜头的报错对不上容量文案（400、下载校验、缺 key……） | `generation_incomplete` + 退出码 **1** → 停下等人修 |

宁可停一轮，也不把真 bug 伪装成「供应商没货」；反过来，「还在排队」也绝不再
伪装成 bug 把接力链掐死。

回归测试：`production/tests/test_jmsjung.py::RoundEndClassificationTests`——
含一条用 run 39037939402 真实收尾数据（S01 成 + 29 镜冷却顶穿 + 57 次容量事件）
的复现用例，断言必须判 42/provider_capacity。
