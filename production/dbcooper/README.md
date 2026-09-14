# D.B. Cooper：雨夜里消失的名字

三分钟横屏中文解说短片。由 `production/new_topic.py` 从参考项目 `production/dahlia/`
开出；参考实现只被复制、未被修改，本片所有编辑都发生在这个目录里。

- slug：`dbcooper`
- 出片分支：`arena/01a099eb-desktop-tutorial`（素材生成从 `arena/01a099c4` 接力过来，results.json 已合入本分支）
- 成片目标文件名：`DB库珀劫机案_三分钟_带声音.mp4`（1920×1080 / 30fps / 180s）

## 针对上一版两个问题的设计（2026-09-13 重做）

上一版被指出「运镜总是从远到近飞入、解说跟画面对不上」。本片的对策全部落在
`story.json` 与 `render.py` 里，可逐条核对：

1. **运镜多样化**：25 个 AI 镜头分配了 **19 种不同运镜**（横向移、焦点转移、固定、
   跟拍、微距缓推/缓拉、摇、俯拍固定、升/降、拉远、过肩、舷窗 POV、航拍环绕、
   航拍横移、环绕），每镜的 `story.json` 里都有 `camera` 字段写明技巧，
   英文提示词里也写死了该镜头的具体运动（`Camera: ...`）。
   全片只有 1 个镜头是「推向主体」（S06 微距缓推纸条），
   另有 3 个拉远、3 个升降、1 个环绕——不再是单一飞入。
2. **解说与画面对应**：
   - 先写解说稿，再把 30 镜按解说句段逐一对位（每镜 `purpose` 写明它承担哪句解说）；
   - `render.py` 的 `CUTS` 不是均匀 6 秒一切，而是**在真实配音上逐段测出的自然停顿处**
     （`audio/N01-N06.mp3` 的停顿分析，单位是各段配音的原始秒数）——
     每一刀都落在话题切换的停顿上，说到哪、画面就是哪；
   - 信息卡只在该章说到具体数字时出现（S03 人物描述、S08 条件、S20 搜救结果、
     S23 1980 发现、S27 案件状态），卡面文字与此刻的解说内容一致。
3. **无畸变**：
   - 负向提示词覆盖 deformed hands / extra fingers / warped face / morphing /
     distorted anatomy / fast zoom / whip pan 等；
   - 劫机者一律背影/过肩/手部入画（身份未证实，红线禁止用 AI 脸冒充），
     其余真实岗位人物（机组、空姐、银行员工）同样不露正脸；
   - 出片后按手册第 8 步审片：`production/review_film.py` 自动抓黑帧/冻结帧/亮度/电平，
     对照表 `qa/Sxx.jpg` **人工逐镜看**，严重畸变或穿帮的镜头用
     `generate.py --payload '{"only":"Sxx","workers":1}'` 重新生成后再出片。
   - `render.py` 的窗口/变速闸门（factor ≤ 1.33）防止用慢动作掩盖坏素材。

## 事实边界（详见 screenplay.md 与 story.json 的 principles/sources）

- 有来源的事实才写（FBI 官方页、Britannica、Wikipedia、KIRO 7、CBS News，共 5 条来源）；
- AI 画面全部标注「AI情景重现 · 非历史影像」；
- 不指认任何嫌疑人，DNA/指纹只陈述「未得出名字」；
- 不渲染炸弹、爆炸、伤亡；电线与红火柴只作静态道具；
- 中文姓名、日期、字幕一律后期添加。

## 当前状态（2026-09-13）

