#!/usr/bin/env bash
# Agent Lab 环境初始化:安装 OpenCode + 根据 Codespaces Secrets 自动写入 API 配置
set -u

echo "=== [1/3] 安装 OpenCode ==="
curl -fsSL https://opencode.ai/install | bash || true

# 确保 opencode 在 PATH 里(不管安装器把它放哪)
OC_BIN="$(command -v opencode 2>/dev/null || true)"
if [ -z "$OC_BIN" ]; then
  for p in "$HOME/.opencode/bin/opencode" "$HOME/.local/bin/opencode" "$HOME/bin/opencode"; do
    [ -x "$p" ] && OC_BIN="$p" && break
  done
fi
if [ -z "$OC_BIN" ]; then
  OC_BIN="$(find "$HOME" -maxdepth 4 -type f -name opencode 2>/dev/null | head -n1)"
fi
if [ -n "$OC_BIN" ]; then
  mkdir -p "$HOME/.local/bin"
  ln -sf "$OC_BIN" "$HOME/.local/bin/opencode"
  grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
  echo "  ✔ OpenCode 就绪: $OC_BIN"
else
  echo "  !! 未找到 opencode,请手动执行: curl -fsSL https://opencode.ai/install | bash"
fi

echo ""
echo "=== [2/3] 写入 API 配置(读取 Codespaces Secrets)==="
mkdir -p "$HOME/.config/opencode"

providers=""

add_provider() {
  if [ -z "$providers" ]; then
    providers="$1"
  else
    providers="${providers},
    $1"
  fi
}

if [ -n "${OPENROUTER_API_KEY:-}" ]; then
  # OpenRouter 是 OpenCode 内置 provider:不要覆盖 npm / baseURL,
  # 只补几个常用模型进选择器,其余模型由内置目录自动带出来。
  add_provider '"openrouter": {
      "options": {
        "apiKey": "'"${OPENROUTER_API_KEY}"'"
      },
      "models": {
        "deepseek/deepseek-chat-v3.1": { "name": "DeepSeek V3.1" },
        "qwen/qwen3-coder": { "name": "Qwen3 Coder" },
        "anthropic/claude-sonnet-4.5": { "name": "Claude Sonnet 4.5" },
        "google/gemini-2.5-flash": { "name": "Gemini 2.5 Flash" }
      }
    }'
  echo "  + OpenRouter 已配置(内置 provider,/models 里能看到全部可用模型)"
fi

if [ -n "${SILICONFLOW_API_KEY:-}" ]; then
  add_provider '"siliconflow": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "SiliconFlow",
      "options": {
        "baseURL": "https://api.siliconflow.cn/v1",
        "apiKey": "'"${SILICONFLOW_API_KEY}"'"
      },
      "models": {
        "deepseek-ai/DeepSeek-V3.1": { "name": "DeepSeek V3.1" },
        "Qwen/Qwen3-Coder": { "name": "Qwen3 Coder" }
      }
    }'
  echo "  + SiliconFlow(硅基流动)已配置"
fi

if [ -n "${SENSENOVA_API_KEY:-}" ]; then
  add_provider '"sensenova": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "SenseNova",
      "options": {
        "baseURL": "https://token.sensenova.cn/v1",
        "apiKey": "'"${SENSENOVA_API_KEY}"'"
      },
      "models": {
        "sensenova-6.7-flash-lite": { "name": "SenseNova 6.7 Flash-Lite" },
        "deepseek-v4-flash": { "name": "DeepSeek V4 Flash" }
      }
    }'
  echo "  + SenseNova(日日新)已配置"
fi

if [ -n "${GROQ_API_KEY:-}" ]; then
  add_provider '"groq": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Groq",
      "options": {
        "baseURL": "https://api.groq.com/openai/v1",
        "apiKey": "'"${GROQ_API_KEY}"'"
      },
      "models": {
        "llama-3.3-70b-versatile": { "name": "Llama 3.3 70B" },
        "openai/gpt-oss-120b": { "name": "GPT-OSS 120B" }
      }
    }'
  echo "  + Groq 已配置"
fi

cat > "$HOME/.config/opencode/opencode.json" <<EOF
{
  "\$schema": "https://opencode.ai/config.json",
  "provider": {
    ${providers}
  }
}
EOF
echo "  配置文件位置: ~/.config/opencode/opencode.json"

echo ""
echo "=== [3/3] 完成 ==="
if [ -n "$providers" ]; then
  echo "在终端运行 opencode,然后用 /models 选模型,直接下任务。"
else
  echo "!! 没检测到任何 API Key Secret。"
  echo "   去 github.com → Settings → Codespaces → Secrets 添加"
  echo "   (OPENROUTER_API_KEY / SILICONFLOW_API_KEY / SENSENOVA_API_KEY / GROQ_API_KEY 任选一或多个),"
  echo "   然后在 Codespace 里重建容器(Ctrl+Shift+P → Dev Containers: Rebuild Container)。"
fi
