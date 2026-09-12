#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多供应商 LLM 客户端 —— 单点风控免疫

设计目标：任何一家供应商封号/限流/改政策，脚本都继续跑，不用改一行调用代码。

用法（最简）：
    from llm_client import chat
    print(chat("把这段话改写成三分钟解说的开场白：..."))

用法（指定能力档位）：
    chat("写个正则", tier="fast")      # 便宜快速，用于分类/抽取/短改写
    chat("通篇润色这个剧本", tier="strong")  # 强模型，用于长文生成

配置（环境变量，有哪个填哪个，全部可选）：
    OPENROUTER_API_KEY   https://openrouter.ai/keys
    GROQ_API_KEY         https://console.groq.com/keys
    DEEPSEEK_API_KEY     https://platform.deepseek.com   （国内直连，无需代理）
    SILICONFLOW_API_KEY  https://cloud.siliconflow.cn    （国内直连，无需代理）
    MOONSHOT_API_KEY     https://platform.moonshot.cn    （国内直连，无需代理）
    OLLAMA_HOST          http://localhost:11434          （本地兜底，零依赖）

    LLM_DEBUG=1          打印每次尝试的供应商与失败原因

关键设计：
  * 全部走 OpenAI 兼容的 /chat/completions，所以新增供应商只要加一行配置。
  * 只使用开源权重模型 —— 不触碰 OpenAI/Anthropic/Google 的地区限制。
  * 429/5xx 自动指数退避重试；401/403 直接跳过该供应商（key 无效或被限）。
  * 供应商顺序 = 国内直连优先，因为对你来说"不需要代理"本身就是稳定性。
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

__all__ = ["chat", "chat_raw", "available_providers", "LLMError"]

DEBUG = os.environ.get("LLM_DEBUG", "") not in ("", "0", "false", "False")


def _log(msg: str) -> None:
    if DEBUG:
        print(f"[llm] {msg}", file=sys.stderr)


class LLMError(RuntimeError):
    """所有供应商都失败时抛出。"""


@dataclass
class Provider:
    name: str
    env_key: str                    # 读取 API key 的环境变量名；空字符串表示不需要 key
    base_url: str
    models: dict[str, str]          # tier -> model id
    key_required: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def api_key(self) -> str | None:
        if not self.key_required:
            return ""
        return os.environ.get(self.env_key) or None

    def enabled(self) -> bool:
        if not self.key_required:
            return bool(os.environ.get("OLLAMA_HOST"))
        return self.api_key is not None


# ---------------------------------------------------------------------------
# 供应商表
#
# 顺序即优先级。国内直连的排前面：对大陆网络环境，"不需要代理"就是最高的可用性。
# 全部为开源权重模型，不受 OpenAI/Anthropic/Google 的地区政策影响。
# ---------------------------------------------------------------------------
PROVIDERS: list[Provider] = [
    Provider(
        name="deepseek",
        env_key="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com/v1",
        models={"fast": "deepseek-chat", "strong": "deepseek-reasoner"},
    ),
    Provider(
        name="siliconflow",
        env_key="SILICONFLOW_API_KEY",
        base_url="https://api.siliconflow.cn/v1",
        models={
            "fast": "Qwen/Qwen2.5-7B-Instruct",
            "strong": "deepseek-ai/DeepSeek-V3",
        },
    ),
    Provider(
        name="moonshot",
        env_key="MOONSHOT_API_KEY",
        base_url="https://api.moonshot.cn/v1",
        models={"fast": "moonshot-v1-8k", "strong": "moonshot-v1-32k"},
    ),
    Provider(
        name="groq",
        env_key="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
        # Groq 只跑开源权重模型，速度是其最大优势
        models={
            "fast": "llama-3.1-8b-instant",
            "strong": "llama-3.3-70b-versatile",
        },
    ),
    Provider(
        name="openrouter",
        env_key="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
        # 只用开源权重 —— 规避封闭权重模型的地区限制
        models={
            "fast": "google/gemma-4-31b-it:free",
            "strong": "nvidia/nemotron-3-ultra-550b-a55b:free",
        },
        extra_headers={
            "HTTP-Referer": "https://github.com/32r4e2q-hub/desktop-tutorial",
            "X-Title": "commentary-pipeline",
        },
    ),
    Provider(
        name="ollama",
        env_key="",
        base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434") + "/v1",
        models={"fast": "qwen2.5:7b", "strong": "qwen2.5:14b"},
        key_required=False,
    ),
]

# 不值得重试的状态码：key 无效、权限不足、请求本身有问题
_FATAL_STATUS = {400, 401, 403, 404}


def available_providers() -> list[str]:
    """返回当前环境下已配置、可用的供应商名列表。"""
    return [p.name for p in PROVIDERS if p.enabled()]


