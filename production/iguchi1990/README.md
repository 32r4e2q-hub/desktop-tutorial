# 井口真理子命案｜三分钟制作包

**目标交付：** 1920×1080、16:9、24fps、180秒、30镜；Agnes Video 2.5 Flash 720P参考模式逐镜生成连续动态片段，后期放大并合成。画面为写实3D情景复原，不冒充历史影像。

## 当前阶段

- 参考图已全部完成并逐张审核：29/29通过（C01–C07、S01–S16、P01–P05）。S02机场图已替换并批准；S02b夜市保持独立场景图。
- 30镜/180秒脚本已校验；旁白按CJK汉字计数664字，约3.69字/秒，并与逐镜时长锁定。
- Agnes Video 2.5 Flash生成器、61秒全局创建间隔、续跑回执、静帧筛查和参考图门禁已配置。视频任务仅由固定分支上的`GEN_REQUEST`明确触发；Actions在发出请求前会先验证全部参考图并检查`AGNES_API_KEY`，缺少密钥时不会调用Agnes。
- 旁白配音、字幕成片、逐镜音效及最终合成依要求排在视频片段生成之后；目前只有脚本和文案清单，没有TTS音频或合成成片。

生成器在 `reference/manifest.json` 中要求每一张图片同时满足：文件存在、SHA-256相符、`review_status=approved`。只要一项不符，`generate.py` 就在触碰API密钥或提交任务前失败。不要手工把缺失或错误图片标成已批准。

## 常用离线检查

```bash
python3 production/iguchi1990/build_story.py
python3 production/iguchi1990/generate.py --validate
python3 -m unittest production.tests.test_iguchi1990 -v
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

   推送到固定分支 `arena/36f9cd13-desktop-tutorial` 后，`.github/workflows/iguchi1990-gen.yml` 才会运行。任务创建串行并至少间隔61秒；最多2个轮询工作线程；尊重服务端`Retry-After`、队列已满和用户额度，不轮换密钥、不绕过限制。

5. 工作流只把任务ID、请求哈希、下载校验、状态和小型联系表提交到Git；原始MP4保存在忽略的`work/iguchi1990/`，并作为短期Actions artifact上传。续跑会恢复已有任务，不重复提交成功任务。
6. 30段视频完成后先逐镜人工检查实际运动、人物一致性、年代物件和非血腥画面，再开始旁白/字幕/音效及合成。联系表旁的`motion_review=suspected_static`必须优先退回重做；自动帧差只是筛查，不能代替人工播放检查。

仓库Actions需预先配置`AGNES_API_KEY`秘密。密钥只通过GitHub Actions secret传给进程，日志不得输出密钥。GitHub仓库分支和原始参考图URL必须可公开访问，否则Agnes服务端无法下载参考图。

## 制作规约

- 用户要求的顺序：参考图定稿 → 30条实际动态视频 → 旁白/逐句字幕/环境音与拟音 → 合成与质检。
- 镜头提示词顺序：STYLE前缀 → `<Picture N>`指定参考图 → 原文角色锚点 → 单镜动作与运镜 → NEGATIVE后缀。
- 全片严格无BGM、无音乐、无旋律性氛围铺底。字幕白字黑边，底部安全区；关键词金色强调。
- 旁白目标约3.7字/秒；成熟、低沉、克制；单句锁定单镜，片尾静音。
- 不展示遗体、人体残骸、凶器、伤害过程、性侵、分尸或血腥；不美化嫌犯，不复刻真实人物肖像。
- 详细事实边界、来源与发布日期检查见 `史实核查.md`；镜头计划与提示词见 `screenplay.md` 和 `镜头提示词与生成记录.md`。
