# 光州胶带案：22米胶带，封住了谁的真相？

本项目是单独案件目录，沿用仓库 `production/missing_groom_89tons/` 的 Agnes Video 2.5 Flash 生成、字幕、音画校验与断点续跑工具链；没有复用旧案件脚本、人物、参考图或输出。目标规格：抖音横屏 16:9、1920×1080、24fps、180 秒、30 个连续运动的写实 3D 动画镜头；不加入 BGM。

## 第 15 期交付入口

- 系列封面：[`交付/第十五期_光州胶带案_系列封面.png`](../../交付/第十五期_光州胶带案_系列封面.png)（同名 JSON 记录取帧/裁剪/事实依据）
- 发布文案：[`交付/第十五期_抖音发布文案.md`](../../交付/第十五期_抖音发布文案.md) / [`抖音发布文案.md`](抖音发布文案.md)
- 制作过程：[`制作过程.md`](制作过程.md)
- 今后默认复用模板：[`模板-如何复用.md`](模板-如何复用.md)
- 共享画面文字层：[`production/gwangju_style.py`](../gwangju_style.py)

## 当前真实状态（2026-11-14 UTC，最终交付）

- 最终母版：`交付/光州胶带案_22米胶带_三分钟_带声音.mp4`，SHA-256 `115df3249e272529085cc66aca268239561ac54f711210a4eac4c4017f106e27`，72,574,275 字节；180.000s / 1920×1080 / 24fps / 4320 帧 / AAC 48kHz 立体声 180.000s / 30 条逐镜字幕。
- 下载：Google Drive 公开只读链接 https://drive.google.com/file/d/1aey4Z3PV4f-th-dsXXkTLnOQ5menihsf/view?usp=drivesdk （直链 https://drive.google.com/uc?export=download&id=1aey4Z3PV4f-th-dsXXkTLnOQ5menihsf ）；仓库内同名文件亦可直接下载。
- `production/verify_master.py` 硬校验 **PASS**（时长/帧数/音轨长度/字幕窗口/字幕-语音同步，最大字幕领先 0.11s）；报告 `qa/verify-master-current.json`。
- 去闪烁：全片 `deflicker=size=61:mode=am,hqdn3d=3:2:9:9,eq=…`；移除了旧版反而制造亮度尖峰的帧级 gamma/blend 修复；S04（黄色十字光束）、S07/S18/S20（伪文字）、S11/S25/S28（闪烁光源/昼夜渐变）源片重生成。逐镜复审见 `qa/flicker-review.md`：旧版 14 镜往复闪烁清零；仅 S09 保留一段单调有动机渐亮（走向门口光源），S11/S14 各有 ≤3.4 的孤立单帧跳变。
- 解说：连贯电影解说式 30 句 / 628 字，10 组连续 TTS 切分为逐镜 shot-locked MP3（`audio/GROUP_TTS_NOTES.md`），最大加速 1.046×；声线 `voice-00` 普通话男声；仅脚本 SFX、无 BGM。
- 抽帧人眼（Agent）复核：`qa/delivery-review/` 6 张接触表覆盖 30 镜 + 片尾标题帧；全 4320 帧灰度审计无近白帧、无冻帧窗口，近黑仅片尾设计内淡出末帧。
- **签收口径：技术 QC 与 Agent 抽帧复核通过；仍需用户完整播放人工复核，本交付不冒充人工签收。**

## 内容红线与核实口径

- 受害者只称“善雅（化名）”。案件相关人员均是虚构演员式设计，仅用角色称谓；嫌疑人不出现真实姓名或可识别真实肖像，凶手只以黑影、剪影或手部呈现。
- 画面不出现遗体、血迹、伤口、绑缚、窒息过程、性相关细节或施害过程。现场仅以书包、便当盒、黄色胶带、证物袋、门缝光和空房间克制暗示。
- 事实与法律口径见 `FACT_CHECK.md`。2024 年 SBS 节目播出时尚未找到与 Y 染色体线索相符者；本轮截至 2026-11-14 未查到更晚的可信公开进展，但这不证明之后没有进展。
- 两名公开报道中的重点对象有不在场证明，不表述为“所有熟人都已逐一排除”。2016 年旧证物复检、2024 年节目公开；姓氏范围是线索，不是身份确认。
- 追诉时效只表述为：2015 年修法取消适用死刑的杀人罪（排除从犯）的公诉时效，并适用于修法时尚未届满的旧案；不说所有杀人案无条件适用。

