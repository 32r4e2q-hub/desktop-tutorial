# 迷案解码人 · 案件解说短片生产仓

真实案件 180 秒中文解说短片（抖音横版 · 1920×1080 · 24 fps）。
现阶段仓库里关于案件只有一部：**上海「冰柜藏尸案」**（第二十期）。
此前的全部旧案件工程、旧成片、旧工作流已删除（主创 2026-11-21 授权）；
git 历史仍含旧案二进制（瘦身需 filter-repo/BFG + 强推，未经主创明示不会执行）。

- 制作总约定：[`AGENTS.md`](AGENTS.md)
- **从一个题目到一条成片：[`新题目开工手册.md`](新题目开工手册.md)**
- 当前唯一上架内容与交付物见下文。

## 当前成片（第二十期 · 上海冰柜藏尸案）

> 2026-11-19 换声重渲（run 44906491612）；母版 `7ee0d60d…`（sha256 `7ee0d60d04e0f6c1cbf2257936668eca9adcb9de38139e4d44793e102c447652`）

| 项 | 内容 |
|---|---|
| 影片 | [`交付/上海冰柜藏尸案_105天_三分钟_带声音.mp4`](交付/上海冰柜藏尸案_105天_三分钟_带声音.mp4)（59,550,078 B · 1920×1080 · 24 fps · 180.000 s · 4320 帧） |
| 封面 / 字幕 / 技术报告 | [`上海冰柜藏尸案_Cover.jpg`](交付/上海冰柜藏尸案_Cover.jpg) · [`上海冰柜藏尸案_Subtitles.srt`](交付/上海冰柜藏尸案_Subtitles.srt) · [`上海冰柜藏尸案_Technical_Report.json`](交付/上海冰柜藏尸案_Technical_Report.json) |
| 系列封面 | [`第二十期_上海冰柜藏尸案_系列封面.png`](交付/第二十期_上海冰柜藏尸案_系列封面.png)（+ 同名 JSON 记录期数/标题/截图来源） |
| 发布文案 | [`交付/第二十期_上海冰柜藏尸案_抖音发布文案.md`](交付/第二十期_上海冰柜藏尸案_抖音发布文案.md) |
| 旁白 | voice-01 低沉男声（30 条，一镜一句；**未经主创完整听检**；S14 近静音已重试，peak 0.773） |
| 事实核查 | [`production/shanghai_freezer_case/FACT_CHECK.md`](production/shanghai_freezer_case/FACT_CHECK.md) — **未联网实时复核**，媒体口径"105天"全片统一 |
| 流水线 | [`production/shanghai_freezer_case/`](production/shanghai_freezer_case/)（唯一参考实现，也是一条将在下期复制它的生产线） |

> 成片 commit 在当前分支（`arena/f9f847e0-desktop-tutorial`）上，对应 **PR #55（换声；状态以 GitHub 为准，本次未合并 main）**。
> 发布到抖音由主创手动；Agent 不代发。
> 交付前待主创完成：完整听检（voice-01）+ 抽帧复核（伪文字/崩脸/未打码）——**自动 QC ≠ 人工签收**。

## 下一个题目怎么来

```bash
python3 production/new_topic.py --slug <kebab-case> --title "片名" --branch <当前分支>
```

会生成 `production/<slug>/`（引擎 + 渲染/写作模板 + 机械正确的 30×6 s story.json 骨架 +
工作流三件套），随后按 [`新题目开工手册.md`](新题目开工手册.md) 填空 → 事实核查 → 参考图 →
配音 → `--validate` → 触发出片 → 三道 QC 闸门 → 封面/文案 → 主创发布。

## 仓库结构

```
production/
├── shanghai_freezer_case/    # 第二十期工程（唯一保留的案件工程；new_topic.py 的参考实现）
├── templates/                # 出片渲染/写作/工作流模板（render.py / build_story.py / *.workflow.yml）
├── new_topic.py              # 新题目脚手架（复制参考工程 → 新项目；--branch 默认当前分支）
├── mystery-cover-template/   # 「迷案解码人」系列竖版封面工具（1080×1440）
├── gwangju_style.py          # 共享画面文字层（字幕/金色注释/钩子大字；所有新片默认）
├── agnes_video.py            # Agnes 2.5 Flash 客户端共享引擎
├── verify_master.py          # 成片硬校验（退出码非 0 不许交付）
├── preflight.py              # 生成物一致性闸门（BLOCKED = 先跑 build_story.py）
├── review_film.py            # 成片接触表/抽帧复核辅助（人工复核用）
├── verbatim_check.py         # ASR 听检（faster-whisper；报告 commit 回分支）
└── tests/                    # 流水线闸门测试（pytest，CI: .github/workflows/ci-tests.yml）
.github/workflows/            # ci-tests、shanghai-freezer-case（出片）、verbatim-check、cleanup-artifacts、release-upload
交付/                         # 第二十期成片 + 字幕 + 封面 + 发布文案
```

## 自检

```bash
python3 -m pytest production/tests -q      # 全绿才继续；含模板渲染与参考工程哈希哨兵
python3 production/shanghai_freezer_case/generate.py --validate
```

## 红线（摘要）

1. `story.json` 等是 `build_story.py` **生成物**，禁手改；生成器与三件产物一起提交。
2. `--validate` / `verify_master.py` 非 0 不许出片/不许交付；不许绕过闸门。
3. 生成额度宝贵：先全绿再 push `GEN_REQUEST`；重摇必须核对 `results.json` 的 `reused_existing_asset` 与 sha256/video_id。
4. FACT_CHECK 未联网复核就如实写"未复核"；不得编造判决/日期/数字。
5. voice-01 未经主创完整听检；Douyin 不代发；自动 QC 结果 ≠ 人工签收。
6. 默认画面文字层 = 光州胶带案风格（`gwangju_style.py`）：解说词字幕 + 金色注释 + 钩子大字，全片常驻「AI动画情景重现 · 非真实影像」。
