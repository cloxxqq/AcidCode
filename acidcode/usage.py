from __future__ import annotations

import json
import time
from typing import Any

from .config import HOME, ensure_dirs

BUDGET_DEFAULT = 200_000
USAGE_PATH = HOME / "usage.json"


class BudgetExhausted(RuntimeError):
    def __init__(self, provider: str, model: str, spent: int, budget: int) -> None:
        super().__init__(f"бюджет модели исчерпан: {provider}/{model} — {spent}/{budget}")
        self.provider = provider
        self.model = model
        self.spent = spent
        self.budget = budget


def _key(provider: str, model: str) -> str:
    return f"{provider}/{model}"


def _empty() -> dict[str, Any]:
    return {"models": {}}


def load() -> dict[str, Any]:
    ensure_dirs()
    if not USAGE_PATH.is_file():
        return _empty()
    try:
        data = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty()
    if not isinstance(data, dict) or not isinstance(data.get("models"), dict):
        return _empty()
    return data


def save(data: dict[str, Any]) -> None:
    ensure_dirs()
    tmp = USAGE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(USAGE_PATH)


def used(provider: str, model: str) -> int:
    entry = load()["models"].get(_key(provider, model))
    if not isinstance(entry, dict):
        return 0
    try:
        return int(entry.get("tokens") or 0)
    except (TypeError, ValueError):
        return 0


def add(provider: str, model: str, tokens: int) -> int:
    if tokens <= 0:
        return used(provider, model)
    data = load()
    key = _key(provider, model)
    entry = data["models"].setdefault(key, {"tokens": 0, "requests": 0})
    entry["tokens"] = int(entry.get("tokens") or 0) + int(tokens)
    entry["requests"] = int(entry.get("requests") or 0) + 1
    entry["updated"] = int(time.time())
    save(data)
    return entry["tokens"]


def reset(prefix: str | None = None) -> int:
    data = load()
    if prefix is None:
        count = len(data["models"])
        data["models"] = {}
    else:
        keys = [k for k in data["models"] if k.startswith(prefix)]
        count = len(keys)
        for k in keys:
            data["models"].pop(k, None)
    save(data)
    return count


def estimate(messages: list[dict[str, Any]], completion: str) -> int:
    chars = 0
    for msg in messages:
        chars += len(str(msg.get("content") or ""))
        for call in msg.get("tool_calls") or []:
            fn = call.get("function") or {}
            chars += len(str(fn.get("name") or "")) + len(str(fn.get("arguments") or ""))
    chars += len(completion or "")
    # грубая оценка: ~4 символа на токен + служебные токены на сообщение
    return max(1, chars // 4 + 8 * len(messages))


def fmt(tokens: int) -> str:
    if tokens >= 100_000:
        return f"{tokens / 1000:.0f}k"
    if tokens >= 1000:
        return f"{tokens / 1000:.1f}k"
    return str(tokens)


def bar(spent: int, budget: int, width: int = 18) -> str:
    if budget <= 0:
        return "?" * width
    ratio = min(max(spent / budget, 0.0), 1.0)
    fill = int(round(ratio * width))
    return "█" * fill + "░" * (width - fill)
