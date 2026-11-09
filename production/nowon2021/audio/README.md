# 逐镜配音（尚未生成）

选定的当前会话音色见 `../voice-selection.json`；须在全部参考图完成、Agnes片段已排队后，用该音色按 `../story.json` 的30条 `narration` 逐条生成中文TTS。不得把其他影片的人声或未经选择的声音冒充本片音色；若跨会话失去voice_id，需重新试听确认。文件建议为 `audio/voice/SH01.mp3` 至 `SH30.mp3`。

实际生成并对照听检后写 `audio/manifest.json`：

```json
{
  "completed": 30,
  "clips": [
    {
      "id": "SH01",
      "file": "audio/voice/SH01.mp3",
      "voice_id": "voice-00",
      "text": "与story.json对应镜头的narration逐字相同",
      "sha256": "实际音频文件的SHA-256"
    }
  ]
}
```

上面仅展示一条的字段形状，不是可用的清单；完整清单必须包含30条真实音频、文本、用户选定声音和准确SHA。`render.py --plan-only` 先检查全部来源与画面审签、以FFmpeg探测音频活动区间并计算逐镜字幕窗口；超出镜头太多时拒绝强行加速，必须改词或重录。所有自动对时及合成后结果仍须人耳、逐字幕复核；用户要求的重点停顿需在最终音频实听确认。
