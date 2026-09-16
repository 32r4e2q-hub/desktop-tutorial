/**
 * 离线自检：不联网，用一个本地 mock 上游验证失败转移 / SSE 透传 / 内存缓存，
 * 以及 4 个 zeroroute 漏洞在这里是否真的被堵上（回归断言）。
 *
 * 运行：node test/run-tests.mjs
 */
import { createMockServer, hits } from "./mock-upstream.mjs";

/**
 * BUNDLE=1 时改成测 bundle/worker.js —— 也就是你"粘进 Cloudflare 控制台的那一份"。
 * 两条路都必须全绿，否则单文件产物不可信（这一步真的能抓出打包漏掉的依赖）。
 */
const mod = /^(1|true|yes)$/i.test(process.env.BUNDLE || "")
  ? await import("../bundle/worker.js")
  : await import("../src/router.js");
const handle = mod.handle ? (req, env) => mod.handle(req, env) : (req, env) => mod.default.fetch(req, env);

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

await t("🔧 成功的 chat 也要留下痕迹：paths 分路径计数 + last_chat 记结果", async () => {
  const env = { ...ENV, DEBUG: "true", PROVIDER_ORDER: "groq" };
  const okRes = await post({ model: "auto", messages: [{ role: "user", content: "hi" }] }, { env });
  eq(okRes.status, 200, "上游正常应 200");
  await okRes.text();
  const d = await (await get("/debug/last-error", { env })).json();
  eq(d.paths["/v1/chat/completions"] >= 1, true, `按路径计数才分得开：${JSON.stringify(d.paths)}`);
  eq(d.paths["/debug/last-error"] >= 1, true, "诊断端点自己被数进去也不能污染结论");
  eq(d.last_chat.status, 200, "成功也要记 last_chat");
  eq(d.last_chat.provider, "groq", "顺带记下是谁答的");
  ok(d.last_chat.ms >= 0 && typeof d.last_chat.user_agent === "string", "要有耗时与 UA");
  // 上游全挂时，last_chat 记的是 502（这才是"到过了、但不是我的锅"的证据）
  const down = { ...ENV, DEBUG: "true", PROVIDER_ORDER: "nvidia", NVIDIA_BASE_URL: "http://127.0.0.1:1/v1" };
  const beforeRej = (await (await get("/debug/last-error", { env: down })).json()).rejections;
  const bad = await post({ model: "auto", messages: [{ role: "user", content: "hi" }] }, { env: down });
  eq(bad.status, 502, "上游不可达应 502");
  await bad.text();
  const d2 = await (await get("/debug/last-error", { env: down })).json();
  eq(d2.last_chat.status, 502, "502 也要记进 last_chat");
  eq(d2.rejections, beforeRej, "上游挂了不该新增 rejections（那是「我拒了客户端」）");
});
await t("🔧 门口就被拒的请求也算 arrivals（路径不对 / 模型名不对都会留下痕迹）", async () => {
  const env = { ...ENV, DEBUG: "true" };
  const badPath = await get("/v1/chat/completions/extra", { token: ENV.ROUTER_API_KEY, env });
  eq(badPath.status, 404, "未知路径应 404");
  let d = await (await get("/debug/last-error", { env })).json();
  ok(d.arrivals >= 1, `未知路径也要计入 arrivals，否则又变成"没请求"的假象：${d.arrivals}`);
  eq(d.last.path, "/v1/chat/completions/extra", "要能看见客户端到底打了哪个路径");
  const badModel = await post({ model: "nope/nope-model", messages: [{ role: "user", content: "hi" }] }, { env });
  eq(badModel.status, 404, "未知模型 404");
  d = await (await get("/debug/last-error", { env })).json();
  eq(d.last.asked_model, "nope/nope-model", "要记下它问的模型名（这是排错关键，且不含内容）");
  ok(!JSON.stringify(d).includes("hi\u0022"), "🔒 仍然不得出现正文");
});
await t("🔒 /debug/last-error：只暴露形状与字节数，绝不泄露一个字的内容", async () => {
  const env = { ...ENV, PROVIDER_ORDER: "groq", DEBUG: "true" };
  const secret = "这句话绝不能出现在诊断里";
  const res = await post({ model: "auto", messages: [{ role: "user", content: { bad: secret } }] }, { env });
  eq(res.status, 400, "非法 content 形状应 400");
  const d = await (await get("/debug/last-error", { env })).json();
  eq(d.arrivals >= 1, true, "arrivals 要计数（否则无从判断请求有没有进来）");
  eq(d.last.status, 400, "记录的状态码");
  ok(JSON.stringify(d.last.messages_shape).includes("user:object"), `形状摘要：${JSON.stringify(d.last.messages_shape)}`);
  const dump = JSON.stringify(d);
  ok(!dump.includes(secret), "🔒 诊断里出现了 prompt 原文！");
  ok(!dump.includes("key-groq-real"), "🔒 诊断里不得出现任何 key");
  // DEBUG 关掉时必须仍然要 key（诊断端点不能变成新的公开面）
  const locked = await get("/debug/last-error", { env: { ...ENV, PROVIDER_ORDER: "groq" } });
  eq(locked.status, 401, "没开 DEBUG 时诊断端点仍需鉴权");
});
await t("Responses 风格兼容：input/instructions 也能跑；取不到消息时 400 里列出顶层字段名", async () => {
  const env = { ...ENV, PROVIDER_ORDER: "groq" };
  const r1 = await post({ model: "auto", instructions: "你是中文助手", input: "你好" }, { env });
  eq(r1.status, 200, `input 字符串形状应可用：${JSON.stringify(await r1.clone().json())}`);
  eq(hits[0].lastText, "你好", "input 应转成最后一条 user 文本");
  const r2 = await post({ model: "auto", input: [{ role: "user", content: [{ type: "input_text", text: "多段" }] }] }, { env });
  eq(r2.status, 200, "input item 数组应可用");
  eq(hits[1].lastText, "多段", "input_text 块要拼进来");
  const r3 = await post({ model: "auto", prompt: "老式补全字段" }, { env });
  eq(r3.status, 200, "老式 prompt 字段也该能用");
  const r4 = await post({ model: "auto", foo: 1 }, { env });
  eq(r4.status, 400, "什么都没有时仍要 400");
  ok((await r4.json()).error.message.includes("foo"), "400 要说明收到了哪些顶层字段");
  eq((await post({ model: "auto", messages: [] }, { env })).status, 400, "空 messages 依旧 400");
});
await t("多模态形状兼容：content 数组拍平 / null 容忍 / 非法形状给具体 400", async () => {
  const env = { ...ENV, PROVIDER_ORDER: "groq" };
  // 客户端最常见的数组形状（OpenAI vision/agent 格式）：两段 text 拼成一个字符串
  const arr = await post({ messages: [{ role: "user", content: [
    { type: "text", text: "第一段" }, { type: "image_url", image_url: { url: "http://x/y.png" } },
    { type: "text", text: "第二段" },
  ] }] }, { env });
  eq(arr.status, 200, `数组 content 不该再被 400 挡掉：${JSON.stringify(await arr.clone().json())}`);
  eq(hits[0].lastText, "第一段\n第二段", "text 块应按序拼接、图片块丢弃");
  // assistant 只带 tool_calls 时 content 为 null：不能算错
  const nul = await post({ messages: [
    { role: "user", content: "查天气" },
    { role: "assistant", content: null, tool_calls: [{ id: "1" }] },
    { role: "user", content: "继续" },
  ] }, { env });
  eq(nul.status, 200, "content:null 应被容忍");
  // 真正不合法的形状：报错必须点明是第几条、什么类型
  const bad = await post({ messages: [{ role: "user", content: 42 }] }, { env });
  eq(bad.status, 400, "数字 content 仍应 400");
  const msg = (await bad.json()).error.message;
  ok(msg.includes("messages[0]") && msg.includes("number"), `错误信息要具体：${msg}`);
  eq((await post({ messages: [{ content: "没 role" }] }, { env })).status, 400, "缺 role 仍应 400");
});
await t("function calling 透传：openai 风格上游带 tools 进出，gemini 明确忽略不报错", async () => {
  const TOOLS = [{ type: "function", function: { name: "get_weather", parameters: { type: "object" } } }];
  const env = { ...ENV, PROVIDER_ORDER: "groq", GROQ_BASE_URL: `${baseOf()}/ok/v1` };
  const res = await post({ messages: [{ role: "user", content: "北京天气" }], tools: TOOLS }, { env });
  eq(res.status, 200, "带 tools 的请求不该被网关挡掉");
  eq(hits[0].tools, 1, "tools 必须原样送到上游");
  const body = await res.json();
  eq(body.choices[0].finish_reason, "tool_calls", "finish_reason 别被改写成 stop");
  const tc = body.choices[0].message.tool_calls;
  ok(Array.isArray(tc) && tc[0].function.name === "get_weather", `tool_calls 要带回：${JSON.stringify(body.choices[0].message)}`);
  eq(tc[0].function.arguments, "{}", "arguments 原样");
  // 流式：openai 风格是原样透传字节，tool_calls 增量不该被动过
  const sres = await post({ stream: true, messages: [{ role: "user", content: "北京天气" }], tools: TOOLS }, { env });
  const st = await sres.text();
  ok(st.includes("tool_calls"), "流式里没有 tool_calls 增量 = 被吞了");
  ok(st.includes("data: [DONE]"), "流式仍要 [DONE] 收尾");
  // 不带 tools 时上游请求体里不该凭空多出 tools 字段（省得有些上游报错）
  await post({ messages: [{ role: "user", content: "闲聊" }] }, { env });
  eq(hits[2].tools, 0, "没传 tools 就不该塞进去");
  // gemini 方言没有 tools 通路：忽略 tools 正常回答，而不是 400/502
  const genv = { ...ENV, PROVIDER_ORDER: "gemini", GEMINI_API_KEY: "key-gemini-real", GEMINI_BASE_URL: `${baseOf()}/gemini/v1beta` };
  const g = await post({ messages: [{ role: "system", content: "你是中文助手" }, { role: "user", content: "天气" }], tools: TOOLS }, { env: genv });
  eq(g.status, 200, "gemini 侧应忽略 tools 而不是报错");
});
await t("新增 provider agnes：通用 openai 通路无需特化代码", async () => {
  const base = { ...ENV, AGNES_API_KEY: "sk-agnes-real", AGNES_BASE_URL: `${baseOf()}/ok/v1` };
  // 只挂 agnes 一家：证明 openai style 是通用的，新免费源=加一行表
  const solo = await post({ model: "auto", messages: [{ role: "user", content: "冒泡排序" }] },
    { env: { ...base, PROVIDER_ORDER: "agnes" } });
  const sb = await solo.json();
  eq(solo.status, 200, `单挂 agnes 应 200，实际 ${JSON.stringify(sb.error || {})}`);
  eq(sb.provider, "agnes", "provider 标记");
  eq(hits.length, 1, "只打一次上游");
  ok(String(sb.model).startsWith("agnes:"), `model 回显：${sb.model}`);

  // 排在 openrouter 之后：openrouter 返 500 时降级到 agnes（冷却导致顺序抖动，故只断言最终答者）
  const chain = await post({ model: "auto", messages: [{ role: "user", content: "x" }] },
    { env: { ...base, PROVIDER_ORDER: "openrouter,agnes", OPENROUTER_BASE_URL: `${baseOf()}/bad-500/v1` } });
  eq(chain.status, 200, "openrouter 挂了不该把整个请求带崩");

  // 钉定 agnes/<model> 时不得扩散到其它 provider
  const before = hits.length;
  const pinned = await post({ model: "agnes/agnes-2.5-flash", messages: [{ role: "user", content: "x" }] },
    { env: { ...base, PROVIDER_ORDER: "openrouter,agnes" } });
  eq(pinned.status, 200, "钉定 agnes/<model> 应可用");
  eq(hits.length - before, 1, "钉定时只该多打一次上游");
});

await t("🔧 PROVIDER_ORDER 里的拼错 id 不再静默丢弃（会在 /healthz 报出来）", async () => {
  const body = await (await get("/healthz", {
    env: { ...ENV, PROVIDER_ORDER: "gemini,Agnes,openrouter,mistral" },  // 大写 A：认不出
  })).json();
  eq(body.providers.map(p => p.id).join(","), "gemini,openrouter,mistral", "认不出的不该进链路");
  eq(body.ignored_ids_in_PROVIDER_ORDER.join(","), "Agnes", "但该明确告诉我它被丢了");
});

await t("默认 PROVIDER_ORDER：agnes 紧随 openrouter，模型名对上官方 id", async () => {
  const body = await (await get("/healthz", { env: { ROUTER_API_KEY: "sk-test-1234567890" } })).json();
  const ids = body.providers.map(p => p.id);
  eq(ids.indexOf("agnes"), ids.indexOf("openrouter") + 1, `顺序：${ids.join(",")}`);
  const ag = body.providers.find(p => p.id === "agnes");
  eq(ag.model, "agnes-2.5-flash", "默认模型");
  eq(ag.enabled, false, "没配 key 时不该被启用");
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
