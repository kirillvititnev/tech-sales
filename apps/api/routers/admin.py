from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.db import get_db
from apps.api.models.catalog import SupplierChannel
from apps.api.models.order import Order
from apps.api.schemas.catalog import ChannelCreate, ChannelOut
from apps.api.schemas.order import AdminOrderAction, AdminOrderStatusUpdate, OrderOut
from apps.api.services.orders import apply_admin_status, cancel_order, mark_issued

router = APIRouter(prefix="/admin", tags=["admin"])


def _orders_query():
    return select(Order).options(selectinload(Order.items))


@router.get("/channels", response_model=list[ChannelOut])
async def list_channels(db: AsyncSession = Depends(get_db)) -> list[SupplierChannel]:
    result = await db.execute(select(SupplierChannel).order_by(SupplierChannel.created_at.desc()))
    return list(result.scalars().all())


@router.post("/channels", response_model=ChannelOut, status_code=201)
async def create_channel(payload: ChannelCreate, db: AsyncSession = Depends(get_db)) -> SupplierChannel:
    channel = SupplierChannel(
        title=payload.title,
        telegram_id=payload.telegram_id,
        username=payload.username,
        is_private=payload.is_private,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.get("/orders", response_model=list[OrderOut])
async def list_orders(db: AsyncSession = Depends(get_db)) -> list[Order]:
    result = await db.execute(_orders_query().order_by(Order.created_at.desc()).limit(100))
    return list(result.scalars().all())


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_admin_order(order_id: UUID, db: AsyncSession = Depends(get_db)) -> Order:
    result = await db.execute(_orders_query().where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
async def update_admin_status(
    order_id: UUID,
    payload: AdminOrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> Order:
    result = await db.execute(_orders_query().where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    try:
        admin_status, customer_status = apply_admin_status(
            delivery_type=order.delivery_type,
            current_admin=order.admin_status,
            current_customer=order.customer_status,
            new_admin=payload.admin_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    order.admin_status = admin_status
    order.customer_status = customer_status
    await db.commit()

    loaded = await db.execute(_orders_query().where(Order.id == order.id))
    return loaded.scalar_one()


@router.post("/orders/{order_id}/actions", response_model=OrderOut)
async def order_action(
    order_id: UUID,
    payload: AdminOrderAction,
    db: AsyncSession = Depends(get_db),
) -> Order:
    result = await db.execute(_orders_query().where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    try:
        if payload.action == "cancel":
            order.customer_status = cancel_order(order.customer_status)
        elif payload.action == "issue":
            order.customer_status = mark_issued(order.customer_status)
        else:
            raise HTTPException(status_code=400, detail="Неизвестное действие")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await db.commit()
    loaded = await db.execute(_orders_query().where(Order.id == order.id))
    return loaded.scalar_one()
