from __future__ import annotations

import os
import platform
import sys

from . import __version__


def _auto_update() -> None:
    """Проверяет канал и ставит обновление до запуска TUI."""
    if os.environ.get("ACIDCODE_AUTOUPDATE_DONE") == "1":
        return
    from . import config, updates

    config_data = config.load()
    if not config_data.get("update_auto", True) or not config_data.get(
        "update_check", True
    ):
        return
    source = str(config_data.get("update_url") or "")
    if not source:
        return
    try:
        info = updates.check(source)
    except updates.UpdateError:
        return
    if not info.get("newer"):
        return
    try:
        result = updates.install(source)
    except updates.UpdateError as exc:
        print(f"AcidCode: обновление не удалось: {exc}")
        return
    print(f"AcidCode: обновлено до {result.get('version', '?')}, перезапускаю…")
    os.environ["ACIDCODE_AUTOUPDATE_DONE"] = "1"
    try:
        os.execv(sys.executable, [sys.executable, "-m", "acidcode", *sys.argv[1:]])
    except OSError as exc:
        print(f"AcidCode: обновление установлено, перезапусти вручную ({exc})")


def _update(args: list[str]) -> int:
    from . import config, updates

    check_only = any(arg in ("check", "--check", "-c") for arg in args)
    sources = [arg for arg in args if arg not in ("check", "--check", "-c")]
    source = sources[0] if sources else str(config.load().get("update_url") or "")
    if not source:
        print("нет источника обновлений: acidcode update <папка|URL>")
        print('или добавь "update_url" в ~/.acidcode/config.json')
        return 2
    try:
        manifest = updates.check(source) if check_only else updates.install(source)
    except updates.UpdateError as exc:
        print(f"обновление не вышло: {exc}")
        return 1
    if not manifest.get("newer"):
        print(f"уже последняя версия: {manifest.get('current', __version__)}")
        return 0
    if check_only:
        print(f"доступна версия {manifest['version']} (сейчас {manifest['current']})")
        print(f"установить: acidcode update {source}")
        return 0
    print(
        f"обновлено до {manifest['version']}: файлов {manifest.get('updated_files', 0)}. "
        f"перезапусти AcidCode."
    )
    return 0


def main() -> int:
    args = [arg for arg in sys.argv[1:] if arg]
    if args and args[0] in ("-V", "--version", "version"):
        print(f"AcidCode {__version__} / python {platform.python_version()}")
        return 0
    if args and args[0].lstrip("/").lower() == "update":
        return _update(args[1:])
    if args and args[0] in ("--update", "-u"):
        return _update(args[1:])

    _auto_update()

    from .app import main as run_tui

    return run_tui()


if __name__ == "__main__":
    sys.exit(main())
