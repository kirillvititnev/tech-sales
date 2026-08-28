import json
import logging
import hmac
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.config import get_settings
from apps.api.db import get_db
from apps.api.models.catalog import Product
from apps.api.models.order import AdminOrderStatus, CustomerOrderStatus, DeliveryType, Order, OrderItem
from apps.api.schemas.order import OrderCreate, OrderOut
from apps.api.security import new_order_access_token, verify_telegram_init_data
from apps.api.services.order_notify import build_admin_order_message, deliver_admin_order_text
from apps.api.services.orders import validate_contacts, validate_delivery

router = APIRouter(prefix="/orders", tags=["orders"])
logger = logging.getLogger(__name__)


def _order_number() -> str:
    import secrets

    return f"WS-{secrets.token_hex(4).upper()}"


def _load_order_query():
    return select(Order).options(selectinload(Order.items))


def _verified_telegram_username(init_data: str | None) -> str | None:
    settings = get_settings()
    if not init_data or not settings.telegram_bot_token:
        return None
    parsed = verify_telegram_init_data(init_data, settings.telegram_bot_token)
    if parsed is None:
        return None
    raw_user = parsed.get("user")
    if not raw_user:
        return None
    try:
        user = json.loads(raw_user)
    except json.JSONDecodeError:
        return None
    username = user.get("username")
    if isinstance(username, str) and username.strip():
        return f"@{username.strip().lstrip('@')}"
    return None


def _public_order(order: Order, *, include_access: bool) -> OrderOut:
    data = OrderOut.model_validate(order)
    if include_access:
        return data
    return data.model_copy(update={"access_token": None})


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    payload: OrderCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    contact_err = validate_contacts(payload.customer_name, payload.customer_phone)
    if contact_err:
        raise HTTPException(status_code=400, detail=contact_err)

    delivery_err = validate_delivery(payload.delivery_type, payload.delivery_address)
    if delivery_err:
        raise HTTPException(status_code=400, detail=delivery_err)

    telegram = (payload.customer_telegram or "").strip() or None
    verified = _verified_telegram_username(payload.telegram_init_data)
    if verified:
        telegram = verified

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
        customer_telegram=telegram,
        customer_status=CustomerOrderStatus.placed,
        admin_status=AdminOrderStatus.accepted,
        delivery_type=payload.delivery_type,
        delivery_address=address,
        comment=(payload.comment or "").strip() or None,
        total_amount=total,
        access_token=new_order_access_token(),
        privacy_consented_at=datetime.now(timezone.utc),
        items=items,
    )
    db.add(order)
    await db.commit()

    loaded = await db.execute(_load_order_query().where(Order.id == order.id))
    saved = loaded.scalar_one()
    try:
        notice = await build_admin_order_message(db, saved)
        background_tasks.add_task(deliver_admin_order_text, notice)
    except Exception:
        logger.exception("Failed to build admin order notice for %s", saved.number)
    return _public_order(saved, include_access=True)


@router.get("/by-number/{number}", response_model=OrderOut)
async def get_order_by_number(
    number: str,
    access: str = Query(min_length=8, max_length=128),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    result = await db.execute(_load_order_query().where(Order.number == number.upper()))
    order = result.scalar_one_or_none()
    token = order.access_token if order else ""
    # Constant-time compare even when the order is missing.
    dummy = token or ("x" * len(access))
    match = hmac.compare_digest(dummy, access) if len(dummy) == len(access) else False
    if not order or not match:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return _public_order(order, include_access=False)
