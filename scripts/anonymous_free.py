#!/usr/bin/env python3
"""
纯白嫖版 - 完全不用你自己的Key
3个源全是匿名的，Key随便填，不用注册，不用绑卡

直接跑就行：
  python scripts/anonymous_free.py "你好"
"""
import requests

# 3个纯匿名源，Key随便填，不用你自己的
FREE_PROVIDERS = [
    {
        "name": "LLM7.io (匿名 30次/分)",
        "url": "https://api.llm7.io/v1/chat/completions",
        "key": "unused",
        "model": "llama-3.1-8b-instant",
    },
    {
        "name": "Pollinations (纯匿名，无需Key)",
        "url": "https://text.pollinations.ai/openai/chat/completions",
        "key": "x",
        "model": "openai",
    },
    {
        "name": "Kilo Code (匿名 :free)",
        "url": "https://api.kilo.ai/api/gateway/chat/completions",
        "key": "kilo-anonymous",
        "model": "llama-3.1-8b-instant:free",
    },
]

def ask_free(prompt: str):
    messages = [{"role": "user", "content": prompt}]
    
    for p in FREE_PROVIDERS:
        try:
            print(f"\n→ 正在白嫖 [{p['name']}] ...")
            resp = requests.post(
                p["url"],
                headers={
                    "Authorization": f"Bearer {p['key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": p["model"],
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 512
                },
                timeout=20
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                print(f"✅ 成功！来源：{p['name']}")
                print("-"*60)
                print(content)
                print("-"*60)
                return content
            else:
                print(f"✗ {p['name']} 返回 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"✗ {p['name']} 挂了: {e}")
    
    print("\n❌ 3个匿名源都挂了，等几分钟再试，或去 https://github.com/open-free-llm-api/awesome-freellm-apis 找新的")
    return None

if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "你好，用中文讲个笑话"
    print(f"你: {prompt}")
    ask_free(prompt)
