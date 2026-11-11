# 蜜月尼古丁命案：新婚第十一天

3 分钟 / 30 镜 / 180 秒 / 16:9 横屏。全部画面规划为虚构写实 3D 动画情景重现，不是历史影像。素材由 Agnes Video 2.5 Flash 生成，720P 源片后续放大至 1920×1080。

## 本轮状态

- ✅ `story.json`：30 镜、时间轴 180 秒、分镜提示词、镜头旁白草案、角色锚点、安全约束；`generate.py --validate --clips-only` 通过。
- ✅ 使用仓库已测试的 Agnes 2.5 Flash 载荷格式与共享 61 秒节流。任务完成后，生成回执和每镜接触表会写入 `results.json` / `qa/`，视频本体留在忽略目录 `work/honeymoon_nicotine/`。
- ⚠️ 当前经验证的 2.5 Flash 请求是 `mode=text`，只接受 8 个字段，不能把本地参考图以图像输入传给该端点。因此本轮将使用原脚本中的角色锚点、统一 STYLE/NEGATIVE 和参考图 ID 做文字约束；不会把文本描述冒称为已生成/已引用的图像参考。
- ⏳ 角色/场景/道具参考图：逐张提示词与定稿检查清单见 `reference/REFERENCE_PACK.md`，尚待使用可接受图像参考输入的工具生成。真实片段生成完成后还需逐 5 镜抽检；接触表不能替代人工审片。
- ⏳ 中文旁白：待用户选择试听音色后逐镜生成；字幕、音效、封面、最终 1080P 合成及 QC 尚未完成。
- ⚠️ 判决、保险、时间线、前女友相关口播先按用户脚本梳理；发布前应逐项对照法院或新闻来源核实。所有内容均标注为情景复原，不披露可模仿的致害细节。

## 生成

```bash
python3 production/honeymoon_nicotine/build_story.py
python3 production/honeymoon_nicotine/generate.py --validate --clips-only
```

`.github/workflows/honeymoon-nicotine-gen.yml` 只监听本项目的 `GEN_REQUEST` marker。默认 payload 为 `{"mode":"clips","workers":2}`，采用共享 61 秒创建间隔、尊重服务端 Retry-After；不会根据月卡假设擅自提高频率。完成后才准备旁白、字幕与成片工作流。
