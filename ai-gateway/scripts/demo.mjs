/**
 * 离线 demo：mock 上游 + 网关一起起，**不需要任何 API key、不需要联网**，
 * 就能亲眼看到失败转移 / SSE 流式 / 内存缓存 / 鉴权拒绝。
 *
 *   node scripts/demo.mjs            → http://localhost:8787
 *
 * 拓扑：mistral 故意 500、cohere 故意 429、groq 健康、gemini 走自己的方言。
 * 所以第一次请求你会看到"跳过 2 个坏的上游、第 3 个成功"。
 */
import { createServer } from "node:http";
import { handle } from "../src/router.js";
import { createMockServer } from "../test/mock-upstream.mjs";

const MOCK_PORT = Number.parseInt(process.env.MOCK_PORT || "8791", 10);
const GW_PORT = Number.parseInt(process.env.PORT || "8787", 10);
const base = `http://127.0.0.1:${MOCK_PORT}`;

const env = {
  PORT: String(GW_PORT),
  ROUTER_API_KEY: "demo-router-key",
  ADMIN_KEY: "demo-admin-key",
  PROVIDER_ORDER: "mistral,cohere,groq,gemini",
  TIMEOUT_MS: "3000",
  COOLDOWN_MS: "5000",
  CACHE_TTL_MS: "60000",
  MISTRAL_API_KEY: "demo-key-mistral", MISTRAL_BASE_URL: `${base}/bad-500/v1`,
  COHERE_API_KEY: "demo-key-cohere", COHERE_BASE_URL: `${base}/limited-429/v1`,
  GROQ_API_KEY: "demo-key-groq", GROQ_BASE_URL: `${base}/ok/v1`, GROQ_MODEL: "llama-3.3-70b-versatile",
  GEMINI_API_KEY: "demo-key-gemini", GEMINI_BASE_URL: `${base}/gemini/v1beta`,
};

const mock = createMockServer();
mock.listen(MOCK_PORT, "127.0.0.1", () => {
  const server = createServer(async (req, res) => {
    try {
      const headers = new Headers();
      for (const [k, v] of Object.entries(req.headers)) if (v !== undefined) headers.set(k, Array.isArray(v) ? v.join(", ") : v);
      const method = req.method || "GET";
      let body;
      if (method !== "GET" && method !== "HEAD") {
        const bufs = [];
        for await (const c of req) bufs.push(c);
        body = Buffer.concat(bufs);
      }
      const out = await handle(new Request(`http://127.0.0.1:${GW_PORT}${req.url}`, { method, headers, body }), env);
      res.writeHead(out.status, Object.fromEntries(out.headers.entries()));
      if (!out.body) return res.end();
      for await (const chunk of out.body) res.write(chunk);
      res.end();
    } catch (err) {
      res.writeHead(500, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { message: "demo internal error" } }));
      console.error(err);
    }
  });
  server.listen(GW_PORT, "0.0.0.0", () => {
    console.log(`
⚡ zeroroute-lite demo 已启动（mock 上游，无真实调用）
   网关    http://localhost:${GW_PORT}
   router key  demo-router-key
   admin  key  demo-admin-key

可以直接抄这几条命令试：

  # 1) 看哪些 provider 活着（key 已掩码）
  curl -s http://localhost:${GW_PORT}/healthz | python3 -m json.tool

  # 2) 失败转移：mistral 500 → cohere 429 → groq 成功
  curl -s -X POST http://localhost:${GW_PORT}/v1/chat/completions \\
    -H "authorization: Bearer demo-router-key" -H 'content-type: application/json' \\
    -d '{"messages":[{"role":"user","content":"你好"}]}' | python3 -m json.tool

  # 3) 再发一次同样的：命中内存缓存（x-cache: HIT）
  # 4) 流式：加 "stream":true，看 SSE 逐 token
  # 5) 没带 key → 401；拿 router key 去看 /metrics → 401
`);
  });
});
