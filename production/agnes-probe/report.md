# Agnes 模型可用性探测报告

- 探测时间（UTC）：`2026-10-12T07:44:53Z`
- 接口基址：`https://apihub.agnes-ai.com`
- key 可用：`是`
- 模式：`付费实测（真的提交生成任务）`

| 模型 | 类型 | 判定 | HTTP | 说明 |
| --- | --- | --- | --- | --- |
| `agnes-video-2.5-flash` | video | 无法判定（需人工看原文） | - | Could not create video task after 4 attempts; last problem: HTTP 503: video queue is full, please retry later (request id: 20261012074920143444574nOg9ATlc) |

## 模型清单接口

- `/v1/models` → HTTP 200，列出 11 个模型

  ```
  agnes-2.5-pro-alpha
  agnes-video-2.5-flash
  agnes-3.0-flash
  agnes-image-2.1-flash
  agnes-video-2.5
  agnes-image-2.0-flash
  agnes-2.5-flash
  agnes-3.0-flash-max
  agnes-2.5-pro
  agnes-2.5-pro-beta
  agnes-image-2.5-flash
  ```
- `/v1/model/list` → HTTP 404（未返回模型列表）
- `/openapi.json` → HTTP 403（未返回模型列表）

## 原始响应摘录

```json
[
  {
    "model": "agnes-video-2.5-flash",
    "kind": "video",
    "mode": "spend",
    "status": null,
    "detail": "Could not create video task after 4 attempts; last problem: HTTP 503: video queue is full, please retry later (request id: 20261012074920143444574nOg9ATlc)",
    "verdict": "UNKNOWN"
  }
]
```
