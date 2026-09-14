/**
 * 离线自检：不联网，用一个本地 mock 上游验证失败转移 / SSE 透传 / 内存缓存，
 * 以及 4 个 zeroroute 漏洞在这里是否真的被堵上（回归断言）。
 *
 * 运行：node test/run-tests.mjs
 */
import { handle } from "../src/router.js";

import { createMockServer, hits } from "./mock-upstream.mjs";

let MOCK_PORT = 0;   // 0 = 让内核挑空闲端口，避免和 demo 抢 8791



/** provider 全部指到 mock 的不同"行为"路径（base 在 mock 起监听后才可知，用函数延迟求值） */
// 先起 mock：ENV 里的 URL 是立即求值的，必须已经知道端口
const mock = createMockServer();
await new Promise(r => mock.listen(MOCK_PORT, "127.0.0.1", r));
MOCK_PORT = mock.address().port;
const baseOf = () => `http://127.0.0.1:${MOCK_PORT}`;
const ENV = {
  ROUTER_API_KEY: "sk-test-1234567890",
  ADMIN_KEY: "admin-test-0987654321",
  TIMEOUT_MS: "300",
  STREAM_TIMEOUT_MS: "2000",
  COOLDOWN_MS: "1500",
  CACHE_TTL_MS: "60000",
  PROVIDER_ORDER: "mistral,cohere,sambanova,openrouter,groq,nvidia",
  GROQ_MODEL: "healthy-model",
  GROQ_API_KEY: "key-groq-real", GROQ_BASE_URL: `${baseOf()}/ok/v1`,
  MISTRAL_API_KEY: "key-mistral-real", MISTRAL_BASE_URL: `${baseOf()}/bad-500/v1`,
  COHERE_API_KEY: "key-cohere-real", COHERE_BASE_URL: `${baseOf()}/limited-429/v1`,
  SAMBANOVA_API_KEY: "key-samba-real", SAMBANOVA_BASE_URL: `${baseOf()}/denied-401/v1`,
  OPENROUTER_API_KEY: "key-openrouter-real", OPENROUTER_BASE_URL: `${baseOf()}/slow/v1`,
  NVIDIA_API_KEY: "key-nvidia-real", NVIDIA_BASE_URL: `${baseOf()}/poison/v1`,
};

const post = (payload, { token = ENV.ROUTER_API_KEY, headers = {}, env = ENV } = {}) =>
  handle(new Request("http://gw.test/v1/chat/completions", {
    method: "POST",
    headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}), ...headers },
    body: JSON.stringify(payload),
  }), env);

const get = (path, { token, headers = {}, env = ENV } = {}) =>
  handle(new Request(`http://gw.test${path}`, { method: "GET", headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), ...headers } }), env);

// ── 断言小框架 ────────────────────────────────────────────────────────────────
let pass = 0, fail = 0;
const results = [];
async function t(name, fn) {
  hits.length = 0;
  try {
    await fn();
    pass++; results.push(["PASS", name]);
  } catch (e) {
    fail++; results.push(["FAIL", name, e.message]);
  }
}
const eq = (a, b, m = "") => { if (a !== b) throw new Error(`${m} 期望 ${JSON.stringify(b)}，实际 ${JSON.stringify(a)}`); };
const ok = (c, m) => { if (!c) throw new Error(m || "断言失败"); };

// ── 用例 ────────────────────────────────────────────────────────────────────
await t("失败转移：mistral 500 → cohere 429 → sambanova 401 → openrouter 超时 → groq 命中", async () => {
  const res = await post({ messages: [{ role: "user", content: "route test" }] });
  const body = await res.json();
  eq(res.status, 200, "状态码");
  eq(body.choices[0].message.content, "hello from ok", "应答内容");
  eq(body.provider, "groq", "落到 groq");
  eq(hits.length, 5, "上游被尝试次数");
  eq(hits.map(h => h.kind).join(","), "bad-500,limited-429,denied-401,slow,ok", "尝试顺序");
});

await t("401 的错误体不回显上游内容（防 key 泄露）", async () => {
  const env = { ...ENV, PROVIDER_ORDER: "sambanova", CACHE_TTL_MS: "0" };
  const res = await post({ messages: [{ role: "user", content: "leak test" }] }, { env });
  const text = JSON.stringify(await res.json());
  eq(res.status, 502, "全失败应 502");
  ok(!text.includes("key-samba-real"), "响应里不得出现真实 key");
  ok(!text.includes("invalid api key"), "响应里不得出现上游原始错误体");
});

