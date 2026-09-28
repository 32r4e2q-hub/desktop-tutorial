#!/usr/bin/env python3
"""
超级版 - 20+ 免费 LLM 白嫖网关 - 自动故障转移
0绑卡，长期白嫖，挂了自动切下一个，像网关一样

来源：GitHub awesome-freellm-apis 134+ 免费接口整理
https://github.com/open-free-llm-api/awesome-freellm-apis

支持的免费源（全部 No Credit Card 或仅需邮箱注册）：
- 匿名无需Key：LLM7.io, Pollinations, Kilo Code
- 邮箱注册即得：OpenRouter, Groq, Mistral, Cohere, HuggingFace, Cerebras, SambaNova, OpenCode Zen, Chutes, Glhf, etc.

用法：
  pip install requests openai fastapi uvicorn python-dotenv

  # 1. 命令行直接问
  python scripts/free_groq_gateway.py --prompt "你好"

  # 2. 启动 OpenAI 兼容网关
  python scripts/free_groq_gateway.py --serve --port 8000

  # 3. 配置你的免费 Key（可选，不配置就只用匿名源）
  # 创建 .env 文件：
  OPENROUTER_API_KEY=sk-or-v1-...
  GROQ_API_KEY=gsk_...
  MISTRAL_API_KEY=...
  HF_TOKEN=hf_...
  CEREBRAS_API_KEY=csk-...
"""
import os
import sys
import time
import json
import random
import argparse
from typing import List, Dict, Optional

try:
    import requests
except ImportError:
    print("请先安装: pip install requests")
    sys.exit(1)

