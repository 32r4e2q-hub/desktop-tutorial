# 金大斗：一条牛仔裤，牵出十七条人命

## 当前状态（2026-10-14）

**这是制作中的项目，不是已交付成片。当前已生成视频片段：0。**

- 用户上传原稿已归档并备份到Google Drive。
- 六章旁白共803字（含标点），不是把原稿过长的29段旁白硬塞进180秒。
- 45镜规划 = 38个Agnes动画镜头 + 7张信息卡；每个镜头使用一次。
- 参考引擎来自用户指定的 `production/zama2017`（日本座间九人案），没有复用该片的旁白或素材。
- 输出目标：180秒、16:9、1920×1080、30fps。Agnes 2.5-flash计划生成720P素材，输出1080p为合成放大，**不是原生1080p素材**。
- 人物统一衣着、背影与手部；受害者以生活空间和空座位致意，不重演暴力与行刑。
- 中文标题、数字、字幕均后期添加，常驻「AI动画情景重现·非新闻影像」。

## Agnes实测与费用阻塞

今天的校验工作流：[38502424746](https://github.com/32r4e2q-hub/desktop-tutorial/actions/runs/38502424746)。原始响应保存于 `probe/report.json`。

|模型|今日实际响应|能说明什么|
|---|---|---|
|agnes-video-v2.0|503 model_not_found / 无可用通道|当前不能用旧模板直接生成|
|agnes-video-2.5|400 prompt is required|校验到参数层，不证明免费或可成功出片|
|agnes-video-2.5-flash|400 prompt is required|候选模型；同样未证明免费生成|

校验使用空prompt、无效时长/帧数，没有提交有效视频生成任务。模型清单GET返回200是清单读取成功；原始报告中model_list下的unexpected_acceptance_stop是旧分类器标签，不代表接收了视频任务，新代码已区分。

仓库2026-10-12的旧报告还记录：v2.0无通道，2.5余额不足，2.5-flash提交时持续队列满。**队列满不是免费证明，模型名字带Flash也不是免费证明。**

`billing-policy.json`默认关闭：不凭模型列表/参数校验打开，不尝试收费型号；明确没有智谱回退。必须拿到当前账号的免费权益/价格证据，才能试一个Agnes片段；试片成功且人工复审通过后才可批量生成。该文件是本地防误操作闸门，**不能强制供应商不扣费**。

## 文件与恢复

- `build_story.py`：唯一内容源；运行后写story、逐字旁白manifest、制作脚本和发布文案。
- `generate.py`：仅Agnes 2.5-flash新payload；默认只校验，不产生任何视频请求。
- `render.py`：座间案引擎副本，配音混音、字幕、信息卡、实测音量等保留；CUTS当前是规划占位，`edit-status.json`阻止过早渲染。
- `template-origin.json`：参考源commit、文件清单、未复用音视频的记录。
- `probe/report.json`：今天的真实模型校验结果。
- `audio/manifest.json`：逐字旁白；未选音色、未生成配音前不能填虚假的voice_id/SHA。
- `results.json`：未来逐镜记录任务ID、请求哈希、视频URL和下载SHA；目前没有此文件，因为未提交生成。
- `external-checkpoints.json`：Linear、Notion、Drive入口。

固定工作分支：`arena/09864331-desktop-tutorial`。脚本和状态已推到这条分支，不能切去其他分支继续。

恢复顺序：查看Linear BOB-5 → 阅读Notion交接 → 拉取固定分支 → 查看probe、billing-policy、results和edit-status → 恢复已有任务而非重提。若创建请求丢失响应，必须先核对供应商任务，不能盲目重复创建。

Linear/Notion是记录系统，Drive是文件存储，**它们不会阻止Arena沙箱重置，也不会自动执行生成**。仅沙箱进程不具备永久执行保障。GitHub Actions是当前可访问Agnes且可使用已有Secret的执行环境；其免费额度与Agnes免费额度是两回事。

## 本地检查

```bash
python3 production/kimdaedoo/build_story.py
python3 production/kimdaedoo/generate.py --validate  # 仅计划与文本一致性，不代表配音完成
python3 production/kimdaedoo/generate.py --validate --require-audio  # 无配音时必须失败
python3 -m pytest production/tests -q
```

本轮离线测试：138 passed、13 skipped、125 subtests passed。跳过项含本地缺ffmpeg/中文字体的媒体测试；不能据此声称成片或排字已通过检查。仓库既有智谱工作流的runner硬编码导致首次CI失败，现仅改为仓库通用runner变量开关，**没有修改它的触发文件或执行智谱请求**。

## 下一步

1. 试听并选旁白音色，生成本片六章配音，不复用旧片音频。
2. 收紧长静音，实测总时长（目标变速比0.86–1.10），按实际分句重对CUTS与字幕；时间网格不是最终剪辑表。
3. 核实当前账号Agnes 2.5-flash免费权益，价格未明时停止真实生成；确认后只试S01，不批量试错。
4. 试片通过后，用75秒提交间隔、队列满分钟级退避和逐镜断点生成。未知提交错误标记ambiguous并停机，不丢弃任务ID重新花额度。
5. 每段素材立即归档Drive或其他持久存储；CDN链接、临时artifact和沙箱磁盘都不能当永久备份。
6. 配音/字幕/音量测量、镜头复审、全帧QC、人工语义与整片试听均通过后才交付带声音的三分钟MP4。

## 事实口径

主要依据韩国先驱报2017-05-26（55天17人、洗衣工报警、1976年12月执行）。次级来源只作对照。具体首次案发日、老板年龄、具体逮捕动作与守候取衣经过、共犯姓名/全部责任、赃款总额没有足够一手支持，制作稿不采用。最后执行日期仅说「1976年12月」，不把二手记录的具体日与地点提升为已核实事实。详细出处在制作脚本内。
