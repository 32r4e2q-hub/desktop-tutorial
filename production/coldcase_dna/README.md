# 一根头发引发的破案革命：冷案复活与DNA表型分析

三分钟横屏纪实法医科学解说短片。严格依据加利福尼亚金州杀手案（Golden State Killer）真实司法调查历史与现代法医基因组学（Forensic Genomics）、家族基因检索（Forensic Genetic Genealogy）科普资料制作。

- 项目 slug：`coldcase_dna`
- 规格：1920×1080 / 30fps / 180s 横屏 / h264+aac 封装
- 视觉画风：与 DB 库珀劫机案一致的严肃纪实重现风格，胶片质感、暗部通透、克制冷调与暖光实用照明
- 配音：云希男声（`voice-00`，普通话解说）
- 闸门校验：
  - 闸门一（计划与配音哈希）：`python3 production/coldcase_dna/generate.py --validate` 100% 通过；
  - 闸门二（静音与混音电平）：`-20 dBFS RMS / -1.5 dBTP`；
  - 闸门三（成品复测）：对最终成片 5400 帧及完整音轨进行闭环复验；
  - 闸门四（画质与畸变 QC）：`production/qc_film.py` 自动化检测 + 逐镜负向提示词约束无畸变。

## 工作流与生成状态

- 生成流水线：`.github/workflows/coldcase_dna-gen.yml`（由 `production/coldcase_dna/GEN_REQUEST` 驱动）
- 出片流水线：`.github/workflows/coldcase_dna-render.yml`（由 `production/coldcase_dna/RENDER_REQUEST` 驱动）
- 听检流水线：`.github/workflows/coldcase_dna-verbatim.yml`（由 `production/coldcase_dna/VERBATIM_REQUEST` 驱动）
- 资产发布流水线：`.github/workflows/release-upload.yml`（由 `production/coldcase_dna/RELEASE_UPLOAD_REQUEST` 驱动）

## 2026-09-16 复检与 18 镜重生成（进行中）

v1 成片被用户指出 2:42 处「人头跟身子是反的」+ 畸变 + 运镜飞来飞去。
逐镜 6 帧复检的结论与对策见 `review/审片复检-2026-09-16.md`：

- **重生成 18 镜**：S01 S02 S04 S05 S06 S07 S09 S11 S12 S14 S17 S19 S21 S22 S24 S26 S28 S30
  （提示词重写：场景前置、锁定机位、显式禁止换场景/环绕/快速推进；S28 改为背影固定机位）；
- **保留 6 镜**：S10 S15 S16 S20 S25 S29（复检合格，提示词未动，`request_hash` 不变，
  素材按 SHA-256 复用）；
- 重生成素材逐镜复检合格后才重新出片。
