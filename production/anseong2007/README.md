# 第九期《安城双尸案：144天，一台发动机》

三分钟横屏 · 1920×1080 · 24 fps · 180 s · 30 镜 · Agnes Video 2.5 Flash（reference 模式，720P 源片放大 1080P）。
模板：`hakamada58`（30 镜 + C/S/P 参考图定稿包）+ main 的世田谷模式手册（一镜一句、解说与片段等长）。

## 进度

| 步骤 | 状态 |
|---|---|
| 事实核查 | ✅ 5 条公开报道（见 `screenplay.md` 事实边界）；S24 改为“埃及买家自拍编号发回”，刑警未赴埃及 |
| 分镜 / 提示词 | ✅ `build_story.py` → `story.json` / `screenplay.md`（STYLE → <Picture N> → 角色锚点原文 → 画面 → NEGATIVE） |
| 参考图 | 🟡 已审 8/27（C01–C06、C08、S01）；其余按平台单轮 10 张上限分批生成 |
| 生成器 | ✅ `generate_clips.py`：一次性排队 30 镜，创建 ≤5 次/分钟（12.1 s 间隔），单线程全局轮询（≤15 次/分钟、429 整体退避），断点续跑；`test_anseong2007.py` 离线仿真 429 / 队列满 / 任务失败自动重建 |
| 视频片段 | ⏳ 参考图全部审定后写 `GEN_REQUEST` 触发 `.github/workflows/anseong2007-gen.yml` |
| 旁白 / 字幕 / 音效 / 合成 | ⏳ 生成期间并行制作 |

## 命令

```bash
python3 production/anseong2007/build_story.py
python3 production/anseong2007/generate_clips.py --validate
python3 -m pytest -q production/tests/test_anseong2007.py
# 触发（只在固定分支 Actions 上真实调用 Agnes）：
echo '{"mode":"full"}' > production/anseong2007/GEN_REQUEST   # 全部 30 镜
echo '{"only":"S12","force":"S12"}' > production/anseong2007/GEN_REQUEST   # 单镜重做
```

参考图 URL 固定到 `reference/revision.txt` 记录的不可变 commit；生成器在触碰密钥前核对每张图的 SHA-256 与审核状态。
