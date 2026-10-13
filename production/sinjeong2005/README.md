# 新亭洞连环杀人案：凶手找到了，却已死去十年

三分钟横版（16:9 · 1920×1080 · 30 fps · 180 秒）中文悬疑解说短片，抖音横屏版。
本片**不套以往的 38 镜动画 + 信息卡模板**，完全按用户上传的参考片做：
写实真人年代剧情景重现、连续剧情镜头、旁白贯穿、中英双语字幕、片头大标题压实景。

案件：2005 年首尔阳川区新亭洞，两名女子相继遇害；专案组查了八年无果，
2020 年旧证物里的 DNA 让案件重启，警方筛查二十三万多人、走访四十家医疗机构，
2025 年终于特定凶手——受害者到访大楼的管理员——而他已在 2015 年去世。
（逐句来源见 [`史实核对.md`](史实核对.md)，上传文案的「至今未破」已按真实进展改正。）

## 本片与以往各部的不同

| 项 | 以往（林过云等） | 本片 |
|---|---|---|
| 生成通道 | Agnes Video V2.0 | **智谱 CogVideoX-Flash**（仓库 `ZHIPUAI_API_KEY`，只在 Actions 里） |
| 画面 | 写实 3D 动画 + 7 张信息卡 + 片尾卡 | **真人实拍感年代剧**，40 镜全为生成镜头（智谱约 5 秒素材按旁白分句剪辑），**0 信息卡、0 片尾卡** |
| 人物 | 只给背影/剪影/手 | **露脸模式**：10 个虚构角色人人有脸、表情生动；不同人物不同脸、同一人物同脸（见下） |
| 字幕 | 中文大字单行 | **中英双语**（中文 48px + 英文 23px 小字，逐句对齐） |
| 节奏 | 45 镜 × 4 秒 | 40 镜（智谱每镜约 5 秒素材），贴近参考片的连续剧情节奏 |

## 人脸一致性（用户硬要求）

- `cast.json` 定义 10 个角色（专案组长、年轻刑警、环卫工、两名受害者、小吃店主、管理员、冷案组长、法医、逃脱女子），
  每个角色一条**不同的**面容描述（脸型/眉眼/鼻口/发型/年龄/衣着各不同）；
- 同一角色在 26 个露脸镜头里**逐字节复用同一条描述**（`build_story.py` 用 `{Cx}` 占位符从 cast.json 注入，想改脸只能改一处）；
- 两道闸门：生成前 `production/face_cast.py check-prompts`（静态，已 PASS）；出片后 `check-frames` 逐镜裁脸比对，
  换脸/撞脸的镜头写 `{"only":"Sxx"}` 只重做那一镜；
- 全部角色为虚构匿名演员，不还原真实人物容貌（见 `cast.json` 的 `_casting_note`）。

## 流程

```
史实核对（4 条韩媒/通讯社来源）
  └─ build_story.py：801 字解说 / 30 镜 / 10 角色 / 双语字幕（唯一内容源）
       └─ 配音（试音选定音色 → 六段 TTS → tighten_pauses → clause_times 对分句、重对 CUTS）
            └─ GEN_REQUEST → Actions 用智谱生成 30 镜 → results.json + qa/ 接触表
                 └─ 人脸/画质复审 → {"only":"Sxx"} 重做坏镜头
                      └─ RENDER_REQUEST → 成片 + delivery/ 报告
                           └─ VERBATIM_REQUEST 听检 / VISUAL_QC_REQUEST 全帧 QC → Release
```

## 出片方式（本仓库分支 arena/f3e80641-desktop-tutorial）

```bash
python3 production/sinjeong2005/build_story.py
python3 production/face_cast.py check-prompts --project production/sinjeong2005
echo '{"workers":1}' > production/sinjeong2005/GEN_REQUEST      # 智谱生成（.github/workflows/sinjeong2005-zhipu-gen.yml）
echo "render $(date -u +%FT%TZ)" > production/sinjeong2005/RENDER_REQUEST
```

成片文件名：`新亭洞连环杀人案_凶手找到了，却已死去十年_三分钟_带声音.mp4`

## 内容边界

- 不展示遗体、血腥或侵害过程；不重演作案；发现现场只拍发现者反应与封锁。
- 凶手由虚构演员扮演（不是真实嫌疑人容貌）；受害者只以生前日常形象出现。
- 画面常驻「AI真人情景重现 · 非新闻影像」；中文姓名、日期、字幕一律后期添加。
- 2025 年警方结论按「特定凶手、已死亡、无公诉权结案」写，不说「已被判刑」。
