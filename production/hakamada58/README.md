# 《他等了58年，才等来一个无罪：袴田事件》

三分钟横屏短片：1920×1080、24fps、180秒、30镜；虚构演员式写实重现，尊重袴田岩与秀子，不使用真实肖像，不展示遗体或暴力过程。

## 进度

- 参考图：34/34 已检查并发布；不可变素材 revision `040d12431c35e7bdde340fee6aff3a0f1dabc5f5`，SHA 清单 `reference/approvals.json`。
- 视频：0/30。现配置 **S01 canary**，只提交一条 Agnes 任务；回收视频解码信息和九帧接触表供检查，通过后再发起剩余镜头。
- 旁白：voice-00 已选；先前 S01–S10 音频中除 S02、S04 外因台词变更需重录，S11–S30 待生成。成片合成尚未启动。

## Agnes 2.5 Flash 参考图实现

按用户提供的 Son of Sam 项目 `arena/e455e5b7-desktop-tutorial` 核对：`agnes-video-2.5-flash` 使用 `mode="reference"`、`images=[1–5 张公网不可变 raw URL]`；其 `results.json` 有 30/30 completed，`run.log` 有完整生成与首剪记录。Hakamada 的 payload 同样使用该结构，按镜头顺序映射场景/人物/道具图；STYLE、角色锚点、逐图用途说明与 NEGATIVE 一起放在 prompt 中。为避免假设计费等级，创建任务默认间隔 61 秒，不采用 Son of Sam 的月卡配速。

提示词 schema 不会发送 `width/height/fps/num_frames/resolution/negative_prompt` 等被拒字段。模型服务器从不可变 commit 获取 PNG；本机路径不会传给 Agnes。

## Canary 与工作流

- `GEN_REQUEST` 当前只允许 `{"mode":"canary","only":"S01","workers":1}`。
- `.github/workflows/hakamada58-gen.yml` 验证计划和 34 张图后，调用一次 S01，并将小型结果回执及 `qa/S01.jpg` 提交回当前固定分支；视频文件留在 runner 的 ignored `work/`，不进入 Git。
- canary 完成后检查 motion contact sheet、解码报告和角色一致性，再决定是否提交剩余 29 镜。

## 文件与命令

```bash
python production/hakamada58/build_story.py
python production/hakamada58/generate_clips.py --validate
python production/tests/test_hakamada58.py
```

- `build_story.py`：30镜、时间线、参考图清单、STYLE/角色锚点/NEGATIVE。
- `generate_clips.py`：2.5 Flash `reference` payload、不可变URL和SHA校验、限频、回执与接触表。
- `reference/`：34张已审 PNG、SHA审批账本与固定 revision。
