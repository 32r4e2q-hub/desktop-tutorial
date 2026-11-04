# 新奥尔良斧头杀手：那个全城放爵士乐的夜晚

三分钟横屏（16:9 · 1920×1080 · 24fps · 180 秒）中文悬疑 3D 动画纪录片。
**30 个 Agnes Video 2.5 Flash 连续运动镜头**（720P 源片，`mode=reference` + 定稿参考图，后期放大到 1080P），
一镜一句中文旁白，字幕与配音同起止，原创程序合成 BGM 与音效。

> 画面为 AI 动画情景重现，不是历史影像。全片不出现遗体、伤口、血腥或挥砍过程；
> 斧头只以墙上的影子、剪影与静物出现；受害者（含那名两岁的孩子）不入画；
> 斧头杀手始终是没有面容的黑影；所有真实人物一律为风格化形象，不复制任何真实相貌。

## 一句话卖点

1919 年 3 月，一封署名「来自地狱」的信让整座新奥尔良在午夜 12:15 同时放起爵士乐——
因为信里说：放爵士的人家，斧头不会落下。那一夜，没有人遇害。

## 结构（九段 / 30 镜）

| 段 | 时间 | 镜号 | 内容 | 色调 |
|---|---|---|---|---|
| N1 开头钩子 | 0:00–0:10 | S01–S02 | 午夜钟声，全城窗口亮起，金色音符汇成河流；街角墙上一道斧头影子被乐声淹没 | 爵士（暖金） |
| N2 第一案 | 0:10–0:35 | S03–S06 | 1918 年 5 月马乔杂货店；凿子在后门板上凿出方洞；墙上斧影；清晨钱一分没少 | 恐惧（冷青） |
| N3 恐慌蔓延 | 0:35–1:00 | S07–S10 | 警局地图的红线；后门又一次被凿开；斧头被藏进柜子、门窗钉死；报纸飞过街头 | 恐惧 |
| N4 对岸的一夜 | 1:00–1:25 | S11–S14 | 1919 年 3 月 10 日格雷特纳；皮球滚到门槛停住；邻居父子被定罪；证词出问题 | 恐惧 |
| N5 来自地狱的信 | 1:25–1:48 | S15–S18 | 报社拆信；信纸逐行亮起，钟面指向 12:15；报纸印出；留声机响起，街角黑影抬头 | 恐惧 |
| N6 全城爵士夜 | 1:48–2:10 | S19–S22 | 全城准备乐器；作曲家连夜写曲；11:59 窗口依次点亮；12:15 乐声震耳，黑影后退 | 爵士 |
| N7 最后一案 | 2:10–2:30 | S23–S25 | 秋天街头松一口气；10 月 27 日后屋黑影与妇人；地上的凿子与斧头剪影 | 恐惧 |
| N8 传闻中的凶手 | 2:30–2:48 | S26–S28 | 日历翻到 1920；洛杉矶街头；橱窗倒影里戴帽子的男人一晃而逝 | 恐惧 |
| N9 结尾钩子 | 2:48–3:00 | S29–S30 | 档案里空着的那一行；深夜窗口与墙上的斧影；金色片名与互动提问 | 爵士 |

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 定稿参考图 | ✅ 24 张（9 角色 + 10 场景 + 5 道具），逐张看过，`reference/revision.txt` 指向不可变提交 | `reference/` |
| 分镜 / 事实边界 / 提示词 | ✅ 30 镜、180 秒；生成器自动拼接 STYLE（双色调）+ 角色锚点 + 参考图说明 + NEGATIVE | `build_story.py`、`story.json` |
| 一镜一句旁白 | 🟡 S01–S10 已录（voice-00，低沉悬疑男声），S11–S30 待录 | `audio/manifest.json` |
| 离线自检 | ✅ 16 项：`python3 -m unittest production.tests.test_neworleans1919 -q` | `production/tests/` |
| Agnes 片段 | 🟡 30 镜已下单（`GEN_REQUEST`），进度看 `results.json` | `results.json`、`qa/` |
| 成片 / 封面 / 字幕 | ⏳ 等旁白齐 + 素材齐后 `RENDER_REQUEST` | `交付/` |

## 怎么跑