await t("流式：正常 SSE 透传，token 逐个到达，[DONE] 收尾", async () => {
  const res = await post({ stream: true, messages: [{ role: "user", content: "stream test" }] });
  const text = await res.text();
  eq(res.status, 200, "状态码");
  ok(res.headers.get("content-type")?.includes("text/event-stream"), "content-type 是 SSE");
  const chunks = text.split("\n\n").filter(l => l.startsWith("data: {"));
  ok(chunks.length >= 3, `应有 ≥3 个 data chunk，实际 ${chunks.length}`);
  ok(text.trimEnd().endsWith("data: [DONE]"), "以 [DONE] 收尾");
  const joined = chunks.map(c => JSON.parse(c.slice(6)).choices[0].delta.content || "").join("");
  eq(joined, "你好，世界", "拼装后的正文");
});

await t("流式：上游空流(nvidia)时不换 provider 而是失败 → 但顺序在 groq 之后，验证不卡死", async () => {
  const env = { ...ENV, PROVIDER_ORDER: "nvidia" };
  const res = await post({ stream: true, messages: [{ role: "user", content: "empty stream" }] }, { env });
  eq(res.status, 502, "空流应 502 而不是 200 空响应");
});

await t("内存缓存：第二次相同请求命中，上游零调用", async () => {
  const msg = [{ role: "user", content: "cache me please" }];
  const r1 = await post({ messages: msg });
  await r1.json();
  eq(r1.headers.get("x-cache"), "MISS", "第一次应 MISS");
  const firstHits = hits.length;
  const r2 = await post({ messages: msg });
  await r2.json();
  eq(r2.headers.get("x-cache"), "HIT", "第二次应 HIT");
  eq(hits.length, firstHits, "命中后不应再打上游");
});

await t("cache:false 与 stream:true 都不写缓存", async () => {
  const msg = [{ role: "user", content: "no-cache check" }];
  await (await post({ messages: msg, cache: false })).json();
  eq(hits.length, 1, "cache:false 应打上游");
  await post({ messages: msg, stream: true }).then(r => r.text());
  eq(hits.length, 2, "流式应打上游");
  const r = await post({ messages: msg });
  eq(r.headers.get("x-cache"), "MISS", "同内容的普通请求仍应 MISS");
  await r.json();
});

await t("钉定模型：provider/model 只打那一个 provider", async () => {
  const res = await post({ model: "groq/llama-3.3-70b-versatile", messages: [{ role: "user", content: "pin" }] });
  eq(res.status, 200, "状态码");
  eq(hits.length, 1, "只尝试 groq");
  eq(hits[0].kind, "ok", "命中 groq");
});

await t("未知模型：404 并提示 /v1/models", async () => {
  const res = await post({ model: "gemini-3.6-flash", messages: [{ role: "user", content: "ghost model" }] });
  eq(res.status, 404, "未知模型应 404（zeroroute 是静默失败）");
  ok((await res.json()).error.message.includes("/v1/models"), "错误提示应指向 /v1/models");
});

await t("冷却：失败过的 provider 在 COOLDOWN 内被排到后面", async () => {
  await post({ messages: [{ role: "user", content: "warm cooldown" }] }).then(r => r.json());
  const before = hits.length;
  await post({ model: "groq/x", messages: [{ role: "user", content: "second" }] }).then(r => r.json());
  eq(hits.length - before, 1, "钉定 groq 时只打 groq");
  // 现在把 groq 打成失败一次 → 下次 auto 请求应跳过它
  const env = { ...ENV, PROVIDER_ORDER: "groq", GROQ_BASE_URL: `${baseOf()}/bad-500/v1` };
  await post({ messages: [{ role: "user", content: "make groq fail" }] }, { env }).then(r => r.json());
  const st = await get("/healthz", { env });
  const groqState = (await st.json()).providers.find(p => p.id === "groq");
  eq(groqState.state, "cooling", "groq 应处于 cooling");
});

