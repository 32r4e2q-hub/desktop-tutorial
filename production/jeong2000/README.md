# 郑斗英：十个月，九条人命

三分钟抖音横版 3D 动画案件解说。项目结构沿用 `production/zama2017`（座间九人案）的 45 镜模板和仓库《新题目开工手册》的闸门，但动态画面供应商已明确替换为 **智谱 CogVideoX-Flash**，不调用 Agnes。

## 规格

- 1920×1080、30 fps、180 秒；45 镜全部只出现一次。
- 38 段 CogVideoX-Flash 写实 3D CGI 动画 + 7 张后期信息卡。
- 六章中文旁白，voice-00；原始 TTS 保留在 `audio/raw/`，收紧后约 175.98 秒，渲染整体变速 1.048。
- 常驻标签：`AI动画情景重现 · 非新闻影像`；字幕 60 px、关键词描黄。
- 不展示血腥、遗体、行凶过程、可复制的入室或越狱方法；人物不做真人肖像还原。

## 当前流程

1. `build_story.py` 是唯一内容源，生成 `story.json`、配音清单、发布文案。
2. `generate.py --validate` 检查 180 秒计划、38+7 镜头、CogVideoX 模型和配音 SHA-256。
3. `jeong2000-gen.yml` 使用仓库 Secret `ZHIPUAI_API_KEY` 调用免费 `cogvideox-flash`，将 task id、URL、请求哈希和视频 SHA-256 写入 `results.json`，并生成逐镜接触表。
4. `fetch_sources.py` 在新 runner 上按 SHA-256 从供应商 CDN 回填素材，不重新消耗生成额度。
5. `render.py` 只接受已登记且哈希一致的 CogVideoX 素材；按 `audio/clause-times.json` 的分句停顿切镜、混音、烧录字幕并复测成片。
6. 后续依次运行逐字听检、5400 帧全帧视觉 QC 和人工语义复核。

## 关键命令

```bash
python3 production/jeong2000/build_story.py
python3 production/jeong2000/generate.py --validate
python3 production/jeong2000/clause_times.py --check-cuts
```

生成通过 marker 触发：

```bash
echo '{"workers":1}' > production/jeong2000/GEN_REQUEST
```

成片目标：`交付/郑斗英_十个月，九条人命_三分钟_带声音.mp4`。

## 内容文件

- `史实核对.md`：上传稿与韩国公开报道逐项核对，记录判决日期等校正。
- `screenplay.md`：六章逐字解说与 45 镜规划。
- `抖音脚本.md`：按真实配音停顿计算的四列时间轴。
- `抖音发布文案.md`：三个标题、介绍、置顶提问与话题。
- `audio/manifest.json`：音色、逐字文本与收紧后音频 SHA-256。