```bash
python3 production/neworleans1919/build_story.py                        # 重建 story.json / 清单 / 脚本
python3 production/neworleans1919/generate.py --validate --clips-only   # 无配音也能验的分镜闸门
python3 production/neworleans1919/publish_reference.py --check          # 参考图齐不齐
python3 -m unittest production.tests.test_neworleans1919 -q
```

云端（沙箱 token 没有 `actions:write`，只能用 marker 文件 push 触发）：

| 触发文件 | 作用 |
|---|---|
| `production/neworleans1919/GEN_REQUEST` | `{"mode":"clips","workers":2}` 生成 30 条片段；单镜重做写 `{"only":"S07"}` |
| `production/neworleans1919/RENDER_REQUEST` | 旁白齐了之后只做 1080P 出片（拼接 / 字幕 / 混音 / 封面） |
| `production/neworleans1919/QC_REQUEST` | 只跑成片质检（**优先级最高**，想重渲先删掉它） |

## 规格

- **模型**：`agnes-video-2.5-flash`，`size=720P`、`aspect_ratio=16:9`、`mode=reference`、`n=1`、`images=[定稿参考图]`；
  请求形状 `model/prompt/seconds/size/aspect_ratio/mode/n/seed/images` 九个字段，NEGATIVE 写在提示词正文里。
- **参考图**：`raw.githubusercontent.com/…/<不可变提交>/production/neworleans1919/reference/<ID>.png`，绝不指向可变分支。
- **节流**：61 秒共享闸门、2 个 worker；「video queue is full」按 61 秒重试；30 镜一轮约 30 分钟，断点续跑。
- **双色调**：恐惧线冷青 / 深蓝 / 泛黄；爵士线暖金 / 琥珀 / 橙红。`style_for()` 按镜头 `style_variant` 二选一，
  爵士镜固定为 S01–S02、S19–S22、S30。
- **旁白与镜头等长**：一镜一句，先录再量，只在必要时 ≤1.55× 轻微加速，不慢放、不截字；
  实测表 `qa/narration-fit.md`（`mode=qc` 自动生成，出现 `over` 直接判失败）。
- **字幕**：白色黑边、底部安全区、关键词金色放大；每条最多两行、每行 ≤26 字（`split_caption` 在标点处断行）。
- **片尾**：S30 窗口与斧影，后期叠金色「新奥尔良斧头杀手」＋「新奥尔良 · 1918—1919 · 爵士之夜」，
  最后 0.8 秒淡出至静音。
- **封面**：右侧暖金窗口与墙上斧影、左侧爵士夜景、金色音符光点；主标题「放爵士的家，斧头不会落下」。

## 事实边界

- 1918 年 5 月起，新奥尔良的意大利裔杂货商家中接连发生夜袭；通行叙述把第一案定在 1918 年 5 月 22/23 日，
  遇害者为杂货商 Joseph 与 Catherine Maggio。凶手从后门进入，多以凿子撬开/凿开木门板，凶器常为主人家自己的斧头。
- 1919 年 3 月 10 日，密西西比河对岸格雷特纳的 Cortimiglia 一家遇袭：父母重伤，两岁女儿 Mary 死亡。
  片中只用空镜、摇篮、皮球与灯影暗示，不出现孩子与遗体。
- 邻居 Iorlando Jordano 与其子 Frank 因 Rosie Cortimiglia 的证词被定罪，她后来翻供，两人获释；案件至今未破。
- 1919 年 3 月 13 日署名「来自地狱」的信由《Times-Picayune》在 3 月 16 日（周日）刊登，指定「下周二午夜 12:15」
  经过新奥尔良，并称家中有爵士乐队演奏的人会被放过。**信件真伪至今没有定论**，片中按「当时的报纸说法」处理。
- 1919 年 3 月 18 日夜（圣约瑟夫节前夜，即信中那个周二的午夜 12:15），新奥尔良的舞厅、酒吧与大量家庭整夜演奏爵士乐；
  通行叙述称那一夜无人遇害。
- 作曲家 Joseph Davilla 与《The Mysterious Axeman's Jazz》有关；有说法认为该曲借信件热度发行，甚至怀疑信件是宣传噱头。
  片中只说「连夜写出一首曲子」，不把写信与作曲写成同一人。
