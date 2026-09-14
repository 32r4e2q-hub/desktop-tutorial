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

---

## 3′. 全程只用鼠标（不装任何东西、不打开终端）★推荐给不熟命令行的你

> 想直接照抄、不想读本文其余部分：[`部署清单.md`](./部署清单.md)（Mistral 版，5 步 + 验证表 + 三条禁令）。

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

## 5. 实话实说的限制

- **免费额度不是"0 成本架构"**。Groq/Gemini 等的条款禁止把免费 key 用于生产/中转分发，被判定滥用会封号。自用、demo、做实验可以；商用请买正式额度。
- 内存缓存与限流是 **per-isolate**：冷启动清空、跨地区不共享，命中率别指望。要共享得换 KV / Durable Objects（见下）。
- Cloudflare 免费档 10ms CPU：长 prompt + 高并发时会撞墙（透传已经很省了，但这是平台限制）。
- 只有 `text` 内容：不支持 function calling / tools / 图片 / 流式 usage 统计（各家字段差异太大，宁可不做也别做错）。
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
test/run-tests.mjs     21 条自检
```
