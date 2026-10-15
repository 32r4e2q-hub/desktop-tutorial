# 李亨浩案《四十四天的电话》制作包

本目录制作 **3 分钟、16:9（1920×1080）3D CGI 动画解说**。郑斗英项目只提供可复用流程；本片的李亨浩案事实独立核对，不混入郑案事实。

## 制作规则

- **视频**：所有动态镜头只由智谱 **CogVideoX-Flash** 生成。有人物的镜头通过 CogVideoX 的 `image_url` 图生视频输入固定角色参考图；不以其他模型或静态图替代视频镜头。
- **角色连续性**：父亲、母亲、儿童、两名警探各有独立的虚构角色参考图和固定身份 ID；重复角色使用同一参考文件及 SHA-256，双警探镜头复用同一组参考图。每个生成回执记录角色 ID、参考图哈希和视频哈希；合成前生成跨镜接触表供逐人脸审查。未知来电者和取款者面容保持遮挡，不把两者推断为同一人。
- **参考图**：仅为虚构动画演员设定图，不复原真实当事人；儿童形象也不模拟李亨浩真人面容。
- **旁白**：Microsoft Edge TTS `zh-CN-YunyangNeural`，由制作代理选定；不调用智谱 GLM-TTS 或 Agnes。章节音频可按实际时长校准、收紧过长静音并计算字幕/镜头切点。
- **事实与披露**：按 `史实核对.md` 修正用户稿中的错误数字及未经证实情节；全片标注“AI动画情景重现 · 非新闻影像”，不展示遗体、血腥或可复制犯罪方法。
- **后期**：本地确定性程序合成配乐、音效、字幕和资料卡；源视频必须具有 CogVideoX 成功回执及 SHA-256，否则拒绝渲染。

> CogVideoX 是概率生成模型，参考图能强力锚定脸部与服装，但单靠 API 不能数学上保证每一帧绝不漂移。工作流会固定参考图、保存哈希并生成跨镜人脸接触表；最终交付前仍须检查接触表，出现身份漂移的镜头要重生成，不能把“参考图哈希一致”误称为视觉检查通过。

## 目录要点

- `build_story.py` / `story.json`：六章剧本、45 镜时间线、人物身份设定、参考图分配及史料来源。
- `references/`：虚构角色单人/双人身份锚点；用于 CogVideoX 图生视频，不是视频镜头。
- `generate.py`：CogVideoX-Flash 调用、图生视频参考、断点续跑、成功回执和 SHA-256 校验。
- `character_consistency_audit.py`：校验每镜参考图哈希并生成按角色分组的跨镜联系表。
- `prepare_tts.py`：调用 Edge TTS 生成六章旁白、收紧停顿、产出 SHA-256 音频清单和字幕/切点时序。
- `fetch_sources.py`：从智谱回执中的 CDN 地址恢复源片并校验哈希。
- `render.py`、`build_audio.py`：确定性组装 180 秒影片、字幕、片头片尾卡、配乐和混音报告。
- `audit_frame_distortions.py`：逐帧技术/时序审计；自动审计不取代跨镜人脸目检。

## 运行

仓库 Actions 需要已有的 `ZHIPUAI_API_KEY` Secret（仅用于 CogVideoX）。工作流固定在 `arena/04ec3850-desktop-tutorial` 分支。

```bash
python production/lee_hyung_ho1991/build_story.py
python production/lee_hyung_ho1991/generate.py --validate
python production/lee_hyung_ho1991/generate.py --publish --payload '{}'
python production/lee_hyung_ho1991/fetch_sources.py --dest work/lee_hyung_ho1991/sources
python production/lee_hyung_ho1991/character_consistency_audit.py \
  --sources work/lee_hyung_ho1991/sources \
  --out work/lee_hyung_ho1991/character-consistency
python production/lee_hyung_ho1991/prepare_tts.py --publish
python production/lee_hyung_ho1991/generate.py --validate --require-audio
python production/lee_hyung_ho1991/render.py \
  --sources work/lee_hyung_ho1991/sources \
  --work work/lee_hyung_ho1991/render \
  --output work/lee_hyung_ho1991/李亨浩_四十四天的电话_三分钟.mp4 \
  --skip-asr
```

GitHub Actions 可先用 `cogvideo_smoke` 做 3 镜身份参考试生成（父亲两镜、双警探一镜）；通过后再在固定分支运行完整制作。大视频留在 Actions artifact / `work/`，不提交进 Git；`results.json` 保存每镜 CogVideoX 任务 ID、角色 ID、参考图哈希、请求哈希、视频哈希和媒体检查结果。智谱任务若以 `1234` 网络错误等可重试状态终止，会保留失败任务记录并最多另建一次任务重试；额度错误不会重试。

## 质量门槛

参考图哈希证明输入来源一致，不等于模型生成的人脸已视觉通过。每个生成镜头仍需检查 QA 帧或跨镜接触表；未完成人工视觉核对时，不标成身份连续性已通过。
