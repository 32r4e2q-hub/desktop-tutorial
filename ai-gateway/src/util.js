/**
 * 小工具：全部基于 Web 标准 API（Node 18+ 与 Cloudflare Workers 通用），零依赖。
 */

/** 生成 OpenAI 风格的响应 id。Workers 里 crypto.randomUUID 可用。 */
export function newId(prefix = "chatcmpl") {
  const rnd = (globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2))
    .replace(/-/g, "").slice(0, 24);
  return `${prefix}-${rnd}`;
}

/**
 * 常数时间字符串比较。
 * 故意不用 `===`：短口令（ROUTER_API_KEY）逐字节短路比较可被计时攻击猜出长度/前缀。
 * 长度不等时也要把较长的循环走完，避免早退泄露信息。
 */
export function timingSafeEqual(a, b) {
  const s1 = String(a ?? "");
  const s2 = String(b ?? "");
  const len = Math.max(s1.length, s2.length);
  let diff = s1.length ^ s2.length;
  for (let i = 0; i < len; i++) {
    diff |= (s1.charCodeAt(i) || 0) ^ (s2.charCodeAt(i) || 0);
  }
  return diff === 0;
}

/** 从 Authorization 头取 Bearer token（也接受裸 token）。 */
export function bearerOf(headerValue) {
  const v = String(headerValue || "").trim();
  if (!v) return "";
  return v.startsWith("Bearer ") || v.startsWith("bearer ") ? v.slice(7).trim() : v;
}

export function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...headers },
  });
}

/** OpenAI 风格的错误体。message 里绝不放 key、上游响应体、堆栈。 */
export function apiError(message, status = 400, extra = {}) {
  return json({ error: { message: String(message).slice(0, 300), type: extra.type || "gateway_error", code: extra.code || null, ...(extra.failovers ? { failovers: extra.failovers } : {}) } }, status);
}

/** SHA-256 hex，用作缓存 key。 */
export async function sha256(text) {
  const buf = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

/**
 * 把上游的 SSE 字节流按行拆成 "data: <payload>" 的 payload 序列。
 * 只做切行，不解析 JSON —— 解析交给各 adapter。
 */
export function sseLineTransform(onPayload, { flush } = {}) {
  const dec = new TextDecoder();
  const enc = new TextEncoder();
  let buf = "";
  return new TransformStream({
    transform(chunk, controller) {
      buf += dec.decode(chunk, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, idx).replace(/\r$/, "");
        buf = buf.slice(idx + 1);
        if (!line.trim()) continue;
        if (!line.startsWith("data:")) continue;
        const payload = line.slice(5).trim();
        for (const out of onPayload(payload) || []) controller.enqueue(enc.encode(out));
      }
    },
    flush(controller) {
      if (buf.trim().startsWith("data:")) {
        const payload = buf.slice(5).trim();
        for (const out of onPayload(payload) || []) controller.enqueue(enc.encode(out));
      }
      if (flush) for (const out of flush() || []) controller.enqueue(enc.encode(out));
    },
  });
}

/** 把若干字符串打包成 SSE 响应体片段（含空行分隔）。 */
export function sseChunk(obj) {
  return `data: ${JSON.stringify(obj)}\n\n`;
}

/** OpenAI chunk 对象（流式的一个 token）。 */
export function openaiChunk({ id, model, created, text, finish = null }) {
  return {
    id, object: "chat.completion.chunk", created, model,
    choices: [{ index: 0, delta: text ? { content: text } : {}, finish_reason: finish }],
  };
}

/** 截断长文本，用于内存态错误摘要。**不用于记录 prompt**：本网关任何地方都不落盘对话内容。 */
const typeName = (v) => (v === null ? "null" : Array.isArray(v) ? "array" : typeof v);

/**
 * 把 message.content 拍平成字符串。
 *
 * OpenAI 规范里 content 既可以是字符串，也可以是内容块数组
 * （[{type:"text",text:"…"}, {type:"image_url",…}]）——多模态与 agent 类客户端
 * 基本都发数组。本网关只做纯文本：text 块按顺序拼接，非文本块丢掉并计数，
 * 其它形状给出具体的 400（而不是笼统一句"需要字符串"）。
 * 返回 { messages, dropped }；不合法时返回 { error }。
 */
export function flattenMessages(messages) {
  const out = [];
  let dropped = 0;
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    if (!m || typeof m !== "object" || typeof m.role !== "string") {
      return { error: `messages[${i}] 需要字符串 role（收到 ${typeName(m)}）` };
    }
    const c = m.content;
    let text;
    if (typeof c === "string") text = c;
    else if (c == null) text = "";                    // 只带 tool_calls 的 assistant 轮
    else if (Array.isArray(c)) {
      const parts = [];
      for (const p of c) {
        if (typeof p === "string") parts.push(p);
        else if (p && typeof p === "object" && typeof p.text === "string") parts.push(p.text);
        else dropped++;                                // image_url / input_audio / file …
      }
      text = parts.join("\n");
    } else if (typeof c === "object" && typeof c.text === "string") text = c.text;
    else return { error: `messages[${i}].content 形状不支持：${typeName(c)}（需要 string、内容块数组或 null）` };
    out.push({ ...m, content: text });
  }
  return { messages: out, dropped };
}

export function brief(s, n = 120) {
  const t = String(s ?? "").replace(/\s+/g, " ").trim();
  return t.length > n ? `${t.slice(0, n)}…` : t;
}
