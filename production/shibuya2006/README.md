# 第十七期｜涩谷短大生惨案：一句话的代价

## 当前真实状态（2026-11-16，录音与转写核验更新）

- 当前分支 `arena/749aaa18-desktop-tutorial`；main基准 `f88154470b0480277f5ca031cd6679961a6fc3b9`。
- 三条第17期工作流已改为跟随触发分支（`github.ref_name` + `arena/**`），不再写死上一轮的 `arena/<id>`，否则本轮分支上这些作业根本不会跑。
- 30镜连续时间线：180秒、平均6秒、单镜5–7秒；修订后637个含标点字符。
- 28张参考图文件已齐，逐张复核后20张签收；S01/S02已完成去雪修正，P01–P07通过。S05/S08/S11/S13已修正签收；S03/S04已移除对应电子设备并签收；8张新增角色侧向图已单独复核，角色仍需特写及部分角度修正。
- 本轮已使用10次图像生成调用，未尝试绕过每轮预算。
- 本期用户选定更低沉男声voice-01；10组连续TTS请求，9组成功、G04因服务内容审核未生成。成功源音频覆盖27镜文本，原始合计145.152秒，不是180秒母版。
- 已生成27份逐镜音频切分候选，保存在忽略目录work/。静音检测与字数先验只能辅助切分，尚未通过听检/转写，不发布最终audio/manifest.json。
- 30段无BGM确定性环境拟音已生成到work/；不是原案录音。
- 已读朝日、读卖、每日原报存档及Japan Times正文，修正“返家日=发现日”“当场认罪”“在住宅抓捕”等错误。父亲驾车送行细节仍待可靠来源，事实门禁保留。
- **30镜视频源片已全部完成**（results.json `selected_sources_ready`，run 43816274028）；成片仍未渲染。
- 录音缺口仍是 S10–S12 三句（G04 内容审核拒绝，未改词绕过）。上一轮“旁白独立转写核验”失败**不是录音问题**，是 runner 上 PyAV 与 faster-whisper 版本不匹配；现已改为 ffmpeg 解码喂数组、工作流钉 Python 3.11 并装 `production/requirements.txt`。详见 `audio/NARRATION_STATUS.md`。
- Arena 的 `voice_id` 是会话级的：本轮复用 `voice-01` 被拒（Unknown voice_id），补录三句需要重新试听选定音色或用户提供录音，不能悄悄换声线。
- 机器可读状态：STATUS.json；审核问题：reference/approvals.json；音频来源：audio/groups/manifest.json。

## 已搭建链路

光州30镜reference模板 → 28张C/S/P参考图门禁 → 不可变commit+SHA256 → Agnes 2.5 Flash reference → 720P真实运动源片 → 1080P/24fps/180秒母版。

创建与查询共享12.1秒闸门，最多2 worker；先提交再查询；遵守Retry-After；模糊POST结果暂停核对，防重复收费。生成器 `full_payload` 和 preflight 都有事实核查门禁，参考图未经签收也无法生成请求。

三层字幕保留光州共享 `gwangju_style`：逐镜白字黑边解说词、金色关键词、金色小注释、九条2秒钩子；AI源片全程禁字。已移除光州镜7的专案冻帧补丁，避免错误复用旧案画面修补；音效改为本案门声、风声、翻纸、时钟，不保留胶带和法槌提示。

独立工作流 `.github/workflows/shibuya2006.yml` 仅面向当前分支；不会触发旧光州任务。脚本来自模板的继承部分仍需实际素材集成验证，不能把离线测试通过称为成片通过。

## 续作顺序

1. **先解决录音缺口**（当前唯一硬阻塞）：S10–S12 需要真实语音。要么本轮重新试听选定一条音色后全篇逐镜重录（推荐，音色统一且一劳永逸），要么用户提供合规录音。不得用静音、旧期声音或改词绕过审核；换声线必须用户同意。见 `audio/NARRATION_STATUS.md`。
2. 逐镜合成后跑 `第17期 · 旁白独立转写核验`：报告写 `qa/narration-asr.json`，相似度 ≥0.90 才进入人工听检，工具本身不签收。
3. 听检通过后写 `audio/review.json`（每条含文本、SHA256、voice_id、复核人），再跑 `build_audio_manifest.py` 生成 `audio/manifest.json`；此时 30 条逐镜文件必须齐全。
4. 渲染：`{"mode":"render"}` 触发 `shibuya2006.yml`，内部依次跑 `build_audio_manifest.py`、`generate.py --render-only --publish`；成片与报告 commit 回当前分支。
5. `narration_fit.py`、`verify_master.py`、`qc.py`，再完整播放复核；每 5 镜开接触表抽检面部/服装/年代，失败只重做对应镜头。
6. 本期视频完成后才从成片取帧制封面，不用参考图冒充截图；保留第17期系列发布信息。

## 本地校验

`python3 production/shibuya2006/test_plan.py`：13项通过（时间线、参考数与锚点、钩子、付费失败关闭、旧案隔离、音频来源哈希、无旧案冻帧、候选未冒充最终对齐）。

`preflight.py`：当前 READY（仅离线检查；本轮没有调用 Agnes 接口）。
`python3 -m pytest production/tests -q`：206 passed / 3 skipped；其中 `test_shibuya2006_audio.py` 守转写解码（ffmpeg→float32）、工作流装配与分支口径。音频时长和 SFX 生成已实测；逐字听检、字幕对齐与成片编码仍未做。

## 本轮补充记录

- G04替代文本试音与锁定稿不一致，已隔离不用，未改动原稿审核状态。见qa/G04-alternate-note.md。
- 远端ab95d85的离线Actions运行43781538968已成功；当前本地HEAD仍为基准，未执行重置、强推或冒称本轮已推送。
- 参考图修正调用返回本轮10张限额；没有继续重试。

## 最新角色补图复核

本轮8张面部特写、2张侧面修正均已打开检查。现有16张独立补充视角，见reference/views/manifest.json。C07法庭组三人仍需独立视角与法官正侧面；角色尚未整体签收或绑定到视频请求。10次图像调用额度已用完；未启动视频生成。

## 法庭角色与参考板更新

本轮补齐法官正侧面、律师与检察官独立正面/侧面/特写，共9次图像调用。新增build_character_boards.py，以已审源图确定性排版10张角色板，全部逐张打开复核，来源哈希记录在reference/boards/manifest.json。未把角色板当作视频片段。下一步是按镜头绑定法官/律师、固定不可变参考版本并完成事实门禁；尚无视频创建请求。

## 参考绑定完成

30个最终槽位全部通过参考审核（原28组设计＋C07拆分的律师/检察官2槽位）。S24明确绑定独立律师C09；法官C07不再使用三人合影。生成器与preflight引用集合一致，新增源图哈希回归测试。事实核查仍未放行，未创建GEN_REQUEST。

## 修订开场已获用户确认，进入视频制作

已删除父亲驾车送行的未核实主张。现行30镜180秒645字符，fact_review.json绑定修订计划哈希；9项测试、preflight、generate --validate --clips-only通过。G01/G06旧音频及对应候选禁止使用。提交GEN_REQUEST请求30镜workers=2；实际创建数量以Actions日志/results.json为准，不把请求队列等同于30个成功任务。
