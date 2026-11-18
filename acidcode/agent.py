from __future__ import annotations

import inspect
import json
from typing import Any, Awaitable, Callable

import httpx

from . import config as cfgmod
from . import tools
from . import usage
from .providers import PROVIDERS, api_key, base_url, model_name

OnText = Callable[[str], None]
OnReasoning = Callable[[str], None]
OnTool = Callable[[str, dict[str, Any]], Awaitable[None]]
OnResult = Callable[[str, str], Awaitable[None]]
OnRound = Callable[[], Any]


class ProviderError(RuntimeError):
    pass


class _HttpFailure(Exception):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(body)
        self.status = status
        self.body = body


def _endpoint(cfg: dict[str, Any]) -> tuple[str, dict[str, str], str]:
    name = cfg.get("provider") or "openrouter"
    if name not in PROVIDERS:
        raise ProviderError(f"неизвестный провайдер: {name}")
    p = PROVIDERS[name]
    key = api_key(cfg, name)
    if p.needs_key and not key:
        raise ProviderError(
            f"нет ключа для {name}. Вставь: /key <ключ>  или задай {p.env}. "
            f"Ключ берётся здесь: {p.docs}"
        )
    model = model_name(cfg, name)
    if not model:
        raise ProviderError("не задана модель: /model <имя>")
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if name == "openrouter":
        headers["HTTP-Referer"] = "https://acidcode.local"
        headers["X-Title"] = "AcidCode"
    if name == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
        headers["x-api-key"] = key
    return f"{base_url(cfg, name)}/chat/completions", headers, model


def _reasoning_payload(cfg: dict[str, Any]) -> dict[str, Any]:
    if (cfg.get("provider") or "") != "deepseek":
        return {}
    effort = (cfg.get("reasoning_effort") or "high").lower()
    if effort in ("off", "none", "disabled"):
        return {}
    if effort not in ("low", "high", "max"):
        effort = "high"
    return {"reasoning_effort": effort, "thinking": {"type": "enabled"}}


