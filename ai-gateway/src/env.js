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
export const PROVIDER_DEFS = [
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
export function loadConfig(env = {}) {
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
export function maskKey(key) {
  const k = String(key || "");
  if (!k) return "未配置";
  if (k.length <= 8) return "••••";
  return `${k.slice(0, 2)}••••${k.slice(-2)}`;
}
