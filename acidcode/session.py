from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import SESSIONS_DIR, ensure_dirs


def _clean(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip("-")
    return safe or "last"


def save(name: str, messages: list[dict[str, Any]], cfg: dict[str, Any]) -> Path:
    ensure_dirs()
    path = SESSIONS_DIR / f"{_clean(name)}.json"
    payload = {
        "provider": cfg.get("provider"),
        "model": cfg.get("model"),
        "messages": messages,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load(name: str) -> list[dict[str, Any]] | None:
    ensure_dirs()
    path = SESSIONS_DIR / f"{_clean(name)}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    messages = data.get("messages")
    return messages if isinstance(messages, list) else None


def listing() -> list[str]:
    ensure_dirs()
    return sorted(p.stem for p in SESSIONS_DIR.glob("*.json"))
