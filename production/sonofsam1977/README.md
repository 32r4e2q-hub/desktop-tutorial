# 山姆之子：一张25美元的罚单

三分钟横屏（16:9 · 1920×1080 · 24fps · 180 秒）中文悬疑 3D 动画短片。
**30 个 Agnes Video 2.5 Flash 连续运动镜头**（720P 源片，`mode=reference` + 定稿参考图，后期放大到 1080P），
一镜一句中文旁白（悬疑低沉男声 voice-00），字幕与配音同起止，原创程序合成 BGM 与音效。

> 画面为 AI 动画情景重现，不是历史影像。全片不出现遗体、伤口、血腥、开枪过程或受害者特写；
> 枪支只以剪影或静物出现；凶手始终是没有面容的黑影；所有真实人物一律为风格化形象，不复制任何真实相貌。

## 一句话卖点

1977 年，让纽约恐慌 13 个月的连环枪手「山姆之子」，竟是被一张 25 美元的停车罚单抓住的——
一位遛狗的邻居看见凶手从黄色福特车上取走了那晚警察开出的罚单，车牌指向扬克斯，大案就此破了。

## 结构（九段 / 30 镜）

| 段 | 时间 | 镜号 | 内容 | 色调 |
|---|---|---|---|---|
| N1 开头钩子 | 0:00–0:10 | S01–S02 | 罚单被风吹过夏夜街头，落上黄色福特的挡风玻璃 | 夏夜（橙黄+冷青） |
| N2 夏夜 | 0:10–0:35 | S03–S06 | 布朗克斯消防栓嬉水、车内情侣、街角黑影、警灯警戒线 | 夏夜 |
| N3 恐慌的城市 | 0:35–1:00 | S07–S10 | 各区夜景蒙太奇、发型店、迪斯科、报摊头条 | 夏夜 |
| N4 来信与专案组 | 1:00–1:25 | S11–S14 | 现场拾信、专案组办公室、专栏作家拆信、信纸红圈日期 | 追查（冷蓝白） |
| N5 罚单与目击者 | 1:25–1:48 | S15–S18 | 布鲁克林黄车与巡警开罚单、黑影取走罚单、戴维斯遛狗目击 | 夏夜 |
| N6 电话那头 | 1:48–2:10 | S19–S22 | 探长翻罚单发现扬克斯车牌、拨号电话飞到扬克斯调度室 | 追查 |
| N7 扬克斯的邻居 | 2:10–2:30 | S23–S25 | 松树街公寓、山姆·卡尔与拉布拉多、警局会议桌 | 夏夜/追查 |
| N8 抓捕 | 2:30–2:48 | S26–S28 | 公寓外埋伏、伯科维茨走出大门、「好吧，你们抓到我了」 | 夏夜 |
| N9 结尾钩子 | 2:48–3:00 | S29–S30 | 欢庆人群转暖金、回到罚单特写，金色片名与互动提问 | 暖金 |

## 当前状态

| 环节 | 状态 | 位置 |
|---|---|---|
| 定稿参考图 | 🟡 20/25 张已生成（C01–C10、SC01–SC10），P01–P05 待生成，逐张审核后写入 `reference/revision.txt` | `reference/` |
| 分镜 / 事实边界 / 提示词 | ✅ 30 镜、180 秒；生成器自动拼接三色调 STYLE + 角色锚点 + 参考图说明 + NEGATIVE | `build_story.py`、`story.json` |
| 一镜一句旁白 | 🟡 S01–S10 已录（voice-00，悬疑低沉男声），S11–S30 待录（TTS 每轮上限 10 条） | `audio/manifest.json` |
| 离线自检 | ⏳ `python3 -m unittest production.tests.test_sonofsam1977 -q` | `production/tests/` |
| Agnes 片段 | ⏳ `GEN_REQUEST` push 后生成，进度看 `results.json` | `results.json`、`qa/` |
| 成片 / 封面 / 字幕 | ⏳ 等旁白齐 + 素材齐后 `RENDER_REQUEST` | `交付/` |

## 怎么跑

```bash
python3 production/sonofsam1977/build_story.py                        # 重建 story.json / 清单 / 脚本（跑两遍才会记录音频 sha）
python3 production/sonofsam1977/generate.py --validate --clips-only   # 无配音也能验的分镜闸门
python3 production/sonofsam1977/publish_reference.py --check          # 参考图齐不齐
python3 -m unittest production.tests.test_sonofsam1977 -q
```

云端（沙箱 token 没有 `actions:write`，只能用 marker 文件 push 触发）：

| 触发文件 | 作用 |
|---|---|
| `production/sonofsam1977/GEN_REQUEST` | `{"mode":"clips","workers":5}` 生成 30 条片段；单镜重做写 `{"only":"S07"}` |
| `production/sonofsam1977/RENDER_REQUEST` | 旁白齐了之后只做 1080P 出片（拼接 / 字幕 / 混音 / 封面） |
| `production/sonofsam1977/QC_REQUEST` | 只跑成片质检（**优先级最高**，想重渲先删掉它） |

## 规格

- **模型**：`agnes-video-2.5-flash`，`size=720P`、`aspect_ratio=16:9`、`mode=reference`、`n=1`、`images=[定稿参考图公网不可变地址]`，月卡配速 12 秒/条、5 并发（见 `AGNES-2.5-Flash调用方法.md`）。
- **成片**：1920×1080 · 24fps · 180.0s · 48kHz 立体声；字幕 ASS 白字黑边、关键词金色放大；常驻标签「AI动画情景复原 · 非真实影像」。
- **安全**：NEGATIVE 拒绝遗体/血腥/开枪/枪口火光/受害者特写/可读文字；黑影角色设定固定无面容、枪支不举起；离线测试 `test_sensitive_imagery_is_never_requested` 守住这条线。
- **交付**：`交付/山姆之子_一张25美元的罚单_三分钟_带声音.mp4` + `山姆之子_封面.jpg/.png` + `山姆之子_字幕.srt` + `山姆之子_技术报告.json`（另有 SonOfSam1977_* 四件别名）。
