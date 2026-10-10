# CogVideoX 三分钟横版短片开工手册

> **适用范围**：把一份中文案件长稿制作成 180 秒、16:9、带配音/字幕/配乐的写实 3D 动画短片。
>
> **跑通参考**：`production/jeong2000/`《郑斗英：十个月，九条人命》。
>
> **动态画面供应商**：智谱 `cogvideox-flash`，读取仓库 Secret `ZHIPUAI_API_KEY`；**不调用 Agnes**。

这份手册只记录郑斗英项目实际跑通并返修过的流程。素材生成、断点续跑、SHA-256 回填、字幕、混音、逐字听检、5400 帧全帧 QC、人工语义签收和 Release 上传都有仓库中的真实实现。

---

## 一、成片标准

| 项目 | 标准 |
|---|---|
| 成片 | 1920×1080、30 fps、180 秒、5400 帧、H.264 + AAC |
| 结构 | 六章，45 镜 × 4 秒规划网格；推荐 38 动画 + 7 信息卡 |
| 动画 | `cogvideox-flash`，`quality="speed"`，实际素材通常约 6 秒 |
| 配音 | 六段中文 TTS；原始音频放 `audio/raw/`，收紧后放 `audio/N0x.mp3` |
| 字幕 | 分句字幕、关键词描黄；切点必须落在真实分句停顿窗内 |
| 声音 | 最终 MP4 实测，不接受“源音频有声但成片没声” |
| 视觉 | 逐镜接触表 + 最终 5400/5400 帧扫描 + 全帧表人工复核 |
| 来源 | 每句事实能指向公开来源；冲突口径写保守表述 |

郑斗英返修终版的实测参考：180 秒、5400/5400 帧、六章听检全部低于 CER 0.15；所有动态镜头都有供应商 URL、请求哈希和素材 SHA-256 收据。

---

## 二、一次性准备

### 1. 仓库 Secret

GitHub 仓库设置中添加：

```text
ZHIPUAI_API_KEY=<智谱 API Key>
```

Secret 只在 Actions 环境中读取，不写进文件、不打印完整值、不进 Git。

### 2. 开新项目

```bash
python3 production/new_cogvideox_topic.py \
  --slug newcase \
  --title "新案件标题" \
  --branch arena/<当前固定分支>
```

脚手架会创建：

- 空白的 45 镜 / 六章内容骨架；
- CogVideoX 生成器与 CDN 素材回填器；
- 渲染、配音收紧、分句对时、逐镜 QC、全帧 QC 工具；
- 生成 / 出片 / 逐字听检 / 全帧视觉 QC 四份工作流；
- 空的 `results.json`，不会继承郑斗英的 task id、URL 或素材。

它**故意不能立即生成**：内容、配音与哈希必须先补齐。

---

## 三、内容阶段

### 第 1 步：先核实事实

在 `production/<slug>/build_story.py` 填写：

- `SOURCES`：来源 URL 与每条来源支撑的句子；
- `PRINCIPLES`：不展示什么、不确定事实怎么写、人物肖像边界；
- `CHAPTERS`：六段逐字口播；
- `SHOTS`：45 镜；
- `CARDS`、片头片尾、关键词、音效与发布文案。

事实冲突时不要硬选一个数字。例如郑斗英案中“九人”包含早年的警员案，连续十个月的案件为另外八人；最终口播必须主动拆开口径。

### 第 2 步：写六章口播

建议合计约 760–800 字，但最终以音频时长为准：

```text
180 秒
- 片头 0.6 秒
- 片尾 6 秒
- 五个章间隔 × 1.08 秒
= 约 168 秒口播窗口
```

要求：

- 前五秒直接给反转或关键报警；
- 数字写中文读法，避免 TTS 念错；
- 不写血腥细节、侵害细节或可复制的越狱/入室步骤；
- 每章末尾留下一章钩子；
- `story.json`、`screenplay.md`、`audio/manifest.json` 的口播必须逐字一致。

### 第 3 步：写 45 镜

推荐 38 个 `kind="cogvideo"` + 7 个 `kind="graphic"`。

