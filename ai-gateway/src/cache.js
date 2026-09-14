/**
 * 内存 LRU + TTL 缓存。
 *
 * 诚实说明（别被"0ms 缓存"这种话术骗）：
 *  - Worker 的内存是 **每个 isolate 私有**，冷启动/跨区域不共享，命中率不保证。
 *  - 只缓存 stream:false 的请求：流式要边收边转，重组后再缓存既费 CPU 又容易错序。
 *  - 要跨实例共享请换 KV / Durable Objects（见 README 的"延伸"）。
 */
export class MemoryCache {
  constructor({ max = 200, ttlMs = 300000 } = {}) {
    this.max = max;
    this.ttlMs = ttlMs;
    this.map = new Map();      // key -> { value, expires }
    this.hits = 0;
    this.misses = 0;
  }

  get(key) {
    const hit = this.map.get(key);
    if (!hit) { this.misses++; return undefined; }
    if (hit.expires < Date.now()) { this.map.delete(key); this.misses++; return undefined; }
    this.map.delete(key);        // LRU：命中后移到队尾
    this.map.set(key, hit);
    this.hits++;
    return hit.value;
  }

  set(key, value) {
    if (!this.ttlMs || this.max <= 0) return;
    this.map.set(key, { value, expires: Date.now() + this.ttlMs });
    while (this.map.size > this.max) this.map.delete(this.map.keys().next().value);
  }

  stats() {
    return { entries: this.map.size, hits: this.hits, misses: this.misses };
  }
}

/** 缓存 key：只取影响输出的字段，忽略 user/pipeline 噪声。 */
export async function cacheKeyOf(body) {
  const norm = JSON.stringify({
    m: body.model ?? "auto",
    msgs: (body.messages || []).map(x => [x.role, typeof x.content === "string" ? x.content : JSON.stringify(x.content)]),
    t: body.temperature ?? null,
    top_p: body.top_p ?? null,
    max_tokens: body.max_tokens ?? null,
  });
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(norm));
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, "0")).join("");
}
