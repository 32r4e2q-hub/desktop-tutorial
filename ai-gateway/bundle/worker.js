/**
 * zeroroute-lite —— 单文件版，可直接粘贴到 Cloudflare Workers 编辑器。
 * ⚠️ 自动生成，不要手改：改 ai-gateway/src/*.js 后跑 `node scripts/bundle.mjs`。
 * 功能：OpenAI 兼容 /v1/chat/completions（失败转移 + SSE 透传 + 内存缓存）、
 *       /v1/models、/healthz、/metrics（需 ADMIN_KEY）。
 * 配置全部来自环境变量/Secret：GROQ_API_KEY、ROUTER_API_KEY、ADMIN_KEY …（见 README 第 3 节）
 * 鉴权 fail-closed：没配 ROUTER_API_KEY 时 /v1 一律 503，不开放、不兜底、不认 any same-origin 旁路。
 * prompt 与回答一律不记录、不落盘。
 */
// ───────────────── util.js ─────────────────
/**
 * 小工具：全部基于 Web 标准 API（Node 18+ 与 Cloudflare Workers 通用），零依赖。
 */

/** 生成 OpenAI 风格的响应 id。Workers 里 crypto.randomUUID 可用。 */
function newId(prefix = "chatcmpl") {
  const rnd = (globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2))
    .replace(/-/g, "").slice(0, 24);
  return `${prefix}-${rnd}`;
}

/**
 * 常数时间字符串比较。
 * 故意不用 `===`：短口令（ROUTER_API_KEY）逐字节短路比较可被计时攻击猜出长度/前缀。
 * 长度不等时也要把较长的循环走完，避免早退泄露信息。
 */
function timingSafeEqual(a, b) {
  const s1 = String(a ?? "");
  const s2 = String(b ?? "");
  const len = Math.max(s1.length, s2.length);
  let diff = s1.length ^ s2.length;
  for (let i = 0; i < len; i++) {
    diff |= (s1.charCodeAt(i) || 0) ^ (s2.charCodeAt(i) || 0);
  }
  return diff === 0;
}

/** 从 Authorization 头取 Bearer token（也接受裸 token）。 */
function bearerOf(headerValue) {
  const v = String(headerValue || "").trim();
  if (!v) return "";
  return v.startsWith("Bearer ") || v.startsWith("bearer ") ? v.slice(7).trim() : v;
}

function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...headers },
  });
}

/** OpenAI 风格的错误体。message 里绝不放 key、上游响应体、堆栈。 */
function apiError(message, status = 400, extra = {}) {
  return json({ error: { message: String(message).slice(0, 300), type: extra.type || "gateway_error", code: extra.code || null, ...(extra.failovers ? { failovers: extra.failovers } : {}) } }, status);
}

/** SHA-256 hex，用作缓存 key。 */
async function sha256(text) {
  const buf = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

/**
 * 把上游的 SSE 字节流按行拆成 "data: <payload>" 的 payload 序列。
 * 只做切行，不解析 JSON —— 解析交给各 adapter。
 */
function sseLineTransform(onPayload, { flush } = {}) {
  const dec = new TextDecoder();
  const enc = new TextEncoder();
  let buf = "";
  return new TransformStream({
    transform(chunk, controller) {
      buf += dec.decode(chunk, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, idx).replace(/\r$/, "");
        buf = buf.slice(idx + 1);
        if (!line.trim()) continue;
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        for (const out of onPayload(payload) || []) controller.enqueue(enc.encode(out));
      }
    },
    flush(controller) {
      if (buf.trim().startsWith("data:")) {
        const payload = buf.slice(5).trim();
        for (const out of onPayload(payload) || []) controller.enqueue(enc.encode(out));
      }
      if (flush) for (const out of flush() || []) controller.enqueue(enc.encode(out));
    },
  });
}

/** 把若干字符串打包成 SSE 响应体片段（含空行分隔）。 */
function sseChunk(obj) {
  return `data: ${JSON.stringify(obj)}\n\n`;
}

/** OpenAI chunk 对象（流式的一个 token）。 */
function openaiChunk({ id, model, created, text, finish = null }) {
  return {
    id, object: "chat.completion.chunk", created, model,
    choices: [{ index: 0, delta: text ? { content: text } : {}, finish_reason: finish }],
  };
}

/** 截断长文本，用于内存态错误摘要。**不用于记录 prompt**：本网关任何地方都不落盘对话内容。 */
const typeName = (v) => (v === null ? "null" : Array.isArray(v) ? "array" : typeof v);

/**
 * 把 message.content 拍平成字符串。
 *
 * OpenAI 规范里 content 既可以是字符串，也可以是内容块数组
 * （[{type:"text",text:"…"}, {type:"image_url",…}]）——多模态与 agent 类客户端
 * 基本都发数组。本网关只做纯文本：text 块按顺序拼接，非文本块丢掉并计数，
 * 其它形状给出具体的 400（而不是笼统一句"需要字符串"）。
 * 返回 { messages, dropped }；不合法时返回 { error }。
 */
function flattenMessages(messages) {
  const out = [];
  let dropped = 0;
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    if (!m || typeof m !== "object" || typeof m.role !== "string") {
      return { error: `messages[${i}] 需要字符串 role（收到 ${typeName(m)}）` };
    }
    const c = m.content;
    let text;
    if (typeof c === "string") text = c;
    else if (c == null) text = "";                    // 只带 tool_calls 的 assistant 轮
    else if (Array.isArray(c)) {
      const parts = [];
      for (const p of c) {
        if (typeof p === "string") parts.push(p);
        else if (p && typeof p === "object" && typeof p.text === "string") parts.push(p.text);
        else dropped++;                                // image_url / input_audio / file …
      }
      text = parts.join("\n");
    } else if (typeof c === "object" && typeof c.text === "string") text = c.text;
    else return { error: `messages[${i}].content 形状不支持：${typeName(c)}（需要 string、内容块数组或 null）` };
    out.push({ ...m, content: text });
  }
  return { messages: out, dropped };
}

