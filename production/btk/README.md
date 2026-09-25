# BTK：软盘里的名字

本项目依照仓库根目录 [`新题目开工手册.md`](../../新题目开工手册.md) 与吉尔戈成片流程制作。视觉基准为《吉尔戈海滩：披萨盒里的凶手》的手绘二维动画纪录片风格，不修改或复用参考片内容。

- 固定分支：`arena/01a0d3ca-desktop-tutorial`
- 目标：横版16:9，1920×1080，30fps，180秒
- 镜头计划：45镜 = 38段Agnes Video V2.0动画 + 7张后期信息卡；每镜只使用一次
- 剧本：[`抖音脚本.md`](抖音脚本.md)（六段口播788字，时间轴来自收紧后配音）
- 事实底稿：[`screenplay.md`](screenplay.md)
- 制作与复核记录：[`制作过程.md`](制作过程.md)
- 预览与来源收据：`qa/`、`results.json`；现存的是上一版素材，不能当作本轮最终画面验收

## 目前状态（2026-09-25）

- 口播与六段 `voice-00` 配音逐字一致；静音收紧后总长约159.53秒。计划留168秒口播槽位，整体以0.950×速率铺满槽位；39个镜头切点通过分句时间检查。部分分句时间明确标为比例／能量回退估计，最终渲染仍优先尝试Whisper对轨。
- 分支已有38段Agnes的上一版生成回执和接触表。按新版提示词与当前证据边界重新比对payload哈希：S01、S02、S15、S21、S23、S24、S30、S31、S32、S36、S37、S44共12镜需重做；其余26镜可按哈希复用。新生成12镜仍须逐镜视觉审查。
- `.github/workflows/btk-*.yml` 已安装；修改 `GEN_REQUEST` 并push会触发Agnes续跑。工作流按官方速率限制调用，不绕过限流。
- 已有 `delivery/technical-report.json`、字幕及接触表属于先前版本/初剪。**当前没有通过画面复审、音画检查和逐字听检的最终MP4，不能宣称已完成成片。**

## 案情边界

- 受害者口径为十名；案发于堪萨斯州威奇托地区，1974—1991年。
- Dennis Rader是Park City法规执行员、Christ Lutheran Church会众委员会主席；不称为市议会议员。
- 软盘已删Word文件的元数据留下Dennis与教会电脑线索；不能称它单独定罪。
- 女儿的大学诊所医学样本经法律程序调取用于亲缘DNA比对，只是亲缘线索，不是直接或“完美匹配”。
- 2005年是认罪及量刑程序；不作无来源的心理判断。
- 软盘于2005年2月16日寄出，雷德于2月25日被捕，脚本称“九天后的手铐”。
- 画面避免血腥再现、受害者肖像、伪文字和镜头中途换场；对真实人物做克制示意，字幕和可读信息由后期合成并标注为AI动画情景重现。

## 出片与验收闸门

1. `build_story.py` 是剧本和45镜内容源；六段TTS文本、`story.json`、音频manifest必须逐字一致。
2. `generate.py --validate` 验证180秒规划、45镜、38个Agnes源、7张卡及音频收据。
3. `clause_times.py --check-cuts` 确认所有镜头切点落在估算分句窗内；回退对齐不宣称为强制音素级对齐。
4. 对新生成12镜及复用26镜逐镜审查接触表：情节匹配、人物/手部畸变、伪文字、画面闪变、运镜、标签；问题镜修复后复检。
5. 通过 `RENDER_REQUEST` 重新渲染，再查时长、画幅、帧率、黑帧、冻结帧、字幕起点、音频RMS/峰值/静音、音画同步，并保留测量报告。
6. 通过 `VERBATIM_REQUEST` 逐字听检，六章CER均须≤0.15。机器报告不能替代人工看片和逐字听检；所有闸门通过后才能签收。

## 本地命令

```bash
python3 production/btk/build_story.py           # 重建 story.json 和音频manifest文本
python3 production/btk/build_story.py --script  # 刷新四列表格
python3 production/btk/build_story.py --publish # 刷新发布文案
python3 production/btk/generate.py --validate
python3 production/btk/clause_times.py --check-cuts
```
