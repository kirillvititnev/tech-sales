"""Store and serve product photos. Magic bytes only — never trust the filename."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from apps.api.config import get_settings

MAX_IMAGE_BYTES = 2 * 1024 * 1024
PUBLIC_PREFIX = "/api/v1/catalog/media/"
_NAME_RE = re.compile(r"^[0-9a-f]{32}\.(jpg|png|webp)$")
_TYPES = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def image_dir() -> Path:
    path = Path(get_settings().product_image_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path.resolve()


def message_photo_eligible(publishable_count: int) -> bool:
    """Price-list screenshots must not become every SKU's photo."""
    return 1 <= publishable_count <= 3


def sniff_image(data: bytes) -> str | None:
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def public_media_url(name: str) -> str:
    return f"{PUBLIC_PREFIX}{name}"


def stored_name_from_url(url: str | None) -> str | None:
    if not url or not url.startswith(PUBLIC_PREFIX):
        return None
    name = url[len(PUBLIC_PREFIX) :]
    if not _NAME_RE.fullmatch(name):
        return None
    return name


def is_storefront_image_url(url: str | None) -> bool:
    return stored_name_from_url(url) is not None


def resolve_image_file(name: str) -> Path:
    if not _NAME_RE.fullmatch(name):
        raise ValueError("Некорректное имя файла")
    base = image_dir()
    path = (base / name).resolve()
    if path.parent != base:
        raise ValueError("Некорректное имя файла")
    return path


def media_type_for(name: str) -> str:
    ext = name.rsplit(".", 1)[-1]
    return _TYPES[ext]


def store_image(data: bytes) -> str:
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Слишком большой файл")
    ext = sniff_image(data)
    if not ext:
        raise ValueError("Нужен JPEG, PNG или WebP")
    name = f"{uuid.uuid4().hex}.{ext}"
    path = resolve_image_file(name)
    path.write_bytes(data)
    return public_media_url(name)


def delete_stored_image(url: str | None) -> None:
    name = stored_name_from_url(url)
    if not name:
        return
    try:
        resolve_image_file(name).unlink(missing_ok=True)
    except ValueError:
        return