/**
 * 把"消息列表"从各家形状里取出来。
 *
 * 除了标准 `messages`，还接受 Responses 风格的 `input`（字符串或 item 数组）
 * + `instructions`（当 system），以及老式补全的 `prompt` —— Hermes 这类客户端
 * 有时会发这些。返回数组；实在取不到就返回 null（由调用方给出可诊断的 400）。
 */
function coerceMessages(body) {
  if (Array.isArray(body.messages) && body.messages.length) return body.messages;
  const out = [];
  const sys = typeof body.instructions === "string" ? body.instructions
    : (typeof body.system === "string" ? body.system : "");
  if (sys) out.push({ role: "system", content: sys });
  const src = body.input ?? body.prompt;
  if (typeof src === "string") out.push({ role: "user", content: src });
  else if (Array.isArray(src)) {
    for (const it of src) {
      if (typeof it === "string") { out.push({ role: "user", content: it }); continue; }
      const parts = Array.isArray(it?.content) ? it.content : null;
      out.push({
        ...it,
        role: typeof it?.role === "string" ? it.role : "user",
        content: parts ? parts.map(p => (typeof p === "string" ? p : p?.text ?? "")).join("\n")
          : (it?.content ?? it?.output_text ?? ""),
      });
    }
  }
  return out.length ? out : null;
}

/** 把消息列表压成"形状摘要"（角色:内容类型），用于 /debug/last-error。不含任何正文。 */
function describeMessages(list) {
  return (Array.isArray(list) ? list : []).slice(0, 12).map((m) => {
    const role = typeof m?.role === "string" ? m.role : "?";
    const c = m?.content;
    if (Array.isArray(c)) {
      const kinds = c.map(p => (typeof p === "string" ? "str" : (p && typeof p === "object" ? (p.type || "obj") : typeof p))).join("+");
      return `${role}:array(${brief(kinds, 48)})`;
    }
    if (c == null) return `${role}:null`;
    return `${role}:${typeof c}`;
  });
}

function brief(s, n = 120) {
  const t = String(s ?? "").replace(/\s+/g, " ").trim();
  return t.length > n ? `${t.slice(0, n)}…` : t;
}


// ───────────────── env.js ─────────────────
/**
 * 配置：只从环境变量读，不写盘、不建 key 文件、不做"UI 里存 key"。
 *
 * 设计取舍（和 zeroroute 不同的地方）：
 *  - 没有 secrets.json / .master.key：Cloudflare 上用 `wrangler secret put`，
 *    key 由平台加密存储，你的代码里永远看不到明文落盘。
 *  - 没有 ADMIN_KEY 兜底到 ROUTER_API_KEY：两个 key 必须是各自独立的值。
 *  - BASE_URL 可覆盖：方便本地 mock 测试，也方便你走自建反代。
 */

/**
 * provider 适配表。style 决定用哪个 adapter：
 *   openai     —— 上游本身就是 OpenAI 兼容 /chat/completions（流式可原样透传）
 *   gemini     —— Google generateContent，需要翻译请求与 SSE
 *   cloudflare —— Workers AI run 接口，需要 account id
 * defaultModel 只作为初值：各家模型名会变，用 `npm run check` 实测，或用 <ID>_MODEL 覆盖。
 */
const PROVIDER_DEFS = [
  {
    id: "groq", name: "Groq", style: "openai",
    base: "https://api.groq.com/openai/v1",
    defaultModel: "llama-3.3-70b-versatile",
  },
  {
    id: "sambanova", name: "SambaNova", style: "openai",
    base: "https://api.sambanova.ai/v1",
    defaultModel: "Meta-Llama-3.3-70B-Instruct",
  },
  {
    id: "mistral", name: "Mistral", style: "openai",
    base: "https://api.mistral.ai/v1",
    defaultModel: "mistral-small-latest",
  },
  {
    id: "openrouter", name: "OpenRouter", style: "openai",
    base: "https://openrouter.ai/api/v1",
    defaultModel: "meta-llama/llama-3.3-70b-instruct:free",
  },
  {
    // Agnes AI（Sapiens AI）：OpenAI 兼容，$0/百万 token 的 flash 档。
    // 国内走 .cn，海外走 https://apihub.agnes-ai.com/v1（用 AGNES_BASE_URL 覆盖）。
    // ⚠️ 上游是 2026-07 才成立的新公司，"永久免费"当宣传语听，别当架构前提：
    //    所以默认排在 openrouter 之后，它挂了自动退回上一家。
    id: "agnes", name: "Agnes AI", style: "openai",
    base: "https://apihub.agnes-ai.cn/v1",
    defaultModel: "agnes-2.5-flash",
  },
  {
    id: "nvidia", name: "NVIDIA NIM", style: "openai",
    base: "https://integrate.api.nvidia.com/v1",
    defaultModel: "nvidia/llama-3.1-nemotron-70b-instruct",
  },
  {
    id: "cohere", name: "Cohere", style: "openai",
    base: "https://api.cohere.com/v2",
    defaultModel: "command-r-plus-08-2024",
  },
  {
    id: "huggingface", name: "Hugging Face", style: "openai",
    base: "https://router.huggingface.co/v1",
    defaultModel: "meta-llama/Llama-3.1-8B-Instruct",
  },
  {
    id: "gemini", name: "Google Gemini", style: "gemini",
    base: "https://generativelanguage.googleapis.com/v1beta",
    // 2026-10-16 起 gemini-2.5-* 整代关停（已下线的 id 一律 404），默认值必须用 3.x
    defaultModel: "gemini-3.5-flash-lite",
  },
  {
    id: "cloudflare", name: "Cloudflare AI", style: "cloudflare",
    base: "https://api.cloudflare.com/client/v4",
    defaultModel: "@cf/meta/llama-3.1-8b-instruct",
    requiresAccount: true,
  },
];

