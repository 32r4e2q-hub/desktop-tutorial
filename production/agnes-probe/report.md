# Agnes 模型可用性探测报告

- 探测时间（UTC）：`2026-10-12T07:14:41Z`
- 接口基址：`https://apihub.agnes-ai.com`
- key 可用：`是`
- 模式：`零成本校验探测（不生成视频）`

| 模型 | 类型 | 判定 | HTTP | 说明 |
| --- | --- | --- | --- | --- |
| `agnes-video-v2.0` | video | 模型不可用（被拒绝/已下线） | 503 |  |
| `agnes-video-2.5` | video | 模型存在（通过了模型名校验） | 400 |  |
| `agnes-video-v2.0-flash` | video | 模型不可用（被拒绝/已下线） | 503 |  |
| `agnes-video-2.5-flash` | video | 模型存在（通过了模型名校验） | 400 |  |
| `agnes-2.0-flash` | text | 模型不可用（被拒绝/已下线） | 503 | No available channel for model agnes-2.0-flash under group default (distributor) (request id: 202610120724041093665521iH7fh55) code=model_not_found type=AgnesAI_error |
| `agnes-2.5-flash` | text | 可用（请求被受理） | 200 | {"id":"295c97318f4448d7b8b93591799341fc","created":1791789854,"model":"agnes-2.5-flash","object":"chat.completion","choices":[{"finish_reason":"length","index":0,"message":{"content":"","role":"assistant","reasoning_cont |

## 模型清单接口

- `/v1/models` → HTTP 200，列出 6 个模型

  ```
  agnes-video-2.5-flash
  agnes-3.0-flash
  agnes-image-2.1-flash
  agnes-image-2.0-flash
  agnes-2.5-flash
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
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261012071442220693880WM4mCYfG)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.23,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261012071442220693880WM4mCYfG) code=model_not_found type=AgnesAI_error"
    },
    "2.5-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261012071552446861808VshtD9U4)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.23,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0 under group default (distributor) (request id: 20261012071552446861808VshtD9U4) code=model_not_found type=AgnesAI_error"
    },
    "verdict": "MODEL_REFUSED"
  },
  {
    "model": "agnes-video-2.5",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 20261012071702680953662RE7yQm1a)\",\"data\":null}",
      "elapsed_s": 0.24,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 20261012071702680953662RE7yQm1a)"
    },
    "2.5-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 20261012071812926848710v9L6toY2)\",\"data\":null}",
      "elapsed_s": 0.24,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 20261012071812926848710v9L6toY2)"
    },
    "verdict": "MODEL_ACCEPTED"
  },
  {
    "model": "agnes-video-v2.0-flash",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261012071923152097147c8Yd1sHh)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.22,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261012071923152097147c8Yd1sHh) code=model_not_found type=AgnesAI_error"
    },
    "2.5-shape": {
      "ok": false,
      "status": 503,
      "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261012072033398899691QBmTLVSO)\",\"type\":\"AgnesAI_error\"}}",
      "elapsed_s": 0.25,
      "verdict": "MODEL_REFUSED",
      "detail": "No available channel for model agnes-video-v2.0-flash under group default (distributor) (request id: 20261012072033398899691QBmTLVSO) code=model_not_found type=AgnesAI_error"
    },
    "verdict": "MODEL_REFUSED"
  },
  {
    "model": "agnes-video-2.5-flash",
    "kind": "video",
    "v2-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 20261012072143631804776SNpfXDIN)\",\"data\":null}",
      "elapsed_s": 0.24,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 20261012072143631804776SNpfXDIN)"
    },
    "2.5-shape": {
      "ok": false,
      "status": 400,
      "raw": "{\"code\":\"invalid_request\",\"message\":\"prompt is required (request id: 20261012072253871291883EJWCNZUi)\",\"data\":null}",
      "elapsed_s": 0.24,
      "verdict": "MODEL_ACCEPTED",
      "detail": "prompt is required (request id: 20261012072253871291883EJWCNZUi)"
    },
    "verdict": "MODEL_ACCEPTED"
  },
  {
    "model": "agnes-2.0-flash",
    "kind": "text",
    "attempts": [
      {
        "ok": false,
        "status": 503,
        "raw": "{\"error\":{\"code\":\"model_not_found\",\"message\":\"No available channel for model agnes-2.0-flash under group default (distributor) (request id: 202610120724041093665521iH7fh55)\",\"type\":\"AgnesAI_error\"}}",
        "elapsed_s": 0.23,
        "verdict": "MODEL_REFUSED",
        "detail": "No available channel for model agnes-2.0-flash under group default (distributor) (request id: 202610120724041093665521iH7fh55) code=model_not_found type=AgnesAI_error",
        "path": "/v1/chat/completions",
        "reported_model": null
      }
    ],
    "verdict": "MODEL_REFUSED",
    "status": 503,
    "detail": "No available channel for model agnes-2.0-flash under group default (distributor) (request id: 202610120724041093665521iH7fh55) code=model_not_found type=AgnesAI_error",
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
        "raw": "{\"id\":\"295c97318f4448d7b8b93591799341fc\",\"created\":1791789854,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user is asking me to reply with\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tokens_details\":{\"reasoning_tokens\":8,\"text_tokens\":0},\"prompt_tokens_details\":{\"cached_tokens\":256}},\"metadata\":{\"weight_version\":\"default\"}}",
        "elapsed_s": 2.1,
        "verdict": "ACCEPTED",
        "detail": "{\"id\":\"295c97318f4448d7b8b93591799341fc\",\"created\":1791789854,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user is asking me to reply with\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tok",
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
    "detail": "{\"id\":\"295c97318f4448d7b8b93591799341fc\",\"created\":1791789854,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user is asking me to reply with\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tok",
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
