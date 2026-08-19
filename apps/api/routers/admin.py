from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db import get_db
from apps.api.models.catalog import SupplierChannel
from apps.api.models.order import Order
from apps.api.schemas.catalog import ChannelCreate, ChannelOut
from apps.api.schemas.order import OrderOut
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/admin", tags=["admin"])


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
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc()).limit(100)
    )
    return list(result.scalars().all())
