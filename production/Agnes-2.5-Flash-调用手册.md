# Agnes Video 2.5 Flash 调用手册（最全实战版）

> 适用模型：`agnes-video-2.5-flash` ｜ 实测：济州案 30 镜 + 光州案多轮验证
> 仓库实现：`production/agnes_video.py`（HTTP 层：建任务/轮询/下载/重试）、
> `production/jeju19s/generate.py`（2.5 Flash payload 组装/去重/并发编排）、
> `production/jeju19s/throttle.py`（12.1s 共享请求闸）
> 纯 Python 标准库即可跑，无需 pip。
>
> ⚠️ 注意：`agnes_video.py` 自带的 `build_payload()` 是旧 V2.0 形状
> （含 `width/height/num_frames/frame_rate`），**2.5 Flash 会直接 400 拒绝**。
> 调 2.5 Flash 时只复用它的 `http_json / create_task / poll_task / download /
> find_video_url / parse_retry_after`，payload 必须按本文第 2 节的形状自己组。

## 1. 总览：三步异步流程

```
POST {base}/v1/videos                      → 建任务，拿 video_id + task_id（两个都存）
GET  {base}/agnesapi?video_id=…&model_name=… → 轮询直到 completed（404 则回退 legacy 端点）
GET  {video_url}                            → 公开直链下载 mp4（免 key），校验收据
```

- Base URL：`https://apihub.agnes-ai.com`（可用环境变量 `AGNES_BASE_URL` 覆盖）
- 认证：所有 API 请求头带 `Authorization: Bearer $AGNES_API_KEY`
  （**只有下载成片直链不需要 key**）
- 建议 UA：`agnes-video-cli/1.0`（下载请求务必带 UA，有网关拦空 UA）
- 超时建议：建任务 120s，轮询单次 60s，下载 300s

## 2. 创建任务：`POST {base}/v1/videos`

Content-Type `application/json`，payload **字段必须精确**——只允许 9 个字段，
多一个就 400：

```json
{
  "model": "agnes-video-2.5-flash",
  "prompt": "【STYLE】…\n\n【角色锚点】…\n\n…本镜画面…\n\n【NEGATIVE】…",
  "seconds": "6",
  "size": "720P",
  "aspect_ratio": "16:9",
  "mode": "reference",
  "n": 1,
  "seed": 12345,
  "images": ["https://公开可达的图1.png", "https://图2.png"]
}
```

### 2.1 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| `model` | string | 固定 `agnes-video-2.5-flash` |
| `prompt` | string | 见第 4 节组装规则：**STYLE 开头、角色锚点、本镜描述、NEGATIVE 拼尾**，`\n\n` 连接 |
| `seconds` | **string** | 片长秒数，只能 `"4"`–`"12"`。**必须是字符串**，传数字必错；代码侧钳制 `str(max(4, min(12, int(d))))` |
| `size` | string | `"720P"`（实测源片规格；要 1080P 交付请本地升采样，不要指望 API 直出） |
| `aspect_ratio` | string | `"16:9"` / `"9:16"` / `"1:1"` / `"4:3"` / `"3:4"` |
| `mode` | string | `"text"` 纯文生 / `"keyframe"` 首尾帧（≥2 图）/ `"reference"` 角色场景锚定（1–5 图）。多镜连续剧用 `reference` |
| `n` | int | 固定 `1` |
| `seed` | int | 见 2.3：**单角色镜头复用该角色的固定 seed**，保多镜脸一致 |
| `images` | string[] | 见第 3 节：**必须是公网可达的 http(s) URL** |

### 2.2 明确被拒绝的字段（带上就 HTTP 400，直接停，不要重试）

```
width, height, fps, num_frames, frame_rate, duration, resolution,
negative_prompt（独立字段）, quality, num_inference_steps
```

记住两条铁律：**时长只认字符串 `seconds`**；**负面约束没有独立字段，必须拼在 prompt 尾部**。

### 2.3 seed 规则

