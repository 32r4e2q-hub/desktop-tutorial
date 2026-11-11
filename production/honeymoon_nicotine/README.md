# 蜜月尼古丁命案：新婚第十一天

3 分钟 / 30 镜 / 180 秒 / 16:9 横屏。全部画面规划为虚构写实 3D 动画情景重现，不是历史影像。素材由 Agnes Video 2.5 Flash 生成，720P 源片后续放大至 1920×1080。

## 本轮状态

- ✅ `story.json`：30 镜、时间轴 180 秒、分镜提示词、镜头旁白草案、角色锚点、安全约束；`generate.py --validate --clips-only` 通过。
- ✅ 使用仓库已测试的 Agnes 2.5 Flash 载荷格式与共享 12 秒节流。任务完成后，生成回执和每镜接触表会写入 `results.json` / `qa/`，视频本体留在忽略目录 `work/honeymoon_nicotine/`。
- ✅/🟡 参考图已逐张生成并查看：C01–C05、C07–C08、S01酒店外观第二版已存入 `reference/`；C06徽章需重生成，S01走廊、S02–S16及P01–P06尚未生成。逐张 QA 见 `reference/REFERENCE_QC.md`。仓库当前分支未找到名为“安城双尸案”的项目目录，采用仓库 Agnes 2.5 Flash 的 `setagaya2000` / `somerton` 参考流程。
- ⚠️ 仓库当前经验证的 Agnes 2.5 Flash adapter 使用 `mode=text`，其 8 字段请求不包含图像输入。图已作为制作参考生成，但不能声称它们已经被 Agnes 视频请求引用；视频重新启动前需确认可用的图像输入接口或接受文本模式限制。当前视频批次已经取消；停止记录在 `results.json`，不代表服务端任务可撤销。
- ⏳ 30个视频片段尚未完成；生成后仍需逐5镜抽检。接触表不能替代人工审片。
- 🟡 中文旁白：用户已选择低沉悬疑男声 `voice-00`，已生成 S01–S10 的第一批试听/制作音频；因脚本复核调整，S04/S05 待按最终台词重生成。字幕、音效、封面、最终 1080P 合成及 QC 尚未完成。
- ⚠️ 判决、保险、时间线、前女友相关口播先按用户脚本梳理；发布前应逐项对照法院或新闻来源核实。所有内容均标注为情景复原，不披露可模仿的致害细节。

## 生成

```bash
python3 production/honeymoon_nicotine/build_story.py
python3 production/honeymoon_nicotine/generate.py --validate --clips-only
```

`.github/workflows/honeymoon-nicotine-gen.yml` 只监听本项目的 `GEN_REQUEST` marker。默认 payload 为 `{"mode":"clips","workers":2}`，采用共享 12 秒创建间隔（每分钟最多 5 次）、尊重服务端 Retry-After；只在参考图逐张定稿后移除 CANCEL_REQUEST 并启动视频请求。完成后才准备旁白、字幕与成片工作流。