| 步骤 | 状态 |
|---|---|
| 剧本 / 分镜 / 事实核查 | ✅ `story.json`（25 Agnes + 5 信息卡）+ `screenplay.md` |
| 配音 | ✅ 六段 mp3（voice-00，用户试听选定），`audio/manifest.json` 带 SHA-256 |
| 闸门一 `generate.py --validate` | ✅ 通过（时间轴、提示词、配音哈希全部一致） |
| CUTS 对轨 | ✅ 本版成片 **34 段**（25 镜 + 5 卡 + S06/b 与 S14/b 复用 + N03 拆刀 + 片尾卡），0 缝隙/重叠，变速比 ≤1.33；卡的切点用从成片字幕反算的真实开口秒；两套对轨按 `boundary_penalty` 择优 |
| Agnes 素材生成 | ✅ **25/25 completed**（Actions 跑，逐镜 checkpoint 回分支） |
| 生成结果人工检视 | ✅ 每张 `qa/Sxx.jpg` 逐镜看，另对成片做全帧抽看。返工次数不靠回忆：分支历史里 `dbcooper: Sxx generated` 共 **51 条 / 25 个镜头 ⇒ 26 次返工**（S28 五次、S22 五次、S17 四次、S09 四次、S01 四次、S11/S07 各三次…）；原因分布：露正脸、provider 故障、机型（含翼下短舱）、嫌疑人画像、自拼字样、上屏文案|
| 渲染混音 + 闸门二/三 | ✅ 成片 180.0s / 5400 帧；混音 −21.75、成片复测 **−21.77 dBFS RMS / 峰值 −1.5 / 静音占比 1.1%**，逐章 −21.7 ~ −21.3 |
| 审片（`review_film.py` + 人工**全帧**看片） | ✅ 见 [`review/审片与听检-2026-09-13.md`](review/审片与听检-2026-09-13.md) 第八节：168 帧"接近全黑"定性为夜戏与片头尾淡变，38 处冻结嫌疑 → 13 真静止（信息卡/档案卡/片尾卡，设计如此）+ 25 微动误判；另按"每编辑段 2 帧"密扫 68 帧全帧（`review/final-sweep-01..03.jpg`）；逐条判定在 `delivery/review-summary.json` |
| 逐字听检 | ✅ `VERBATIM_REQUEST seq8`，run 34809143395：六章 CER 0.0294–0.0769（上限 0.15，`failing: []`），差异全是 ASR 的同音字/数字写法；报告自带 `film_sha256` 且被测试要求等于 `technical-report.json` 的 sha（对照组 N03 反而 0.1346）。六个连续版本的 AAC 流 sha256 前缀同为 `4976ca9100e9264e`，所以跨版 CER 一模一样|
| 成片 | ✅ `交付/DB库珀劫机案_三分钟_带声音.mp4`（52,908,455 字节，SHA-256 `974a487f534eacd1…`，见 `delivery/technical-report.json`；无瑕疵轮第十版，依次替换 `6e110ff0…`→`25970170…`→`41cdd275…`→`4bc53d9b…`→`a9c144d3…`→`b10cad23…`→`a8460c30…`→`86f89636…`→`200b3784…`→`efe1f921…`） |
| 无瑕疵轮（同日第二、三轮） | ✅ 第四轮（同日）：台账 **30 条 = 已修并在成片复验 21 · 不修或残留并给量化理由 8 · 有意保留 1**。本轮新消掉的 9 条都在"上屏文字与物体属性"这一类：片尾卡的工程路径、archive 卡的 TODO 占位文字、S28/S01 的模型自拼字样与伪涂装、S01/S10/S28 的机型不一致、档案卡表头那个不存在的航司名，另有机型一致性与上屏文案两条测试；`visual_review=pending` 仍有意保留；逐条见 `delivery/review-summary.json` |
| 换机器复现混音 | ✅ 沙箱重跑 `build_audio.py`，与云端记录逐项差 0.00 dB（`delivery/reproducibility-2026-09-13.json`，有测试钉住） |

**打回重做的四镜**（这就是"人工逐镜看"要抓的东西，自动闸门看不见）：

| 镜头 | 问题 | 处理 |
|---|---|---|
| S05 | 空姐转身面向镜头，正脸全程可见——违反本片"机组不露正脸"的自述 | 提示词加硬约束（机位全程在她背后、任何一帧不许出现人脸），重生成 |
| S11 | 写的是"盘旋的飞机"，模型自作主张切进驾驶舱/候机楼（多张正脸），内容漂移 | 提示词加"纯外景航拍，绝不进机舱"，重生成 |
| S17 | 跳伞镜头里是**红色单发螺旋桨小飞机**，不是三发 T 尾的波音 727 | 提示词点名机型 + 明确"绝不是螺旋桨小飞机"，重生成 |
| S10 | provider 侧 500，任务判死两次 | `--prune-failed` 清掉死任务后重新提交 |

这段"已知残留"已经消掉：当年 S17 的剪影是四发翼吊，现在它的命题里根本没有飞机
（"the airliner has already flown out of the top of the shot"）；S01/S10 同理（见下节第 4 条）。
机身确实入画的只剩 S11/S12/S13/S28 四处，本版成片逐条复核为 T 尾 + 翼下干净 + 无涂装文字；
S29 是纯森林镜，画面里没有飞机。

## 第四轮补上的四条红线（都是吃过亏才写下来的）

1. **上屏文案里不许有工程标识**。观众拿不到 `story.json`：片尾卡那行原本印「来源见 story.json 的 sources」，
   等于把内部便条当字幕。`render.py` 里所有 `centered(` / `d.text(` 的字符串字面量由测试扫描，
   出现 `.json|story.|production/|work/|.md` 即红。