CogVideoX 提示词遵循：

1. **一个镜头只写一个地点、一个主体状态、一个运镜**；
2. 动作越复杂，穿墙、穿门、肢体融合风险越高；
3. 能用静物或空镜表达，就不要让人物开门、进门、抓取、交接物品；
4. 明确 `no cut, no scene change, no camera relocation`；
5. 不让模型生成中文、门牌、报纸、钞票细节或制服文字；
6. 人物只给背影、远景或画外阴影，不还原真实人物面孔。

郑斗英项目的返修教训：

- “人物走向门口”可能变成人物穿门，改为空走廊；
- “手打开抽屉/拿取物品”容易生成畸形手，改为抽屉已经打开、物品已经摆好；
- “便衣带包进门”风险很高，改为包或门外空镜；
- 只看中间帧不够，畸变往往发生在开头或结尾，必须看整段全帧表。

写完运行：

```bash
python3 production/<slug>/build_story.py
```

---

## 四、配音与切点

### 第 4 步：生成六段配音

先试听并选音色，把六段原始输出保存为：

```text
production/<slug>/audio/raw/N01.mp3
...
production/<slug>/audio/raw/N06.mp3
```

然后：

```bash
python3 production/<slug>/tighten_pauses.py
python3 production/<slug>/clause_times.py
sha256sum production/<slug>/audio/N0*.mp3
```

把收紧后六段音频的 SHA-256 写入 `audio/manifest.json`。

### 第 5 步：按停顿调整 CUTS

`render.py::CUTS` 中每个切点取分句起点前约 0.15 秒：

```bash
python3 production/<slug>/clause_times.py --check-cuts
```

必须全部通过，并满足：

- 45 镜全部用到；
- 每镜只出现一次；
- 动画段不能长到需要过度慢放；
- 信息卡可以承接较长句子；
- 改口播或重做配音后，CUTS 必须重新计算。

### 第 6 步：运行第一道总闸门

```bash
python3 production/<slug>/generate.py --validate
```

通过时应看到类似：

```text
VALID: 180-second plan; 45 shots; 38 CogVideoX-Flash sources; 7 graphics; narration hashes match
```

---

## 五、安装工作流并生成素材

### 第 7 步：安装四份项目工作流

```bash
cp production/<slug>/workflows/<slug>-*.yml .github/workflows/
python3 -m pytest production/tests -q
```

工作流必须固定到当前 Arena 分支，并使用：

```yaml
runs-on: ${{ vars.RUNNER_LABEL || 'ubuntu-latest' }}
```

### 第 8 步：触发 CogVideoX

全量生成：

```bash
printf '{"workers":1}\n' > production/<slug>/GEN_REQUEST
git add -A
git commit -m '<slug>: 触发 CogVideoX-Flash 生成'
git push origin <当前固定分支>
```

单镜返修：

```bash
printf '{"workers":1,"only":"S06,S13"}\n' > production/<slug>/GEN_REQUEST
```

生成器行为：

- 调用 `client.videos.generations(model="cogvideox-flash", quality="speed", prompt=...)`；
- 遇到 1305 / 429 / 暂时性网络问题退避重试；
- 每镜保存 task id、URL、请求哈希、字节数与 SHA-256；
- 每完成一镜就回写分支，失败后可继续；
- 请求哈希没变且已有完成收据时，不重复花额度；
- 素材视频不提交 Git，只提交小型接触表和收据。

`results.json` 是素材来源证明；不要手改已完成镜头的 SHA-256。

---

## 六、逐镜复审与返修

### 第 9 步：第一轮逐镜检查

检查 `production/<slug>/qa/Sxx.jpg`：

1. 是否表达当前旁白，而不是只“看起来高级”；
2. 是否中途换景；
3. 人物是否穿门、穿墙、凭空出现或融合；
4. 手、腿、头部是否变形；
5. 是否出现可读伪文字、车牌、品牌、模型水印；
6. 是否出现遗体、血迹、攻击动作等越界内容。

发现问题：先改 `build_story.py`，重建 `story.json`，再用 `only` 只重做坏镜头。

### 第 10 步：处理模型角标

