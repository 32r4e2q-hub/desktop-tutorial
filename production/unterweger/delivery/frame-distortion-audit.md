# 成片逐帧畸变 / 时序 QC

- 成片：`杰克·翁特维格_最成功的一次伪装_三分钟_带声音.mp4`
- SHA-256：`d0bfa6648a0d110a984ee4f772a4fb7f739d2abe7164a9b8c57f40fd63b33b17`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：919（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：904
- >1 秒近静止区段：3；其中非信息卡/片尾段：3
- 帧差/光流/亮度突变待复核窗口：2
- 人脸检测：逐帧总检测 1904；达到复核阈值的候选 1147
- 手部检测：逐帧总检测 1908；超出宽松几何边界的 landmark 事件 216

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 92 | 0 | 0 | 0.9621 | 0 |
| S02 | graphic | 128 | 0 | 0 | 180.6998 | 0 |
| S03 | agnes | 117 | 0 | 2 | 0.9611 | 0 |
| S04 | agnes | 54 | 54 | 5 | 2.8162 | 0 |
| S05 | agnes | 115 | 72 | 28 | 2.4008 | 0 |
| S06 | agnes | 75 | 0 | 0 | 0.4432 | 0 |
| S07 | agnes | 95 | 95 | 0 | 1.3453 | 0 |
| S08 | agnes | 157 | 0 | 0 | 0.4223 | 0 |
| S09 | agnes | 82 | 6 | 0 | 0.9408 | 0 |
| S10 | agnes | 99 | 3 | 0 | 0.7163 | 0 |
| S11 | graphic | 171 | 3 | 0 | 239.833 | 0 |
| S12 | agnes | 73 | 54 | 0 | 2.5078 | 0 |
| S13 | agnes | 142 | 142 | 49 | 0.6611 | 0 |
| S14 | agnes | 111 | 0 | 0 | 0.9821 | 0 |
| S15 | agnes | 109 | 0 | 0 | 1.7137 | 0 |
| S16 | agnes | 113 | 91 | 99 | 0.4336 | 0 |
| S17 | agnes | 110 | 0 | 1 | 0.9295 | 0 |
| S18 | graphic | 90 | 0 | 0 | 107.1312 | 0 |
| S19 | agnes | 138 | 111 | 140 | 2.5959 | 0 |
| S20 | agnes | 96 | 0 | 124 | 0.538 | 0 |
| S21 | agnes | 101 | 101 | 38 | 1.62 | 0 |
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
| S34 | agnes | 81 | 81 | 62 | 0.3435 | 0 |
| S35 | agnes | 105 | 0 | 0 | 1.0245 | 0 |
| S36 | agnes | 87 | 87 | 76 | 0.8712 | 0 |
| S37 | graphic | 68 | 27 | 0 | 171.173 | 0 |
| S38 | agnes | 162 | 142 | 262 | 1.2428 | 0 |
| S39 | agnes | 126 | 21 | 15 | 1.5723 | 0 |
| S40 | graphic | 139 | 36 | 0 | 243.4859 | 0 |
| S41 | agnes | 85 | 0 | 170 | 0.3732 | 0 |
| S42 | agnes | 118 | 0 | 0 | 0.5613 | 0 |
| S43 | agnes | 132 | 132 | 179 | 0.9954 | 0 |
| S44 | agnes | 141 | 0 | 2 | 0.6956 | 0 |
| S45 | agnes | 199 | 33 | 0 | 0.5656 | 0 |
| END | graphic | 114 | 0 | 0 | 0.4257 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/unterweger/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/unterweger/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/unterweger/final-frame-audit/suspect-frames/frame_00335_t011.167.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00336_t011.200.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00337_t011.233.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00338_t011.267.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00339_t011.300.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00340_t011.333.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00341_t011.367.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00342_t011.400.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00343_t011.433.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00344_t011.467.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00345_t011.500.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00346_t011.533.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00347_t011.567.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00348_t011.600.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00349_t011.633.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00350_t011.667.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00351_t011.700.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00352_t011.733.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00353_t011.767.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00354_t011.800.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00355_t011.833.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00356_t011.867.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00357_t011.900.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00358_t011.933.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00359_t011.967.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00360_t012.000.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00361_t012.033.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00362_t012.067.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00363_t012.100.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00364_t012.133.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00365_t012.167.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00366_t012.200.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00367_t012.233.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00368_t012.267.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00369_t012.300.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00370_t012.333.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_00371_t012.367.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02719_t090.633.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02720_t090.667.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02721_t090.700.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02722_t090.733.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02723_t090.767.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_02724_t090.800.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/unterweger/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S05.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S13.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S16.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S17.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S19.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S20.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S21.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S22.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S23.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S27.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S28.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S30.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S32.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S34.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S36.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S38.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S39.jpg`
- 手部动态接触表：`work/unterweger/final-frame-audit/contacts/hands-S41.jpg`
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
