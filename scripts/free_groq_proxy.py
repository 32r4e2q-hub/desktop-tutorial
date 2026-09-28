#!/usr/bin/env python3
"""
极简版 - 3合1 轮询客户端
直接当 OpenAI 客户端用，自动切换

用法：
  from free_groq_proxy import FreeGroqClient
  client = FreeGroqClient()
  print(client.ask("你好"))

或者命令行：
  python scripts/free_groq_proxy.py "你好"
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from free_groq_gateway import chat_with_failover

class FreeGroqClient:
    def __init__(self):
        pass
    
    def ask(self, prompt: str, model: str = None) -> str:
        messages = [{"role": "user", "content": prompt}]
        result = chat_with_failover(messages, model=model)
        return result["content"]
    
    def chat(self, messages, model=None):
        result = chat_with_failover(messages, model=model)
        return result["content"]

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "你好，用中文介绍一下自己"
    client = FreeGroqClient()
    try:
        answer = client.ask(prompt)
        print(answer)
    except Exception as e:
        print(f"失败: {e}", file=sys.stderr)
        sys.exit(1)
