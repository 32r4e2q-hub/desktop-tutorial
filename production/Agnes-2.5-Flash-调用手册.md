# Agnes Video 2.5 Flash 调用手册（实测可用版）

> 来源：本仓库 `production/agnes_video.py` + `production/jeju19s/generate.py` 实测跑通
> （济州案 30 镜 + 光州案 22 轮 attempt 验证）。纯标准库即可跑，无需 pip。

## 1. 基础信息

- Base URL：`https://apihub.agnes-ai.com`
- 认证：`Authorization: Bearer $AGNES_API_KEY`
- 模型名：`agnes-video-2.5-flash`
- 流程（异步任务 API）：创建 → 轮询 → 下载直链

## 2. 创建任务

`POST {base}/v1/videos`，JSON payload（**字段必须精确，多一个就 400**）：

```json
{
  "model": "agnes-video-2.5-flash",
  "prompt": "【STYLE】…画面描述…【NEGATIVE】…",
  "seconds": "6",
  "size": "720P",
  "aspect_ratio": "16:9",
  "mode": "reference",
  "n": 1,
  "seed": 12345,
  "images": ["https://公开可达的图1.png", "https://图2.png"]
}
```

### 字段说明与坑位

| 字段 | 说明 |
|---|---|
| `prompt` | **STYLE 开头、NEGATIVE 拼尾**，无独立 `negative_prompt` 字段 |
| `seconds` | **必须是字符串**，`"4"`–`"12"`（超出会被钳到 4–12） |
| `size` | `"720P"`（源片规格；交付时再升采样到 1080P） |
| `aspect_ratio` | `"16:9"` / `"9:16"` / `"1:1"` / `"4:3"` / `"3:4"` |
| `mode` | `text`（纯文生）/ `keyframe`（2+ 图首尾帧）/ `reference`（1–5 图角色场景锚定） |
| `n` | 固定 `1` |
| `seed` | 整数；**单人镜头复用该角色固定 seed 保脸一致** |
| `images` | **必须是公开 URL**（我们用的是 gitblob/raw 链接）；reference 模式 1–5 张 |

### 明确被拒绝的字段（带上就 400）

`width`、`height`、`fps`、`num_frames`、`frame_rate`、`resolution`、独立 `negative_prompt`

### 返回

`200 + JSON`，取 `video_id`（或 `id`）和 `task_id`。两个都存，轮询用得上。

## 3. 轮询任务

主轮询：`GET {base}/agnesapi?video_id=<VIDEO_ID>&model_name=agnes-video-2.5-flash`

- `status` 落到 `completed/complete/succeeded/success/done/finished` 即完成，从响应里取 `video_url`（字段可能是 `url`，递归找 `.mp4` 链接）。
- 落到 `failed/failure/error/cancelled/canceled/expired/rejected` 即失败。
- **主端点 404 时 fallback 到 `GET {base}/v1/videos/<TASK_ID>`**，两个端点轮流试（都记失败次数，超限才放弃）。

## 4. 下载成片

`video_url` 是公开直链（形如 `https://platform-outputs.agnes-ai.space/videos/…mp4`），**无需 API key**，普通 GET 下载即可。务必校验字节数/sha256 并做可解码检查。

## 5. 限流与并发（血泪经验）

- **创建和轮询共享一个 12.1 秒请求闸**（每次 HTTP 前都等闸）。
- 严格遵守服务端 `Retry-After`（秒数或 HTTP 日期）。
- `429/5xx`：指数退避重试；`401/403`：key 问题直接停；`400/404/405/413/422`：payload 问题直接停。
- `provider busy` / `rate_limited` 是常态，重试即可，不要改并发硬冲。
- **workers ≤ 2**；月卡约每分钟 5 次额度；30 镜全量约 2.5 小时。
- 同一 payload（规范 JSON 的 sha256，即 `request_hash`）**绝不重复创建**，先查 results 记录复用。

## 6. prompt 结构（reference 模式实测模板）

```
【STYLE】<全局画风：写实、电影感、光线要求> + <角色锚点：与参考图一致的人物描述>
<本镜画面描述：场景+人物动作+运镜+构图（16:9主体三分线，底部字幕安全区低干扰）>
【NEGATIVE】<禁卡通/禁文字/禁血腥等约束>
```

- 要改单镜重排：只改该镜 prompt → 其 `request_hash` 变化 → 触发新任务，其余镜自动复用。
- 防串镜技巧：在 prompt 里写死"全镜只发生在XX场景，不切换到其他场景"，实测有效（济州 S09 翻车后加固一次通过）。

## 7. 最小可用 Python（标准库，复制即跑）

```python
import json, time, urllib.request

BASE = "https://apihub.agnes-ai.com"
KEY = "你的AGNES_API_KEY"

def api(method, path, body=None):
    req = urllib.request.Request(BASE + path,
        data=json.dumps(body).encode() if body else None, method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())

# 1. 创建
task = api("POST", "/v1/videos", {"model": "agnes-video-2.5-flash",
    "prompt": "【STYLE】photorealistic cinematic … 【NEGATIVE】cartoon, text …",
    "seconds": "6", "size": "720P", "aspect_ratio": "16:9",
    "mode": "reference", "n": 1, "seed": 7,
    "images": ["https://你的公开图.png"]})
vid = task.get("video_id") or task.get("id")

# 2. 轮询
while True:
    st = api("GET", f"/agnesapi?video_id={vid}&model_name=agnes-video-2.5-flash")
    if (st.get("status") or "").lower() in ("completed","succeeded","done"):
        print("URL:", st.get("url") or st.get("video_url")); break
    time.sleep(15)  # 生产环境请用 12.1s 闸 + Retry-After + 双端点 fallback
```

完整生产实现见 `production/agnes_video.py`（HTTP 层）和 `production/jeju19s/generate.py`（任务编排/复用/退避）。
