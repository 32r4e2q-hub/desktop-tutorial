# 井口真理子命案｜三分钟制作包

**目标交付：** 1920×1080、横版 16:9、24fps、180秒、30镜；Agnes Video 2.5 Flash 720P参考模式逐镜生成连续动态片段，后期放大并合成。用户已确认沿用现有横版规格，而非切换为 9:16；画面为写实3D情景复原，不冒充历史影像。

## 当前阶段

- 2026-11-07旁白修订稿 v2 已启用：`narration_rewrite_v2.md`，658个CJK汉字、180秒约3.656字/秒，逐句沿用现有30镜时长。用户试听选定 `voice-03`；30条MP3均已生成并通过初步PyAV/RMS时长门限。`SHOTS`、`story.json`、`screenplay.md`、`audio/manifest.json` 与活动音轨已更新；进度、SHA和逐镜秒数见 `audio/rewrite_v2/progress.json`。现有字幕与MP4仍是voice-02旧版，须经渲染工作流重建；完整播放与最终QA尚未完成。
- 现有交付目录中的MP4/ASS/SRT仍绑定旧版旁白，不能称为新稿成片。
- 参考图已全部审核通过（29/29：C01–C07、S01–S16、P01–P05）；S02机场图已替换并批准，S02b夜市是独立场景图。
- Agnes run `42363010740` 已完成 30/30 段 720P 动态素材，全部解码通过。源片约 1280×720；渲染必须按时间轴裁到每镜目标帧数，禁止静帧补时。源素材在本地直接下载遭遇 GitHub artifact `EOF`，最终渲染工作流应在 Actions runner 内用 `actions/download-artifact@v4` 读取旧 run。
- S01–S30 联系表已逐张人工查看，但这只是抽帧复核，不等同完整播放。S23/S27 替换联系表达到预期；S09 最终替换保持单一站外镜头；首个合成候选曾碰到人物，最新强柔焦候选的脸部抽帧清晰，左侧招牌遮挡改善，但1.3–1.4秒仍见少量红色字形残片。此候选未获最终画面放行，须完整播放复核；若要求无可读伪字，应继续修整或重生成。S08 黑边裁切及后段卡片柔焦也已修正。其他镜头仍有生成式招牌/纸张文字等待全片核验；记录见 `visual_review.md`。
- 新版音轨初步时长门限已全部通过；最终 `render.py` 仍须逐条解码、应用不超过1.15×的加速并输出正式 `narration_timing.json`。现有 MP4 仍是旧版旁白，需等渲染完成后再完整播放复核。
- `render.py` 已实现 30 镜 SHA/提示词核验、无冻结/补帧门禁、逐镜裁切、遮挡柔焦、字幕、48 kHz 逐镜环境声/非周期拟音与尾段静音。离线单元测试和合成素材裁切/补边冒烟测试通过；尚未对真实30镜运行。
- `.github/workflows/iguchi1990-render.yml` 会在 Actions runner 从原始 Agnes run 与一个或两个分轮修复 run 下载素材，技术门禁通过后生成 1080p24 候选片、字幕和质检报告。可用固定分支上的 `production/iguchi1990/RENDER_REQUEST` 提交各 run ID 与 artifact 名称触发；全片逐镜人工复看/声音监听完成前，不称为定稿。
- 生成器已配置每分钟不超过 5 次创建（至少 12.1 秒间隔）、遵守更严格服务端冷却、保存续跑回执、静帧筛查和参考图门禁。只有固定分支上的 `GEN_REQUEST` 或手动工作流能触发 Agnes；不轮换密钥、不绕过限额。

生成器在 `reference/manifest.json` 中要求每一张图片同时满足：文件存在、SHA-256相符、`review_status=approved`。只要一项不符，`generate.py` 就在触碰API密钥或提交任务前失败。不要手工把缺失或错误图片标成已批准。

## 常用离线检查

```bash
python3 production/iguchi1990/build_story.py
python3 production/iguchi1990/generate.py --validate
python3 -m unittest production.tests.test_iguchi1990 production.tests.test_iguchi_render -v
```

`--validate`只检查计划并报告门禁状态，不会调用Agnes。当前清单为29/29；工作流仍会在提交任务前重新核对全部图片文件、SHA-256和逐张审核状态。任何参考图被替换后，必须重建清单并再次审核。

## 参考图完成后，才开始排队

1. 按顺序完成全部场景参考图，再完成全部道具参考图；机场与夜市始终是两张独立图片。
2. 每张新图必须单独呈现、单独检查；只在 `build_story.py` 的 `REFERENCE_REVIEW` 中把确实合格的图设为 `approved`，重跑构建并核对 `reference/manifest.json` 的29/29。
3. 确认当前分支已推到GitHub，使 `raw.githubusercontent.com` 参考图URL公开且可访问。
4. 只在全部29张图批准后，写入 `GEN_REQUEST`：

   ```json
   {"mode":"clips","workers":2}
   ```

   推送到固定分支 `arena/36f9cd13-desktop-tutorial` 后，`.github/workflows/iguchi1990-gen.yml` 才会运行。创建串行，计划上限为每分钟5次并至少间隔12.1秒；若回执或Agnes返回更严格的速率窗口/`Retry-After`，生成器会延长间隔并跨工作流续存冷却。最多2个轮询工作线程；尊重队列容量和账户额度，不轮换密钥、不绕过限制。

5. 工作流只把任务ID、请求哈希、下载校验、状态和小型联系表提交到Git；原始MP4保存在忽略的`work/iguchi1990/`，并作为短期Actions artifact上传。续跑会恢复已有任务，不重复提交成功任务。
6. 30段素材完成后逐镜人工检查实际运动、人物一致性、年代物件和非血腥画面；只重生成并复核 S09、S23、S27。现行固定分支的 `iguchi1990-render.yml` 需提供原始 Agnes run 与修复 run 的 ID，才会在 runner 下载并 SHA 校验素材、渲染逐镜旁白/字幕/环境音和技术质检候选片。联系表旁的`motion_review=suspected_static`必须优先退回重做；自动帧差只是筛查，不能代替人工播放检查。输出后还须完整播放复核逻辑、安全、连续性、字幕和声音，方可称为定稿。

仓库Actions需预先配置`AGNES_API_KEY`秘密。密钥只通过GitHub Actions secret传给进程，日志不得输出密钥。GitHub仓库分支和原始参考图URL必须可公开访问，否则Agnes服务端无法下载参考图。

## 制作规约

- 用户要求的顺序：参考图定稿 → 30条实际动态视频 → 旁白/逐句字幕/环境音与拟音 → 合成与质检。
- 镜头提示词顺序：STYLE前缀 → `<Picture N>`指定参考图 → 原文角色锚点 → 单镜动作与运镜 → NEGATIVE后缀。
- 全片严格无BGM、无音乐、无旋律性氛围铺底。字幕白字黑边，底部安全区；关键词金色强调。
- 旁白目标约3.7字/秒；成熟、低沉、克制；单句锁定单镜，片尾静音。
- 不展示遗体、人体残骸、凶器、伤害过程、性侵、分尸或血腥；不美化嫌犯，不复刻真实人物肖像。
- 详细事实边界、来源与发布日期检查见 `史实核查.md`；镜头计划与提示词见 `screenplay.md` 和 `镜头提示词与生成记录.md`。