const upper = (id) => id.toUpperCase();

function intEnv(v, def) {
  const n = Number.parseInt(String(v ?? ""), 10);
  return Number.isFinite(n) && n > 0 ? n : def;
}

/** 把一个 env 对象解析成运行时配置（纯函数，便于测试）。 */
function loadConfig(env = {}) {
  const order = String(env.PROVIDER_ORDER || PROVIDER_DEFS.map(p => p.id).join(","))
    .split(",").map(s => s.trim()).filter(Boolean);

  const byId = new Map(PROVIDER_DEFS.map(d => [d.id, d]));
  const providers = [];
  const ignoredIds = [];   // 认不出的 id（拼错/大小写）不静默丢，交给 /healthz 报出来
  for (const id of order) {
    const def = byId.get(id);
    if (!def) { ignoredIds.push(id); continue; }
    const U = upper(id);
    const apiKey = String(env[`${U}_API_KEY`] || "").trim();
    const account = def.requiresAccount ? String(env.CLOUDFLARE_ACCOUNT_ID || "").trim() : "";
    providers.push({
      id: def.id,
      name: def.name,
      style: def.style,
      baseUrl: String(env[`${U}_BASE_URL`] || def.base).replace(/\/+$/, ""),
      model: String(env[`${U}_MODEL`] || def.defaultModel).trim(),
      apiKey,
      account,
      // 配齐凭据才启用；cloudflare 额外要求 account id
      enabled: apiKey.length > 8 && (!def.requiresAccount || account.length > 0),
    });
  }

  const routerKey = String(env.ROUTER_API_KEY || "").trim();
  const adminKey = String(env.ADMIN_KEY || "").trim();

  return {
    providers,
    ignoredIds,
    routerKey,
    adminKey,
    // 明确关掉时（默认）匿名请求一律 401；zeroroute 的 same-origin / "free" token 兜底这里一律不存在
    allowAnonymous: /^(1|true|yes)$/i.test(String(env.ALLOW_ANONYMOUS || "")),
    corsOrigins: String(env.ALLOWED_ORIGINS || "")
      .split(",").map(s => s.trim().toLowerCase()).filter(Boolean),
    timeoutMs: intEnv(env.TIMEOUT_MS, 15000),
    streamTimeoutMs: intEnv(env.STREAM_TIMEOUT_MS, 120000),
    cooldownMs: intEnv(env.COOLDOWN_MS, 30000),
    cacheTtlMs: intEnv(env.CACHE_TTL_MS, 300000),
    cacheMax: intEnv(env.CACHE_MAX, 200),
    rateRpm: intEnv(env.RATE_LIMIT_RPM, 60),
    debug: /^(1|true|yes)$/i.test(String(env.DEBUG || "")),
  };
}

/** 掩码：只保留前 2 后 2，且长度不足时全掩（zeroroute 暴露前 4 后 4，偏多）。 */
function maskKey(key) {
  const k = String(key || "");
  if (!k) return "未配置";
  if (k.length <= 8) return "••••";
  return `${k.slice(0, 2)}••••${k.slice(-2)}`;
}


// ───────────────── cache.js ─────────────────
/**
 * 内存 LRU + TTL 缓存。
 *
 * 诚实说明（别被"0ms 缓存"这种话术骗）：
 *  - Worker 的内存是 **每个 isolate 私有**，冷启动/跨区域不共享，命中率不保证。
 *  - 只缓存 stream:false 的请求：流式要边收边转，重组后再缓存既费 CPU 又容易错序。
 *  - 要跨实例共享请换 KV / Durable Objects（见 README 的"延伸"）。
 */
class MemoryCache {
  constructor({ max = 200, ttlMs = 300000 } = {}) {
    this.max = max;
    this.ttlMs = ttlMs;
    this.map = new Map();      // key -> { value, expires }
    this.hits = 0;
    this.misses = 0;
  }

  get(key) {
    const hit = this.map.get(key);
    if (!hit) { this.misses++; return undefined; }
    if (hit.expires < Date.now()) { this.map.delete(key); this.misses++; return undefined; }
    this.map.delete(key);        // LRU：命中后移到队尾
    this.map.set(key, hit);
    this.hits++;
    return hit.value;
  }

  set(key, value) {
    if (!this.ttlMs || this.max <= 0) return;
    this.map.set(key, { value, expires: Date.now() + this.ttlMs });
    while (this.map.size > this.max) this.map.delete(this.map.keys().next().value);
  }

  stats() {
    return { entries: this.map.size, hits: this.hits, misses: this.misses };
  }
}

/** 缓存 key：只取影响输出的字段，忽略 user/pipeline 噪声。 */
async function cacheKeyOf(body) {
  const norm = JSON.stringify({
    m: body.model ?? "auto",
    msgs: (body.messages || []).map(x => [x.role, typeof x.content === "string" ? x.content : JSON.stringify(x.content)]),
    t: body.temperature ?? null,
    top_p: body.top_p ?? null,
    max_tokens: body.max_tokens ?? null,
  });
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(norm));
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, "0")).join("");
}


