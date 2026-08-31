from pathlib import Path

import pytest

from apps.api.services.product_images import (
    MAX_IMAGE_BYTES,
    message_photo_eligible,
    resolve_image_file,
    sniff_image,
    store_image,
    stored_name_from_url,
)

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
_WEBP = b"RIFF" + b"\x10\x00\x00\x00" + b"WEBP" + b"\x00" * 12
_SVG = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"
_HTML = b"<!DOCTYPE html><html><script>alert(1)</script></html>"


def test_message_photo_eligible_skips_price_lists() -> None:
    assert not message_photo_eligible(0)
    assert message_photo_eligible(1)
    assert message_photo_eligible(3)
    assert not message_photo_eligible(4)


def test_sniff_accepts_jpeg_png_webp() -> None:
    assert sniff_image(_JPEG) == "jpg"
    assert sniff_image(_PNG) == "png"
    assert sniff_image(_WEBP) == "webp"


def test_sniff_rejects_svg_html_and_short() -> None:
    assert sniff_image(_SVG) is None
    assert sniff_image(_HTML) is None
    assert sniff_image(b"\xff\xd8") is None


def test_stored_name_from_url_rejects_traversal_and_foreign() -> None:
    assert stored_name_from_url("https://evil.example/x.jpg") is None
    assert stored_name_from_url("/api/v1/catalog/media/../secrets.jpg") is None
    assert stored_name_from_url("/api/v1/catalog/media/not-a-uuid.jpg") is None
    good = "/api/v1/catalog/media/" + "a" * 32 + ".jpg"
    assert stored_name_from_url(good) == "a" * 32 + ".jpg"


def test_resolve_image_file_rejects_dotdot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PRODUCT_IMAGE_DIR", str(tmp_path))
    from apps.api.config import get_settings

    get_settings.cache_clear()
    try:
        with pytest.raises(ValueError):
            resolve_image_file("../passwd.jpg")
        with pytest.raises(ValueError):
            resolve_image_file("x.jpg")
    finally:
        get_settings.cache_clear()


def test_store_image_writes_uuid_jpeg(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PRODUCT_IMAGE_DIR", str(tmp_path))
    from apps.api.config import get_settings

    get_settings.cache_clear()
    try:
        url = store_image(_JPEG)
        name = stored_name_from_url(url)
        assert name is not None
        assert (tmp_path / name).read_bytes()[:3] == b"\xff\xd8\xff"
        with pytest.raises(ValueError, match="JPEG"):
            store_image(_SVG)
        with pytest.raises(ValueError, match="большой"):
            store_image(b"\xff\xd8\xff" + b"\x00" * (MAX_IMAGE_BYTES + 1))
    finally:
        get_settings.cache_clear()
