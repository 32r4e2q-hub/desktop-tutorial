# 李亨浩案《四十四天的电话》制作包

本目录制作一部 **3 分钟、16:9（1920×1080）3D CGI 动画解说**。郑斗英项目只提供了可复用的制作流程；本片所有李亨浩案事实均独立核对，不把郑斗英案内容带入。

## 已定制作选择

- **生成服务**：只调用智谱 GLM-TTS 与 CogVideoX-Flash；不调用 Agnes 或其他生成式影像、语音 API。
- **旁白**：六章中文旁白，智谱 GLM-TTS `chuichui` 系统音色，语气克制、纪实；由制作代理选定，不需用户试听确认。
- **画面**：45 个剪辑单元，38 段智谱 CogVideoX-Flash 动画 + 7 张后期信息卡；匿名化情景演员、不复刻真实面容、不显示遗体或暴力过程。
- **事实**：按 `史实核对.md` 修正用户稿中的错误数字和未经证实情节；切点与字幕按实际旁白音频测算。
- **披露**：全片常驻“AI动画情景重现 · 非新闻影像”；每张资料卡标注为公开报道摘要，不是档案影像。
- **音频**：本地确定性程序合成配乐和轻量音效；生成式语音只用 GLM-TTS。混音后检查电平、峰值、静音比例和章节电平。

## 目录要点

- `build_story.py`：剧本、分镜、片卡与史料清单的单一来源；可重建 `story.json`。
- `story.json`：智谱视频生成与渲染共用的 45 镜制作计划。
- `prepare_tts.py`：调用 GLM-TTS，写入原始 WAV 与收紧后的 MP3、SHA-256 清单，并自动计算旁白切点。
- `generate.py`：智谱 CogVideoX-Flash 生成与分镜回执检查；每个镜头的任务 ID、请求哈希和成片 SHA-256 逐步记录到当前 Arena 分支。
- `fetch_sources.py`：从回执中的智谱 CDN 地址恢复源片，并校验 SHA-256。
- `render.py`、`build_audio.py`：确定性组装 3 分钟成片、字幕、片头片尾卡、配乐与混音报告。
- `audit_frame_distortions.py`：可选的逐帧黑帧、冻结、时序、人脸/手部候选质量审计；自动审计不能替代看片。
- `delivery/`：小型 EDL、技术报告与自动质检摘要；大视频和中间片段留在 GitHub Actions artifact / `work/`，不写入 Git。

## 云端运行

仓库 Actions 需要已有的 `ZHIPUAI_API_KEY` Secret。流程只在固定分支 `arena/04ec3850-desktop-tutorial` 发布。

```bash
python production/lee_hyung_ho1991/build_story.py
python production/lee_hyung_ho1991/prepare_tts.py --publish
python production/lee_hyung_ho1991/generate.py --validate
python production/lee_hyung_ho1991/generate.py --publish --payload '{}'
python production/lee_hyung_ho1991/fetch_sources.py \
  --dest work/lee_hyung_ho1991/sources
python production/lee_hyung_ho1991/render.py \
  --sources work/lee_hyung_ho1991/sources \
  --work work/lee_hyung_ho1991/render \
  --output work/lee_hyung_ho1991/李亨浩_四十四天的电话_三分钟.mp4 \
  --skip-asr
```

仓库内 `.github/workflows/lee-hyung-ho1991.yml` 提供完整 Action：TTS 缓存校验、视频断点续跑、渲染、音频/画面报告、逐帧自动 QC 与最终视频 artifact。视频源片保存在 `work/`，不会提交进 Git；`results.json` 中保存每条源片的可复核回执。

## 状态

剧本、事实核对和工作流适配已经准备；调用 API、生成音视频、成片和人工视觉复核由 Action 实际执行后再记录，未跑出的产物不会标成完成。
