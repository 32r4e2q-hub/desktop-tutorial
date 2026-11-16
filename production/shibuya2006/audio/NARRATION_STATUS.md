# 第17期旁白：哪一句真的有声音（2026-11-16 复核）

## 结论先说

30 镜里 **27 镜已有可用的源语音，S10、S11、S12 三句没有任何音频**。上一轮「旁白独立转写核验」失败的原因**不是录音坏掉**，而是媒体环境里的 PyAV 与 faster-whisper 版本对不上（见文末）。录音侧的缺口只有一个，且是明确的：G04 那三句被语音服务的内容审核拒绝。

| 镜头 | 源 | 状态 |
|---|---|---|
| S01 S02 S03 | `audio/groups/G01.mp3` 仍是旧稿（父亲驾车送行），已作废 | 逐镜独立音频 `audio/S01..S03.mp3` 可用 |
| S04–S09 | `G02`、`G03` 各含 3 句连续 TTS | 按停顿切成候选，**未对齐签收** |
| S10 S11 S12 | `G04` | **缺失**：服务返回内容审核拒绝，未改词绕过 |
| S13 S14 S15 | `G05` | 候选切分，未对齐签收 |
| S16 S17 S18 | `G06` 旧稿作废 | 逐镜独立音频 `audio/S16..S18.mp3` 可用 |
| S19–S24 | `G07`、`G08` | 候选切分，未对齐签收 |
| S25–S30 | `G09`、`G10` | 候选切分，未对齐签收 |

- 候选切分只存在于被忽略的 `work/shibuya2006/audio_candidates/`，报告在 `qa/group-tts-split-candidates.json`，脚本明确标注 `candidate_only_not_alignment_pass`。
- 成片闸门要的是 **30 个逐镜文件 + `audio/review.json` 的逐条复核（文本/哈希/音色一致）**；现在两者都没有。

## 为什么不能“顺手补三句”

1. Arena 的 `voice_id` 是会话级的。本轮用 `voice-01` 直接合成时被明确拒绝：

   ```
   Failed to generate speech: Unknown voice_id "voice-01"
   ```

   也就是说，上一轮用户选定的那条声线在本轮拿不到；要新声音就得重新试听选定。
2. 现有 27 句是旧声线。把一条**新声线**塞进 S10–S12 会造成同一部片里两种音色，`STATUS.json` 的 `speaker_change_allowed_without_approval` 是 `false`，必须用户点头。
3. G04 是**内容审核**拒绝，不是网络或额度问题。改词让它过审属于绕过审核，手册明令禁止；要动台词就得重新事实核查并让用户确认。

## 三条可选路线（需要用户拍板）

| 方案 | 做法 | 代价 | 风险 |
|---|---|---|---|
| A. 全篇重录 30 句（推荐） | 本轮重新试听选定一条低沉男声，逐镜单独合成 30 条；旧音频仅留 provenance | 10 条/轮，约 3 轮；之后逐条 ASR 复核 | 音色与上一轮不同，但全片统一 |
| B. 只补 S10–S12 | 用新选定音色或用户提供的合规录音补三句 | 快 | 音色可能明显不一致；仍要用户书面认可 |
| C. 用户自己录三句 | 按 `完整旁白_录制与导演提示.md` 的口径录 S10–S12 | 保持原声线 | 真人声与 TTS 音色也可能不统一；需要实际试听 |

若逐句单独合成时 S10–S12 仍被审核拒绝，A 也走不通，那就只剩 C，或者由用户决定是否接受改写后的非直述表述（属于改稿，需重新核查）。

## 上周那次失败到底是什么

`第17期 · 旁白独立转写核验`（run 43816706197）在第一条片段就崩：

```
TypeError: open() got an unexpected keyword argument 'metadata_errors'
```

栈底在 `av.container.core.open`：runner 上解析到的 PyAV 比 faster-whisper 传参要求的旧。修法不是改录音，而是把 PyAV 从音频路径上拿掉——

- `transcribe_audio_candidates.py` 现在用 ffmpeg 解码成 16 kHz 单声道 float32，直接把数组交给模型；
- 工作流钉 `python-version: 3.11` 并安装 `production/requirements.txt`（其中 `av>=12,<19`），不再只装 faster-whisper；
- 失败时把完整栈和 `python/ffmpeg` 版本写进 `qa/narration-asr-error.txt`，成功时删掉旧诊断文件，避免“上次的红”挂在报告里。

离线回归见 `production/tests/test_shibuya2006_audio.py`（解码长度/类型、模型不再吃文件路径、工作流装配与分支口径）。
