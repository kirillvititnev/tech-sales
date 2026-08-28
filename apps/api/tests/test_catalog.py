from apps.api.routers.catalog import SORT_OPTIONS


def test_catalog_sort_options() -> None:
    assert "relevance" in SORT_OPTIONS
    assert "price_asc" in SORT_OPTIONS
    assert "price_desc" in SORT_OPTIONS
    assert "name_asc" in SORT_OPTIONS
    assert "newest" in SORT_OPTIONS
    assert "hot" in SORT_OPTIONS
