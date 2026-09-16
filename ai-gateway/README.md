# zeroroute-lite — 自写的免费额度多云 LLM 网关

一个 OpenAI 兼容的多云路由网关：**失败转移 + SSE 流式 + 内存缓存**，
零运行时依赖、零构建步骤、无 dashboard、无遥测、prompt 不落盘。

写它的原因：[amjadlle/zeroroute](https://github.com/amjadlle/zeroroute) 的功能是真的（我实测过），
但它有 4 个能直接利用的安全问题，而且自带作者的商业尾巴（收款商品 ID、第三方中转）。
本项目**不引用它的任何代码**，只保留那条真正有价值的核心逻辑，把洞堵上。

```
客户端 ──POST /v1/chat/completions──▶ 本网关 ──▶ Groq ──┐ 429/5xx/超时                │
                                          ├────────▶ SambaNova ─┤ 自动下一个 ──────────┘
                                          └─ 健康者应答 ←───────┘
```

---

## 1. 30 秒看它是不是真的能跑（不用 key、不用网）

```bash
cd ai-gateway
node scripts/demo.mjs        # 需要 Node ≥ 18.17
```

另开一个终端：

```bash
# 失败转移：mistral(500) → cohere(429) → groq(✅)，40ms 级
curl -s -X POST http://localhost:8787/v1/chat/completions \
  -H "authorization: Bearer demo-router-key" -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"你好"}]}'

# 同一句再发一次 → header 里 x-cache: HIT
# 加 "stream":true → 逐 token 的 SSE
curl -s -N -X POST http://localhost:8787/v1/chat/completions \
  -H "authorization: Bearer demo-router-key" -H 'content-type: application/json' \
  -d '{"stream":true,"messages":[{"role":"user","content":"数到三"}]}'

# 鉴权：不带 key → 401；拿 router key 去看 /metrics → 401
curl -s http://localhost:8787/healthz | python3 -m json.tool
```

自检（21 条断言，含 7 条"zeroroute 那 4 个洞"的回归测试）：

```bash
node test/run-tests.mjs      # 21 passed, 0 failed
```

---

## 2. 接真模型：只需要一个 key

```bash
cp .env.example .env
# 只填 GROQ_API_KEY 就能跑（https://console.groq.com/keys 免费领）
# 顺手生成两个各自的 key：
#   echo "ROUTER_API_KEY=$(openssl rand -hex 24)" >> .env
#   echo "ADMIN_KEY=$(openssl rand -hex 24)"      >> .env

node scripts/check-providers.mjs   # ★上线前必跑：实测 key 有效性 + 模型名是否存在 + SSE 是否可用
node local-server.mjs              # http://localhost:8787
```

`check-providers.mjs` 是故意存在的：各家免费政策和模型 id 一直在变，**上游一改名字，网关就是静默 404 → 一路 failover → 502**。
别信任何 README（包括 zeroroute 里 `gemini-3.6-flash`、`gemma-4-31B-it` 这种看着就不存在的 id）里写的模型名，跑一次脚本比猜强。

客户端接法（OpenAI SDK / LangChain / 任何兼容客户端都一样）：

```python
from openai import OpenAI
client = OpenAI(
    base_url="http://localhost:8787/v1",   # 部署后换成 https://zeroroute-lite.<你的子域>.workers.dev/v1
    api_key="sk-local-123",               # = .env 里的 ROUTER_API_KEY
)
r = client.chat.completions.create(model="auto", messages=[{"role": "user", "content": "hi"}])
```

`model` 的三种写法：

| 写法 | 行为 |
|---|---|
| `auto`（或省略） | 按 `PROVIDER_ORDER` 依次尝试，失败自动下一个 |
| `groq/llama-3.3-70b-versatile` | 钉定这个 provider 的这个模型；不失败转移 |
| 未知模型 | **直接 404 并提示**（不静默烧一遍所有上游） |

### 2.1 加一个新免费源（例：Agnes AI 的 `agnes-2.5-flash`）

只要上游讲 OpenAI 兼容，加源就是**往表里加一行**，路由/流式/降级/缓存全都不用碰：

```js
// src/env.js PROVIDER_DEFS
{ id: "agnes", name: "Agnes AI", style: "openai",
  base: "https://apihub.agnes-ai.cn/v1", defaultModel: "agnes-2.5-flash" },
```

然后 `node scripts/bundle.mjs` 重打包 + `npm test`，部署侧只加两个配置：
`AGNES_API_KEY`（secret）和可选的 `AGNES_MODEL` / `AGNES_BASE_URL`（海外节点用 `https://apihub.agnes-ai.com/v1`）。
默认 `PROVIDER_ORDER` 里 `agnes` 紧跟 `openrouter`：两个免费源互为备胎，谁挂了都不影响整体可用。

> ⚠️ 说清楚：`agnes-2.5-flash` 现在的 $0 报价来自 Agnes AI（Sapiens AI，2026 年才成立的新公司）的促销期，
> 「永久免费」这类话术不要写进你的架构假设。它排在链路中间、失败就自动降级，才是对的用法。
> 同门的 `agnes-2.5-pro-alpha` 是**付费**的，别填进 `AGNES_MODEL`。

---

## 3′. 全程只用鼠标（不装任何东西、不打开终端）★推荐给不熟命令行的你

> 想直接照抄、不想读本文其余部分：[`部署清单.md`](./部署清单.md)（5 步 + 验证表 + 三条禁令）。
>
> 要接进 **Windows 版 Hermes**（agent 客户端）：[`Hermes-Windows接入.md`](./Hermes-Windows接入.md)。


原理：本项目压成了一个文件 `bundle/worker.js`（851 行），Cloudflare 网页编辑器可以整份粘进去。
**不用等 PR 合并**：分支上就能直接复制 →
https://github.com/32r4e2q-hub/desktop-tutorial/blob/arena/01a09ead-desktop-tutorial/ai-gateway/bundle/worker.js
代码与 `src/` 由 `node scripts/bundle.mjs` 同步生成，且**用同一套 21 条测试验过**（`BUNDLE=1 node test/run-tests.mjs`）。

1. **拿一个 Groq key**：https://console.groq.com/keys → `Create API Key` → 立刻复制（只显示一次）。
2. **注册 Cloudflare**：https://dash.cloudflare.com/sign-up （邮箱+密码即可，**不要信用卡**）。
3. 打开 https://dash.cloudflare.com/?to=/:account/workers-and-pages → **Create application** →
   选 **Hello World** 模板 → 名字随便，如 `zeroroute-lite` → **Deploy**。（这几个按钮名与
   Cloudflare 官方文档 2026-05 版一致；UI 若微调，找同名的那一个。）
4. 进去后点 **Edit code**（会打开网页编辑器）→ 把左侧 `worker.js` 里的内容**全删**→
   粘贴本仓库 [`bundle/worker.js`](./bundle/worker.js) 的**全部内容**（在 GitHub 上打开该文件，
   点代码块右上角的复制图标）→ **Save and Deploy**（若只有 **Deploy** 带下拉箭头，就选里面的 **Save**，
   然后回 Overview 点 Deploy）。
5. 配 3 个 key（**这一步决定安全与否**）：你的 Worker → **Settings** →
   **Variables and Secrets** → **Add** → 类型选 **Secret** → 填名字和值，逐条加完点 **Deploy**。
   ⚠️ 一定选 **Secret**，不要选 Variable：Cloudflare 文档原话是"Do not use vars to store
   sensitive information — use secrets instead"，Variable 的值在 dashboard 里是明文可读的。

   | 名字 | 值 | 说明 |
   |---|---|---|
   | `GROQ_API_KEY` | 第 1 步那串 | 上游模型 |
   | `ROUTER_API_KEY` | 自己现编一串，如 `https://www.random.org/strings/` 生成 32 位 | 你的客户端要带的 key |
   | `ADMIN_KEY` | **另一个**不同的串 | 只有看 `/metrics` 才用 |

   ⚠️ 三个都必须填。`ROUTER_API_KEY` 留空的话网关会直接 503 拒绝所有请求（这是故意的 fail-closed，
   而 zeroroute 会当成"公开模式"放任何人进来烧你的额度）。
6. 你的地址就在 **Settings → Domains** 里：`https://zeroroute-lite.<你的子域>.workers.dev`。
7. 验证（只需浏览器，直接开这两个链接看 JSON）：
   - `https://zeroroute-lite.<你的子域>.workers.dev/healthz` → 应看到 `"mode": "authenticated"`、groq `"enabled": true`
   - `.../v1/models` → 用第 5 步的 `ROUTER_API_KEY` 才有结果；**不带 key 打开必须报 401**（报 200 就说明你配错了）

要挂到自己网站/OpenAI 客户端时：`base_url = https://zeroroute-lite.<你的子域>.workers.dev/v1`，`api_key` = `ROUTER_API_KEY`。

> 想改模型名/加别的上游：就在第 5 步的 Secrets 里再加 `GROQ_MODEL=...`（或 `MISTRAL_API_KEY=...`）。
> 不知道哪个模型名真实存在？先跑 `node scripts/check-providers.mjs`（这条确实需要终端），
> 或直接去 https://console.groq.com/docs/model-limits/preview 看当前可用清单，别信任何 README 里的示例名。

---

## 3. 部署到 Cloudflare Workers（走命令行，可重复部署）

免费档：10 万请求/天、每请求 10ms CPU。本网关流式是**原样透传字节**，CPU 很省。

```bash
cd ai-gateway
npm i -D wrangler            # 只有 devDependency，运行时依然 0 依赖
npx wrangler login

# ★ key 一律用 secret，绝不用 [vars]（vars 在 dashboard 里是明文可见的）
npx wrangler secret put ROUTER_API_KEY
npx wrangler secret put ADMIN_KEY
npx wrangler secret put GROQ_API_KEY
# 有几个填几个：GEMINI_API_KEY / MISTRAL_API_KEY / SAMBANOVA_API_KEY ...
# 用 Cloudflare AI 的话还需要：npx wrangler secret put CLOUDFLARE_ACCOUNT_ID

npx wrangler deploy
```

上线后立刻验证：

```bash
curl -s https://zeroroute-lite.<你的子域>.workers.dev/healthz | python3 -m json.tool
curl -s -X POST https://zeroroute-lite.<你的子域>.workers.dev/v1/chat/completions \
  -H "authorization: Bearer <ROUTER_API_KEY>" -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"ping"}]}'
```

> ⚠️ **别照抄 zeroroute 的 "Cloudflare Pages + build output = public" 那套步骤**：
> Pages 只会把 `public/` 当静态文件发，API 要靠 `functions/` 目录，
> 而它的 `src/services/secrets.ts` 用的是 `node:fs` —— 在 Workers/Pages 上根本不能"在 UI 里存 key"。
> 本项目没有这段死代码：配置只来自环境变量/secret。

想绑自己的域名：改 `wrangler.toml` 里注释掉的 `routes`，再在 dashboard 里加 DNS。

---

## 4. 与 zeroroute 的差异（逐条可验证）

| 项 | zeroroute（实测） | 本项目 | 守它的测试 |
|---|---|---|---|
| 只设 `ROUTER_API_KEY` 时的管理员权限 | `ADMIN_KEY = ADMIN_KEY \|\| ROUTER_API_KEY`，网页上那个半公开 key 直接能 `GET /api/keys` | 两个 key 互不兜底；`ADMIN_KEY` 缺失 → `/metrics` 503 | 回归 2 / 回归 3 |
| 匿名白嫖 | `Bearer free` + `Sec-Fetch-Site: same-origin` 即 200 | 任何 header 旁路都不认；只有 `ALLOW_ANONYMOUS=true` 才开放，默认关 | 回归 1 / 回归 5 |
| prompt 隐私 | `data/metrics.json` 明文存 prompt 前 100 字 + 回答前 100 字 | 只计数，**不留任何文本**；也不落盘 | 回归 4 |
| 上游错误体 | 直接透传给调用方（有些厂商 401 会回显你的 key） | 只给 `groq: key rejected` 这类摘要，细节留在内存/DEBUG | 「401 不回显」 |
| 商业尾巴 | `wrangler.toml` 内嵌作者 Dodo 商品 ID；第 10 个 provider 是作者自营 `bazaarlink.ai` | 无 | — |
| 攻击面 | 内置 dashboard + widget + `/api/keys` | 只有 4 个端点，其余一律 404 | 「没有 dashboard」 |
| CORS | 默认 `*` | 默认不发 CORS 头，需显式 `ALLOWED_ORIGINS` | 回归 7 |
| 流式实现 | 逐 chunk 解析再重组（为了缓存） | 原样透传字节；流式不缓存 | — |

它里面**值得保留的东西我留了**：失败转移 + 冷却自愈、SSE、SHA-256 内存缓存、常数时间比 key、
`<ID>_MODEL`/`PROVIDER_ORDER` 这种可配性。它做得不好的地方（auth 兜底、落盘、静态假 model 名、内置前端）我去掉了。

---

## 4′. 远程排错：`GET /debug/last-error`

客户端报 `400` 却不告诉你它发了什么时（Hermes 就是这样），在 Cloudflare 里加一个变量
`DEBUG=true` 并部署，然后浏览器直接开：

```
https://<你的worker>.<子域>.workers.dev/debug/last-error
```

它会给出：最近一次被拒请求的方法/路径/状态码/**content-type/字节数/UA**、body 的**顶层字段名**、
每条消息的**形状摘要**（如 `user:array(text+image_url)`）。`arrivals` 不涨 = 请求根本没进到你的代码，
该去查客户端或 Cloudflare 边缘；`arrivals` 涨而 `rejections` 也涨 = 是我的校验拒的，按 `message` 改即可。

**它不含任何 prompt 或回答内容，也不含任何 key**（`note` 里明说了这条），`DEBUG` 关着时仍需要带 key 才能读。

---

## 5. 实话实说的限制

- **免费额度不是"0 成本架构"**。Groq/Gemini 等的条款禁止把免费 key 用于生产/中转分发，被判定滥用会封号。自用、demo、做实验可以；商用请买正式额度。
- **免费源模型 id 有保质期**：`gemini-2.5-*` 整代 2026-10-16 关停（已下线的 id 一律 404），各家数字也按项目/地区浮动。所以模型名走变量、链路走 `PROVIDER_ORDER`，别把 id 硬编码进客户端。
- **上游的 400 不一定是你说的这件事**：Google 对**无效 key** 也回 400 `INVALID_ARGUMENT`（不是 401）。本网关只回 `gemini: http 400` 这种摘要，先怀疑 key，再怀疑模型名；实在要确诊就临时设 `DEBUG=true`，去 Workers 日志看被截断的上游原文。
- 内存缓存与限流是 **per-isolate**：冷启动清空、跨地区不共享，命中率别指望。要共享得换 KV / Durable Objects（见下）。
- Cloudflare 免费档 10ms CPU：长 prompt + 高并发时会撞墙（透传已经很省了，但这是平台限制）。
- `/v1/models` 每个条目带 `max_model_len`/`context_length`（取 `<ID>_CONTEXT`，默认各家保守值）：
  Hermes 这类客户端会拿它探测上下文窗口，探测失败就用内置兜底值 —— 报大了它会在**发出请求之前**把
  上下文算成畸形，症状是 `format_error` / `HTTP 400` 而网关啥也没收到。`auto` 那条报的是**各家最小值**。
- 只做纯文本：`content` 接受字符串或 OpenAI 的内容块数组（text 块按序拼接），
  `messages` 缺失时兼容 Responses 风格的 `input` + `instructions` 与老式 `prompt`；
  都取不到才 400，且 400 里会列出**收到的顶层字段名**（只给字段名，不碰内容）。
  但 **image / audio / file 块会被丢掉**。要真用图，得给 provider 加 vision 通路。
- **function calling 只在 `style:"openai"` 的上游透传**（groq / sambanova / mistral / openrouter /
  agnes / cohere / nvidia / huggingface）：请求里的 `tools`/`tool_choice` 原样送上去，响应里的
  `tool_calls` 原样带回来，流式则是字节级透传。**`gemini` 与 `cloudflare` 两家不做翻译**，
  带 `tools` 时会被忽略（模型只回文字）——所以接 Hermes / Claude-Code 这类 agent 时，
  `PROVIDER_ORDER` 里要让它排在这些家之后，或干脆用 `<id>/<model>` 钉到 OpenAI 兼容的那几家。
- 不做 /v1/responses（OpenAI 的另一种协议）、不做 `anthropic_messages`：Hermes 里请显式写
  `api_mode: chat_completions`。
- 无 dashboard 是故意的：那玩意把"改你的 provider 配置"暴露到公网，是本项目要修的那个洞本身。

## 6. 延伸（需要时再加，别提前造）

- 跨 isolate 共享缓存/配额：`env.CACHE.put()` 用 Workers KV，或把每个 provider 的用量放 Durable Object。
- 真需要 dashboard：再写一个只读版，绑 Cloudflare Access 做身份，**不要**用"网页里填 key"。
- 计费/审计：加 OpenTelemetry 导出，而不是往本地 JSON 里写 prompt。

## 文件

```
worker.js              Cloudflare 入口（13 行）
local-server.mjs       本地入口（同一个 handle()）
src/router.js          路由 + 失败转移 + 缓存判定
src/adapters.js        各家方言翻译（openai / gemini / cloudflare）
src/auth.js            fail-closed 鉴权 + 限流
src/cache.js           LRU+TTL 内存缓存
src/env.js             provider 表与 env 解析
src/util.js            常数时间比较、SSE、摘要
scripts/demo.mjs       离线演示（mock 上游）
scripts/check-providers.mjs  上线前实测 key/模型名/SSE
test/mock-upstream.mjs 可控的坏上游（500/429/401/超时/空流/方言）
test/run-tests.mjs     23 条自检
```
