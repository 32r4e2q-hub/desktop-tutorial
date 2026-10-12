# 成片逐帧畸变 / 时序 QC

- 成片：`姜浩顺_一滴袖口的血，十名女人_三分钟_带声音.mp4`
- SHA-256：`37b338a9fa4159b080f3f6373b64237ecaaf2f2a977472c83c6642a0a890eb81`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：13（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：2；其中非信息卡/片尾段：2
- 帧差/光流/亮度突变待复核窗口：21
- 人脸检测：逐帧总检测 1061；达到复核阈值的候选 475
- 手部检测：逐帧总检测 614；超出宽松几何边界的 landmark 事件 75

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 149 | 0 | 0 | 0.6048 | 1 |
| S02 | graphic | 101 | 0 | 0 | 191.2762 | 0 |
| S03 | agnes | 73 | 0 | 0 | 0.0676 | 0 |
| S04 | agnes | 143 | 33 | 132 | 2.2414 | 3 |
| S05 | agnes | 131 | 131 | 45 | 1.0968 | 0 |
| S06 | agnes | 58 | 0 | 0 | 0.1251 | 0 |
| S07 | agnes | 121 | 0 | 0 | 6.5279 | 6 |
| S08 | agnes | 122 | 7 | 66 | 15.7041 | 2 |
| S09 | agnes | 160 | 0 | 0 | 1.469 | 0 |
| S10 | graphic | 72 | 6 | 0 | 143.122 | 0 |
| S11 | agnes | 120 | 0 | 0 | 0.3362 | 0 |
| S12 | agnes | 113 | 164 | 0 | 0.2626 | 0 |
| S13 | agnes | 115 | 0 | 0 | 0.2861 | 0 |
| S14 | agnes | 56 | 38 | 14 | 0.8396 | 0 |
| S15 | agnes | 133 | 0 | 0 | 0.6254 | 0 |
| S16 | agnes | 68 | 0 | 0 | 0.1116 | 0 |
| S17 | agnes | 114 | 0 | 52 | 0.5471 | 0 |
| S18 | graphic | 132 | 37 | 0 | 263.2924 | 0 |
| S19 | agnes | 82 | 0 | 0 | 0.9715 | 0 |
| S20 | agnes | 130 | 0 | 12 | 0.5841 | 0 |
| S21 | agnes | 133 | 0 | 0 | 0.1232 | 0 |
| S22 | agnes | 85 | 0 | 35 | 4.9518 | 6 |
| S23 | graphic | 161 | 44 | 0 | 234.8434 | 0 |
| S24 | agnes | 108 | 0 | 0 | 0.0984 | 0 |
| S25 | graphic | 91 | 49 | 0 | 225.3865 | 0 |
| S26 | agnes | 140 | 0 | 7 | 1.6399 | 0 |
| S27 | agnes | 118 | 118 | 47 | 3.4338 | 0 |
| S28 | agnes | 139 | 0 | 0 | 0.2616 | 0 |
| S29 | agnes | 128 | 0 | 0 | 1.2462 | 0 |
| S30 | agnes | 126 | 0 | 0 | 3.4165 | 1 |
| S31 | agnes | 96 | 0 | 0 | 0.1917 | 0 |
| S32 | graphic | 102 | 0 | 0 | 184.4466 | 0 |
| S33 | agnes | 117 | 117 | 0 | 0.2 | 0 |
| S34 | agnes | 89 | 0 | 0 | 0.13 | 0 |
| S35 | agnes | 123 | 0 | 0 | 0.1317 | 0 |
| S36 | agnes | 90 | 0 | 0 | 0.0895 | 0 |
| S37 | agnes | 102 | 67 | 0 | 0.3011 | 0 |
| S38 | agnes | 148 | 0 | 0 | 0.6168 | 0 |
| S39 | agnes | 193 | 193 | 204 | 0.7175 | 0 |
| S40 | agnes | 81 | 0 | 0 | 0.0678 | 0 |
| S41 | graphic | 141 | 57 | 0 | 199.4203 | 0 |
| S42 | agnes | 143 | 0 | 0 | 0.1504 | 0 |
| S43 | agnes | 101 | 0 | 0 | 0.2361 | 0 |
| S44 | agnes | 159 | 0 | 0 | 0.3686 | 0 |
| S45 | agnes | 179 | 0 | 0 | 0.4121 | 1 |
| END | graphic | 114 | 0 | 0 | 0.453 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/kanghosun2009/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/kanghosun2009/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/kanghosun2009/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00443_t014.767.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00444_t014.800.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00445_t014.833.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00446_t014.867.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00447_t014.900.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00448_t014.933.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00449_t014.967.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00450_t015.000.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00451_t015.033.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00452_t015.067.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00453_t015.100.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00454_t015.133.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00455_t015.167.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00456_t015.200.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00457_t015.233.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00458_t015.267.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00459_t015.300.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00460_t015.333.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00461_t015.367.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00462_t015.400.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00463_t015.433.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00464_t015.467.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00685_t022.833.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00686_t022.867.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00687_t022.900.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00688_t022.933.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00689_t022.967.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00690_t023.000.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00691_t023.033.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00692_t023.067.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00693_t023.100.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00694_t023.133.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00695_t023.167.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00696_t023.200.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00697_t023.233.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00698_t023.267.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00699_t023.300.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00700_t023.333.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00701_t023.367.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00702_t023.400.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00703_t023.433.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00704_t023.467.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00705_t023.500.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00706_t023.533.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00707_t023.567.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00708_t023.600.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00709_t023.633.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00710_t023.667.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00711_t023.700.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00785_t026.167.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00786_t026.200.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00787_t026.233.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00788_t026.267.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00789_t026.300.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00790_t026.333.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00791_t026.367.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00792_t026.400.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00793_t026.433.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00794_t026.467.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00795_t026.500.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00796_t026.533.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00797_t026.567.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00798_t026.600.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00799_t026.633.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00814_t027.133.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00815_t027.167.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00816_t027.200.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00817_t027.233.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00818_t027.267.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00819_t027.300.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00820_t027.333.jpg', 'work/kanghosun2009/final-frame-audit/suspect-frames/frame_00821_t027.367.jpg']`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S04.jpg`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S05.jpg`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S08.jpg`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S14.jpg`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S17.jpg`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S20.jpg`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S22.jpg`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S26.jpg`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S27.jpg`
- 手部动态接触表：`work/kanghosun2009/final-frame-audit/contacts/hands-S39.jpg`

