# 成片逐帧畸变 / 时序 QC

- 成片：`呼格吉勒图案_18岁报案人被判死刑_18年后还他清白_三分钟_带声音.mp4`
- SHA-256：`bb11dc2139882ef53fd9e04bfb326790efbc77a111f30c5ef278226fef9e4f6e`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：12（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：5；其中非信息卡/片尾段：5
- 帧差/光流/亮度突变待复核窗口：20
- 人脸检测：逐帧总检测 811；达到复核阈值的候选 545
- 手部检测：逐帧总检测 833；超出宽松几何边界的 landmark 事件 105

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 79 | 0 | 0 | 0.8314 | 1 |
| S02 | graphic | 102 | 0 | 0 | 193.897 | 0 |
| S03 | agnes | 125 | 0 | 0 | 0.1414 | 0 |
| S04 | agnes | 91 | 91 | 0 | 0.5978 | 0 |
| S05 | agnes | 90 | 0 | 82 | 0.1309 | 0 |
| S06 | agnes | 92 | 0 | 0 | 0.3383 | 0 |
| S07 | agnes | 93 | 0 | 0 | 0.2423 | 0 |
| S08 | agnes | 151 | 0 | 0 | 0.0868 | 0 |
| S09 | agnes | 140 | 0 | 0 | 0.4908 | 0 |
| S10 | graphic | 135 | 37 | 0 | 191.6153 | 0 |
| S11 | agnes | 142 | 0 | 0 | 0.2844 | 0 |
| S12 | agnes | 129 | 0 | 0 | 0.5979 | 0 |
| S13 | agnes | 133 | 0 | 0 | 0.2889 | 0 |
| S14 | agnes | 131 | 0 | 0 | 0.1806 | 0 |
| S15 | agnes | 140 | 0 | 1 | 3.521 | 1 |
| S16 | agnes | 137 | 12 | 0 | 0.1989 | 0 |
| S17 | graphic | 104 | 33 | 0 | 181.0737 | 0 |
| S18 | agnes | 131 | 0 | 0 | 0.7257 | 0 |
| S19 | agnes | 87 | 87 | 67 | 0.6148 | 0 |
| S20 | agnes | 61 | 0 | 6 | 6.5144 | 3 |
| S21 | agnes | 117 | 117 | 221 | 0.5293 | 0 |
| S22 | agnes | 115 | 115 | 236 | 0.7223 | 0 |
| S23 | agnes | 137 | 0 | 0 | 0.0992 | 0 |
| S24 | agnes | 132 | 10 | 0 | 0.4327 | 0 |
| S25 | graphic | 135 | 15 | 0 | 191.0759 | 0 |
| S26 | agnes | 89 | 0 | 0 | 2.4831 | 0 |
| S27 | agnes | 137 | 0 | 16 | 8.2444 | 5 |
| S28 | agnes | 141 | 0 | 0 | 2.2556 | 0 |
| S29 | agnes | 116 | 116 | 67 | 1.8208 | 0 |
| S30 | agnes | 117 | 0 | 0 | 0.3764 | 0 |
| S31 | agnes | 148 | 0 | 136 | 5.2098 | 4 |
| S32 | graphic | 76 | 15 | 0 | 116.9846 | 1 |
| S33 | agnes | 69 | 0 | 0 | 0.0907 | 0 |
| S34 | agnes | 90 | 0 | 0 | 0.1915 | 0 |
| S35 | agnes | 118 | 0 | 0 | 0.0667 | 0 |
| S36 | agnes | 118 | 0 | 1 | 1.1047 | 3 |
| S37 | agnes | 89 | 0 | 0 | 0.1424 | 0 |
| S38 | graphic | 120 | 36 | 0 | 180.7921 | 0 |
| S39 | agnes | 128 | 0 | 0 | 0.1084 | 0 |
| S40 | graphic | 158 | 11 | 0 | 258.2306 | 0 |
| S41 | agnes | 127 | 0 | 0 | 0.2394 | 0 |
| S42 | agnes | 116 | 116 | 0 | 0.8167 | 0 |
| S43 | agnes | 112 | 0 | 0 | 0.051 | 0 |
| S44 | agnes | 128 | 0 | 0 | 0.2668 | 0 |
| S45 | agnes | 160 | 0 | 0 | 1.1257 | 1 |
| END | graphic | 114 | 0 | 0 | 0.6017 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/hugejiletu/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/hugejiletu/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/hugejiletu/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00332_t011.067.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00333_t011.100.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00334_t011.133.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00335_t011.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00336_t011.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00337_t011.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00338_t011.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_00339_t011.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01667_t055.567.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01668_t055.600.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01669_t055.633.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01670_t055.667.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_01671_t055.700.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02275_t075.833.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02276_t075.867.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02277_t075.900.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02278_t075.933.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02279_t075.967.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02280_t076.000.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02281_t076.033.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02282_t076.067.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02283_t076.100.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02284_t076.133.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02285_t076.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02286_t076.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02287_t076.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_02288_t076.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03070_t102.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03071_t102.367.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03072_t102.400.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03073_t102.433.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03074_t102.467.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03075_t102.500.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03076_t102.533.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03077_t102.567.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03078_t102.600.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03079_t102.633.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03080_t102.667.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03081_t102.700.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03082_t102.733.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03083_t102.767.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03084_t102.800.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03085_t102.833.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03086_t102.867.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03087_t102.900.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03088_t102.933.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03089_t102.967.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03090_t103.000.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03091_t103.033.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03534_t117.800.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03535_t117.833.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03536_t117.867.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03537_t117.900.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03538_t117.933.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03539_t117.967.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03540_t118.000.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03541_t118.033.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03542_t118.067.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03543_t118.100.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03544_t118.133.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03545_t118.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03546_t118.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03547_t118.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03548_t118.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03549_t118.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03550_t118.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03551_t118.367.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03552_t118.400.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03553_t118.433.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03554_t118.467.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03555_t118.500.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03556_t118.533.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03743_t124.767.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03744_t124.800.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03745_t124.833.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03746_t124.867.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_03747_t124.900.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04047_t134.900.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04048_t134.933.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04049_t134.967.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04050_t135.000.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04051_t135.033.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04052_t135.067.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04053_t135.100.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04054_t135.133.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04055_t135.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04056_t135.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04057_t135.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04058_t135.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04059_t135.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_04060_t135.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/hugejiletu/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S05.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S19.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S20.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S21.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S22.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S27.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S29.jpg`
- 手部动态接触表：`work/hugejiletu/final-frame-audit/contacts/hands-S31.jpg`

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
