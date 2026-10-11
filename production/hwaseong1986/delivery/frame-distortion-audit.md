# 成片逐帧畸变 / 时序 QC

- 成片：`李春才_华城连环杀人案，DNA揭开了33年的秘密_三分钟_带声音.mp4`
- SHA-256：`25b8b37ffadd935c8edb9f2032f3f6df5fd50578d3a244a45892338950a7265e`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：14（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：3；其中非信息卡/片尾段：3
- 帧差/光流/亮度突变待复核窗口：18
- 人脸检测：逐帧总检测 1013；达到复核阈值的候选 671
- 手部检测：逐帧总检测 1449；超出宽松几何边界的 landmark 事件 479

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 107 | 70 | 0 | 1.7324 | 1 |
| S02 | graphic | 88 | 0 | 0 | 186.7783 | 0 |
| S03 | agnes | 116 | 0 | 0 | 0.1401 | 0 |
| S04 | agnes | 108 | 0 | 0 | 0.0945 | 0 |
| S05 | agnes | 76 | 0 | 0 | 0.1238 | 0 |
| S06 | agnes | 94 | 94 | 2 | 1.3765 | 1 |
| S07 | agnes | 108 | 0 | 76 | 1.6437 | 0 |
| S08 | agnes | 230 | 0 | 656 | 0.3292 | 0 |
| S09 | agnes | 135 | 0 | 0 | 0.1441 | 0 |
| S10 | agnes | 102 | 0 | 0 | 0.1717 | 0 |
| S11 | graphic | 99 | 15 | 0 | 167.2906 | 0 |
| S12 | agnes | 95 | 95 | 0 | 7.486 | 0 |
| S13 | agnes | 123 | 0 | 0 | 0.2026 | 0 |
| S14 | agnes | 116 | 24 | 0 | 0.2976 | 0 |
| S15 | agnes | 119 | 0 | 0 | 0.58 | 0 |
| S16 | agnes | 62 | 49 | 0 | 15.889 | 2 |
| S17 | agnes | 74 | 74 | 0 | 0.1475 | 0 |
| S18 | agnes | 78 | 0 | 0 | 0.8091 | 0 |
| S19 | graphic | 110 | 4 | 0 | 239.0155 | 0 |
| S20 | agnes | 130 | 0 | 147 | 0.7871 | 0 |
| S21 | agnes | 122 | 0 | 0 | 0.129 | 0 |
| S22 | agnes | 127 | 127 | 29 | 0.4444 | 0 |
| S23 | agnes | 178 | 0 | 176 | 0.1075 | 0 |
| S24 | agnes | 149 | 0 | 160 | 0.3805 | 0 |
| S25 | agnes | 103 | 0 | 0 | 0.064 | 0 |
| S26 | graphic | 121 | 19 | 0 | 226.5083 | 0 |
| S27 | agnes | 127 | 42 | 0 | 4.9 | 4 |
| S28 | agnes | 136 | 0 | 0 | 5.8823 | 2 |
| S29 | agnes | 119 | 119 | 118 | 1.3489 | 0 |
| S30 | agnes | 170 | 0 | 0 | 0.1917 | 0 |
| S31 | agnes | 66 | 0 | 0 | 0.1711 | 0 |
| S32 | agnes | 126 | 0 | 0 | 0.6602 | 0 |
| S33 | graphic | 95 | 42 | 0 | 230.5889 | 0 |
| S34 | agnes | 104 | 0 | 0 | 0.0717 | 0 |
| S35 | agnes | 153 | 0 | 0 | 0.371 | 0 |
| S36 | agnes | 110 | 0 | 0 | 0.1221 | 0 |
| S37 | agnes | 124 | 0 | 0 | 0.0956 | 0 |
| S38 | agnes | 104 | 0 | 0 | 0.2676 | 0 |
| S39 | graphic | 132 | 34 | 0 | 206.3953 | 0 |
| S40 | agnes | 163 | 163 | 85 | 3.4503 | 6 |
| S41 | graphic | 92 | 42 | 0 | 157.7435 | 0 |
| S42 | agnes | 91 | 0 | 0 | 0.1062 | 0 |
| S43 | agnes | 122 | 0 | 0 | 0.8877 | 0 |
| S44 | agnes | 97 | 0 | 0 | 0.2171 | 0 |
| S45 | agnes | 185 | 0 | 0 | 0.8473 | 1 |
| END | graphic | 114 | 0 | 0 | 0.3246 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/hwaseong1986/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/hwaseong1986/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/hwaseong1986/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00060_t002.000.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00061_t002.033.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00062_t002.067.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00063_t002.100.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00064_t002.133.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00065_t002.167.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00066_t002.200.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00581_t019.367.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00582_t019.400.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00583_t019.433.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00584_t019.467.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_00585_t019.500.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01716_t057.200.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01717_t057.233.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01718_t057.267.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01719_t057.300.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01720_t057.333.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01723_t057.433.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01724_t057.467.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01725_t057.500.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01726_t057.533.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01727_t057.567.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01728_t057.600.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_01729_t057.633.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03009_t100.300.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03010_t100.333.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03011_t100.367.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03012_t100.400.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03013_t100.433.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03014_t100.467.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03015_t100.500.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03016_t100.533.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03017_t100.567.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03018_t100.600.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03019_t100.633.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03020_t100.667.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03021_t100.700.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03022_t100.733.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03023_t100.767.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03024_t100.800.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03025_t100.833.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03026_t100.867.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03195_t106.500.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03196_t106.533.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03197_t106.567.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03198_t106.600.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03199_t106.633.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03200_t106.667.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03201_t106.700.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03202_t106.733.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03203_t106.767.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_03204_t106.800.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04567_t152.233.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04568_t152.267.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04569_t152.300.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04570_t152.333.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04571_t152.367.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04572_t152.400.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04573_t152.433.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04574_t152.467.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04575_t152.500.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04576_t152.533.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04577_t152.567.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04578_t152.600.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04579_t152.633.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04580_t152.667.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04581_t152.700.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04586_t152.867.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04587_t152.900.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04588_t152.933.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04589_t152.967.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04590_t153.000.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04643_t154.767.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04644_t154.800.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04645_t154.833.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04646_t154.867.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04647_t154.900.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04653_t155.100.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04654_t155.133.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04655_t155.167.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04656_t155.200.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04657_t155.233.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04672_t155.733.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04673_t155.767.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04674_t155.800.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04675_t155.833.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_04676_t155.867.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/hwaseong1986/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/hwaseong1986/final-frame-audit/contacts/hands-S06.jpg`
- 手部动态接触表：`work/hwaseong1986/final-frame-audit/contacts/hands-S07.jpg`
- 手部动态接触表：`work/hwaseong1986/final-frame-audit/contacts/hands-S08.jpg`
- 手部动态接触表：`work/hwaseong1986/final-frame-audit/contacts/hands-S20.jpg`
- 手部动态接触表：`work/hwaseong1986/final-frame-audit/contacts/hands-S22.jpg`
- 手部动态接触表：`work/hwaseong1986/final-frame-audit/contacts/hands-S23.jpg`
- 手部动态接触表：`work/hwaseong1986/final-frame-audit/contacts/hands-S24.jpg`
- 手部动态接触表：`work/hwaseong1986/final-frame-audit/contacts/hands-S29.jpg`
- 手部动态接触表：`work/hwaseong1986/final-frame-audit/contacts/hands-S40.jpg`

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