// ───────────────── auth.js ─────────────────
/**
 * 鉴权与限流：全部 **fail-closed**（默认拒绝），这是 zeroroute 最大的两个洞所在处。
 *
 * zeroroute 的做法（已实测可利用）：
 *   1) 没配 ADMIN_KEY 时 `ADMIN_KEY = ADMIN_KEY || ROUTER_API_KEY` —— 塞进网页的半公开 key 直接变成管理员 key；
 *   2) `Sec-Fetch-Site: same-origin` 或 `Bearer free/public/zeroroute` 即放行 —— curl 随手伪造，任何人可白嫖你的免费额度。
 * 这里：两个 key 各管各的，缺失即拒绝；不认任何"演示 token"，不认任何请求头旁路。
 */

/** 每个 isolate 独立的固定窗口计数。注意：不是全局配额，只做滥用的第一道防线。 */
class RateLimiter {
  constructor({ limit = 60, windowMs = 60_000 } = {}) {
    this.limit = limit;
    this.windowMs = windowMs;
    this.buckets = new Map();   // key -> { count, start }
  }

  /** @returns {{allowed:boolean, retryAfterSec:number}} */
  check(key) {
    const now = Date.now();
    const b = this.buckets.get(key);
    if (!b || now - b.start > this.windowMs) {
      this.buckets.set(key, { count: 1, start: now });
      this.#prune(now);
      return { allowed: true, retryAfterSec: 0 };
    }
    b.count += 1;
    if (b.count > this.limit) {
      return { allowed: false, retryAfterSec: Math.max(1, Math.ceil((this.windowMs - (now - b.start)) / 1000)) };
    }
    return { allowed: true, retryAfterSec: 0 };
  }

  #prune(now) {
    if (this.buckets.size <= 512) return;
    for (const [k, v] of this.buckets) if (now - v.start > this.windowMs * 2) this.buckets.delete(k);
  }
}

/**
 * 校验调用方 token。
 * @param {string} provided  请求带来的 Bearer token
 * @param {string} expected  期望值（ROUTER_API_KEY 或 ADMIN_KEY）
 * @param {boolean} openMode 仅当 ALLOW_ANONYMOUS=true 且校验的是 chat key 时为 true
 */
function checkToken(provided, expected, openMode = false) {
  const want = String(expected || "").trim();
  if (!want) return openMode === true;            // 未配置：要么明确开放，要么拒绝——绝不"兜底"到另一个 key
  return timingSafeEqual(provided, want);
}

/** 从 request 取调用方标识，用于限流分桶（优先用 token 而不是可伪造的 XFF）。 */
function clientKeyOf(request, fallback = "anon") {
  const auth = request.headers.get("authorization") || "";
  const token = bearerOf(auth);
  if (token) {
    return `tok:${token.slice(0, 6)}…${token.length.toString(36)}`;
  }
  const xff = request.headers.get("cf-connecting-ip") || request.headers.get("x-real-ip") || "";
  return xff ? `ip:${xff}` : `ip:${fallback}`;
}


// ───────────────── adapters.js ─────────────────
/**
 * provider 适配器：把 OpenAI 格式的请求翻成各家上游格式，再把响应翻回 OpenAI 格式。
 *
 * 关键性能决定：对 OpenAI 兼容上游（Groq/Mistral/SambaNova/…）**流式原样透传字节**，
 * 不解析、不重组。Workers 免费档只有 10ms CPU/请求，逐 token JSON 解析是很奢侈的。
 */

const createdSec = () => Math.floor(Date.now() / 1000);

/** 组装一次对上游的 fetch 请求（不含 body 校验，交给 router）。 */
function buildUpstream(provider, body, { stream }) {
  const p = {
    stream,
    temperature: body.temperature,
    top_p: body.top_p,
    max_tokens: body.max_tokens ?? body.max_completion_tokens,
    stop: body.stop,
  };

  if (provider.style === "openai") {
    const payload = { model: provider.model, messages: body.messages, stream, ...compact(p) };
    // agent 类客户端（Hermes 等）靠 tools 才能真动手：原样透传，不做方言翻译
    if (Array.isArray(body.tools) && body.tools.length) {
      payload.tools = body.tools;
      if (body.tool_choice !== undefined) payload.tool_choice = body.tool_choice;
      if (body.parallel_tool_calls !== undefined) payload.parallel_tool_calls = body.parallel_tool_calls;
    }
    return {
      url: `${provider.baseUrl}/chat/completions`,
      init: {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${provider.apiKey}` },
        body: JSON.stringify(payload),
      },
    };
  }

  if (provider.style === "gemini") {
    const system = (body.messages || []).filter(m => m.role === "system").map(m => m.content).join("\n");
    const contents = (body.messages || [])
      .filter(m => m.role !== "system")
      .map(m => ({ role: m.role === "assistant" ? "model" : "user", parts: [{ text: String(m.content ?? "") }] }));
    const payload = {
      contents,
      ...(system ? { systemInstruction: { parts: [{ text: system }] } } : {}),
      generationConfig: compact({
        temperature: p.temperature, topP: p.top_p, maxOutputTokens: p.max_tokens, stopSequences: p.stop,
      }),
    };
    const verb = stream ? "streamGenerateContent?alt=sse" : "generateContent";
    return {
      url: `${provider.baseUrl}/models/${provider.model}:${verb}`,
      init: {
        method: "POST",
        headers: { "content-type": "application/json", "x-goog-api-key": provider.apiKey },
        body: JSON.stringify(payload),
      },
    };
  }

  if (provider.style === "cloudflare") {
    const payload = {
      messages: body.messages,
      stream,
      ...compact({ temperature: p.temperature, top_p: p.top_p, max_tokens: p.max_tokens }),
    };
    return {
      url: `${provider.baseUrl}/accounts/${provider.account}/ai/run/${provider.model}${stream ? "?stream=true" : ""}`,
      init: {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${provider.apiKey}` },
        body: JSON.stringify(payload),
      },
    };
  }

  throw new Error(`unknown provider style: ${provider.style}`);
}

