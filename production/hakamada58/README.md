# 《他等了58年，才等来一个无罪：袴田事件》

三分钟横屏短片：目标 1920×1080、24fps、180秒、30镜；每镜先由 Agnes 2.5 Flash 生成真实连续运动素材（不是静态图推拉），后期再合成旁白、字幕、音效与 BGM。人物使用虚构演员式形象，尊重袴田岩与秀子，不使用真实肖像，不展示遗体或暴力过程。

## 进度

- 参考图：38张逐项检查并登记在 `reference/approvals.json`；不可变素材版本由 `reference/revision.txt` 固定。
- 视频复检：原始 S01–S30 已生成每镜144帧（共4320帧）时间标记审核表，九帧初审不作为最终验收。S03全帧符合空街火灾；S04最新参考版九帧表可见无十字车标的消防车、三名消防员与水流，待144帧复核；S12新重拍九帧表符合纯正俯拍、恰好五件干净衣物且无人物/污渍/伪字，待144帧复核；S20旧版及workflow `42244655816` 的新参考版都仍有硬切（宽景切到手部/纸张特写），需进一步收紧提示后再次重拍。新增发现S22存在不必要切换/溶解，S23在3.25秒硬切，S27有人物前景插入/叠影，S28有黑场与类人体布包及不相关切镜，S29为明显分屏。S23重拍workflow `42245032106` 已完成，task `task_0JdcYMj6BoTfYSYvTAL0guHjInp2qwro` 九帧表初步符合单一印章场景，待144帧审核；S22首个重拍仍切成狱门、押解与单人特写；第二次重拍workflow `42290123978` 已完成，九帧表初步显示兄妹保持同框静止，待144帧复核。P27（同框法庭）、P28（无人体干净物证）、P29（庭院兄妹同框）参考均已审阅更新；S27–S29固定连续镜头重拍workflow `42290702425` 已启动生成。全部镜头逐帧验收通过后才重渲染并替换Release母版。
- Agnes 账号为用户确认的 $4 月卡，创建任务按 12 秒最小间隔、最多 5 个并发 worker；遵从服务器 Retry-After，不轮换密钥。最终连续生成仍会受 Actions 运行预算限制；若超时或遇到服务端冷却，任务 ID 与回执保存，重跑时恢复已有任务而不是重新创建。
- 旁白：voice-00 的 S01–S30 均已生成，MP3 与逐条 SHA/台词清单见 `audio/manifest.json`（30/30）。
- 最终成片：GitHub Actions run [42227002875](https://github.com/32r4e2q-hub/desktop-tutorial/actions/runs/42227002875) 已成功；母版经校验为 1920×1080、24fps、180秒。30条旁白逐句对齐，关键词金色强调，并混合克制的程序化氛围配乐与低音量程序化环境音效。
- 第六期直接下载：发布页 [hakamada58-episode06-v1](https://github.com/32r4e2q-hub/desktop-tutorial/releases/tag/hakamada58-episode06-v1)；MP4 资产 [1080p／180秒](https://github.com/32r4e2q-hub/desktop-tutorial/releases/download/hakamada58-episode06-v1/hakamada58-episode06-1080p-180s.mp4)，封面资产 [1080×1440 PNG](https://github.com/32r4e2q-hub/desktop-tutorial/releases/download/hakamada58-episode06-v1/hakamada58-episode06-cover-1080x1440.png)。另附 SRT/ASS 字幕；大视频不进 Git。
- 系列第六期封面按第五期 `迷案解码人` 模板制作，1080×1440；采用已审通过的 S29 画面，成品 `第六期_袴田事件_封面.png` 与文字/来源记录 `.json` 一并保存在本目录。

## Agnes 2.5 Flash 参考图实现

按用户指定的 Son of Sam 项目 `arena/e455e5b7-desktop-tutorial` 核对：`agnes-video-2.5-flash` 使用 `mode="reference"`、`images=[1–5 张公网不可变 raw URL]`；其 `results.json` 有 30/30 completed，`run.log` 有完整生成与首剪记录。Hakamada 的 payload 同样使用该结构，按镜头顺序映射场景/人物/道具图；STYLE、角色锚点、逐图用途说明与 NEGATIVE 一起放在 prompt 中。

提示词 schema 不会发送 `width/height/fps/num_frames/resolution/negative_prompt` 等被拒字段。模型服务器从不可变 commit 获取 PNG；本机路径不会传给 Agnes。各段输出经解码检查，并另由 `audit_motion.py` 下载 SHA 校验的源片，为每镜24fps的144帧生成4张带帧号/时间戳的逐帧审核页；`qa/frame_audit/audit_summary.json` 记录帧数与基础异常指标。自动提帧不能替代人工审查，所有镜头仍须人工核对畸变、逻辑、角色与连续性。

## 一次连续全片工作流

- `GEN_REQUEST` 请求 `{"mode":"full","workers":5}`；full 模式选择 S01–S30 全部镜头，不再拆成每五镜停一次。
- `.github/workflows/hakamada58-gen.yml` 在固定分支上验证脚本与全部参考图后启动全片任务；默认 $4 月卡节奏为 12 秒创建间隔、最多 5 个 worker，遵从 `Retry-After`。已有相同 request hash 的 S01–S06 直接复用保存的视频 URL/任务 ID；若文件缺失仅从已有 URL 恢复，不新建任务。
- 生成器逐项保存回执到 runner；workflow 同时上传 30 天可下载的 receipts/QA artifact，并在发布前 fetch/rebase 重试，避免并发分支推进丢失结果。视频文件仅在 runner 的 ignored `work/` 中，不进入 Git。
- `recover_tasks.py` 仅查询任务列表、不创建任务；当前 Agnes 网关对 `GET /v1/videos` 返回 404。失败发布若仍有 GitHub Actions receipts artifact，可用 `RECOVERY_REQUEST.artifact_run_id` 在 runner 内恢复结果/QA，无须重做任务。
- 运行完成后集中审阅 S01–S30，再进入旁白、字幕、音效、BGM及最终 1920×1080、180秒合成。

## 文件与命令

```bash
python production/hakamada58/build_story.py
python production/hakamada58/generate_clips.py --validate
python production/tests/test_hakamada58.py
```

- `build_story.py`：30镜、时间线、参考图清单、STYLE/角色锚点/NEGATIVE。
- `generate_clips.py`：2.5 Flash `reference` payload、不可变URL和SHA校验、12秒并发安全限频、任务复用与接触表。
- `throttle.py`：月卡创建节奏、429 Retry-After 冷却和运行预算保护。
- `reference/`：38张已审 PNG、SHA审批账本与固定 revision。