// ── 安全回归：zeroroute 的 4 个洞必须全部失效 ───────────────────────────────
await t("🔒 回归1：Sec-Fetch-Site + Bearer free 不能白嫖（zeroroute 可）", async () => {
  for (const tok of ["free", "public", "zeroroute", "", "sk-test-1234567890x"]) {
    const res = await post({ messages: [{ role: "user", content: "freeloader" }] }, {
      token: tok || null,
      headers: { "sec-fetch-site": "same-origin", origin: "http://gw.test" },
    });
    eq(res.status, tok ? 401 : 401, `token="${tok}" 必须 401`);
  }
  eq(hits.length, 0, "一次都不该打到上游");
});

await t("🔒 回归2：ROUTER_API_KEY 不能当 ADMIN_KEY 用（zeroroute 可）", async () => {
  const res = await get("/metrics", { token: ENV.ROUTER_API_KEY });
  eq(res.status, 401, "router key 看指标必须 401");
  const okRes = await get("/metrics", { token: ENV.ADMIN_KEY });
  eq(okRes.status, 200, "admin key 应可看");
});

await t("🔒 回归3：没配 ADMIN_KEY 时 /metrics fail-closed，且任何 token 都进不去", async () => {
  const env = { ...ENV, ADMIN_KEY: "" };
  for (const tok of [undefined, "", "anything", ENV.ROUTER_API_KEY]) {
    const res = await get("/metrics", { token: tok, env });
    eq(res.status, 503, `ADMIN_KEY 缺失时 ${JSON.stringify(tok)} 必须 503`);
  }
  // 而且不存在 /api/customer/me 这种"我是不是管理员"的自证接口
  const nope = await get("/api/customer/me", { token: "totally-not-a-key", env });
  eq(nope.status, 404, "不该存在该端点");
});

await t("🔒 回归4：响应与指标里都没有 prompt 文本（zeroroute 落盘明文）", async () => {
  const secret = "机密合同条款-绝密编号-42";
  const res = await post({ messages: [{ role: "user", content: secret }] });
  await res.json();
  const metrics = await (await get("/metrics", { token: ENV.ADMIN_KEY })).text();
  ok(!metrics.includes(secret), "/metrics 不得包含 prompt");
  const health = await (await get("/healthz")).text();
  ok(!health.includes(secret), "/healthz 不得包含 prompt");
  ok(!health.includes("key-groq-real"), "/healthz 不得包含明文 key");
  ok(/•/.test(health), "/healthz 的 key 应掩码");
});

await t("🔒 回归5：ALLOW_ANONYMOUS 是唯一开放开关，且默认关闭", async () => {
  const noKey = { ...ENV, ROUTER_API_KEY: "" };
  const denied = await post({ messages: [{ role: "user", content: "anon?" }] }, { token: null, env: noKey });
  eq(denied.status, 503, "没 key 且未开匿名 → 503 明确拒绝");
  ok((await denied.json()).error.message.includes("ROUTER_API_KEY"), "错误信息要告诉用户怎么修");
  const open = await post({ messages: [{ role: "user", content: "anon?" }] }, { token: null, env: { ...noKey, ALLOW_ANONYMOUS: "true" } });
  eq(open.status, 200, "显式 ALLOW_ANONYMOUS=true 才放行");
});

await t("🔒 回归6：限流生效并带 retry-after", async () => {
  const env = { ...ENV, RATE_LIMIT_RPM: "3", CACHE_TTL_MS: "0" };
  let last = null;
  for (let i = 0; i < 5; i++) {
    last = await post({ messages: [{ role: "user", content: `burst ${i}` }] }, { env });
    await last.text();
  }
  eq(last.status, 429, "第 4 次起应 429");
  ok(Number(last.headers.get("retry-after")) >= 1, "应带 retry-after");
});

await t("🔒 回归7：CORS 默认不发头；显式 allowlist 才发", async () => {
  const pre = await handle(new Request("http://evil.test/v1/models", { method: "OPTIONS", headers: { origin: "http://evil.test" } }), ENV);
  eq(pre.status, 204, "preflight 返回 204");
  eq(pre.headers.get("access-control-allow-origin"), null, "默认无 CORS 头（zeroroute 默认 *）");
  const allowed = await handle(new Request("http://gw.test/v1/models", { method: "OPTIONS", headers: { origin: "https://app.io" } }), { ...ENV, ALLOWED_ORIGINS: "https://app.io" });
  eq(allowed.headers.get("access-control-allow-origin"), "https://app.io", "allowlist 内应放行");
});

