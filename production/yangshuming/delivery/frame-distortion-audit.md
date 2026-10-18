# 成片逐帧畸变 / 时序 QC

- 成片：`红衣杀手杨树明_14年，9名女性遇害，警方如何撕开他的伪装？_三分钟_带声音.mp4`
- SHA-256：`f26c9f55a97a9f4f82b8b55a5c0c755843bd73cfa03d60c81b0e4afd5f417ab7`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：13（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：4；其中非信息卡/片尾段：4
- 帧差/光流/亮度突变待复核窗口：7
- 人脸检测：逐帧总检测 711；达到复核阈值的候选 251
- 手部检测：逐帧总检测 755；超出宽松几何边界的 landmark 事件 151

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 116 | 0 | 0 | 0.8825 | 1 |
| S02 | graphic | 93 | 0 | 0 | 163.0338 | 0 |
| S03 | agnes | 120 | 0 | 0 | 1.5994 | 0 |
| S04 | agnes | 108 | 0 | 0 | 0.8158 | 0 |
| S05 | agnes | 112 | 0 | 0 | 0.0881 | 0 |
| S06 | agnes | 122 | 0 | 0 | 0.4285 | 2 |
| S07 | agnes | 77 | 0 | 0 | 0.0479 | 0 |
| S08 | agnes | 122 | 0 | 0 | 0.0662 | 0 |
| S09 | agnes | 176 | 0 | 0 | 1.0324 | 0 |
| S10 | graphic | 138 | 0 | 0 | 164.0082 | 0 |
| S11 | agnes | 106 | 106 | 154 | 1.2277 | 0 |
| S12 | agnes | 112 | 0 | 0 | 0.5649 | 0 |
| S13 | agnes | 153 | 0 | 0 | 0.1761 | 0 |
| S14 | agnes | 94 | 11 | 0 | 1.1671 | 0 |
| S15 | agnes | 144 | 136 | 0 | 0.3108 | 0 |
| S16 | agnes | 104 | 0 | 0 | 0.3672 | 0 |
| S17 | graphic | 139 | 2 | 0 | 210.3294 | 0 |
| S18 | agnes | 100 | 0 | 0 | 0.0567 | 0 |
| S19 | agnes | 86 | 66 | 0 | 0.5422 | 0 |
| S20 | agnes | 145 | 0 | 0 | 0.1419 | 0 |
| S21 | agnes | 123 | 0 | 0 | 0.1153 | 0 |
| S22 | agnes | 100 | 0 | 0 | 0.0785 | 0 |
| S23 | agnes | 106 | 0 | 0 | 0.7302 | 0 |
| S24 | agnes | 134 | 0 | 0 | 1.5338 | 0 |
| S25 | agnes | 83 | 83 | 162 | 1.3232 | 0 |
| S26 | agnes | 65 | 0 | 55 | 8.9124 | 1 |
| S27 | agnes | 118 | 118 | 158 | 2.3046 | 0 |
| S28 | agnes | 105 | 0 | 210 | 0.0815 | 0 |
| S29 | agnes | 123 | 0 | 16 | 0.2271 | 0 |
| S30 | graphic | 154 | 0 | 0 | 184.5729 | 0 |
| S31 | agnes | 162 | 0 | 0 | 0.3254 | 0 |
| S32 | graphic | 129 | 15 | 0 | 237.4285 | 0 |
| S33 | agnes | 119 | 43 | 0 | 1.0384 | 0 |
| S34 | agnes | 122 | 122 | 0 | 0.2717 | 0 |
| S35 | agnes | 92 | 0 | 0 | 0.3115 | 0 |
| S36 | agnes | 73 | 0 | 0 | 0.3826 | 0 |
| S37 | agnes | 116 | 0 | 0 | 0.0776 | 0 |
| S38 | graphic | 133 | 0 | 0 | 198.5583 | 0 |
| S39 | agnes | 134 | 0 | 0 | 0.8482 | 0 |
| S40 | graphic | 106 | 9 | 0 | 200.8552 | 0 |
| S41 | agnes | 140 | 0 | 0 | 0.8215 | 1 |
| S42 | agnes | 87 | 0 | 0 | 0.1401 | 0 |
| S43 | agnes | 130 | 0 | 0 | 0.4748 | 0 |
| S44 | agnes | 110 | 0 | 0 | 0.2061 | 0 |
| S45 | agnes | 155 | 0 | 0 | 0.9058 | 1 |
| END | graphic | 114 | 0 | 0 | 0.6007 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/yangshuming/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/yangshuming/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/yangshuming/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00657_t021.900.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00658_t021.933.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00659_t021.967.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00660_t022.000.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00661_t022.033.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00662_t022.067.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00663_t022.100.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00664_t022.133.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00665_t022.167.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00666_t022.200.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00667_t022.233.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00668_t022.267.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00669_t022.300.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_00670_t022.333.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01194_t039.800.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01195_t039.833.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01196_t039.867.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01197_t039.900.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01198_t039.933.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01199_t039.967.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01200_t040.000.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01201_t040.033.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01202_t040.067.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01203_t040.100.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01204_t040.133.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01215_t040.500.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01216_t040.533.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01217_t040.567.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01218_t040.600.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01219_t040.633.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01220_t040.667.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01221_t040.700.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_01222_t040.733.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_02930_t097.667.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_02931_t097.700.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_02932_t097.733.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_02933_t097.767.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_02934_t097.800.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04792_t159.733.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04793_t159.767.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04794_t159.800.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04795_t159.833.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04796_t159.867.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04797_t159.900.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04798_t159.933.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04799_t159.967.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04800_t160.000.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04801_t160.033.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04802_t160.067.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_04803_t160.100.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/yangshuming/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/yangshuming/final-frame-audit/contacts/hands-S11.jpg`
- 手部动态接触表：`work/yangshuming/final-frame-audit/contacts/hands-S25.jpg`
- 手部动态接触表：`work/yangshuming/final-frame-audit/contacts/hands-S26.jpg`
- 手部动态接触表：`work/yangshuming/final-frame-audit/contacts/hands-S27.jpg`
- 手部动态接触表：`work/yangshuming/final-frame-audit/contacts/hands-S28.jpg`

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
