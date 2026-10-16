# 成片逐帧畸变 / 时序 QC

- 成片：`lee-hyung-ho-3min-1080p-v2.mp4`
- SHA-256：`ec3331e20f20d6214a02a1b26f2baca250d427e4326cf53ab0bb801ae3e5caf1`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：12（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：0；其中非信息卡/片尾段：0
- 帧差/光流/亮度突变待复核窗口：43
- 人脸检测：逐帧总检测 1591；达到复核阈值的候选 1202
- 手部检测：逐帧总检测 318；超出宽松几何边界的 landmark 事件 161

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S03 | graphic | 126 | 15 | 0 | 152.5714 | 1 |
| S04 | cogvideo | 90 | 90 | 0 | 9.45 | 4 |
| S02 | cogvideo | 27 | 0 | 0 | 0.0745 | 0 |
| S05 | cogvideo | 60 | 58 | 14 | 5.3797 | 1 |
| S01 | cogvideo | 42 | 0 | 0 | 0.5098 | 0 |
| S07 | cogvideo | 111 | 0 | 0 | 1.1876 | 0 |
| S10 | graphic | 120 | 15 | 0 | 221.6721 | 0 |
| S06 | cogvideo | 132 | 0 | 0 | 0.3735 | 0 |
| S08 | cogvideo | 191 | 191 | 10 | 1.8925 | 0 |
| S09 | cogvideo | 97 | 0 | 0 | 0.0908 | 0 |
| S15 | cogvideo | 60 | 0 | 0 | 1.1726 | 0 |
| S33 | cogvideo | 114 | 0 | 0 | 0.1191 | 0 |
| S13 | cogvideo | 63 | 0 | 0 | 0.0966 | 0 |
| S11 | cogvideo | 69 | 0 | 0 | 0.4811 | 0 |
| S12 | cogvideo | 192 | 193 | 166 | 7.4439 | 1 |
| S17 | graphic | 126 | 15 | 0 | 178.2311 | 0 |
| S14 | cogvideo | 151 | 0 | 0 | 0.7273 | 0 |
| S16 | cogvideo | 80 | 125 | 0 | 3.8656 | 17 |
| S20 | cogvideo | 105 | 0 | 0 | 0.1861 | 0 |
| S18 | cogvideo | 108 | 1 | 0 | 3.8158 | 4 |
| S19 | cogvideo | 66 | 121 | 0 | 4.6956 | 10 |
| S21 | cogvideo | 141 | 0 | 0 | 0.1091 | 0 |
| S22 | cogvideo | 114 | 114 | 0 | 0.4369 | 0 |
| S23 | cogvideo | 188 | 188 | 2 | 1.0564 | 0 |
| S24 | graphic | 127 | 0 | 0 | 132.2237 | 0 |
| S25 | cogvideo | 108 | 0 | 0 | 0.462 | 0 |
| S26 | cogvideo | 96 | 0 | 0 | 0.1378 | 0 |
| S30 | graphic | 195 | 15 | 0 | 216.7112 | 0 |
| S28 | cogvideo | 102 | 0 | 0 | 0.1988 | 0 |
| S27 | cogvideo | 69 | 69 | 0 | 5.5244 | 0 |
| S29 | cogvideo | 106 | 0 | 0 | 0.4499 | 0 |
| S31 | cogvideo | 65 | 0 | 0 | 0.2315 | 0 |
| S32 | cogvideo | 63 | 21 | 0 | 0.201 | 0 |
| S35 | cogvideo | 72 | 0 | 0 | 0.1754 | 0 |
| S34 | cogvideo | 144 | 144 | 124 | 12.7233 | 1 |
| S37 | graphic | 186 | 24 | 0 | 201.5122 | 0 |
| S36 | cogvideo | 81 | 0 | 0 | 0.0838 | 0 |
| S41 | cogvideo | 180 | 0 | 0 | 0.2132 | 0 |
| S38 | cogvideo | 192 | 3 | 0 | 0.4385 | 0 |
| S39 | cogvideo | 102 | 0 | 0 | 0.3787 | 0 |
| S40 | cogvideo | 189 | 0 | 0 | 1.0862 | 0 |
| S42 | cogvideo | 189 | 0 | 0 | 0.528 | 0 |
| S43 | cogvideo | 87 | 0 | 0 | 0.09 | 0 |
| S44 | cogvideo | 189 | 189 | 2 | 1.0012 | 0 |
| S45 | graphic | 171 | 0 | 0 | 87.3823 | 3 |
| END | graphic | 114 | 0 | 0 | 0.657 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/revision-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/revision-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/revision-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/revision-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/revision-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/revision-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/revision-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/revision-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/revision-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/revision-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/revision-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/revision-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/revision-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/revision-frame-audit/suspect-frames/frame_00132_t004.400.jpg', 'work/revision-frame-audit/suspect-frames/frame_00133_t004.433.jpg', 'work/revision-frame-audit/suspect-frames/frame_00134_t004.467.jpg', 'work/revision-frame-audit/suspect-frames/frame_00135_t004.500.jpg', 'work/revision-frame-audit/suspect-frames/frame_00136_t004.533.jpg', 'work/revision-frame-audit/suspect-frames/frame_00137_t004.567.jpg', 'work/revision-frame-audit/suspect-frames/frame_00182_t006.067.jpg', 'work/revision-frame-audit/suspect-frames/frame_00183_t006.100.jpg', 'work/revision-frame-audit/suspect-frames/frame_00184_t006.133.jpg', 'work/revision-frame-audit/suspect-frames/frame_00185_t006.167.jpg', 'work/revision-frame-audit/suspect-frames/frame_00186_t006.200.jpg', 'work/revision-frame-audit/suspect-frames/frame_00187_t006.233.jpg', 'work/revision-frame-audit/suspect-frames/frame_00188_t006.267.jpg', 'work/revision-frame-audit/suspect-frames/frame_00189_t006.300.jpg', 'work/revision-frame-audit/suspect-frames/frame_00190_t006.333.jpg', 'work/revision-frame-audit/suspect-frames/frame_00191_t006.367.jpg', 'work/revision-frame-audit/suspect-frames/frame_00192_t006.400.jpg', 'work/revision-frame-audit/suspect-frames/frame_00193_t006.433.jpg', 'work/revision-frame-audit/suspect-frames/frame_00194_t006.467.jpg', 'work/revision-frame-audit/suspect-frames/frame_00286_t009.533.jpg', 'work/revision-frame-audit/suspect-frames/frame_00287_t009.567.jpg', 'work/revision-frame-audit/suspect-frames/frame_00288_t009.600.jpg', 'work/revision-frame-audit/suspect-frames/frame_00289_t009.633.jpg', 'work/revision-frame-audit/suspect-frames/frame_00290_t009.667.jpg', 'work/revision-frame-audit/suspect-frames/frame_01344_t044.800.jpg', 'work/revision-frame-audit/suspect-frames/frame_01345_t044.833.jpg', 'work/revision-frame-audit/suspect-frames/frame_01346_t044.867.jpg', 'work/revision-frame-audit/suspect-frames/frame_01347_t044.900.jpg', 'work/revision-frame-audit/suspect-frames/frame_01348_t044.933.jpg', 'work/revision-frame-audit/suspect-frames/frame_01771_t059.033.jpg', 'work/revision-frame-audit/suspect-frames/frame_01772_t059.067.jpg', 'work/revision-frame-audit/suspect-frames/frame_01773_t059.100.jpg', 'work/revision-frame-audit/suspect-frames/frame_01774_t059.133.jpg', 'work/revision-frame-audit/suspect-frames/frame_01775_t059.167.jpg', 'work/revision-frame-audit/suspect-frames/frame_01776_t059.200.jpg', 'work/revision-frame-audit/suspect-frames/frame_01777_t059.233.jpg', 'work/revision-frame-audit/suspect-frames/frame_01778_t059.267.jpg', 'work/revision-frame-audit/suspect-frames/frame_01779_t059.300.jpg', 'work/revision-frame-audit/suspect-frames/frame_01780_t059.333.jpg', 'work/revision-frame-audit/suspect-frames/frame_01781_t059.367.jpg', 'work/revision-frame-audit/suspect-frames/frame_01782_t059.400.jpg', 'work/revision-frame-audit/suspect-frames/frame_01783_t059.433.jpg', 'work/revision-frame-audit/suspect-frames/frame_01784_t059.467.jpg', 'work/revision-frame-audit/suspect-frames/frame_01785_t059.500.jpg', 'work/revision-frame-audit/suspect-frames/frame_01786_t059.533.jpg', 'work/revision-frame-audit/suspect-frames/frame_01787_t059.567.jpg', 'work/revision-frame-audit/suspect-frames/frame_01788_t059.600.jpg', 'work/revision-frame-audit/suspect-frames/frame_01789_t059.633.jpg', 'work/revision-frame-audit/suspect-frames/frame_01790_t059.667.jpg', 'work/revision-frame-audit/suspect-frames/frame_01791_t059.700.jpg', 'work/revision-frame-audit/suspect-frames/frame_01792_t059.733.jpg', 'work/revision-frame-audit/suspect-frames/frame_01793_t059.767.jpg', 'work/revision-frame-audit/suspect-frames/frame_01794_t059.800.jpg', 'work/revision-frame-audit/suspect-frames/frame_01795_t059.833.jpg', 'work/revision-frame-audit/suspect-frames/frame_01796_t059.867.jpg', 'work/revision-frame-audit/suspect-frames/frame_01797_t059.900.jpg', 'work/revision-frame-audit/suspect-frames/frame_01798_t059.933.jpg', 'work/revision-frame-audit/suspect-frames/frame_01799_t059.967.jpg', 'work/revision-frame-audit/suspect-frames/frame_01800_t060.000.jpg', 'work/revision-frame-audit/suspect-frames/frame_01801_t060.033.jpg', 'work/revision-frame-audit/suspect-frames/frame_01802_t060.067.jpg', 'work/revision-frame-audit/suspect-frames/frame_01803_t060.100.jpg', 'work/revision-frame-audit/suspect-frames/frame_01804_t060.133.jpg', 'work/revision-frame-audit/suspect-frames/frame_01805_t060.167.jpg', 'work/revision-frame-audit/suspect-frames/frame_01806_t060.200.jpg', 'work/revision-frame-audit/suspect-frames/frame_01807_t060.233.jpg', 'work/revision-frame-audit/suspect-frames/frame_01808_t060.267.jpg', 'work/revision-frame-audit/suspect-frames/frame_01809_t060.300.jpg', 'work/revision-frame-audit/suspect-frames/frame_01814_t060.467.jpg', 'work/revision-frame-audit/suspect-frames/frame_01815_t060.500.jpg', 'work/revision-frame-audit/suspect-frames/frame_01816_t060.533.jpg', 'work/revision-frame-audit/suspect-frames/frame_01817_t060.567.jpg', 'work/revision-frame-audit/suspect-frames/frame_01818_t060.600.jpg', 'work/revision-frame-audit/suspect-frames/frame_01819_t060.633.jpg', 'work/revision-frame-audit/suspect-frames/frame_01820_t060.667.jpg', 'work/revision-frame-audit/suspect-frames/frame_01821_t060.700.jpg', 'work/revision-frame-audit/suspect-frames/frame_01822_t060.733.jpg', 'work/revision-frame-audit/suspect-frames/frame_01823_t060.767.jpg', 'work/revision-frame-audit/suspect-frames/frame_01824_t060.800.jpg', 'work/revision-frame-audit/suspect-frames/frame_01825_t060.833.jpg', 'work/revision-frame-audit/suspect-frames/frame_01826_t060.867.jpg', 'work/revision-frame-audit/suspect-frames/frame_01827_t060.900.jpg', 'work/revision-frame-audit/suspect-frames/frame_01828_t060.933.jpg', 'work/revision-frame-audit/suspect-frames/frame_01829_t060.967.jpg', 'work/revision-frame-audit/suspect-frames/frame_01830_t061.000.jpg', 'work/revision-frame-audit/suspect-frames/frame_01831_t061.033.jpg', 'work/revision-frame-audit/suspect-frames/frame_01832_t061.067.jpg', 'work/revision-frame-audit/suspect-frames/frame_01833_t061.100.jpg', 'work/revision-frame-audit/suspect-frames/frame_01834_t061.133.jpg', 'work/revision-frame-audit/suspect-frames/frame_01835_t061.167.jpg', 'work/revision-frame-audit/suspect-frames/frame_01836_t061.200.jpg', 'work/revision-frame-audit/suspect-frames/frame_01837_t061.233.jpg', 'work/revision-frame-audit/suspect-frames/frame_01838_t061.267.jpg', 'work/revision-frame-audit/suspect-frames/frame_01839_t061.300.jpg', 'work/revision-frame-audit/suspect-frames/frame_01840_t061.333.jpg', 'work/revision-frame-audit/suspect-frames/frame_01841_t061.367.jpg', 'work/revision-frame-audit/suspect-frames/frame_01842_t061.400.jpg', 'work/revision-frame-audit/suspect-frames/frame_01843_t061.433.jpg', 'work/revision-frame-audit/suspect-frames/frame_01844_t061.467.jpg', 'work/revision-frame-audit/suspect-frames/frame_01845_t061.500.jpg', 'work/revision-frame-audit/suspect-frames/frame_01846_t061.533.jpg', 'work/revision-frame-audit/suspect-frames/frame_01847_t061.567.jpg', 'work/revision-frame-audit/suspect-frames/frame_01848_t061.600.jpg', 'work/revision-frame-audit/suspect-frames/frame_01956_t065.200.jpg', 'work/revision-frame-audit/suspect-frames/frame_01957_t065.233.jpg', 'work/revision-frame-audit/suspect-frames/frame_01958_t065.267.jpg', 'work/revision-frame-audit/suspect-frames/frame_01959_t065.300.jpg', 'work/revision-frame-audit/suspect-frames/frame_01960_t065.333.jpg', 'work/revision-frame-audit/suspect-frames/frame_01961_t065.367.jpg']`
- 手部动态接触表：`work/revision-frame-audit/contacts/hands-S05.jpg`
- 手部动态接触表：`work/revision-frame-audit/contacts/hands-S08.jpg`
- 手部动态接触表：`work/revision-frame-audit/contacts/hands-S12.jpg`
- 手部动态接触表：`work/revision-frame-audit/contacts/hands-S34.jpg`

## 限制

自动检测会漏检遮挡、极小目标和模型本身识别不到的 AI 畸变；时序异常也可能是有意运镜、火焰、蒸汽或字幕变化。所以候选必须看原始分辨率前后帧，语义与解剖必须人工目检。没有候选不等于数学上证明‘完美无瑕疵’。
