# 光州胶带案：22米胶带，封住了谁的真相？

本项目是单独案件目录，沿用仓库 `production/missing_groom_89tons/` 的 Agnes Video 2.5 Flash 生成、字幕、音画校验与断点续跑工具链；没有复用旧案件脚本、人物、参考图或输出。目标规格：抖音横屏 16:9、1920×1080、24fps、180 秒、30 个连续运动的写实 3D 动画镜头；不加入 BGM。

## 当前真实状态（2026-11-14 UTC）

- 内容计划：30 镜、180 秒、9 段解说单元，旁白共 663 字符；`build_story.py` 为唯一内容源。
- C/S/P 共 30 张参考图均已逐张目视检查、登记 SHA-256；不可变资产 revision 为 `5395eb5cc0574eb75622acb9e51da43e5f24b9e0`。
- Agnes 全片素材 run `43544148329` 于 05:06:22 UTC 成功完成；针对视觉偏差的 S04、S26 同批重生成 run `43563547641` 于 06:07:33 UTC 成功结束。`results.json` 已确认 30/30 均为 completed，每镜有任务 ID、SHA-256 与字节数；当前阶段为 `selected_sources_ready`。源 MP4 可由已验证的 Agnes 收据在 Actions runner 上恢复；大体积中间源片不提交进 Git。
- 接触表复核：S04 重生成后只见母亲、没有女儿；S26 已去掉有字样的文件和印章，改为法槌与时钟象征画面（保留普通时钟刻度）。其他镜头仍需随最终成片做完整动态复核。
- 现将 `GEN_REQUEST` 切换为 `mode=render`，触发 render-only：按收据恢复全部 30 镜，生成 180 秒母版、字幕和封面，并运行自动技术 QC。
- 普通话男声 `voice-00` 已由用户试听选定；`audio/` 中 S01–S30 的 MP3、逐镜文稿、时长和 SHA-256 manifest 均已核验，最大需加速 1.4063×（上限 1.55×）。人工旁白听检仍待完成；试听稿为 `work/gwangju_tape_case/narration-review.mp3`。
- 30 条确定性 SFX WAV 已生成，48 kHz 立体声、时长与哈希校验通过；无 BGM。试听稿为 `work/gwangju_tape_case/sfx-review.mp3`，人工听检仍待完成。可重建试听与剪辑中间文件保存在被忽略的 `work/`。
- 当前仍没有字幕文件、封面或 180 秒母版；render-only 运行完成后再更新为真实交付状态。自动技术 QC 通过也不等于最终签收：全片人工听检和逐镜动态画面复核仍需完成。

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
| `.github/workflows/gwangju-tape-case.yml` | 只监听本案当前分支的 `GEN_REQUEST` / `CANCEL_REQUEST`；Agnes 全片与 S04/S26 重生成均成功；当前 `GEN_REQUEST` 为 `mode=render`。 |
| `audio/voice.json` | 声线描述、已选 TTS 声线与逐镜生成状态。 |
| `results.json` | 任务状态与 provenance；30/30 全部 completed，最新素材阶段为 `selected_sources_ready`，渲染后会更新交付信息。 |

## 本地只读检查

```bash
python3 production/gwangju_tape_case/build_story.py
python3 -m py_compile production/gwangju_tape_case/*.py
python3 -m pytest production/tests/test_gwangju_tape_case.py -q
python3 production/gwangju_tape_case/preflight.py
python3 production/gwangju_tape_case/generate.py --validate --clips-only
```

测试覆盖 30 镜/180 秒、角色与引用、提示词边界、Hook/Explainer ASS 字幕及 SFX WAV 时长/哈希。参考图、审批哈希和 revision 完整前，`preflight.py` 与最后一条命令预期阻断；不应通过复用其他案件资产绕过检查。
