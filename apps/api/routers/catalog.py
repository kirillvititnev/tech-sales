from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import get_db
from apps.api.models.catalog import Category, Product
from apps.api.schemas.catalog import (
    CatalogFacetsOut,
    CategoryOut,
    FacetValueOut,
    ProductDetailOut,
    ProductOut,
    SuggestItemOut,
)
from apps.api.security import escape_like, public_product_attributes

router = APIRouter(prefix="/catalog", tags=["catalog"])

CATALOG_ID_LOOKUP_LIMIT = 50

SORT_OPTIONS = {
    "relevance",
    "price_asc",
    "price_desc",
    "name_asc",
    "name_desc",
    "brand_asc",
    "newest",
    "hot",
}


def _device_category_col():
    return Product.attributes["device_category"].astext


def _device_name_col():
    return Product.attributes["device_name"].astext


def _kind_col():
    return Product.attributes["kind"].astext


def _attr_text(key: str):
    return Product.attributes[key].astext


def _search_haystack():
    """Title + brand + key attribute fields used for token search."""
    return func.concat_ws(
        " ",
        Product.title,
        Product.brand,
        _device_name_col(),
        _attr_text("config"),
        _attr_text("storage"),
        _attr_text("color"),
        _attr_text("sim"),
        _attr_text("ram"),
    )


def _apply_product_filters(
    stmt,
    *,
    q: str | None = None,
    brand: str | None = None,
    category_id: UUID | None = None,
    device_category: str | None = None,
    hot: bool | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
):
    stmt = stmt.where(Product.is_published.is_(True))
    if q:
        # Token AND-match so "17 pro max 256" hits "iPhone 17 Pro Max · 256GB · …"
        haystack = _search_haystack()
        for token in q.strip().split():
            if not token:
                continue
            stmt = stmt.where(haystack.ilike(f"%{escape_like(token)}%", escape="\\"))
    if brand:
        stmt = stmt.where(Product.brand.ilike(escape_like(brand.strip()), escape="\\"))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if device_category:
        stmt = stmt.where(_device_category_col() == device_category.strip())
    if hot is True:
        stmt = stmt.where(Product.is_hot.is_(True))
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    return stmt


def _order_products(stmt, sort: str):
    kind = _kind_col()
    kind_rank = case(
        (kind == "iphone", 0),
        (kind == "samsung", 1),
        (kind == "apple_other", 2),
        else_=3,
    )
    device_name = _device_name_col()

    if sort == "price_asc":
        return stmt.order_by(Product.price.asc().nulls_last(), Product.title.asc())
    if sort == "price_desc":
        return stmt.order_by(Product.price.desc().nulls_last(), Product.title.asc())
    if sort == "name_asc":
        return stmt.order_by(device_name.asc().nulls_last(), Product.title.asc())
    if sort == "name_desc":
        return stmt.order_by(device_name.desc().nulls_last(), Product.title.desc())
    if sort == "brand_asc":
        return stmt.order_by(
            Product.brand.asc().nulls_last(),
            device_name.asc().nulls_last(),
            Product.title.asc(),
        )
    if sort == "newest":
        return stmt.order_by(Product.updated_at.desc(), Product.title.asc())
    if sort == "hot":
        return stmt.order_by(
            Product.is_hot.desc(),
            Product.price.asc().nulls_last(),
            Product.title.asc(),
        )

    # relevance (default): phones first, then brand / device / price
    return stmt.order_by(
        Product.is_hot.desc(),
        kind_rank,
        Product.brand.asc().nulls_last(),
        device_name.asc().nulls_last(),
        Product.title.asc(),
        Product.price.asc().nulls_last(),
    )


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[Category]:
    result = await db.execute(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.name)
    )
    return list(result.scalars().all())