## 顺序（不可提前生成视频）

1. 完成 C、S、P 全套参考图；每张单独读回检查，失败或不符合设计则重生成，编号不变，最终文件和 SHA-256 写入 `reference/approvals.json`。
2. 所有参考图通过后，把参考图与审批清单固定到 GitHub 上的不可变 commit，`reference/revision.txt` 写该 40 位 commit。随后运行 `build_story.py`、`generate.py --validate --clips-only`。
3. 一次只为 30 镜排队 Agnes Video 2.5 Flash reference 片段；请求共享闸门每 12.1 秒至少一次（不超过 5 次/分钟），最多 2 个 worker。每条提示词由工具自动按 STYLE → 逐字角色锚点 → 单镜描述 → NEGATIVE 组成。
4. 下载并逐镜检查运动、人物一致性、无伪文字和安全要求；失败镜头单独重生成。视频必须是真实连续运动，不能以静帧加推拉替代。
5. 使用已选的低沉克制普通话男声 `voice-00`；逐镜合成旁白、同步字幕和脚本音效，不加 BGM；输出后运行 `qc.py`、`narration_fit.py` 与仓库通用 `production/verify_master.py`，再人工逐镜/全片视听复核。

## 目录与工具

| 路径 | 用途 |
|---|---|
| `build_story.py` | 本案唯一内容源：STYLE、NEGATIVE、人物锚点、30 镜脚本、H1–H9、解释字幕、来源和发布信息。 |
| `story.json`、`screenplay.md`、`抖音脚本.md`、`抖音发布文案.md` | 由 `build_story.py` 生成；改内容应改源脚本后重建。 |
| `reference/REFERENCE_PACK.md` | C/S/P 参考图定义、画面提示词与逐张状态。 |
| `reference/approvals.json` | 每张参考图的审批状态、路径和 SHA-256；未通过的不能进入 Agnes payload。 |
| `reference/revision.txt` | 固定到包含全部参考图的不可变资产 commit `5395eb5cc0574eb75622acb9e51da43e5f24b9e0`。 |
| `generate.py` / `throttle.py` | Agnes Video 2.5 Flash reference 模式、队列状态、断点续跑、12.1 秒 POST/GET 共享请求闸门。 |
| `render.py` | 逐镜画面、旁白与脚本 SFX 混音，合成 H1–H9 大字钩子、金色解释字卡、同步字幕、片尾标题；封面取自成片真实帧并后期加字。 |
| `build_sfx.py` | 按镜头脚本生成确定性的轻量拟音/环境声；无旋律、无 BGM，并生成时长和哈希清单。 |
| `preflight.py` | 离线核对 30 镜时序、参考图审批/哈希、每镜 1–5 张引用与 revision；缺项即阻断，不调用 Agnes。 |
| `qc.py` / `narration_fit.py` | 生成片段、时长、分辨率、音频和旁白适配校验；自动通过不等于人工签收。 |
| `.github/workflows/gwangju-tape-case.yml` | 监听本续作分支的 `GEN_REQUEST` / `CANCEL_REQUEST`；先重生成 S07/S18/S20，复核后改为 `mode=render` 出最终母版。 |
| `audio/voice.json` | 声线描述、已选 TTS 声线与逐镜生成状态。 |
| `results.json` | 任务状态与 provenance；30/30 全部 completed，阶段为 `first_cut_ready`，已登记母版与 sidecar 哈希；视听签收仍待人工完成。 |
| `qa/qc-report.json` / `qa/qc-summary.md` | 自动技术 QC 与源片抽样报告；技术通过，但明确保留视觉复核待办及采样限制。 |

## 本地只读检查

```bash
python3 production/gwangju_tape_case/build_story.py
python3 -m py_compile production/gwangju_tape_case/*.py
python3 -m pytest production/tests/test_gwangju_style.py production/tests/test_new_topic.py -q
python3 production/gwangju_tape_case/preflight.py
python3 production/gwangju_tape_case/generate.py --validate --clips-only
```

测试覆盖默认画面文字层（Caption/Hook/Explainer）、脚手架复制 gwangju_style.py、本案 30 镜/180 秒与发布文案字段；参考图/引用/提示词边界仍由 preflight.py 与 generate.py --validate 守门。参考图、审批哈希和 revision 完整前，`preflight.py` 与最后一条命令预期阻断；不应通过复用其他案件资产绕过检查。
