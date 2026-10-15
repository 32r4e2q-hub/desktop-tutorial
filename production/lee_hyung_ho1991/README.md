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

仓库 Actions 需要已有的 `ZHIPUAI_API_KEY` Secret（仅用于 CogVideoX）。工作流固定在 `arena/1f36798e-desktop-tutorial` 分支。

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

GitHub Actions 可先用 `cogvideo_smoke` 做 3 镜身份参考试生成（父亲两镜、双警探一镜）；通过后再在固定分支运行完整制作。大视频留在 Actions artifact / `work/`，不提交进 Git；`results.json` 保存每镜 CogVideoX 任务 ID、角色 ID、参考图哈希、请求哈希、视频哈希和媒体检查结果。智谱任务若以 `1234` 网络错误等可重试状态终止，会保留失败任务记录；每轮单镜最多尝试一个任务，失败后继续处理其他镜头；最多预提交 3 个云端任务，避免全片串行等待。重启复用同请求哈希的 queued/processing 任务 ID，额度错误不会重试。

## 质量门槛

参考图哈希证明输入来源一致，不等于模型生成的人脸已视觉通过。每个生成镜头仍需检查 QA 帧或跨镜接触表；未完成人工视觉核对时，不标成身份连续性已通过。


## 2026-10-15 调度提速修复

- 成功片段大多几分钟完成，多次失败约 30 分钟后收到服务端 `1234 网络错误`。
  该回执不证明内容审核拒绝，也无法由本地脚本保证消除。
- 旧循环虽然预填窗口，却每次只等待一个任务；现在每轮轮询所有在途任务，先完成先收，空位及时补充。
- HTTP 请求超时 60 秒、关闭 SDK 内部隐式重试，避免隐藏的长等待；提交限流退避不阻塞其他任务查询。
- 不因 PROCESSING 时间长就删除任务或重复提交。重启保留任务 ID；每轮可重试失败最多一次，放到未做镜头之后。
- 下载前保存成功 URL，下载/检查失败至多重试三次，下一轮复用 URL，不重新生成视频。
- `recovered-receipts.json` 从已取消分支救回 S04/S07 成功回执；合并时核对请求及参考图哈希，下载时核对视频 SHA-256。
- 工作流并发组匹配实际运行的首个制作任务，新运行通过 GitHub 原生并发控制接管。
- 不改模型、分辨率、人物参考图、字幕或质量门槛。提速幅度需观察云端实际回执，不能承诺固定倍数。


## 2026-10-16 残余四镜恢复

本轮只补做 S11/S18/S27/S44（其余回执匹配的 34 镜跳过）。云端 `1234` 是提供方异步任务错误，
不是 Python 渲染异常或明确的内容审核结论。参考图也在其他镜头成功过。
将本轮窗口设为 2、单镜最多 3 次尝试、失败冷却 90 秒、生成预算 210 分钟，给 350 分钟工作流留出后期时间。
不无限重试，不把 PROCESSING 当失败，不改动角色参考图或成功镜头请求。

新增生成前素材恢复闸门：缺失回执允许留待生成，已有成功回执的下载或哈希错误则必须停止，
不能再花数小时补镜后才发现旧素材不可用。签名链接失效时可查询原成功任务恢复 URL，仍必须匹配原 SHA-256，
不会重新生成已有视频。所有源片在失败时也写入 Actions cache 和 artifact，而非只保留 3 个测试镜头。
这只能防止今后的素材丢失；若既有链接与原任务均不可恢复，会如实报错，不以假素材顶替。