@router.get("/facets", response_model=CatalogFacetsOut)
async def catalog_facets(
    q: str | None = None,
    brand: str | None = None,
    category_id: UUID | None = None,
    device_category: str | None = None,
    hot: bool | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    db: AsyncSession = Depends(get_db),
) -> CatalogFacetsOut:
    filtered = _apply_product_filters(
        select(Product.id, Product.price, Product.brand),
        q=q,
        brand=brand,
        category_id=category_id,
        device_category=device_category,
        hot=hot,
        min_price=min_price,
        max_price=max_price,
    )
    filtered_subq = filtered.subquery()

    total = int((await db.execute(select(func.count()).select_from(filtered_subq))).scalar_one())
    price_min, price_max = (
        await db.execute(select(func.min(filtered_subq.c.price), func.max(filtered_subq.c.price)))
    ).one()

    # Brand facet: ignore brand filter so the user can switch brands
    brands_stmt = _apply_product_filters(
        select(Product.brand, func.count()),
        q=q,
        category_id=category_id,
        device_category=device_category,
        hot=hot,
        min_price=min_price,
        max_price=max_price,
    )
    brands_stmt = (
        brands_stmt.where(Product.brand.is_not(None))
        .group_by(Product.brand)
        .order_by(func.count().desc(), Product.brand.asc())
    )
    brand_rows = (await db.execute(brands_stmt)).all()

    # Device category facet: ignore device_category filter
    cat_col = _device_category_col()
    cats_stmt = _apply_product_filters(
        select(cat_col, func.count()),
        q=q,
        brand=brand,
        category_id=category_id,
        hot=hot,
        min_price=min_price,
        max_price=max_price,
    )
    cats_stmt = (
        cats_stmt.where(cat_col.is_not(None), cat_col != "")
        .group_by(cat_col)
        .order_by(func.count().desc(), cat_col.asc())
    )
    cat_rows = (await db.execute(cats_stmt)).all()

    return CatalogFacetsOut(
        brands=[FacetValueOut(value=str(name), count=int(cnt)) for name, cnt in brand_rows if name],
        device_categories=[
            FacetValueOut(value=str(name), count=int(cnt)) for name, cnt in cat_rows if name
        ],
        price_min=price_min,
        price_max=price_max,
        total=total,
    )


@router.get("/suggest", response_model=list[SuggestItemOut])
async def suggest_products(
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> list[SuggestItemOut]:
    stmt = select(Product).where(Product.is_published.is_(True))
    haystack = _search_haystack()
    for token in q.strip().split():
        if token:
            stmt = stmt.where(haystack.ilike(f"%{escape_like(token)}%", escape="\\"))
    stmt = stmt.order_by(Product.is_hot.desc(), Product.title.asc()).limit(limit)
    products = list((await db.execute(stmt)).scalars().all())
    out: list[SuggestItemOut] = []
    for p in products:
        attrs = public_product_attributes(p.attributes if isinstance(p.attributes, dict) else {})
        out.append(
            SuggestItemOut(
                slug=p.slug,
                title=p.title,
                brand=p.brand,
                price=p.price,
                device_category=attrs.get("device_category") if isinstance(attrs.get("device_category"), str) else None,
                device_name=attrs.get("device_name") if isinstance(attrs.get("device_name"), str) else None,
            )
        )
    return out


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    q: str | None = None,
    brand: str | None = None,
    category_id: UUID | None = None,
    device_category: str | None = None,
    hot: bool | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    sort: str = Query(default="relevance"),
    limit: int = Query(default=120, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ids: list[UUID] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    if ids is not None:
        if len(ids) > CATALOG_ID_LOOKUP_LIMIT:
            raise HTTPException(status_code=400, detail="Не больше 50 товаров за запрос")
        unique = list(dict.fromkeys(ids))
        if not unique:
            return []
        loaded = await db.execute(
            select(Product).where(Product.id.in_(unique), Product.is_published.is_(True))
        )
        found = {product.id: product for product in loaded.scalars().all()}
        return [found[item] for item in unique if item in found]

    sort_key = sort if sort in SORT_OPTIONS else "relevance"
    stmt = _apply_product_filters(
        select(Product),
        q=q,
        brand=brand,
        category_id=category_id,
        device_category=device_category,
        hot=hot,
        min_price=min_price,
        max_price=max_price,
    )
    stmt = _order_products(stmt, sort_key).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/products/{slug}", response_model=ProductDetailOut)
async def get_product(slug: str, db: AsyncSession = Depends(get_db)) -> Product:
    result = await db.execute(
        select(Product).where(Product.slug == slug, Product.is_published.is_(True))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product
