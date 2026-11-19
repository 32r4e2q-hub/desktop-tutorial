# 后车有镜 · 生成循环事故复盘（2026-11-19 · 上海冰柜藏尸案）

> 定位：这不是项目 README，也不替代逐镜 QC。它把 2026-11-19 一整天的「看起来在疯狂烧配额、实则无效/重复/缺闸」复盘成可执行的规则。
> 适用：所有走 `generate.py` + Agnes 的片子（本片即样板）。**先读本文，再动 GEN_REQUEST。**

## 一、事故链（三个互相叠加的事实）

1. **story.json 手改被 CI 静默覆盖（no-op 重做）**：0ad8e57 手改了 story.json（六镜合规重写+换种子）但没同步 `build_story.py` 的 `ROWS`。CI 每次先跑 `build_story.py`，按旧 ROWS 重生成 story.json → 合规重写整体消失 → `request_hash` 不变 → 六镜全部 `reused_existing_asset=true`。run `44482909764` 看起来「跑了、提交了、失败了」，实际一次新画面都没生成；接触表与旧破稿完全一致（S03/S25 冰柜内人体+血迹原样复用）。
2. **create 重试无上限（429 风暴）**：`retry_create_until_accepted` 是**无界**的，受 300 分钟 job timeout 兜底。本片 S16 首轮被打到 attempts=19 才出片；二轮 S16/S19/S25/S27/S28 每个首次 create 都撞 429（「provider busy; retrying」），靠重试风暴挤过去。这就是用户看到的「一直在烧额度、像死循环」。
3. **「completed」不等于合规**：Agnes 对「全部虚化不可读」这类约束两轮稳定画出可读字符（S19 一轮数字/日期字；S27 两轮行式伪文字）。机检（解码/冻结/曝光）永远不会拦住这个——只能靠人看接触表。

## 二、本次已落地的机制（不再靠记忆）

| 机制 | 位置 | 作用 |
|---|---|---|
| `build_story.py` 是唯一事实源；`story.json`/`screenplay.md`/`抖音脚本.md` 是**生成物** | 仓库约定 | 任何剧情/种子/提示词变更只能改生成器 |
| `preflight.py` 新增「生成物与 build_story.py 输出一致性」硬闸 | `preflight.py:generated_sources_consistency()` | CI 在 preflight 阶段就拒绝「手改后未重新生成」的分支，**不再进入 Agnes 队列** |
| `SEED_OVERRIDES` + 对象级正向白名单提示词 | `build_story.py` | S03/S16/S19/S25/S27/S28 六镜重做；二轮 S19/S27 改「完全空白纸页/整面失焦白纸」 |
| 重做证据三件套 | `results.json` | `request_hash` 变化 + `reused_existing_asset=false` + **新 sha256/video_id**；缺一即视为没真重做 |
| 合规签核闸门 | `visual_review_required=true` | 渲染前必须人工（或代检）看新接触表；自动解码通过 ≠ 画面合规 |
| `VISUAL_REVIEW_ROUND2_2026-11-19.md` | qa/ | 每镜证据、用户裁定（S27 接受）、未检项如实清单 |

## 三、以后不再犯的操作规范

1. 改 prompt/种子/时长/金句 → 改 `build_story.py` → `python3 build_story.py` → **三件生成物一起提交**。禁止手改 story.json。
2. CI 出片前看 `prepare_prompt_changes` 的日志行：`queued prompt-refresh shots: …` 必须包含期待的镜头；若显示无变更，**立刻停手**，查生成器与提交的生成物是否一致，不要让 Agnes 跑 no-op。
3. 任何「重做」必须核对 results.json 的 sha256/video_id 确实变化；`reused_existing_asset=true` 出现在「本想重做」的 run 里 = 立即止损，不看片。
4. 接触表/QC 全绿后，**仍需逐帧人工看**（AI 伪文字、遗体、未打码全靠它兜底）；不通过=不渲染。
5. 单镜/少量镜头重做优先于 30 镜全量；S16 这类「内容审核高敏」镜头直接用对象级正向白名单（「完全空白/失焦/仅几何块」），别在提示词里留「数字/文字/人脸」等会触发模型画字的名词。
6. 429 属供应商容量问题：观察 3–5 分钟无新检查点不是死循环；但若 create 已重试 >10 次且全 429，应降低并发（workers=1）并改在低谷时段，而不是继续硬推。
7. 交付物 sha256 要进报告（`交付/*` 与 `results.json:delivery`）；封面/字幕复用旧版时要明确写「字节一致+内容说明」。

## 四、仍然悬着的风险（不自欺）

- Agnes create 重试仍是**无界**策略（仓库刻意，timeout 兜底）；本文档只把它显性化，没有改成有界。改动它需要主创明确裁决。
- 本机沙箱下载 CI artifact 持续 EOF；逐镜「完整播放」签核必须在真实机器上由主创完成。
- AI 伪文字零可读 ≠ 平台审核零风险；S27 纸面行式纹理经主创裁定接受，若平台按最严字面要求「完全无纹理」则必须再议。

## 补充 · 2026-11-19 渲染重试事故（run 44510238238）

- 现象：重推渲染（mode=render，不生成新资产）7 分钟失败，**失败现场日志从未落盘**：工作流失败处理器（`.github/workflows/shanghai-freezer-case.yml`）裸 `git push` 无 rebase 重试，且被触发渲染后我又并行推送了 AGENTS.md（cd79354），远端推进→非快进→push 被拒；`set +e` 吞错→`git diff --cached --quiet` 早已提交 or 提交未推→无任何诊断提交。Actions artifact 下载同样 EOF，故根因靠推断：**最可能是 restore_sources 从 Agnes  receipts 重下 30 镜时网络/平台抖动**（工作流在 5 分钟时仍处于下载校验阶段；编码本身需约 50 分钟），或被并行本地 push 间接拖垮的推送——确切行号未知，**如实留白**。
- 修复：失败处理器 push 改为 `HEAD:refs/heads/arena/...` 且带 `pull --rebase` 三次重试；第三次仍失败则把日志尾部 120 行写进 Step Summary（artifact 全废也有线索）。
- 铁律（以后不要再犯）：**触发渲染后，在 run 结束前不再向该分支做任何本地 push**；所有本地提交先做完、push 完，最后一个 push 才触发渲染。CI 内凡是手写的 `git push` 一律三件套（`HEAD:refs/heads/...` + rebase 重试 + 摘要兜底）。
- 验证缺口：本仓库沙箱下载 Actions artifact/日志持续 EOF（Azure blob 截断），CI 失败取证依赖「失败处理器自提交日志」或 Step Summary——这就是为什么这个闸门不能省。
