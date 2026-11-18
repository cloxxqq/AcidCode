from __future__ import annotations

import asyncio
import fnmatch
import glob as globlib
import os
import re
import sys
from pathlib import Path
from typing import Any

MAX_READ = 200_000
MAX_OUT = 20_000
MAX_MATCHES = 200

WORKDIR: Path = Path.cwd().resolve()

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__",
    "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache",
}

SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Прочитать текстовый файл. Опционально диапазон строк.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer", "minimum": 1},
                    "end": {"type": "integer", "minimum": 1},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Записать файл целиком. Создаёт родительские папки.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Заменить точную строку old на new. old должен встречаться ровно один раз.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string"},
                    "new": {"type": "string"},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Показать содержимое папки.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_search",
            "description": "Найти файлы по glob-маске, например **/*.py",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "Поиск регулярного выражения по файлам проекта.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "include": {"type": "string", "description": "маска файлов, напр. *.py"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Выполнить shell-команду в рабочей папке. Таймаут 120 с.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "minimum": 1, "maximum": 600},
                },
                "required": ["command"],
            },
        },
    },
]


def set_workdir(path: Path) -> None:
    global WORKDIR
    WORKDIR = path.resolve()


def _resolve(raw: str) -> Path:
    p = Path(raw)
    if not p.is_absolute():
        p = WORKDIR / p
    p = p.resolve()
    try:
        p.relative_to(WORKDIR)
    except ValueError as exc:
        raise ValueError(f"путь вне рабочей папки: {p}") from exc
    return p


def _trim(text: str, limit: int = MAX_OUT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n… обрезано, всего {len(text)} байт"


def read_file(path: str, start: int | None = None, end: int | None = None) -> str:
    p = _resolve(path)
    if not p.is_file():
        return f"нет файла: {p}"
    if p.stat().st_size > MAX_READ:
        return f"файл больше {MAX_READ} байт: {p}"
    text = p.read_text(encoding="utf-8", errors="replace")
    if start or end:
        lines = text.splitlines()
        a = max((start or 1) - 1, 0)
        b = end if end else len(lines)
        text = "\n".join(f"{i + a + 1}: {lines[i]}" for i in range(a, min(b, len(lines))))
    return _trim(text)


def write_file(path: str, content: str) -> str:
    p = _resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"записано {len(content)} символов → {p}"


def edit_file(path: str, old: str, new: str) -> str:
    p = _resolve(path)
    if not p.is_file():
        return f"нет файла: {p}"
    text = p.read_text(encoding="utf-8")
    hits = text.count(old)
    if hits == 0:
        return "old не найден — правка не применена"
    if hits > 1:
        return f"old встречается {hits} раз — уточни контекст, правка не применена"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"правка применена → {p}"


def list_dir(path: str) -> str:
    p = _resolve(path)
    if not p.is_dir():
        return f"нет папки: {p}"
    rows = []
    for child in sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        if child.name in SKIP_DIRS:
            continue
        tag = "d" if child.is_dir() else "f"
        try:
            size = child.stat().st_size if child.is_file() else 0
        except OSError:
            size = 0
        rows.append(f"{tag} {child.name}" + (f"  {size}b" if tag == "f" else ""))
    return _trim("\n".join(rows) or "(пусто)")


def glob_search(pattern: str) -> str:
    matches = globlib.glob(pattern, root_dir=WORKDIR, recursive=True)
    files = [m for m in matches if (WORKDIR / m).is_file()]
    files.sort()
    return _trim("\n".join(files[:1000]) or "(ничего не найдено)")


def grep_search(pattern: str, include: str | None = None) -> str:
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        return f"плохое выражение: {exc}"
    out: list[str] = []
    for root, dirs, files in os.walk(WORKDIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if include and not fnmatch.fnmatch(fname, include):
                continue
            fpath = Path(root) / fname
            try:
                if fpath.stat().st_size > MAX_READ:
                    continue
                text = fpath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    rel = fpath.relative_to(WORKDIR)
                    out.append(f"{rel}:{lineno}: {line.strip()[:200]}")
                    if len(out) >= MAX_MATCHES:
                        return _trim("\n".join(out) + "\n… лимит совпадений")
    return _trim("\n".join(out) or "(ничего не найдено)")


async def run_shell(command: str, timeout: int = 120) -> str:
    if sys.platform == "win32":
        argv = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
    else:
        argv = ["bash", "-lc", command]
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(WORKDIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        raw, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return f"таймаут {timeout} с — процесс убит"
    text = raw.decode("utf-8", errors="replace")
    return _trim(f"exit={proc.returncode}\n{text}" if text else f"exit={proc.returncode}")


async def execute(name: str, args: dict[str, Any]) -> str:
    try:
        if name == "read_file":
            return read_file(args["path"], args.get("start"), args.get("end"))
        if name == "write_file":
            return write_file(args["path"], args["content"])
        if name == "edit_file":
            return edit_file(args["path"], args["old"], args["new"])
        if name == "list_dir":
            return list_dir(args["path"])
        if name == "glob_search":
            return glob_search(args["pattern"])
        if name == "grep_search":
            return grep_search(args["pattern"], args.get("include"))
        if name == "run_shell":
            return await run_shell(args["command"], int(args.get("timeout") or 120))
        return f"неизвестный инструмент: {name}"
    except KeyError as exc:
        return f"нет аргумента {exc}"
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"
