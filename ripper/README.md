# 《白教堂的雾》— 开膛手杰克：v4 任务续做

**本次交付已完成：v4.1 续做版，3:12.29，1080×1920 / 24 fps，87,559,177 字节（87.6 MB）。**

全片解码、4,615 帧、10 段旁白时序、47 条字幕安全宽度检查通过；15 项回归测试通过。已抽查最终 28 镜总览和 S22 三个时间点。

## 恢复到哪里

原 Arena 会话 `01a0768f-8258-7ee8-a2e8-17d98501f1ae` 的页面无法读取。
本次只以 GitHub 已保存的文件及提交历史为依据，不声称恢复了原会话未保存的聊天、缓存或最终导出文件。

- 恢复来源：`arena/01a0768f-desktop-tutorial`，固定提交 `65c0299c7ff83c504e76932764ff13da539e2bdf`。
- 原制作分支最新编辑：`56accc4653bcbde689d7fbd8e423e71476f6d5fd`，2026-09-06 15:35:28 北京时间，S22 修剪。
- 仓库旧 MP4 是 v3，提交 `a5fe624b7be0a3a51010b17b247219ab5e20b7a5`，90,370,918 字节。
- 此后有 v4 单向时间重映射/光流、镜头重拍、S10/S13/S14/S26 修剪、N09 调整、S22 修剪，但旧 MP4 没有更新。
- 已恢复 28 个镜头、10 段既有配音；所有二进制素材均按原 Git blob SHA 校验。

**本次版本为 `v4.1-resumed-20260906`，是基于这些最新保存素材的新导出版，不是找到了原会话所说的“最后 88MB 原文件”。**
本次工作保存在当前会话分支 `arena/01a076fd-desktop-tutorial`，不修改原制作分支。

## 本次收尾

- 沿用已保存的镜头顺序、裁切、旁白、音效与油画基调，不调用收费生成接口、不换配音。
- 重建 10 段字幕停顿边界，并导出独立 SRT。停顿对齐含估算回退，并非逐词人工听校。
- 长字幕按实测字宽缩小字号，保持在画面横向 8% 安全边距内。
- 转场的入镜画面也遵守最新 `use` 和 `crop`，不再重新带入剪掉的开头。
- 抽查发现 S22 的 AI 门牌误写为“113”；本次将该镜头重新构图至窗户/水桶，去掉错误门牌，保留原镜头动作和旁白。
- 在原生 720p 素材尺寸上做画面处理和光流，然后输出 1080×1920；标题/字幕直接以 1080p 绘制。
- 内存与线程受限的分段渲染；逐段记入缓存。缺镜头、损坏配音、编码器失败均中止，不再静默导出残片。
- 修正旧封装的 `-shortest` 在音频结束于两帧之间时截掉最后一帧的问题：最终压制直接取完整画面和原始 WAV，仅补齐不到一帧的尾部静音，并严格核对全部帧数。
- 自动检查：全片解码、尺寸/帧率/帧数、H.264/AAC、黑场/冻结抽样、音量、10 段原旁白相关性及时移、字幕安全宽度。
- 最终交付附版本、来源提交、SHA-256、时间线、QC 报告、镜头总览，避免把 v3 当成新版。

自动检查不等于全部画面人工逐帧无瑕疵认证；AI 画面和沿用旁白的历史断言仍需要发布者审阅。

## 运行

```bash
# 在仓库根目录；gh 必须连接拥有该私有仓库访问权限的 GitHub 账号。
python3 -m venv .venv
.venv/bin/pip install -r ripper/requirements.txt
.venv/bin/python ripper/recover_assets.py

# 15 项回归测试。无字体时只跳过依赖字体的一项。
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -m unittest discover -s ripper/tests -v

# 完整续做：校验原素材 → 字幕 → 渲染 → 压制 → QC → 交付文件
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -u ripper/finish.py --workers 2

# 仅重新压制/验证已完成的母版，不重绘画面：
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  .venv/bin/python -u ripper/finish.py --export-only
```

长时间运行请用平台后台进程功能，不要放在会被超时杀死的短命令里。

## 文件与状态

- `deliverable/status.json`：实际阶段；只有 `complete` 表示本次交付完成。
- `deliverable/final_manifest.json`：最终版本、字节数、SHA-256、来源及生产代码指纹。
- `deliverable/qc_report.json`：本次成片检查结果。
- `deliverable/timeline.json`：28 镜时间线及最新入出点。
- `deliverable/subtitles.srt`：本次字幕。
- `deliverable/preview_sheet.jpg`：28 镜中段抽样总览。
- `/home/user/downloads/ripper_whitechapel_fog_v4_1_resumed_1080x1920.mp4`：通过自动 QC 后的交付视频；在 Arena 文件查看器下载。
- `history/v3_*`：明确归档的旧版本说明/QC，不是当前成片结果。

`source_manifest.json` 固定全部源素材版本；大文件只放在忽略的 `.cache/`、`build/`、`output/` 中。
工作区重新恢复后若缺少素材或字体，重新执行 `recover_assets.py` 即可。恢复脚本只下载已有素材，不生成新镜头。

用户要求固定下载链接后，GitHub Release 附件上传失败，因此本版 MP4 按原项目 `deliverable/` 的成片保存方式纳入当前分支（87.6 MB，低于 GitHub 单文件限制）。源镜头、配音、字体和中间文件仍不加入 Git。

`/home/user/downloads/` 中保留指向该成片的链接，Arena 文件查看器仍可下载；GitHub 固定下载地址需要登录拥有私有仓库权限的账号。
