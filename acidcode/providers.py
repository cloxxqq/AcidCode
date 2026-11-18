from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    name: str
    label: str
    base_url: str
    env: str
    docs: str
    default_model: str
    needs_key: bool = True


_PROVIDERS = [
    Provider(
        "openrouter",
        "OpenRouter (много моделей, есть :free)",
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        "https://openrouter.ai/keys",
        "meta-llama/llama-3.3-70b-instruct:free",
    ),
    Provider(
        "google",
        "Google AI Studio (Gemini)",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "GEMINI_API_KEY",
        "https://aistudio.google.com/apikey",
        "gemini-3-flash-preview",
    ),
    Provider(
        "groq",
        "Groq (быстрый инференс)",
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
        "https://console.groq.com/keys",
        "llama-3.3-70b-versatile",
    ),
    Provider(
        "cerebras",
        "Cerebras",
        "https://api.cerebras.ai/v1",
        "CEREBRAS_API_KEY",
        "https://cloud.cerebras.ai",
        "llama-3.3-70b",
    ),
    Provider(
        "mistral",
        "Mistral (Experiment — бесплатно)",
        "https://api.mistral.ai/v1",
        "MISTRAL_API_KEY",
        "https://console.mistral.ai/api-keys",
        "mistral-small-latest",
    ),
    Provider(
        "github",
        "GitHub Models (бесплатно с аккаунтом)",
        "https://models.github.ai/inference",
        "GITHUB_TOKEN",
        "https://github.com/settings/tokens",
        "openai/gpt-4o-mini",
    ),
    Provider(
        "sambanova",
        "SambaNova Cloud",
        "https://api.sambanova.ai/v1",
        "SAMBANOVA_API_KEY",
        "https://cloud.sambanova.ai",
        "Meta-Llama-3.3-70B-Instruct",
    ),
    Provider(
        "nvidia",
        "NVIDIA NIM (free credits)",
        "https://integrate.api.nvidia.com/v1",
        "NVIDIA_API_KEY",
        "https://build.nvidia.com",
        "meta/llama-3.3-70b-instruct",
    ),
    Provider(
        "together",
        "Together AI",
        "https://api.together.xyz/v1",
        "TOGETHER_API_KEY",
        "https://api.together.ai/settings/api-keys",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    ),
    Provider(
        "fireworks",
        "Fireworks AI",
        "https://api.fireworks.ai/inference/v1",
        "FIREWORKS_API_KEY",
        "https://fireworks.ai/account/api-keys",
        "accounts/fireworks/models/llama-v3p3-70b-instruct",
    ),
    Provider(
        "deepseek",
        "DeepSeek (не free, но копейки)",
        "https://api.deepseek.com/v1",
        "DEEPSEEK_API_KEY",
        "https://platform.deepseek.com/api_keys",
        "deepseek-chat",
    ),
    Provider(
        "openai",
        "OpenAI (GPT-5.x)",
        "https://api.openai.com/v1",
        "OPENAI_API_KEY",
        "https://platform.openai.com/api-keys",
        "gpt-5.4-mini",
    ),
    Provider(
        "anthropic",
        "Anthropic (Claude 5.x, OpenAI-совместимый шлюз)",
        "https://api.anthropic.com/v1",
        "ANTHROPIC_API_KEY",
        "https://console.anthropic.com/settings/keys",
        "claude-sonnet-5-5",
    ),
    Provider(
        "pollinations",
        "Pollinations (без ключа)",
        "https://text.pollinations.ai/openai",
        "POLLINATIONS_API_KEY",
        "https://pollinations.ai",
        "openai",
        needs_key=False,
    ),
    Provider(
        "ollama",
        "Ollama (локально, без ключа)",
        "http://127.0.0.1:11434/v1",
        "OLLAMA_API_KEY",
        "https://ollama.com/download",
        "qwen2.5-coder:7b",
        needs_key=False,
    ),
    Provider(
        "lmstudio",
        "LM Studio (локально, без ключа)",
        "http://127.0.0.1:1234/v1",
        "LMSTUDIO_API_KEY",
        "https://lmstudio.ai",
        "local-model",
        needs_key=False,
    ),
]

PROVIDERS: dict[str, Provider] = {p.name: p for p in _PROVIDERS}


def api_key(cfg: dict, name: str) -> str:
    entry = cfg.get("providers", {}).get(name, {})
    key = (entry.get("api_key") or "").strip()
    if key:
        return key
    p = PROVIDERS[name]
    return os.environ.get(p.env, "").strip()


def base_url(cfg: dict, name: str) -> str:
    entry = cfg.get("providers", {}).get(name, {})
    return (entry.get("base_url") or PROVIDERS[name].base_url).rstrip("/")


def model_name(cfg: dict, name: str) -> str:
    entry = cfg.get("providers", {}).get(name, {})
    return (cfg.get("model") or entry.get("model") or PROVIDERS[name].default_model).strip()