- 单人镜头：用该角色的固定 seed（例：EUNAE=291110，每镜沿用，脸最稳）。
- 多人/空镜：用本镜独立 seed。
- 同 payload + 同 seed ≠ 保证逐帧相同，但人物/画风一致性显著更好。

### 2.4 返回处理

成功 `2xx + JSON`，取值顺序：

```python
video_id = created.get("video_id") or created.get("id") or created.get("task_id")
task_id  = created.get("task_id") or created.get("id") or video_id
```

**两个都持久化**（`video_id` 给主轮询端点，`task_id` 给 legacy 回退端点）。
若响应里没有任何任务标识 → 记为 `create_unknown`，**先对账、绝不直接重发 POST**
（可能已扣费建任务，重发=重复扣费）。

## 3. 参考图 `images`：URL 构造与校验

### 3.1 要求

- 公网 GET 可达的 `http(s)` URL；**本地路径、私有桶链接一律不行**。
- `reference` 模式 1–5 张；`keyframe` 模式 ≥2 张（首图=起始帧，尾图=结束帧）。
- 实测用 PNG；图片本身不要含可读文字/水印（除非画面本就需要）。

### 3.2 推荐做法：immutable raw 链接（防"图被改了但任务还在跑"）

```
https://raw.githubusercontent.com/<owner>/<repo>/<40位commit>/path/to/ref.png
```

用完整 commit SHA 钉死版本，文件内容变化 → SHA 变化 → 旧链接永远指向旧图。
生产校验链（每镜建任务前都做）：

1. 本地 PNG 魔数校验（`89 50 4E 47 0D 0A 1A 0A`）；
2. `sha256(本地文件) == 审批记录中的 sha256`，不等则拒建任务；
3. 数量 1–5，否则拒建。

### 3.3 reference 图配比经验

人物镜：角色图 + 场景图（如 `C01+S03`）；空镜/道具镜：场景图 + 道具图
（如 `P01+P03`）。角色在 prompt 里还要配文字锚点（见 4.2），图文双锚定最稳。

## 4. prompt 组装规则

### 4.1 结构（`\n\n` 连接四段，缺一不可）

```
【STYLE】全局画风 + 时代材质 + 运镜/构图铁律 + 红线
【角色锚点】出镜每个角色各一段（与参考图一致的人物描述）
本镜画面描述（场景 + 人物动作 + 运镜 + 构图 + 本镜特许/禁令）
【NEGATIVE】全局禁令
```

### 4.2 实测原文示例（济州案，可直接改写套用）

STYLE 头：

```
【STYLE】电影级写实3D动画情景重现，明确标注为非真实历史影像；35mm胶片摄影质感，
浅景深，长焦压缩，韩国悬疑公路电影风格……；16:9横屏宽银幕，主体放在三分线附近，
画面底部六分之一留作字幕安全区；所有镜头必须是真实连续运动的3D影像……绝不以
静态图加推拉冒充视频；……绝不出现撞击瞬间、遗体、血腥或伤口；……
```

角色锚点（例）：

```
【C01锚点】29岁韩国女性,黑色及肩长发,清秀明亮,米色针织外套牛仔裤,笑容温暖爽朗
```

本镜描述（例 S01，5s）：

```
黑场中一部手机屏幕亮起，录音声波一格格跳动，右下角计时器停在0:19……
真实连续运动贯穿全镜，镜头运镜：大特写缓慢推近；构图保持16:9横屏，
主体置于三分线，底部字幕安全区保持低干扰；不要任何文字、标签、时间戳或招牌。
```

NEGATIVE 尾：

```
【NEGATIVE】卡通，Q版，动漫，夸张表情，过度饱和，文字，水印，字幕，可读文字，
真实姓名，真实肖像，血腥，伤口，遗体，尸体，撞击瞬间，……畸形手指，多余肢体，
人物面部崩坏，低清晰度，画面闪烁，风格突变，竖屏构图，黑边，静态图加推拉，
幻灯片，拼版，伪招牌。
```

### 4.3 防串镜技巧（翻车后验证有效）

