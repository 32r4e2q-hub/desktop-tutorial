# 成片逐帧畸变 / 时序 QC

- 成片：`周克华案_逃亡八年，最后四天_三分钟_带声音.mp4`
- SHA-256：`7a131df165a5d2bbb4aa609636e7409168ba3d80dff360646e68d3ba663da6d1`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：13（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：0
- >1 秒近静止区段：3；其中非信息卡/片尾段：3
- 帧差/光流/亮度突变待复核窗口：5
- 人脸检测：逐帧总检测 252；达到复核阈值的候选 0
- 手部检测：逐帧总检测 49；超出宽松几何边界的 landmark 事件 43

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 96 | 0 | 0 | 0.6477 | 1 |
| S02 | graphic | 94 | 0 | 0 | 57.9543 | 0 |
| S03 | agnes | 137 | 0 | 0 | 0.2262 | 0 |
| S04 | agnes | 81 | 0 | 0 | 0.3631 | 0 |
| S05 | agnes | 77 | 0 | 0 | 0.9254 | 0 |
| S06 | agnes | 66 | 0 | 0 | 0.1138 | 0 |
| S07 | agnes | 116 | 0 | 0 | 0.1258 | 0 |
| S08 | agnes | 162 | 0 | 0 | 0.269 | 0 |
| S09 | graphic | 142 | 0 | 0 | 103.7224 | 0 |
| S10 | agnes | 115 | 0 | 0 | 0.4443 | 0 |
| S11 | agnes | 146 | 0 | 0 | 0.6509 | 0 |
| S12 | agnes | 166 | 60 | 48 | 2.9764 | 1 |
| S13 | agnes | 116 | 0 | 0 | 0.7175 | 0 |
| S14 | agnes | 127 | 0 | 0 | 1.1917 | 0 |
| S15 | agnes | 100 | 0 | 0 | 0.3874 | 0 |
| S16 | graphic | 100 | 58 | 0 | 200.2988 | 0 |
| S17 | agnes | 74 | 0 | 0 | 0.2937 | 0 |
| S18 | agnes | 119 | 0 | 0 | 0.2278 | 0 |
| S19 | agnes | 153 | 0 | 0 | 0.3204 | 0 |
| S20 | agnes | 73 | 0 | 0 | 0.1186 | 0 |
| S21 | agnes | 91 | 91 | 0 | 1.7761 | 0 |
| S22 | graphic | 67 | 30 | 0 | 185.3712 | 0 |
| S23 | agnes | 204 | 0 | 0 | 0.0664 | 0 |
| S24 | agnes | 187 | 0 | 0 | 2.4166 | 0 |
| S25 | graphic | 113 | 0 | 0 | 172.244 | 0 |
| S26 | agnes | 122 | 0 | 0 | 0.324 | 0 |
| S27 | agnes | 156 | 0 | 0 | 0.5061 | 0 |
| S28 | agnes | 89 | 1 | 0 | 0.1651 | 0 |
| S29 | agnes | 96 | 0 | 0 | 0.0939 | 0 |
| S30 | agnes | 167 | 0 | 0 | 0.0862 | 0 |
| S31 | agnes | 84 | 0 | 0 | 0.1083 | 0 |
| S32 | agnes | 91 | 0 | 0 | 0.5339 | 0 |
| S33 | graphic | 86 | 0 | 0 | 169.4223 | 0 |
| S34 | agnes | 95 | 0 | 1 | 0.13 | 0 |
| S35 | agnes | 80 | 0 | 0 | 2.7795 | 1 |
| S36 | agnes | 88 | 0 | 0 | 0.1372 | 0 |
| S37 | agnes | 72 | 12 | 0 | 0.0796 | 0 |
| S38 | agnes | 196 | 0 | 0 | 0.3295 | 0 |
| S39 | agnes | 164 | 0 | 0 | 0.351 | 0 |
| S40 | graphic | 127 | 0 | 0 | 224.2599 | 0 |
| S41 | agnes | 120 | 0 | 0 | 0.1207 | 0 |
| S42 | agnes | 91 | 0 | 0 | 0.085 | 0 |
| S43 | agnes | 143 | 0 | 0 | 0.8286 | 0 |
| S44 | agnes | 106 | 0 | 0 | 0.1558 | 0 |
| S45 | agnes | 191 | 0 | 0 | 24.8863 | 1 |
| END | graphic | 114 | 0 | 0 | 0.7238 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/zhoukehua2012/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/zhoukehua2012/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01335_t044.500.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01336_t044.533.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01337_t044.567.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01338_t044.600.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01339_t044.633.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01340_t044.667.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01341_t044.700.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01342_t044.733.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01343_t044.767.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01344_t044.800.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01345_t044.833.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01346_t044.867.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01347_t044.900.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01348_t044.933.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01349_t044.967.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01350_t045.000.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01351_t045.033.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01352_t045.067.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01353_t045.100.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01354_t045.133.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01355_t045.167.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01356_t045.200.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01357_t045.233.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01358_t045.267.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01359_t045.300.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01360_t045.333.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01361_t045.367.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01362_t045.400.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01363_t045.433.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01375_t045.833.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01376_t045.867.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01377_t045.900.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01378_t045.933.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01379_t045.967.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01380_t046.000.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01381_t046.033.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_01382_t046.067.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_03912_t130.400.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_03913_t130.433.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_03914_t130.467.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_03915_t130.500.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_03916_t130.533.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05280_t176.000.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05281_t176.033.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05282_t176.067.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05283_t176.100.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05284_t176.133.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05285_t176.167.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/zhoukehua2012/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/zhoukehua2012/final-frame-audit/contacts/hands-S12.jpg`

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
