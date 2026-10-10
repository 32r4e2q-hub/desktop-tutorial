# 成片逐帧畸变 / 时序 QC

- 成片：`郑斗英_十个月，九条人命_三分钟_带声音.mp4`
- SHA-256：`95f154a2db18754a9204189d93d3714a82e7d6f01c6c8fd0c9a8309b13b7d992`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：13（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：0；其中非信息卡/片尾段：0
- 帧差/光流/亮度突变待复核窗口：4
- 人脸检测：逐帧总检测 246；达到复核阈值的候选 0
- 手部检测：逐帧总检测 0；超出宽松几何边界的 landmark 事件 0

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | cogvideo | 90 | 0 | 0 | 0.6331 | 1 |
| S02 | cogvideo | 81 | 0 | 0 | 0.7997 | 0 |
| S03 | graphic | 117 | 15 | 0 | 183.9499 | 0 |
| S04 | cogvideo | 143 | 0 | 0 | 0.1005 | 0 |
| S05 | cogvideo | 89 | 0 | 0 | 0.8713 | 0 |
| S06 | cogvideo | 70 | 0 | 0 | 0.1231 | 0 |
| S07 | cogvideo | 83 | 0 | 0 | 0.0999 | 0 |
| S08 | cogvideo | 145 | 9 | 0 | 0.279 | 0 |
| S09 | cogvideo | 114 | 0 | 0 | 0.3468 | 0 |
| S10 | graphic | 122 | 35 | 0 | 188.8312 | 0 |
| S11 | cogvideo | 106 | 0 | 0 | 0.2652 | 0 |
| S12 | cogvideo | 144 | 0 | 0 | 0.1345 | 0 |
| S13 | cogvideo | 84 | 0 | 0 | 0.126 | 0 |
| S14 | cogvideo | 151 | 0 | 0 | 0.1044 | 0 |
| S15 | cogvideo | 132 | 0 | 0 | 0.1725 | 0 |
| S16 | cogvideo | 112 | 0 | 0 | 0.3646 | 0 |
| S17 | graphic | 152 | 28 | 0 | 185.2336 | 0 |
| S18 | cogvideo | 129 | 0 | 0 | 0.1746 | 0 |
| S19 | cogvideo | 134 | 0 | 0 | 3.409 | 1 |
| S20 | cogvideo | 52 | 0 | 0 | 0.1639 | 0 |
| S21 | cogvideo | 102 | 65 | 0 | 0.194 | 0 |
| S22 | cogvideo | 106 | 0 | 0 | 0.3994 | 0 |
| S23 | cogvideo | 141 | 0 | 0 | 0.1001 | 0 |
| S24 | graphic | 108 | 0 | 0 | 200.3315 | 0 |
| S25 | cogvideo | 83 | 0 | 0 | 0.2515 | 0 |
| S26 | cogvideo | 103 | 0 | 0 | 0.2799 | 0 |
| S27 | cogvideo | 117 | 0 | 0 | 0.0157 | 0 |
| S28 | cogvideo | 128 | 0 | 0 | 0.1276 | 0 |
| S29 | cogvideo | 162 | 20 | 0 | 0.1121 | 0 |
| S30 | cogvideo | 148 | 0 | 0 | 1.7181 | 0 |
| S31 | graphic | 128 | 53 | 0 | 185.0901 | 0 |
| S32 | cogvideo | 155 | 0 | 0 | 0.0978 | 0 |
| S33 | cogvideo | 126 | 0 | 0 | 0.0898 | 0 |
| S34 | cogvideo | 67 | 0 | 0 | 0.111 | 0 |
| S35 | cogvideo | 73 | 0 | 0 | 0.0718 | 0 |
| S36 | cogvideo | 85 | 0 | 0 | 0.3647 | 0 |
| S37 | cogvideo | 80 | 0 | 0 | 0.0807 | 0 |
| S38 | graphic | 154 | 5 | 0 | 260.1127 | 0 |
| S39 | cogvideo | 118 | 0 | 0 | 0.096 | 0 |
| S40 | cogvideo | 94 | 0 | 0 | 0.208 | 0 |
| S41 | cogvideo | 96 | 0 | 0 | 0.0901 | 0 |
| S42 | cogvideo | 171 | 0 | 0 | 0.5665 | 0 |
| S43 | graphic | 179 | 16 | 0 | 173.6128 | 0 |
| S44 | cogvideo | 142 | 0 | 0 | 0.1584 | 0 |
| S45 | cogvideo | 170 | 0 | 0 | 0.4315 | 1 |
| END | graphic | 114 | 0 | 0 | 0.5692 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/jeong2000/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/jeong2000/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/jeong2000/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02176_t072.533.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02177_t072.567.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02178_t072.600.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02179_t072.633.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02180_t072.667.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02181_t072.700.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02182_t072.733.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02183_t072.767.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_02184_t072.800.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`

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
