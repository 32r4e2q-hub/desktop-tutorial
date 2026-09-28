#!/usr/bin/env python3
"""
纯白嫖聊天窗口版 - 不用你自己的Key
像微信一样一直聊，不用每次都打命令
"""
import requests

FREE_PROVIDERS = [
    {
        "name": "LLM7.io",
        "url": "https://api.llm7.io/v1/chat/completions",
        "key": "unused",
        "model": "llama-3.1-8b-instant",
    },
    {
        "name": "Pollinations",
        "url": "https://text.pollinations.ai/openai/chat/completions",
        "key": "x",
        "model": "openai",
    },
    {
        "name": "Kilo Code",
        "url": "https://api.kilo.ai/api/gateway/chat/completions",
        "key": "kilo-anonymous",
        "model": "llama-3.1-8b-instant:free",
    },
]

def ask(prompt, history):
    messages = history + [{"role": "user", "content": prompt}]
    for p in FREE_PROVIDERS:
        try:
            print(f"  [正在用 {p['name']} 回答...]", flush=True)
            resp = requests.post(
                p["url"],
                headers={"Authorization": f"Bearer {p['key']}", "Content-Type": "application/json"},
                json={"model": p["model"], "messages": messages, "temperature": 0.7, "max_tokens": 800},
                timeout=25
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                return content, p["name"]
        except Exception as e:
            continue
    return "❌ 3个免费源都挂了，等1分钟再试", "无"

if __name__ == "__main__":
    print("="*60)
    print("🤖 纯白嫖聊天窗口 - 不用你自己的Key")
    print("   输入 quit 退出，输入 clear 清空记忆")
    print("   3个匿名源自动轮询：LLM7.io / Pollinations / Kilo")
    print("="*60)
    
    history = []
    
    while True:
        try:
            q = input("\n你: ").strip()
            if not q:
                continue
            if q.lower() in ("quit", "exit", "q", "退出"):
                print("拜拜！")
                break
            if q.lower() in ("clear", "清空"):
                history = []
                print("✅ 记忆已清空")
                continue
            
            answer, provider = ask(q, history)
            print(f"\nAI [{provider}]: {answer}")
            
            # 保留最近10轮对话记忆
            history.append({"role": "user", "content": q})
            history.append({"role": "assistant", "content": answer})
            if len(history) > 20:
                history = history[-20:]
                
        except KeyboardInterrupt:
            print("\n拜拜！")
            break
