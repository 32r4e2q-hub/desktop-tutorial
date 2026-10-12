# 交付件清单 · 姜浩顺：一滴袖口的血，十名女人（三分钟横版）

**成片**：`交付/姜浩顺_一滴袖口的血，十名女人_三分钟_带声音.mp4`
**SHA-256**：`bc74518c8b7ec323e17ed55657af352bd61b9497f4da9dc0e13a607520198c06` · 68,685,458 bytes · 1920×1080 / 30 fps / 180.0 s / 5400 帧

> 认版本只看 SHA-256，不看文件名与大小（每次重渲 mp4 的时间戳都会变）。
> 本片共出过四版：v1（`603a3df`）首版出片后经人工复检重做了 `S13/S19/S44`（去可读字与店招）及 `S12/S14/S22/S31/S37`（改背影/俯拍构图防撞脸并绕开 1301 审核）得 v2（`71d0790`）；v2 全帧 QC 检出 `S04` 与 `S39` 各有一段 1.2–1.6 s 近静止区段，重做两镜得 v3（`5412fa2`）；v3 全帧 QC 发现 `S39` 首秒仍有约 1 s 静态起幅，遂改写 `S39` 第三版提示词（开镜即动）并重渲得 **v4 终版（`bc74518c…`）**，同步跑完逐字听检、5400 帧全帧审计与角色脸画面闸门。分诊记录见 [`AI辅助视觉复核-2026-10-12.md`](AI辅助视觉复核-2026-10-12.md)。

| 文件 | 内容 | 绑定成片的方式 |
|---|---|---|
| `technical-report.json` | 规格 / 解码复测 / 混音实测 / 素材计数 | `sha256` 字段 = 上面的 SHA |
| `verbatim-check.json` | 六章逐字听检（faster-whisper small，上限 CER 0.15；本片 0.0240–0.1171，全部 ok） | `film_sha256` 字段 = 上面的 SHA |
| `visual-qc-summary.json` | 全帧 QC 摘要（5400/5400 帧，非计划黑帧 0，非图卡冻结 0，时序窗口 21，人脸候选 511，手部事件 82） | `sha256` 字段 = 上面的 SHA |
| `frame-distortion-audit.json` / `.md` | 5400 帧逐帧指标 + 镜头统计汇总 | `sha256` 字段 = 上面的 SHA |
| `face-cast-report.json` + `face-cast/` | **露脸模式画面闸门**：逐镜检脸、每个角色一张人脸接触表（`C1/C2/C3/C5.jpg`）、同角色/跨角色相似度分诊 | 最终成片复检批次（commit `c9e6397`） |
| `audio-report.json` / `final-audio-report.json` | 配音与混音测量（成品实测 RMS −20.61 dBFS / 峰值 −1.57 dBFS / 静音占比 1.1%） | 制作批次（终版批次） |
| `caption-timing.json` / `captions.srt` | 字幕时间轴（60 px 版，`clause-times DP` 对齐） | 制作批次 |
| `alignment-report.json` / `narration-timing.json` | 分句对齐与旁白节奏（变速比 0.973） | 制作批次 |
| `edit-decision-list.json` | 46 段 EDL（38 个 CogVideoX-Flash 镜头 + 7 张信息卡 + 片尾卡，每镜只用一次） | 制作批次 |
| `final-contact.jpg` / `visual-qc-shot-midpoints.jpg` | 逐段中点帧拼图（46 段） | 制作批次 |
| `AI辅助视觉复核-2026-10-12.md` | 出片后逐张看片的记录：四版迭代、全帧审计旗标分诊、角色跨镜一致性判决、伪文字与字幕复核 | 与本版 SHA 同批 |
| `face-cast-prompts.json` | 静态闸门报告（生成之前的面容 token 一致性 / 撞脸检查） | 与 `cast.json` 同批 |
| `ref-image-probe.json` | 智谱免费档 `image_url` 首帧图探测收据 | 生成批次记录 |

**评审证据（仓库内 + Actions artifact）**：46 张分镜全帧接触表、9 张手部动态接触表与候选异常原始分辨率帧已随分支保存在 `production/kanghosun2009/qa/final-frame-review/`，同时在 Actions run [`38231788493`](https://github.com/32r4e2q-hub/desktop-tutorial/actions/runs/38231788493) 归档。

**人工签收**：`visual-qc-summary.json` 的 `human_semantic_visual_review`、`technical-report.json` 的 `visual_review` 与 `face-cast-report.json` 的 `human_review` 均保持 `pending`——机器不替人签收。
