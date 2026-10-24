# 小丑背后的真相：约翰·韦恩·盖西

## 本轮重建，旧流程不再使用

- 当前分支：`arena/3c0c229a-desktop-tutorial`。
- 新项目：`production/gacy1978`；旧 `production/gacy` 只留审计，不续跑旧实验。
- 权威模板：`production/kitakyushu2002`；步骤遵循根目录 `新题目开工手册.md`。
- **45 镜 = 38 个实际动态视频 + 7 张信息卡**，六章，180 秒，1920×1080，30fps。
- 唯一视频模型 `cogvideox-flash`，使用 Actions 里的既有 `ZHIPUAI_API_KEY`。不启用付费模型或其他供应商。
- `kind=agnes` 是模板内部的历史动态镜头标签，**不是本片实际调用的供应商**。`generate.py` 只开放 `--validate`；实际生成只能用 `generate_cogvideox.py`。

## 内容与当前状态

`build_story.py` 是唯一内容源：六段旁白 **773 字（含标点）**、45 个分镜、7 卡、字幕关键词、发布文案和封面要求。
角色使用四位虚构成年演员；盖西和波戈是同一角色的日常/小丑妆容变体，少年仅背影。

已完成：模板引擎移植、内容重写、四个工作流安装；用户选定voice-00、六段全新TTS、原始及收紧音频SHA、分句对齐和CUTS检查。原始173.16秒，收紧152.21秒，模板tempo约0.906。
**未完成：38段实际素材、逐镜/同脸复核、成片与实际视觉/听检。**
`generate.py --validate` 已验证本轮六段文本与音频SHA；这不是视频生成成功。
`delivery/face-cast-prompts.json` 仅为静态提示词检查，不是画面同脸签收。
没有复制模板音频、素材、收据、分句时码、CUTS、取用窗或 QC 结论。

## 严格按手册推进

1. 事实边界及来源见 `事实核查.md`；旁白和规划分镜见 `screenplay.md`。罗伯特·皮斯特年龄修正为 **15 岁**。
2. 本轮试听选音色 → 六段分别存 `audio/raw/N01.mp3` 至 `N06.mp3`。
3. `tighten_pauses.py` 只剪静音；保留「地板下」后约 0.5 秒的指定停顿，不删除字。未核实的「马上回来」不当成真实引语使用。
4. `clause_times.py` → `tools/plan_cuts.py` → `clause_times.py --check-cuts`。当前 CUTS 只是新规划占位，不能当实际时码；`WINDOWS={}`，待本片实看后设置。
5. 回填新音频 SHA 与音色记录，执行以下三道检查：
   ```bash
   python production/gacy1978/generate.py --validate
   python production/gacy1978/generate_cogvideox.py --validate
   python production/face_cast.py check-prompts --project production/gacy1978
   ```
6. 以上通过后才新增 `COGVIDEOX_GEN_REQUEST` 并推送，内容 `{"ref_image":false}`，一次按模板生成全部38个镜头；不再做旧双图前置实验。
7. 下载真实片段，检查运动、构图、换场、脸与手；运行 `face_cast.py check-frames` 并人工看角色接触表。**面容 token/seed 不保证跨镜同脸**；纯三字段 SDK 请求并未发送 seed。坏镜头按模板单镜改提示词/重做，不冒充已解决。
8. 根据新配音与新素材重对 CUTS；保留来源标识。混音、约低于旁白18dB的BGM、指定停顿、章间0.3秒黑场、最后1秒静音均须以本片实测验收，不能沿用模板数值报告。
9. `RENDER_REQUEST` → 初剪；`VERBATIM_REQUEST` → CER逐字听检；`VISUAL_QC_REQUEST` → 5400帧全帧审计 → 人工语义签收。初剪不是终版。
10. 通过实际 QC 后交付影片、封面、字幕、发布文案；`build_story.py --script` 在真实对齐后生成正式四列时间表。

四个工作流均位于 `workflows/`，并已安装在 `.github/workflows/`，只响应本分支、本项目 marker。
本轮已提交免费全量生成marker，具体运行状态以Actions和新results.json为准；未提交渲染marker。`template-provenance.json` 记录模板文件 SHA 与必要差异。

## 合规与故障处理

1301 记录原始拒绝信息并停该镜头，按仓库手册改成合规、非侵害、单一场景表达；不混淆词语、不绕过审核。
模板支持请求哈希断点续跑；任务成功、文件下载、SHA校验、动态/同脸/全帧检查是不同证据，不能互相替代。
