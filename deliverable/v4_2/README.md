# v4.2 CRF24 交付档（全量重渲 · 已按仓库分片方案入库）

《白教堂的雾 — 开膛手杰克》。这份是 **2026-09-08 在本沙箱从"最新保存的素材"全量重渲 + CRF24 压制**的交付档，
不是上一会话那个 113.2 MB 文件本身（那份从没进过 Git，找不回来，见 `../DELIVERY.md`）。

## 内容规格（本次实测）

| 项 | 值 |
|---|---|
| 文件 | `ripper_whitechapel_fog_v4_2_crf24_1080x1920.mp4` |
| 体积 | **100,216,657 字节（100.2 MB / 95.6 MiB）** |
| SHA-256 | `f723581d2a7954bb7925d3e245c0dde938c35061446d074af335ec916ede5902` |
| 画面 | 1080×1920 · 24 fps · **4720 帧** · **3:16.67（196.67 s）** · 27 镜 |
| 编码 | libx264 **CRF 24** / preset medium / High@4.1 / yuv420p · 视频约 3909 kb/s，容器约 4076 kb/s |
| 音频 | AAC-LC 48 kHz 立体声 161 kb/s · −20.3 dB RMS · 峰值 −1.82 dB |
| 字幕 | 内嵌烧录 + 独立 `subtitles.srt`（47 条，边界按旁白音频实测） |
| 流式播放 | `-movflags +faststart`，实测 `ftyp → moov → mdat`（moov 前置），可边下边播 |
| QC | 全片解码 `-xerror` 无错；帧数 = 期望 4720；无长黑场/冻结段；10 段旁白起点 0.57–0.81 s；见 `qc_report.json` |
| 来源 | 输入固定在 `arena/01a07943-desktop-tutorial` 提交 `4aaab744545297514c69e70fb5a76d88aec7e934`（run 17 重拍镜头 + S22 裁切 + 10 段旁白 + CJK 字体），逐文件按 git blob 校验通过；渲染管线 `RENDER_VERSION = v5-filmic-20260907` |

## 为什么在 Git 里是 3 个分片

100,216,657 字节 **超过 GitHub 仓库单文件 100 MB 上限**，整档提交会被服务端拒收；
所以沿用本仓库既有的做法（`production/new_source_parts/` 装 340 MB 的 `bailin.mp4` 时就是这么干的）：
按 45 MB 切块 + `manifest.json`（含整档 sha256）。

```
parts/movie.part-000   45,000,000 B
parts/movie.part-001   45,000,000 B
parts/movie.part-002   10,216,657 B
parts/manifest.json    整档 sha256 / size / parts 列表 / 复原命令
```

## 一条命令复原（已实测字节级一致）

```bash
mkdir -p out && cd out
BASE=https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/arena/01a07be4-desktop-tutorial/deliverable/v4_2/parts
for p in movie.part-000 movie.part-001 movie.part-002 manifest.json; do curl -LO $BASE/$p; done
cat movie.part-* > ripper_whitechapel_fog_v4_2_crf24_1080x1920.mp4
sha256sum ripper_whitechapel_fog_v4_2_crf24_1080x1920.mp4     # 应为 f723581d…5902
```

在仓库里也可以直接用校验脚本（比 sha、报行数、可选 `--emit` 落盘）：

```bash
python3 deliverable/verify_parts.py deliverable/v4_2/parts --emit 交付版_v4.2.mp4
```

浏览器里逐个下载：`parts/movie.part-000` · `movie.part-001` · `movie.part-002`（同目录 `manifest.json`），
或者在 <https://github.com/32r4e2q-hub/desktop-tutorial/tree/arena/01a07be4-desktop-tutorial/deliverable/v4_2/parts> 里下载整个目录。

## 本目录里的其他文件

| 文件 | 说明 |
|---|---|
| `preview_30s_v4_2.mp4` | 30 s 预览（0–30 s：雾街 → 片名卡 → 钩子；CRF22 · 13 MB · faststart，可直接播放） |
| `poster_v4_2.jpg` | 海报帧 / 封面：t=15.5 s 片名卡「白教堂的雾 · 1888 开膛手杰克」，1080×1920 |
| `subtitles.srt` | 47 条字幕，边界由 `vo_align.py` 从旁白音频实测 |
| `timeline.json` | 27 镜入出点 / 时长 / 所属旁白块 |
| `qc_report.json` | 本次压制与全片检查结果（`passed: true`） |
| `final_manifest.json` | 版本、来源提交、字节数、SHA-256、编码参数 |
| `probe.txt` | 容器/码流原始探测输出 |
| `SHA256SUMS.txt` | 本目录除整档 MP4 外全部文件的校验值 |

## 与另外两版的关系

- **v4.1（`../ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4`，87,559,177 B，SHA `03d838cc…88d6`）**：
  上一会话用**稍早一批素材**导出、ABR `-b:v 3500k` 压制，28 镜 / 3:12.29。它是目前 Git 里唯一"整档单文件"成片。
- **v4.2（本目录）**：素材更新（run 16–17 重拍 + S22 二次裁切）、管线更新（v5-filmic 分级）、
  按你的要求改成 **CRF24** 交付档，时长随之变成 3:16.67。两版都是同一套旁白 + 字幕策略，不是简单重编码关系。
- 上一会话提到的 **113.2 MB 那份**：从未进入 Git（当年写在 `ripper/output/`，被 `.gitignore` 排除），无法恢复；
  本版是**重新导出**，不是找回。
