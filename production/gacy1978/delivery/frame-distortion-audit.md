# 成片逐帧畸变 / 时序 QC

- 成片：`小丑背后的真相_约翰韦恩盖西_三分钟_带声音.mp4`
- SHA-256：`53af564f8af653cc8d669fa037d8096a07138c35be690dae04ba3a91a7585023`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：49（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：1
- >1 秒近静止区段：1；其中非信息卡/片尾段：1
- 帧差/光流/亮度突变待复核窗口：36
- 人脸检测：逐帧总检测 1129；达到复核阈值的候选 906
- 手部检测：逐帧总检测 593；超出宽松几何边界的 landmark 事件 163

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 127 | 45 | 0 | 4.3798 | 8 |
| S02 | graphic | 108 | 0 | 0 | 225.2268 | 0 |
| S03 | agnes | 71 | 71 | 79 | 1.3938 | 0 |
| S04 | agnes | 87 | 0 | 0 | 0.0485 | 0 |
| S05 | agnes | 99 | 0 | 0 | 0.3688 | 0 |
| S06 | agnes | 125 | 48 | 0 | 1.2931 | 0 |
| S07 | agnes | 107 | 0 | 10 | 0.1079 | 0 |
| S08 | agnes | 158 | 1 | 0 | 468.6455 | 1 |
| S09 | agnes | 146 | 146 | 1 | 5.2327 | 4 |
| S10 | graphic | 111 | 0 | 0 | 151.8965 | 0 |
| S11 | agnes | 90 | 90 | 16 | 1.3545 | 0 |
| S12 | agnes | 128 | 0 | 2 | 0.7677 | 0 |
| S13 | agnes | 132 | 0 | 0 | 0.7761 | 0 |
| S14 | agnes | 156 | 0 | 0 | 1.1454 | 0 |
| S15 | agnes | 122 | 0 | 0 | 20.1669 | 1 |
| S16 | agnes | 80 | 0 | 0 | 0.564 | 0 |
| S17 | graphic | 63 | 0 | 0 | 151.8628 | 0 |
| S18 | agnes | 66 | 0 | 0 | 1.0106 | 0 |
| S19 | agnes | 130 | 130 | 62 | 0.8088 | 0 |
| S20 | agnes | 114 | 0 | 2 | 0.1833 | 0 |
| S21 | agnes | 115 | 28 | 0 | 11.8792 | 3 |
| S22 | agnes | 106 | 0 | 71 | 7.441 | 5 |
| S23 | agnes | 140 | 0 | 0 | 10.5955 | 1 |
| S24 | agnes | 86 | 86 | 0 | 0.6456 | 0 |
| S25 | agnes | 130 | 130 | 18 | 0.7156 | 0 |
| S26 | agnes | 115 | 0 | 0 | 1.2131 | 0 |
| S27 | agnes | 146 | 10 | 13 | 8.9498 | 0 |
| S28 | agnes | 130 | 130 | 37 | 1.7462 | 0 |
| S29 | agnes | 146 | 0 | 0 | 2.0573 | 0 |
| S30 | graphic | 189 | 43 | 0 | 428.5446 | 1 |
| S31 | agnes | 99 | 20 | 6 | 11.6345 | 1 |
| S32 | graphic | 120 | 0 | 0 | 183.4416 | 0 |
| S33 | agnes | 147 | 0 | 0 | 0.2991 | 0 |
| S34 | agnes | 80 | 0 | 0 | 0.1184 | 0 |
| S35 | agnes | 72 | 9 | 0 | 0.5683 | 0 |
| S36 | agnes | 111 | 0 | 109 | 9.947 | 2 |
| S37 | agnes | 138 | 138 | 55 | 0.7023 | 0 |
| S38 | graphic | 127 | 0 | 0 | 400.7258 | 1 |
| S39 | agnes | 133 | 4 | 38 | 1.3316 | 0 |
| S40 | graphic | 106 | 0 | 0 | 164.6557 | 0 |
| S41 | agnes | 143 | 0 | 0 | 1.0346 | 0 |
| S42 | agnes | 98 | 0 | 0 | 11.2325 | 4 |
| S43 | agnes | 67 | 0 | 74 | 4.7979 | 3 |
| S44 | agnes | 117 | 0 | 0 | 0.1986 | 0 |
| S45 | agnes | 205 | 0 | 0 | 0.6935 | 1 |
| END | graphic | 114 | 0 | 0 | 0.5786 | 0 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/gacy1978/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/gacy1978/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/gacy1978/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00011_t000.367.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00012_t000.400.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00013_t000.433.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00014_t000.467.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00015_t000.500.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00016_t000.533.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00017_t000.567.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00018_t000.600.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00019_t000.633.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00020_t000.667.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00021_t000.700.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00022_t000.733.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00023_t000.767.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00024_t000.800.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00025_t000.833.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00026_t000.867.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00027_t000.900.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00028_t000.933.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00029_t000.967.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00030_t001.000.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00031_t001.033.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00032_t001.067.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00033_t001.100.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00034_t001.133.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00035_t001.167.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00036_t001.200.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00037_t001.233.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00038_t001.267.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00039_t001.300.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00040_t001.333.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00041_t001.367.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00042_t001.400.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00043_t001.433.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00871_t029.033.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00872_t029.067.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00873_t029.100.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00874_t029.133.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00875_t029.167.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00942_t031.400.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00943_t031.433.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00944_t031.467.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00945_t031.500.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00946_t031.533.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00947_t031.567.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00948_t031.600.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00949_t031.633.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00950_t031.667.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00951_t031.700.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00952_t031.733.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00953_t031.767.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00954_t031.800.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00955_t031.833.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00956_t031.867.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00957_t031.900.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00958_t031.933.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00959_t031.967.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00960_t032.000.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00961_t032.033.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00962_t032.067.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00963_t032.100.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00964_t032.133.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00965_t032.167.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00966_t032.200.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00967_t032.233.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_00968_t032.267.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_01756_t058.533.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_01757_t058.567.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_01758_t058.600.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_01759_t058.633.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_01760_t058.667.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02259_t075.300.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02260_t075.333.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02261_t075.367.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02262_t075.400.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02263_t075.433.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02264_t075.467.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02265_t075.500.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02266_t075.533.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02267_t075.567.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02272_t075.733.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02273_t075.767.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02274_t075.800.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02275_t075.833.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02276_t075.867.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02277_t075.900.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02278_t075.933.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02279_t075.967.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02280_t076.000.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02281_t076.033.jpg', 'work/gacy1978/final-frame-audit/suspect-frames/frame_02282_t076.067.jpg']`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S03.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S07.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S09.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S11.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S19.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S20.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S22.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S25.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S27.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S28.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S31.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S36.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S37.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S39.jpg`
- 手部动态接触表：`work/gacy1978/final-frame-audit/contacts/hands-S43.jpg`

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
