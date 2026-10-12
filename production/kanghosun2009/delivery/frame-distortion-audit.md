# 成片逐帧畸变 / 时序 QC

- 成片：`姜浩顺_一滴袖口的血，十名女人_三分钟_带声音.mp4`
- SHA-256：`33c33b85c5d4ea723698c6529b4e7bed1900e189f68b1bc8abb5517cfa0538cc`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：13（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：2；其中非信息卡/片尾段：2
- 帧差/光流/亮度突变待复核窗口：21
- 人脸检测：逐帧总检测 1201；达到复核阈值的候选 540
- 手部检测：逐帧总检测 715；超出宽松几何边界的 landmark 事件 77

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 149 | 0 | 0 | 0.6047 | 1 |
| S03 | agnes | 101 | 0 | 0 | 0.1523 | 0 |
| S08 | agnes | 73 | 5 | 69 | 15.693 | 3 |
| S07 | agnes | 143 | 0 | 0 | 6.4759 | 5 |
| S04 | agnes | 131 | 92 | 292 | 2.6417 | 1 |
| S05 | agnes | 179 | 179 | 89 | 1.1335 | 0 |
| S27 | agnes | 122 | 122 | 63 | 3.433 | 0 |
| S10 | graphic | 87 | 4 | 0 | 142.6993 | 0 |
| S09 | agnes | 145 | 0 | 0 | 1.5094 | 0 |
| S11 | agnes | 120 | 0 | 0 | 0.3317 | 0 |
| S12 | agnes | 113 | 164 | 0 | 0.2633 | 0 |
| S13 | agnes | 171 | 0 | 33 | 7.7752 | 1 |
| S14 | agnes | 133 | 72 | 11 | 0.8371 | 0 |
| S17 | agnes | 68 | 0 | 41 | 0.5451 | 0 |
| S15 | agnes | 114 | 0 | 0 | 0.625 | 0 |
| S16 | agnes | 174 | 0 | 0 | 0.1169 | 0 |
| S21 | agnes | 123 | 0 | 0 | 0.1034 | 0 |
| S19 | agnes | 94 | 0 | 0 | 1.0811 | 0 |
| S18 | graphic | 86 | 35 | 0 | 206.3891 | 0 |
| S06 | agnes | 85 | 0 | 0 | 0.1391 | 0 |
| S20 | agnes | 67 | 0 | 17 | 0.5803 | 0 |
| S23 | graphic | 94 | 49 | 0 | 185.6609 | 0 |
| S26 | agnes | 108 | 0 | 0 | 0.2952 | 0 |
| S25 | graphic | 91 | 10 | 0 | 77.0845 | 0 |
| S28 | agnes | 113 | 0 | 0 | 0.2627 | 0 |
| S29 | agnes | 79 | 0 | 0 | 1.2445 | 0 |
| S24 | agnes | 66 | 0 | 0 | 0.0796 | 0 |
| S30 | agnes | 171 | 0 | 0 | 3.382 | 2 |
| S22 | agnes | 96 | 0 | 46 | 4.961 | 6 |
| S02 | graphic | 126 | 0 | 0 | 169.4813 | 0 |
| S31 | agnes | 96 | 0 | 0 | 0.194 | 0 |
| S33 | agnes | 132 | 132 | 0 | 0.1967 | 0 |
| S32 | graphic | 87 | 0 | 0 | 140.9623 | 0 |
| S34 | agnes | 89 | 0 | 0 | 0.1303 | 0 |
| S35 | agnes | 80 | 0 | 0 | 0.1287 | 0 |
| S36 | agnes | 43 | 0 | 0 | 0.0624 | 0 |
| S38 | agnes | 192 | 0 | 0 | 0.3322 | 0 |
| S37 | agnes | 148 | 91 | 0 | 0.3297 | 0 |
| S39 | agnes | 193 | 193 | 54 | 1.6877 | 0 |
| S40 | agnes | 185 | 0 | 0 | 0.0733 | 0 |
| S41 | graphic | 66 | 53 | 0 | 131.2217 | 0 |
| S42 | agnes | 168 | 0 | 0 | 0.1584 | 0 |
| S43 | agnes | 152 | 0 | 0 | 0.3148 | 0 |
| S44 | agnes | 119 | 0 | 0 | 0.3275 | 0 |
| S45 | agnes | 114 | 0 | 0 | 0.4156 | 1 |
| END | graphic | 114 | 0 | 0 | 0.4532 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`/tmp/kanghosun2009-final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`/tmp/kanghosun2009-final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00267_t008.900.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00268_t008.933.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00269_t008.967.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00270_t009.000.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00271_t009.033.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00272_t009.067.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00289_t009.633.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00290_t009.667.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00291_t009.700.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00292_t009.733.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00293_t009.767.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00294_t009.800.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00295_t009.833.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00296_t009.867.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00297_t009.900.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00349_t011.633.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00350_t011.667.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00351_t011.700.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00352_t011.733.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00353_t011.767.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00354_t011.800.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00355_t011.833.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00356_t011.867.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00357_t011.900.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00358_t011.933.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00359_t011.967.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00360_t012.000.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00361_t012.033.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00362_t012.067.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00363_t012.100.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00364_t012.133.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00365_t012.167.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00366_t012.200.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00367_t012.233.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00368_t012.267.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00369_t012.300.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00370_t012.333.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00371_t012.367.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00372_t012.400.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00373_t012.433.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00374_t012.467.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00375_t012.500.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00376_t012.533.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00377_t012.567.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00378_t012.600.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00379_t012.633.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00380_t012.667.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00381_t012.700.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00382_t012.733.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00383_t012.767.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00590_t019.667.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00591_t019.700.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00592_t019.733.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00593_t019.767.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_00594_t019.800.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01506_t050.200.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01507_t050.233.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01508_t050.267.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01509_t050.300.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01510_t050.333.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01511_t050.367.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01512_t050.400.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01513_t050.433.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01514_t050.467.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01515_t050.500.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01516_t050.533.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01517_t050.567.jpg', '/tmp/kanghosun2009-final-frame-audit/suspect-frames/frame_01518_t050.600.jpg']`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S04.jpg`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S05.jpg`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S08.jpg`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S13.jpg`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S14.jpg`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S17.jpg`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S20.jpg`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S22.jpg`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S27.jpg`
- 手部动态接触表：`/tmp/kanghosun2009-final-frame-audit/contacts/hands-S39.jpg`

