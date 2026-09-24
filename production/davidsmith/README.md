# 大卫·史密斯：无罪之后

三分钟横版（16:9）悬疑科普动画，按 `production/gilgo/` 的长岛吉尔戈海滩成片方法制作：

- 1920×1080 / 30 fps / 180 秒 / AAC 立体声
- 45 个唯一镜头：**38 个 Agnes Video V2.0 动画镜头 + 7 张后期信息卡**
- 六段中文配音，最终脚本 786 字（去标点 723 字），音色 `voice-00`
- 大号白字黑边字幕，关键词描黄；字幕切换来自 `audio/clause-times.json`
- 全片常驻「AI动画情景重现 · 非新闻影像」标签；不使用真实人物 AI 脸、不展示遗体或血腥过程

## 已完成的内容

| 文件 | 作用 |
|---|---|
| `build_story.py` | 唯一内容源：事实边界、来源、六段逐字口播、45 镜提示词、信息卡、标题、金句、音效事件 |
| `story.json` | 45 镜规划、38 个 Agnes 请求、7 张信息卡、presentation 叠字配置 |
| `抖音脚本.md` | 用户交付脚本：3 个标题、核心爆点、四列表格、金句结尾、事实边界、来源 |
| `抖音发布文案.md` | 发布正文、置顶提问、话题和发布前自查 |
| `screenplay.md` | 事实边界、逐字口播、分镜职责、制作闸门与来源 |
| `audio/raw/` | Agnes 生成前的原始 TTS 配音 |
| `audio/N01.mp3 … N06.mp3` | 收紧停顿后的成片配音；manifest 记录 SHA-256 |
| `audio/clause-times.json` | 分句起止时间；`render.py` 的 CUTS 与字幕对轨共用 |
| `qa/` / `results.json` | Agnes 片段的下载收据、SHA-256、解码信息和接触表（生成后回填） |
| `delivery/` | 出片后的 EDL、字幕、音画/电平报告、最终接触表和逐字听检 |

## 本片口播事实口径

史密斯是英国卡车司机，公开报道称其有 “Honey Monster / Lurch / Bigfoot” 等外号；本片采用“大脚怪”作为易懂说法，
不把它写成警方正式称谓。萨拉·克拉姆于 1991 年遇害；史密斯在 1993 年被判无罪，并曾向陪审团道谢。1999 年他因阿曼达·沃克案被定罪并服无期刑，随后在狱中向同仓犯人吹嘘自己已经逃过前案。

英国《刑事司法法 2003》为一罪不二审留下“新的、令人信服的证据”例外，规则后来生效；2022 年上诉法院准许重审，2023 年 5 月史密斯被判克拉姆案谋杀罪成立，终身监禁、最低刑期 27 年。本片明确区分“法律例外”与“完全废除一罪不二审”。

## 离线闸门

```bash
# 依赖：ffmpeg、fonts-noto-cjk；本地还需要 production/requirements.txt
python3 production/davidsmith/build_story.py
python3 production/davidsmith/generate.py --validate
python3 production/davidsmith/clause_times.py --check-cuts
python3 production/davidsmith/build_story.py --script
python3 production/davidsmith/build_story.py --publish
```

当前 `generate.py --validate` 已通过：45 镜、38 个 Agnes 源、7 张信息卡，六段音频 SHA-256 一致。
`clause_times.py --check-cuts` 已通过：所有切点落在分句停顿窗内。

## Agnes 生成、复审与出片

工作流已复制到 `.github/workflows/davidsmith-gen.yml`、`davidsmith-render.yml`、`davidsmith-verbatim.yml`。
它们只在固定分支 `arena/01a0d0c4-desktop-tutorial` 上工作：

```bash
# 生成全部 38 个 Agnes 动画镜头；免费额度按 75 秒节流，结果和 QA 接触表逐镜 checkpoint
printf '{"workers":2}\n' > production/davidsmith/GEN_REQUEST
git add -A && git commit -m 'davidsmith: script and audio ready' && git push origin arena/01a0d0c4-desktop-tutorial

# 发现脸、伪文字、换场或畸变，只重做坏镜头，其余按 request_hash/SHA-256 复用
printf '{"workers":1,"only":"S03,S08"}\n' > production/davidsmith/GEN_REQUEST

# 看完 qa/Sxx.jpg 后再出片
printf 'render %s\n' "$(date -u +%FT%TZ)" > production/davidsmith/RENDER_REQUEST

# 成片回填后做逐字听检
printf 'verbatim %s\n' "$(date -u +%FT%TZ)" > production/davidsmith/VERBATIM_REQUEST
```

生成器会实时把 `waiting_create_slot`、`queued`、`polling`、`media and QA ready` 等状态写入 `results.json` 并提交回分支；
不会绕过 Agnes 的每分钟限额，也不会用图片或静态图冒充缺失的动画源。每个返回片段都要过：请求哈希、下载 SHA-256、
时长/分辨率检查、完整解码和 2 fps 接触表生成。明显畸变、露脸、伪文字或中途换场的镜头不进入成片。

渲染器还会检查：45 镜各用一次、1920×1080/30 fps/180 秒、字幕时间轴、双声道、整体与逐章电平、静音占比和最终 MP4 完整解码。
最终文件名为 `交付/大卫·史密斯_无罪之后_三分钟_带声音.mp4`。
