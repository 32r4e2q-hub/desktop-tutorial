# 一次性补齐角色视图的云端队列

本批计划：10张侧面、10张背面、9张面部特写，共29张缺失视图，另修订P02男肖像，共30个独立图生图请求。

依据：2026-11-02读取 Agnes 官方文档
https://wiki.agnes-ai.com/en/docs/agnes-image-25-flash.md

- `POST https://apihub.agnes-ai.com/v1/images/generations`
- `model=agnes-image-2.5-flash`，`size=1K`，单人视图`ratio=3:4`。
- 按文档示例把现有角色PNG以Data URI放入`extra_body.image`，不是纯文字重画。
- `extra_body.response_format=url`，同步响应读取`data[0].url`，再下载和解码验证。
- 每张为独立图像，非拼图；原正面图不覆盖，C01已有面部图不重复生成。
- 首张C01_side作为接口金丝雀，成功下载后同一运行继续余下29张；最多2个worker，创建间隔至少12秒。429尊重退避；网络结果不明不自动重复提交。
- `batch-results.json`记录输入SHA、请求SHA、返回URL、输出SHA、尺寸与状态，不存密钥或Base64请求正文。
- 候选图与接触表会提交到当前固定分支。生成成功不等于审核通过，不自动跳到视频。

工作流：`.github/workflows/crippen1910-reference-batch.yml`。
触发文件：`production/crippen1910/REFERENCE_BATCH_REQUEST`。

验证：
```
python3 production/crippen1910/batch_references.py --validate
python3 -m unittest production.tests.test_crippen_reference_batch -q
```

## 实际结果与质量限制

- 全30请求批次41469730755成功，之后6请求修订批次41472228725成功。每次运行的独立收据在 `reference/batch-runs/`，最新 `batch-results.json` 仅代表最新6项修订，不能误读为完整批次。
- 当前64张主/补充参考文件均已存在；完整编号总览为 `reference-overview.pdf`，当前内容SHA为 `reference/inventory.json`。
- 反复实际检查发现：多图姿态引导未能可靠保证严格侧视，且可能混入配饰、人物或身体片段。不能因为API返回200便批准。
- 7张侧视通过Arena图像编辑工具另做并替换，来源为各自正面图+已核实90度姿态图。C05的黑裤修正版被拒收，未覆盖白制服正面标准。
- 当前方案改用姿态参考+头部裁切，P02只输入报纸本身，避免将参考人物实体合成进报纸。仍有C05_side、C06_side、C08_side需重做。
- 面部裁切和报纸平面印刷肖像合成有独立可复现脚本与SHA收据，不冒充新的API生成。
- 无参考图批准，无视频提交；视频闸门保持关闭。