async def _stream_once(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    on_text: OnText | None,
    on_reasoning: OnReasoning | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    parts: list[str] = []
    calls: dict[int, dict[str, str]] = {}
    timeout = httpx.Timeout(connect=20.0, read=None, write=60.0, pool=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", errors="replace")
                raise _HttpFailure(resp.status_code, body[:1200])
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if "error" in chunk and chunk["error"]:
                    raise ProviderError(str(chunk["error"])[:800])
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    think = delta.get("reasoning_content") or delta.get("reasoning")
                    if think:
                        if on_reasoning:
                            on_reasoning(think)
                    text = delta.get("content")
                    if text:
                        parts.append(text)
                        if on_text:
                            on_text(text)
                    for tc in delta.get("tool_calls") or []:
                        idx = int(tc.get("index") or 0)
                        slot = calls.setdefault(
                            idx, {"id": "", "name": "", "args": "", "extra": None}
                        )
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        extra = tc.get("extra_content")
                        if extra:
                            slot["extra"] = extra
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["name"] += fn["name"]
                        if fn.get("arguments"):
                            slot["args"] += fn["arguments"]
    tool_calls: list[dict[str, Any]] = []
    for idx, slot in sorted(calls.items()):
        if not slot["name"]:
            continue
        entry: dict[str, Any] = {
            "id": slot["id"] or f"call_{idx}",
            "type": "function",
            "function": {"name": slot["name"], "arguments": slot["args"] or "{}"},
        }
        # Gemini 3 требует вернуть thought_signature в следующем запросе
        if slot.get("extra"):
            entry["extra_content"] = slot["extra"]
        tool_calls.append(entry)
    return "".join(parts), tool_calls


def _friendly(status: int, body: str) -> str:
    low = body.lower()
    if (
        ("insufficient" in low and "balance" in low)
        or "no credits remaining" in low
        or "credit balance is too low" in low
        or "insufficient_quota" in low
        or "credit_balance_exhausted" in low
    ):
        return (
            "на счёте провайдера ноль. пополни баланс в личном кабинете "
            "или переключись на бесплатный бэкенд: /provider pollinations"
        )
    if status == 401:
        return "ключ не принят (401). проверь провайдера и ключ: /status, затем /key"
    if status == 404:
        return "модель или эндпоинт не найдены (404). список моделей: /models"
    if status == 429:
        return "лимит запросов (429). подожди или смени модель/провайдера"
    return f"{status}: {body[:800]}"


async def stream_chat(
    cfg: dict[str, Any],
    messages: list[dict[str, Any]],
    on_text: OnText | None = None,
    on_reasoning: OnReasoning | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    url, headers, model = _endpoint(cfg)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": float(cfg.get("temperature", 0.3)),
        "tools": tools.SCHEMAS,
        "tool_choice": "auto",
    }
    payload.update(_reasoning_payload(cfg))
    try:
        return await _stream_once(url, headers, payload, on_text, on_reasoning)
    except _HttpFailure as fail:
        if fail.status in (400, 404, 422):
            payload.pop("tools", None)
            payload.pop("tool_choice", None)
            try:
                return await _stream_once(url, headers, payload, on_text, on_reasoning)
            except _HttpFailure as fail2:
                raise ProviderError(_friendly(fail2.status, fail2.body)) from None
        raise ProviderError(_friendly(fail.status, fail.body)) from None
    except httpx.HTTPError as exc:
        raise ProviderError(f"сеть: {exc}") from None


async def run_turn(
    cfg: dict[str, Any],
    messages: list[dict[str, Any]],
    on_text: OnText | None = None,
    on_tool: OnTool | None = None,
    on_result: OnResult | None = None,
    on_reasoning: OnReasoning | None = None,
    on_round: OnRound | None = None,
) -> None:
    provider = cfg.get("provider") or "openrouter"
    model = model_name(cfg, provider)
    system = cfg.get("system") or cfgmod.DEFAULT_SYSTEM
    system = (
        f"{system}\n\n"
        f"Текущая конфигурация: провайдер {provider}, модель {model}. "
        f"Если спрашивают, какая ты модель — отвечай: AcidCode, модель {model} через провайдера {provider}. "
        f"Не называй себя ChatGPT, GPT-4, Claude или другой чужой моделью."
    )
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": system})
    else:
        messages[0]["content"] = system

    budget = int(cfg.get("model_budget") or usage.BUDGET_DEFAULT)

    steps = int(cfg.get("max_steps", 25))
    for _ in range(steps):
        spent = usage.used(provider, model)
        if spent >= budget:
            raise usage.BudgetExhausted(provider, model, spent, budget)
        if on_round:
            maybe = on_round()
            if inspect.isawaitable(maybe):
                await maybe
        text, calls = await stream_chat(cfg, messages, on_text, on_reasoning)
        usage.add(provider, model, usage.estimate(messages, text))
        assistant: dict[str, Any] = {"role": "assistant", "content": text or ""}
        if calls:
            assistant["tool_calls"] = calls
        messages.append(assistant)
        if not calls:
            return
        for call in calls:
            name = call["function"]["name"]
            raw = call["function"]["arguments"] or "{}"
            try:
                args = json.loads(raw)
                if not isinstance(args, dict):
                    raise ValueError("аргументы не объект")
            except (json.JSONDecodeError, ValueError):
                args = {}
            if on_tool:
                maybe = on_tool(name, args)
                if inspect.isawaitable(maybe):
                    await maybe
            output = await tools.execute(name, args)
            if on_result:
                maybe = on_result(name, output)
                if inspect.isawaitable(maybe):
                    await maybe
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": output[:20000],
                }
            )
    messages.append(
        {"role": "assistant", "content": f"[остановлено: достигнут лимит {steps} шагов]"}
    )


async def list_models(cfg: dict[str, Any]) -> list[str]:
    name = cfg.get("provider") or "openrouter"
    if name not in PROVIDERS:
        raise ProviderError(f"неизвестный провайдер: {name}")
    key = api_key(cfg, name)
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if name == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
        headers["x-api-key"] = key
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{base_url(cfg, name)}/models", headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise ProviderError(f"не удалось получить список моделей: {exc}") from None
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    ids = [str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")]
    return sorted(ids)
