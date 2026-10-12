# Agnes 模型可用性探测报告

- 探测时间（UTC）：`2026-10-12T07:27:00Z`
- 接口基址：`https://apihub.agnes-ai.com`
- key 可用：`是`
- 模式：`零成本校验探测（不生成视频）`

| 模型 | 类型 | 判定 | HTTP | 说明 |
| --- | --- | --- | --- | --- |
| `agnes-2.5-flash` | text | 可用（请求被受理） | 200 | {"id":"dc2dc85e01034f1a87aca4b181bd2039","created":1791790021,"model":"agnes-2.5-flash","object":"chat.completion","choices":[{"finish_reason":"length","index":0,"message":{"content":"","role":"assistant","reasoning_cont |
| `agnes-3.0-flash` | text | 可用（请求被受理） | 200 | {"id":"fb45812dee8d43fe82558f326e312ff4","created":1791790035,"model":"agnes-3.0-flash","object":"chat.completion","choices":[{"finish_reason":"stop","index":0,"message":{"content":"ok","role":"assistant"},"provider_spec |
| `agnes-3.0-flash-max` | text | 鉴权失败（key 无效） | 403 | Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072724230684324gqRfhUDR) code=insufficient_user_quota type=AgnesAI_error |
| `agnes-2.5-pro` | text | 鉴权失败（key 无效） | 403 | Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072732500911499CH1zhgrp) code=insufficient_user_quota type=AgnesAI_error |
| `agnes-2.5-pro-alpha` | text | 鉴权失败（key 无效） | 403 | Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072740777881264e6nMMRsR) code=insufficient_user_quota type=AgnesAI_error |
| `agnes-2.5-pro-beta` | text | 鉴权失败（key 无效） | 403 | Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072749459180530FUGfKqP) code=insufficient_user_quota type=AgnesAI_error |

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
    "model": "agnes-2.5-flash",
    "kind": "text",
    "attempts": [
      {
        "ok": true,
        "status": 200,
        "raw": "{\"id\":\"dc2dc85e01034f1a87aca4b181bd2039\",\"created\":1791790021,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user wants me to reply with just\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_tokens_details\":{\"reasoning_tokens\":8,\"text_tokens\":0},\"prompt_tokens_details\":{\"cached_tokens\":256}},\"metadata\":{\"weight_version\":\"default\"}}",
        "elapsed_s": 1.3,
        "verdict": "ACCEPTED",
        "detail": "{\"id\":\"dc2dc85e01034f1a87aca4b181bd2039\",\"created\":1791790021,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user wants me to reply with just\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_to",
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
    "detail": "{\"id\":\"dc2dc85e01034f1a87aca4b181bd2039\",\"created\":1791790021,\"model\":\"agnes-2.5-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"length\",\"index\":0,\"message\":{\"content\":\"\",\"role\":\"assistant\",\"reasoning_content\":\"The user wants me to reply with just\"},\"provider_specific_fields\":{\"matched_stop\":null}}],\"usage\":{\"completion_tokens\":8,\"prompt_tokens\":291,\"total_tokens\":299,\"completion_to",
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
  },
  {
    "model": "agnes-3.0-flash",
    "kind": "text",
    "attempts": [
      {
        "ok": true,
        "status": 200,
        "raw": "{\"id\":\"fb45812dee8d43fe82558f326e312ff4\",\"created\":1791790035,\"model\":\"agnes-3.0-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"stop\",\"index\":0,\"message\":{\"content\":\"ok\",\"role\":\"assistant\"},\"provider_specific_fields\":{\"matched_stop\":248046}}],\"usage\":{\"completion_tokens\":2,\"prompt_tokens\":81,\"total_tokens\":83},\"metadata\":{\"weight_version\":\"default\",\"weight_versions\":[{\"version\":\"default\",\"start\":0,\"end\":2}]}}",
        "elapsed_s": 5.71,
        "verdict": "ACCEPTED",
        "detail": "{\"id\":\"fb45812dee8d43fe82558f326e312ff4\",\"created\":1791790035,\"model\":\"agnes-3.0-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"stop\",\"index\":0,\"message\":{\"content\":\"ok\",\"role\":\"assistant\"},\"provider_specific_fields\":{\"matched_stop\":248046}}],\"usage\":{\"completion_tokens\":2,\"prompt_tokens\":81,\"total_tokens\":83},\"metadata\":{\"weight_version\":\"default\",\"weight_versions\":[{\"version\":\"de",
        "path": "/v1/chat/completions",
        "reply": "ok",
        "reported_model": "agnes-3.0-flash",
        "usage": {
          "completion_tokens": 2,
          "prompt_tokens": 81,
          "total_tokens": 83
        }
      }
    ],
    "verdict": "ACCEPTED",
    "status": 200,
    "detail": "{\"id\":\"fb45812dee8d43fe82558f326e312ff4\",\"created\":1791790035,\"model\":\"agnes-3.0-flash\",\"object\":\"chat.completion\",\"choices\":[{\"finish_reason\":\"stop\",\"index\":0,\"message\":{\"content\":\"ok\",\"role\":\"assistant\"},\"provider_specific_fields\":{\"matched_stop\":248046}}],\"usage\":{\"completion_tokens\":2,\"prompt_tokens\":81,\"total_tokens\":83},\"metadata\":{\"weight_version\":\"default\",\"weight_versions\":[{\"version\":\"de",
    "reported_model": "agnes-3.0-flash",
    "reply": "ok",
    "usage": {
      "completion_tokens": 2,
      "prompt_tokens": 81,
      "total_tokens": 83
    }
  },
  {
    "model": "agnes-3.0-flash-max",
    "kind": "text",
    "attempts": [
      {
        "ok": false,
        "status": 403,
        "raw": "{\"error\":{\"message\":\"Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072724230684324gqRfhUDR)\",\"type\":\"AgnesAI_error\",\"param\":\"\",\"code\":\"insufficient_user_quota\"}}",
        "elapsed_s": 0.26,
        "verdict": "AUTH_FAILED",
        "detail": "Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072724230684324gqRfhUDR) code=insufficient_user_quota type=AgnesAI_error",
        "path": "/v1/chat/completions",
        "reported_model": null
      }
    ],
    "verdict": "AUTH_FAILED",
    "status": 403,
    "detail": "Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072724230684324gqRfhUDR) code=insufficient_user_quota type=AgnesAI_error",
    "reported_model": null,
    "reply": null,
    "usage": null
  },
  {
    "model": "agnes-2.5-pro",
    "kind": "text",
    "attempts": [
      {
        "ok": false,
        "status": 403,
        "raw": "{\"error\":{\"message\":\"Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072732500911499CH1zhgrp)\",\"type\":\"AgnesAI_error\",\"param\":\"\",\"code\":\"insufficient_user_quota\"}}",
        "elapsed_s": 0.29,
        "verdict": "AUTH_FAILED",
        "detail": "Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072732500911499CH1zhgrp) code=insufficient_user_quota type=AgnesAI_error",
        "path": "/v1/chat/completions",
        "reported_model": null
      }
    ],
    "verdict": "AUTH_FAILED",
    "status": 403,
    "detail": "Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072732500911499CH1zhgrp) code=insufficient_user_quota type=AgnesAI_error",
    "reported_model": null,
    "reply": null,
    "usage": null
  },
  {
    "model": "agnes-2.5-pro-alpha",
    "kind": "text",
    "attempts": [
      {
        "ok": false,
        "status": 403,
        "raw": "{\"error\":{\"message\":\"Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072740777881264e6nMMRsR)\",\"type\":\"AgnesAI_error\",\"param\":\"\",\"code\":\"insufficient_user_quota\"}}",
        "elapsed_s": 0.25,
        "verdict": "AUTH_FAILED",
        "detail": "Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072740777881264e6nMMRsR) code=insufficient_user_quota type=AgnesAI_error",
        "path": "/v1/chat/completions",
        "reported_model": null
      }
    ],
    "verdict": "AUTH_FAILED",
    "status": 403,
    "detail": "Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072740777881264e6nMMRsR) code=insufficient_user_quota type=AgnesAI_error",
    "reported_model": null,
    "reply": null,
    "usage": null
  },
  {
    "model": "agnes-2.5-pro-beta",
    "kind": "text",
    "attempts": [
      {
        "ok": false,
        "status": 403,
        "raw": "{\"error\":{\"message\":\"Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072749459180530FUGfKqP)\",\"type\":\"AgnesAI_error\",\"param\":\"\",\"code\":\"insufficient_user_quota\"}}",
        "elapsed_s": 0.29,
        "verdict": "AUTH_FAILED",
        "detail": "Insufficient user quota, remaining: ＄0.000000 (request id: 20261012072749459180530FUGfKqP) code=insuf
```
