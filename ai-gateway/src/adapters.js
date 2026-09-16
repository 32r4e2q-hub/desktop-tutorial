/**
 * provider 适配器：把 OpenAI 格式的请求翻成各家上游格式，再把响应翻回 OpenAI 格式。
 *
 * 关键性能决定：对 OpenAI 兼容上游（Groq/Mistral/SambaNova/…）**流式原样透传字节**，
 * 不解析、不重组。Workers 免费档只有 10ms CPU/请求，逐 token JSON 解析是很奢侈的。
 */
import { newId, openaiChunk, sseChunk, sseLineTransform } from "./util.js";

const createdSec = () => Math.floor(Date.now() / 1000);

/** 组装一次对上游的 fetch 请求（不含 body 校验，交给 router）。 */
export function buildUpstream(provider, body, { stream }) {
  const p = {
    stream,
    temperature: body.temperature,
    top_p: body.top_p,
    max_tokens: body.max_tokens ?? body.max_completion_tokens,
    stop: body.stop,
  };

  if (provider.style === "openai") {
    const payload = { model: provider.model, messages: body.messages, stream, ...compact(p) };
    // agent 类客户端（Hermes 等）靠 tools 才能真动手：原样透传，不做方言翻译
    if (Array.isArray(body.tools) && body.tools.length) {
      payload.tools = body.tools;
      if (body.tool_choice !== undefined) payload.tool_choice = body.tool_choice;
      if (body.parallel_tool_calls !== undefined) payload.parallel_tool_calls = body.parallel_tool_calls;
    }
    return {
      url: `${provider.baseUrl}/chat/completions`,
      init: {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${provider.apiKey}` },
        body: JSON.stringify(payload),
      },
    };
  }

  if (provider.style === "gemini") {
    const system = (body.messages || []).filter(m => m.role === "system").map(m => m.content).join("\n");
    const contents = (body.messages || [])
      .filter(m => m.role !== "system")
      .map(m => ({ role: m.role === "assistant" ? "model" : "user", parts: [{ text: String(m.content ?? "") }] }));
    const payload = {
      contents,
      ...(system ? { systemInstruction: { parts: [{ text: system }] } } : {}),
      generationConfig: compact({
        temperature: p.temperature, topP: p.top_p, maxOutputTokens: p.max_tokens, stopSequences: p.stop,
      }),
    };
    const verb = stream ? "streamGenerateContent?alt=sse" : "generateContent";
    return {
      url: `${provider.baseUrl}/models/${provider.model}:${verb}`,
      init: {
        method: "POST",
        headers: { "content-type": "application/json", "x-goog-api-key": provider.apiKey },
        body: JSON.stringify(payload),
      },
    };
  }

  if (provider.style === "cloudflare") {
    const payload = {
      messages: body.messages,
      stream,
      ...compact({ temperature: p.temperature, top_p: p.top_p, max_tokens: p.max_tokens }),
    };
    return {
      url: `${provider.baseUrl}/accounts/${provider.account}/ai/run/${provider.model}${stream ? "?stream=true" : ""}`,
      init: {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${provider.apiKey}` },
        body: JSON.stringify(payload),
      },
    };
  }

  throw new Error(`unknown provider style: ${provider.style}`);
}

