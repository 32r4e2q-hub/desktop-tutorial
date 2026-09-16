/**
 * 离线 mock 上游：给自检与 demo 用，让整条链路不联网也能跑。
 * 单独运行：node test/mock-upstream.mjs 8791
 *
 * 路径首段决定"这个 provider 怎么坏"：
 *   /ok            正常回答（支持 stream）
 *   /bad-500       500 崩溃
 *   /limited-429   429 限流
 *   /denied-401    401 key 无效（且**故意在错误体里回显 key**，用来验证网关不外泄上游响应体）
 *   /slow          挂住不回（验证超时）
 *   /poison        200 + 空 SSE（验证"连上了但没吐字"要 failover）
 *   /json-only     收了 stream=true 却只回 JSON（验证合成单 chunk SSE）
 *   /gemini        Gemini 方言（stream 标记在 URL verb 上）
 *   /cf            Cloudflare Workers AI 方言
 */
import { createServer } from "node:http";

export const hits = [];

export function createMockServer() {
  return createServer(async (req, res) => {
    let raw = "";
    for await (const c of req) raw += c;
    const body = (() => { try { return JSON.parse(raw || "{}"); } catch { return {}; } })();
    const kind = req.url.split("/")[1] || "ok";
    const lastMsg = Array.isArray(body.messages) ? body.messages[body.messages.length - 1] : null;
    hits.push({
      kind, model: body.model || "?", auth: req.headers.authorization || "", tools: (body.tools || []).length,
      // 断言用：上游实际收到的最后一条文本（多模态数组应已被拍平成字符串）
      lastText: typeof lastMsg?.content === "string"
        ? lastMsg.content
        : (body.contents?.[body.contents.length - 1]?.parts || []).map(p => p.text || "").join(""),
    });

    const reply = (code, obj) => { res.writeHead(code, { "content-type": "application/json" }); res.end(JSON.stringify(obj)); };
    const sseHead = () => res.writeHead(200, { "content-type": "text/event-stream" });
    const openaiChunk = (text, finish = null) => `data: ${JSON.stringify({
      id: "cmpl-mock", object: "chat.completion.chunk", created: 1, model: "mock-model",
      choices: [{ index: 0, delta: text ? { content: text } : {}, finish_reason: finish }],
    })}\n\n`;

    if (kind === "bad-500") return reply(500, { error: { message: "upstream exploded" } });
    if (kind === "limited-429") return reply(429, { error: { message: "rate limit reached" } });
    if (kind === "denied-401") return reply(401, { error: { message: `invalid api key (echo: ${req.headers.authorization})` } });
    if (kind === "poison") { sseHead(); return res.end(""); }
    if (kind === "slow") return;                       // 不响应 → 触发客户端超时
    if (kind === "json-only") {
      return reply(200, {
        id: "cmpl-jsononly", object: "chat.completion", created: 1, model: "mock-model",
        choices: [{ index: 0, message: { role: "assistant", content: "hello from ok" }, finish_reason: "stop" }],
      });
    }

    // ── Gemini 方言：请求体形状与响应形状都和 OpenAI 不同 ──
    if (kind === "gemini") {
      if (!Array.isArray(body.contents) || body.contents.some(c => !["user", "model"].includes(c.role))) {
        return reply(400, { error: { message: "gemini 请求体翻译错了" } });
      }
      if (body.systemInstruction?.parts?.[0]?.text !== "你是中文助手") {
        return reply(400, { error: { message: "systemInstruction 没翻译出来" } });
      }
      if (body.stream || req.url.includes("streamGenerateContent")) {   // gemini 的 stream 标记在 URL verb 里
        sseHead();
        res.write('data: {"candidates":[{"content":{"parts":[{"text":"维度"}],"role":"model"}}]}\n\n');
        res.write('data: {"candidates":[{"content":{"parts":[{"text":"翻译"}],"role":"model"},"finishReason":"STOP"}],"usageMetadata":{"promptTokenCount":5,"candidatesTokenCount":2}}\n\n');
        return res.end();
      }
      return reply(200, {
        candidates: [{ content: { parts: [{ text: "维度翻译 OK" }], role: "model" }, finishReason: "STOP" }],
        usageMetadata: { promptTokenCount: 5, candidatesTokenCount: 2, totalTokenCount: 7 },
      });
    }

    // ── Cloudflare Workers AI 方言 ──
    if (kind === "cf") {
      if (!req.url.includes("/accounts/acct-1/ai/run/")) return reply(400, { error: { message: "account/run 路径不对" } });
      if (body.stream) {
        sseHead();
        res.write('data: {"token":{"text":"云上"}}\n\n');
        res.write('data: {"token":{"text":"结果"}}\n\n');
        return res.end("data: [DONE]\n\n");
      }
      return reply(200, { success: true, result: { response: "云端答案" } });
    }

    // ── 默认：健康上游 ──
    const wantTool = Array.isArray(body.tools) && body.tools.length > 0;
    if (body.stream && wantTool) {            // 工具调用的流式形状
      sseHead();
      const call = { index: 0, id: "call_1", type: "function",
        function: { name: body.tools[0].function?.name || "lookup", arguments: "{}" } };
      res.write(`data: ${JSON.stringify({ id: "cmpl-mock", object: "chat.completion.chunk", created: 1,
        model: "mock-model", choices: [{ index: 0, delta: { role: "assistant", tool_calls: [call] } }] })}\n\n`);
      res.write(`data: ${JSON.stringify({ id: "cmpl-mock", object: "chat.completion.chunk", created: 1,
        model: "mock-model", choices: [{ index: 0, delta: {}, finish_reason: "tool_calls" }] })}\n\n`);
      return res.end("data: [DONE]\n\n");
    }
    if (wantTool) {                            // 非流式：content 为空，答案在 tool_calls
      return reply(200, {
        id: "cmpl-mock", object: "chat.completion", created: 1, model: "mock-model",
        choices: [{ index: 0, message: { role: "assistant", content: null, tool_calls:
          [{ id: "call_1", type: "function", function: { name: body.tools[0].function?.name || "lookup", arguments: "{}" } }] },
          finish_reason: "tool_calls" }],
      });
    }
    if (body.stream) {
      sseHead();
      for (const w of ["你好", "，", "世界"]) res.write(openaiChunk(w));
      res.write(openaiChunk("", "stop"));
      return res.end("data: [DONE]\n\n");
    }
    return reply(200, {
      id: "cmpl-mock", object: "chat.completion", created: 1, model: "mock-model",
      choices: [{ index: 0, message: { role: "assistant", content: `hello from ${kind}` }, finish_reason: "stop" }],
      usage: { prompt_tokens: 9, completion_tokens: 3, total_tokens: 12 },
    });
  });
}

if (process.argv[1] && process.argv[1].endsWith("mock-upstream.mjs")) {
  const port = Number.parseInt(process.argv[2] || "8791", 10);
  createMockServer().listen(port, "127.0.0.1", () => console.log(`mock upstream on http://127.0.0.1:${port}`));
}
