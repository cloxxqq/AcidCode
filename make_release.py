from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from acidcode import __version__

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "acidcode"
DIST = ROOT / "dist"

PORTABLE = (
    "pyproject.toml",
    "install.bat",
    "acidcode.cmd",
    "README.md",
    "CHANGELOG.md",
    "assets/acidcode-logo.svg",
)

SETUP = """AcidCode — установка у друга

1. Поставь Python 3.13:
   https://www.python.org/downloads/
   При установке отметь "Add python.exe to PATH".
   Подойдёт и Python 3.13 из Microsoft Store.

2. Распакуй этот архив, например в C:\\AcidCode.
   Внутри должны лежать acidcode\\, install.bat, acidcode.cmd.

3. Один раз запусти install.bat.
   Он создаст .venv и поставит зависимости.

4. Запусти acidcode.cmd.

5. Выбери провайдера и вставь ключ:
   /provider google
   /key <ключ>
   или без ключа:
   /provider pollinations
   /model openai

6. Автообновления.
   Один раз выполни в AcidCode:
   /update \\\\server\\share\\acidcode\\latest.json
   (или /update https://example.com/acidcode/latest.json)

   Путь сохранится в update_url, и при каждом запуске AcidCode
   будет сам проверять и ставить свежую версию.
   Перезапуск после обновления делает сам.

Язык: /lang ru или /lang en
Тема:  /theme acid | amber | ice | violet | mono
"""


def main() -> int:
    DIST.mkdir(exist_ok=True)
    archive = DIST / f"acidcode-{__version__}.zip"
    files = sorted(
        path
        for path in PACKAGE.rglob("*")
        if path.is_file()
        and path.suffix in (".py", ".tcss")
        and "__pycache__" not in path.parts
    )
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(ROOT).as_posix())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = {
        "version": __version__,
        "file": archive.name,
        "sha256": digest,
        "notes": f"AcidCode {__version__}",
    }
    (DIST / "latest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    friend = DIST / f"AcidCode-{__version__}-friend.zip"
    with zipfile.ZipFile(friend, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            zf.write(path, path.relative_to(ROOT).as_posix())
        for name in PORTABLE:
            path = ROOT / name
            if path.is_file():
                zf.write(path, name)
        zf.writestr("SETUP.txt", SETUP)

    print(f"версия: {__version__}")
    print(f"архив обновления: {archive}")
    print(f"набор для друга:  {friend}")
    print(f"файлов в пакете:  {len(files)}")
    print(f"sha256: {digest}")
    print(f"манифест: {DIST / 'latest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
