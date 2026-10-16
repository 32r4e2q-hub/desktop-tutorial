# 成片逐帧畸变 / 时序 QC

- 成片：`李亨浩_四十四天的电话_三分钟.mp4`
- SHA-256：`5946ef6151344badf20081bd26b8315c73c7e43f6fba5e25965e5c28cad274d1`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：14（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：2；其中非信息卡/片尾段：2
- 帧差/光流/亮度突变待复核窗口：56
- 人脸检测：逐帧总检测 1926；达到复核阈值的候选 1445
- 手部检测：逐帧总检测 535；超出宽松几何边界的 landmark 事件 160

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | cogvideo | 135 | 0 | 0 | 0.8008 | 1 |
| S02 | cogvideo | 102 | 0 | 0 | 0.0852 | 0 |
| S03 | graphic | 94 | 9 | 0 | 96.9637 | 0 |
| S04 | cogvideo | 129 | 127 | 1 | 9.466 | 0 |
| S05 | cogvideo | 64 | 61 | 18 | 5.381 | 0 |
| S06 | cogvideo | 96 | 0 | 0 | 0.1269 | 0 |
| S07 | cogvideo | 160 | 206 | 140 | 10.302 | 2 |
| S08 | cogvideo | 119 | 119 | 9 | 3.3885 | 6 |
| S09 | cogvideo | 99 | 0 | 0 | 0.0876 | 0 |
| S10 | graphic | 174 | 15 | 0 | 243.6113 | 0 |
| S11 | cogvideo | 64 | 0 | 0 | 0.4859 | 0 |
| S12 | cogvideo | 192 | 192 | 170 | 7.4121 | 1 |
| S13 | cogvideo | 93 | 0 | 0 | 0.1041 | 0 |
| S14 | cogvideo | 90 | 0 | 0 | 0.0737 | 0 |
| S15 | cogvideo | 160 | 0 | 0 | 1.1706 | 0 |
| S16 | cogvideo | 73 | 113 | 0 | 3.8644 | 15 |
| S17 | graphic | 114 | 9 | 0 | 167.7138 | 0 |
| S18 | cogvideo | 127 | 27 | 0 | 12.8156 | 3 |
| S19 | cogvideo | 68 | 125 | 0 | 4.6948 | 8 |
| S20 | cogvideo | 117 | 0 | 0 | 0.2011 | 0 |
| S21 | cogvideo | 87 | 87 | 0 | 1.7904 | 0 |
| S22 | cogvideo | 72 | 0 | 0 | 0.2964 | 0 |
| S23 | cogvideo | 144 | 144 | 1 | 2.0726 | 0 |
| S24 | graphic | 127 | 0 | 0 | 189.7711 | 0 |
| S25 | cogvideo | 110 | 0 | 0 | 0.127 | 0 |
| S26 | cogvideo | 97 | 185 | 24 | 0.7206 | 0 |
| S27 | cogvideo | 67 | 67 | 0 | 5.543 | 0 |
| S28 | cogvideo | 128 | 0 | 0 | 2.5249 | 1 |
| S29 | cogvideo | 123 | 0 | 0 | 0.314 | 1 |
| S30 | graphic | 151 | 15 | 0 | 257.4998 | 0 |
| S31 | cogvideo | 131 | 0 | 0 | 10.3677 | 8 |
| S32 | cogvideo | 70 | 0 | 0 | 0.06 | 0 |
| S33 | cogvideo | 147 | 0 | 16 | 13.5172 | 1 |
| S34 | cogvideo | 131 | 131 | 112 | 3.4869 | 0 |
| S35 | cogvideo | 114 | 0 | 0 | 0.3424 | 3 |
| S36 | cogvideo | 59 | 0 | 0 | 0.0621 | 0 |
| S37 | graphic | 139 | 34 | 0 | 215.8596 | 0 |
| S38 | cogvideo | 133 | 0 | 0 | 0.1677 | 0 |
| S39 | cogvideo | 134 | 0 | 0 | 0.7042 | 0 |
| S40 | cogvideo | 130 | 0 | 0 | 0.416 | 2 |
| S41 | cogvideo | 172 | 72 | 43 | 0.4484 | 1 |
| S42 | cogvideo | 108 | 0 | 0 | 0.1251 | 0 |
| S43 | cogvideo | 85 | 0 | 0 | 0.4254 | 0 |
| S44 | cogvideo | 187 | 187 | 1 | 0.9802 | 0 |
| S45 | graphic | 170 | 1 | 0 | 95.1076 | 2 |
| END | graphic | 114 | 0 | 0 | 0.493 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/lee_hyung_ho1991/frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/lee_hyung_ho1991/frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00636_t021.200.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00637_t021.233.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00638_t021.267.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00639_t021.300.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00640_t021.333.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00641_t021.367.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00642_t021.400.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00646_t021.533.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00647_t021.567.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00648_t021.600.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00649_t021.633.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00650_t021.667.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00870_t029.000.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00871_t029.033.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00872_t029.067.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00873_t029.100.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00874_t029.133.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00875_t029.167.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00876_t029.200.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00877_t029.233.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00878_t029.267.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00879_t029.300.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00880_t029.333.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00881_t029.367.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00882_t029.400.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00883_t029.433.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00884_t029.467.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00885_t029.500.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00886_t029.533.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00887_t029.567.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00888_t029.600.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00889_t029.633.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00890_t029.667.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00891_t029.700.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00892_t029.733.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00893_t029.767.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00894_t029.800.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00895_t029.833.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_00896_t029.867.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01278_t042.600.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01279_t042.633.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01280_t042.667.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01281_t042.700.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01282_t042.733.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01771_t059.033.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01772_t059.067.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01773_t059.100.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01774_t059.133.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01775_t059.167.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01776_t059.200.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01777_t059.233.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01778_t059.267.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01779_t059.300.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01780_t059.333.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01781_t059.367.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01782_t059.400.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01783_t059.433.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01784_t059.467.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01785_t059.500.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01786_t059.533.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01787_t059.567.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01788_t059.600.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01789_t059.633.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01790_t059.667.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01791_t059.700.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01792_t059.733.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01793_t059.767.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01794_t059.800.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01795_t059.833.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01796_t059.867.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01797_t059.900.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01798_t059.933.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01799_t059.967.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01800_t060.000.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01801_t060.033.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01802_t060.067.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01803_t060.100.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01804_t060.133.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01805_t060.167.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01806_t060.200.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01807_t060.233.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01808_t060.267.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01809_t060.300.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01814_t060.467.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01815_t060.500.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01816_t060.533.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01817_t060.567.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01818_t060.600.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01819_t060.633.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01820_t060.667.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01821_t060.700.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01822_t060.733.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01823_t060.767.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01824_t060.800.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01825_t060.833.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01826_t060.867.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01827_t060.900.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01828_t060.933.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01829_t060.967.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01830_t061.000.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01831_t061.033.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01832_t061.067.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01833_t061.100.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01834_t061.133.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01835_t061.167.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01836_t061.200.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01837_t061.233.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01838_t061.267.jpg', 'work/lee_hyung_ho1991/frame-audit/suspect-frames/frame_01839_t061.300.jpg']`
- 手部动态接触表：`work/lee_hyung_ho1991/frame-audit/contacts/hands-S05.jpg`
- 手部动态接触表：`work/lee_hyung_ho1991/frame-audit/contacts/hands-S07.jpg`
- 手部动态接触表：`work/lee_hyung_ho1991/frame-audit/contacts/hands-S08.jpg`
- 手部动态接触表：`work/lee_hyung_ho1991/frame-audit/contacts/hands-S12.jpg`
- 手部动态接触表：`work/lee_hyung_ho1991/frame-audit/contacts/hands-S26.jpg`
- 手部动态接触表：`work/lee_hyung_ho1991/frame-audit/contacts/hands-S33.jpg`
- 手部动态接触表：`work/lee_hyung_ho1991/frame-audit/contacts/hands-S34.jpg`
- 手部动态接触表：`work/lee_hyung_ho1991/frame-audit/contacts/hands-S41.jpg`

## 限制

自动检测会漏检遮挡、极小目标和模型本身识别不到的 AI 畸变；时序异常也可能是有意运镜、火焰、蒸汽或字幕变化。所以候选必须看原始分辨率前后帧，语义与解剖必须人工目检。没有候选不等于数学上证明‘完美无瑕疵’。
