# 跨分支 Agnes 生成方式对照（2026-11-11）

本报告只读检查其他分支及当前分支回执；没有在其他分支创建任务，也没有在当前分支新建视频任务。

## 对照一：旧分支 `arena/ed1fa571-desktop-tutorial` / `nowon2021`

- Actions run [42583099084](https://github.com/32r4e2q-hub/desktop-tutorial/actions/runs/42583099084) 是多轮续跑中的最后一轮；其 `results.json` 为 `phase=clips_ready`、30/30 `completed`。
- 回执统计：30 个最终任务、总 `create_attempts=58`、单镜最多 7 次；任务创建时间从 2026-11-09 01:40:37Z 到 08:14:04Z。两次创建间隔最小 12 秒、中位 301 秒，说明它不是 6 分钟内一次性塞满队列，而是横跨数小时退避/续跑。
- 实际 `request_payload` 使用 `model=agnes-video-2.5-flash`、`mode=reference`、`images=[1–5 个固定 raw URL]`；30 镜回执里保存这些请求字段。该分支 README 引用 Agnes Video 2.5 Flash 官方文档并记录该 schema。
- 调度器比当前分支更保守：单一串行 creator + 独立 poller/下载池；POST 与 GET 共用 12.1 秒 request gate；同一 task 至少 45 秒才再次 poll；队列满至少等 60 秒、capacity 类错误至少等 120 秒；含糊的创建响应记为 `create_unknown` 后停止，不盲目重发；不自动重新付费创建失败 task；预算将尽时留出 10 分钟不再创建，并由工作流自动续跑。

这提供了较强的仓库内实证：相同 Agnes 2.5 Flash `reference` schema 曾在服务端被接受，30 个任务全部完成。它不是本次直接抓取官方站点文档的结果；也不替代对当前成片的视觉审核。

## 对照二：最近分支 `arena/4d042fa6-desktop-tutorial` / `motel2026`

- run [42930325736](https://github.com/32r4e2q-hub/desktop-tutorial/actions/runs/42930325736) 成功。分支回执记录 30/30 镜头完成，`phase=delivery_ready`，180 秒、1920×1080、24fps；最终成片有独立人工最终复核记录。
- 但这套近期生成器 `full_payload()` 明确发 `mode=text`，没有 `images`。所以它证明文本模式出片流程可工作，不能作为 reference-mode 图像输入的证据。
- 它的每镜回执同样声明 12 秒最小创建间隔、最多 2 workers、尊重 Retry-After、capacity 失败无限重试。故“12 秒 + 两个 worker”本身不能单独解释本次停滞；还要看服务端队列、请求形状和并发请求。

## 本分支本次运行

- 生成 run [42953032851](https://github.com/32r4e2q-hub/desktop-tutorial/actions/runs/42953032851) 于 03:28:56Z 开始，按用户指示在 03:40:16Z 被 stop workflow 取消（约 11 分 20 秒）。S01、S02 分别于 03:30:00Z、03:30:12Z 得到 task ID；S03–S30 没有保存的 task ID。
- 独立状态查询显示 S01/S02 在 03:55:39Z 仍是 pending、0%；到 03:59:21Z 两者才变为 completed、100%。仅 S01/S02 在 run [42956363021](https://github.com/32r4e2q-hub/desktop-tutorial/actions/runs/42956363021) 被回收并通过解码检查；这表明 Agnes 上游处理至少花了约 25–29 分钟，不能用“每分钟最多 5 次创建”推断 provider 也会及时完成。
- 当前脚本允许最多 2 个 worker，12 秒 gate 只在创建时预留间隔；两个 worker 的 polling 可按每 task 25 秒并发发 GET。当前识别到容量错误后的最小退避也是 12 秒，重试不封顶，且没有 `nowon2021` 那套逐镜自动续跑策略。
- 当前生成 run 的完整日志下载两次均被 GitHub log service 返回 EOF；因此**没有证据断定**当时具体命中 429、queue-full、连接超时或别的 provider 错误。S03–S30 的 `retrying_create` 记录也没有足够信息证明服务端从未收到任何无回执请求。

## 判断与建议

最有证据支持的解释是：本次遭遇了慢处理/容量背压；S01/S02 在 run 取消后仍继续完成，S03–S30 则在创建/重试阶段没有得到已保存回执。由于日志不可读，不能把它定性为 reference schema 被拒，也不能把某个限流错误说成已证根因。用户要求停止后我们取消了 workflow，故它没有继续等待剩余任务，也没有再发起新视频请求。

要安全继续，应移植 `nowon2021` 的串行创建、全局 POST/GET gate、明确的容量退避、`create_unknown` 防重复、长预算断点续跑和自动续跑机制；保留当前 S01/S02 的已完成回执，不重建、不重复计费。S01 的运动仍需完整播放审查；在完成调度器修正和 S01 视觉处理前，维持当前 retrieve-only marker，不启动 S03–S30。
