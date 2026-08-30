from uuid import uuid4

from apps.api.routers.catalog import CATALOG_ID_LOOKUP_LIMIT, SORT_OPTIONS
from apps.api.schemas.catalog import ProductOut


def test_catalog_sort_options() -> None:
    assert "relevance" in SORT_OPTIONS
    assert "price_asc" in SORT_OPTIONS
    assert "price_desc" in SORT_OPTIONS
    assert "name_asc" in SORT_OPTIONS
    assert "newest" in SORT_OPTIONS
    assert "hot" in SORT_OPTIONS


def test_catalog_id_lookup_limit() -> None:
    assert CATALOG_ID_LOOKUP_LIMIT == 50


def test_product_out_drops_remote_image_url() -> None:
    base = {
        "id": uuid4(),
        "slug": "iphone",
        "title": "iPhone",
        "brand": "Apple",
        "price": "1000",
        "is_hot": False,
        "attributes": {},
    }
    local = "/api/v1/catalog/media/" + "ab" * 16 + ".jpg"
    assert ProductOut.model_validate({**base, "image_url": local}).image_url == local
    assert ProductOut.model_validate({**base, "image_url": "https://evil.example/x.jpg"}).image_url is None
    assert ProductOut.model_validate({**base, "image_url": "javascript:alert(1)"}).image_url is None
