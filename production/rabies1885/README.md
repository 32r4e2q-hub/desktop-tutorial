# 狂犬病疫苗：一百四十年前那场赌局

三分钟横屏科普片的**当前可复现制作源**。本目录于 2026-10-05 从项目的历史制作分支接管到
`arena/01a10a48-desktop-tutorial`，后续生成、出片、逐字听检和交付均只在此分支闭环。

- 成片规格：1920×1080 / 30 fps / 180 秒；45 镜（38 个 Agnes 动画镜头 + 7 张信息卡），每镜只使用一次。
- 当前旁白：6 段共 863 字（含标点）；`story.json`、`audio/manifest.json` 与 `screenplay.md` 必须逐字同步。
- 当前素材：`results.json` 记录 38 条已完成 Agnes 回执和 SHA-256；无档案素材。最新一轮全量素材完成于 2026-10-05。
- 当前配音：`audio/N01.mp3`—`N06.mp3` 是收紧停顿后的渲染用音轨；原始输出在 `audio/raw/`。
- 当前闸门：`python3 production/rabies1885/generate.py --validate` 已通过（时间线、45 镜、素材回执和配音哈希）。

> **交付状态：等待本分支的新渲染闭环。** 本目录没有把历史候选 MP4、接触表或旧听检报告当作本次交付证据：
> 它们早于当前这批素材和 863 字旁白，不能证明本版本成片正确。只有本分支触发的出片任务写回的
> `交付/`、`delivery/`、技术报告、逐字听检报告和人工画面签收，才能解除此状态。

## 本次闭环

工作流已固定到当前分支；模板副本在 `workflows/`，GitHub 生效副本在 `.github/workflows/`。
仅在完成每一步且证据齐全时进入下一步：

1. **内容与音频闸门**

   ```bash
   python3 production/rabies1885/build_story.py  # 仅当改了唯一内容源时；会重写 story/manifest 的文本
   python3 production/rabies1885/generate.py --validate
   python3 production/rabies1885/clause_times.py --check-cuts
   ```

   修改旁白后必须重新生成对应配音、收紧停顿、重算分句时间和 SHA-256；不能用旧音频或旧字幕凑合。

2. **素材复核**

   `results.json` 的请求哈希和 `story.json` 必须匹配。逐镜查看 `qa/Sxx.jpg` / 全帧接触表（由本轮工作流产出）：
   场景须符合分镜；不得有人脸、可读伪文字、畸形肢体、中途换场、黑帧或不当暴力。仅坏镜用
   `GEN_REQUEST` 的 `{"workers":2,"only":"S03,S08"}` 重做，不能混入未验收的来源。

3. **渲染与交付报告**

   在当前分支创建或改写 `RENDER_REQUEST` 后 push。`rabies1885-render.yml` 会恢复素材，按实测配音渲染，
   并将新 MP4、字幕、EDL、音频/技术报告写回 `交付/` 与 `delivery/`。报告必须对应新 MP4 的 SHA-256。

4. **逐字听检与人工签收**

   新成片写回后，创建或改写 `VERBATIM_REQUEST` 后 push。`delivery/verbatim-check.json` 中六段 CER 都必须
   ≤ 0.15；再按 EDL 逐段检查画面与字幕、按切点前后 0.25 秒检查字幕切换。任何失败均回到对应步骤修复并重渲。

## 文件职责

| 路径 | 作用 |
|---|---|
| `build_story.py` | 唯一内容源：旁白、45 镜、信息卡、字幕关键词、发布文案和事实来源 |
| `story.json` | 机器可读时间线和镜头计划；由内容源维护 |
| `audio/manifest.json`、`audio/N0*.mp3`、`audio/clause-times.json` | 渲染用配音、哈希及分句时间 |
| `results.json` | Agnes 请求、素材 URL、请求哈希与 SHA-256 回执 |
| `generate.py` | 完整性闸门、增量 Agnes 生成和来源回执 |
| `render.py` / `../run_project.sh` | 剪辑、字幕、混音、成片技术复测与写回 |
| `workflows/` / `.github/workflows/` | marker 工作流模板 / GitHub 生效副本 |
| `delivery/`、`qa/`、`交付/` | **仅**存放本分支最新出片后生成的审核证据与成片，不预置历史候选物 |

## 内容与安全底线

- 全部生成画面标注为「AI动画情景重现 · 非新闻影像」；不冒充历史新闻或档案。
- 巴斯德、约瑟夫、母亲和医生只以背影、剪影或手部出现；不生成可识别的真实人物面孔。
- 不展示遗体、伤口、血腥或侵害过程；中文文字和日期全部后期添加。
- 十三针/十四剂在权威史料的计数不同，旁白只保留「十天、十几针」，不混用精确数字。
- 本片是历史与公共卫生科普，不替代医疗建议；疑似狂犬病暴露应立即清洗伤口并向当地专业医疗机构咨询处置。

`制作过程.md` 是接管前的历史工作日志，可能引用旧分支、旧字数或旧候选片；它不作为本版本的交付状态依据。
