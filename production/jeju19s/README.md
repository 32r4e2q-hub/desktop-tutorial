# 济州岛敞篷车命案：19秒

本项目是单独案件目录，沿用仓库 `production/gwangju_tape_case/` 的 Agnes Video 2.5 Flash
生成、字幕、音画校验与断点续跑工具链；没有复用旧案件脚本、人物、参考图或输出。
目标规格：抖音横屏 16:9、1920×1080、24fps、180 秒、30 个连续运动的写实 3D 动画镜头；不加 BGM。

## 当前真实状态（2026-11-17 UTC，开工）

- 内容源 `build_story.py` 已定稿：30 镜 / 180 秒 / 617 字解说 / H1–H9 钩子 / 10 条金色注释。
- 事实核查：`FACT_CHECK.md`（韩媒法庭报道×7 + 中文报道×2 + 请愿/节目整理交叉）。
- 参考图：33 张（C×8、S×17、P×8）生成中，逐张目视检查后登记 `reference/approvals.json`。
- 出片分支：`arena/5375d891-desktop-tutorial`；成片名：`济州岛敞篷车命案_19秒_三分钟_带声音.mp4`。

## 内容红线与核实口径

- 终审：杀人罪不成立，危险驾驶致死判 4 年。全片用“检方称/家属认为/法院认为”，不下结论。
- 事故只用声波图、黑场、路缘与石墙空镜、事后现场表现；不出现撞击瞬间、遗体、血腥、伤口。
- 赵恩爱与家人为中文报道中的称呼，韩媒匿名；崔某为媒体假名；所有人物均为虚构演员式形象。
- 车辆颜色（红）、年龄（29岁）、手机录音载体、密码情节的口径保留见 `FACT_CHECK.md` 第二节。

## 顺序（不可提前生成视频）

1. 完成 C、S、P 全套参考图；每张单独读回检查，失败或不符合设计则重生成，编号不变，
   最终文件和 SHA-256 写入 `reference/approvals.json`。
2. 所有参考图通过后，把参考图与审批清单固定到 GitHub 上的不可变 commit，
   `reference/revision.txt` 写该 40 位 commit。随后运行 `build_story.py`、
   `generate.py --validate --clips-only`。
3. 一次为 30 镜排队 Agnes Video 2.5 Flash reference 片段；请求共享闸门每 12.1 秒至少一次
   （不超过 5 次/分钟，月卡额度），最多 2 个 worker。每条提示词由工具自动按
   STYLE → 逐字角色锚点 → 单镜描述 → NEGATIVE 组成。
4. 下载并逐镜检查运动、人物一致性、无伪文字和安全要求；失败镜头单独重生成。
   视频必须是真实连续运动，不能以静帧加推拉替代。
5. 使用用户选定的悬疑低沉普通话男声；逐镜合成旁白、同步字幕和脚本音效，不加 BGM；
   输出后运行 `qc.py`、`narration_fit.py` 与仓库通用 `production/verify_master.py`，
   再人工逐镜/全片视听复核。

## 目录与工具

| 路径 | 用途 |
|---|---|
| `build_story.py` | 本案唯一内容源：STYLE、NEGATIVE、人物锚点、30 镜脚本、H1–H9、解释字幕、来源和发布信息。 |
| `story.json`、`screenplay.md`、`抖音脚本.md`、`抖音发布文案.md` | 由 `build_story.py` 生成；改内容应改源脚本后重建。 |
| `reference/REFERENCE_PACK.md` | C/S/P 参考图定义、画面提示词与逐张状态。 |
| `reference/approvals.json` | 每张参考图的审批状态、路径和 SHA-256；未通过的不能进入 Agnes payload。 |
| `reference/revision.txt` | 待固定：包含全部参考图的不可变资产 commit（40 位）。 |
| `generate.py` / `throttle.py` | Agnes Video 2.5 Flash reference 模式、队列状态、断点续跑、12.1 秒 POST/GET 共享请求闸门。 |
| `render.py` | 逐镜画面、旁白与脚本 SFX 混音，合成 H1–H9 大字钩子、金色解释字卡、同步字幕、片尾标题；封面取自成片真实帧并后期加字。 |
| `build_sfx.py` | 按镜头脚本生成确定性的轻量拟音/环境声；无旋律、无 BGM，并生成时长和哈希清单。 |
| `preflight.py` | 离线核对 30 镜时序、参考图审批/哈希、每镜 1–5 张引用与 revision；缺项即阻断，不调用 Agnes。 |
| `qc.py` / `narration_fit.py` | 生成片段、时长、分辨率、音频和旁白适配校验；自动通过不等于人工签收。 |
| `.github/workflows/jeju19s.yml` | 监听本分支的 `GEN_REQUEST` / `CANCEL_REQUEST`；`mode=clips` 生成 30 镜，复核后 `mode=render` 出片。 |
| `audio/voice.json` | 声线描述、已选 TTS 声线与逐镜生成状态。 |
| `results.json` | 任务状态与 provenance（生成阶段由工作流写回）。 |
| `qa/` | 接触表与 QC 报告（生成/出片阶段由工作流写回）。 |

## 本地只读检查

```bash
python3 production/jeju19s/build_story.py
python3 -m py_compile production/jeju19s/*.py
python3 production/jeju19s/preflight.py
python3 production/jeju19s/generate.py --validate --clips-only
```

参考图/引用/提示词边界仍由 preflight.py 与 generate.py --validate 守门。
参考图、审批哈希和 revision 完整前，`preflight.py` 与最后一条命令预期阻断；
不应通过复用其他案件资产绕过检查。
