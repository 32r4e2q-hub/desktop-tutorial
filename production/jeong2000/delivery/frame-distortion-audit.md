# 成片逐帧畸变 / 时序 QC

- 成片：`郑斗英_十个月，九条人命_三分钟_带声音.mp4`
- SHA-256：`0b0ee6417a70d319613578c7cecbf6de6207834b72e894ca4132d964f0d8fd31`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：13（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：1；其中非信息卡/片尾段：1
- 帧差/光流/亮度突变待复核窗口：5
- 人脸检测：逐帧总检测 298；达到复核阈值的候选 0
- 手部检测：逐帧总检测 592；超出宽松几何边界的 landmark 事件 469

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | cogvideo | 90 | 0 | 0 | 0.5783 | 1 |
| S02 | cogvideo | 81 | 0 | 0 | 0.7067 | 0 |
| S03 | graphic | 117 | 15 | 0 | 217.8736 | 0 |
| S04 | cogvideo | 143 | 19 | 0 | 0.0861 | 0 |
| S05 | cogvideo | 89 | 0 | 0 | 0.7387 | 0 |
| S06 | cogvideo | 70 | 6 | 0 | 0.6799 | 0 |
| S07 | cogvideo | 83 | 0 | 0 | 0.0983 | 0 |
| S08 | cogvideo | 145 | 46 | 0 | 0.3194 | 0 |
| S09 | cogvideo | 114 | 0 | 0 | 0.3945 | 0 |
| S10 | graphic | 122 | 35 | 0 | 167.1173 | 0 |
| S11 | cogvideo | 106 | 0 | 0 | 1.9386 | 0 |
| S12 | cogvideo | 144 | 0 | 0 | 0.1411 | 0 |
| S13 | cogvideo | 84 | 0 | 67 | 0.6402 | 0 |
| S14 | cogvideo | 151 | 0 | 0 | 0.0887 | 0 |
| S15 | cogvideo | 132 | 0 | 0 | 0.1401 | 0 |
| S16 | cogvideo | 112 | 0 | 0 | 0.3709 | 0 |
| S17 | graphic | 152 | 26 | 0 | 224.6343 | 0 |
| S18 | cogvideo | 129 | 0 | 0 | 0.1493 | 0 |
| S19 | cogvideo | 134 | 0 | 0 | 2.8061 | 2 |
| S20 | cogvideo | 52 | 0 | 0 | 0.1451 | 0 |
| S21 | cogvideo | 102 | 63 | 0 | 0.1823 | 0 |
| S22 | cogvideo | 106 | 0 | 155 | 0.1526 | 0 |
| S23 | cogvideo | 141 | 0 | 0 | 0.0814 | 0 |
| S24 | graphic | 108 | 0 | 0 | 163.8131 | 0 |
| S25 | cogvideo | 83 | 0 | 0 | 0.1927 | 0 |
| S26 | cogvideo | 103 | 0 | 0 | 0.2194 | 0 |
| S27 | cogvideo | 117 | 0 | 0 | 0.0232 | 0 |
| S28 | cogvideo | 128 | 0 | 0 | 0.2293 | 0 |
| S29 | cogvideo | 162 | 0 | 0 | 0.134 | 0 |
| S30 | cogvideo | 148 | 12 | 0 | 1.7525 | 0 |
| S31 | graphic | 128 | 55 | 0 | 185.9277 | 0 |
| S32 | cogvideo | 155 | 0 | 0 | 0.1002 | 0 |
| S33 | cogvideo | 126 | 0 | 370 | 0.1829 | 0 |
| S34 | cogvideo | 67 | 0 | 0 | 0.5619 | 0 |
| S35 | cogvideo | 73 | 0 | 0 | 0.1113 | 0 |
| S36 | cogvideo | 85 | 0 | 0 | 0.4406 | 0 |
| S37 | cogvideo | 80 | 0 | 0 | 0.0796 | 0 |
| S38 | graphic | 154 | 5 | 0 | 233.2553 | 0 |
| S39 | cogvideo | 118 | 0 | 0 | 0.0967 | 0 |
| S40 | cogvideo | 94 | 0 | 0 | 0.1704 | 0 |
| S41 | cogvideo | 96 | 0 | 0 | 0.0877 | 0 |
| S42 | cogvideo | 171 | 0 | 0 | 0.495 | 0 |
| S43 | graphic | 179 | 16 | 0 | 202.4218 | 0 |
| S44 | cogvideo | 142 | 0 | 0 | 0.1495 | 0 |
| S45 | cogvideo | 170 | 0 | 0 | 0.5692 | 1 |
| END | graphic | 114 | 0 | 0 | 0.5692 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/jeong2000/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/jeong2000/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/jeong2000/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01354_t045.133.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01355_t045.167.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01356_t045.200.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01357_t045.233.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01358_t045.267.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01359_t045.300.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01360_t045.333.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01361_t045.367.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01362_t045.400.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01363_t045.433.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01364_t045.467.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01365_t045.500.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01366_t045.533.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01367_t045.567.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01368_t045.600.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01369_t045.633.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01370_t045.667.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_01371_t045.700.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02176_t072.533.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02177_t072.567.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02178_t072.600.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02179_t072.633.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02180_t072.667.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02181_t072.700.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02182_t072.733.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02183_t072.767.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02184_t072.800.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02350_t078.333.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02351_t078.367.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02352_t078.400.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02353_t078.433.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02354_t078.467.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02355_t078.500.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02356_t078.533.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02357_t078.567.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02358_t078.600.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02359_t078.633.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02360_t078.667.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02361_t078.700.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02362_t078.733.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02363_t078.767.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/jeong2000/final-frame-audit/contacts/hands-S13.jpg`
- 手部动态接触表：`work/jeong2000/final-frame-audit/contacts/hands-S22.jpg`
- 手部动态接触表：`work/jeong2000/final-frame-audit/contacts/hands-S33.jpg`

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
