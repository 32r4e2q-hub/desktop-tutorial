# 成片逐帧畸变 / 时序 QC

- 成片：`狂犬病疫苗_一百四十年前那场赌局_三分钟_带声音.mp4`
- SHA-256：`4098e8eeb49ba6b124ae9404b6b1e89b24a983b4cc99dc1290d21ec974455bdf`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：14（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：0；其中非信息卡/片尾段：0
- 帧差/光流/亮度突变待复核窗口：8
- 人脸检测：逐帧总检测 270；达到复核阈值的候选 0
- 手部检测：逐帧总检测 544；超出宽松几何边界的 landmark 事件 77

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 116 | 6 | 22 | 2.025 | 0 |
| S02 | agnes | 96 | 0 | 6 | 10.4553 | 0 |
| S03 | agnes | 87 | 26 | 8 | 5.2674 | 1 |
| S04 | agnes | 92 | 0 | 0 | 1.1878 | 0 |
| S05 | agnes | 126 | 0 | 1 | 10.2158 | 0 |
| S06 | agnes | 90 | 4 | 0 | 1.173 | 0 |
| S07 | graphic | 87 | 15 | 0 | 185.5893 | 0 |
| S08 | agnes | 125 | 0 | 0 | 1.3268 | 0 |
| S09 | agnes | 120 | 0 | 0 | 1.0138 | 0 |
| S10 | agnes | 159 | 47 | 62 | 1.4414 | 0 |
| S11 | agnes | 155 | 27 | 0 | 1.6766 | 0 |
| S12 | agnes | 85 | 2 | 0 | 2.0076 | 0 |
| S13 | graphic | 153 | 0 | 0 | 192.7184 | 0 |
| S14 | agnes | 137 | 5 | 3 | 2.2072 | 0 |
| S15 | agnes | 167 | 0 | 0 | 1.0083 | 0 |
| S16 | agnes | 75 | 0 | 0 | 1.4405 | 0 |
| S17 | agnes | 165 | 0 | 17 | 0.8351 | 0 |
| S18 | agnes | 127 | 7 | 118 | 2.1774 | 0 |
| S19 | agnes | 134 | 8 | 0 | 1.9108 | 0 |
| S20 | agnes | 167 | 0 | 0 | 0.6622 | 0 |
| S21 | graphic | 78 | 0 | 0 | 125.4908 | 0 |
| S22 | agnes | 141 | 0 | 0 | 1.7337 | 0 |
| S23 | agnes | 124 | 5 | 9 | 2.9 | 0 |
| S24 | agnes | 119 | 0 | 0 | 2.2976 | 0 |
| S25 | agnes | 97 | 0 | 0 | 1.1075 | 0 |
| S26 | agnes | 71 | 0 | 2 | 0.8954 | 0 |
| S27 | agnes | 153 | 3 | 13 | 1.9501 | 0 |
| S28 | graphic | 94 | 0 | 0 | 150.9708 | 0 |
| S29 | agnes | 98 | 0 | 0 | 0.4103 | 0 |
| S30 | agnes | 148 | 7 | 201 | 3.0666 | 0 |
| S31 | agnes | 109 | 5 | 0 | 0.5891 | 0 |
| S32 | agnes | 101 | 1 | 0 | 2.3106 | 0 |
| S33 | agnes | 75 | 0 | 0 | 1.087 | 0 |
| S34 | graphic | 122 | 0 | 0 | 185.319 | 0 |
| S35 | agnes | 132 | 0 | 0 | 0.8259 | 0 |
| S36 | agnes | 65 | 3 | 0 | 0.534 | 0 |
| S37 | agnes | 123 | 0 | 0 | 3.95 | 4 |
| S38 | graphic | 114 | 22 | 0 | 262.7062 | 0 |
| S39 | agnes | 145 | 67 | 34 | 3.8824 | 0 |
| S40 | agnes | 54 | 0 | 0 | 0.9798 | 0 |
| S41 | agnes | 103 | 10 | 0 | 0.791 | 0 |
| S42 | graphic | 158 | 0 | 0 | 242.9201 | 0 |
| S43 | agnes | 78 | 0 | 0 | 1.49 | 0 |
| S44 | agnes | 172 | 0 | 48 | 4.2774 | 1 |
| S45 | agnes | 149 | 0 | 0 | 23.4977 | 1 |
| END | graphic | 114 | 0 | 0 | 0.6592 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/rabies1885/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/rabies1885/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/rabies1885/final-frame-audit/suspect-frames/frame_00213_t007.100.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_00214_t007.133.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_00215_t007.167.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_00216_t007.200.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_00217_t007.233.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_00218_t007.267.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_00219_t007.300.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_00220_t007.333.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04209_t140.300.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04210_t140.333.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04211_t140.367.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04212_t140.400.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04213_t140.433.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04239_t141.300.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04240_t141.333.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04241_t141.367.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04242_t141.400.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04243_t141.433.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04269_t142.300.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04270_t142.333.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04271_t142.367.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04272_t142.400.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04273_t142.433.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04299_t143.300.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04300_t143.333.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04301_t143.367.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04302_t143.400.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04303_t143.433.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04968_t165.600.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04969_t165.633.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04970_t165.667.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04971_t165.700.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04972_t165.733.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04973_t165.767.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04974_t165.800.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04975_t165.833.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04976_t165.867.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04977_t165.900.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04978_t165.933.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04979_t165.967.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04980_t166.000.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04981_t166.033.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04982_t166.067.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04983_t166.100.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04984_t166.133.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04985_t166.167.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04986_t166.200.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04987_t166.233.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04988_t166.267.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04989_t166.300.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04990_t166.333.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04991_t166.367.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04992_t166.400.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04993_t166.433.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04994_t166.467.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04995_t166.500.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04996_t166.533.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04997_t166.567.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04998_t166.600.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_04999_t166.633.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_05000_t166.667.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_05001_t166.700.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_05002_t166.733.jpg', 'work/rabies1885/final-frame-audit/suspect-frames/frame_05003_t166.767.jpg']`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S01.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S02.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S03.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S10.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S17.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S18.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S23.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S27.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S30.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S39.jpg`
- 手部动态接触表：`work/rabies1885/final-frame-audit/contacts/hands-S44.jpg`

