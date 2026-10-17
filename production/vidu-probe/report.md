# Vidu 探针结果

- 时间（UTC）：`2026-10-17T14:56:31Z`
- 真提交任务：`是`

| secret 名 | 域名 | 积分查询 | 剩余积分 | 结论 |
| --- | --- | --- | --- | --- |
| `VIDU_API_KEY` | https://api.vidu.cn | HTTP 401 | None | KEY_INVALID_OR_FORBIDDEN |
| `VIDU_CN_API_KEY` | https://api.vidu.cn | HTTP 200 | None | KEY_OK |

### VIDU_CN_API_KEY @ https://api.vidu.cn 真提交结果

- POST: HTTP 400　task_id: `None`
- 最终状态: `None`　消耗积分: `None`
- 视频: （无）
- 原始响应: `{"code":400,"reason":"CreditInsufficient","message":"insufficient credits","metadata":{"trace_id":"802961edaa9c3fdbe99575e2b9e01c9a"}}`
