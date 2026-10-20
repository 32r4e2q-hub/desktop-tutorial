# 成片逐帧畸变 / 时序 QC

- 成片：`周克华案_逃亡八年，最后四天_三分钟_带声音.mp4`
- SHA-256：`eb0c1a97f6a1c6b78e91108dc76c2b91b09d4d34f5225fc6b34fb34b320d5831`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：16（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：1；其中非信息卡/片尾段：1
- 帧差/光流/亮度突变待复核窗口：2
- 人脸检测：逐帧总检测 109；达到复核阈值的候选 0
- 手部检测：逐帧总检测 0；超出宽松几何边界的 landmark 事件 0

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 92 | 0 | 0 | 0.6487 | 1 |
| S03 | agnes | 90 | 0 | 0 | 0.2071 | 0 |
| S06 | agnes | 132 | 0 | 0 | 1.6667 | 0 |
| S02 | graphic | 118 | 0 | 0 | 64.2582 | 0 |
| S05 | agnes | 97 | 0 | 0 | 0.9287 | 0 |
| S07 | agnes | 111 | 0 | 0 | 0.1106 | 0 |
| S08 | agnes | 159 | 0 | 0 | 0.1641 | 0 |
| S09 | graphic | 155 | 0 | 0 | 113.3289 | 0 |
| S10 | agnes | 205 | 0 | 0 | 0.2427 | 0 |
| S12 | agnes | 49 | 45 | 0 | 0.2728 | 0 |
| S11 | agnes | 157 | 0 | 0 | 0.2674 | 0 |
| S13 | agnes | 112 | 0 | 0 | 0.1416 | 0 |
| S14 | agnes | 150 | 0 | 0 | 1.2613 | 0 |
| S15 | agnes | 215 | 0 | 0 | 0.3236 | 0 |
| S20 | agnes | 134 | 0 | 0 | 0.1193 | 0 |
| S17 | agnes | 152 | 0 | 0 | 0.7211 | 0 |
| S23 | agnes | 68 | 0 | 0 | 0.0533 | 0 |
| S18 | agnes | 135 | 0 | 0 | 0.2611 | 0 |
| S19 | agnes | 142 | 0 | 0 | 0.2938 | 0 |
| S22 | graphic | 63 | 5 | 0 | 56.6816 | 0 |
| S21 | agnes | 53 | 1 | 0 | 0.4872 | 0 |
| S16 | graphic | 131 | 58 | 0 | 193.0983 | 0 |
| S24 | agnes | 113 | 0 | 0 | 2.3691 | 0 |
| S04 | agnes | 174 | 0 | 0 | 0.3288 | 0 |
| S25 | graphic | 78 | 0 | 0 | 160.4097 | 0 |
| S26 | agnes | 123 | 0 | 0 | 0.3266 | 0 |
| S27 | agnes | 92 | 0 | 0 | 0.5156 | 0 |
| S29 | agnes | 60 | 0 | 0 | 0.0724 | 0 |
| S28 | agnes | 157 | 0 | 0 | 0.165 | 0 |
| S30 | agnes | 99 | 0 | 0 | 0.0931 | 0 |
| S32 | agnes | 166 | 0 | 0 | 0.5941 | 0 |
| S33 | graphic | 83 | 0 | 0 | 62.0863 | 0 |
| S34 | agnes | 168 | 0 | 0 | 0.2946 | 0 |
| S35 | agnes | 84 | 0 | 0 | 0.1124 | 0 |
| S36 | agnes | 70 | 0 | 0 | 0.6144 | 0 |
| S37 | agnes | 92 | 0 | 0 | 0.1134 | 0 |
| S31 | agnes | 99 | 0 | 0 | 0.1271 | 0 |
| S38 | agnes | 156 | 0 | 0 | 0.1579 | 0 |
| S40 | graphic | 122 | 0 | 0 | 191.1133 | 0 |
| S43 | agnes | 58 | 0 | 0 | 0.628 | 0 |
| S46 | agnes | 98 | 0 | 0 | 0.1932 | 0 |
| S42 | agnes | 47 | 0 | 0 | 0.0702 | 0 |
| S41 | agnes | 85 | 0 | 0 | 0.1033 | 0 |
| S39 | agnes | 52 | 0 | 0 | 0.352 | 0 |
| S44 | agnes | 143 | 0 | 0 | 0.1888 | 0 |
| S45 | agnes | 147 | 0 | 0 | 0.4773 | 1 |
| END | graphic | 114 | 0 | 0 | 0.3478 | 0 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/zhoukehua2012/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/zhoukehua2012/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05269_t175.633.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05270_t175.667.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05271_t175.700.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05272_t175.733.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05273_t175.767.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05274_t175.800.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05275_t175.833.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05276_t175.867.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05277_t175.900.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05278_t175.933.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05279_t175.967.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg']`