/** 非流式响应 → OpenAI chat.completion。 */
function normalize(provider, raw) {
  if (provider.style === "openai") {
    const choice = raw?.choices?.[0];
    return {
      id: raw?.id || newId(),
      object: "chat.completion",
      created: raw?.created || createdSec(),
      model: `${provider.id}:${raw?.model || provider.model}`,
      provider: provider.id,
      choices: [{
        index: 0,
        message: {
          role: "assistant",
          content: choice?.message?.content ?? choice?.text ?? "",
          // 上游要调工具时 content 往往是空的，答案全在 tool_calls 里 —— 吞掉就等于让 agent 失忆
          ...(Array.isArray(choice?.message?.tool_calls) && choice.message.tool_calls.length
            ? { tool_calls: choice.message.tool_calls } : {}),
        },
        finish_reason: choice?.finish_reason || "stop",
      }],
      usage: raw?.usage || null,
    };
  }

  if (provider.style === "gemini") {
    const part = raw?.candidates?.[0]?.content?.parts || [];
    return {
      id: newId(), object: "chat.completion", created: createdSec(),
      model: `${provider.id}:${provider.model}`, provider: provider.id,
      choices: [{
        index: 0,
        message: { role: "assistant", content: part.map(x => x.text || "").join("") },
        finish_reason: raw?.candidates?.[0]?.finishReason ? "stop" : "stop",
      }],
      usage: raw?.usageMetadata
        ? { prompt_tokens: raw.usageMetadata.promptTokenCount, completion_tokens: raw.usageMetadata.candidatesTokenCount, total_tokens: raw.usageMetadata.totalTokenCount }
        : null,
    };
  }

  // cloudflare：result.response 可能是字符串，也可能是 JSON（带 response_format 时）
  const text = typeof raw?.result?.response === "string" ? raw.result.response : JSON.stringify(raw?.result ?? {});
  return {
    id: newId(), object: "chat.completion", created: createdSec(),
    model: `${provider.id}:${provider.model}`, provider: provider.id,
    choices: [{ index: 0, message: { role: "assistant", content: text }, finish_reason: raw?.result?.finish_reason || "stop" }],
    usage: raw?.result?.usage || null,
  };
}

/**
 * 流式响应的 body 变换器。
 * openai 兼容上游返回 null —— 直接 pipe，零解析。
 */
function streamBodyFor(provider, id, model) {
  if (provider.style === "openai") return null;
  const created = createdSec();

  if (provider.style === "gemini") {
    return sseLineTransform((payload) => {
      if (payload === "[DONE]") return [sseChunk(openaiChunk({ id, model, created, finish: "stop" })), "data: [DONE]\n\n"];
      let obj; try { obj = JSON.parse(payload); } catch { return []; }
      const text = (obj?.candidates?.[0]?.content?.parts || []).map(x => x.text || "").join("");
      const out = [];
      if (text) out.push(sseChunk(openaiChunk({ id, model, created, text })));
      if (obj?.candidates?.[0]?.finishReason) {
        out.push(sseChunk(openaiChunk({ id, model, created, finish: "stop" })), "data: [DONE]\n\n");
      }
      return out;
    }, { flush: () => [sseChunk(openaiChunk({ id, model, created, finish: "stop" })), "data: [DONE]\n\n"] });
  }

  // cloudflare：data: {"response":"tok"} 或新版 {"token":{"text":"tok"}}
  return sseLineTransform((payload) => {
    if (payload === "[DONE]") return ["data: [DONE]\n\n"];
    let obj; try { obj = JSON.parse(payload); } catch { return []; }
    const text = typeof obj?.response === "string" ? obj.response : obj?.token?.text;
    return text ? [sseChunk(openaiChunk({ id, model, created, text }))] : [];
  }, { flush: () => ["data: [DONE]\n\n"] });
}

function compact(o) {
  const out = {};
  for (const [k, v] of Object.entries(o)) if (v !== undefined && v !== null && v !== "") out[k] = v;
  return out;
}

/**
 * 上游返回错误时给调用方看的摘要。
 * ⚠️ 故意**不带**上游响应体：有些厂商的 401 体会把你的 key 原样回显出来，
 *    透传给客户端等于泄露。（test/run-tests.mjs 里有一条断言专门守这个。）
 * 详细原因只进 ps.lastError（内存态）与 DEBUG 日志。
 */
function upstreamReason(status, providerId) {
  const tag = status === 429 ? "rate limited"
    : status === 401 || status === 403 ? "key rejected"
      : status === 404 ? "model not found"
        : `http ${status}`;
  return `${providerId}: ${tag}`;
}


// ───────────────── router.js ─────────────────
/**
 * 网关核心：一个纯 (Request, env) => Response 的函数。
 * 同一个函数既跑在 Cloudflare Worker 里，也跑在 node local-server.mjs 里 —— 没有第二份实现要维护。
 *
 * 路由：
 *   POST /v1/chat/completions   OpenAI 兼容（含 stream:true）
 *   GET  /v1/models             列出已启用 provider 的模型
 *   GET  /healthz               存活探针（公开，只含掩码信息）
 *   GET  /metrics               计数器（需 ADMIN_KEY；**不含任何 prompt 内容**）
 *   其它路径一律 404 —— 不内置 dashboard / widget，少一个可被攻击的面。
 */

const VERSION = "1.5.1";

