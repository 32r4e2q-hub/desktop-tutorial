# 成片逐帧畸变 / 时序 QC

- 成片：`玛丽赛勒斯特号_海上最大的未解之谜_三分钟_带声音.mp4`
- SHA-256：`3363842810ec22667788ec363d7ef3f63255ed5ba2c6e8b901b7fa538e7b9e19`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：45（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：42
- >1 秒近静止区段：3；其中非信息卡/片尾段：3
- 帧差/光流/亮度突变待复核窗口：20
- 人脸检测：逐帧总检测 260；达到复核阈值的候选 22
- 手部检测：逐帧总检测 262；超出宽松几何边界的 landmark 事件 146

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 111 | 0 | 0 | 1.3878 | 1 |
| S02 | agnes | 199 | 9 | 0 | 0.5398 | 1 |
| S03 | agnes | 225 | 0 | 0 | 0.7894 | 1 |
| S04 | agnes | 121 | 150 | 88 | 1.7076 | 0 |
| S05B | agnes | 98 | 0 | 0 | 0.3836 | 0 |
| S05A | agnes | 156 | 0 | 0 | 0.5281 | 1 |
| S06 | agnes | 136 | 0 | 0 | 0.9548 | 1 |
| S07A | agnes | 343 | 0 | 68 | 0.755 | 0 |
| S07B | agnes | 96 | 0 | 0 | 2.3555 | 0 |
| S08 | agnes | 108 | 0 | 0 | 0.2257 | 0 |
| S09 | agnes | 67 | 0 | 0 | 0.7836 | 1 |
| S10 | agnes | 51 | 0 | 0 | 1.2789 | 1 |
| S11 | agnes | 83 | 0 | 0 | 0.4282 | 0 |
| S12 | agnes | 205 | 0 | 0 | 0.1765 | 0 |
| S13 | agnes | 252 | 0 | 0 | 0.31 | 0 |
| S15 | agnes | 195 | 0 | 0 | 0.7041 | 0 |
| S14 | agnes | 264 | 0 | 0 | 0.6757 | 1 |
| S16 | agnes | 144 | 0 | 0 | 0.6761 | 1 |
| S17 | agnes | 90 | 0 | 0 | 0.286 | 0 |
| S18A | agnes | 182 | 0 | 0 | 0.4015 | 0 |
| S18B | agnes | 184 | 0 | 85 | 0.5369 | 1 |
| S19 | agnes | 182 | 12 | 0 | 2.749 | 1 |
| S20 | agnes | 289 | 11 | 0 | 0.362 | 1 |
| S21 | agnes | 279 | 0 | 0 | 0.7361 | 1 |
| S22 | agnes | 252 | 0 | 0 | 0.4399 | 1 |
| S23 | agnes | 107 | 0 | 0 | 2.6562 | 1 |
| S24 | agnes | 261 | 0 | 20 | 1.0702 | 0 |
| S25 | agnes | 128 | 0 | 0 | 0.3766 | 0 |
| S26 | agnes | 122 | 0 | 0 | 1.6676 | 1 |
| S27 | agnes | 168 | 0 | 0 | 1.7521 | 1 |
| S28 | agnes | 212 | 78 | 1 | 2.0267 | 2 |
| END | graphic | 90 | 0 | 0 | 0.6636 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/maryceleste1872/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/maryceleste1872/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/maryceleste1872/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00302_t010.067.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00303_t010.100.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00304_t010.133.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00305_t010.167.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00306_t010.200.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00307_t010.233.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00308_t010.267.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00309_t010.300.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00310_t010.333.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00311_t010.367.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00312_t010.400.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00313_t010.433.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00314_t010.467.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00315_t010.500.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00316_t010.533.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00317_t010.567.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00318_t010.600.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00319_t010.633.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00320_t010.667.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00900_t030.000.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00901_t030.033.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00902_t030.067.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00903_t030.100.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00904_t030.133.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00905_t030.167.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00906_t030.200.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00907_t030.233.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00908_t030.267.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00909_t030.300.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00910_t030.333.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00911_t030.367.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00912_t030.400.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00913_t030.433.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00914_t030.467.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00915_t030.500.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00916_t030.533.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00917_t030.567.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00918_t030.600.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_00919_t030.633.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01652_t055.067.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01653_t055.100.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01654_t055.133.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01655_t055.167.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01656_t055.200.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01657_t055.233.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01658_t055.267.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01659_t055.300.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01660_t055.333.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01661_t055.367.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01662_t055.400.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01663_t055.433.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01664_t055.467.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01665_t055.500.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01666_t055.533.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01667_t055.567.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01668_t055.600.jpg', 'work/maryceleste1872/final-frame-audit/suspect-frames/frame_01669_t055.633.jpg']`
- 手部动态接触表：`work/maryceleste1872/final-frame-audit/contacts/hands-S04.jpg`
- 手部动态接触表：`work/maryceleste1872/final-frame-audit/contacts/hands-S07A.jpg`
- 手部动态接触表：`work/maryceleste1872/final-frame-audit/contacts/hands-S18B.jpg`
- 手部动态接触表：`work/maryceleste1872/final-frame-audit/contacts/hands-S24.jpg`

