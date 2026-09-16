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
import { loadConfig, maskKey } from "./env.js";
import { checkToken, clientKeyOf, RateLimiter } from "./auth.js";
import { MemoryCache, cacheKeyOf } from "./cache.js";
import { buildUpstream, normalize, streamBodyFor, upstreamReason } from "./adapters.js";
import { apiError, bearerOf, brief, coerceMessages, describeMessages, flattenMessages, json, newId, openaiChunk, sseChunk } from "./util.js";

export const VERSION = "1.6.0";

// ── 每个 isolate 一份运行时状态（冷启动即清空，这是有意的：不落盘） ──────────
const state = {
  lastRejection: null,          // 最近一次"进来了但被我拒了"的元数据（只有形状，没有内容）
  rejections: 0,
  arrivals: 0,
  paths: Object.create(null),   // 每个路径各数一次：证明"Hermes 到底打的是哪个路径"
  dbg: false,                 // DEBUG 开关的镜像：让"拒绝原因"也能进 Workers 日志（计数器是 per-isolate，日志不是）
  lastChat: null,             // 最近一次 /v1/chat/completions 的结果摘要（成功也记；只有元数据）
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

export async function handle(request, env = {}) {
  const cfg = configFor(env);
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const cors = corsHeaders(request, cfg);
  state.dbg = cfg.debug;
  state.arrivals++;
  state.paths[path] = (state.paths[path] || 0) + 1;
  const t0 = Date.now();
  // withCors 是每个响应唯一的出口，所以在这儿顺手记一笔 chat 的结果：
  // 成功也要记 —— 否则"答应了但客户端不认"和"根本没来"看起来一模一样。
  const withCors = (res) => {
    for (const [k, v] of Object.entries(cors)) res.headers.set(k, v);
    if (path === "/v1/chat/completions") {
      state.lastChat = {
        at: new Date().toISOString(),
        status: res.status,
        ms: Date.now() - t0,
        provider: res.headers.get("x-provider") || "-",
        cache: res.headers.get("x-cache") || "-",
        content_type: res.headers.get("content-type") || "-",
        user_agent: brief(request.headers.get("user-agent") || "(无)", 60),
      };
    }
    return res;
  };   // 先计数：这样"到门口就被 404/405"的请求也算进来了，不会假报"没请求"

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
      paths: state.paths,
      last_chat: state.lastChat || "(还没有 /v1/chat/completions 请求到过这个 isolate)",
      last: state.lastRejection || "(还没有被拒的请求)",
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
      { id: p.model, object: "model", created: 1700000000, owned_by: p.id, max_model_len: p.context, context_length: p.context },
      { id: `${p.id}/${p.model}`, object: "model", created: 1700000000, owned_by: p.id, max_model_len: p.context, context_length: p.context },
    ]);
    // auto 这个条目也要报窗口，而且必须取各家里的**最小值**：它可能落到任何一家，
    // 报大了就等于骗客户端（那正是"Hermes 组出畸形请求、在发出前就 400"的成因）
    const minCtx = data.reduce((m, x) => Math.min(m, x.max_model_len || Infinity), Infinity);
    data.push({
      id: "auto", object: "model", created: 1700000000, owned_by: "zeroroute-lite",
      max_model_len: Number.isFinite(minCtx) ? minCtx : 128000,
      context_length: Number.isFinite(minCtx) ? minCtx : 128000,
    });
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
    if (cfg.debug) console.warn(`[zeroroute-lite] 502 failovers: ${brief(failures.join(","), 160)}`);
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
  if (state.dbg) {
    // 只有元数据；Workers 日志按请求逐条落地，比 per-isolate 计数器可靠
    console.warn(`[zeroroute-lite] 拒绝 ${request.method} ${new URL(request.url).pathname} → ${status} ${brief(message, 160)}`);
  }
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
