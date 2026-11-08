# 第九期《安城双尸案：144天，一台发动机》

三分钟横屏 · 1920×1080 · 24 fps · 180 s · 30 镜 · Agnes Video 2.5 Flash（reference 模式，720P 源片放大 1080P）。
模板：`hakamada58`（30 镜 + C/S/P 参考图定稿包）+ main 的世田谷模式手册（一镜一句、解说与片段等长）。

## 进度

| 步骤 | 状态 |
|---|---|
| 事实核查 | ✅ 5 条公开报道（见 `screenplay.md` 事实边界）；S24 改为“埃及买家自拍编号发回”，刑警未赴埃及 |
| 分镜 / 提示词 | ✅ `build_story.py` → `story.json` / `screenplay.md`（STYLE → <Picture N> → 角色锚点原文 → 画面 → NEGATIVE） |
| 参考图 | ✅ 27/27 逐张审定（C05/C07 重生成去名人相似脸）；固定在 commit `3b6de10`（`reference/revision.txt`） |
| 生成器 | ✅ `generate_clips.py`：一次性排队 30 镜，创建 ≤5 次/分钟，单线程全局轮询，断点续跑；已修复 PyAV 18 下 `inspect_clip` 关闭容器后读属性的 bug（首轮 16 镜因此停在 `download_pending`，续跑会重新轮询并下载，不重复创建） |
| 视频片段 | 🟡 首轮 run 42457809910 运行中：16 镜 Agnes 已完成；Agnes 当日额度用尽后限速为每 5 分钟 1 次创建，生成器按 Retry-After 继续排队 |
| 旁白 | 🟡 voice-01（低沉男声）已录 S01–S09；S10 改稿待重录；S11–S30 待录（每轮最多 10 条）；`audio/voice/recorded.json` 记录每个 mp3 的实际朗读文本，改稿自动作废旧录音 |
| 合成 | ✅ `render.py` + `.github/workflows/anseong2007-render.yml`；本地 30 段合成源片全流程验证：4320 帧 / 180.000 s / 尾秒静音 |
| 封面 / 发布标题 | ⏳ 需本期成片真实帧（AGENTS.md） |

## 命令

```bash
python3 production/anseong2007/build_story.py
python3 production/anseong2007/generate_clips.py --validate
python3 -m pytest -q production/tests/test_anseong2007.py
# 触发（只在固定分支 Actions 上真实调用 Agnes）：
echo '{"mode":"full"}' > production/anseong2007/GEN_REQUEST   # 全部 30 镜
echo '{"only":"S12","force":"S12"}' > production/anseong2007/GEN_REQUEST   # 单镜重做
python3 production/anseong2007/render.py --plan-only                 # 配音窗口（只加速 ≤1.15×）
# 渲染（Actions）：RENDER_REQUEST = {"clips_run_id": "<gen run id>", "clips_artifact": "anseong2007-clips-<gen run id>", "publish": true}
```

参考图 URL 固定到 `reference/revision.txt` 记录的不可变 commit；生成器在触碰密钥前核对每张图的 SHA-256 与审核状态。
