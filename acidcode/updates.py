from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from . import __version__


class UpdateError(RuntimeError):
    """Обновление невозможно: сеть, манифест, архив или хеш."""


def version_tuple(text: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in str(text).strip().lstrip("vV").split("."):
        digits = ""
        for char in chunk:
            if char.isdigit():
                digits += char
            else:
                break
        parts.append(int(digits or 0))
    return tuple(parts) or (0,)


def is_newer(remote: str, local: str = __version__) -> bool:
    left, right = version_tuple(remote), version_tuple(local)
    size = max(len(left), len(right))
    left += (0,) * (size - len(left))
    right += (0,) * (size - len(right))
    return left > right


def _is_url(source: str) -> bool:
    return source.lower().startswith(("http://", "https://"))


def manifest_ref(source: str) -> str:
    """Превращает папку/базовый URL в путь к latest.json."""
    source = source.strip()
    if _is_url(source):
        path = urlparse(source).path.lower()
        if path.endswith(".json"):
            return source
        return source.rstrip("/") + "/latest.json"
    path = Path(source).expanduser()
    if path.is_dir() or path.suffix == "":
        path = path / "latest.json"
    return str(path)


def _read_manifest(source: str, timeout: float = 20.0) -> dict[str, Any]:
    ref = manifest_ref(source)
    if _is_url(ref):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(ref)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise UpdateError(f"не смог прочитать манифест {ref}: {exc}") from None
    else:
        path = Path(ref)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise UpdateError(f"нет манифеста {path}: {exc}") from None
        except json.JSONDecodeError as exc:
            raise UpdateError(f"битый манифест {path}: {exc}") from None
    if not isinstance(data, dict) or not data.get("version"):
        raise UpdateError("в манифесте нет поля version")
    return data


def _package_ref(manifest: dict[str, Any], ref: str) -> str:
    file = manifest.get("file") or manifest.get("url") or manifest.get("package")
    if not file:
        raise UpdateError("в манифесте нет file или url")
    file = str(file).strip()
    if _is_url(file):
        return file
    if _is_url(ref):
        return urljoin(ref, file)
    path = Path(file).expanduser()
    if not path.is_absolute():
        path = Path(ref).parent / path
    return str(path)


def check(source: str) -> dict[str, Any]:
    """Читает манифест и сообщает, есть ли версия новее текущей."""
    ref = manifest_ref(source)
    manifest = _read_manifest(source)
    remote = str(manifest["version"])
    manifest["ref"] = ref
    manifest["current"] = __version__
    manifest["newer"] = is_newer(remote)
    manifest["package"] = _package_ref(manifest, ref)
    return manifest


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(ref: str, dest: Path, timeout: float = 120.0) -> Path:
    if _is_url(ref):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                with client.stream("GET", ref) as response:
                    response.raise_for_status()
                    with dest.open("wb") as handle:
                        for chunk in response.iter_bytes():
                            handle.write(chunk)
        except httpx.HTTPError as exc:
            raise UpdateError(f"скачивание упало: {exc}") from None
    else:
        try:
            shutil.copyfile(Path(ref), dest)
        except OSError as exc:
            raise UpdateError(f"не смог скопировать {ref}: {exc}") from None
    return dest


_PACKAGE = Path(__file__).resolve().parent


def apply_zip(zip_path: Path) -> int:
    """Раскладывает acidcode/*.py и *.tcss из архива поверх текущего пакета."""
    updated = 0
    if not zip_path.is_file():
        raise UpdateError(f"нет архива: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for name in archive.namelist():
                norm = name.replace("\\", "/")
                marker = norm.find("acidcode/")
                if marker < 0:
                    continue
                rel = norm[marker + len("acidcode/"):]
                if not rel or rel.endswith("/"):
                    continue
                parts = Path(rel).parts
                if any(part in ("", ".", "..") for part in parts):
                    raise UpdateError(f"опасный путь в архиве: {name}")
                if not parts[-1].endswith((".py", ".tcss")):
                    continue
                target = _PACKAGE.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with archive.open(name) as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                except OSError as exc:
                    raise UpdateError(f"не смог записать {target}: {exc}") from None
                updated += 1
    except (OSError, zipfile.BadZipFile) as exc:
        raise UpdateError(f"архив не читается: {exc}") from None
    if updated == 0:
        raise UpdateError("в архиве нет файлов acidcode/**/*.py")
    cache = _PACKAGE / "__pycache__"
    if cache.is_dir():
        shutil.rmtree(cache, ignore_errors=True)
    return updated


def install(source: str) -> dict[str, Any]:
    """Проверяет, скачивает и устанавливает обновление. Возвращает манифест."""
    manifest = check(source)
    if not manifest["newer"]:
        return manifest
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "acidcode-update.zip"
        _download(str(manifest["package"]), archive)
        expected = str(manifest.get("sha256") or "").strip().lower()
        if expected:
            actual = sha256_file(archive)
            if actual != expected:
                raise UpdateError(
                    f"sha256 не совпал: ждал {expected[:12]}…, получил {actual[:12]}…"
                )
        manifest["updated_files"] = apply_zip(archive)
    return manifest
