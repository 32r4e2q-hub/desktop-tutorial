# 成片逐帧畸变 / 时序 QC

- 成片：`呼格吉勒图案_18岁报案人被判死刑_18年后还他清白_三分钟_带声音.mp4`
- SHA-256：`78f93e26652fc314dbcb2663386ee09e8d0dc0a0d43b7b9ef388cb0c73083188`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：12（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：4；其中非信息卡/片尾段：4
- 帧差/光流/亮度突变待复核窗口：6
- 人脸检测：逐帧总检测 905；达到复核阈值的候选 567
- 手部检测：逐帧总检测 783；超出宽松几何边界的 landmark 事件 56

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 125 | 0 | 0 | 0.8385 | 1 |
| S02 | graphic | 108 | 11 | 0 | 217.767 | 0 |
| S03 | agnes | 106 | 0 | 0 | 0.153 | 0 |
| S04 | agnes | 120 | 120 | 0 | 1.0981 | 0 |
| S05 | agnes | 81 | 0 | 50 | 0.1352 | 0 |
| S06 | agnes | 119 | 0 | 0 | 0.3383 | 0 |
| S07 | agnes | 117 | 0 | 0 | 0.2507 | 0 |
| S08 | agnes | 115 | 0 | 0 | 0.0983 | 0 |
| S11 | agnes | 95 | 0 | 0 | 0.2807 | 0 |
| S09 | agnes | 67 | 0 | 0 | 0.1974 | 0 |
| S12 | agnes | 119 | 0 | 0 | 0.5988 | 0 |
| S10 | graphic | 117 | 38 | 0 | 185.068 | 0 |
| S13 | agnes | 119 | 0 | 0 | 0.2722 | 0 |
| S14 | agnes | 128 | 0 | 0 | 0.1766 | 0 |
| S15 | agnes | 138 | 0 | 0 | 3.5209 | 1 |
| S16 | agnes | 149 | 11 | 0 | 0.3482 | 0 |
| S17 | graphic | 74 | 34 | 0 | 177.3468 | 0 |
| S18 | agnes | 73 | 0 | 0 | 0.7235 | 0 |
| S19 | agnes | 97 | 97 | 88 | 0.6202 | 0 |
| S20 | agnes | 79 | 0 | 6 | 6.5299 | 2 |
| S23 | agnes | 103 | 0 | 0 | 0.0767 | 0 |
| S21 | agnes | 117 | 117 | 249 | 0.5258 | 0 |
| S22 | agnes | 141 | 141 | 282 | 0.7211 | 0 |
| S24 | agnes | 130 | 9 | 0 | 0.4305 | 0 |
| S25 | graphic | 138 | 15 | 0 | 207.3823 | 0 |
| S26 | agnes | 118 | 0 | 25 | 2.4725 | 0 |
| S27 | agnes | 95 | 0 | 0 | 0.1989 | 0 |
| S28 | agnes | 124 | 0 | 0 | 2.2447 | 0 |
| S29 | agnes | 109 | 109 | 83 | 1.8122 | 0 |
| S30 | agnes | 139 | 0 | 0 | 0.3782 | 0 |
| S31 | agnes | 96 | 0 | 0 | 0.395 | 0 |
| S32 | graphic | 109 | 15 | 0 | 99.2741 | 0 |
| S33 | agnes | 110 | 0 | 0 | 0.1277 | 0 |
| S34 | agnes | 107 | 0 | 0 | 0.2498 | 0 |
| S35 | agnes | 115 | 0 | 0 | 0.0679 | 0 |
| S36 | agnes | 92 | 0 | 0 | 0.1034 | 0 |
| S37 | agnes | 129 | 0 | 0 | 0.2327 | 0 |
| S38 | graphic | 128 | 35 | 0 | 162.8384 | 0 |
| S39 | agnes | 122 | 0 | 0 | 0.1058 | 0 |
| S40 | graphic | 154 | 14 | 0 | 212.0779 | 0 |
| S41 | agnes | 108 | 0 | 0 | 0.2402 | 0 |
| S42 | agnes | 139 | 139 | 0 | 0.9665 | 0 |
| S43 | agnes | 140 | 0 | 0 | 0.0521 | 0 |
| S44 | agnes | 162 | 0 | 0 | 0.2758 | 0 |
| S45 | agnes | 215 | 0 | 0 | 1.2265 | 1 |
| END | graphic | 114 | 0 | 0 | 0.6017 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/hugejiletu/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/hugejiletu/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/hugejiletu/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00365_t012.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00366_t012.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00367_t012.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00368_t012.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00369_t012.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00370_t012.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00371_t012.367.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00372_t012.400.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00373_t012.433.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00374_t012.467.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00395_t013.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00396_t013.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00397_t013.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00398_t013.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00399_t013.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00400_t013.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00407_t013.567.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00408_t013.600.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00409_t013.633.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00410_t013.667.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00411_t013.700.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00484_t016.133.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00485_t016.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00486_t016.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00487_t016.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00488_t016.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00489_t016.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00490_t016.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00491_t016.367.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00492_t016.400.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00493_t016.433.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00494_t016.467.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00495_t016.500.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00496_t016.533.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01570_t052.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01571_t052.367.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01572_t052.400.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01573_t052.433.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01574_t052.467.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02110_t070.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02111_t070.367.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02112_t070.400.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02113_t070.433.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02114_t070.467.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02115_t070.500.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02116_t070.533.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02117_t070.567.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02118_t070.600.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02119_t070.633.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02120_t070.667.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02121_t070.700.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02122_t070.733.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02123_t070.767.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S05.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S19.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S20.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S21.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S22.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S26.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S29.jpg`

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
- [S11](../qa/final-frame-review/all-frames/S11-all-frames.jpg)
- [S09](../qa/final-frame-review/all-frames/S09-all-frames.jpg)
- [S12](../qa/final-frame-review/all-frames/S12-all-frames.jpg)
- [S10](../qa/final-frame-review/all-frames/S10-all-frames.jpg)
- [S13](../qa/final-frame-review/all-frames/S13-all-frames.jpg)
- [S14](../qa/final-frame-review/all-frames/S14-all-frames.jpg)
- [S15](../qa/final-frame-review/all-frames/S15-all-frames.jpg)
- [S16](../qa/final-frame-review/all-frames/S16-all-frames.jpg)
- [S17](../qa/final-frame-review/all-frames/S17-all-frames.jpg)
- [S18](../qa/final-frame-review/all-frames/S18-all-frames.jpg)
- [S19](../qa/final-frame-review/all-frames/S19-all-frames.jpg)
- [S20](../qa/final-frame-review/all-frames/S20-all-frames.jpg)
- [S23](../qa/final-frame-review/all-frames/S23-all-frames.jpg)
- [S21](../qa/final-frame-review/all-frames/S21-all-frames.jpg)
- [S22](../qa/final-frame-review/all-frames/S22-all-frames.jpg)
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
