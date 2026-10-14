# 金大斗案 · PIXAZO 逐条生成

2026-10-14 用户明确授权：PIXAZO 替代 Agnes，沿用38个动画分镜、原旁白与180秒时间轴。

## 接口与证据
- 仓库既有接入位于 `arena/01a07943-desktop-tutorial` 的 `production/multi_video.py` 与 `.github/workflows/ai-shots.yml`（只读参考，不切换分支）；已有 `PIXAZO_API_KEY` Secret 引用。密钥仅在 Actions 内注入，不读取/打印值。
- 官方模型目录：https://www.pixazo.ai/models/ltx.md ：variant `ltx-v2-3-free`，当前显示名 LTX Video 2.5。固定 POST `https://gateway.pixazo.ai/ltx-video/v1/text-to-video`，Ocp-Apim-Subscription-Key 认证；GET `/v2/requests/status/{request_id}`。
- 官方通用免费页 https://www.pixazo.ai/api/free 的模型卡含 LTX，但 FAQ 仍称免费视频待推出，描述不一致。因此不承诺账户零扣费，不改账单设置，不充值、不用 Pro/Lite。
- 第三方示例 https://github.com/sanjaymeherdev/PixazoFreeHub 报告每模型60请求/分钟；这不是当前账户官方配额证明，不当作精确额度。具体账户额度仍可能更低。

## 实际节流（客户端保守值，不伪称官方数值）
- 并发任务上限1，逐镜提交→保存任务号→查询→下载/测量/归档→下一镜。
- 提交和查询共享至少75秒间隔（不超过0.8请求/分钟）；官方模型文档建议查询5–10秒，本方案更慢以降低请求量。
- 429按150/300/600/900秒指数退避，优先更长的 Retry-After（支持秒或HTTP日期）；队列满120/240/480/900秒，此后15分钟；无换key绕限流。
- 已受理任务只查同一编号。POST前持久化submitting；网络中断/5xx未知受理结果暂停，不盲目重发。402/余额/额度/鉴权/参数错误暂停，不无限重试。
- 明确失败的任务保留历史，15分钟后最多累计3次；下载/归档失败最多8次，始终保留原任务而不重新生成。
- 持续3小时一个Actions时段，保存断点后显式dispatch同一分支；平台额度不足或续跑失败可能中止。GitHub Actions分钟独立于PIXAZO额度。
- `PIXAZO_REQUEST.json` 的 enabled=false 并推送可停（2分钟检查一次）。Agnes `LOOP_REQUEST.json` 已关闭，避免双队列。

## 防截短与画质
- 官方free接口最多121帧，帧数1+8k；W×H×帧数超过100,000,000会自动缩短。
- 使用1024×576（16:9、32倍数）×121帧＝71,368,704，20fps得到6.05秒源片，满足原6秒素材计划，成片每镜约4秒。
- 不宣称原生1080p/30fps；最终合成到1920×1080/30fps。生成后ffprobe检查时长/尺寸/宽高比，人工视觉质量审核仍待进行。

## 持久记录
- `pixazo-results.json` 独立保存PIXAZO回执，不覆盖Agnes失败历史。
- 内容哈希命名MP4立即归档至私有仓库Release `kimdaedoo-pixazo-source-clips`。Actions14天artifact只是备份，不是唯一存储。
- 恢复命令：`python production/kimdaedoo/fetch_sources.py --results production/kimdaedoo/pixazo-results.json --dest work/kimdaedoo/sources`，Release恢复需GH_TOKEN。
- 所有素材完成不等于成片完成，之后仍需合成、字幕/声音复核与人工质检。

## 首次真实调用结果（2026-10-14 07:38 UTC）

工作流38529522117：S01 POST返回HTTP402 `card_required`，无request_id，0/38。队列paused_error，无自动续跑。不是限流，继续退避不能解决账户激活门槛。没有充值或修改支付设置。等待用户自行核对控制台激活与免费权益后恢复，保留本次回执。
