# 天使医生：哈罗德·希普曼的250条人命

由 `production/new_topic.py` 从参考项目 `production/dahlia` 开出来的新项目目录。
参考实现只被复制，没有被修改；本片的所有编辑都发生在这个目录里。

- slug：`shipman`
- 出片分支：`arena/01a0c697-desktop-tutorial`

## 现在还不能出片（故意的）

`generate.py --validate` 现在**会失败**，因为提示词、解说词、配音都是空的。
按下面顺序填完，它才会放行。

## 待办清单

1. **事实与红线** → `story.json` 的 `principles` / `sources`，`screenplay.md` 的「事实边界」。
   每一条要说的话都得有公开来源；没有来源的推测不写。
2. **解说稿** → 六段各 90–120 字。同一段文字要**逐字一致**地出现在三处：
   `screenplay.md`、`story.json` 的 `chapters[].text`、`audio/manifest.json` 的 `clips[].text`。
3. **分镜提示词** → `story.json` 的 `shots[].prompt`（英文，前面会自动拼 `style_prefix`）、
   `purpose`、`transition_out`。信息卡镜头把 `kind` 改成 `graphic` 并写 `graphic` 文案；
   用真实档案照片的镜头改成 `archive`，并补 `archive_asset` / `archive_sha256`。
4. **配音** → 六段 mp3 放进 `audio/`，把每段的 `sha256` 和 `text` 填进 `audio/manifest.json`：

   ```bash
   sha256sum audio/N01.mp3
   ```

5. **剪辑表与字幕内容** → `render.py` 的 `CUTS` 骨架是均匀 6 秒一切，**必须**听完配音后按真实停顿重对。
   副本里已经用 `TODO` 标出三处参考项目专属内容：字幕高亮关键词、逐镜标签覆盖、片头字幕卡。
   需要具名信息卡（参考项目的 `portrait_a` / `archive` / `truth` 那类）时，
   在本目录副本的 `card_image()` / `archive_image()` 里加分支，别去改参考项目。
6. **校验** → `python3 production/shipman/generate.py --validate` 必须通过。
7. **出片** → 本地：`bash production/run_project.sh shipman`；
   Actions：「解说短片出片」→ `project` 填 `shipman`（`.github/workflows/commentary-render.yml`
   已经在仓库里，不用再放一次；它必须与 `production/commentary-render.workflow.yml`
   逐字节相同，`python3 -m pytest production/tests/test_workflows.py -q` 守着这件事）。
   想要专属按钮，把本目录的 `shipman.workflow.yml` 复制成 `.github/workflows/shipman.yml`——
   这一步代理做不了（GitHub App 缺 workflows 权限，push 与 API 均 403），只能你手动做，
   而且要**逐字节照抄**：上一次贴错内容（贴成聊天正文）让 main 每次 push 都失败一次。
   `film_name` 留空会用标题当片名，重跑已交付的片子请填原片名。

## 目录

| 路径 | 作用 |
|---|---|
| `story.json` | 分镜计划：30 镜 × 6 秒、6 章 × 30 秒（骨架已算好，内容待填） |
| `screenplay.md` | 解说稿 + 事实边界 + 分镜表 |
| `audio/manifest.json` | 六段配音的文件名、SHA-256 与逐字文本 |
| `generate.py` | 生成 AI 素材（75 秒节流、断点续跑）+ `--validate` 闸门 |
| `fetch_sources.py` | 按 `results.json` 的 SHA-256 回填素材，不重新生成 |
| `build_audio.py` | numpy 混音 + 静音闸门（整体/逐段电平不达标就报错） |
| `render.py` | 剪辑、字幕、信息卡、封装，并对**最终 mp4** 复测电平 |
| `align_audio.py` | 字幕对轨（ASR 或停顿估算） |
| `media.py` / `throttle.py` | 探测与节流的公共实现（副本） |
| `shipman.workflow.yml` | 本项目专属的出片工作流模板（放到 `.github/workflows/` 才能用） |
| `../run_project.sh` | **所有项目共用**的出片脚本：`bash production/run_project.sh shipman` |

## 红线（继承自参考项目，不要删）

- AI 画面一律标注「AI情景重现 · 非历史影像」，不冒充真实影像；
- 真实人物只用有出处的档案照片，不用 AI 生成的脸冒充本人；
- 未侦破的案件不指认凶手，推测不写成结论；
- 中文姓名、日期、字幕一律后期添加，不交给视频模型拼写；
- 成片必须实测电平（`--validate` 之后还有 `render.py` 的成品复测），无声不许交付。
