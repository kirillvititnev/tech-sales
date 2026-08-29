from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from apps.api.db import get_db
from apps.api.models.catalog import ChannelStatus, Product, ProductOffer, SupplierChannel
from apps.api.models.order import CustomerOrderStatus, Order
from apps.api.models.user import User
from apps.api.schemas.account import AdminBonusAdjust, AdminUserOut, AdminUserPatch
from apps.api.schemas.catalog import (
    AdminProductOut,
    AdminProductPatch,
    ChannelCreate,
    ChannelOut,
    ChannelStatusUpdate,
    ManualProductCreate,
    MarkupRule,
    OfferLogOut,
    StoreSettingsOut,
    StoreSettingsUpdate,
)
from apps.api.schemas.order import AdminOrderAction, AdminOrderMessage, AdminOrderOut, AdminOrderStatusUpdate
from apps.api.services.admin_catalog import get_or_create_store_settings, slugify_manual
from apps.api.services.bonuses import apply_admin_bonus, set_user_active
from apps.api.services.orders import (
    apply_admin_status,
    cancel_order,
    customer_status_notice,
    manager_notice,
    mark_issued,
)
from apps.api.services.referrals import credit_paid_order
from apps.api.services.reprice import reprice_synced_products

from apps.api.security import escape_like, require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _orders_query():
    return select(Order).options(selectinload(Order.items))


def _parse_markup_rules(raw: object) -> list[MarkupRule]:
    if not isinstance(raw, list):
        return []
    parsed: list[MarkupRule] = []
    for item in raw:
        try:
            parsed.append(MarkupRule.model_validate(item))
        except ValidationError:
            continue
    return parsed


def _dump_markup_rules(rules: list[MarkupRule]) -> list[dict]:
    return [{"match": rule.match, "value": rule.value, "percent": float(rule.percent)} for rule in rules]


def _settings_out(row) -> StoreSettingsOut:
    return StoreSettingsOut(
        default_markup_percent=row.default_markup_percent,
        price_round_to=row.price_round_to,
        referral_percent_l1=row.referral_percent_l1,
        referral_percent_l2=row.referral_percent_l2,
        referral_percent_l3=row.referral_percent_l3,
        markup_rules=_parse_markup_rules(row.markup_rules),
    )


@router.get("/settings", response_model=StoreSettingsOut)
async def get_settings(db: AsyncSession = Depends(get_db)) -> StoreSettingsOut:
    row = await get_or_create_store_settings(db)
    await db.commit()
    return _settings_out(row)


@router.patch("/settings", response_model=StoreSettingsOut)
async def patch_settings(
    payload: StoreSettingsUpdate, db: AsyncSession = Depends(get_db)
) -> StoreSettingsOut:
    row = await get_or_create_store_settings(db)
    if payload.default_markup_percent is not None:
        row.default_markup_percent = payload.default_markup_percent
    if payload.price_round_to is not None:
        row.price_round_to = payload.price_round_to
    if payload.referral_percent_l1 is not None:
        row.referral_percent_l1 = payload.referral_percent_l1
    if payload.referral_percent_l2 is not None:
        row.referral_percent_l2 = payload.referral_percent_l2
    if payload.referral_percent_l3 is not None:
        row.referral_percent_l3 = payload.referral_percent_l3
    markup_changed = (
        payload.default_markup_percent is not None
        or payload.price_round_to is not None
        or payload.markup_rules is not None
    )
    if payload.markup_rules is not None:
        row.markup_rules = _dump_markup_rules(payload.markup_rules)
        flag_modified(row, "markup_rules")
    if markup_changed:
        await reprice_synced_products(db, row)
    await db.commit()
    await db.refresh(row)
    return _settings_out(row)


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


