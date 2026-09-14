/**
 * 把 src/ 下的多模块压成**一个文件**，好让你能直接在 Cloudflare 网页编辑器里粘贴。
 *   node scripts/bundle.mjs   →  bundle/worker.js
 *
 * 为什么需要：Cloudflare 的 Git 集成要配构建、网页编辑器又只适合单文件；
 * 对一个"我就想点几下部署完"的场景，单文件粘贴是最短路径。
 * src/ 仍是唯一真源：改完 src 跑一次本脚本，bundle/ 会被重新生成（测试也支持直接跑 bundle）。
 */
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(dirname(fileURLToPath(import.meta.url)));

/** 依赖顺序：被依赖的在前。只有 6 个文件，手写顺序比引入打包器更可控。 */
const ORDER = ["util.js", "env.js", "cache.js", "auth.js", "adapters.js", "router.js"];

const chunks = [];
for (const file of ORDER) {
  const src = readFileSync(resolve(here, "src", file), "utf-8");
  const body = src
    .split("\n")
    .filter(line => !/^\s*import\s.*from\s/.test(line) && !/^\s*import\s*\{/.test(line))
    .map(line => line.replace(/^export\s+default\s+/, "const __default_ = ").replace(/^export\s+/, ""))
    .join("\n");
  chunks.push(`// ───────────────── ${file} ─────────────────\n${body}`);
}

const out = `/**
 * zeroroute-lite —— 单文件版，可直接粘贴到 Cloudflare Workers 编辑器。
 * ⚠️ 自动生成，不要手改：改 ai-gateway/src/*.js 后跑 \`node scripts/bundle.mjs\`。
 * 功能：OpenAI 兼容 /v1/chat/completions（失败转移 + SSE 透传 + 内存缓存）、
 *       /v1/models、/healthz、/metrics（需 ADMIN_KEY）。
 * 配置全部来自环境变量/Secret：GROQ_API_KEY、ROUTER_API_KEY、ADMIN_KEY …（见 README 第 3 节）
 * 鉴权 fail-closed：没配 ROUTER_API_KEY 时 /v1 一律 503，不开放、不兜底、不认 any same-origin 旁路。
 * prompt 与回答一律不记录、不落盘。
 */
${chunks.join("\n\n")}

// ───────────────── 入口 ─────────────────
export default {
  fetch: (request, env) => handle(request, env),
};
`;

mkdirSync(resolve(here, "bundle"), { recursive: true });
writeFileSync(resolve(here, "bundle", "worker.js"), out, "utf-8");
console.log(`bundle/worker.js  ← ${ORDER.join(" + ")}\n${out.split("\n").length} 行`);
