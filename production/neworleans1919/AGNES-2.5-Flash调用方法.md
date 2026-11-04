# Agnes Video 2.5 Flash：分镜视频片段调用手册

> 本文件记录的是一次**真实跑通 30 个镜头**的调用方法（《新奥尔良斧头杀手》第四期，2026-11-04）。
> 实现代码在 [`production/agnes_video.py`](../agnes_video.py)（HTTP 客户端，纯标准库）与
> [`production/neworleans1919/generate.py`](generate.py)（编排、闸门、断点续跑）。
> 换题目复用请照 [`production/setagaya2000/模板-如何复用.md`](../setagaya2000/模板-如何复用.md)，
> 本文只讲**Agnes 这一层的接口形状、配额与坑**。

---

## 1. 一句话总结

Agnes 是**异步任务式**接口：先 `POST` 建任务拿 `video_id`，再轮询状态，最后下载。
它**没有** `width/height/fps/num_frames` 这些参数，也**不接受**独立的 `negative_prompt` 字段——
能控制的全在 `prompt` 文本里，画幅只由 `size` + `aspect_ratio` 决定。

| 项 | 实测值 |
|---|---|
| 模型名 | `agnes-video-2.5-flash`（旧文档写 `agnes-video-v2.0`，两个都能用，2.5 更快更稳） |
| 基址 | `https://apihub.agnes-ai.com`（Bearer 认证，key 走 `AGNES_API_KEY`） |
| 单镜时长 | `seconds` 取整数，**4–12 秒**；本片每镜 5–7 秒，正好覆盖 30 镜 = 180 秒 |
| 画幅 | `size: "720P"` + `aspect_ratio: "16:9"` → 1280×720 源片，后期放大到 1920×1080 |
| 参考图 | `mode: "reference"` + `images: [url, ...]`（最多 5 张，**必须是公网可访问 URL**） |
| 一致性 | `seed` 固定；单角色镜头复用该角色的 seed，人脸漂移明显减少 |
| 产出 | 任务完成后 `metadata.url` 给一个 mp4 直链，下载后核对字节数与 SHA-256 |

---

## 2. 请求形状（照抄即可）

```jsonc
POST https://apihub.agnes-ai.com/v1/videos
Authorization: Bearer $AGNES_API_KEY
Content-Type: application/json

{
  "model": "agnes-video-2.5-flash",
  "prompt": "【STYLE】…【角色锚点】…【NEGATIVE】…",   // 全部约束都写在这里
  "seconds": "7",                                    // 字符串或整数都可以，4–12
  "size": "720P",
  "aspect_ratio": "16:9",
  "mode": "reference",                               // 传了 images 就必须是这个模式
  "n": 1,
  "seed": 19190319,
  "images": ["https://raw.githubusercontent.com/.../C02.png",
             "https://raw.githubusercontent.com/.../SC04.png"]
}
```

三个必须记住的接口事实：

1. **`negative_prompt` 会被拒**。所有「不要黑边 / 不要竖构图 / 不要文字 / 不要血腥」都写成
   `【NEGATIVE】…` 追加在 `prompt` 末尾，模型按文本理解。
2. **不收 `width/height/fps/resolution`**。画幅只有 `size` + `aspect_ratio`；帧率由流水线在
   `render.py` 里统一成 24 fps，不在生成阶段纠结。
3. **`images` 必须是公网 URL**，本地文件要先发布（本仓库的做法：把定稿参考图提交到分支，
   用 `raw.githubusercontent.com/<owner>/<repo>/<sha>/<path>` 的**固定 commit SHA** 地址，
   保证同一部片所有镜头引用的是同一版参考图，见 `reference/revision.txt`）。

---

## 3. 轮询与下载

```
GET {base}/agnesapi?video_id=<VIDEO_ID>&model_name=<MODEL>     ← 首选
GET {base}/v1/videos/<TASK_ID>                                  ← 上面 404 时兜底
```

- 状态 `pending → processing → completed`（失败会带 `failed` 与原因）。
- **本片实测：`pending` 可能持续很久**（配额紧张时 20–30 分钟都见过）。轮询超时不要设成
  25 分钟就放弃——本片最终用的是 `interval=25s, timeout=min(5400, 剩余预算)`，即 **90 分钟**。
  超时后不要重新建任务，**保存 `video_id` 下一轮接着轮询**（`results.json` 里 `status=queued`
  就是用来的）。
- 完成后 `metadata.url` 是**带签名的直链，会过期**，拿到就马上下载并写盘。
- 下载必须回校：`bytes` 与 `sha256` 都写进 `results.json`，渲染前 `render.py` 会再核一遍——
  **素材对不上就不许出片**，这是防止「拿错片/被替换」的硬闸门。

---

## 4. 配额与配速（这次踩得最久的地方）

Agnes 的 Key 分两档，**代码里的配速必须和 Key 档位一致**，否则会「看起来在跑，其实一直在等」。

| 档位 | 建任务频率 | 并发 | 本片参数 |
|---|---|---|---|
| 免费池 | 1 次 / 61 秒 | 2 | `REQUEST_INTERVAL_SECONDS = 61`、`workers = 2` |
| **月卡（本片）** | **5 次 / 分钟** | 5 | `REQUEST_INTERVAL_SECONDS = 12`、`workers = 5` |

- 月卡上限 **500 视频秒/天**。本片 30 镜 × 5–7 秒 = 180 秒，一天内轻松装下；
  一旦当天额度用尽，API 会直接回 **`HTTP 429：今日视频额度已用完，降为每 5 分钟 1 次`**。
  这时**不要狂重试**：按 `Retry-After` 退避，剩下的镜头会以 5 分钟 1 镜的速度补齐
  （本片 21→30 镜就是这么补完的）。
