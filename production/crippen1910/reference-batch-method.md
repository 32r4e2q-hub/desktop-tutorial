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
