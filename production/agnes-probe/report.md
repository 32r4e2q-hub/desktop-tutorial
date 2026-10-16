# Agnes 模型可用性探测报告

- 探测时间（UTC）：`2026-10-16T07:30:46Z`
- 接口基址：`https://apihub.agnes-ai.com`
- key 可用：`是`
- 模式：`付费实测（真的提交生成任务）`

| 模型 | 类型 | 判定 | HTTP | 说明 |
| --- | --- | --- | --- | --- |
| `agnes-video-2.5` | video | 模型存在（通过了模型名校验） | 400 |  |
| `agnes-video-2.5-flash` | video | 可用（请求被受理） | 200 | 第 5 次提交被受理 |

## 模型清单接口

- `/v1/models` → HTTP 200，列出 10 个模型

  ```
  agnes-2.5-pro-alpha
  agnes-video-2.5-flash
  agnes-3.0-flash
  agnes-image-2.1-flash
  agnes-video-2.5
  agnes-image-2.0-flash
  agnes-2.5-flash
  agnes-3.0-pro
  agnes-2.5-pro-beta
  agnes-image-2.5-flash
  ```
- `/v1/model/list` → HTTP 404（未返回模型列表）
- `/openapi.json` → HTTP 403（未返回模型列表）

## 原始响应摘录

```json
[
  {
    "model": "agnes-video-2.5",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 20261016073047605586671zn6ieM72)\",\"data\":null}",
      "elapsed_s": 0.3,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 20261016073047605586671zn6ieM72)"
    },
    "2.5-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 202610160731578952292516jfBWSiG)\",\"data\":null}",
      "elapsed_s": 0.29,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 202610160731578952292516jfBWSiG)"
    },
    "verdict": "MODEL_ACCEPTED"
  },
  {
    "model": "agnes-video-2.5-flash",
    "kind": "video",
    "mode": "spend",
    "status": 200,
    "verdict": "ACCEPTED",
    "video_id": "task_7dSNNBCUzfnQQygImVbcQaMhG8Bfy0UT",
    "task_id": "task_7dSNNBCUzfnQQygImVbcQaMhG8Bfy0UT",
    "attempts": [
      {
        "attempt": 1,
        "at": "07:36:08Z",
        "error": "Could not create video task after 1 attempts; last problem: HTTP 503: video queue is full, please retry later (request id: 20261016073608902431585a98PNgqf)"
      },
      {
        "attempt": 2,
        "at": "07:39:09Z",
        "error": "Could not create video task after 1 attempts; last problem: HTTP 503: video queue is full, please retry later (request id: 20261016073909202038344BKDHnvH8)"
      },
      {
        "attempt": 3,
        "at": "07:42:09Z",
        "error": "Could not create video task after 1 attempts; last problem: HTTP 503: video queue is full, please retry later (request id: 20261016074209563203093fZQN4T9r)"
      },
      {
        "attempt": 4,
        "at": "07:45:09Z",
        "error": "Could not create video task after 1 attempts; last problem: HTTP 503: video queue is full, please retry later (request id: 202610160745098707801813qEakoYA)"
      }
    ],
    "accepted_on_attempt": 5,
    "accepted_at": "07:48:09Z",
    "detail": "第 5 次提交被受理",
    "video_url": "https://platform-outputs.agnes-ai.space/videos/agnes-video-2.5/task_7dSNNBCUzfnQQygImVbcQaMhG8Bfy0UT.mp4",
    "final_status": "completed"
  }
]
```