## 限制

自动检测会漏检遮挡、极小目标和模型本身识别不到的 AI 畸变；时序异常也可能是有意运镜、火焰、蒸汽或字幕变化。所以候选必须看原始分辨率前后帧，语义与解剖必须人工目检。没有候选不等于数学上证明‘完美无瑕疵’。

## 全部输出帧的视觉接触表

全片 5400 帧按时间顺序逐帧收录、没有抽样；46 张分镜头接触表，每格 160×90 像素。缩略图用于扫查，异常仍须查看原始分辨率。

- 清单：`../qa/final-frame-review/all-frames/manifest.json`

- [S01](../qa/final-frame-review/all-frames/S01-all-frames.jpg)
- [S03](../qa/final-frame-review/all-frames/S03-all-frames.jpg)
- [S08](../qa/final-frame-review/all-frames/S08-all-frames.jpg)
- [S07](../qa/final-frame-review/all-frames/S07-all-frames.jpg)
- [S04](../qa/final-frame-review/all-frames/S04-all-frames.jpg)
- [S05](../qa/final-frame-review/all-frames/S05-all-frames.jpg)
- [S27](../qa/final-frame-review/all-frames/S27-all-frames.jpg)
- [S10](../qa/final-frame-review/all-frames/S10-all-frames.jpg)
- [S09](../qa/final-frame-review/all-frames/S09-all-frames.jpg)
- [S11](../qa/final-frame-review/all-frames/S11-all-frames.jpg)
- [S12](../qa/final-frame-review/all-frames/S12-all-frames.jpg)
- [S13](../qa/final-frame-review/all-frames/S13-all-frames.jpg)
- [S14](../qa/final-frame-review/all-frames/S14-all-frames.jpg)
- [S17](../qa/final-frame-review/all-frames/S17-all-frames.jpg)
- [S15](../qa/final-frame-review/all-frames/S15-all-frames.jpg)
- [S16](../qa/final-frame-review/all-frames/S16-all-frames.jpg)
- [S21](../qa/final-frame-review/all-frames/S21-all-frames.jpg)
- [S19](../qa/final-frame-review/all-frames/S19-all-frames.jpg)
- [S18](../qa/final-frame-review/all-frames/S18-all-frames.jpg)
- [S06](../qa/final-frame-review/all-frames/S06-all-frames.jpg)
- [S20](../qa/final-frame-review/all-frames/S20-all-frames.jpg)
- [S23](../qa/final-frame-review/all-frames/S23-all-frames.jpg)
- [S26](../qa/final-frame-review/all-frames/S26-all-frames.jpg)
- [S25](../qa/final-frame-review/all-frames/S25-all-frames.jpg)
- [S28](../qa/final-frame-review/all-frames/S28-all-frames.jpg)
- [S29](../qa/final-frame-review/all-frames/S29-all-frames.jpg)
- [S24](../qa/final-frame-review/all-frames/S24-all-frames.jpg)
- [S30](../qa/final-frame-review/all-frames/S30-all-frames.jpg)
- [S22](../qa/final-frame-review/all-frames/S22-all-frames.jpg)
- [S02](../qa/final-frame-review/all-frames/S02-all-frames.jpg)
- [S31](../qa/final-frame-review/all-frames/S31-all-frames.jpg)
- [S33](../qa/final-frame-review/all-frames/S33-all-frames.jpg)
- [S32](../qa/final-frame-review/all-frames/S32-all-frames.jpg)
- [S34](../qa/final-frame-review/all-frames/S34-all-frames.jpg)
- [S35](../qa/final-frame-review/all-frames/S35-all-frames.jpg)
- [S36](../qa/final-frame-review/all-frames/S36-all-frames.jpg)
- [S38](../qa/final-frame-review/all-frames/S38-all-frames.jpg)
- [S37](../qa/final-frame-review/all-frames/S37-all-frames.jpg)
- [S39](../qa/final-frame-review/all-frames/S39-all-frames.jpg)
- [S40](../qa/final-frame-review/all-frames/S40-all-frames.jpg)
- [S41](../qa/final-frame-review/all-frames/S41-all-frames.jpg)
- [S42](../qa/final-frame-review/all-frames/S42-all-frames.jpg)
- [S43](../qa/final-frame-review/all-frames/S43-all-frames.jpg)
- [S44](../qa/final-frame-review/all-frames/S44-all-frames.jpg)
- [S45](../qa/final-frame-review/all-frames/S45-all-frames.jpg)
- [END](../qa/final-frame-review/all-frames/END-all-frames.jpg)

人工逐帧视觉复核状态：**PENDING**。自动结果或缩略接触表都不等于无瑕疵。