凡是容易被模型"加戏"的镜，在本镜描述里写死一镜到底声明，例如：

> 全镜只发生在深夜车厢内这一个场景，不切换到白天、不切换到其他场景，
> 不得叠加录音声波图形。

济州 S09 v1 因串镜（白天追车+办公室+声波叠加）被退回，加固后 v2 一次通过。

## 5. 去重：`request_hash`（防重复扣费的核心）

```python
encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
request_hash = hashlib.sha256(encoded).hexdigest()
```

- 同一 `request_hash` **绝不重复 POST**：先查本地收据（results.json 式台账）。
- 收据完整（同 hash + 有 `video_url` + 有 `sha256` + 有 `bytes`）→ 直接复用。
- 想重做某镜：只改该镜 prompt/seed/images → hash 变化 → 自动触发新任务，
  其余镜复用（即 `--only S09` 单镜重排的原理）。
- 未对账状态（`submitting / create_unknown / failed / 有 task 无 video_id /
  有 url 无字节数`）→ **拒绝新 POST**，先人工/程序对账。

## 6. 轮询任务

### 6.1 双端点

主端点：

```
GET {base}/agnesapi?video_id=<VIDEO_ID>&model_name=agnes-video-2.5-flash
```

- 主端点回 `400/404` 且手里有 `task_id` → 切 legacy 端点：
  `GET {base}/v1/videos/<TASK_ID>`；legacy 也 404 → 切回主端点。
- 两端点轮流试，**每次失败都计数**，连续失败超限（生产值 12 次）才放弃，
  防止"任务其实建成功了，只是暂时查不到"时误判。

### 6.2 状态集（大小写不敏感）

```python
COMPLETED = {"completed", "complete", "succeeded", "success", "done", "finished"}
FAILED    = {"failed", "failure", "error", "cancelled", "canceled", "expired", "rejected"}
```

- 落到 COMPLETED：从响应递归取 `video_url`（字段可能是 `url`，藏在
  `metadata / output / data / result` 下）；**completed 但暂无 URL → 继续等**，
  不要当失败。
- 落到 FAILED：停，记错误文本。
- 其他（含无 status 但有 URL）：继续轮询。

### 6.3 轮询节流参数（生产值）

- 轮询间隔 45s；单任务超时 1500s（或剩余预算）；连续失败上限 12 次。
- **每次轮询 GET 也要过 12.1s 共享闸**（见第 8 节），与 POST 共用时间线。
- 轮询撞 429：sleep `max(60, 间隔×2, Retry-After)`，并把冷却广播给全闸。

## 7. 下载成片

- `video_url` 形如 `https://platform-outputs.agnes-ai.space/videos/…mp4`，
  **公开直链，无需 API key**，普通 GET + UA 即可。
- 原子写入：先下 `.part` 文件，成功后 rename；重试 3 次、退避 5s 起。
- **文件 < 1024 字节视为失败**（通常是错误页冒充的）。
- 下载后算 `sha256 + 字节数`，连同 `video_url / request_hash` 写入收据；
  建议再做一次可解码检查（ffprobe / 解码首帧）。

## 8. 限流与并发（必读，血泪经验）

### 8.1 12.1 秒共享请求闸

**所有 POST 和轮询 GET 共用同一个闸**，任意两次 API 请求间隔 ≥ 12.1s
（`RequestGate(minimum_interval=12.1)`，小于 12.1 直接抛异常）。
429/容量冷却通过 `gate.defer(秒数)` 广播给所有 worker。
实现可直接抄 `production/jeju19s/throttle.py`（约 50 行，threading 实现）。

### 8.2 Retry-After 必须遵守

同时兼容两种格式：纯秒数（`120`）、HTTP 日期
（`email.utils.parsedate_to_datetime` 转时间戳）；解析失败按无冷却处理。
等待时长取 `max(当前退避, Retry-After)`。

### 8.3 建任务重试分级（只针对 HTTP 429 拒绝）

