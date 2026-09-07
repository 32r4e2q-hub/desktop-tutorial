# 《白教堂的雾 — 开膛手杰克》最终交付包（本次会话重建 + 提供链接）

## 一句话结论

**你说的那份 113.2 MB 的 v4 文件已经不存在了**，它当年只落在那个会话的沙箱目录里、没有进 Git；
本次把 **仍在 Git 里的最终成片（87,559,177 字节，v4.1）** 取出来，重新做了 30s 预览 + 海报帧，
并用带 Range 的 HTTP 服务给出可直接点开/下载的链接。

## 为什么那份 113.2 MB 找不回来（可复核的证据）

| 检查项 | 结果 |
| --- | --- |
| 会话 `01a07943` 分支 `ripper/.gitignore` | 明确忽略 `output/`；`ripper/play_server.py` 里 `FULL = ripper/output/白教堂的雾_开膛手杰克_1080x1920_交付版_v4.mp4`，`PREVIEW = output/preview_30s.mp4`，`POSTER = output/poster_frame.jpg` —— 三个交付文件全在被忽略的目录 |
| 该分支 Git 树 | 无任何 `.mp4` 成片、无 `preview_30s.mp4`、无 `poster_frame.jpg`（只有 28 个源镜头、10 段旁白、字体、脚本） |
| 仓库全部 26 个 Actions artifact | 只有 `ai-shots-*`（24–56 MB，源镜头包）和另一项目「阴曹使者-10分钟电影解说-720p」（81–192 MB）；没有 ≈113 MB 的本片成片 |
| GitHub Release | 该会话记录里写「Release 附件上传失败」；本次实测同样失败：沙箱到 `uploads.github.com` 出网被阻断（`curl` 返回 000 / SSL_ERROR），`raw.githubusercontent.com` 也不通 |

结论：Arena 的沙箱是一次性的，**只有提交进 Git 的字节会留下来**。上一会话没提交的那份导出，任何链接都无法恢复——我不会给一个假装还能用的旧链接。

## 本次给你的三个交付件

| 文件 | 说明 | 大小 | SHA-256 |
| --- | --- | --- | --- |
| `ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4` | 完整成片（本包内为 Git blob 的原样导出，逐字节校验通过） | 87,559,177 B | `03d838ccea317d42d864dbf35257fb16ce64c3b308a4c6f6668acd6b6cbb88d6` |
| `preview_30s.mp4` | 30s 预览（片头 0–30s：雾街 → 片名卡 → 案情钩子，带旁白与字幕）1080×1920 · H.264 CRF24 · AAC 128k · faststart | 15,890,100 B | `3170fa5edb3752d8…d86b8d` |
| `poster_frame.jpg` | 海报帧 / 封面：t=7.0s 片名卡「白教堂的雾 · 1888 开膛手杰克」，1080×1920 | 154,206 B | `a2ba2fb131014c30…95553c` |

附带：`poster_alt_ending.jpg`（备选封面，结尾“他是谁？”）、`preview_sheet.jpg`（28 镜总览）、
`subtitles.srt`（47 条）、`timeline.json`（28 镜入出点）、`qc_report.json`、`final_manifest.json`、
`发布说明_v4.1.md`、`SHA256SUMS_v4.1_upstream.txt`。

## 链接 A：本次沙箱内即时链接（可直接播放/下载，沙箱回收即失效）

<https://8017-i2n10w6pv0wzpnjrloffn.e2b.app>

- `/` —— 播放页（成片 / 预览 切换 + 全部文件下载列表）
- `/movie.mp4` —— 完整成片；`/preview.mp4` —— 30s 预览；`/poster.jpg` —— 海报帧；`/poster_alt.jpg` —— 备选封面
- `/subtitles.srt`、`/timeline.json`、`/qc_report.json`、`/final_manifest.json`、`/preview_sheet.jpg`

服务端 `deliverable/serve.py`：HTTP/1.1 + `Accept-Ranges: bytes` + 206 分片（实测 `Range: bytes=0-1023` 返回 206、`Content-Range` 正确），
配合成片本身的 `+faststart`（`ftyp → moov → mdat`，moov 在偏移 32）实现边下边播 / 任意拖动。

## 链接 B：固定地址（Git 里的本体，长期有效，需登录有该私有仓库权限的账号）

- 成片（87.6 MB，blob 已在仓库中）：
  <https://github.com/32r4e2q-hub/desktop-tutorial/blob/arena/01a076fd-desktop-tutorial/ripper/deliverable/ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4>
  直链：<https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/arena/01a076fd-desktop-tutorial/ripper/deliverable/ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4>
- 本包（预览 / 海报 / 服务脚本 / 本文档）：<https://github.com/32r4e2q-hub/desktop-tutorial/tree/arena/01a07be4-desktop-tutorial/deliverable>

> 87.6 MB 低于 GitHub 单文件 100 MB 上限，所以本体能进 Git；113 MB 那一档无论哪个会话都进不来（GitHub 会直接拒收），这也是这类导出必须另存网盘/OSS 的原因。

## 成片规格（本次在本沙箱实测，不是转抄记录）

- 容器：`ftyp/mov`，`moov` 前置（faststart，可流式播放）
- 视频：H.264 High@4.1，yuv420p，1080×1920，24 fps，4615 帧，192.29 s，约 3474 kb/s（`-b:v 3500k -maxrate 5000k`）
- 音频：AAC-LC 48 kHz 立体声 约 162 kb/s；整片响度 −16.85 LUFS / 真峰值 −2.07 dBTP（`loudness_report.json`）
- 完整性：本次 `ffmpeg -xerror` 全片解码 **无错误**（39.3 s 跑完）；SHA-256 与 `final_manifest.json` 记录一致 → 与上一会话提交进 Git 的字节完全相同
- QC（上一会话产出，随包附上）：全片解码 / 帧数 / 尺寸帧率 / 编码格式 / 黑场冻结抽样 / 音量 / 10 段旁白起点相关性与偏移 ≤0.10 s / 47 条字幕安全宽度 —— 全部通过

## 与「113.2 MB · H.264 **CRF24**」的差异（说清楚，不含糊）

入库的 v4.1 是 `-b:v 3500k -maxrate 5000k` 的 ABR 二压，不是 CRF24 两遍；
两者是同一批素材、同一条时间线的不同封装档，画面内容一致，体积/码控策略不同。
若你确实要 CRF24 那一档，可选（都需要重新导出，**不是找回原文件**）：

1. 只重压：以现有成片再走一遍 `-crf 24`（一次额外代际损失，约 6 分钟，通常体积更小）；
2. 全量重渲：在本仓 `ripper/` 里跑 `finish.py`（2 核 / 3 GB 环境约 30–60 分钟），从源镜头重画到封装，输出自定义 CRF24 交付档。

说一声即可，我按你选的那条做。

## 本地自取

```bash
python3 deliverable/serve.py 8017      # 起本包 HTTP 服务（Range 支持）
sha256sum -c deliverable/SHA256SUMS.txt  # 校验
```