- 1919 年 10 月 27 日，杂货商 Mike Pepitone 在卧室遇害，遗孀 Esther 称看见一个男人逃出屋子；这是最后一起被广泛接受的袭击。
- 「Esther 在洛杉矶开枪打死名叫 Mumfre 的男人」属于长期流传的传闻，研究者未找到该人的确凿记录；
  片中明确标注为传闻，并让「找不到他」成为结尾悬念。

### 来源

- Ghost City Tours：斧头杀手信件全文（Hell, March 13, 1919） — https://ghostcitytours.com/new-orleans/ghost-stories/axeman-new-orleans/
- Country Roads Magazine：The Axeman of New Orleans（信件刊登日期与那一夜） — https://countryroadsmagazine.com/art-and-culture/history/the-axeman-new-orleans/
- All That's Interesting：The Axeman Of New Orleans — https://allthatsinteresting.com/axeman-of-new-orleans
- Crime Library：From Hell — The Axeman of New Orleans — https://crimelibrary.org/serial_killers/weird/axeman/7.html
- Sinister Crimes：Axeman of New Orleans（1918–1919）时间线 — https://sinistercrimes.com/axeman-of-new-orleans/
- Wikipedia：Axeman of New Orleans — https://en.wikipedia.org/wiki/Axeman_of_New_Orleans

## 文件地图

| 路径 | 内容 |
|---|---|
| `build_story.py` / `story.json` | 唯一内容源：双色调 STYLE、NEGATIVE、11 个角色与 seed、30 镜提示词与参考图、30 条旁白、九段结构、事实边界、字幕高亮、音效设计、发布文案 |
| `screenplay.md` | 完整旁白 + 30 镜分镜表（含参考图与色调）+ 来源 + 后期规范 |
| `publish_reference.py` | 校验 24 张定稿图 → 提交 → 写入不可变 `reference/revision.txt` 与 `approvals.json` |
| `generate.py` | Agnes 2.5 Flash 请求（`mode=reference`）、61 秒节流、断点续跑、接触表、`--validate` / `--clips-only` / `--render-only` |
| `render.py` | 30 镜拼接、双色调调色、逐镜字幕、片尾卡、封面、技术报告 |
| `build_audio.py` | 逐镜旁白铺时间轴、算字幕窗口、程序合成爵士乐与恐惧线配乐 + 音效、混音与实测报告 |
| `qc.py` / `narration_fit.py` | 成片质检（容器/冻结/黑帧/闪烁/电平/静音/字幕/封面）与解说词等长实测 |
| `reference/` | 24 张定稿参考图 + `revision.txt` + `approvals.json` |
| `audio/` | `manifest.json` + `S01–S30.mp3`（一镜一句，含 sha256 / target_start / target_duration） |
| `qa/` / `results.json` | 逐镜接触表、QC 摘要与生成收据 |
| `workflows/neworleans1919-gen.yml` | 工作流副本（仓库根同名文件才是真正生效的那份） |
| `抖音脚本.md` / `抖音发布文案.md` | 发布用分镜表、声音设计与文案 |

## 校验记录（最终版）

- 成片：`交付/NewOrleans1919_Final.mp4` · 1920×1080 · 24 fps · 180.000 s · 4320 帧 · h264 High + AAC 48 kHz 立体声 · 72.2 MB
- 全片解码零错误；硬闸门（尺寸/帧率/时长/黑帧/冻结/闪烁/电平/末秒静音/字幕/封面）全部通过
- 旁白 30 句与镜头一一等长：最大加速 1.23×（S10），无减速、无截断
- 三段标志句（「斧头不会落下」「没有人遇害」「你放哪首歌」）后各留约 0.5 s 静默，实测只剩余音
- 双色调段落响度：恐惧段 −22.3 dBFS，爵士段 −20.9 dBFS（音乐轨增益 0.27 vs 0.47，差约 4.9 dB）
- 末尾 174–179 s 为片尾页：标题 + 「真实案件改编 · 部分画面为3D复原 · 传闻细节未经证实」；179 s 后静音
- 全片右上角常驻合规角标「AI动画情景复原 · 非真实影像」
- 字幕 30 条与旁白逐字一致，无重叠、无越界；底部安全边距 72 px，关键词金色放大
