/**
 * 本地运行入口（Node 18+，零依赖）：node local-server.mjs
 * 读 .env（简易解析，不引 dotenv），把 process.env 当 env 传给同一个 handle()。
 */
import { createServer } from "node:http";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { handle } from "./src/router.js";

const here = dirname(fileURLToPath(import.meta.url));

/** 只支持 KEY=VALUE / 注释 / 引号包裹，够用了——引一个 dotenv 不如自己写 20 行。 */
function loadDotEnv(file) {
  const out = {};
  if (!existsSync(file)) return out;
  for (const line of readFileSync(file, "utf-8").split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const eq = t.indexOf("=");
    if (eq < 1) continue;
    const k = t.slice(0, eq).trim();
    let v = t.slice(eq + 1).trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    out[k] = v;
  }
  return out;
}

export function makeEnv(overrides = {}) {
  return { ...loadDotEnv(resolve(here, ".env")), ...process.env, ...overrides };
}

/** 供测试复用：拿到一个 fetch 函数而不是真端口监听。 */
export function makeHandler(env) {
  return (request) => handle(request, env);
}

const PORT = Number.parseInt(process.env.PORT || "8787", 10);
const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (isMain) {
  const env = makeEnv();
  const server = createServer(async (req, res) => {
    const started = Date.now();
    try {
      const host = req.headers.host || `127.0.0.1:${PORT}`;
      const headers = new Headers();
      for (const [k, v] of Object.entries(req.headers)) {
        if (v !== undefined) headers.set(k, Array.isArray(v) ? v.join(", ") : v);
      }
      const method = req.method || "GET";
      const body = method === "GET" || method === "HEAD" ? undefined : await collect(req);
      const response = await handle(new Request(`http://${host}${req.url}`, { method, headers, body }), env);

      res.writeHead(response.status, Object.fromEntries(response.headers.entries()));
      if (!response.body) return res.end();
      for await (const chunk of response.body) res.write(chunk);
      res.end();
    } catch (err) {
      console.error(`[zeroroute-lite] ${req.method} ${req.url} 500 in ${Date.now() - started}ms:`, err?.message || err);
      if (!res.headersSent) res.writeHead(500, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { message: "internal error" } }));   // 不回显堆栈
    }
  });

  server.listen(PORT, "0.0.0.0", () => {
    const enabled = Object.keys(loadDotEnv(resolve(here, ".env")));
    console.log(`⚡ zeroroute-lite  listening on http://localhost:${PORT}`);
    if (!env.ROUTER_API_KEY && !/^(1|true|yes)$/i.test(String(env.ALLOW_ANONYMOUS || ""))) {
      console.log("⚠️  ROUTER_API_KEY 未设置 → 所有 /v1 请求都会 503（fail-closed，故意的）。");
      console.log("    本地试用：export ROUTER_API_KEY=sk-local-123");
    }
    if (enabled.length === 0) console.log("    提示：把 .env.example 复制成 .env 并填入至少一个 provider 的 key。");
  });
}

async function collect(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return chunks.length ? Buffer.concat(chunks) : undefined;
}
