# 成片逐帧畸变 / 时序 QC

- 成片：`韩国雨衣杀手柳永哲_十个月，二十条人命_三分钟_带声音.mp4`
- SHA-256：`e70689acf8b43f393b627835d7c637a1475ebc80d5c95596fc4e3c0929ea7c20`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：276（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：262
- >1 秒近静止区段：1；其中非信息卡/片尾段：1
- 帧差/光流/亮度突变待复核窗口：4
- 人脸检测：逐帧总检测 732；达到复核阈值的候选 204
- 手部检测：逐帧总检测 965；超出宽松几何边界的 landmark 事件 134

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 132 | 0 | 0 | 1.0062 | 1 |
| S02 | graphic | 76 | 0 | 0 | 161.0573 | 0 |
| S03 | agnes | 51 | 0 | 0 | 0.3147 | 0 |
| S04 | agnes | 83 | 0 | 0 | 1.1526 | 0 |
| S05 | agnes | 76 | 76 | 0 | 0.5401 | 0 |
| S06 | agnes | 111 | 108 | 186 | 0.6987 | 0 |
| S07 | agnes | 72 | 0 | 0 | 0.5165 | 0 |
| S08 | agnes | 129 | 0 | 0 | 2.0321 | 0 |
| S09 | agnes | 145 | 0 | 0 | 0.5349 | 0 |
| S10 | agnes | 83 | 1 | 0 | 3.3473 | 0 |
| S11 | graphic | 105 | 62 | 0 | 219.5848 | 0 |
| S12 | agnes | 115 | 0 | 0 | 1.5375 | 0 |
| S13 | agnes | 124 | 0 | 125 | 4.5702 | 1 |
| S14 | agnes | 71 | 0 | 0 | 0.9947 | 0 |
| S15 | agnes | 154 | 3 | 0 | 1.5825 | 0 |
| S16 | agnes | 91 | 0 | 0 | 0.5879 | 0 |
| S17 | agnes | 93 | 0 | 0 | 0.9194 | 0 |
| S18 | graphic | 128 | 5 | 0 | 193.197 | 0 |
| S19 | agnes | 110 | 8 | 0 | 0.6984 | 0 |
| S20 | agnes | 123 | 65 | 0 | 0.3656 | 0 |
| S21 | agnes | 89 | 0 | 0 | 0.4405 | 0 |
| S22 | agnes | 86 | 0 | 0 | 1.0264 | 0 |
| S23 | agnes | 108 | 0 | 0 | 0.5865 | 0 |
| S24 | agnes | 121 | 2 | 0 | 0.9394 | 0 |
| S25 | graphic | 91 | 1 | 0 | 183.6626 | 0 |
| S26 | agnes | 122 | 0 | 0 | 1.7974 | 0 |
| S27 | agnes | 92 | 107 | 92 | 0.7182 | 0 |
| S28 | agnes | 129 | 28 | 0 | 2.077 | 0 |
| S29 | agnes | 56 | 0 | 0 | 0.8082 | 0 |
| S30 | agnes | 128 | 0 | 0 | 0.7267 | 0 |
| S31 | agnes | 176 | 89 | 0 | 2.2723 | 0 |
| S32 | agnes | 103 | 69 | 206 | 0.3628 | 0 |
| S33 | agnes | 78 | 0 | 0 | 0.7445 | 0 |
| S34 | agnes | 156 | 0 | 0 | 0.9671 | 0 |
| S35 | agnes | 168 | 48 | 9 | 0.328 | 0 |
| S36 | graphic | 35 | 0 | 0 | 138.376 | 0 |
| S37 | agnes | 148 | 0 | 0 | 1.4806 | 0 |
| S38 | agnes | 202 | 0 | 187 | 2.0454 | 0 |
| S39 | agnes | 136 | 9 | 0 | 1.9101 | 0 |
| S40 | agnes | 160 | 0 | 160 | 3.4806 | 1 |
| S41 | graphic | 195 | 45 | 0 | 182.4181 | 0 |
| S42 | agnes | 116 | 0 | 0 | 0.6215 | 0 |
| S43 | graphic | 136 | 6 | 0 | 181.399 | 0 |
| S44 | agnes | 122 | 0 | 0 | 2.2537 | 0 |
| S45 | agnes | 261 | 0 | 0 | 0.5004 | 0 |
| END | graphic | 114 | 0 | 0 | 0.6018 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/raincoat2004/frame_distortion_audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/raincoat2004/frame_distortion_audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00000_t000.000.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00001_t000.033.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00002_t000.067.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00003_t000.100.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00004_t000.133.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00005_t000.167.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00006_t000.200.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00007_t000.233.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00008_t000.267.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00009_t000.300.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00010_t000.333.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00340_t011.333.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00341_t011.367.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00342_t011.400.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00343_t011.433.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00344_t011.467.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00345_t011.500.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00346_t011.533.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00347_t011.567.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00348_t011.600.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00349_t011.633.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00350_t011.667.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00351_t011.700.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00352_t011.733.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00353_t011.767.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00354_t011.800.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00355_t011.833.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00356_t011.867.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00357_t011.900.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00358_t011.933.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00359_t011.967.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00360_t012.000.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00361_t012.033.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00362_t012.067.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00376_t012.533.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00377_t012.567.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00378_t012.600.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00379_t012.633.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00380_t012.667.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_00381_t012.700.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_01179_t039.300.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_01180_t039.333.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_01181_t039.367.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_01182_t039.400.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_01183_t039.433.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_01184_t039.467.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_01185_t039.500.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_04297_t143.233.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_04298_t143.267.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_04299_t143.300.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_04300_t143.333.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_04301_t143.367.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_04302_t143.400.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_04303_t143.433.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_04304_t143.467.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_05286_t176.200.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_05287_t176.233.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_05288_t176.267.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_05289_t176.300.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_05290_t176.333.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_05291_t176.367.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_05292_t176.400.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_05293_t176.433.jpg', 'work/raincoat2004/frame_distortion_audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/raincoat2004/frame_distortion_audit/contacts/hands-S06.jpg`
- 手部动态接触表：`work/raincoat2004/frame_distortion_audit/contacts/hands-S13.jpg`
- 手部动态接触表：`work/raincoat2004/frame_distortion_audit/contacts/hands-S27.jpg`
- 手部动态接触表：`work/raincoat2004/frame_distortion_audit/contacts/hands-S32.jpg`
- 手部动态接触表：`work/raincoat2004/frame_distortion_audit/contacts/hands-S38.jpg`
- 手部动态接触表：`work/raincoat2004/frame_distortion_audit/contacts/hands-S40.jpg`

## 限制

自动检测会漏检遮挡、极小目标和模型本身识别不到的 AI 畸变；时序异常也可能是有意运镜、火焰、蒸汽或字幕变化。所以候选必须看原始分辨率前后帧，语义与解剖必须人工目检。没有候选不等于数学上证明‘完美无瑕疵’。
