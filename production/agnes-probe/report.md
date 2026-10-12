# Agnes 模型可用性探测报告

- 探测时间（UTC）：`2026-10-12T07:11:29Z`
- 接口基址：`https://apihub.agnes-ai.com`
- key 可用：`是`
- 模式：`零成本校验探测（不生成视频）`

| 模型 | 类型 | 判定 | HTTP | 说明 |
| --- | --- | --- | --- | --- |
| `agnes-video-v2.0` | video | 模型不可用（被拒绝/已下线） | 503 |  |
| `agnes-video-2.5` | video | 模型存在（通过了模型名校验） | 400 |  |
| `agnes-video-v2.0-flash` | video | 模型不可用（被拒绝/已下线） | 503 |  |
| `agnes-video-2.5-flash` | video | 被限流（模型存在） | 429 |  |
| `agnes-2.0-flash` | text | 模型不可用（被拒绝/已下线） | 503 | No available channel for model agnes-2.0-flash under group default (distributor) (request id: 202610120712283774808654SVpYfAC) code=model_not_found type=AgnesAI_error |
| `agnes-2.5-flash` | text | 可用（请求被受理） | 200 | {"id":"28af888810f34a0d9ad60f78dbbbbd1f","created":1791789155,"model":"agnes-2.5-flash","object":"chat.completion","choices":[{"finish_reason":"length","index":0,"message":{"content":"","role":"assistant","reasoning_cont |

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
    "model": "agnes-video-v2.0",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261012071130568751398GvUzk1ia)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.23,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261012071130568751398GvUzk1ia) code=model_not_found type=AgnesAI_error"
    },
    "2.5-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261012071137786369709mluPMqgO)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.21,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261012071137786369709mluPMqgO) code=model_not_found type=AgnesAI_error"
    },
    "verdict": "MODEL_REFUSED"
  },
  {
    "model": "agnes-video-2.5",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 202610120711454195296sutH8hOo)\",\"data\":null}",
      "elapsed_s": 0.23,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 202610120711454195296sutH8hOo)"
    },
    "2.5-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 20261012071152239650888NuaW9HK7)\",\"data\":null}",
      "elapsed_s": 0.23,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 20261012071152239650888NuaW9HK7)"
    },
    "verdict": "MODEL_ACCEPTED"
  },
  {
    "model": "agnes-video-v2.0-flash",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261012071159461959993RpLDpCzI)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.21,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261012071159461959993RpLDpCzI) code=model_not_found type=AgnesAI_error"
    },
    "2.5-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261012071206689222537E9mH96mr)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.23,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261012071206689222537E9mH96mr) code=model_not_found type=AgnesAI_error"
    },
    "verdict": "MODEL_REFUSED"
  },
  {
    "model": "agnes-video-2.5-flash",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 429,
      "raw": "{\"error\":{\"message\":\"You’ve reached the API rate limit for free users. Upgrade to a Token Plan to unlock higher limits and continue using the API without interruption. (request id: 20261012071213916277729DlaRGu7z)\",\"type\":\"AgnesAI_error\",\"param\":\"\",\"code\":\"rate_limit_exceeded\"}}",
      "elapsed_s": 0.23,
      "verdict": "RATE_LIMITED",
      "detail": "You’ve reached the API rate limit for free users. Upgrade to a Token Plan to unlock higher limits and continue using the API without interruption. (request id: 20261012071213916277729DlaRGu7z) code=rate_limit_exceeded type=AgnesAI_error"
    },
    "2.5-shape": {
      "ok": false,
      "status": 429,
      "raw": "{\"error\":{\"message\":\"You’ve reached the API rate limit for free users. Upgrade to a Token Plan to unlock higher limits and continue using the API without interruption. (request id: 20261012071221145189951VJpr5zN5)\",\"type\":\"AgnesAI_error\",\"param\":\"\",\"code\":\"rate_limit_exceeded\"}}",
      "elapsed_s": 0.23,
      "verdict": "RATE_LIMITED",
      "detail": "You’ve reached the API rate limit for free users. Upgrade to a Token Plan to unlock higher limits and continue using the API without interruption. (request id: 20261012071221145189951VJpr5zN5) code=rate_limit_exceeded type=AgnesAI_error"
    },
    "verdict": "RATE_LIMITED"
  },
  {
    "model": "agnes-2.0-flash",
    "kind": "text",
    "attempts": [
      {
        "ok": false,
        "status": 503,
        "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-2.0-flash under group default (distributor) (request id: 202610120712283774808654SVpYfAC)\",\"type\":\"AgnesAI_error\"}}",
        "elapsed_s": 0.23,
        "verdict": "MODEL_REFUSED",
        "detail": "No available channel for model agnes-2.0-flash under group default (distributor) (request id: 202610120712283774808654SVpYfAC) code=model_not_found type=AgnesAI_error",
        "path": "/v1/chat/completions",
        "reported_model": null
      }
    ],
    "verdict": "MODEL_REFUSED",
    "status": 503,
    "detail": "No available channel for model agnes-2.0-flash under group default (distributor) (request id: 202610120712283774808654SVpYfAC) code=model_not_found type=AgnesAI_error",
    "reported_model": null,
    "reply": null,
    "usage": null
  },
  {
    "model": "agnes-2.5-flash",
    "kind": "text",
    "attempts": [
      {
        "ok": true,
        "status": 200,
        "raw": "{\"id\":\"28af888810f34a0d9ad60f78dbbbbd1f\",\"created\":1791789155,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user is asking me to reply with\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tokens_details\":{\"reasoning_tokens\":8,\"text_tokens\":0},\"prompt_tokens_details\":{\"cached_tokens\":256}},\"metadata\":{\"weight_version\":\"default\"}}",
        "elapsed_s": 0.58,
        "verdict": "ACCEPTED",
        "detail": "{\"id\":\"28af888810f34a0d9ad60f78dbbbbd1f\",\"created\":1791789155,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user is asking me to reply with\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tok",
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
    "detail": "{\"id\":\"28af888810f34a0d9ad60f78dbbbbd1f\",\"created\":1791789155,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user is asking me to reply with\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tok",
    "reported_model": "agnes-2.5-flash",
    "reply": "",
    "usage": {
      "completion_tokens": 8,
      
```