2. **脚手架占位文字不许留在能上屏的路径上**。`archive_image()` 抄自参考项目，里面还写着「TODO 档案卡标题」三行；
   本片 archive 镜头数为 0 所以没上屏——但闸门不该指望"没人点到它"，所以它现在直接 `raise RuntimeError`。
3. **卡面上的名字要么是事实要么不写**。地区名待在公司名的位置上（`PACIFIC NORTHWEST`）会被读成"片方编的航司"；
   改成可核的航段 `PORTLAND-SEATTLE-RENO`（14:50 波特兰、17:46 西雅图塔科马、22:15 里诺，均出自 sources）。
4. **负向清单压不住"物体自带属性"的先验——四次应验**：S09 钞票必带数字、S07 越肩机位必有人头、
   S28 机身必带涂装与注册号、S01 停机位必有一架带字的飞机。写 `absolutely NO letters/engines/faces` 都没用。
   唯一有效解是**让那个物体或那个表面不在这镜的命题里**（推远到读不出，或整个取消）。
   配套两条：判读一律在**成片全帧**上做（`qa/Sxx.jpg` 是 2 fps、每格 384 px 的印相，两次穿帮都是从那儿漏掉的）；
   机型一致性由 `PlanTests::test_the_airframe_is_the_same_aircraft_in_every_shot_that_shows_it`
   钉住镜头集合与句式，改一个镜头的命题就会被迫回答"这镜里还有没有机身"。

## 出片步骤（在 GitHub Actions 上）

1. **生成素材**：「DB库珀 · Agnes生成」（`.github/workflows/dbcooper-gen.yml`，
   与 `dbcooper-agnes.workflow.yml` 逐字节一致，有测试守着）已在 2026-09-13 起
   同时支持两种触发方式：
   - 人在 Actions 里点，填 `payload`；
   - 代理（没有 workflow_dispatch 权限时）把要补的镜头写进
     `production/dbcooper/GEN_REQUEST`（如 `{"only":"S10","workers":1}`）再 push——
     只有这个文件变化才触发，逐镜 checkpoint 不会把出片循环点着。
   25 个镜头 × 75 秒节流 ≈ 30~60 分钟；`results.json` 与 `qa/` 抽帧逐镜 commit 回本分支。
   **补坏镜头**：provider 判死的任务（如 S10 的 500）会连带清掉——工作流先跑
   `generate.py --prune-failed`，否则重跑只会去轮询同一个已死的 task_id。
2. **出片**：两条路等价——
   - 人在 Actions 触发「解说短片出片」（`.github/workflows/commentary-render.yml`），
     `project` 填 `dbcooper`，`film_name` 填 `DB库珀劫机案_三分钟_带声音.mp4`；
   - 代理把 `production/dbcooper/RENDER_REQUEST` 的 `seq` +1 后 push，
     走本项目的 `.github/workflows/dbcooper-render.yml`（与
     `dbcooper-render.workflow.yml` 逐字节一致，有测试守着）。
   两者跑的都是 `production/run_project.sh`：按 SHA-256 回填素材（不重新生成）、
   渲染混音、复测电平，并把成片与报告 commit 回本分支的 `交付/` 与 `delivery/`。
3. **审片**：`python3 production/review_film.py --film 交付/DB库珀劫机案_三分钟_带声音.mp4
   --project production/dbcooper --work work/dbcooper/review`；
   逐字听检：「逐字听检」工作流填 `dbcooper`。

## 目录

| 路径 | 作用 |
|---|---|
| `story.json` | 分镜计划：30 镜 × 6 秒 / 6 章 × 30 秒，含 `camera` 运镜字段与 5 条来源 |
| `screenplay.md` | 解说稿 + 事实边界 + 分镜表 + 运镜策略说明 |
| `audio/N01-N06.mp3` | 六段配音（voice-00），`manifest.json` 记录文件名/SHA-256/逐字文本 |
| `generate.py` | Agnes 生成（75 秒节流、断点续跑）+ `--validate` 闸门 |
| `fetch_sources.py` | 按 `results.json` 的 SHA-256 回填素材，不重新生成 |
| `render.py` | 剪辑（CUTS 已按真实停顿对齐）、字幕、信息卡、混音、成品复测 |
| `build_audio.py` | numpy 混音 + 静音闸门 |
| `dbcooper-render.workflow.yml` | 本项目专属的出片工作流模板（`RENDER_REQUEST` 的 push 即可触发） |
| `dbcooper-agnes.workflow.yml` | 本项目专属的 Agnes 生成工作流模板（需复制到 .github/workflows/） |
| `results.json` | 生成回执（生成后出现）：请求哈希、SHA-256、CDN 地址 |
| `qa/` | 每镜抽帧回执（生成后出现），人工审片用 |
| `delivery/` | 出片后的实测报告 |
