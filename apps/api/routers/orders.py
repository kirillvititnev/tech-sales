import secrets
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.db import get_db
from apps.api.models.catalog import Product
from apps.api.models.order import AdminOrderStatus, CustomerOrderStatus, DeliveryType, Order, OrderItem
from apps.api.schemas.order import OrderCreate, OrderOut
from apps.api.services.orders import validate_contacts, validate_delivery

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_number() -> str:
    return f"WS-{secrets.token_hex(4).upper()}"


def _load_order_query():
    return select(Order).options(selectinload(Order.items))


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)) -> Order:
    contact_err = validate_contacts(payload.customer_name, payload.customer_phone)
    if contact_err:
        raise HTTPException(status_code=400, detail=contact_err)

    delivery_err = validate_delivery(payload.delivery_type, payload.delivery_address)
    if delivery_err:
        raise HTTPException(status_code=400, detail=delivery_err)

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

    address = (payload.delivery_address or "").strip() or None
    if payload.delivery_type == DeliveryType.pickup_moscow:
        address = address or "Самовывоз, Москва"

    order = Order(
        number=_order_number(),
        customer_name=payload.customer_name.strip(),
        customer_phone=payload.customer_phone.strip(),
        customer_telegram=(payload.customer_telegram or "").strip() or None,
        customer_status=CustomerOrderStatus.placed,
        admin_status=AdminOrderStatus.accepted,
        delivery_type=payload.delivery_type,
        delivery_address=address,
        comment=(payload.comment or "").strip() or None,
        total_amount=total,
        items=items,
    )
    db.add(order)
    await db.commit()

    loaded = await db.execute(_load_order_query().where(Order.id == order.id))
    return loaded.scalar_one()


@router.get("/by-number/{number}", response_model=OrderOut)
async def get_order_by_number(number: str, db: AsyncSession = Depends(get_db)) -> Order:
    result = await db.execute(_load_order_query().where(Order.number == number.upper()))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: UUID, db: AsyncSession = Depends(get_db)) -> Order:
    result = await db.execute(_load_order_query().where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order
