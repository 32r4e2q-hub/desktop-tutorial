# Agnes 国内站探针结果

- 时间（UTC）：`2026-10-18T15:25:55Z`
- 目标模型：`agnes-video-2.5-flash`
- 真提交任务：`否`

## key 指纹（不含 key 本体）

- 国际 key：sha256_12=3c1a065df259, 末4位=bflr, 长度=51

## key × 域名 矩阵

| key | 域名 | HTTP | 目标模型在列 | 备注 |
| --- | --- | --- | --- | --- |
| - | https://apihub.agnes-ai.cn | 可达性=True | - |  |
| - | https://api.agnes-ai.cn | 可达性=True | - |  |
| INTL | https://apihub.agnes-ai.cn | 200 | True | {"data":[{"id":"agnes-2.5-pro-alpha","object":"model","created":1626777600,"owned_by":"custom","supported_endpoint_types |
| INTL | https://api.agnes-ai.cn | 401 | False | {"error":{"code":"","message":"无效的令牌 (request id: 20261018152556455698716AvmNrud5)","type":"AgnesAI_error"}} |

## 结论

仓库里还没有国内站 key（未配置 AGNES_CN_API_KEY/AGNES_CN_KEY/AGNES_CN_TOKEN）。本轮只测了域名可达性与国际 key 互通性。 国际 key 打国内域名：['200', '401']（居然互通）。
