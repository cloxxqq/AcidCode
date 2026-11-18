from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import usage
from .providers import PROVIDERS, api_key


@dataclass(frozen=True)
class RankedModel:
    provider: str
    model: str
    tier: str
    free: bool


# Порядок = рейтинг. Первые строки — лучшие, последние — запасной аэродром.
RANKED: tuple[RankedModel, ...] = (
    RankedModel("anthropic", "claude-opus-5-5", "top", False),
    RankedModel("openai", "gpt-5.6-luna", "top", False),
    RankedModel("anthropic", "claude-sonnet-5-5", "top", False),
    RankedModel("openai", "gpt-5.5-pro", "top", False),
    RankedModel("google", "gemini-3.8-flash", "top", True),
    RankedModel("google", "gemini-3.1-pro-preview", "top", True),
    RankedModel("deepseek", "deepseek-v4-pro", "top", False),
    RankedModel("openai", "gpt-5.4-mini", "top", False),
    RankedModel("google", "gemini-3.7-flash", "top", True),
    RankedModel("groq", "llama-3.3-70b-versatile", "top", True),
    RankedModel("deepseek", "deepseek-flash", "top", False),
    RankedModel("google", "gemini-3-flash-preview", "top", True),
    RankedModel("mistral", "mistral-small-latest", "mid", True),
    RankedModel("cerebras", "llama-3.3-70b", "mid", True),
    RankedModel("sambanova", "Meta-Llama-3.3-70B-Instruct", "mid", True),
    RankedModel("groq", "llama-3.1-8b-instant", "mid", True),
    RankedModel("nvidia", "meta/llama-3.3-70b-instruct", "mid", True),
    RankedModel("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free", "mid", True),
    RankedModel("github", "openai/gpt-4o-mini", "mid", True),
    RankedModel("fireworks", "accounts/fireworks/models/llama-v3p3-70b-instruct", "mid", False),
    RankedModel("pollinations", "openai", "bad", True),
    RankedModel("lmstudio", "local-model", "bad", True),
    RankedModel("ollama", "qwen2.5-coder:7b", "bad", True),
)

LOCAL_PROVIDERS = {"lmstudio", "ollama"}


def has_key(cfg: dict[str, Any], provider: str) -> bool:
    p = PROVIDERS.get(provider)
    if p is None:
        return False
    return bool(api_key(cfg, provider)) or not p.needs_key


def numbered(models: tuple[RankedModel, ...] | list[RankedModel] = RANKED) -> list[tuple[int, RankedModel]]:
    return list(enumerate(models, 1))


def pick_by_number(index: int) -> RankedModel | None:
    for i, rm in numbered():
        if i == index:
            return rm
    return None


def filtered(kind: str = "") -> list[RankedModel]:
    if not kind:
        return list(RANKED)
    kind = kind.lower()
    if kind in ("free", "paid"):
        want_free = kind == "free"
        return [rm for rm in RANKED if rm.free is want_free]
    if kind in ("top", "mid", "bad"):
        return [rm for rm in RANKED if rm.tier == kind]
    return list(RANKED)


def next_candidate(
    cfg: dict[str, Any],
    current_provider: str,
    current_model: str,
    budget: int,
    exclude: set[tuple[str, str]] | None = None,
) -> RankedModel | None:
    skipped = exclude or set()
    # берём лучшую доступную модель по рейтингу, текущую и локальные серверы пропускаем
    for rm in RANKED:
        if rm.provider == current_provider and rm.model == current_model:
            continue
        if (rm.provider, rm.model) in skipped:
            continue
        if rm.provider in LOCAL_PROVIDERS:
            continue
        if not has_key(cfg, rm.provider):
            continue
        if usage.used(rm.provider, rm.model) >= budget:
            continue
        return rm
    return None