// ── 每个 isolate 一份运行时状态（冷启动即清空，这是有意的：不落盘） ──────────
const state = {
  lastRejection: null,          // 最近一次"进来了但被我拒了"的元数据（只有形状，没有内容）
  rejections: 0,
  arrivals: 0,
  providers: new Map(),          // id -> { cooldownUntil, failures, lastLatencyMs, lastError }
  cache: null,
  limiter: null,
  counters: { requests: 0, ok: 0, failed: 0, failovers: 0, byProvider: {} },
};
const cfgByEnv = new WeakMap();

function configFor(env) {
  const cached = cfgByEnv.get(env);
  if (cached) return cached;
  const cfg = loadConfig(env);
  cfgByEnv.set(env, cfg);
  state.cache = new MemoryCache({ max: cfg.cacheMax, ttlMs: cfg.cacheTtlMs });
  state.limiter = new RateLimiter({ limit: cfg.rateRpm });
  return cfg;
}

function providerState(id) {
  let s = state.providers.get(id);
  if (!s) { s = { cooldownUntil: 0, failures: 0, lastLatencyMs: 0, lastError: "" }; state.providers.set(id, s); }
  return s;
}

const AUTO = new Set([undefined, null, "", "auto", "zeroroute-lite", "free"]);

/** 依据 body.model 决定候选 provider 列表（含模型钉定）。 */
function candidatesFor(cfg, requestedModel) {
  const enabled = cfg.providers.filter(p => p.enabled);
  const now = Date.now();

  let picked = enabled;
  if (!AUTO.has(requestedModel)) {
    const [maybeId, ...rest] = String(requestedModel).split("/");
    const byId = enabled.find(p => p.id === maybeId && rest.length);
    if (byId) {
      picked = [{ ...byId, model: rest.join("/") }];
    } else {
      const byModel = enabled.filter(p => p.model === requestedModel);
      if (byModel.length) picked = byModel;
      else return { picked: [], unknownModel: true };
    }
  }

  // 冷却中的放到最后（不是丢弃）：全部可用时优先健康的，避免"全在冷却"就直接 503
  const healthy = picked.filter(p => (state.providers.get(p.id)?.cooldownUntil || 0) <= now);
  const cooling = picked.filter(p => (state.providers.get(p.id)?.cooldownUntil || 0) > now);
  return { picked: [...healthy, ...cooling], cooling: cooling.length };
}