# 尝试加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# ========= 超级配置区 - 20+ 免费源 =========
# 每个都是 OpenAI 兼容，Key 从环境变量读，没有就跳过（匿名源除外）
PROVIDERS: List[Dict] = [
    # ===== Tier 1: 纯匿名，无需任何Key，0绑卡 =====
    {
        "name": "LLM7.io",
        "base_url": "https://api.llm7.io/v1",
        "api_key": "unused",
        "models": ["llama-3.1-8b-instant", "gpt-oss-20b", "qwen-2.5-7b-instruct", "deepseek-r1", "gemma-2-9b-it"],
        "default_model": "llama-3.1-8b-instant",
        "timeout": 30,
        "env": None,
        "no_card": True,
    },
    {
        "name": "Pollinations",
        "base_url": "https://text.pollinations.ai/openai",
        "api_key": "x",
        "models": ["openai", "openai-large", "mistral", "llama", "qwen"],
        "default_model": "openai",
        "timeout": 30,
        "env": None,
        "no_card": True,
    },
    {
        "name": "Kilo Code",
        "base_url": "https://api.kilo.ai/api/gateway",
        "api_key": "kilo-anonymous",
        "models": ["llama-3.1-8b-instant:free", "openai/gpt-oss-20b:free", "qwen-2.5-7b-instruct:free", "deepseek-r1:free"],
        "default_model": "llama-3.1-8b-instant:free",
        "timeout": 30,
        "env": None,
        "no_card": True,
    },

    # ===== Tier 2: 邮箱注册即得，无需绑卡 =====
    {
        "name": "OpenRouter-Free",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "models": [
            "meta-llama/llama-3.1-8b-instruct:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "google/gemma-2-9b-it:free",
            "qwen/qwen-2.5-7b-instruct:free",
            "deepseek/deepseek-r1:free",
        ],
        "default_model": "meta-llama/llama-3.1-8b-instruct:free",
        "timeout": 30,
        "env": "OPENROUTER_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://openrouter.ai/keys",
    },
    {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.getenv("GROQ_API_KEY", ""),
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "qwen/qwen3-32b",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
        ],
        "default_model": "llama-3.3-70b-versatile",
        "timeout": 20,  # Groq 超快
        "env": "GROQ_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://console.groq.com/keys",
    },
    {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "api_key": os.getenv("MISTRAL_API_KEY", ""),
        "models": ["mistral-small-latest", "mistral-large-latest", "codestral-latest", "open-mistral-7b", "open-mixtral-8x7b"],
        "default_model": "open-mistral-7b",
        "timeout": 30,
        "env": "MISTRAL_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://console.mistral.ai/api-keys/",
    },
    {
        "name": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key": os.getenv("CEREBRAS_API_KEY", ""),
        "models": ["llama-3.3-70b", "llama3.1-8b", "qwen-3-32b", "gpt-oss-120b"],
        "default_model": "llama3.1-8b",
        "timeout": 20,
        "env": "CEREBRAS_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://cloud.cerebras.ai/",
    },
    {
        "name": "HuggingFace",
        "base_url": "https://router.huggingface.co/v1",
        "api_key": os.getenv("HF_TOKEN", os.getenv("HUGGINGFACE_API_KEY", "")),
        "models": [
            "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "Qwen/Qwen2.5-7B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "HuggingFaceH4/zephyr-7b-beta"
        ],
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "timeout": 40,
        "env": "HF_TOKEN",
        "no_card": True,
        "optional": True,
        "get_key": "https://huggingface.co/settings/tokens",
    },
    {
        "name": "Cohere",
        "base_url": "https://api.cohere.com/compatibility/v1",
        "api_key": os.getenv("COHERE_API_KEY", ""),
        "models": ["command-r", "command-r-plus", "command", "command-light"],
        "default_model": "command-r",
        "timeout": 30,
        "env": "COHERE_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://dashboard.cohere.com/api-keys",
    },
    {
        "name": "SambaNova",
        "base_url": "https://api.sambanova.ai/v1",
        "api_key": os.getenv("SAMBANOVA_API_KEY", ""),
        "models": ["Meta-Llama-3.1-8B-Instruct", "Meta-Llama-3.1-70B-Instruct", "Meta-Llama-3.1-405B-Instruct"],
        "default_model": "Meta-Llama-3.1-8B-Instruct",
        "timeout": 30,
        "env": "SAMBANOVA_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://cloud.sambanova.ai/",
    },
    {
        "name": "Chutes",
        "base_url": "https://api.chutes.ai/v1",
        "api_key": os.getenv("CHUTES_API_KEY", ""),
        "models": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct"],
        "default_model": "deepseek-ai/DeepSeek-V3",
        "timeout": 30,
        "env": "CHUTES_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://chutes.ai/app/api",
    },
    {
        "name": "Glhf.chat",
        "base_url": "https://glhf.chat/api/openai/v1",
        "api_key": os.getenv("GLHF_API_KEY", ""),
        "models": ["hf:meta-llama/Meta-Llama-3.1-8B-Instruct", "hf:Qwen/Qwen2.5-7B-Instruct"],
        "default_model": "hf:meta-llama/Meta-Llama-3.1-8B-Instruct",
        "timeout": 30,
        "env": "GLHF_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://glhf.chat/",
    },
    {
        "name": "OpenCode Zen",
        "base_url": "https://opencode.ai/zen/v1",
        "api_key": os.getenv("OPENCODE_API_KEY", ""),
        "models": ["deepseek-v3", "qwen-2.5-72b", "llama-3.3-70b"],
        "default_model": "deepseek-v3",
        "timeout": 30,
        "env": "OPENCODE_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://opencode.ai/zen",
    },
    {
        "name": "Agnes AI",
        "base_url": "https://apihub.agnes-ai.com/v1",
        "api_key": os.getenv("AGNES_API_KEY", ""),
        "models": ["llama-3.1-8b", "qwen-2.5-7b"],
        "default_model": "llama-3.1-8b",
        "timeout": 30,
        "env": "AGNES_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://agnes-ai.com/",
    },
    {
        "name": "AionLabs",
        "base_url": "https://api.aionlabs.ai/v1",
        "api_key": os.getenv("AIONLABS_API_KEY", ""),
        "models": ["llama-3.1-8b", "qwen-2.5"],
        "default_model": "llama-3.1-8b",
        "timeout": 30,
        "env": "AIONLABS_API_KEY",
        "no_card": True,
        "optional": True,
    },
    # Google Gemini 的 OpenAI 兼容端点
    {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key": os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")),
        "models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemma-2-9b-it"],
        "default_model": "gemini-2.0-flash",
        "timeout": 30,
        "env": "GEMINI_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://aistudio.google.com/app/apikey",
    },
    # Cloudflare Workers AI (需要 ACCOUNT_ID)
    {
        "name": "Cloudflare Workers AI",
        "base_url": f"https://api.cloudflare.com/client/v4/accounts/{os.getenv('CF_ACCOUNT_ID','')}/ai/v1",
        "api_key": os.getenv("CF_API_KEY", ""),
        "models": ["@cf/meta/llama-3.1-8b-instruct", "@cf/qwen/qwen1.5-7b-chat-awq"],
        "default_model": "@cf/meta/llama-3.1-8b-instruct",
        "timeout": 30,
        "env": "CF_API_KEY",
        "no_card": True,
        "optional": True,
        "get_key": "https://dash.cloudflare.com/",
    },
]