## 限制

自动检测会漏检遮挡、极小目标和模型本身识别不到的 AI 畸变；时序异常也可能是有意运镜、火焰、蒸汽或字幕变化。所以候选必须看原始分辨率前后帧，语义与解剖必须人工目检。没有候选不等于数学上证明‘完美无瑕疵’。

## 全部输出帧的视觉接触表

全片 5400 帧按时间顺序逐帧收录、没有抽样；46 张分镜头接触表，每格 160×90 像素。缩略图用于扫查，异常仍须查看原始分辨率。

- 清单：`../qa/final-frame-review/all-frames/manifest.json`

- [S01](../qa/final-frame-review/all-frames/S01-all-frames.jpg)
- [S02](../qa/final-frame-review/all-frames/S02-all-frames.jpg)
- [S03](../qa/final-frame-review/all-frames/S03-all-frames.jpg)
- [S04](../qa/final-frame-review/all-frames/S04-all-frames.jpg)
- [S05](../qa/final-frame-review/all-frames/S05-all-frames.jpg)
- [S06](../qa/final-frame-review/all-frames/S06-all-frames.jpg)
- [S07](../qa/final-frame-review/all-frames/S07-all-frames.jpg)
- [S08](../qa/final-frame-review/all-frames/S08-all-frames.jpg)
- [S09](../qa/final-frame-review/all-frames/S09-all-frames.jpg)
- [S10](../qa/final-frame-review/all-frames/S10-all-frames.jpg)
- [S11](../qa/final-frame-review/all-frames/S11-all-frames.jpg)
- [S12](../qa/final-frame-review/all-frames/S12-all-frames.jpg)
- [S13](../qa/final-frame-review/all-frames/S13-all-frames.jpg)
- [S14](../qa/final-frame-review/all-frames/S14-all-frames.jpg)
- [S15](../qa/final-frame-review/all-frames/S15-all-frames.jpg)
- [S16](../qa/final-frame-review/all-frames/S16-all-frames.jpg)
- [S17](../qa/final-frame-review/all-frames/S17-all-frames.jpg)
- [S18](../qa/final-frame-review/all-frames/S18-all-frames.jpg)
- [S19](../qa/final-frame-review/all-frames/S19-all-frames.jpg)
- [S20](../qa/final-frame-review/all-frames/S20-all-frames.jpg)
- [S21](../qa/final-frame-review/all-frames/S21-all-frames.jpg)
- [S22](../qa/final-frame-review/all-frames/S22-all-frames.jpg)
- [S23](../qa/final-frame-review/all-frames/S23-all-frames.jpg)
- [S24](../qa/final-frame-review/all-frames/S24-all-frames.jpg)
- [S25](../qa/final-frame-review/all-frames/S25-all-frames.jpg)
- [S26](../qa/final-frame-review/all-frames/S26-all-frames.jpg)
- [S27](../qa/final-frame-review/all-frames/S27-all-frames.jpg)
- [S28](../qa/final-frame-review/all-frames/S28-all-frames.jpg)
- [S29](../qa/final-frame-review/all-frames/S29-all-frames.jpg)
- [S30](../qa/final-frame-review/all-frames/S30-all-frames.jpg)
- [S31](../qa/final-frame-review/all-frames/S31-all-frames.jpg)
- [S32](../qa/final-frame-review/all-frames/S32-all-frames.jpg)
- [S33](../qa/final-frame-review/all-frames/S33-all-frames.jpg)
- [S34](../qa/final-frame-review/all-frames/S34-all-frames.jpg)
- [S35](../qa/final-frame-review/all-frames/S35-all-frames.jpg)
- [S36](../qa/final-frame-review/all-frames/S36-all-frames.jpg)
- [S37](../qa/final-frame-review/all-frames/S37-all-frames.jpg)
- [S38](../qa/final-frame-review/all-frames/S38-all-frames.jpg)
- [S39](../qa/final-frame-review/all-frames/S39-all-frames.jpg)
- [S40](../qa/final-frame-review/all-frames/S40-all-frames.jpg)
- [S41](../qa/final-frame-review/all-frames/S41-all-frames.jpg)
- [S42](../qa/final-frame-review/all-frames/S42-all-frames.jpg)
- [S43](../qa/final-frame-review/all-frames/S43-all-frames.jpg)
- [S44](../qa/final-frame-review/all-frames/S44-all-frames.jpg)
- [S45](../qa/final-frame-review/all-frames/S45-all-frames.jpg)
- [END](../qa/final-frame-review/all-frames/END-all-frames.jpg)

人工逐帧视觉复核状态：**PENDING**。自动结果或缩略接触表都不等于无瑕疵。
