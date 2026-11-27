# 交接：还差什么才能出片（2026-11-27 更新）

进度：事实核查、30 镜脚本、去 AI 味预检、14 张参考图、**30 镜视频素材全部生成完毕**、S01–S20 旁白已完成。
**卡在最后一件事：S21–S30 十条旁白还没做**（本回合 TTS 配额在 S11–S20 那批用完了，连续两回合都是这个限制）。

## 下一回合要做的第一件事

用 `voice-01` 逐条合成 `audio/S21.mp3` … `audio/S30.mp3`，文本严格照 `story.json` 的 `shots[].narration`：

| 镜号 | 旁白 |
|---|---|
| S21 | 她说，十二月十二日早上，他喝醉了回家。 |
| S22 | 她提出离婚，他把离婚申请书撕了。 |
| S23 | 律师说，她长期被家暴，患上了创伤后应激障碍。 |
| S24 | 二零零五年六月，她的鼻骨被打断，进过庇护所。 |
| S25 | 辩方主张她当时心神丧失，应当无罪。 |
| S26 | 二零零八年四月二十八日，东京地裁给出结论。 |
| S27 | 幻视幻听存在，但没有影响到责任能力。 |
| S28 | 求刑二十年，判了十五年。 |
| S29 | 二零一零年六月，东京高裁驳回上诉，辩方放弃上告，十五年就此确定。 |
| S30 | 从报案到刑期确定，隔了三年半；那四个小时，监控记得清清楚楚。 |

然后：

```bash
.venv/bin/python production/mihashi2006/build_audio_manifest.py   # 本地无 ffprobe，已加 imageio-ffmpeg 兜底
.venv/bin/python production/mihashi2006/narration_fit.py
python3 production/mihashi2006/preflight.py
python3 production/mihashi2006/generate.py --validate --clips-only
printf '{"mode":"render"}\n' > production/mihashi2006/GEN_REQUEST      # 提交并 push 出片
```

## 已经不用再做的

- 参考图 14 张（C01–C03、S01–S11）已全部批准并钉进 `reference/revision.txt`。
- 30 镜素材已全部 `completed`；S18（土上手印）与 S27（纸面伪文字）已单镜重做，`reused_existing_asset=false`。
- 工作流已装到 `.github/workflows/mihashi2006*.yml`。

## 出片后

- `verify_master.py --film ... --story ... --srt ...` 必须 PASS；`volumedetect` 记进 QA（目标均值≈-14 dB、峰值 -3～-6 dB，`render.py` 已加 10 dB 增益 + limiter）。
- 成片抽帧复核字幕压暗部（S08/S22/S25 偏暗）；第 29 期封面用 `mystery-cover-template/generate_cover.py --episode 29`。
- 发布文案是生成物 `抖音发布文案.md`，交付时另存一份到 `交付/`。
