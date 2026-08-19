import secrets
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.db import get_db
from apps.api.models.catalog import Product
from apps.api.models.order import AdminOrderStatus, CustomerOrderStatus, Order, OrderItem
from apps.api.schemas.order import OrderCreate, OrderOut

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_number() -> str:
    return f"WS-{secrets.token_hex(4).upper()}"


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)) -> Order:
    product_ids = [i.product_id for i in payload.items]
    result = await db.execute(
        select(Product).where(Product.id.in_(product_ids), Product.is_published.is_(True))
    )
    products = {p.id: p for p in result.scalars().all()}
    if len(products) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="Один или несколько товаров недоступны")

    items: list[OrderItem] = []
    total = Decimal("0")
    for line in payload.items:
        product = products[line.product_id]
        if product.price is None:
            raise HTTPException(status_code=400, detail=f"Нет цены у товара: {product.title}")
        unit = Decimal(product.price)
        total += unit * line.quantity
        items.append(
            OrderItem(
                product_id=product.id,
                title=product.title,
                unit_price=unit,
                quantity=line.quantity,
            )
        )

    order = Order(
        number=_order_number(),
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_telegram=payload.customer_telegram,
        customer_status=CustomerOrderStatus.placed,
        admin_status=AdminOrderStatus.accepted,
        delivery_type=payload.delivery_type,
        delivery_address=payload.delivery_address,
        comment=payload.comment,
        total_amount=total,
        items=items,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    loaded = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    return loaded.scalar_one()


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)) -> Order:
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order
