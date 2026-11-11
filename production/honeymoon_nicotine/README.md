# 蜜月尼古丁命案：新婚第十一天

3 分钟 / 30 镜 / 180 秒 / 16:9 横屏。全部画面规划为虚构写实 3D 动画情景重现，不是历史影像。素材由 Agnes Video 2.5 Flash 生成，720P 源片后续放大至 1920×1080。

## 本轮状态（2026-11-11）

- ✅ `story.json`：30 镜、180 秒、16:9、旁白草案、角色锚点与内容安全约束；`generate.py --validate --clips-only` 离线通过。
- ✅ 31 张批准参考图及逐张 QC、哈希记录见 `reference/REFERENCE_QC.md` / `reference/approvals.json`。
- ✅ 找到仓库内的 reference-mode 实证：旧分支 `arena/ed1fa571-desktop-tutorial` 的 `nowon2021` README 引用 Agnes 2.5 Flash 官方 schema，`generate_clips.py` 提交 `mode=reference` + 1–5 个 `images`，其 `results.json` 保留实际图片 payload 且 30/30 任务完成。当前 S01/S02 也以同一字段形状完成并已回收。由此可确认该 schema 在 Agnes 服务端至少曾可用；参考依据：[旧分支 README](https://github.com/32r4e2q-hub/desktop-tutorial/blob/arena/ed1fa571-desktop-tutorial/production/nowon2021/README.md)、[生成器](https://github.com/32r4e2q-hub/desktop-tutorial/blob/arena/ed1fa571-desktop-tutorial/production/nowon2021/generate_clips.py)、[30镜回执](https://github.com/32r4e2q-hub/desktop-tutorial/blob/arena/ed1fa571-desktop-tutorial/production/nowon2021/results.json)。这属于仓库运行实证；不是本次直接抓取官方站点文档。
- ⚠️ 暂停创建 S03–S30 的原因改为：当前批次的服务端容量/重试过程缺乏可读日志，且 S01 的运动真实性仍未通过完整播放检查；不能把参考图 schema 当成本次卡住的已证根因。
- ✅ 旧生成 workflow `42953032851` 已取消；S01/S02 的既有 Agnes task 在 2026-11-11 03:59 UTC 查询为 `completed` / 100%，未创建新任务。
- ✅ 已只下载这两个既有任务的输出：均为 1280×720、24fps、5.184 秒，并通过解码检查；字节数、SHA-256 与接触表见 `results.json`、`qa/S01.json`、`qa/S02.json`。源片/接触表来自 Actions run `42956363021`；视频本体在 Actions artifact，完整播放检查仍待完成。
- 🔎 接触表初检：S02 可见男子出门并沿走廊移动，外观大致符合 C01 锚点；S01 场景与酒店外景参考图相符，但采样帧主要呈逐渐推进，未能证明有独立场景运动。S01 暂不通过“不可用静态图推拉”的要求；须看完整视频再判定。两镜最终视觉审核仍为 pending。
- ⏳ S03–S30 没有已记录的任务 ID 或成片；全片、逐 5 镜角色一致性抽检、字幕/音效合成和最终 QC 均未完成。当前 `GEN_REQUEST` 为 `mode=retrieve`，只允许回收已完成任务，不会创建视频。
- 🟡 中文旁白：用户已选择低沉悬疑男声 `voice-00`，已生成 S01–S10 的第一批试听/制作音频；因脚本复核调整，S04/S05 待按最终台词重生成。字幕、音效、封面、最终 1080P 合成及 QC 尚未完成。
- ⚠️ 判决、保险、时间线、前女友相关口播先按用户脚本梳理；发布前应逐项对照法院或新闻来源核实。所有内容均标注为情景复原，不披露可模仿的致害细节。

## 生成

```bash
python3 production/honeymoon_nicotine/build_story.py
python3 production/honeymoon_nicotine/generate.py --validate --clips-only
```

`.github/workflows/honeymoon-nicotine-gen.yml` 监听本项目的 `GEN_REQUEST` marker：`mode=status` 仅查询既有 task；`mode=retrieve` 仅下载并解码已完成 task；只有 `mode=clips` 才会创建新视频任务。当前 marker 保持 retrieve-only。**在 Agnes 2.5 Flash 图像参考接口得到确认、S01 通过完整运动检查之前，不要切换到 clips。** 真正创建任务时共享创建间隔至少 12 秒（每分钟最多 5 次），尊重服务端 Retry-After。