def _post(
    provider: Provider,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int | None,
    timeout: int,
) -> dict[str, Any]:
    url = f"{provider.base_url}/chat/completions"
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    headers = {
        "Content-Type": "application/json",
        **provider.extra_headers,
    }
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat_raw(
    messages: list[dict[str, str]],
    *,
    tier: str = "strong",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    timeout: int = 120,
    max_retries: int = 2,
    only: list[str] | None = None,
) -> tuple[str, str]:
    """
    发起一次对话补全，返回 (正文, 实际使用的 "供应商/模型")。

    按 PROVIDERS 顺序依次尝试，直到某一家成功。
    429/5xx 会在该供应商内部指数退避重试；401/403/400 直接换下一家。

    only: 限定只用哪几家（供应商名列表），用于测试。
    """
    if not messages:
        raise ValueError("messages 不能为空")

    candidates = [p for p in PROVIDERS if p.enabled()]
    if only:
        candidates = [p for p in candidates if p.name in only]

    if not candidates:
        raise LLMError(
            "没有任何可用的供应商。请至少设置以下之一：\n"
            "  DEEPSEEK_API_KEY / SILICONFLOW_API_KEY / MOONSHOT_API_KEY\n"
            "  GROQ_API_KEY / OPENROUTER_API_KEY / OLLAMA_HOST"
        )

    errors: list[str] = []

    for provider in candidates:
        model = provider.models.get(tier) or provider.models.get("strong")
        if not model:
            continue

        for attempt in range(max_retries + 1):
            try:
                _log(f"尝试 {provider.name} / {model} (第 {attempt + 1} 次)")
                data = _post(
                    provider, model, messages, temperature, max_tokens, timeout
                )
                choices = data.get("choices") or []
                if not choices:
                    raise ValueError(f"响应中没有 choices: {str(data)[:200]}")
                content = (choices[0].get("message") or {}).get("content")
                if not content:
                    raise ValueError("响应 content 为空")
                _log(f"✓ {provider.name} 成功")
                return content, f"{provider.name}/{model}"

            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", "replace")[:300]
                except Exception:
                    pass
                msg = f"{provider.name}: HTTP {e.code} {body}"
                _log(msg)

                if e.code in _FATAL_STATUS:
                    errors.append(msg)
                    break  # key 有问题，重试无意义，换下一家

                if attempt < max_retries:
                    # 429 / 5xx：指数退避 + 抖动
                    delay = (2 ** attempt) + random.uniform(0, 0.5)
                    _log(f"  {delay:.1f}s 后重试")
                    time.sleep(delay)
                    continue
                errors.append(msg)

            except Exception as e:  # noqa: BLE001 — 网络层什么都可能抛
                msg = f"{provider.name}: {type(e).__name__}: {e}"
                _log(msg)
                if attempt < max_retries:
                    time.sleep((2 ** attempt) + random.uniform(0, 0.5))
                    continue
                errors.append(msg)

    raise LLMError(
        "所有供应商均失败：\n  " + "\n  ".join(errors)
    )


def chat(
    prompt: str,
    *,
    system: str | None = None,
    tier: str = "strong",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    **kwargs: Any,
) -> str:
    """便捷入口：给一段 prompt，拿回一段文本。"""
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    text, _ = chat_raw(
        messages,
        tier=tier,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
    return text


def _self_test() -> int:
    """python3 llm_client.py  —— 体检：看哪些供应商可用，并实际打一次。"""
    print("=" * 60)
    print("多供应商 LLM 客户端 —— 连通性体检")
    print("=" * 60)

    print("\n供应商状态：")
    any_on = False
    for p in PROVIDERS:
        on = p.enabled()
        any_on = any_on or on
        mark = "\033[32m✓ 已配置\033[0m" if on else "\033[90m− 未配置\033[0m"
        hint = "" if p.key_required else "  (本地，需 OLLAMA_HOST)"
        print(f"  {mark}  {p.name:<12} {p.env_key or 'OLLAMA_HOST':<22}{hint}")

    if not any_on:
        print(
            "\n\033[33m没有配置任何 key。至少设置一个再跑，例如：\033[0m\n"
            "  export DEEPSEEK_API_KEY=sk-xxx    # 国内直连，不用代理\n"
            "  export GROQ_API_KEY=gsk_xxx\n"
        )
        return 1

    print("\n实际调用测试（tier=fast）……")
    try:
        text, used = chat_raw(
            [{"role": "user", "content": "只回复两个字：收到"}],
            tier="fast",
            max_tokens=32,
            temperature=0,
        )
        print(f"  \033[32m✓ 成功\033[0m  使用了 {used}")
        print(f"  回复：{text.strip()[:80]}")
        return 0
    except LLMError as e:
        print(f"  \033[31m✗ 全部失败\033[0m\n{e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(_self_test())
