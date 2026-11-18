from __future__ import annotations

import asyncio
import difflib
import re
import sys
import time
from pathlib import Path
from typing import Any

from rich.markup import escape
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import BindingsMap
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Markdown, Static

from . import (
    __version__,
    agent,
    config,
    i18n,
    ranking,
    session,
    themes,
    tools,
    updates,
    usage,
)
from .providers import PROVIDERS
from .spinner import EarthSpinner


LOGO_FONT: dict[str, list[str]] = {
    "A": [" ███ ", "█   █", "█████", "█   █", "█   █"],
    "c": [" ███", "█   ", "█   ", "█   ", " ███"],
    "i": ["███", " █ ", " █ ", " █ ", "███"],
    "d": ["   ██", "    █", " ████", "█   █", " ████"],
    "C": [" ████", "█    ", "█    ", "█    ", " ████"],
    "o": [" ███ ", "█   █", "█   █", "█   █", " ███ "],
    "e": [" ███ ", "█   █", "█████", "█    ", " ███ "],
}


def _wordmark(text: str) -> list[str]:
    glyphs = [LOGO_FONT[char] for char in text]
    return [" ".join(glyph[row] for glyph in glyphs) for row in range(5)]


class SplashScreen(Screen):
    def compose(self) -> ComposeResult:
        p = getattr(self.app, "_palette", themes.PALETTES[themes.DEFAULT])
        logo = Text(justify="center")
        logo.append("</>\n\n", style=f"bold {p['accent']}")
        for line in _wordmark("AcidCode"):
            logo.append(line + "\n", style=f"bold {p['text']}")
        logo.append(f"\nv{__version__}\n", style=p["modtag"])
        logo.append("terminal coding bench", style=p["modtag"])
        yield Static(logo, id="splash-text")

    def on_mount(self) -> None:
        self.set_timer(1.8, self._dismiss)

    def on_key(self) -> None:
        self._dismiss()

    def _dismiss(self) -> None:
        if self.app.screen is self:
            self.app.pop_screen()