郑斗英流水线采取两层处理：

- 不在 ASS 字幕中叠加右上/右下“AI生成”标签；
- `render.py` 对 CogVideoX 源片默认安全推近 `1.12×`，裁掉供应商角标。

如新供应商改变角标位置，必须看片确认，不能只假设裁切有效。

---

## 七、出片、听检与全帧审计

### 第 11 步：出片

素材齐全后写 `RENDER_REQUEST`；也可由生成工作流自动触发。

本地等价命令：

```bash
bash production/run_project.sh <slug> false '<成片文件名>.mp4'
```

渲染器会：

- 从 CDN 按 URL 下载并核对 SHA-256；
- 缺一个镜头就失败，不用静帧冒充视频；
- 生成 EDL、字幕、配乐、音效和最终 MP4；
- 对最终 MP4 复测时长、帧率、声音电平与静音比例。

### 第 12 步：逐字听检

写 `VERBATIM_REQUEST` 触发最终成片转写：

- 每章 CER ≤ 0.15；
- 检查对象必须是最终 MP4，而不是源配音；
- 数字、人名、地名的同音替换要人工确认。

### 第 13 步：全帧视觉 QC

写 `VISUAL_QC_REQUEST`，输出：

- `frame-distortion-audit.json/.md`；
- `visual-qc-summary.json`；
- `qa/final-frame-review/all-frames/`；
- 人脸、手部、时序异常候选。

自动状态 `REVIEW` 不等于失败，也不等于通过。必须逐张查看 45 镜 + 片尾的全帧表；人物穿门这种语义错误可能不会触发任何自动阈值。

任何素材、裁切或字幕改动后，都必须重新执行：

```text
出片 → 逐字听检 → 5400 帧 QC → 人工语义签收
```

旧报告不能证明新成片。

---

## 八、Release 下载链接

先创建 Release 壳：

```bash
gh release create <tag> --target <当前分支> --title '<标题>' --notes '<规格与 SHA-256>'
```

写 marker：

```text
production/<slug>/RELEASE_UPLOAD_REQUEST

tag=<tag>
src=交付/<中文成片名>.mp4
asset=<ASCII文件名>.mp4
```

提交并推送后，通用 `release-upload.yml` 由 runner 上传。返修同一版本时修改 marker，再次触发 `--clobber`，并更新 Release notes 与新 SHA-256。

---

## 九、故障处理

| 症状 | 处理 |
|---|---|
| 1305 / 429 | 不换 key 绕限流；等待生成器退避，必要时稍后重触发 |
| 任务已失败却反复轮询 | `generate.py --prune-failed` 清掉无 URL 的失败收据 |
| CDN 下载哈希不一致 | 立即失败；不要忽略，不要拿别的镜头替代 |
| 画面穿门/融合 | 改成静物、空镜或动作发生后的状态，再只重做该镜 |
| 手部畸变 | 从提示词彻底删除手与抓取动作，不要只加 negative prompt |
| 角标仍可见 | 调整 `DEFAULT_COGVIDEO_CROP`，重渲染并重新全帧检查 |
| CUTS 过度慢放 | 把切点移动到相邻分句停顿，或把较长段分给信息卡 |
| Release 还是旧文件 | 修改 `RELEASE_UPLOAD_REQUEST` 触发上传，并核对资产字节数与 SHA-256 |

---

## 十、签收清单

发布前逐项确认：

- [ ] 45 镜、180 秒、每镜只用一次；
- [ ] `results.json` 中 38 个动画镜头均为 completed；
- [ ] 模型全部是 `cogvideox-flash`，未调用 Agnes；
- [ ] 六段口播、字幕、脚本逐字一致；
- [ ] 最终 MP4 有声且电平达标；
- [ ] 5400/5400 帧解码；
- [ ] 所有候选和全帧表已人工看完；
- [ ] 无穿门、穿墙、肢体/手部畸变、伪文字与供应商角标；
- [ ] Release 资产 SHA-256 等于本地交付文件；
- [ ] 发布文案明确为动画情景重现，但成片画面是否保留角标按本项目要求执行。