| 429 错误文本含 | 冷却下限 |
|---|---|
| `queue is full` / `queue_full` / `no available channel` / `get_channel_failed` / `too many pending` | 60s |
| `capacity` / `concurrent` | 120s |
| 其他 429 | 30s |

实际等待 = `max(12.1s, 上表下限, Retry-After)`，然后 `gate.defer()` 并重试。
`provider busy / rate_limited` 是常态，只管退避重试，**不要加并发硬冲**。

### 8.4 错误分类总表

| 情况 | 动作 |
|---|---|
| 401 / 403 | key 问题，**直接停** |
| 400 / 404 / 405 / 413 / 422（建任务） | payload/字段问题，**直接停**，修 payload |
| 429 | 按 8.3 分级冷却后重试 |
| 5xx / HTTP 408 / 425 / `video queue is full` / `no available channel` / `temporarily unavailable` / 网络异常 | **建任务结果不明 → 对账，不自动重发 POST**（防重复扣费） |
| 轮询网络错/非 2xx | 计数，连续 12 次才放弃 |
| 轮询 401/403 | 直接停 |

### 8.5 并发架构

- **workers ≤ 2**；月卡约每分钟 5 次额度；30 镜全量约 2.5 小时。
- 先**串行 prequeue**：把所有缺失镜逐个 POST（每发一次过闸），task ID 落盘；
  再开 worker 并发轮询+下载。不要让 worker 边 POST 边长轮询（会饿死后面的创建）。
- 预算/超时：给整批设总 deadline，闸冷却若超过 deadline 则抛 `BudgetExhausted`，
  已存 task ID 下次可断点续跑（resume 逻辑：有 `video_id` 直接进轮询，不重建）。

## 9. 生产级最小实现（标准库，复制即跑）

下面是剥离业务后的完整可跑版本：含共享闸、Retry-After、分级 429、
双端点轮询、request_hash 台账复用、原子下载。