await t("没有 dashboard/widget：/app、/widget.js 一律 404", async () => {
  for (const p of ["/app", "/dashboard", "/widget.js", "/api/keys"]) {
    eq((await get(p, { token: ENV.ADMIN_KEY })).status, 404, `${p} 应 404`);
  }
});

await t("Gemini 方言：请求翻译 + 非流式响应归一化 + usage 映射", async () => {
  const env = { ...ENV, PROVIDER_ORDER: "gemini", GEMINI_API_KEY: "key-gemini-real", GEMINI_BASE_URL: `${baseOf()}/gemini/v1beta` };
  const res = await post({ model: "auto", messages: [{ role: "system", content: "你是中文助手" }, { role: "user", content: "把这段翻成英文" }] }, { env });
  eq(res.status, 200, `状态码（400 说明翻译错）: ${JSON.stringify(await res.clone().json())}`);
  const body = await res.json();
  eq(body.choices[0].message.content, "维度翻译 OK", "正文");
  eq(body.usage.total_tokens, 7, "usage 归一化");
  eq(body.provider, "gemini", "provider 标记");
});

await t("Gemini 方言：SSE 流被转成 OpenAI chunk，并以 [DONE] 收尾", async () => {
  const env = { ...ENV, PROVIDER_ORDER: "gemini", GEMINI_API_KEY: "key-gemini-real", GEMINI_BASE_URL: `${baseOf()}/gemini/v1beta` };
  const res = await post({ stream: true, messages: [{ role: "system", content: "你是中文助手" }, { role: "user", content: "流式" }] }, { env });
  const text = await res.text();
  const joined = text.split("\n\n").filter(l => l.startsWith("data: {"))
    .map(l => JSON.parse(l.slice(6)).choices[0].delta.content || "").join("");
  eq(joined, "维度翻译", "流式拼装结果");
  ok(text.includes("data: [DONE]"), "缺 [DONE]");
});

await t("Cloudflare AI 方言：需要 account id，非流式与流式都归一化", async () => {
  const env = { ...ENV, PROVIDER_ORDER: "cloudflare", CLOUDFLARE_API_KEY: "key-cf-real", CLOUDFLARE_ACCOUNT_ID: "acct-1", CLOUDFLARE_BASE_URL: `${baseOf()}/cf`, CLOUDFLARE_MODEL: "x/y" };
  const res = await post({ messages: [{ role: "user", content: "cf test" }] }, { env });
  eq(res.status, 200, "非流式应 200");
  eq((await res.json()).choices[0].message.content, "云端答案", "cf 正文");
  const sres = await post({ stream: true, messages: [{ role: "user", content: "cf stream" }] }, { env });
  const st = await sres.text();
  const joined = st.split("\n\n").filter(l => l.startsWith("data: {")).map(l => JSON.parse(l.slice(6)).choices[0].delta.content || "").join("");
  eq(joined, "云上结果", "cf 流式拼装");
  // 缺 account id 时不应被当成已启用 provider（否则会拿一个必然失败的候选去烧超时）
  const noAcct = { ...env, CLOUDFLARE_ACCOUNT_ID: "" };
  const r2 = await post({ messages: [{ role: "user", content: "no account" }] }, { env: noAcct });
  eq(r2.status, 503, "缺 account id 应报 no_provider 而不是 502 超时");
});

await t("上游无视 stream=true 返回 JSON 时：合成单 chunk SSE，不做静默空流", async () => {
  const env = { ...ENV, PROVIDER_ORDER: "groq", GROQ_BASE_URL: `${baseOf()}/json-only/v1` };
  const res = await post({ stream: true, messages: [{ role: "user", content: "ignores stream" }] }, { env });
  const text = await res.text();
  eq(res.status, 200, "状态码");
  ok(res.headers.get("content-type")?.includes("text/event-stream"), "对外仍是 SSE 格式");
  const joined = text.split("\n\n").filter(l => l.startsWith("data: {")).map(l => JSON.parse(l.slice(6)).choices[0].delta.content || "").join("");
  eq(joined, "hello from ok", "JSON 应答被合成进流里");
  ok(text.includes("[DONE]"), "缺 [DONE]");
});

mock.close();
for (const r of results) console.log(r[0] === "PASS" ? `  ✅ ${r[1]}` : `  ❌ ${r[1]}\n       ${r[2]}`);
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
