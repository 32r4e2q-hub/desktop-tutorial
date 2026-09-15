# 披萨炸弹劫案（2003）· 动画解说片

《贴身绑爆弹的快递员：披萨炸弹劫案（2003）》——三分钟横屏中文解说，
风格化 2D 动画纪录片（不冒充真实影像，不使用任何真实人物面孔）。

## 这个目录里有什么

| 文件 | 作用 |
|---|---|
| `story.json` | 唯一真相源：六章解说、30 个镜头（23 Agnes 动画 + 7 信息卡 + 0 档案）、原则与来源 |
| `screenplay.md` | 剧本+事实边界（有来源/并列呈现/坚决不画）+分镜表+运镜策略 |
| `render.py` | 本地成片装配：CUTS（切点实测自配音停顿）、字幕、混音、SFX |
| `generate.py` | 云端 Agnes 生成器：幂等、断点续跑、逐镜 checkpoint 回分支 |
| `align_audio.py` / `build_audio.py` | 字幕时间轴（ASR→停顿回退）与确定性混音 |
| `fetch_sources.py` | 抓真实档案帧并出接触表（本片 0 archive 镜头，保留供核验） |
| `throttle.py` / `watch_run.py` | 云端节流（2 路×75s）与 Actions 运行日志轮询 |
| `audio/` | 六段配音 N01–N06.mp3 + `manifest.json`（用户试听选定 voice-00） |
| `GEN_REQUEST` / `RENDER_REQUEST` / `VERBATIM_REQUEST` | 三张触发便签（push 才生效，见下） |
| `*.workflow.yml` | 三条流水线的模板；`.github/workflows/pizzabomber-*.yml` 是逐字节一致的已装副本 |

## 流水线（顺序固定）

1. `python3 production/pizzabomber/generate.py --validate` —— 剧本/时间轴/配音哈希的离线闸门。
2. 把 payload 写进 `GEN_REQUEST` 并 push → `披萨炸弹 · Agnes生成` 跑 23 镜（约 30–60 分钟，
   逐镜 checkpoint 回本分支；`--prune-failed` 先清死任务）。
3. 素材齐后把 `{{"ts":"..."}}` 写进 `RENDER_REQUEST` push → `披萨炸弹 · 出片`：
   回填素材 → 混音 → 渲染 → QC → 成片与报告 commit 回分支、拷入 `交付/`。
4. 人工看 `production/pizzabomber/qa/S*.jpg` 接触表逐镜查畸变/露脸/穿帮；
   坏镜头 `{"only":"Sxx"}` 重生成，回第 2 步。
5. `VERBATIM_REQUEST` push → 逐字听检（CER≤0.15）；`review_film` 查黑帧冻结帧。
6. 三道闸门 + 人工全部绿了才算交付；`制作过程.md` 记录每步数字与返工。

## 红线（写进 `story.json` principles，逐条有测试）

- 真实人物不露正脸（背影/剪影/手部/道具），不用 AI 脸冒充本人；
- 不渲染起爆瞬间与伤亡；装置只做静态道具特写，标注「依警方描述绘制 · 示意」；
- 卡面数字与解说逐字同源；中文文字一律后期排版，画面内无伪文字/品牌；
- 韦尔斯是共谋还是受害者：只并列两方口径，片内不作裁决。

## 已知边界

- 沙箱不能直连 Agnes API（HTTP 000），生成/听检必须在 Actions runner 上跑；
- 配音由平台 TTS 生成（voice-00 为用户试听选定），逐字与剧本三处同步由测试钉死；
- `results.json` 只在云端生成后回传，本地永远以分支上的最新版本为准。