```python
#!/usr/bin/env python3
"""Agnes Video 2.5 Flash minimal production client (stdlib only)."""
import email.utils, hashlib, json, os, threading, time, urllib.error, urllib.parse, urllib.request

BASE = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com").rstrip("/")
KEY = os.environ["AGNES_API_KEY"]
MODEL = "agnes-video-2.5-flash"
UA = "agnes-video-cli/1.0"
GATE_INTERVAL = 12.1
LEDGER = "agnes_ledger.json"  # request_hash -> receipt

COMPLETED = {"completed", "complete", "succeeded", "success", "done", "finished"}
FAILED = {"failed", "failure", "error", "cancelled", "canceled", "expired", "rejected"}

class Fatal(Exception): pass

class Gate:  # 12.1s 共享闸：POST 与轮询 GET 共用
    def __init__(self, interval=GATE_INTERVAL):
        self.i, self.nx, self.bl, self.lk = interval, 0.0, 0.0, threading.Lock()
    def acquire(self):
        while True:
            with self.lk:
                now = time.monotonic(); ready = max(self.bl, self.nx)
                if now >= ready:
                    self.nx = now + self.i; return
                delay = ready - now
            time.sleep(min(10.0, delay))
    def defer(self, s):
        with self.lk:
            self.bl = max(self.bl, time.monotonic() + max(0.0, float(s or 0)))

GATE = Gate()

def retry_after(v):
    if not v: return 0.0
    try: return max(0.0, float(v))
    except (ValueError, TypeError):
        try:
            w = email.utils.parsedate_to_datetime(str(v)); return max(0.0, w.timestamp() - time.time())
        except Exception: return 0.0

def http(method, url, payload=None, timeout=90):
    GATE.acquire()
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": f"Bearer {KEY}", "Accept": "application/json", "User-Agent": UA,
                 **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code, raw, ra = r.status, r.read(), retry_after(r.headers.get("Retry-After"))
    except urllib.error.HTTPError as e:
        code, raw, ra = e.code, e.read(), retry_after(e.headers.get("Retry-After"))
    try: body = json.loads(raw.decode()) if raw.decode().strip() else None
    except ValueError: body = None
    return code, body, ra

def find_url(b):
    cands = []
    if isinstance(b.get("metadata"), dict):
        cands += [b["metadata"].get("url"), b["metadata"].get("video_url")]
    cands += [b.get("url"), b.get("video_url")]
    for k in ("output", "data", "result"):
        n = b.get(k)
        if isinstance(n, dict): cands += [n.get("url"), n.get("video_url")]
        elif isinstance(n, str): cands.append(n)
    return next((c for c in cands if isinstance(c, str) and c.startswith("http")), None)

def build_prompt(style, anchors, shot, negative):
    return "\n\n".join([style.strip()] + [a.strip() for a in anchors] + [shot.strip(), negative.strip()])

def build_payload(prompt, seconds, images, seed, aspect="16:9"):
    assert 1 <= len(images) <= 5 and all(u.startswith("http") for u in images)
    return {"model": MODEL, "prompt": prompt, "seconds": str(max(4, min(12, int(seconds)))),
            "size": "720P", "aspect_ratio": aspect, "mode": "reference" if images else "text",
            "n": 1, "seed": int(seed), "images": images}

def rhash(p): return hashlib.sha256(json.dumps(p, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

def create(payload):
    delay = 5.0
    while True:
        code, body, ra = http("POST", BASE + "/v1/videos", payload, timeout=120)
        if 200 <= code < 300 and isinstance(body, dict): return body
        txt = json.dumps(body, ensure_ascii=False)[:300] if body else f"HTTP {code}"
        if code in (401, 403): raise Fatal(f"鉴权失败 {code}: {txt}")
        if code in (400, 404, 405, 413, 422): raise Fatal(f"请求被拒 {code}（修 payload）: {txt}")
        if code == 429 or code >= 500:
            low = txt.lower()
            floor = 60.0 if any(m in low for m in ("queue", "channel", "pending")) else \
                    120.0 if any(m in low for m in ("capacity", "concurrent")) else 30.0
            wait = max(GATE_INTERVAL, floor, ra)
            print(f"create {code}, {wait:g}s 后重试: {txt}", flush=True)
            GATE.defer(wait); time.sleep(wait); delay = min(delay * 2, 60); continue
        raise Fatal(f"建任务异常 {code}: {txt}")

def poll(video_id, task_id, interval=45.0, timeout=1500.0, max_failures=12):
    primary = BASE + "/agnesapi?" + urllib.parse.urlencode({"video_id": video_id, "model_name": MODEL})
    legacy = BASE + "/v1/videos/" + urllib.parse.quote(task_id, safe="") if task_id else None
    url, fails, t0, last = primary, 0, time.monotonic(), None
    while True:
        try:
            code, body, ra = http("GET", url, timeout=60)
        except Exception as e:
            fails += 1; print(f"poll 网络错 {e} [{fails}/{max_failures}]", flush=True)
        else:
            if 200 <= code < 300 and isinstance(body, dict):
                fails = 0
                st = str(body.get("status") or "").lower(); u = find_url(body)
                if st != last: print(f"poll status={st or '?'} ({int(time.monotonic()-t0)}s)", flush=True); last = st
                if st in COMPLETED or (not st and u):
                    if u: return body, u
                    print("poll completed 但 URL 未就绪，继续等", flush=True)
                elif st in FAILED: raise Fatal(f"任务 {st}: {json.dumps(body, ensure_ascii=False)[:300]}")
            elif code == 429:
                wait = max(60.0, interval * 2, ra); print(f"poll 429，冷却 {wait:g}s", flush=True)
                GATE.defer(wait); time.sleep(wait); continue
            elif code in (400, 404) and legacy:
                fails += 1; url = legacy if url == primary else primary
                print(f"poll {code}，切换端点 [{fails}/{max_failures}]", flush=True)
            elif code in (401, 403): raise Fatal(f"轮询鉴权失败 {code}")
            else:
                fails += 1; print(f"poll HTTP {code} [{fails}/{max_failures}]", flush=True)
        if fails >= max_failures: raise Fatal(f"轮询连续失败 {fails} 次，放弃 video_id={video_id}")
        if time.monotonic() - t0 >= timeout: raise Fatal(f"轮询超时 {timeout:g}s video_id={video_id}")
        time.sleep(interval)

def download(url, dest):
    part = dest + ".part"; delay = 5.0
    for a in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r, open(part, "wb") as f:
                while True:
                    b = r.read(1 << 18)
                    if not b: break
                    f.write(b)
            import os as _o
            if _o.path.getsize(part) < 1024: raise OSError("文件过小，疑似错误页")
            _o.replace(part, dest); return dest
        except Exception as e:
            print(f"download 尝试 {a}/3 失败: {e}", flush=True); time.sleep(delay); delay *= 2
    raise Fatal(f"下载失败 {url}")

def generate(prompt, seconds, images, seed, dest, ledger_path=LEDGER):
    payload = build_payload(prompt, seconds, images, seed)
    h = rhash(payload)
    ledger = json.load(open(ledger_path, encoding="utf-8")) if os.path.exists(ledger_path) else {}
    if ledger.get(h, {}).get("sha256") and os.path.exists(ledger[h].get("file", "")):
        print(f"复用已收据 {h[:8]}"); return ledger[h]["file"]
    created = create(payload)
    vid = created.get("video_id") or created.get("id") or created.get("task_id")
    tid = created.get("task_id") or created.get("id") or vid
    if not vid: raise Fatal("建任务无回执 ID，需对账，勿重发")
    _, url = poll(str(vid), str(tid) if tid else None)
    download(url, dest)
    s = hashlib.sha256(open(dest, "rb").read()).hexdigest()
    ledger[h] = {"file": dest, "video_url": url, "sha256": s, "video_id": vid}
    json.dump(ledger, open(ledger_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"完成 {dest} sha256={s[:12]}…"); return dest
```

