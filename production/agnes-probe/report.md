# Agnes 模型可用性探测报告

- 探测时间（UTC）：`2026-10-16T07:09:44Z`
- 接口基址：`https://apihub.agnes-ai.com`
- key 可用：`是`
- 模式：`付费实测（真的提交生成任务）`

| 模型 | 类型 | 判定 | HTTP | 说明 |
| --- | --- | --- | --- | --- |
| `agnes-video-v2.0` | video | 模型不可用（被拒绝/已下线） | 503 |  |
| `agnes-video-v2.0-flash` | video | 模型不可用（被拒绝/已下线） | 503 |  |
| `agnes-video-2.5` | video | 模型存在（通过了模型名校验） | 400 |  |
| `agnes-video-2.5-flash` | video | 模型可用，但队列/通道忙（稍后重试） | - | Could not create video task after 6 attempts; last problem: HTTP 503: video queue is full, please retry later (request id: 20261016072329681588445FOeBCV8h) |
| `agnes-2.5-flash` | text | 可用（请求被受理） | 200 | {"id":"9e3c25b763cf484e8b04671961cf4376","created":1792135480,"model":"agnes-2.5-flash","object":"chat.completion","choices":[{"finish_reason":"length","index":0,"message":{"content":"","role":"assistant","reasoning_cont |

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
    "model": "agnes-video-v2.0",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261016070946372017293YsJv6zuq)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.32,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261016070946372017293YsJv6zuq) code=model_not_found type=AgnesAI_error"
    },
    "2.5-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261016071056655021475VjbfZ89V)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.28,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261016071056655021475VjbfZ89V) code=model_not_found type=AgnesAI_error"
    },
    "verdict": "MODEL_REFUSED"
  },
  {
    "model": "agnes-video-v2.0-flash",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261016071206933979572ObDM7ZT2)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.28,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261016071206933979572ObDM7ZT2) code=model_not_found type=AgnesAI_error"
    },
    "2.5-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261016071317251739160cOzLWvy8)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.32,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261016071317251739160cOzLWvy8) code=model_not_found type=AgnesAI_error"
    },
    "verdict": "MODEL_REFUSED"
  },
  {
    "model": "agnes-video-2.5",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 20261016071427555940113JDmTihP5)\",\"data\":null}",
      "elapsed_s": 0.31,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 20261016071427555940113JDmTihP5)"
    },
    "2.5-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 202610160715378765543999ReSt06V)\",\"data\":null}",
      "elapsed_s": 0.3,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 202610160715378765543999ReSt06V)"
    },
    "verdict": "MODEL_ACCEPTED"
  },
  {
    "model": "agnes-video-2.5-flash",
    "kind": "video",
    "mode": "spend",
    "status": null,
    "detail": "Could not create video task after 6 attempts; last problem: HTTP 503: video queue is full, please retry later (request id: 20261016072329681588445FOeBCV8h)",
    "verdict": "QUEUE_FULL"
  },
  {
    "model": "agnes-2.5-flash",
    "kind": "text",
    "attempts": [
      {
        "ok": true,
        "status": 200,
        "raw": "{\"id\":\"9e3c25b763cf484e8b04671961cf4376\",\"created\":1792135480,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user is asking me to reply with\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tokens_details\":{\"reasoning_tokens\":8,\"text_tokens\":0},\"prompt_tokens_details\":{\"cached_tokens\":256}},\"metadata\":{\"weight_version\":\"default\"}}",
        "elapsed_s": 0.7,
        "verdict": "ACCEPTED",
        "detail": "{\"id\":\"9e3c25b763cf484e8b04671961cf4376\",\"created\":1792135480,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user is asking me to reply with\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tok",
        "path": "/v1/chat/completions",
        "reply": "",
        "reported_model": "agnes-2.5-flash",
        "usage": {
          "completion_tokens": 8,
          "prompt_tokens": 291,
          "total_tokens": 299,
          "completion_tokens_details": {
            "reasoning_tokens": 8,
            "text_tokens": 0
          },
          "prompt_tokens_details": {
            "cached_tokens": 256
          }
        }
      }
    ],
    "verdict": "ACCEPTED",
    "status": 200,
    "detail": "{\"id\":\"9e3c25b763cf484e8b04671961cf4376\",\"created\":1792135480,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user is asking me to reply with\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tok",
    "reported_model": "agnes-2.5-flash",
    "reply": "",
    "usage": {
      "completion_tokens": 8,
      "prompt_tokens": 291,
      "total_tokens": 299,
      "completion_tokens_details": {
        "reasoning_tokens": 8,
        "text_tokens": 0
      },
      "prompt_tokens_details": {
        "cached_tokens": 256
      }
    }
  }
]
```
