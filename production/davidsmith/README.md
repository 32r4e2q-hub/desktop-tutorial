# 大卫·史密斯：无罪之后

三分钟横版（16:9）悬疑科普动画，按仓库 `production/gilgo/` 的制作方法开工：六段旁白、45 个唯一镜头、Agnes Video V2.0 片段、后期信息卡、硬字幕、混音和逐字听检。

- slug：`davidsmith`
- 分支：`arena/01a0d0c4-desktop-tutorial`
- 规格：1920×1080 / 30 fps / 180 秒 / 30 fps / AAC 立体声
- 画面：38 个 Agnes 动画镜头 + 7 张后期信息卡；每镜只用一次
- 风格：手绘 2D 动画纪录片、冷蓝/纸张米色/钠灯橙、轻微桶形镜头畸变与色差；不做人体畸变
- 字幕：分句对轨，54 号白字黑边，关键词描黄；全片常驻「AI动画情景重现 · 非新闻影像」
- 配音：用户试听选择 `voice-00`；799 字旁白，收紧停顿后约 161.8 秒，按成片可用时长约 0.963 倍变速

## 已完成的内容

1. `build_story.py` 写入了六段逐字一致的旁白、38 个 Agnes 提示词、7 张信息卡、标题、爆点、金句、字幕高亮、音效事件、事实边界和公开来源。
2. `story.json` 已通过计划结构核对：45 镜 = 38 Agnes + 7 graphic；`audio/manifest.json` 绑定 `voice-00` 和旁白文本。
3. 六段 TTS 已放入 `audio/raw/`；`tighten_pauses.py` 只剪静音、不改字，成品旁白在 `audio/N01.mp3`—`N06.mp3`。
4. `audio/clause-times.json` 已生成；`render.py::CUTS` 已按分句起点前约 0.15 秒重对，`clause_times.py --check-cuts` 全部通过。
5. `抖音脚本.md` 已生成：三个标题、核心爆点、四列详细分镜表、金句结尾、事实边界和资料来源；`抖音发布文案.md` 已生成。

## Agnes 生成与实时校验

工作流在 `.github/workflows/davidsmith-gen.yml`（源模板在 `workflows/`）里，使用 `GEN_REQUEST` 触发：

```bash
echo '{"workers":2}' > production/davidsmith/GEN_REQUEST
git add -A && git commit -m 'davidsmith: prepare Agnes generation' && git push origin arena/01a0d0c4-desktop-tutorial
```

工作流遵守共享 75 秒创建间隔、断点续跑和 SHA-256 收据；每段完成后写入 `results.json` 并生成 `qa/Sxx.jpg` / `qa/Sxx.json`。坏镜头只改它的 prompt 后单独重做，例如：

```bash
echo '{"workers":1,"only":"S07,S18"}' > production/davidsmith/GEN_REQUEST
```

跟进命令：

```bash
gh run list --workflow davidsmith-gen.yml --branch arena/01a0d0c4-desktop-tutorial --limit 1
gh run watch <run-id> --interval 15
```

每个 QA 接触表必须检查：是否中途换场、是否露脸、是否有可读伪文字、手部/物件是否畸变、镜头是否有黑帧或冻结、畸变是否是受控的光学效果而不是人体变形。未通过就不进入 `RENDER_REQUEST`。

## 出片与音画同步闸门

```bash
echo "render $(date -u +%FT%TZ)" > production/davidsmith/RENDER_REQUEST
git add -A && git commit -m 'davidsmith: render first cut' && git push origin arena/01a0d0c4-desktop-tutorial
```

`render.py` 会拒绝未登记或 SHA-256 不匹配的 Agnes 片段，不会用图片/静帧顶替；然后按 `CUTS` 剪辑、生成图卡、烧录大字幕、合成音效和原创氛围配乐，对最终 MP4 再测一次时长、帧数、解码、电平和静音占比。`VERBATIM_REQUEST` 再做六章逐字听检，目标 CER ≤ 0.15。

## 目录地图

| 路径 | 作用 |
|---|---|
| `build_story.py` | 唯一内容源：旁白、45 镜、卡片、标签、音效、标题和发布文案 |
| `story.json` | 180 秒计划与 Agnes 请求数据 |
| `抖音脚本.md` | 用户交付的三标题、爆点、四列详细脚本和来源 |
| `抖音发布文案.md` | 发布正文、置顶问题和话题 |
| `screenplay.md` | 事实边界、逐字旁白、分镜计划、出片闸门 |
| `audio/raw/` | 原始 TTS；`audio/N0x.mp3` 为收紧后的成片配音 |
| `audio/manifest.json` | voice_id、逐字文本和 SHA-256 收据 |
| `audio/clause-times.json` | 分句时间；字幕和 CUTS 共用 |
| `render.py` | CUTS、卡片、字幕、音效、混音、最终复测 |
| `results.json` / `qa/` | Agnes 生成回执、素材哈希和接触表 |
| `workflows/` | 三份项目工作流源文件；复制到 `.github/workflows/` 后可由 marker 触发 |

## 事实与呈现红线

- “暗网涉猎者”没有纳入成片：公开报道支持的是卡车司机、假名接触、长期暴力/性犯罪记录和两起已定罪命案。
- 二零二三年本次重审定罪的是萨拉·克拉姆案；阿曼达·沃克案的终身刑此前已生效。
- 只说英国法律为“新的且有说服力的证据”提供重审例外，不把它说成任意翻案。
- 不展示遗体、血腥或侵害过程；不生成真实人物正脸；不把动画冒充新闻、监控、庭审或原始证物。
- 公开来源列在 `抖音脚本.md` 和 `screenplay.md` 末尾。