async function handle(request, env = {}) {
  const cfg = configFor(env);
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const cors = corsHeaders(request, cfg);
  const withCors = (res) => { for (const [k, v] of Object.entries(cors)) res.headers.set(k, v); return res; };
  state.arrivals++;   // 先计数：这样"到门口就被 404/405"的请求也算进来了，不会假报"没请求"

  if (request.method === "OPTIONS") return withCors(new Response(null, { status: 204 }));

  // ── 公开探针：只报"配了几个 provider / 掩码"，不报 key，不报 prompt ──────────
  if (request.method === "GET" && path === "/debug/last-error") {
    // 默认仍要 key；只有 DEBUG=true 时才允许直接开在浏览器地址栏里看
    if (!cfg.debug) {
      const denied = authorize(request, cfg, "models");
      if (denied) return withCors(denied);
    }
    return withCors(json({
      status: "ok", version: VERSION, arrivals: state.arrivals, rejections: state.rejections,
      last: state.lastRejection || "(还没有被拒的请求：如果 arrivals 也不涨，说明请求根本没到这里)",
      note: "只有形状与字节数等元数据，不含任何 prompt/回答内容",
    }));
  }

  if (request.method === "GET" && (path === "/healthz" || path === "/health")) {
    return withCors(json({
      status: "ok",
      version: VERSION,
      mode: cfg.routerKey ? "authenticated" : "OPEN — set ROUTER_API_KEY",
      // PROVIDER_ORDER 里认不出的 id（拼错、大小写）在这里现形，而不是被静默跳过
      ...(cfg.ignoredIds.length ? { ignored_ids_in_PROVIDER_ORDER: cfg.ignoredIds } : {}),
      providers: cfg.providers.map(p => ({
        id: p.id, enabled: p.enabled, model: p.model,
        key: p.apiKey ? maskKey(p.apiKey) : "未配置",
        state: providerState(p.id).cooldownUntil > Date.now() ? "cooling" : "ready",
      })),
    }));
  }

  // ── 指标：需要 ADMIN_KEY，且绝不与 ROUTER_API_KEY 互兜底 ─────────────────────
  if (request.method === "GET" && path === "/metrics") {
    if (!cfg.adminKey) {
      return withCors(json({ error: { message: "ADMIN_KEY 未配置，指标接口不可用（故意 fail-closed）" } }, 503));
    }
    if (!checkToken(bearerOf(request.headers.get("authorization")), cfg.adminKey)) {
      return withCors(json({ error: { message: "unauthorized" } }, 401));
    }
    const c = state.counters;
    return withCors(json({
      requests: c.requests, ok: c.ok, failed: c.failed, failovers: c.failovers,
      cache: state.cache.stats(),
      providers: c.byProvider,
      note: "只统计次数与延迟；prompt/回答内容一律不记录",
    }));
  }

  // ── 模型清单 ────────────────────────────────────────────────────────────────
  if (request.method === "GET" && (path === "/v1/models" || path === "/models")) {
    const denied = authorize(request, cfg, "models");
    if (denied) return withCors(denied);
    const data = cfg.providers.filter(p => p.enabled).flatMap(p => [
      { id: p.model, object: "model", created: 1700000000, owned_by: p.id },
      { id: `${p.id}/${p.model}`, object: "model", created: 1700000000, owned_by: p.id },
    ]);
    data.push({ id: "auto", object: "model", created: 1700000000, owned_by: "zeroroute-lite" });
    return withCors(json({ object: "list", data }));
  }

  // ── 聊天主路 ────────────────────────────────────────────────────────────────
  if (request.method === "POST" && (path === "/v1/chat/completions" || path === "/chat/completions")) {
    const denied = authorize(request, cfg, "chat");
    if (denied) {
      noteRejection(request, denied.status, "鉴权未通过（详见 message）", { has_auth_header: !!request.headers.get("authorization") });
      return withCors(denied);
    }

    const rl = state.limiter.check(clientKeyOf(request));
    if (!rl.allowed) {
      return json(
        { error: { message: `rate limit exceeded，${rl.retryAfterSec}s 后重试`, type: "rate_limit_error", code: "rate_limited" } },
        429,
        { "retry-after": String(rl.retryAfterSec), ...cors }
      );
    }

    let body, raw = "";
    try { raw = await request.text(); } catch {
      noteRejection(request, 400, "读取请求体失败", { raw_bytes: 0 });
      return withCors(apiError("读取请求体失败", 400, { code: "unreadable_body" }));
    }
    try { body = JSON.parse(raw); } catch {
      noteRejection(request, 400, "请求体不是合法 JSON", {
        raw_bytes: raw.length, first_char: (raw.trim().slice(0, 1) || "(空)"),
      });
      return withCors(apiError("请求体不是合法 JSON", 400, { code: "invalid_json", raw_bytes: raw.length }));
    }
    // 取消息：标准 messages，或 Responses 风格的 input/instructions，或老式 prompt
    const msgs = coerceMessages(body);
    if (!msgs) {
      const keys = Object.keys(body).join(",");
      noteRejection(request, 400, "messages 必须是非空数组", {
        top_level_keys: brief(keys, 200) || "(空对象)", raw_bytes: raw.length,
      });
      return withCors(apiError(
        `messages 必须是非空数组（收到 ${brief(keys, 160) || "空对象"}）`, 400));
    }
    // content 允许 string / 内容块数组 / null（见 util.flattenMessages），这里统一拍平
    const flat = flattenMessages(msgs);
    if (flat.error) {
      noteRejection(request, 400, flat.error, {
        messages_shape: describeMessages(msgs), top_level_keys: brief(Object.keys(body).join(","), 200),
        dropped_non_text: flat.dropped,
      });
      return withCors(apiError(flat.error, 400, { code: "invalid_message" }));
    }
    if (flat.dropped && cfg.debug) {
      console.warn(`[zeroroute-lite] 忽略了 ${flat.dropped} 个非文本内容块（本网关只做 text）`);
    }
    body.messages = flat.messages;

    state.counters.requests++;
    const wantStream = body.stream === true;
    const { picked, unknownModel, cooling } = candidatesFor(cfg, body.model);

    if (unknownModel) {
      noteRejection(request, 404, `未知模型 "${String(body.model).slice(0, 60)}"`, {
        asked_model: String(body.model).slice(0, 60),
        top_level_keys: brief(Object.keys(body).join(","), 200),
        messages_shape: describeMessages(coerceMessages(body) || []),
      });
      return withCors(apiError(`未知模型 "${body.model}"；用 "auto" 或 GET /v1/models 看可用值`, 404, { code: "model_not_found" }));
    }
    if (!picked.length) {
      return withCors(apiError("没有已启用的 provider：检查 <PROVIDER>_API_KEY 环境变量", 503, { code: "no_provider" }));
    }

    // 非流式且允许缓存 → 先查
    const useCache = !wantStream && body.cache !== false && cfg.cacheTtlMs > 0;
    const key = useCache ? await cacheKeyOf(body) : null;
    if (useCache) {
      const hit = state.cache.get(key);
      if (hit) return withCors(json(hit, 200, { "x-cache": "HIT" }));
    }

    const failures = [];
    for (const provider of picked) {
      const ps = providerState(provider.id);
      const started = Date.now();
      try {
        const { url: upstreamUrl, init } = buildUpstream(provider, body, { stream: wantStream });
        const upstream = await fetch(upstreamUrl, {
          ...init,
          signal: AbortSignal.timeout(wantStream ? cfg.streamTimeoutMs : cfg.timeoutMs),
        });

        if (!upstream.ok) {
          // 上游响应体只进内存态与 DEBUG 日志，绝不回显给客户端（可能含 key）
          const snippet = brief(await safeText(upstream), 160);
          ps.failures++; ps.lastError = `${upstream.status} ${snippet}`.trim();
          ps.cooldownUntil = Date.now() + cfg.cooldownMs;
          if (cfg.debug) console.warn(`[zeroroute-lite] ${provider.id} → ${ps.lastError}`);
          failures.push(upstreamReason(upstream.status, provider.id));
          state.counters.failovers++;
          continue;
        }

        if (wantStream) {
          const res = await streamResponse(upstream, provider, body);
          if (!res) { failures.push(`${provider.id}: empty stream`); ps.failures++; continue; }
          ps.failures = 0; ps.cooldownUntil = 0; ps.lastLatencyMs = Date.now() - started;
          bump(provider.id, started, true);
          return withCors(res);
        }

        const raw = await upstream.json();
        const result = normalize(provider, raw);
        ps.failures = 0; ps.cooldownUntil = 0; ps.lastLatencyMs = Date.now() - started;
        if (useCache) state.cache.set(key, result);
        bump(provider.id, started, false);
        return withCors(json(result, 200, { "x-cache": "MISS", "x-provider": provider.id }));
      } catch (err) {
        ps.failures++;
        ps.lastError = brief(err?.message || err, 160);
        ps.cooldownUntil = Date.now() + cfg.cooldownMs;
        failures.push(`${provider.id}: ${err?.name === "TimeoutError" ? "timeout" : "unreachable"}`);
        state.counters.failovers++;
      }
    }

    state.counters.failed++;
    return withCors(apiError(
      `所有候选 provider 都失败了${cooling ? `（有 ${cooling} 个在冷却中）` : ""}`,
      502,
      { code: "all_providers_failed", failovers: failures }
    ));
  }

  // 到这儿说明路径/方法我根本不认——正是"客户端说 400/404，但网关毫无记录"的那种情况
  noteRejection(request, 404, `路径不存在：${request.method} ${path}`, {
    asked_path: path, query: brief(url.search.slice(0, 60), 60),
  });
  return withCors(apiError(`not found: ${path}`, 404, { code: "not_found" }));
}

