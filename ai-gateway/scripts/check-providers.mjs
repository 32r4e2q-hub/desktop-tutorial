/**
 * 上线前自查：拿你的真 key 逐个打一次上游，确认
 *   1) key 有效、2) 模型名真的存在、3) 流式真的能跑。
 *
 * 为什么需要这个脚本：各家免费政策与模型名变动很频繁（上游一旦改名，
 * 网关这边就是静默 404 → 一直 failover → 502）。跑一次比猜强。
 *
 *   cp .env.example .env   # 填 key
 *   node scripts/check-providers.mjs
 */
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { loadConfig } from "../src/env.js";

const here = dirname(dirname(fileURLToPath(import.meta.url)));

function loadDotEnv(file) {
  const out = {};
  if (!existsSync(file)) return out;
  for (const line of readFileSync(file, "utf-8").split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i < 1) continue;
    let v = t.slice(i + 1).trim();
    if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) v = v.slice(1, -1);
    out[t.slice(0, i).trim()] = v;
  }
  return out;
}

const env = { ...loadDotEnv(resolve(here, ".env")), ...process.env };
const cfg = loadConfig(env);
const enabled = cfg.providers.filter(p => p.enabled);

if (!enabled.length) {
  console.log("❌ 一个 provider 都没配上。检查 .env 里的 <PROVIDER>_API_KEY（长度需 > 8）。");
  process.exit(1);
}
console.log(`检测 ${enabled.length} 个 provider（超时 20s）：\n`);

const results = [];
for (const p of enabled) {
  const started = Date.now();
  const line = { id: p.id, model: p.model };
  try {
    const probe = { model: p.model, messages: [{ role: "user", content: "Say OK" }], max_tokens: 8 };
    const url = p.style === "openai" ? `${p.baseUrl}/chat/completions`
      : p.style === "gemini" ? `${p.baseUrl}/models/${p.model}:generateContent`
        : `${p.baseUrl}/accounts/${p.account}/ai/run/${p.model}`;
    const headers = p.style === "gemini"
      ? { "content-type": "application/json", "x-goog-api-key": p.apiKey }
      : { "content-type": "application/json", authorization: `Bearer ${p.apiKey}` };

    const res = await fetch(url, { method: "POST", headers, body: JSON.stringify(probe), signal: AbortSignal.timeout(20000) });
    line.http = res.status;
    if (!res.ok) {
      const t = (await res.text()).slice(0, 160).replace(/\s+/g, " ");
      line.verdict = res.status === 401 || res.status === 403 ? "key 无效" : res.status === 404 ? "模型名不存在 ← 改 <ID>_MODEL" : `HTTP ${res.status}`;
      line.detail = t;
    } else {
      const data = await res.json();
      const text = p.style === "openai" ? data?.choices?.[0]?.message?.content
        : p.style === "gemini" ? data?.candidates?.[0]?.content?.parts?.map(x => x.text).join("")
          : data?.result?.response;
      line.verdict = text ? "✅ 可用" : "⚠️ 200 但取不到正文";
      line.ms = Date.now() - started;
      // 流式也顺手验一次（能发现"只支持非流式"这类坑）
      try {
        const sres = await fetch(p.style === "openai" ? url : p.style === "gemini" ? `${p.baseUrl}/models/${p.model}:streamGenerateContent?alt=sse` : `${url}?stream=true`, {
          method: "POST", headers,
          body: JSON.stringify({ ...probe, stream: true }),
          signal: AbortSignal.timeout(20000),
        });
        const body = await sres.text();
        line.stream = sres.ok && /data:/.test(body) ? "✅ SSE" : `⚠️ ${sres.status}`;
      } catch (e) { line.stream = `⚠️ ${e.name}`; }
    }
  } catch (err) {
    line.verdict = err?.name === "TimeoutError" ? "⏱ 超时（20s）" : `❌ ${err?.cause?.code || err?.message}`;
  }
  results.push(line);
  const fmt = (l) => `${l.id.padEnd(12)} ${String(l.http ?? "---").padEnd(4)} ${String(l.ms ?? "-").padStart(5)}ms  ${l.stream || ""}  ${l.verdict}${l.detail ? ` — ${l.detail.slice(0, 90)}` : ""}`;
  console.log(fmt(line));
}

const good = results.filter(r => String(r.verdict).includes("可用")).length;
console.log(`\n可用 ${good}/${results.length}。`);
console.log(good === 0
  ? "提示：全都不通就先只留 GROQ_API_KEY 一个跑通，再逐个加回来。"
  : "把这些 id 填进 .env 的 PROVIDER_ORDER，顺序 = 失败转移优先级。");
