# 多供应商 LLM 客户端

> 解决的问题：**任何一家 LLM 供应商封号、限流、改地区政策，流水线都不中断。**

## 为什么需要它

单一供应商的失效方式比想象中多：

| 失效类型 | 真实案例 |
|---|---|
| 地区政策收紧 | OpenRouter 2026 年起按**账单地址**（不是 IP）限制 OpenAI/Anthropic/Google 模型 |
| 注册被拒 | Groq 拒绝 outlook / proton / 别名邮箱，报 `signup error: trace_id=...` |
| 免费额度下架 | DeepSeek R1、Qwen3-Coder、Llama 3.3 的 `:free` 版本 2026 年陆续取消 |
| 限流 | OpenRouter 免费档未充值时 50 请求/天 |

靠"找一个更好的供应商"解决不了，因为下一家迟早也会变。**正确做法是让调用方不关心用的是哪一家。**

## 配置

有哪个填哪个，全部可选，至少填一个：

```bash
# —— 国内直连，不需要代理（推荐优先配置）——
export DEEPSEEK_API_KEY=sk-xxx        # platform.deepseek.com
export SILICONFLOW_API_KEY=sk-xxx     # cloud.siliconflow.cn
export MOONSHOT_API_KEY=sk-xxx        # platform.moonshot.cn

# —— 海外 ——
export GROQ_API_KEY=gsk_xxx           # console.groq.com/keys
export OPENROUTER_API_KEY=sk-or-xxx   # openrouter.ai/keys

# —— 本地兜底，完全离线 ——
export OLLAMA_HOST=http://localhost:11434
```

写进 `~/.bashrc` 或项目的 `.env` 里（注意 `.env` 别提交进 Git）。

## 体检

```bash
python3 production/llm_client.py
```

会列出哪些供应商已配置，并实际打一次请求确认连通。

## 使用

```python
import sys; sys.path.insert(0, "production")
from llm_client import chat

# 最简
print(chat("把这段话改写成解说开场白：..."))

# 带 system prompt
print(chat(
    "这段旁白 180 字，压到 120 字，保留悬念",
    system="你是电影解说编剧，语言凝练，节奏紧凑。",
))

# 档位：fast 便宜快速（分类/抽取/短改写），strong 强模型（长文生成）
chat("判断这句话的情绪，只回一个词", tier="fast")
chat("通篇润色这个三分钟解说剧本", tier="strong")

# 想知道实际用了哪家
from llm_client import chat_raw
text, used = chat_raw([{"role": "user", "content": "..."}])
print(used)   # 例如 'deepseek/deepseek-chat'
```

排查问题时开调试：

```bash
LLM_DEBUG=1 python3 你的脚本.py
```

会打印每次尝试的供应商和失败原因。

## 行为约定

**降级顺序**：按 `PROVIDERS` 表从上到下。国内直连排前面 —— 对大陆网络环境，"不需要代理"本身就是最高的可用性。

**错误处理**（已实测验证）：

| 状态码 | 行为 |
|---|---|
| 429 / 5xx | 该供应商内指数退避重试（1s、2s、4s + 抖动），仍失败则换下一家 |
| 400 / 401 / 403 / 404 | **立即跳过**，不浪费重试时间（key 无效重试无意义） |
| 全部失败 | 抛 `LLMError`，消息里含每一家的具体失败原因 |

**只用开源权重模型**。不碰 OpenAI / Anthropic / Google 的封闭权重模型 —— 那些才是有地区限制的，绕开它们等于绕开整类风控问题。

## 加一家新供应商

只要对方提供 OpenAI 兼容的 `/chat/completions`，在 `PROVIDERS` 加一条即可：

```python
Provider(
    name="新供应商",
    env_key="NEW_API_KEY",
    base_url="https://api.example.com/v1",
    models={"fast": "小模型-id", "strong": "大模型-id"},
),
```

调用方代码一行都不用改。

## 注意

- **不要把 key 写进代码或提交进 Git**，一律走环境变量。
- OpenRouter 这一项**只配了开源权重模型**。如果你的账号能用封闭权重模型，可以自行改 `models`，但要清楚：OpenRouter ToS 5.7 禁止用 VPN/代理规避受限模型，违反可导致账号永久终止。
- Ollama 是完全离线的兜底。装好后 `ollama pull qwen2.5:7b`，断网也能跑。