// ── 内部小工具 ────────────────────────────────────────────────────────────────

/**
 * 记一笔"被拒"的元数据，供 GET /debug/last-error 读。
 * 刻意只存：方法/路径/状态码/字节数/content-type/UA/消息形状 —— 一个字的 prompt 都不留，
 * 与"不落盘 prompt"是同一条原则。远程排错时它是唯一能看清"客户端到底发了什么形状"的办法。
 */
function noteRejection(request, status, message, extra = {}) {
  state.rejections++;
  state.lastRejection = {
    at: new Date().toISOString(),
    method: request.method,
    path: new URL(request.url).pathname,
    status,
    message: String(message).slice(0, 200),
    content_type: request.headers.get("content-type") || "(无)",
    content_length: request.headers.get("content-length") || "(无)",
    user_agent: brief(request.headers.get("user-agent") || "(无)", 60),
    ...extra,
  };
}

function authorize(request, cfg, what) {
  const token = bearerOf(request.headers.get("authorization"));
  // 唯一的"开放模式"开关：ALLOW_ANONYMOUS=true 且没配 key。默认关。
  const openMode = what === "chat" && cfg.allowAnonymous && !cfg.routerKey;
  if (checkToken(token, cfg.routerKey, openMode)) return null;
  if (!cfg.routerKey && !cfg.allowAnonymous) {
    return apiError("网关未配置 ROUTER_API_KEY，已按 fail-closed 拒绝。请设置 ROUTER_API_KEY，或明确设 ALLOW_ANONYMOUS=true", 503, { code: "unconfigured" });
  }
  return apiError("invalid router api key", 401, { code: "unauthorized" });
}

/**
 * 流式：先拿到第一个 chunk 再回 200，这样上游立刻挂掉还能继续 failover。
 * 另：有些上游会**无视 stream 参数**返回 200 + 一坨 JSON（或空 body）。
 *    空 body → 返回 null 交给上层换下一个 provider；JSON → 合成单 chunk 的 SSE。
 *    不加这层的话，客户端会收到"200 但一个 token 都没有"的静默失败。
 */
async function streamResponse(upstream, provider, body) {
  const id = newId();
  const model = `${provider.id}:${provider.model}`;
  const ctype = upstream.headers.get("content-type") || "";

  if (!ctype.includes("text/event-stream")) {
    const text = await upstream.text().catch(() => "");
    if (!text.trim()) return null;
    let raw;
    try { raw = JSON.parse(text); } catch { return null; }
    const done = normalize(provider, raw);
    const sse = new Response(
      sseChunk(openaiChunk({ id, model, created: Math.floor(Date.now() / 1000), text: done.choices[0].message.content, finish: "stop" })) + "data: [DONE]\n\n",
      { status: 200, headers: { "content-type": "text/event-stream; charset=utf-8", "cache-control": "no-cache, no-transform", "x-accel-buffering": "no", "x-provider": provider.id, "x-note": "upstream ignored stream=true" } }
    );
    return sse;
  }

  const reader = upstream.body.getReader();
  const first = await reader.read();
  if (first.done) return null;

  const transform = streamBodyFor(provider, id, model);
  const headers = {
    "content-type": "text/event-stream; charset=utf-8",
    "cache-control": "no-cache, no-transform",
    connection: "keep-alive",
    "x-accel-buffering": "no",
    "x-provider": provider.id,
  };

  // 把已读到的 first chunk 放回头部，再透传剩余字节（openai 兼容路径唯一多做的事就是这个 prepend）
  const head = new ReadableStream({
    start(controller) {
      controller.enqueue(first.value);
      pump(reader, controller).catch(e => controller.error(e));
    },
  });
  const bodyStream = transform ? head.pipeThrough(transform) : head;
  return new Response(bodyStream, { status: 200, headers });
}

async function pump(reader, controller) {
  while (true) {
    const { done, value } = await reader.read();
    if (done) { controller.close(); return; }
    controller.enqueue(value);
  }
}

function bump(providerId, started, streamed) {
  state.counters.ok++;
  const p = state.counters.byProvider[providerId] ||= { requests: 0, avgLatencyMs: 0, streams: 0 };
  p.requests++;
  p.avgLatencyMs = Math.round((p.avgLatencyMs * (p.requests - 1) + (Date.now() - started)) / p.requests);
  if (streamed) p.streams++;
}

async function safeText(res) {
  try { return (await res.text()).slice(0, 400); } catch { return ""; }
}

function corsHeaders(request, cfg) {
  const origin = (request.headers.get("origin") || "").toLowerCase();
  if (!origin || !cfg.corsOrigins.length) return {};
  const allowed = cfg.corsOrigins.includes("*") || cfg.corsOrigins.includes(origin)
    || cfg.corsOrigins.some(p => p.startsWith("*.") && origin.endsWith(p.slice(1)));
  if (!allowed) return {};
  return {
    "access-control-allow-origin": origin,
    "vary": "origin",
    "access-control-allow-headers": "authorization, content-type",
    "access-control-allow-methods": "POST, GET, OPTIONS",
    "access-control-max-age": "600",
  };
}


// ───────────────── 入口 ─────────────────
export default {
  fetch: (request, env) => handle(request, env),
};
