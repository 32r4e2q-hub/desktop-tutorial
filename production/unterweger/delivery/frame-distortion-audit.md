# 成片逐帧畸变 / 时序 QC

- 成片：`杰克·翁特维格_最成功的一次伪装_三分钟_带声音.mp4`
- SHA-256：`c8fdb2af709a917cbe5cccbf0ee10512d44ab8d16a3bb840330d725d6f04646d`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：592（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：577
- >1 秒近静止区段：0；其中非信息卡/片尾段：0
- 帧差/光流/亮度突变待复核窗口：3
- 人脸检测：逐帧总检测 1839；达到复核阈值的候选 1057
- 手部检测：逐帧总检测 1686；超出宽松几何边界的 landmark 事件 151

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 92 | 0 | 0 | 0.9626 | 0 |
| S02 | graphic | 128 | 0 | 0 | 185.9331 | 0 |
| S03 | agnes | 117 | 0 | 6 | 0.9509 | 0 |
| S04 | agnes | 54 | 3 | 0 | 1.2408 | 0 |
| S05 | agnes | 115 | 70 | 26 | 2.3989 | 0 |
| S06 | agnes | 75 | 0 | 0 | 0.4358 | 0 |
| S07 | agnes | 95 | 95 | 0 | 1.357 | 0 |
| S08 | agnes | 157 | 0 | 0 | 0.416 | 0 |
| S09 | agnes | 82 | 6 | 0 | 0.9408 | 0 |
| S10 | agnes | 99 | 3 | 0 | 0.7163 | 0 |
| S11 | graphic | 171 | 3 | 0 | 239.833 | 0 |
| S12 | agnes | 73 | 53 | 0 | 2.5078 | 0 |
| S13 | agnes | 142 | 142 | 49 | 0.6611 | 0 |
| S14 | agnes | 111 | 0 | 0 | 0.9821 | 0 |
| S15 | agnes | 109 | 0 | 0 | 1.7152 | 0 |
| S16 | agnes | 113 | 113 | 113 | 0.8184 | 0 |
| S17 | agnes | 110 | 0 | 0 | 0.938 | 0 |
| S18 | graphic | 90 | 0 | 0 | 107.1312 | 0 |
| S19 | agnes | 138 | 111 | 140 | 2.5959 | 0 |
| S20 | agnes | 96 | 0 | 124 | 0.538 | 0 |
| S21 | agnes | 101 | 101 | 34 | 1.6403 | 0 |
| S22 | agnes | 149 | 149 | 216 | 1.2917 | 0 |
| S23 | agnes | 123 | 0 | 33 | 4.0958 | 0 |
| S24 | graphic | 178 | 0 | 0 | 216.5232 | 0 |
| S25 | agnes | 67 | 67 | 0 | 3.8935 | 1 |
| S26 | agnes | 163 | 0 | 0 | 0.3887 | 0 |
| S27 | agnes | 125 | 49 | 120 | 0.5515 | 0 |
| S28 | agnes | 160 | 91 | 131 | 3.1268 | 0 |
| S29 | agnes | 121 | 0 | 0 | 0.2902 | 0 |
| S30 | agnes | 171 | 113 | 10 | 1.8216 | 0 |
| S31 | graphic | 65 | 34 | 0 | 157.6692 | 0 |
| S32 | agnes | 103 | 0 | 146 | 0.6918 | 0 |
| S33 | agnes | 150 | 110 | 0 | 1.7066 | 0 |
| S34 | agnes | 81 | 47 | 0 | 0.5251 | 0 |
| S35 | agnes | 105 | 0 | 0 | 0.9992 | 0 |
| S36 | agnes | 87 | 87 | 82 | 0.8739 | 0 |
| S37 | graphic | 68 | 27 | 0 | 171.173 | 0 |
| S38 | agnes | 162 | 142 | 262 | 1.2428 | 0 |
| S39 | agnes | 126 | 21 | 15 | 1.5723 | 0 |
| S40 | graphic | 139 | 36 | 0 | 243.4859 | 0 |
| S41 | graphic | 85 | 34 | 0 | 181.8164 | 0 |
| S42 | agnes | 118 | 0 | 0 | 0.5613 | 0 |
| S43 | agnes | 132 | 132 | 179 | 0.9954 | 0 |
| S44 | agnes | 141 | 0 | 0 | 0.6956 | 0 |
| S45 | agnes | 199 | 0 | 0 | 0.8492 | 1 |
| END | graphic | 114 | 0 | 0 | 0.4257 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/unterweger/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/unterweger/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/unterweger/final-frame-audit/suspect-frames/frame_00409_t013.633.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00410_t013.667.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00411_t013.700.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00412_t013.733.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00413_t013.767.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00414_t013.800.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00415_t013.833.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00416_t013.867.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00417_t013.900.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00418_t013.933.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00419_t013.967.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00420_t014.000.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00421_t014.033.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00422_t014.067.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00423_t014.100.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00424_t014.133.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00425_t014.167.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00457_t015.233.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00458_t015.267.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00459_t015.300.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00460_t015.333.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00461_t015.367.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00462_t015.400.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00463_t015.433.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00464_t015.467.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00465_t015.500.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00466_t015.533.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00467_t015.567.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00468_t015.600.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00469_t015.633.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00470_t015.667.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00502_t016.733.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00503_t016.767.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00504_t016.800.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00505_t016.833.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00506_t016.867.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00507_t016.900.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00579_t019.300.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00580_t019.333.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00581_t019.367.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00582_t019.400.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00583_t019.433.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00584_t019.467.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00585_t019.500.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00586_t019.533.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00587_t019.567.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00588_t019.600.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02719_t090.633.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02720_t090.667.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02721_t090.700.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02722_t090.733.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02723_t090.767.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02724_t090.800.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S03.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S05.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S13.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S16.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S19.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S20.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S21.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S22.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S23.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S27.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S28.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S30.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S32.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S36.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S38.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S39.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S43.jpg`

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
