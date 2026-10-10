# 成片逐帧畸变 / 时序 QC

- 成片：`郑斗英_十个月，九条人命_三分钟_带声音.mp4`
- SHA-256：`0b1f5be395f594addf0bcb5ed8e80fc69809337cca5a119d6914849f4f91c21c`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：13（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：0；其中非信息卡/片尾段：0
- 帧差/光流/亮度突变待复核窗口：4
- 人脸检测：逐帧总检测 242；达到复核阈值的候选 0
- 手部检测：逐帧总检测 0；超出宽松几何边界的 landmark 事件 0

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | cogvideo | 90 | 0 | 0 | 0.6343 | 1 |
| S02 | cogvideo | 81 | 0 | 0 | 0.7943 | 0 |
| S03 | graphic | 117 | 15 | 0 | 236.5465 | 0 |
| S04 | cogvideo | 143 | 0 | 0 | 0.0987 | 0 |
| S05 | cogvideo | 89 | 0 | 0 | 0.8714 | 0 |
| S06 | cogvideo | 70 | 0 | 0 | 0.1291 | 0 |
| S07 | cogvideo | 83 | 0 | 0 | 0.102 | 0 |
| S08 | cogvideo | 145 | 6 | 0 | 0.2798 | 0 |
| S09 | cogvideo | 114 | 0 | 0 | 0.3582 | 0 |
| S10 | graphic | 122 | 35 | 0 | 175.034 | 0 |
| S11 | cogvideo | 106 | 0 | 0 | 0.2644 | 0 |
| S12 | cogvideo | 144 | 0 | 0 | 0.1344 | 0 |
| S13 | cogvideo | 84 | 2 | 0 | 0.2472 | 0 |
| S14 | cogvideo | 151 | 0 | 0 | 0.1043 | 0 |
| S15 | cogvideo | 132 | 0 | 0 | 0.1731 | 0 |
| S16 | cogvideo | 112 | 0 | 0 | 0.3591 | 0 |
| S17 | graphic | 152 | 26 | 0 | 232.2788 | 0 |
| S18 | cogvideo | 129 | 0 | 0 | 0.1642 | 0 |
| S19 | cogvideo | 134 | 0 | 0 | 0.5916 | 0 |
| S20 | cogvideo | 52 | 0 | 0 | 0.1684 | 0 |
| S21 | cogvideo | 102 | 69 | 0 | 0.1956 | 0 |
| S22 | cogvideo | 106 | 0 | 0 | 0.3922 | 0 |
| S23 | cogvideo | 141 | 0 | 0 | 0.095 | 0 |
| S24 | graphic | 108 | 0 | 0 | 167.9649 | 0 |
| S25 | cogvideo | 83 | 0 | 0 | 0.2518 | 0 |
| S26 | cogvideo | 103 | 0 | 0 | 0.2799 | 0 |
| S27 | cogvideo | 117 | 0 | 0 | 0.0158 | 0 |
| S28 | cogvideo | 128 | 0 | 0 | 0.1377 | 0 |
| S29 | cogvideo | 162 | 13 | 0 | 0.1165 | 0 |
| S30 | cogvideo | 148 | 0 | 0 | 1.7253 | 0 |
| S31 | graphic | 128 | 55 | 0 | 263.6932 | 1 |
| S32 | cogvideo | 155 | 0 | 0 | 0.0949 | 0 |
| S33 | cogvideo | 126 | 0 | 0 | 0.0983 | 0 |
| S34 | cogvideo | 67 | 0 | 0 | 0.111 | 0 |
| S35 | cogvideo | 73 | 0 | 0 | 0.0678 | 0 |
| S36 | cogvideo | 85 | 0 | 0 | 0.3766 | 0 |
| S37 | cogvideo | 80 | 0 | 0 | 0.0807 | 0 |
| S38 | graphic | 154 | 5 | 0 | 213.2492 | 0 |
| S39 | cogvideo | 118 | 0 | 0 | 0.096 | 0 |
| S40 | cogvideo | 94 | 0 | 0 | 0.1974 | 0 |
| S41 | cogvideo | 96 | 0 | 0 | 0.0896 | 0 |
| S42 | cogvideo | 171 | 0 | 0 | 0.5669 | 0 |
| S43 | graphic | 179 | 16 | 0 | 187.225 | 0 |
| S44 | cogvideo | 142 | 0 | 0 | 0.1623 | 0 |
| S45 | cogvideo | 170 | 0 | 0 | 0.4347 | 1 |
| END | graphic | 114 | 0 | 0 | 0.5692 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/jeong2000/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/jeong2000/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/jeong2000/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_03539_t117.967.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_03540_t118.000.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_03541_t118.033.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_03542_t118.067.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_03543_t118.100.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/jeong2000/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`

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