## 限制

自动检测会漏检遮挡、极小目标和模型本身识别不到的 AI 畸变；时序异常也可能是有意运镜、火焰、蒸汽或字幕变化。所以候选必须看原始分辨率前后帧，语义与解剖必须人工目检。没有候选不等于数学上证明‘完美无瑕疵’。

## 全部输出帧的视觉接触表

全片 5400 帧按时间顺序逐帧收录、没有抽样；32 张分镜头接触表，每格 160×90 像素。缩略图用于扫查，异常仍须查看原始分辨率。

- 清单：`../qa/final-frame-review/all-frames/manifest.json`

- [S01](../qa/final-frame-review/all-frames/S01-all-frames.jpg)
- [S02](../qa/final-frame-review/all-frames/S02-all-frames.jpg)
- [S03](../qa/final-frame-review/all-frames/S03-all-frames.jpg)
- [S04](../qa/final-frame-review/all-frames/S04-all-frames.jpg)
- [S05B](../qa/final-frame-review/all-frames/S05B-all-frames.jpg)
- [S05A](../qa/final-frame-review/all-frames/S05A-all-frames.jpg)
- [S06](../qa/final-frame-review/all-frames/S06-all-frames.jpg)
- [S07A](../qa/final-frame-review/all-frames/S07A-all-frames.jpg)
- [S07B](../qa/final-frame-review/all-frames/S07B-all-frames.jpg)
- [S08](../qa/final-frame-review/all-frames/S08-all-frames.jpg)
- [S09](../qa/final-frame-review/all-frames/S09-all-frames.jpg)
- [S10](../qa/final-frame-review/all-frames/S10-all-frames.jpg)
- [S11](../qa/final-frame-review/all-frames/S11-all-frames.jpg)
- [S12](../qa/final-frame-review/all-frames/S12-all-frames.jpg)
- [S13](../qa/final-frame-review/all-frames/S13-all-frames.jpg)
- [S15](../qa/final-frame-review/all-frames/S15-all-frames.jpg)
- [S14](../qa/final-frame-review/all-frames/S14-all-frames.jpg)
- [S16](../qa/final-frame-review/all-frames/S16-all-frames.jpg)
- [S17](../qa/final-frame-review/all-frames/S17-all-frames.jpg)
- [S18A](../qa/final-frame-review/all-frames/S18A-all-frames.jpg)
- [S18B](../qa/final-frame-review/all-frames/S18B-all-frames.jpg)
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
- [END](../qa/final-frame-review/all-frames/END-all-frames.jpg)

人工逐帧视觉复核状态：**PENDING**。自动结果或缩略接触表都不等于无瑕疵。
