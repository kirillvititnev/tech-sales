from apps.api.routers.catalog import CATALOG_ID_LOOKUP_LIMIT, SORT_OPTIONS


def test_catalog_sort_options() -> None:
    assert "relevance" in SORT_OPTIONS
    assert "price_asc" in SORT_OPTIONS
    assert "price_desc" in SORT_OPTIONS
    assert "name_asc" in SORT_OPTIONS
    assert "newest" in SORT_OPTIONS
    assert "hot" in SORT_OPTIONS


def test_catalog_id_lookup_limit() -> None:
    assert CATALOG_ID_LOOKUP_LIMIT == 50