- 用 [`throttle.py`](throttle.py) 做全局限流：`RequestGate(minimum_interval=…, allow_fast_plan=True)`。
  有 `allow_fast_plan=True` 才允许间隔小于 10 秒，否则会抛 `ValueError`——这是防止有人
  误把免费池当付费池刷的保险。
- 自检命令：`python3 production/neworleans1919/throttle_probe.py --pacing`
  直接打印当前生效的间隔、每分钟次数、并发数与轮询超时。**改参数后先跑它**。

---

## 5. 提示词结构（决定画面质量的部分）

每个镜头一个 prompt，**固定三段式**，顺序不能变：

```
【STYLE】<两种色调之一：恐惧线=冷青/深蓝/黄调煤气灯；爵士线=暖金/琥珀/橙红 + 金色音符粒子>
<场景与动作：谁、在哪、做什么、镜头怎么动、画面里必须有哪些真实运动>
【角色锚点】<逐字复用参考图定稿的角色外貌描述，一个字都不能改>
【NEGATIVE】<不要遗体/伤口/血迹/挥砍、不要文字与乱码、不要竖构图与黑边、不要面部崩坏、斧头只作影子或剪影>
```

关键经验：

- **「真实运动」必须写具体**，否则容易得到「静帧 + 缓慢推近」。有效的写法是点名元素：
  `fog rolling, water rippling, lamp swinging, curtain stirring, hem passing the doorway`。
- **角色锚点要逐字复用**（本片锚点存在 `build_story.py` 里，由代码拼接，不手抄）。
- 单角色镜头固定 seed 能明显降低换脸率；跨角色镜头用 `shot.seed`。
- 参考图最多 5 张：场景 1 张 + 角色 1–3 张 + 道具 1 张，超过就挑最关键的。

---

## 6. 断点续跑（长任务的必须项）

`results.json` 是唯一事实来源，每建一次任务、每拿到一个 `video_id`、每下载一镜都立刻落盘并
提交到分支（`checkpoint()`）。重启后：

- `status=completed` 的镜头直接复用，不重生成；
- `status=queued` 的镜头用存下来的 `video_id` **继续轮询**，不重新建任务；
- 请求内容变了（prompt 改了）会算 `request_hash`，hash 不一致才重做——避免「改了一个字，
  30 镜全重来」。

---

## 7. 闸门（这些检查是白捡的，别省）

| 闸门 | 作用 |
|---|---|
| `generate.py --validate` | 30 镜、180 秒、时间轴连续、每镜 prompt 三段式完整、参考图 1–5 张、配音与镜头一一对应 |
| 建任务前 `validate_payload` | payload 字段与形状必须和上面的约定一致（防止偷偷加了被拒的字段） |
| 下载后校验 | 字节数 + SHA-256 必须与回执一致 |
| 解码检查 | 每镜落地后跑一遍解码并出接触表 `qa/Sxx.jpg`，人工看 |
| `render.py` 开头 `verify_sources` | 再次核对 30 个源片的 SHA-256，对不上直接失败 |

---

## 8. 一次典型调用（最小可运行）

```bash
# 文本生成（不带参考图）
AGNES_API_KEY=... python3 production/agnes_video.py \
  --model agnes-video-2.5-flash \
  --prompt "【STYLE】…【NEGATIVE】…" \
  --seconds 6 --size 720P --aspect 16:9 \
  --output work/cat.mp4

# 带参考图（公网 URL）
AGNES_API_KEY=... python3 production/agnes_video.py \
  --model agnes-video-2.5-flash \
  --prompt "…" --seconds 6 --size 720P --aspect 16:9 \
  --image https://raw.githubusercontent.com/<owner>/<repo>/<sha>/production/neworleans1919/reference/C02.png \
  --output work/shot.mp4

# 只看请求体，不花钱
python3 production/agnes_video.py --prompt "…" --seconds 6 --dry-run
```

整片编排走 marker + Actions，不在本地直跑：

```bash
printf '{"mode":"clips","workers":5}' > production/neworleans1919/GEN_REQUEST   # 生成 30 镜
printf '{"mode":"render","workers":1}' > production/neworleans1919/RENDER_REQUEST # 出片
printf '{"mode":"qc"}' > production/neworleans1919/QC_REQUEST                    # 成片质检
```

> ⚠️ 提交信息里带 `[skip-neworleans1919]` 会**跳过**工作流；marker 必须用不带该标记的提交推送。

---

## 9. 补充：这次顺手修掉的三个坑（避免重犯）

1. **并发分组把自己堵死**：旧 workflow 的 `concurrency` 分组被上一轮 run 占着，新 run 一直
   `pending` 等机器。修法：分组版本号升级（`…-v2`），并在 job 开头主动取消同 workflow 的过期
   run（`POST /actions/runs/{id}/cancel`）。
2. **`continue-on-error` 把渲染失败伪装成成功**：run 绿了却没有成片。修法：生成/渲染步骤**不吞
   错误**，失败就让 run 红；同时把 `run.log` 在生成后立刻推上分支，失败原因能从仓库里读到
   （沙箱拿不到 Actions 日志）。
3. **配乐事件分桶按「秒 ÷ 采样块长」算**，导致所有音符都落在第 0 块、爵士段落整段静音；
   同时摆动八分的步长写成 `eighth/3` 使后半小节错位。修法：块号一律 `int(at * RATE // BLOCK)`，
   八分步长 `eighth * swing / 1.5`。**这类「整段没声音」的问题，先查时间轴单位，不要先怀疑素材。**
