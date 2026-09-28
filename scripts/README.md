# 3合1 免费 Groq 网关 - 自动故障转移

**0绑卡、0充值、临时用，挂了自动切下一个，像网关一样**

这个沙盒里因为网络限制测不了，但你本地和 Google Cloud Shell 里能跑。

### 支持的免费源（全部 No Credit Card）

| 序号 | 名字 | Base URL | Key | 模型 | 限速 |
|------|------|----------|-----|------|------|
| 1 | LLM7.io | https://api.llm7.io/v1 | unused | llama-3.1-8b-instant, gpt-oss-20b | 30 RPM |
| 2 | Pollinations | https://text.pollinations.ai/openai | x | openai | 无限，纯匿名 |
| 3 | Kilo Code | https://api.kilo.ai/api/gateway | kilo-anonymous | llama-3.1-8b-instant:free | 匿名 |
| 4 | OpenRouter (可选) | https://openrouter.ai/api/v1 | 需 OPENROUTER_API_KEY | :free 模型 | 50/天免费 |

### 快速开始

```bash
pip install -r requirements-free-gateway.txt

# 1. 命令行直接问，会自动轮询
python scripts/free_groq_gateway.py --prompt "你好"

# 2. 交互式
python scripts/free_groq_gateway.py

# 3. 启动 OpenAI 兼容网关
python scripts/free_groq_gateway.py --serve --port 8000
```

启动网关后，你原来的代码**一行不用改**，只改 base_url：

```python
from openai import OpenAI
client = OpenAI(
    base_url="http://localhost:8000/v1",  # 指向本地网关
    api_key="anything"  # 随便填
)
res = client.chat.completions.create(
    model="llama-3.1-8b-instant",  # 网关会自动映射到可用源的模型
    messages=[{"role": "user", "content": "你好"}]
)
print(res.choices[0].message.content)
```

网关会自动：
- 轮询 3 个免费源
- 某个挂了（429, 500, 超时）马上切下一个
- 记录是哪个源返回的，方便调试

### 极简客户端

```python
from scripts.free_groq_proxy import FreeGroqClient
client = FreeGroqClient()
print(client.ask("用中文讲个笑话"))
```

### 为什么之前的方法挂了？

- Cerebras：2026年9月开始要 $5 验证了
- GitHub Models：官方已下线
- Groq 官方：风控太严，trace_id 错误
- Puter.com：现在也要绑卡验证了

所以现在最稳的就是这种匿名池轮询，挂一个切一个。

### 如果 3 个都挂了怎么办？

1. 去 https://github.com/open-free-llm-api/awesome-freellm-apis 找最新的免费源，加到 PROVIDERS 列表里就行
2. 或者去 Discord 找 Groq 管理员解封你的账号，官方的才是最稳的