_round_robin_index = 0

def get_active_providers():
    active = []
    for p in PROVIDERS:
        if p.get("optional") and not p.get("api_key"):
            continue
        # Cloudflare 特殊检查
        if p["name"] == "Cloudflare Workers AI" and not os.getenv("CF_ACCOUNT_ID"):
            continue
        active.append(p)
    return active

def get_next_providers():
    global _round_robin_index
    active = get_active_providers()
    if not active:
        # 至少返回匿名源
        return [p for p in PROVIDERS if not p.get("optional")]
    start = _round_robin_index % len(active)
    ordered = active[start:] + active[:start]
    _round_robin_index = (_round_robin_index + 1) % len(active)
    if random.random() < 0.3:
        random.shuffle(ordered)
    return ordered

def call_one_provider(provider, messages, model=None):
    base_url = provider["base_url"].rstrip("/")
    api_key = provider["api_key"]
    use_model = model if model and model in provider["models"] else provider["default_model"]
    
    url = f"{base_url}/chat/completions"
    # Gemini 的 OpenAI 兼容端点已经是 /openai/，不需要再加 /chat/completions? 其实需要
    # 上面已经处理

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # 一些特殊 provider 需要额外 header
    if provider["name"] == "OpenRouter-Free":
        headers["HTTP-Referer"] = "https://github.com/open-free-llm-api/awesome-freellm-apis"
        headers["X-Title"] = "Free Gateway"

    payload = {
        "model": use_model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=provider.get("timeout", 30))
    
    if resp.status_code != 200:
        raise RuntimeError(f"[{provider['name']}] HTTP {resp.status_code}: {resp.text[:800]}")
    
    try:
        data = resp.json()
    except:
        raise RuntimeError(f"[{provider['name']}] 非 JSON 返回: {resp.text[:500]}")

    if "choices" in data and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if "message" in choice and "content" in choice["message"]:
            content = choice["message"]["content"]
            if content:
                return content
        if "text" in choice:
            return choice["text"]
    if "content" in data:
        return data["content"]
    
    raise RuntimeError(f"[{provider['name']}] 无法解析: {str(data)[:800]}")

def chat_with_failover(messages, model=None, max_retries=10):
    providers = get_next_providers()
    last_error = None
    
    for i, provider in enumerate(providers):
        if i >= max_retries:
            break
        try:
            print(f"  → 尝试 [{provider['name']}] {model or provider['default_model']} ...", flush=True)
            content = call_one_provider(provider, messages, model)
            if content and len(content.strip()) > 0:
                return {
                    "content": content,
                    "provider": provider["name"],
                    "model": provider["default_model"],
                    "base_url": provider["base_url"]
                }
        except Exception as e:
            last_error = e
            print(f"  ✗ [{provider['name']}] 失败: {e}", flush=True)
            time.sleep(0.5)
            continue
    
    raise RuntimeError(f"所有 {len(providers)} 个免费源都挂了，最后错误: {last_error}")

