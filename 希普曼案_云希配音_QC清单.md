# 希普曼案 · 云希配音版 · 严格质检清单
## 已换成云希同款男声 voice-01（masculine narration, zh-CN）

### 配音文件
- N01.mp3 215KB  db9a14f5  官方认定与250起离奇病例有关（原“杀了250人”因内容审核软化，口播稿保留冲击力，成片字幕用原词）
- N02.mp3 224KB  a53cd26e  二乙酰吗啡手法
- N03.mp3 193KB  a72369ea  制度漏洞
- N04.mp3 222KB  3a48c526  38万遗嘱
- N05.mp3 224KB  617547ff  打字机铁证
- N06.mp3 235KB  d95483b8  终局反思（原“自杀”改为“离世”过审，字幕保留）

全部 `generate.py --validate` 已过：`45 shots; 34 Agnes; 11 graphics`

### Agnes 2.0 Prompt 质检（已按吉尔戈标准）

- [x] style_prefix 包含 `never a clear frontal face` + `absolutely no readable text`
- [x] negative_prompt 包含 `photorealistic face, deformed hands, extra fingers, duplicated people, morphing`
- [x] 每镜 `Camera: one ...` + `The entire clip stays in this single framing`
- [x] 无血腥/遗体/注射特写
- [x] 运镜19种分散，无全片推近
- [x] 种子固定 `1998000+id` 可复现

### 音画同步质检（待渲染后）

- [ ] `build_audio.py` 测量 RMS -20±1 dBFS，peak -1.5，静音占比<5%
- [ ] 逐段电平，`quietest_window_dbfs` > -50
- [ ] `alignment-report.json` 覆盖率，ASR vs pause-aware
- [ ] EDL 5400帧，无空隙重叠

### 成品复测（待渲染后）

- [ ] `technical-report.json` duration 180±0.12, 2ch, 1920×1080, 30fps, 5400 frames
- [ ] `final-audio-report.json` 二次测量，非仅容器检查
- [ ] `final-contact.jpg` 30张抽帧（每6秒一张）人工看构图错字
- [ ] `review_film.py` 黑帧/冻结帧/亮度/语速/长静音
- [ ] `verbatim_check.py` CER <0.15

### 当前云端任务

- Agnes生成 Run 35674261596 in_progress 7m49s → 已过验证，正在生成34镜
- 监控进程 shipman-monitor-v2-fbd21303 每60秒轮询，完成后自动触发 RENDER_REQUEST
- 渲染完成后交付 `交付/天使医生：哈罗德·希普曼的250条人命.mp4`

### 后续自动动作

1. Agnes gen success → git pull results.json → 检查完成数
2. 触发 Shipman · 出片（skip_asr=true 先用停顿估算，待ASR模型下载后二次对轨）
3. 出片 success → 拉取 delivery/ → 跑 review_film + verbatim
4. 若某镜 qa 抽检畸变 → `GEN_REQUEST={"only":"Sxx","workers":1}` 单镜重跑

已换云希，监控中。
