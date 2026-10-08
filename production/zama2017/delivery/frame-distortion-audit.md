# 成片逐帧畸变 / 时序 QC

- 成片：`日本座间九人案_一间公寓里的九条人命_三分钟_带声音.mp4`
- SHA-256：`72315da4506340f3abfce2984a67893c707f5bbdd0042306e55c839f6668de1f`
- 视频：1920×1080 / 30.000 fps / 180.000 秒
- 覆盖：解码并分析 **5400/5400 帧**；逐帧 MediaPipe 人脸/手检测；320x180 时序分析
- 自动状态：**REVIEW**（机器结果，不等同于无任何视觉瑕疵）

## 全片结果

- PTS 连续性异常：0
- 亮度低于 12 的帧：950（片头/片尾淡入淡出需按时间线解释）
- 非计划黑帧：935
- >1 秒近静止区段：3；其中非信息卡/片尾段：3
- 帧差/光流/亮度突变待复核窗口：4
- 人脸检测：逐帧总检测 898；达到复核阈值的候选 466
- 手部检测：逐帧总检测 869；超出宽松几何边界的 landmark 事件 240

## 镜头统计

| 镜头 | 类型 | 帧数 | 人脸检出 | 手检出 | 光流残差 P95 峰值 | 时序异常窗口 |
|---|---:|---:|---:|---:|---:|---:|
| S01 | agnes | 80 | 0 | 0 | 0.6905 | 1 |
| S02 | graphic | 66 | 1 | 0 | 137.308 | 0 |
| S03 | agnes | 111 | 0 | 0 | 1.6532 | 0 |
| S04 | agnes | 110 | 0 | 0 | 1.1464 | 0 |
| S05 | agnes | 70 | 70 | 0 | 0.8376 | 0 |
| S06 | agnes | 61 | 61 | 0 | 1.2043 | 0 |
| S07 | agnes | 88 | 0 | 0 | 0.4282 | 0 |
| S08 | agnes | 110 | 0 | 0 | 1.6819 | 0 |
| S09 | agnes | 84 | 0 | 0 | 0.6145 | 0 |
| S10 | agnes | 129 | 0 | 0 | 0.6248 | 0 |
| S11 | graphic | 102 | 55 | 0 | 194.3943 | 0 |
| S12 | agnes | 152 | 0 | 0 | 1.697 | 0 |
| S13 | agnes | 71 | 0 | 0 | 0.7628 | 0 |
| S14 | agnes | 128 | 0 | 0 | 1.5986 | 0 |
| S15 | agnes | 152 | 0 | 0 | 1.3883 | 0 |
| S16 | agnes | 126 | 0 | 0 | 0.7421 | 0 |
| S17 | agnes | 93 | 0 | 1 | 0.5066 | 0 |
| S18 | graphic | 118 | 0 | 0 | 229.5965 | 0 |
| S19 | agnes | 60 | 0 | 0 | 0.6145 | 0 |
| S20 | agnes | 118 | 0 | 0 | 0.3752 | 0 |
| S21 | agnes | 138 | 54 | 0 | 0.5613 | 0 |
| S22 | agnes | 120 | 0 | 0 | 2.4165 | 0 |
| S23 | agnes | 121 | 0 | 0 | 1.0746 | 0 |
| S24 | agnes | 100 | 100 | 1 | 0.4382 | 0 |
| S25 | graphic | 131 | 0 | 0 | 176.3721 | 0 |
| S26 | agnes | 134 | 0 | 126 | 0.6663 | 0 |
| S27 | agnes | 180 | 180 | 70 | 1.6536 | 0 |
| S28 | agnes | 80 | 0 | 91 | 0.9126 | 0 |
| S29 | agnes | 98 | 12 | 0 | 0.6568 | 0 |
| S30 | agnes | 175 | 127 | 0 | 0.6448 | 0 |
| S31 | agnes | 131 | 0 | 98 | 6.9867 | 1 |
| S32 | agnes | 107 | 6 | 247 | 0.6586 | 0 |
| S33 | agnes | 110 | 0 | 0 | 1.8339 | 1 |
| S34 | agnes | 104 | 0 | 0 | 1.1163 | 0 |
| S35 | agnes | 162 | 0 | 11 | 1.0688 | 0 |
| S36 | graphic | 94 | 58 | 0 | 148.97 | 0 |
| S37 | agnes | 86 | 53 | 70 | 1.4096 | 0 |
| S38 | agnes | 166 | 0 | 0 | 0.9747 | 0 |
| S39 | agnes | 180 | 2 | 0 | 2.4515 | 0 |
| S40 | agnes | 83 | 3 | 83 | 2.3262 | 0 |
| S41 | graphic | 127 | 58 | 0 | 192.6432 | 0 |
| S42 | agnes | 104 | 0 | 0 | 0.471 | 0 |
| S43 | graphic | 190 | 58 | 0 | 204.7695 | 0 |
| S44 | agnes | 106 | 0 | 0 | 0.7797 | 0 |
| S45 | agnes | 230 | 0 | 71 | 1.0752 | 0 |
| END | graphic | 114 | 0 | 0 | 0.4033 | 1 |

## 复核文件

- 全 45 镜 + 片尾画面中帧：`work/zama2017/final-frame-audit/contacts/shot-midpoints.jpg`
- 逐帧指标 CSV：`work/zama2017/final-frame-audit/frame-metrics.csv`
- 候选异常原始分辨率帧：`['work/zama2017/final-frame-audit/suspect-frames/frame_00000_t000.000.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00001_t000.033.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00002_t000.067.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00003_t000.100.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00004_t000.133.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00005_t000.167.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00006_t000.200.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00007_t000.233.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00008_t000.267.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00009_t000.300.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00010_t000.333.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00365_t012.167.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00366_t012.200.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00367_t012.233.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00368_t012.267.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00369_t012.300.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00370_t012.333.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00371_t012.367.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00372_t012.400.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00373_t012.433.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00374_t012.467.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00375_t012.500.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00376_t012.533.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00377_t012.567.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00378_t012.600.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00379_t012.633.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00380_t012.667.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00381_t012.700.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00382_t012.733.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00383_t012.767.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00384_t012.800.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00385_t012.833.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00386_t012.867.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00387_t012.900.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00388_t012.933.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_00389_t012.967.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03342_t111.400.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03343_t111.433.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03344_t111.467.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03345_t111.500.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03346_t111.533.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03347_t111.567.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03348_t111.600.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03349_t111.633.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03350_t111.667.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03351_t111.700.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03620_t120.667.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03621_t120.700.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03622_t120.733.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03623_t120.767.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_03624_t120.800.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_05286_t176.200.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_05287_t176.233.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_05288_t176.267.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_05289_t176.300.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_05290_t176.333.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_05291_t176.367.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_05292_t176.400.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_05293_t176.433.jpg', 'work/zama2017/final-frame-audit/suspect-frames/frame_05294_t176.467.jpg']`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S17.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S24.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S26.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S27.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S28.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S31.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S32.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S35.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S37.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S40.jpg`
- 手部动态接触表：`work/zama2017/final-frame-audit/contacts/hands-S45.jpg`

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