/** 非流式响应 → OpenAI chat.completion。 */
export function normalize(provider, raw) {
  if (provider.style === "openai") {
    const choice = raw?.choices?.[0];
    return {
      id: raw?.id || newId(),
      object: "chat.completion",
      created: raw?.created || createdSec(),
      model: `${provider.id}:${raw?.model || provider.model}`,
      provider: provider.id,
      choices: [{
        index: 0,
        message: {
          role: "assistant",
          content: choice?.message?.content ?? choice?.text ?? "",
          // 上游要调工具时 content 往往是空的，答案全在 tool_calls 里 —— 吞掉就等于让 agent 失忆
          ...(Array.isArray(choice?.message?.tool_calls) && choice.message.tool_calls.length
            ? { tool_calls: choice.message.tool_calls } : {}),
        },
        finish_reason: choice?.finish_reason || "stop",
      }],
      usage: raw?.usage || null,
    };
  }

  if (provider.style === "gemini") {
    const part = raw?.candidates?.[0]?.content?.parts || [];
    return {
      id: newId(), object: "chat.completion", created: createdSec(),
      model: `${provider.id}:${provider.model}`, provider: provider.id,
      choices: [{
        index: 0,
        message: { role: "assistant", content: part.map(x => x.text || "").join("") },
        finish_reason: raw?.candidates?.[0]?.finishReason ? "stop" : "stop",
      }],
      usage: raw?.usageMetadata
        ? { prompt_tokens: raw.usageMetadata.promptTokenCount, completion_tokens: raw.usageMetadata.candidatesTokenCount, total_tokens: raw.usageMetadata.totalTokenCount }
        : null,
    };
  }

  // cloudflare：result.response 可能是字符串，也可能是 JSON（带 response_format 时）
  const text = typeof raw?.result?.response === "string" ? raw.result.response : JSON.stringify(raw?.result ?? {});
  return {
    id: newId(), object: "chat.completion", created: createdSec(),
    model: `${provider.id}:${provider.model}`, provider: provider.id,
    choices: [{ index: 0, message: { role: "assistant", content: text }, finish_reason: raw?.result?.finish_reason || "stop" }],
    usage: raw?.result?.usage || null,
  };
}

/**
 * 流式响应的 body 变换器。
 * openai 兼容上游返回 null —— 直接 pipe，零解析。
 */
export function streamBodyFor(provider, id, model) {
  if (provider.style === "openai") return null;
  const created = createdSec();

  if (provider.style === "gemini") {
    return sseLineTransform((payload) => {
      if (payload === "[DONE]") return [sseChunk(openaiChunk({ id, model, created, finish: "stop" })), "data: [DONE]\n\n"];
      let obj; try { obj = JSON.parse(payload); } catch { return []; }
      const text = (obj?.candidates?.[0]?.content?.parts || []).map(x => x.text || "").join("");
      const out = [];
      if (text) out.push(sseChunk(openaiChunk({ id, model, created, text })));
      if (obj?.candidates?.[0]?.finishReason) {
        out.push(sseChunk(openaiChunk({ id, model, created, finish: "stop" })), "data: [DONE]\n\n");
      }
      return out;
    }, { flush: () => [sseChunk(openaiChunk({ id, model, created, finish: "stop" })), "data: [DONE]\n\n"] });
  }

  // cloudflare：data: {"response":"tok"} 或新版 {"token":{"text":"tok"}}
  return sseLineTransform((payload) => {
    if (payload === "[DONE]") return ["data: [DONE]\n\n"];
    let obj; try { obj = JSON.parse(payload); } catch { return []; }
    const text = typeof obj?.response === "string" ? obj.response : obj?.token?.text;
    return text ? [sseChunk(openaiChunk({ id, model, created, text }))] : [];
  }, { flush: () => ["data: [DONE]\n\n"] });
}

function compact(o) {
  const out = {};
  for (const [k, v] of Object.entries(o)) if (v !== undefined && v !== null && v !== "") out[k] = v;
  return out;
}

/**
 * 上游返回错误时给调用方看的摘要。
 * ⚠️ 故意**不带**上游响应体：有些厂商的 401 体会把你的 key 原样回显出来，
 *    透传给客户端等于泄露。（test/run-tests.mjs 里有一条断言专门守这个。）
 * 详细原因只进 ps.lastError（内存态）与 DEBUG 日志。
 */
export function upstreamReason(status, providerId) {
  const tag = status === 429 ? "rate limited"
    : status === 401 || status === 403 ? "key rejected"
      : status === 404 ? "model not found"
        : `http ${status}`;
  return `${providerId}: ${tag}`;
}
