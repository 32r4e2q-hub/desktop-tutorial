# 已审参考图的存储

64 张已审图（31 个主资产及 33 张补充视图）完整保存在本分支历史中的不可变提交 `b3a0bf17dc080c80a3694ca4c460b365c9b491d9`，没有删除历史图像。

为避免最终交付补丁重复携带 107 MB 参考 PNG，当前目录的 PNG 是忽略的本地缓存。每张图的永久链接、字节数、SHA256 见 `archive-index.json`；正式审批仍以 `approvals.json` 为准。恢复全部参考图：

```sh
python3 production/crippen1910/reference_storage.py
```

恢复使用现有 Git/GitHub 连接，按不可变提交取回原始字节并逐张验证 SHA；不切换分支、不重新生图、不要求新密钥。`build_story.py` 与成片工作流会自动恢复缺失的缓存。实际图生视频请求一直引用该不可变提交，链接不变。