def _trim(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + " …"


def _short(obj: dict[str, Any], limit: int = 160) -> str:
    return _trim(", ".join(f"{k}={v!r}" for k, v in obj.items()), limit)


_IDENTITY_RX = re.compile(
    r"^\s*(какая\s+(ты\s+)?модель|что\s+ты\s+за\s+модель|какой\s+(ты\s+)?модель[юи]?|"
    r"кто\s+ты|what\s+model(\s+are\s+you)?|which\s+model|who\s+are\s+you)\s*[\?\!\.]*\s*$",
    re.IGNORECASE,
)


def _is_identity_question(text: str) -> bool:
    return bool(_IDENTITY_RX.match(text))


class AcidCode(App):
    CSS_PATH = "theme.tcss"
    TITLE = "AcidCode"

    def __init__(self) -> None:
        super().__init__()
        self.cfg = config.load()
        lang = self.cfg.get("lang")
        self.lang = lang if lang in i18n.LANGS else "ru"
        self.messages: list[dict[str, Any]] = []
        self.session_name = "last"
        tools.set_workdir(Path.cwd())
        for theme in themes.THEMES.values():
            self.register_theme(theme)
        theme_name = self.cfg.get("theme")
        self.theme = theme_name if theme_name in themes.THEMES else themes.DEFAULT
        self._palette = themes.PALETTES.get(self.theme, themes.PALETTES[themes.DEFAULT])
        self._last_tool: tuple[str, dict[str, Any]] | None = None
        self._sync_bindings()
        self._refresh_title()

    # ---------------------------------------------------------------- язык

    def _t(self, key: str, **kwargs: Any) -> str:
        return i18n.t(self.lang, key, **kwargs)

    def _sync_bindings(self) -> None:
        # пересобираем карту, чтобы подписи внизу шли на выбранном языке
        self._bindings = BindingsMap()
        for key, action, label in (
            ("ctrl+c", "quit", self._t("key.quit")),
            ("ctrl+n", "new_session", self._t("key.new")),
            ("ctrl+s", "save_session", self._t("key.save")),
            ("f1", "show_help", self._t("key.help")),
        ):
            self._bindings.bind(key, action, label, priority=action == "quit")
        if getattr(self, "_is_mounted", False):
            self.refresh_bindings()

    def _set_lang(self, lang: str) -> None:
        self.lang = lang
        self.cfg["lang"] = lang
        config.save(self.cfg)
        prompt = self.query_one("#prompt", Input)
        prompt.placeholder = self._t("prompt")
        self._show_workspace()
        self._sync_bindings()

    def _set_theme(self, name: str) -> None:
        self.theme = name
        self._palette = themes.PALETTES.get(name, themes.PALETTES[themes.DEFAULT])
        self.cfg["theme"] = name
        config.save(self.cfg)
        self._show_workspace()

    # ------------------------------------------------------------ верхняя UI

    def _current_model(self) -> tuple[str, str, int, int]:
        name = self.cfg.get("provider") or "openrouter"
        provider = PROVIDERS.get(name)
        model = self.cfg.get("model") or (provider.default_model if provider else "?")
        budget = int(self.cfg.get("model_budget") or usage.BUDGET_DEFAULT)
        return name, model, usage.used(name, model), budget

    def _refresh_title(self) -> None:
        name, model, spent, budget = self._current_model()
        self.sub_title = f"{name} · {model} · {usage.fmt(spent)}/{usage.fmt(budget)}"
        self._refresh_meta()

    def _refresh_meta(self) -> None:
        try:
            meta = self.query_one("#prompt-meta", Static)
        except Exception:
            return
        name, model, spent, budget = self._current_model()
        short = model if len(model) <= 28 else model[:27] + "…"
        p = self._palette
        text = Text()
        text.append(short, style=p["dim"])
        text.append("  |  ", style=p["border"])
        text.append(f"{usage.fmt(spent)} {self._t('ui.tokens')}", style=p["dim"])
        text.append("  |  ", style=p["border"])
        text.append(f"{usage.fmt(budget)} {self._t('ui.limit')}", style=p["modtag"])
        meta.update(text)

    def _git_branch(self) -> str:
        folder = tools.WORKDIR
        for parent in (folder, *folder.parents):
            head = parent / ".git" / "HEAD"
            if head.is_file():
                try:
                    raw = head.read_text(encoding="utf-8").strip()
                except OSError:
                    break
                if raw.startswith("ref: refs/heads/"):
                    return raw.rsplit("/", 1)[-1]
                return raw[:8]
            if (parent / ".git").is_dir():
                return "repo"
            if parent == parent.parent:
                break
        return "—"

    def compose(self) -> ComposeResult:
        with Horizontal(id="topbar"):
            yield Static(
                Text("</>", style=f"bold {self._palette['accent']}"),
                id="brand-mark",
            )
            yield Static("AcidCode", id="brand-name")
            yield Static(f"v{__version__}", id="brand-version")
            yield Static("●", id="brand-dot")
            yield Static("", id="topbar-spacer")
            yield Static(f"⎇ git: {escape(self._git_branch())}", id="branch")
        with Horizontal(id="workspace"):
            with Vertical(id="code-panel"):
                yield VerticalScroll(Static("", id="code"), id="code-scroll")
            with Vertical(id="ai-panel"):
                yield VerticalScroll(id="chat")
        with Horizontal(id="bottombar"):
            with Horizontal(id="promptbox"):
                yield Static("›", id="prompt-glyph")
                yield Input(placeholder=self._t("prompt"), id="prompt")
            yield Static("", id="prompt-meta")

    async def on_mount(self) -> None:
        self.query_one("#code-panel").border_title = "workspace"
        self.query_one("#ai-panel").border_title = "AI PROMPT"
        self._show_workspace()
        self._refresh_meta()
        await self._welcome()
        self.push_screen(SplashScreen())
        self.set_timer(2.2, self._focus_prompt)
        self._check_updates()

    async def _welcome(self) -> None:
        p = self._palette
        text = Text()
        text.append("› ", style=f"bold {p['accent']}")
        text.append(self._t("ui.ready"), style=f"bold {p['text']}")
        text.append("\n")
        text.append(self._t("ui.hint"), style=p["dim"])
        await self._append(Static(text, classes="block welcome"))

    @work(exclusive=True, group="update")
    async def _check_updates(self) -> None:
        if self.cfg.get("update_auto", True):
            # автообновление уже отработало до запуска TUI
            return
        source = str(self.cfg.get("update_url") or "")
        if not source or not self.cfg.get("update_check", True):
            return
        try:
            info = await asyncio.to_thread(updates.check, source)
        except updates.UpdateError:
            return
        if not info.get("newer"):
            return
        if self.cfg.get("update_auto"):
            try:
                info = await asyncio.to_thread(updates.install, source)
            except updates.UpdateError as exc:
                await self._append(
                    Static(
                        escape(self._t("update.fail", error=str(exc))),
                        classes="block error",
                    )
                )
                return
            await self._append(
                Static(
                    escape(
                        self._t(
                            "update.done",
                            version=info.get("version", "?"),
                            count=info.get("updated_files", 0),
                        )
                    ),
                    classes="block note",
                )
            )
        else:
            await self._append(
                Static(
                    escape(
                        self._t(
                            "update.ready",
                            version=info.get("version", "?"),
                            current=info.get("current", "?"),
                        )
                    ),
                    classes="block note",
                )
            )

    def _focus_prompt(self) -> None:
        self.query_one("#prompt", Input).focus()

    def _stop_spinners(self) -> None:
        for widget in self.query(EarthSpinner):
            widget.stop()

    def _apply_model(self, provider: str, model: str) -> None:
        self.cfg["provider"] = provider
        self.cfg["model"] = model
        config.save(self.cfg)
        self._refresh_title()

    async def _append(self, widget) -> Any:
        chat = self.query_one("#chat", VerticalScroll)
        await chat.mount(widget)
        chat.scroll_end(animate=False)
        return widget

    def _scroll_end(self) -> None:
        self.query_one("#chat", VerticalScroll).scroll_end(animate=False)

    # ----------------------------------------------------------- code panel

    def _rel(self, raw: str) -> str:
        path = Path(raw)
        if not path.is_absolute():
            path = tools.WORKDIR / path
        try:
            return path.resolve().relative_to(tools.WORKDIR).as_posix()
        except (OSError, ValueError):
            return str(raw)

    def _safe_read(self, raw: str) -> tuple[str, str] | None:
        if not raw:
            return None
        path = Path(raw)
        if not path.is_absolute():
            path = tools.WORKDIR / path
        try:
            path = path.resolve()
            path.relative_to(tools.WORKDIR)
            if not path.is_file() or path.stat().st_size > 512_000:
                return None
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            return None
        return path.relative_to(tools.WORKDIR).as_posix(), text

    def _set_code(self, title: str, text: Text) -> None:
        self.query_one("#code-panel").border_title = title
        self.query_one("#code", Static).update(text)
        self.query_one("#code-scroll", VerticalScroll).scroll_home(animate=False)

    def _show_workspace(self) -> None:
        p = self._palette
        name, model, spent, budget = self._current_model()
        text = Text()
        text.append("workspace\n", style=f"bold {p['accent']}")
        text.append(f"{tools.WORKDIR}\n\n", style=p["dim"])
        text.append("AcidCode ", style=f"bold {p['text']}")
        text.append(f"v{__version__}\n", style=p["modtag"])
        text.append(f"{self._t('banner.provider')}  ", style=p["dim"])
        text.append(f"{name}\n", style=p["text"])
        text.append(f"{self._t('banner.model')}     ", style=p["dim"])
        text.append(f"{model}\n", style=p["text"])
        text.append(f"{self._t('banner.budget')}    ", style=p["dim"])
        text.append(f"{usage.fmt(spent)}/{usage.fmt(budget)}\n", style=p["text"])
        text.append(f"\n{self._t('ui.files')}\n", style=f"bold {p['accent2']}")

        shown = 0
        try:
            children = sorted(
                Path.cwd().iterdir(), key=lambda item: (item.is_file(), item.name.lower())
            )
        except OSError:
            children = []
        for child in children:
            if child.name.startswith(".") or child.name in {
                "__pycache__", ".venv", "node_modules", "dist", "build"
            }:
                continue
            if shown >= 18:
                text.append("  …\n", style=p["modtag"])
                break
            mark = "▸" if child.is_dir() else "·"
            text.append(f"  {mark} {child.name}", style=p["code"])
            if child.is_file():
                try:
                    text.append(f"  {child.stat().st_size}b", style=p["modtag"])
                except OSError:
                    pass
            text.append("\n")
            shown += 1

        text.append("\n")
        text.append(self._t("banner.hint") + "\n", style=p["tool"])
        text.append(self._t("banner.rating"), style=p["tool_out"])
        self._set_code("workspace", text)

    def _show_missing(self, raw: str) -> None:
        p = self._palette
        text = Text()
        text.append(self._t("ui.preview_missing") + "\n", style=p["error_text"])
        text.append(str(raw), style=p["dim"])
        self._set_code("preview", text)

    def _show_file(self, raw: str, prefix: str = "") -> None:
        found = self._safe_read(raw)
        if found is None:
            self._show_missing(raw)
            return
        rel, content = found
        p = self._palette
        lines = content.splitlines()
        limit = 320
        text = Text()
        text.append(f"{prefix}{rel}\n", style=f"bold {p['accent']}")
        text.append("─" * min(72, max(24, len(rel) + 8)) + "\n", style=p["border"])
        if not lines:
            text.append("(empty)\n", style=p["dim"])
        for number, line in enumerate(lines[:limit], 1):
            text.append(f"{number:>4} ", style=p["modtag"])
            text.append(line + "\n", style=p["code"])
        if len(lines) > limit:
            text.append(
                "\n" + self._t("ui.truncated", count=len(lines) - limit) + "\n",
                style=p["modtag"],
            )
        self._set_code(rel, text)

    def _show_edit_diff(
        self, raw: str, old: str, new: str, verb: str = "diff"
    ) -> None:
        rel = self._rel(raw)
        found = self._safe_read(raw)
        base = found[1] if found is not None else ""
        if base and old and old in base:
            updated = base.replace(old, new, 1)
            diff_lines = list(
                difflib.unified_diff(
                    base.splitlines(),
                    updated.splitlines(),
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                    lineterm="",
                    n=3,
                )
            )
        else:
            diff_lines = list(
                difflib.unified_diff(
                    old.splitlines(),
                    new.splitlines(),
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                    lineterm="",
                    n=2,
                )
            )
        p = self._palette
        text = Text()
        text.append(f"{verb} & {rel}\n", style=f"bold {p['accent']}")
        text.append("─" * min(72, max(24, len(rel) + 8)) + "\n", style=p["border"])
        if not diff_lines:
            text.append("(no changes)\n", style=p["dim"])
        for line in diff_lines[:420]:
            if line.startswith(("+++", "---")):
                style = p["modtag"]
            elif line.startswith("@@"):
                style = f"bold {p['accent2']}"
            elif line.startswith("+"):
                style = f"{p['accent']} on {p['diff_add']}"
            elif line.startswith("-"):
                style = f"{p['error_text']} on {p['diff_del']}"
            else:
                style = p["dim"]
            text.append(line + "\n", style=style)
        if len(diff_lines) > 420:
            text.append(
                "\n" + self._t("ui.truncated", count=len(diff_lines) - 420) + "\n",
                style=p["modtag"],
            )
        self._set_code(f"{verb} & {rel}", text)

    def _show_tool_output(
        self, name: str, args: dict[str, Any], output: str
    ) -> None:
        if name not in ("run_shell", "list_dir", "glob_search", "grep_search"):
            return
        p = self._palette
        body = _trim(output, 6000)
        text = Text()
        if name == "run_shell":
            title = "shell"
            text.append(f"$ {args.get('command', '')}\n\n", style=f"bold {p['accent']}")
        elif name == "list_dir":
            title = f"dir & {args.get('path', '.')}"
        elif name == "glob_search":
            title = f"glob & {args.get('pattern', '')}"
        else:
            title = f"grep & {args.get('pattern', '')}"
        text.append(body or "(no output)", style=p["code"])
        self._set_code(title, text)

    def _preview_tool(self, name: str, args: dict[str, Any]) -> None:
        try:
            if name == "read_file":
                self._show_file(str(args.get("path") or ""), "read & ")
            elif name == "write_file":
                found = self._safe_read(str(args.get("path") or ""))
                base = found[1] if found is not None else ""
                self._show_edit_diff(
                    str(args.get("path") or ""), base, str(args.get("content") or ""), "write"
                )
            elif name == "edit_file":
                self._show_edit_diff(
                    str(args.get("path") or ""),
                    str(args.get("old") or ""),
                    str(args.get("new") or ""),
                )
            elif name == "run_shell":
                p = self._palette
                text = Text()
                text.append(f"$ {args.get('command', '')}\n\n", style=f"bold {p['accent']}")
                text.append(self._t("ui.shell_run"), style=p["dim"])
                self._set_code("shell", text)
            elif name == "list_dir":
                p = self._palette
                text = Text()
                text.append(f"dir & {args.get('path', '.')}\n\n", style=f"bold {p['accent']}")
                text.append(self._t("ui.search_run"), style=p["dim"])
                self._set_code("dir", text)
            elif name in ("glob_search", "grep_search"):
                p = self._palette
                pattern = args.get("pattern", "")
                text = Text()
                text.append(f"{name} & {pattern}\n\n", style=f"bold {p['accent']}")
                text.append(self._t("ui.search_run"), style=p["dim"])
                self._set_code(name, text)
        except Exception:
            # предпросмотр не должен ломать ход модели
            pass

    # ---------------------------------------------------------------- ввод

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        inp = self.query_one("#prompt", Input)
        inp.value = ""
        if text.startswith("/"):
            await self._handle_command(text)
            return
        if _is_identity_question(text):
            name = self.cfg.get("provider") or "openrouter"
            provider = PROVIDERS.get(name)
            model = self.cfg.get("model") or (provider.default_model if provider else "?")
            await self._append(
                Static(
                    escape(self._t("identity", model=model, provider=name)),
                    classes="block note",
                )
            )
            return
        await self._append(Static(f"› {escape(text)}", classes="block user"))
        self.messages.append({"role": "user", "content": text})
        self._run_turn()

    # ----------------------------------------------------------------- ход

    @work(exclusive=True, group="turn")
    async def _run_turn(self) -> None:
        inp = self.query_one("#prompt", Input)
        inp.disabled = True
        self._stop_spinners()

        tag = await self._append(Static("", classes="block modtag"))

        def refresh_tag() -> None:
            name = self.cfg.get("provider") or "openrouter"
            provider = PROVIDERS.get(name)
            model = self.cfg.get("model") or (provider.default_model if provider else "?")
            tag.update(escape(self._t("tag", provider=name, model=model)))

        refresh_tag()
        think = await self._append(Static("", classes="block think"))
        think.display = False
        box = await self._append(Markdown(""))
        earth = await self._append(EarthSpinner())
        earth.display = False

        buf = ""
        rbuf = ""
        shown_at = {"t": 0.0}
        hide_timer = {"h": None}

        def hide_now() -> None:
            hide_timer["h"] = None
            earth.stop()

        def show_earth() -> None:
            timer = hide_timer["h"]
            if timer is not None:
                timer.stop()
                hide_timer["h"] = None
            earth.start()
            shown_at["t"] = time.monotonic()

        def hide_earth(immediate: bool = False) -> None:
            timer = hide_timer["h"]
            if timer is not None:
                timer.stop()
                hide_timer["h"] = None
            if not earth.display:
                return
            delay = 0.0 if immediate else max(0.0, 0.35 - (time.monotonic() - shown_at["t"]))
            if delay <= 0:
                earth.stop()
            else:
                hide_timer["h"] = self.set_timer(delay, hide_now)

        async def on_round() -> None:
            refresh_tag()
            show_earth()

        def on_reasoning(chunk: str) -> None:
            # рассуждения не гасят планету: ответ ещё не пошёл
            nonlocal rbuf
            rbuf += chunk
            think.display = True
            think.update(escape(rbuf))
            self._scroll_end()

        def on_text(chunk: str) -> None:
            nonlocal buf
            hide_earth()
            buf += chunk
            box.update(buf)
            self._scroll_end()

        async def on_tool(name: str, args: dict[str, Any]) -> None:
            hide_earth(immediate=True)
            self._last_tool = (name, args)
            self._preview_tool(name, args)
            await self._append(
                Static(f"⚙ {escape(name)} {escape(_short(args))}", classes="block tool")
            )

        async def on_result(name: str, output: str) -> None:
            if self._last_tool is not None:
                self._show_tool_output(*self._last_tool, output)
            await self._append(
                Static(escape(_trim(output, 1500)), classes="block tool output")
            )

        def reset_output() -> None:
            # неудачная попытка не должна оставлять обрывки в чате
            nonlocal buf, rbuf
            buf = ""
            rbuf = ""
            box.update("")
            think.update("")
            think.display = False
            hide_earth(immediate=True)

        attempts = 0
        skipped: set[tuple[str, str]] = set()
        origin_provider = self.cfg.get("provider") or "openrouter"
        origin_model = self.cfg.get("model") or (
            PROVIDERS[origin_provider].default_model if origin_provider in PROVIDERS else ""
        )
        while True:
            attempts += 1
            try:
                await agent.run_turn(
                    self.cfg,
                    self.messages,
                    on_text=on_text,
                    on_tool=on_tool,
                    on_result=on_result,
                    on_reasoning=on_reasoning,
                    on_round=on_round,
                )
                break
            except usage.BudgetExhausted as exc:
                skipped.add((exc.provider, exc.model))
                nxt = ranking.next_candidate(
                    self.cfg, exc.provider, exc.model, exc.budget, skipped
                )
                if nxt is None or attempts > len(ranking.RANKED):
                    await self._append(
                        Static(
                            escape(
                                self._t(
                                    "turn.budget_none",
                                    provider=exc.provider,
                                    model=exc.model,
                                    spent=usage.fmt(exc.spent),
                                    budget=usage.fmt(exc.budget),
                                )
                            ),
                            classes="block error",
                        )
                    )
                    break
                self._apply_model(nxt.provider, nxt.model)
                reset_output()
                await self._append(
                    Static(
                        escape(
                            self._t(
                                "turn.budget_switch",
                                provider=exc.provider,
                                model=exc.model,
                                spent=usage.fmt(exc.spent),
                                budget=usage.fmt(exc.budget),
                                next_provider=nxt.provider,
                                next_model=nxt.model,
                            )
                        ),
                        classes="block note",
                    )
                )
                continue
            except agent.ProviderError as exc:
                message = str(exc)
                low = message.lower()
                transient = (
                    "503" in message
                    or "429" in message
                    or "high demand" in low
                    or "overloaded" in low
                )
                billing = any(
                    word in low
                    for word in ("credit", "quota", "баланс", "счёт", "счет")
                )
                name = self.cfg.get("provider") or "openrouter"
                model = self.cfg.get("model") or ""
                budget = int(self.cfg.get("model_budget") or usage.BUDGET_DEFAULT)
                skipped.add((name, model))
                if billing and attempts <= 2 and name != "pollinations":
                    self._apply_model("pollinations", "openai")
                    reset_output()
                    await self._append(
                        Static(
                            escape(
                                self._t(
                                    "turn.billing", provider=name, model=model
                                )
                            ),
                            classes="block note",
                        )
                    )
                    continue
                nxt = ranking.next_candidate(self.cfg, name, model, budget, skipped)
                if transient and nxt is not None and attempts <= 3:
                    self._apply_model(nxt.provider, nxt.model)
                    reset_output()
                    await self._append(
                        Static(
                            escape(
                                self._t(
                                    "turn.overloaded",
                                    provider=name,
                                    model=model,
                                    next_provider=nxt.provider,
                                    next_model=nxt.model,
                                )
                            ),
                            classes="block note",
                        )
                    )
                    continue
                if transient:
                    current = (
                        self.cfg.get("provider") or "openrouter",
                        self.cfg.get("model") or "",
                    )
                    if current != (origin_provider, origin_model):
                        self._apply_model(origin_provider, origin_model)
                        await self._append(
                            Static(
                                escape(
                                    self._t(
                                        "turn.restore",
                                        provider=origin_provider,
                                        model=origin_model,
                                    )
                                ),
                                classes="block note",
                            )
                        )
                await self._append(Static(f"✖ {escape(message)}", classes="block error"))
                break
            except Exception as exc:  # noqa: BLE001 — UI не должен падать от ответа бэкенда
                await self._append(
                    Static(
                        f"✖ {escape(type(exc).__name__)}: {escape(str(exc))}",
                        classes="block error",
                    )
                )
                break
            finally:
                hide_earth()

        inp.disabled = False
        inp.focus()
        self._refresh_title()
        session.save(self.session_name, self.messages, self.cfg)

    # -------------------------------------------------------------- экраны

    def _ranked_view(self, kind: str = "") -> str:
        kind = (kind or "").strip().lower()
        budget = int(self.cfg.get("model_budget") or usage.BUDGET_DEFAULT)
        current_provider = self.cfg.get("provider") or "openrouter"
        current_model = self.cfg.get("model") or (
            PROVIDERS[current_provider].default_model
            if current_provider in PROVIDERS
            else ""
        )
        rows = [self._t("models.title", budget=usage.fmt(budget)), ""]
        last_tier = ""
        for index, rm in ranking.numbered():
            if kind in ("free", "paid"):
                if rm.free is not (kind == "free"):
                    continue
            elif kind in ("top", "mid", "bad"):
                if rm.tier != kind:
                    continue
            if rm.tier != last_tier:
                rows.append(self._t(f"tier.{rm.tier}"))
                last_tier = rm.tier
            spent = usage.used(rm.provider, rm.model)
            key_mark = "+" if ranking.has_key(self.cfg, rm.provider) else "—"
            cur_mark = (
                "→"
                if (rm.provider, rm.model) == (current_provider, current_model)
                else " "
            )
            price = self._t("price.free" if rm.free else "price.paid")
            rows.append(
                f"{cur_mark} {index:>2}. {rm.provider}/{rm.model}  [{price}]"
            )
            rows.append(
                f"      {usage.bar(spent, budget)} {usage.fmt(spent)}/{usage.fmt(budget)}"
                f"  {self._t('models.key')}:{key_mark}"
            )
        rows.append("")
        rows.append(self._t("models.hint"))
        return "\n".join(rows)

    def _usage_view(self) -> str:
        budget = int(self.cfg.get("model_budget") or usage.BUDGET_DEFAULT)
        data = usage.load()["models"]
        if not data:
            return self._t("usage.empty", budget=usage.fmt(budget))
        rows = [self._t("usage.title", budget=usage.fmt(budget)), ""]
        for key, entry in sorted(data.items()):
            spent = int(entry.get("tokens") or 0)
            requests = int(entry.get("requests") or 0)
            rows.append(
                f"{key}\n  {usage.bar(spent, budget)} {usage.fmt(spent)}/{usage.fmt(budget)}"
                f" · {self._t('usage.requests')} {requests}"
            )
        rows.append("")
        rows.append(self._t("usage.hint"))
        return "\n".join(rows)

    # ------------------------------------------------------------- команды

    async def _handle_command(self, text: str) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/help", "/?"):
            await self._append(
                Static(escape(i18n.help_text(self.lang)), classes="block note")
            )
        elif cmd == "/exit":
            self.exit()
        elif cmd == "/clear":
            chat = self.query_one("#chat", VerticalScroll)
            await chat.remove_children()
            await self._append(Static(self._t("cmd.cleared"), classes="block note"))
        elif cmd == "/new":
            self.messages.clear()
            self.session_name = "last"
            await self._append(Static(self._t("cmd.new"), classes="block note"))
        elif cmd == "/lang":
            if not arg:
                await self._append(
                    Static(self._t("lang.current", lang=self.lang), classes="block note")
                )
            elif arg.lower() not in i18n.LANGS:
                await self._append(
                    Static(self._t("lang.bad"), classes="block error")
                )
            else:
                self._set_lang(arg.lower())
                await self._append(
                    Static(
                        self._t("lang.done", lang=self.lang), classes="block note"
                    )
                )
        elif cmd == "/theme":
            if not arg:
                names = " · ".join(
                    f"{name} ({self._t('theme.label.' + name)})"
                    + (" *" if name == self.theme else "")
                    for name in themes.THEMES
                )
                await self._append(
                    Static(
                        escape(
                            f"{self._t('theme.current', name=self.theme)}\n{names}"
                        ),
                        classes="block note",
                    )
                )
            elif arg.lower() not in themes.THEMES:
                await self._append(
                    Static(
                        escape(self._t("theme.bad", name=arg)),
                        classes="block error",
                    )
                )
            else:
                self._set_theme(arg.lower())
                await self._append(
                    Static(
                        escape(self._t("theme.done", name=arg.lower())),
                        classes="block note",
                    )
                )
        elif cmd == "/update":
            check_only = arg.lower() == "check"
            source = "" if check_only else arg
            explicit_source = bool(source)
            if not source:
                source = str(self.cfg.get("update_url") or "")
            if not source:
                await self._append(
                    Static(self._t("update.no_source"), classes="block note")
                )
                return
            await self._append(
                Static(self._t("update.checking"), classes="block note")
            )
            try:
                info = await asyncio.to_thread(
                    updates.check if check_only else updates.install, source
                )
            except updates.UpdateError as exc:
                await self._append(
                    Static(
                        escape(self._t("update.fail", error=str(exc))),
                        classes="block error",
                    )
                )
            else:
                if explicit_source:
                    self.cfg["update_url"] = source
                    config.save(self.cfg)
                    await self._append(
                        Static(
                            escape(self._t("update.source_saved", source=source)),
                            classes="block note",
                        )
                    )
                if not info.get("newer"):
                    await self._append(
                        Static(
                            self._t(
                                "update.none",
                                version=info.get("current", "?"),
                            ),
                            classes="block note",
                        )
                    )
                elif check_only:
                    await self._append(
                        Static(
                            escape(
                                self._t(
                                    "update.ready",
                                    version=info.get("version", "?"),
                                    current=info.get("current", "?"),
                                )
                            ),
                            classes="block note",
                        )
                    )
                else:
                    await self._append(
                        Static(
                            escape(
                                self._t(
                                    "update.done",
                                    version=info.get("version", "?"),
                                    count=info.get("updated_files", 0),
                                )
                            ),
                            classes="block note",
                        )
                    )
        elif cmd == "/status":
            name = self.cfg.get("provider") or "openrouter"
            provider = PROVIDERS.get(name)
            model = self.cfg.get("model") or (
                provider.default_model if provider else "?"
            )
            key = bool(self.cfg.get("providers", {}).get(name, {}).get("api_key"))
            thinking = (
                self.cfg.get("reasoning_effort", "high")
                if name == "deepseek"
                else self._t("status.na")
            )
            await self._append(
                Static(
                    escape(
                        f"{self._t('status.provider')}: {name}\n"
                        f"{self._t('status.model')}: {model}\n"
                        f"{self._t('status.budget')}: {usage.fmt(usage.used(name, model))}"
                        f"/{usage.fmt(int(self.cfg.get('model_budget') or usage.BUDGET_DEFAULT))}\n"
                        f"{self._t('status.key')}: "
                        f"{self._t('status.key_yes') if key else self._t('status.key_no')}\n"
                        f"{self._t('status.thinking')}: {thinking}\n"
                        f"{self._t('status.folder')}: {tools.WORKDIR}\n"
                        f"{self._t('status.messages')}: {len(self.messages)}\n"
                        f"{self._t('status.config')}: {config.CONFIG_PATH}"
                    ),
                    classes="block note",
                )
            )
        elif cmd == "/providers":
            rows = [self._t("providers.title")]
            for p in PROVIDERS.values():
                mark = "★" if p.name == (self.cfg.get("provider") or "") else " "
                rows.append(
                    f"{mark} {p.name:<12} {p.label}\n"
                    f"    {self._t('providers.docs')}: {p.docs}   "
                    f"{self._t('providers.env')}: {p.env}"
                )
            await self._append(Static(escape("\n".join(rows)), classes="block note"))
        elif cmd == "/provider":
            if not arg:
                await self._append(
                    Static(self._t("provider.need"), classes="block note")
                )
            elif arg not in PROVIDERS:
                await self._append(
                    Static(
                        escape(self._t("provider.unknown", name=arg)),
                        classes="block error",
                    )
                )
            else:
                self.cfg["provider"] = arg
                self.cfg["model"] = ""
                config.save(self.cfg)
                self._refresh_title()
                await self._append(
                    Static(
                        escape(self._t("provider.done", name=arg)),
                        classes="block note",
                    )
                )
        elif cmd == "/key":
            name = self.cfg.get("provider") or "openrouter"
            if not arg:
                await self._append(Static(self._t("key.need"), classes="block note"))
            else:
                config.provider_entry(self.cfg, name)["api_key"] = arg
                config.save(self.cfg)
                await self._append(
                    Static(
                        escape(
                            self._t("key.saved", provider=name, count=len(arg))
                        ),
                        classes="block note",
                    )
                )
        elif cmd == "/model":
            if not arg:
                name = self.cfg.get("provider") or "openrouter"
                provider = PROVIDERS.get(name)
                current = self.cfg.get("model") or self._t("model.default")
                default = provider.default_model if provider else "?"
                await self._append(
                    Static(
                        escape(
                            f"{self._t('model.current', model=current)}\n"
                            f"{self._t('model.default_line', model=default)}"
                        ),
                        classes="block note",
                    )
                )
            else:
                self.cfg["model"] = arg
                config.save(self.cfg)
                self._refresh_title()
                await self._append(
                    Static(
                        escape(self._t("model.done", model=arg)),
                        classes="block note",
                    )
                )
        elif cmd == "/models":
            if arg:
                kind = i18n.normalize_filter(arg)
                if not kind:
                    await self._append(
                        Static(self._t("models.bad_filter"), classes="block error")
                    )
                    return
            else:
                kind = ""
            await self._append(
                Static(escape(self._ranked_view(kind)), classes="block note")
            )
        elif cmd == "/switch":
            if not arg:
                await self._append(
                    Static(self._t("switch.need"), classes="block note")
                )
            elif arg.lower() == "next":
                name = self.cfg.get("provider") or "openrouter"
                model = self.cfg.get("model") or PROVIDERS[name].default_model
                budget = int(self.cfg.get("model_budget") or usage.BUDGET_DEFAULT)
                nxt = ranking.next_candidate(self.cfg, name, model, budget)
                if nxt is None:
                    await self._append(
                        Static(self._t("switch.none"), classes="block error")
                    )
                else:
                    self._apply_model(nxt.provider, nxt.model)
                    await self._append(
                        Static(
                            escape(
                                self._t(
                                    "switch.done",
                                    provider=nxt.provider,
                                    model=nxt.model,
                                )
                            ),
                            classes="block note",
                        )
                    )
            else:
                try:
                    index = int(arg)
                except ValueError:
                    await self._append(
                        Static(self._t("switch.bad_number"), classes="block error")
                    )
                    return
                rm = ranking.pick_by_number(index)
                if rm is None:
                    await self._append(
                        Static(self._t("switch.not_found"), classes="block error")
                    )
                elif not ranking.has_key(self.cfg, rm.provider):
                    await self._append(
                        Static(
                            escape(
                                self._t("switch.no_key", provider=rm.provider)
                            ),
                            classes="block error",
                        )
                    )
                else:
                    self._apply_model(rm.provider, rm.model)
                    await self._append(
                        Static(
                            escape(
                                self._t(
                                    "switch.done",
                                    provider=rm.provider,
                                    model=rm.model,
                                )
                            ),
                            classes="block note",
                        )
                    )
        elif cmd == "/usage":
            if arg.lower().startswith("reset"):
                target = arg[len("reset"):].strip()
                removed = usage.reset(None if target in ("", "all") else target)
                self._refresh_title()
                await self._append(
                    Static(
                        escape(self._t("usage.reset_done", count=removed)),
                        classes="block note",
                    )
                )
            else:
                await self._append(
                    Static(escape(self._usage_view()), classes="block note")
                )
        elif cmd == "/system":
            if not arg:
                await self._append(
                    Static(
                        escape(
                            self._t(
                                "system.current",
                                text=self.cfg.get("system", ""),
                            )
                        ),
                        classes="block note",
                    )
                )
            else:
                self.cfg["system"] = arg
                config.save(self.cfg)
                await self._append(
                    Static(self._t("system.done"), classes="block note")
                )
        elif cmd == "/reasoning":
            if not arg:
                await self._append(
                    Static(
                        escape(
                            f"{self._t('reasoning.current', level=self.cfg.get('reasoning_effort', 'high'))}\n"
                            f"{self._t('reasoning.options')}"
                        ),
                        classes="block note",
                    )
                )
            elif arg.lower() not in ("off", "low", "high", "max"):
                await self._append(
                    Static(self._t("reasoning.bad"), classes="block error")
                )
            else:
                self.cfg["reasoning_effort"] = arg.lower()
                config.save(self.cfg)
                await self._append(
                    Static(
                        self._t("reasoning.done", level=arg.lower()),
                        classes="block note",
                    )
                )
        elif cmd == "/save":
            name = arg or self.session_name
            path = session.save(name, self.messages, self.cfg)
            self.session_name = name
            await self._append(
                Static(
                    escape(self._t("save.done", path=str(path))),
                    classes="block note",
                )
            )
        elif cmd == "/load":
            if not arg:
                await self._append(Static(self._t("load.need"), classes="block note"))
                return
            messages = session.load(arg)
            if messages is None:
                await self._append(
                    Static(
                        escape(self._t("load.none", name=arg)),
                        classes="block error",
                    )
                )
                return
            self.messages = messages
            self.session_name = arg
            await self._append(
                Static(
                    escape(
                        self._t("load.done", count=len(messages), name=arg)
                    ),
                    classes="block note",
                )
            )
        elif cmd == "/sessions":
            names = session.listing()
            await self._append(
                Static(
                    escape("\n".join(names) or self._t("sessions.empty")),
                    classes="block note",
                )
            )
        else:
            await self._append(
                Static(
                    escape(self._t("cmd.unknown", cmd=cmd)),
                    classes="block error",
                )
            )

    def action_new_session(self) -> None:
        self.messages.clear()
        self.session_name = "last"
        self.notify(self._t("cmd.new"))

    def action_save_session(self) -> None:
        path = session.save(self.session_name, self.messages, self.cfg)
        self.notify(self._t("save.done", path=path.name))

    def action_show_help(self) -> None:
        self.call_later(
            self._append,
            Static(escape(i18n.help_text(self.lang)), classes="block note"),
        )


def main() -> int:
    if sys.version_info < (3, 13):
        print("нужен python 3.13+", file=sys.stderr)
        return 1
    AcidCode().run()
    return 0