## 限制

自动检测会漏检遮挡、极小目标和模型本身识别不到的 AI 畸变；时序异常也可能是有意运镜、火焰、蒸汽或字幕变化。所以候选必须看原始分辨率前后帧，语义与解剖必须人工目检。没有候选不等于数学上证明‘完美无瑕疵’。

## 全部输出帧的视觉接触表

全片 5400 帧按时间顺序逐帧收录、没有抽样；46 张分镜头接触表，每格 160×90 像素。缩略图用于扫查，异常仍须查看原始分辨率。

- 清单：`../qa/all-frames/manifest.json`

- [S01](../qa/all-frames/S01-all-frames.jpg)
- [S02](../qa/all-frames/S02-all-frames.jpg)
- [S03](../qa/all-frames/S03-all-frames.jpg)
- [S04](../qa/all-frames/S04-all-frames.jpg)
- [S05](../qa/all-frames/S05-all-frames.jpg)
- [S06](../qa/all-frames/S06-all-frames.jpg)
- [S07](../qa/all-frames/S07-all-frames.jpg)
- [S08](../qa/all-frames/S08-all-frames.jpg)
- [S09](../qa/all-frames/S09-all-frames.jpg)
- [S10](../qa/all-frames/S10-all-frames.jpg)
- [S11](../qa/all-frames/S11-all-frames.jpg)
- [S12](../qa/all-frames/S12-all-frames.jpg)
- [S13](../qa/all-frames/S13-all-frames.jpg)
- [S14](../qa/all-frames/S14-all-frames.jpg)
- [S15](../qa/all-frames/S15-all-frames.jpg)
- [S16](../qa/all-frames/S16-all-frames.jpg)
- [S17](../qa/all-frames/S17-all-frames.jpg)
- [S18](../qa/all-frames/S18-all-frames.jpg)
- [S19](../qa/all-frames/S19-all-frames.jpg)
- [S20](../qa/all-frames/S20-all-frames.jpg)
- [S21](../qa/all-frames/S21-all-frames.jpg)
- [S22](../qa/all-frames/S22-all-frames.jpg)
- [S23](../qa/all-frames/S23-all-frames.jpg)
- [S24](../qa/all-frames/S24-all-frames.jpg)
- [S25](../qa/all-frames/S25-all-frames.jpg)
- [S26](../qa/all-frames/S26-all-frames.jpg)
- [S27](../qa/all-frames/S27-all-frames.jpg)
- [S28](../qa/all-frames/S28-all-frames.jpg)
- [S29](../qa/all-frames/S29-all-frames.jpg)
- [S30](../qa/all-frames/S30-all-frames.jpg)
- [S31](../qa/all-frames/S31-all-frames.jpg)
- [S32](../qa/all-frames/S32-all-frames.jpg)
- [S33](../qa/all-frames/S33-all-frames.jpg)
- [S34](../qa/all-frames/S34-all-frames.jpg)
- [S35](../qa/all-frames/S35-all-frames.jpg)
- [S36](../qa/all-frames/S36-all-frames.jpg)
- [S37](../qa/all-frames/S37-all-frames.jpg)
- [S38](../qa/all-frames/S38-all-frames.jpg)
- [S39](../qa/all-frames/S39-all-frames.jpg)
- [S40](../qa/all-frames/S40-all-frames.jpg)
- [S41](../qa/all-frames/S41-all-frames.jpg)
- [S42](../qa/all-frames/S42-all-frames.jpg)
- [S43](../qa/all-frames/S43-all-frames.jpg)
- [S44](../qa/all-frames/S44-all-frames.jpg)
- [S45](../qa/all-frames/S45-all-frames.jpg)
- [END](../qa/all-frames/END-all-frames.jpg)

人工逐帧视觉复核状态：**PENDING**。自动结果或缩略接触表都不等于无瑕疵。