def cli_mode(prompt, model=None):
    messages = [{"role": "user", "content": prompt}]
    try:
        result = chat_with_failover(messages, model=model)
        print("\n" + "="*70)
        print(f"✅ 成功 [{result['provider']}] {result['model']}")
        print(f"   {result['base_url']}")
        print("="*70)
        print(result["content"])
        print("="*70)
        print(f"\n💡 提示：已自动轮询 {len(get_active_providers())} 个免费源，当前可用 {len(get_active_providers())} 个")
        print("   想长期白嫖，去 .env 里加更多 Key：OPENROUTER_API_KEY, GROQ_API_KEY, MISTRAL_API_KEY, HF_TOKEN 等")
    except Exception as e:
        print(f"\n❌ 全部失败: {e}", file=sys.stderr)
        print("\n去这里找更多免费 Key 加到 .env：https://github.com/open-free-llm-api/awesome-freellm-apis", file=sys.stderr)
        sys.exit(1)

def serve_gateway(port=8000):
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        import uvicorn
    except ImportError:
        print("需要安装: pip install fastapi uvicorn")
        sys.exit(1)

    app = FastAPI(title="Free LLM 超级网关 - 20+免费源故障转移", version="2.0")

    @app.get("/")
    def root():
        active = get_active_providers()
        return {
            "message": f"超级网关运行中，当前 {len(active)} 个可用源",
            "active_providers": [{"name": p["name"], "model": p["default_model"], "no_card": p.get("no_card"), "env": p.get("env")} for p in active],
            "all_providers": len(PROVIDERS),
            "usage": "POST /v1/chat/completions OpenAI 兼容，自动故障转移",
            "get_more_keys": "https://github.com/open-free-llm-api/awesome-freellm-apis",
            "env_example": {
                "OPENROUTER_API_KEY": "sk-or-v1-...",
                "GROQ_API_KEY": "gsk_...",
                "MISTRAL_API_KEY": "...",
                "HF_TOKEN": "hf_...",
                "GEMINI_API_KEY": "...",
                "CEREBRAS_API_KEY": "csk-...",
            }
        }

    @app.get("/v1/models")
    def list_models():
        all_models = []
        for p in get_active_providers():
            for m in p["models"]:
                all_models.append({"id": m, "object": "model", "owned_by": p["name"]})
        return {"object": "list", "data": all_models}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        body = await request.json()
        messages = body.get("messages", [])
        model = body.get("model")
        
        if not messages:
            return JSONResponse({"error": "messages 不能为空"}, status_code=400)
        
        try:
            result = chat_with_failover(messages, model=model)
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": result["model"],
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": result["content"]},
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "provider": result["provider"]
            }
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=502)

    print(f"\n🚀 超级网关启动 http://0.0.0.0:{port}")
    print(f"   可用源 {len(get_active_providers())}/{len(PROVIDERS)}: {[p['name'] for p in get_active_providers()]}")
    print(f"   curl http://localhost:{port}/v1/models")
    print(f"   加更多 Key 到 .env 可解锁更多源：https://github.com/open-free-llm-api/awesome-freellm-apis\n")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="20+免费源超级网关 - 自动故障转移")
    parser.add_argument("--prompt", type=str, help="直接提问")
    parser.add_argument("--model", type=str, help="指定模型")
    parser.add_argument("--serve", action="store_true", help="启动网关")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--list", action="store_true", help="列出所有可用源")
    
    args = parser.parse_args()
    
    if args.list:
        active = get_active_providers()
        print(f"\n当前可用 {len(active)}/{len(PROVIDERS)} 个免费源：\n")
        for p in active:
            print(f"  ✅ {p['name']:20} {p['default_model']:35} env={p.get('env') or '匿名'}")
        print(f"\n未配置的（加 Key 到 .env 可解锁）：\n")
        for p in PROVIDERS:
            if p.get("optional") and not p.get("api_key"):
                print(f"  ⭕ {p['name']:20} 需 {p.get('env')} -> {p.get('get_key','')}")
        sys.exit(0)

    if args.serve:
        serve_gateway(port=args.port)
    elif args.prompt:
        cli_mode(args.prompt, model=args.model)
    else:
        print("超级网关 - 输入问题自动轮询 20+ 免费源 (quit 退出)")
        print(f"当前可用 {len(get_active_providers())} 个源，输入 --list 查看全部")
        while True:
            try:
                q = input("\n你: ").strip()
                if not q or q.lower() in ("quit", "exit", "q"):
                    break
                cli_mode(q)
            except KeyboardInterrupt:
                break
