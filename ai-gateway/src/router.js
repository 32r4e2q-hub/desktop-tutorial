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
import { apiError, bearerOf, brief, flattenMessages, json, newId, openaiChunk, sseChunk } from "./util.js";

export const VERSION = "1.2.0";

// ── 每个 isolate 一份运行时状态（冷启动即清空，这是有意的：不落盘） ──────────
const state = {
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
  const withCors = (res) => { for (const [k, v] of Object.entries(cors)) res.headers.set(k, v); return res; };

  if (request.method === "OPTIONS") return withCors(new Response(null, { status: 204 }));

  // ── 公开探针：只报"配了几个 provider / 掩码"，不报 key，不报 prompt ──────────
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
    if (denied) return withCors(denied);

    const rl = state.limiter.check(clientKeyOf(request));
    if (!rl.allowed) {
      return json(
        { error: { message: `rate limit exceeded，${rl.retryAfterSec}s 后重试`, type: "rate_limit_error", code: "rate_limited" } },
        429,
        { "retry-after": String(rl.retryAfterSec), ...cors }
      );
    }

    let body;
    try { body = await request.json(); } catch { return withCors(apiError("请求体不是合法 JSON", 400)); }
    if (!Array.isArray(body.messages) || body.messages.length === 0) {
      return withCors(apiError("messages 必须是非空数组", 400));
    }
    // content 允许 string / 内容块数组 / null（见 util.flattenMessages），这里统一拍平
    const flat = flattenMessages(body.messages);
    if (flat.error) return withCors(apiError(flat.error, 400, { code: "invalid_message" }));
    if (flat.dropped && cfg.debug) {
      console.warn(`[zeroroute-lite] 忽略了 ${flat.dropped} 个非文本内容块（本网关只做 text）`);
    }
    body.messages = flat.messages;

    state.counters.requests++;
    const wantStream = body.stream === true;
    const { picked, unknownModel, cooling } = candidatesFor(cfg, body.model);

    if (unknownModel) {
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

  return withCors(apiError(`not found: ${path}`, 404, { code: "not_found" }));
}

// ── 内部小工具 ────────────────────────────────────────────────────────────────

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