## 限制

自动检测会漏检遮挡、极小目标和模型本身识别不到的 AI 畸变；时序异常也可能是有意运镜、火焰、蒸汽或字幕变化。所以候选必须看原始分辨率前后帧，语义与解剖必须人工目检。没有候选不等于数学上证明‘完美无瑕疵’。

## 全部输出帧的视觉接触表

全片 5400 帧按时间顺序逐帧收录、没有抽样；47 张分镜头接触表，每格 160×90 像素。缩略图用于扫查，异常仍须查看原始分辨率。

- 清单：`../qa/final-frame-review/all-frames/manifest.json`

- [S01](../qa/final-frame-review/all-frames/S01-all-frames.jpg)
- [S03](../qa/final-frame-review/all-frames/S03-all-frames.jpg)
- [S06](../qa/final-frame-review/all-frames/S06-all-frames.jpg)
- [S02](../qa/final-frame-review/all-frames/S02-all-frames.jpg)
- [S05](../qa/final-frame-review/all-frames/S05-all-frames.jpg)
- [S07](../qa/final-frame-review/all-frames/S07-all-frames.jpg)
- [S08](../qa/final-frame-review/all-frames/S08-all-frames.jpg)
- [S09](../qa/final-frame-review/all-frames/S09-all-frames.jpg)
- [S10](../qa/final-frame-review/all-frames/S10-all-frames.jpg)
- [S12](../qa/final-frame-review/all-frames/S12-all-frames.jpg)
- [S11](../qa/final-frame-review/all-frames/S11-all-frames.jpg)
- [S13](../qa/final-frame-review/all-frames/S13-all-frames.jpg)
- [S14](../qa/final-frame-review/all-frames/S14-all-frames.jpg)
- [S15](../qa/final-frame-review/all-frames/S15-all-frames.jpg)
- [S20](../qa/final-frame-review/all-frames/S20-all-frames.jpg)
- [S17](../qa/final-frame-review/all-frames/S17-all-frames.jpg)
- [S23](../qa/final-frame-review/all-frames/S23-all-frames.jpg)
- [S18](../qa/final-frame-review/all-frames/S18-all-frames.jpg)
- [S19](../qa/final-frame-review/all-frames/S19-all-frames.jpg)
- [S22](../qa/final-frame-review/all-frames/S22-all-frames.jpg)
- [S21](../qa/final-frame-review/all-frames/S21-all-frames.jpg)
- [S16](../qa/final-frame-review/all-frames/S16-all-frames.jpg)
- [S24](../qa/final-frame-review/all-frames/S24-all-frames.jpg)
- [S04](../qa/final-frame-review/all-frames/S04-all-frames.jpg)
- [S25](../qa/final-frame-review/all-frames/S25-all-frames.jpg)
- [S26](../qa/final-frame-review/all-frames/S26-all-frames.jpg)
- [S27](../qa/final-frame-review/all-frames/S27-all-frames.jpg)
- [S29](../qa/final-frame-review/all-frames/S29-all-frames.jpg)
- [S28](../qa/final-frame-review/all-frames/S28-all-frames.jpg)
- [S30](../qa/final-frame-review/all-frames/S30-all-frames.jpg)
- [S32](../qa/final-frame-review/all-frames/S32-all-frames.jpg)
- [S33](../qa/final-frame-review/all-frames/S33-all-frames.jpg)
- [S34](../qa/final-frame-review/all-frames/S34-all-frames.jpg)
- [S35](../qa/final-frame-review/all-frames/S35-all-frames.jpg)
- [S36](../qa/final-frame-review/all-frames/S36-all-frames.jpg)
- [S37](../qa/final-frame-review/all-frames/S37-all-frames.jpg)
- [S31](../qa/final-frame-review/all-frames/S31-all-frames.jpg)
- [S38](../qa/final-frame-review/all-frames/S38-all-frames.jpg)
- [S40](../qa/final-frame-review/all-frames/S40-all-frames.jpg)
- [S43](../qa/final-frame-review/all-frames/S43-all-frames.jpg)
- [S46](../qa/final-frame-review/all-frames/S46-all-frames.jpg)
- [S42](../qa/final-frame-review/all-frames/S42-all-frames.jpg)
- [S41](../qa/final-frame-review/all-frames/S41-all-frames.jpg)
- [S39](../qa/final-frame-review/all-frames/S39-all-frames.jpg)
- [S44](../qa/final-frame-review/all-frames/S44-all-frames.jpg)
- [S45](../qa/final-frame-review/all-frames/S45-all-frames.jpg)
- [END](../qa/final-frame-review/all-frames/END-all-frames.jpg)

人工逐帧视觉复核状态：**PENDING**。自动结果或缩略接触表都不等于无瑕疵。
