from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import get_db
from apps.api.models.catalog import Category, Product
from apps.api.schemas.catalog import CategoryOut, ProductDetailOut, ProductOut

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(db: AsyncSession = Depends(get_db)) -> list[Category]:
    result = await db.execute(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.name)
    )
    return list(result.scalars().all())


@router.get("/products", response_model=list[ProductOut])
async def list_products(
    q: str | None = None,
    brand: str | None = None,
    category_id: UUID | None = None,
    hot: bool | None = None,
    limit: int = Query(default=40, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    stmt = select(Product).where(Product.is_published.is_(True))
    if q:
        stmt = stmt.where(Product.title.ilike(f"%{q}%"))
    if brand:
        stmt = stmt.where(Product.brand.ilike(brand))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if hot is True:
        stmt = stmt.where(Product.is_hot.is_(True))
    stmt = stmt.order_by(Product.is_hot.desc(), Product.updated_at.desc()).limit(limit).offset(offset)
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
