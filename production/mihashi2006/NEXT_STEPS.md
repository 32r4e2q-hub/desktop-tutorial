# 交接：还差什么才能出片（2026-11-25）

当前进度：脚本、事实核查、10/13 张参考图、S01–S10 旁白已完成；S11–S30 旁白与 S08/S09/S10 参考图未做。

## 1. 参考图还差三张（生图每回合上限 10 张，本回合用完）

`reference/S08.png`（地下车库坡道与手推车）、`S09.png`（重新粉刷的空房间与倒放衣柜）、`S10.png`（东京地裁石阶外景）。
生成后必须：写 `approvals.json` 条目（`status=approved` + sha256 + dimensions）→ 提交 → 把该提交 hash 写进
`reference/revision.txt` → 重跑 `build_story.py` 与 `preflight.py`（现在 preflight 报 `pending references S10` 就是因为缺这三张）。

## 2. 旁白还差二十条（TTS 每回合上限 10 条）

`audio/S11.mp3` … `audio/S30.mp3`，逐字用 `story.json` 的 `shots[].narration`，音色 `voice-01`
（`audio/voice.json` 已登记）。做完跑：

```bash
python3 production/mihashi2006/build_audio_manifest.py
python3 production/mihashi2006/narration_fit.py     # 逐镜比对时长，超 1.55 倍就重写那句
python3 production/mihashi2006/preflight.py
python3 production/mihashi2006/generate.py --validate --clips-only
```

## 3. 生成 30 镜与出片

```bash
printf '{"mode":"clips","workers":2}\n' > production/mihashi2006/GEN_REQUEST   # 提交并 push
# 30 镜全部 completed 后
printf '{"mode":"render"}\n' > production/mihashi2006/GEN_REQUEST
```

工作流已装到 `.github/workflows/mihashi2006*.yml`；成片落 `交付/东京街头分尸案_三桥歌织的四小时电梯_三分钟_带声音.mp4`。

## 4. 出片后

- `verify_master.py --film ... --story ... --srt ...` 必须 PASS；`volumedetect` 记进 QA（目标均值≈-14 dB、峰值 -3～-6 dB；
  `render.py` 已加 10 dB 增益 + limiter）。
- 抽帧看画面：13 张参考图与成片都必须是**照片级写实**；出现动画/插画质感就单镜重做。
- 第 29 期封面：`python3 production/mystery-cover-template/generate_cover.py --episode 29 ...`
- 发布文案已在 `抖音发布文案.md`（生成物），交付时另存一份到 `交付/`。
