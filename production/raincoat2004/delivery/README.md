# 交付件清单 · 韩国雨衣杀手柳永哲（三分钟横版）

**成片**：`交付/韩国雨衣杀手柳永哲_十个月，二十条人命_三分钟_带声音.mp4`
**SHA-256**：`e70689acf8b43f393b627835d7c637a1475ebc80d5c95596fc4e3c0929ea7c20` · 65,449,488 bytes · 1920×1080 / 30 fps / 180.0 s / 5400 帧

> 认版本只看 SHA-256，不看文件名与大小（每次重渲 mp4 的时间戳都会变）。
> 本片出过两版：第一版字幕 43 px，第二版（**本版**）按用户要求调到 **60 px** 并重渲染、
> 重跑听检与全帧 QC——旧报告对新成片一律作废。

| 文件 | 内容 | 绑定成片的方式 |
|---|---|---|
| `technical-report.json` | 规格 / 解码复测 / 混音实测 / 素材计数 | `sha256` 字段 = 上面的 SHA |
| `verbatim-check.json` | 六章逐字听检（faster-whisper small，上限 CER 0.15；本片 0.028–0.054） | `film_sha256` 字段 |
| `visual-qc-summary.json` | 全帧 QC 摘要（黑帧 / 冻结 / 时序 / 人脸 / 手部） | `sha256` 字段 |
| `frame-distortion-audit.json` / `.md` | 5400 帧逐帧指标 + 汇总 | `sha256` 字段 |
| `face-cast-report.json` + `face-cast/` | **露脸模式画面闸门**：逐镜检脸、每个角色一张人脸接触表、同角色/跨角色相似度分诊 | `sha256` 字段 |
| `audio-report.json` / `final-audio-report.json` | 配音与混音测量（成品实测 RMS −20.32 dBFS / 峰值 −1.70 dBFS） | 制作批次（最终批次即本片） |
| `caption-timing.json` / `captions.srt` | 字幕时间轴（60 px 版） | 制作批次 |
| `alignment-report.json` / `narration-timing.json` | 分句对齐与旁白节奏 | 制作批次 |
| `edit-decision-list.json` | 45 段 EDL（每镜入出点与用途） | 制作批次 |
| `final-contact.jpg` | 45 段中点帧拼图 | 制作批次 |
| `face-cast-prompts.json` | 静态闸门报告（生成之前的 token 一致性 / 撞脸检查） | 与 `cast.json` 同批 |

**评审证据（artifact，不入 Git）**：全帧接触表、手部动态表、原始分辨率候选帧在
`.github/workflows/raincoat2004-visual-qc.yml` 的 artifact `raincoat2004-final-frame-qc-*` 里。

**人工签收**：`visual-qc-summary.json` 的 `human_semantic_visual_review` 与
`technical-report.json` 的 `visual_review` 都是 `pending`——机器不替人签收；
露脸模式的相似度报告同样只是分诊，判决看 `delivery/face-cast/` 的接触表（同一角色跨镜是不是同一张脸）。
