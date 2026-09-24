# BTK：软盘里的名字

本项目按照仓库根目录 [`新题目开工手册.md`](../../新题目开工手册.md) 与吉尔戈成片流程制作；视觉基准为《吉尔戈海滩：披萨盒里的凶手》的手绘二维动画纪录片风格。项目目录独立，参考片不修改。

- 固定分支：`arena/01a0d3ca-desktop-tutorial`
- 目标：横版16:9，1920×1080、30fps、180秒
- 镜头计划：45镜 = 38段 Agnes Video V2.0 动画 + 7张后期信息卡，每镜一次、不复用
- 案情边界：十名已确认受害者，1974—1991；2005年被捕、认罪并判十个连续终身监禁（最低175年）
- 脚本：[`抖音脚本.md`](抖音脚本.md)（按六段配音切点生成；TTS文本逐字校验通过）
- 事实底稿：[`screenplay.md`](screenplay.md)
- 状态记录：[`制作过程.md`](制作过程.md)

## 已完成

- 以 `new_topic.py` 开出独立项目和吉尔戈模式工具副本。
- 写完六段口播、45镜提示词、7张信息卡、画面原则、片头片尾卡、音效提示与发布文案，内容唯一源为 `build_story.py`。
- 脚本已通过事实边界校正：不把女儿样本误称为“直接完美匹配”；不说雷德已经在狱中死亡；不将当庭叙述改写成无来源的心理诊断。
- 逐镜提示词限定单场景、单运镜；禁止可读伪文字、正脸、血腥和暴力过程。
- 用户试听选择了普通话男声 `voice-00`；六段TTS已生成，原始总长164.69秒，收紧长静音后162.92秒，180秒成片中的旁白段目标变速0.970×；SHA-256收据已填，`generate.py --validate` 已通过。
- 分句切点由 `clause_times.py` 与 `align_cuts.py` 写入；`clause_times.py --check-cuts` 通过。渲染时字幕将优先使用Whisper词级对轨。

## 出片流程 / 闸门

1. 试听并选定中文旁白音色；生成六段配音到 `audio/raw/`，之后运行 `tighten_pauses.py`、`clause_times.py` 并回填 SHA-256。
2. `align_cuts.py` 按句首与片段长度动态规划切点，`clause_times.py --check-cuts` 校验；最终字幕优先使用渲染流程的 Whisper 词级时间。
3. `generate.py --validate`：180秒规划、45镜、38个Agnes源、7卡、逐字稿与音频哈希全部吻合。
4. Agnes生成：通过 `GEN_REQUEST` 触发 GitHub Actions。每个镜头按75秒节流、断点续跑；回执与14帧接触表写入 `results.json`、`qa/`。
5. 逐镜人工审看接触表：场景是否正确、7秒内是否换场、人物/手部是否畸变、伪文字、画面跳变与运镜偏差。问题镜只重做对应ID，并把每次改动记入制作过程。
6. `render.py` 的 CUTS 按分句边界重排；所有镜头各用一次、素材SHA-256须匹配回执。
7. `RENDER_REQUEST` 出片；对最终MP4逐帧技术抽检（帧率/画幅/时长/黑帧/冻结帧/畸变/字幕切点）、逐镜中点接触表、全片音量/峰值/静音、音画同步。
8. `VERBATIM_REQUEST` 做逐章语音转写听检；每章CER ≤ 0.15。未完成真实素材生成、画面复审、成片复检和听检前，不宣称已完成成片。

## 启动命令

```bash
python3 production/btk/build_story.py
python3 production/btk/build_story.py --publish
python3 production/btk/generate.py --validate   # 等音频文件和sha256完成后才通过
```

GitHub工作流模板保留在 `workflows/`，本分支的三份工作流已安装到 `.github/workflows/`。写入 `GEN_REQUEST` / `RENDER_REQUEST` / `VERBATIM_REQUEST` 并push即可触发；当前已准备 `GEN_REQUEST`，等待本分支推送后启动Agnes素材生成。云端生成仍受Agnes官方请求速率限制，不做限流绕过。
