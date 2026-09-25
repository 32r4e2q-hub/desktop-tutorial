# BTK：软盘里的名字

本项目依照仓库根目录 [`新题目开工手册.md`](../../新题目开工手册.md) 与吉尔戈成片流程制作。视觉基准为《吉尔戈海滩：披萨盒里的凶手》的手绘二维动画纪录片风格，不修改或复用参考片内容。

- 固定分支：`arena/01a0d661-desktop-tutorial`
- 目标：横版16:9，1920×1080，30fps，180秒
- 正片镜头：45镜 = 38段 Agnes Video V2.0 动画 + 7张后期信息卡；每镜只用一次
- 片尾：另有3.8秒 END 信息卡，不计入45个正片镜头；脚本表格明确标注
- 剧本：[`抖音脚本.md`](抖音脚本.md)，六段口播788字（不含标点），时间轴来自收紧后的配音
- 事实底稿：[`screenplay.md`](screenplay.md)
- 制作与复核记录：[`制作过程.md`](制作过程.md)
- 视频来源回执与接触表：`results.json`、`qa/`

## 目前状态（2026-09-25，第二轮）

- 六段 `voice-00` 普通话配音已生成并核对哈希；时长159.53秒，排入168秒口播槽位，整体变速0.950×。口播与故事源逐字一致；39个切点通过分句时间窗检查（其中部分时间为已标注的比例／能量回退估计，不宣称音素级对齐）。
- 产线已整体迁移到 `arena/01a0d661-desktop-tutorial` 分支续作：`btk-gen/btk-render/btk-verbatim` 工作流、`generate.py`、`watch_run.py`、`story.json` 的分支绑定全部改绑，历史分支只留既有回执。
- 九镜返修续跑（`36084719543`）完成后第二轮接触表复审：S01、S03、S21、S23 通过；S02（电视边框伪字 YEIA/6S18）、S24（米色外套+白色圆毂，出现被禁的中心孔）、S35（倒下样本管带白色标签带）、S41（卡匣呈六角形而非直角方形）、S44（手触碰软盘且硬壳弯折）拒收，提示词已再次收紧，`GEN_REQUEST` 现只重做这五镜。
- 新增 `btk-review.yml` 复审包工作流（`REVIEW_REQUEST` 触发）：按 SHA-256 回执回填 38 段源素材，逐镜产出全时长均匀 16 帧、640×360 抽帧条与冻结/闪变/硬切指标，commit 回 `qa-full/`。沙箱连不上 Agnes CDN、也读不到 Actions 日志，Git 是唯一通道，接触表细节不足以定案。
- `.github/workflows/btk-*.yml` 已安装；生成会按工作流的速率限制执行。历史 `delivery/` 文件来自先前初剪，不能冒充本轮最终成片。
- **当前没有经完整画面复审、音画同步检查和逐字听检通过的最终MP4；不标记为交付完成。**

## 案情边界

- 受害者口径为十名；案发于堪萨斯州威奇托地区，1974—1991年。
- Dennis Rader是Park City法规执行员、Christ Lutheran Church会众委员会主席；不称为市议会议员。
- 软盘已删Word文件的元数据留下Dennis与教会电脑线索；不能称它单独定罪。
- 女儿的大学诊所医学样本经法律程序调取用于亲缘DNA比对，只是亲缘线索，不是直接或“完美匹配”。
- 2005年是认罪及量刑程序；不作无来源的心理判断。
- 软盘于2005年2月16日寄出，雷德于2月25日被捕，脚本称“九天后的手铐”。
- 画面避免血腥再现、受害者肖像、伪文字和镜头中途换场；真实人物只用克制示意，字幕和可读信息由后期合成并标注为AI动画情景重现。

## 出片与验收闸门

1. `build_story.py` 是剧本和45镜内容源；六段TTS文本、`story.json`、音频manifest须逐字一致。
2. `generate.py --validate` 验证180秒规划、45个正片镜头、38个Agnes源、7张卡及音频收据；`clause_times.py --check-cuts` 验证镜头切点。
3. 复审三条返修镜，并对其余35个复用镜头进行逐镜检查：情节匹配、人物/手部、伪文字/肖像、畸变、闪变、运镜及中途换场。接触表只能辅助，不代替完整片段审看。
4. 所有视觉素材过闸后，通过 `RENDER_REQUEST` 重新渲染；复核时长、画幅、帧率、黑帧、冻结帧、字幕起点、音频RMS/峰值/静音、双声道及音画同步，保存报告。
5. 通过 `VERBATIM_REQUEST` 做逐章逐字听检，六章CER均须≤0.15。机器报告不能替代人工看片和逐字听检；所有闸门通过后才能签收。

## 本地命令

```bash
python3 production/btk/build_story.py           # 重建 story.json 和音频manifest文本
python3 production/btk/build_story.py --script  # 刷新四列表格
python3 production/btk/build_story.py --publish # 刷新发布文案
python3 production/btk/generate.py --validate
python3 production/btk/clause_times.py --check-cuts
```