@router.patch("/channels/{channel_id}/status", response_model=ChannelOut)
async def patch_channel_status(
    channel_id: UUID,
    payload: ChannelStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> SupplierChannel:
    result = await db.execute(select(SupplierChannel).where(SupplierChannel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    try:
        channel.status = ChannelStatus(payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Неверный статус") from exc
    await db.commit()
    await db.refresh(channel)
    return channel


@router.get("/products", response_model=list[AdminProductOut])
async def admin_list_products(
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    stmt = select(Product)
    if q and q.strip():
        term = f"%{escape_like(q.strip())}%"
        stmt = stmt.where(Product.title.ilike(term, escape="\\"))
    stmt = stmt.order_by(Product.updated_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/products", response_model=AdminProductOut, status_code=201)
async def create_manual_product(
    payload: ManualProductCreate, db: AsyncSession = Depends(get_db)
) -> Product:
    product = Product(
        slug=slugify_manual(payload.title),
        title=payload.title.strip(),
        brand=(payload.brand or "").strip() or None,
        description=(payload.description or "").strip() or None,
        price=payload.price.quantize(Decimal("0.01")),
        cost_median=payload.price.quantize(Decimal("0.01")),
        markup_percent=Decimal("0"),
        is_manual=True,
        is_hot=payload.is_hot,
        is_published=payload.is_published,
        attributes={"source": "manual"},
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.patch("/products/{product_id}", response_model=AdminProductOut)
async def patch_product(
    product_id: UUID,
    payload: AdminProductPatch,
    db: AsyncSession = Depends(get_db),
) -> Product:
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    if payload.is_hot is not None:
        product.is_hot = payload.is_hot
    if payload.is_published is not None:
        product.is_published = payload.is_published
    if payload.title is not None:
        product.title = payload.title.strip()
    if payload.price is not None:
        product.price = payload.price.quantize(Decimal("0.01"))
        if product.is_manual:
            product.cost_median = product.price
    await db.commit()
    await db.refresh(product)
    return product


@router.get("/products/{product_id}/offers", response_model=list[OfferLogOut])
async def product_offers(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[OfferLogOut]:
    result = await db.execute(select(Product).where(Product.id == product_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Товар не найден")

    offers = (
        await db.execute(
            select(ProductOffer)
            .options(selectinload(ProductOffer.channel))
            .where(ProductOffer.product_id == product_id)
            .order_by(ProductOffer.parsed_at.desc())
            .limit(100)
        )
    ).scalars().all()

    return [
        OfferLogOut(
            id=o.id,
            raw_title=o.raw_title,
            raw_price=o.raw_price,
            currency=o.currency,
            parsed_at=o.parsed_at,
            source_message_id=o.source_message_id,
            is_active=o.is_active,
            channel_id=o.channel_id,
            channel_title=o.channel.title if o.channel else "—",
            folder_label=o.channel.folder_label if o.channel else None,
        )
        for o in offers
    ]


@router.get("/orders", response_model=list[AdminOrderOut])
async def list_orders(db: AsyncSession = Depends(get_db)) -> list[Order]:
    result = await db.execute(_orders_query().order_by(Order.created_at.desc()).limit(100))
    return list(result.scalars().all())


@router.get("/orders/{order_id}", response_model=AdminOrderOut)
async def get_admin_order(order_id: UUID, db: AsyncSession = Depends(get_db)) -> Order:
    result = await db.execute(_orders_query().where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order


@router.patch("/orders/{order_id}/status", response_model=AdminOrderOut)
async def update_admin_status(
    order_id: UUID,
    payload: AdminOrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> Order:
    result = await db.execute(_orders_query().where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    previous = order.customer_status
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
    if customer_status == CustomerOrderStatus.paid and previous != CustomerOrderStatus.paid:
        settings_row = await get_or_create_store_settings(db)
        await credit_paid_order(db, order, settings_row)
    notice = customer_status_notice(
        user_id=order.user_id,
        number=order.number,
        previous=previous,
        new_status=customer_status,
    )
    if notice:
        db.add(notice)
    await db.commit()

    loaded = await db.execute(_orders_query().where(Order.id == order.id))
    return loaded.scalar_one()


@router.post("/orders/{order_id}/actions", response_model=AdminOrderOut)
async def order_action(
    order_id: UUID,
    payload: AdminOrderAction,
    db: AsyncSession = Depends(get_db),
) -> Order:
    result = await db.execute(_orders_query().where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    previous = order.customer_status
    try:
        if payload.action == "cancel":
            order.customer_status = cancel_order(order.customer_status)
        elif payload.action == "issue":
            order.customer_status = mark_issued(order.customer_status)
        else:
            raise HTTPException(status_code=400, detail="Неизвестное действие")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    notice = customer_status_notice(
        user_id=order.user_id,
        number=order.number,
        previous=previous,
        new_status=order.customer_status,
    )
    if notice:
        db.add(notice)
    await db.commit()
    loaded = await db.execute(_orders_query().where(Order.id == order.id))
    return loaded.scalar_one()


@router.post("/orders/{order_id}/message", response_model=AdminOrderOut)
async def order_message(
    order_id: UUID,
    payload: AdminOrderMessage,
    db: AsyncSession = Depends(get_db),
) -> Order:
    result = await db.execute(_orders_query().where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    notice = manager_notice(user_id=order.user_id, number=order.number, body=payload.body)
    if notice is None:
        raise HTTPException(
            status_code=400,
            detail="У заказа нет кабинета — напишите клиенту напрямую",
        )
    db.add(notice)
    await db.commit()
    loaded = await db.execute(_orders_query().where(Order.id == order.id))
    return loaded.scalar_one()


async def _get_user(db: AsyncSession, user_id: UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    stmt = select(User)
    needle = (q or "").strip()
    if needle:
        term = f"%{escape_like(needle)}%"
        stmt = stmt.where(
            or_(
                User.email.ilike(term, escape="\\"),
                User.name.ilike(term, escape="\\"),
                User.phone.ilike(term, escape="\\"),
                User.telegram_id.ilike(term, escape="\\"),
                User.referral_code.ilike(term, escape="\\"),
            )
        )
    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def patch_user(
    user_id: UUID,
    payload: AdminUserPatch,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _get_user(db, user_id)
    await set_user_active(db, user, is_active=payload.is_active)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/bonus", response_model=AdminUserOut)
async def adjust_user_bonus(
    user_id: UUID,
    payload: AdminBonusAdjust,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _get_user(db, user_id)
    try:
        await apply_admin_bonus(db, user, delta=payload.delta, note=payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(user)
    return user


async def _get_user(db: AsyncSession, user_id: UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    stmt = select(User)
    needle = (q or "").strip()
    if needle:
        term = f"%{escape_like(needle)}%"
        stmt = stmt.where(
            or_(
                User.email.ilike(term, escape="\\"),
                User.name.ilike(term, escape="\\"),
                User.phone.ilike(term, escape="\\"),
                User.telegram_id.ilike(term, escape="\\"),
                User.referral_code.ilike(term, escape="\\"),
            )
        )
    stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def patch_user(
    user_id: UUID,
    payload: AdminUserPatch,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _get_user(db, user_id)
    await set_user_active(db, user, is_active=payload.is_active)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/bonus", response_model=AdminUserOut)
async def adjust_user_bonus(
    user_id: UUID,
    payload: AdminBonusAdjust,
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await _get_user(db, user_id)
    try:
        await apply_admin_bonus(db, user, delta=payload.delta, note=payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(user)
    return user
