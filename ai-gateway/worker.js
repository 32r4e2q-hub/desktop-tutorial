/**
 * Cloudflare Worker 入口。
 * 部署：wrangler secret put GROQ_API_KEY && wrangler deploy
 */
import { handle } from "./src/router.js";

export default {
  fetch: (request, env) => handle(request, env),
};