## 10. 上手检查清单（新 agent 照着做）

1. `AGNES_API_KEY` 就绪（只放环境变量/secret，永不打印、永不进 git）。
2. 参考图已上传到公网可达 URL（推荐 raw.githubusercontent + commit 钉版本），
   本地留 PNG 做 sha256 校验。
3. 先 `--dry-run` 式打印 payload 自查：9 字段、无禁用字段、`seconds` 是字符串、
   `images` 1–5 个公网 URL。
4. 单镜试跑：建任务 → 轮询 → 下载 → sha256 → 解码抽帧看一眼。
5. 批量：先串行 prequeue 全 POST，再 ≤2 worker 轮询；整批设总 deadline；
   台账落盘，断点可续。
6. 单镜翻车只改该镜 prompt/seed/images（hash 变了自动重排），别动别人的。

## 11. 常见翻车速查

| 现象 | 原因 | 修法 |
|---|---|---|
| 建任务 400 | 带了 `width/height/fps/…` 或独立 `negative_prompt`，或 `seconds` 传了数字 | 按第 2 节 9 字段重组 |
| 建任务 401/403 | key 错/过期/没配 | 换 key，直停 |
| 建任务 429 queue full | 服务端排队满 | 按 8.3 冷却重试，不要加并发 |
| 轮询一直 404 | 任务在另一端点/建任务其实没成功 | 双端点轮试 + 计数；超限后对账 |
| completed 但没 URL | URL 还没生成 | 继续等，不是失败 |
| 下载几百字节 | 错误页冒充 | 按失败重试下载 |
| 多镜人物换脸 | seed 没固定 / 缺角色锚点图 | 单角色固定 seed + 图文双锚定 |
| 一镜内串场景 | prompt 没锁场景 | 加一镜到底声明（4.3） |
| 被重复扣费 | 未对账就重发 POST | 落实 request_hash 台账 + create_unknown 对账流程 |

## 12. 实测性能参考

- 源片：720P（`1280×720`，24fps，5s 镜约 1.8MB）。
- 月卡约每分钟 5 次额度；双 worker + 12.1s 闸，30 镜全量约 2.5 小时。
- 把参考图钉死在 git commit 上后，跨机器/跨时间重跑结果可复现、可对账。
