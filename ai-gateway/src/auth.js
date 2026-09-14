/**
 * 鉴权与限流：全部 **fail-closed**（默认拒绝），这是 zeroroute 最大的两个洞所在处。
 *
 * zeroroute 的做法（已实测可利用）：
 *   1) 没配 ADMIN_KEY 时 `ADMIN_KEY = ADMIN_KEY || ROUTER_API_KEY` —— 塞进网页的半公开 key 直接变成管理员 key；
 *   2) `Sec-Fetch-Site: same-origin` 或 `Bearer free/public/zeroroute` 即放行 —— curl 随手伪造，任何人可白嫖你的免费额度。
 * 这里：两个 key 各管各的，缺失即拒绝；不认任何"演示 token"，不认任何请求头旁路。
 */
import { bearerOf, timingSafeEqual } from "./util.js";

/** 每个 isolate 独立的固定窗口计数。注意：不是全局配额，只做滥用的第一道防线。 */
export class RateLimiter {
  constructor({ limit = 60, windowMs = 60_000 } = {}) {
    this.limit = limit;
    this.windowMs = windowMs;
    this.buckets = new Map();   // key -> { count, start }
  }

  /** @returns {{allowed:boolean, retryAfterSec:number}} */
  check(key) {
    const now = Date.now();
    const b = this.buckets.get(key);
    if (!b || now - b.start > this.windowMs) {
      this.buckets.set(key, { count: 1, start: now });
      this.#prune(now);
      return { allowed: true, retryAfterSec: 0 };
    }
    b.count += 1;
    if (b.count > this.limit) {
      return { allowed: false, retryAfterSec: Math.max(1, Math.ceil((this.windowMs - (now - b.start)) / 1000)) };
    }
    return { allowed: true, retryAfterSec: 0 };
  }

  #prune(now) {
    if (this.buckets.size <= 512) return;
    for (const [k, v] of this.buckets) if (now - v.start > this.windowMs * 2) this.buckets.delete(k);
  }
}

/**
 * 校验调用方 token。
 * @param {string} provided  请求带来的 Bearer token
 * @param {string} expected  期望值（ROUTER_API_KEY 或 ADMIN_KEY）
 * @param {boolean} openMode 仅当 ALLOW_ANONYMOUS=true 且校验的是 chat key 时为 true
 */
export function checkToken(provided, expected, openMode = false) {
  const want = String(expected || "").trim();
  if (!want) return openMode === true;            // 未配置：要么明确开放，要么拒绝——绝不"兜底"到另一个 key
  return timingSafeEqual(provided, want);
}

/** 从 request 取调用方标识，用于限流分桶（优先用 token 而不是可伪造的 XFF）。 */
export function clientKeyOf(request, fallback = "anon") {
  const auth = request.headers.get("authorization") || "";
  const token = bearerOf(auth);
  if (token) {
    return `tok:${token.slice(0, 6)}…${token.length.toString(36)}`;
  }
  const xff = request.headers.get("cf-connecting-ip") || request.headers.get("x-real-ip") || "";
  return xff ? `ip:${xff}` : `ip:${fallback}`;
}
