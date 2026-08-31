from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.db import get_db
from apps.api.deps import require_user
from apps.api.models.account import BonusLedger, Favorite, ProductView, UserNotification
from apps.api.models.catalog import Product
from apps.api.models.order import Order
from apps.api.models.user import User
from apps.api.schemas.account import (
    PRIVACY_POLICY_VERSION,
    BonusExportOut,
    DataExportOut,
    DeleteAccountIn,
    FavoriteIn,
    MeOut,
    NotificationOut,
    ProfilePatch,
    UnreadNotificationsOut,
    ViewIn,
)
from apps.api.schemas.catalog import ProductOut
from apps.api.schemas.order import OrderOut
from apps.api.services.passwords import dummy_verify, verify_password
from apps.api.services.privacy import erase_account_personal_data
from apps.api.services.sessions import revoke_all_sessions

router = APIRouter(prefix="/me", tags=["account"])


def _me(user: User) -> MeOut:
    return MeOut.model_validate(user)


@router.get("", response_model=MeOut)
async def read_me(user: User = Depends(require_user)) -> MeOut:
    return _me(user)


@router.patch("", response_model=MeOut)
async def patch_me(
    payload: ProfilePatch,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    if payload.name is not None:
        user.name = payload.name.strip() or None
    if payload.phone is not None:
        user.phone = payload.phone.strip() or None
    await db.commit()
    await db.refresh(user)
    return _me(user)


@router.get("/orders", response_model=list[OrderOut])
async def my_orders(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> list[OrderOut]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(50)
    )
    return [
        OrderOut.model_validate(order).model_copy(update={"access_token": None})
        for order in result.scalars().all()
    ]


@router.get("/orders/{number}", response_model=OrderOut)
async def my_order(
    number: str,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> OrderOut:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.number == number.upper(), Order.user_id == user.id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return OrderOut.model_validate(order).model_copy(update={"access_token": None})


@router.get("/favorites", response_model=list[ProductOut])
async def list_favorites(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    result = await db.execute(
        select(Product)
        .join(Favorite, Favorite.product_id == Product.id)
        .where(Favorite.user_id == user.id, Product.is_published.is_(True))
        .order_by(Favorite.created_at.desc())
        .limit(100)
    )
    return list(result.scalars().all())


@router.post("/favorites", response_model=ProductOut, status_code=201)
async def add_favorite(
    payload: FavoriteIn,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Product:
    product = await db.get(Product, payload.product_id)
    if product is None or not product.is_published:
        raise HTTPException(status_code=404, detail="Товар не найден")
    exists = await db.execute(
        select(Favorite.id).where(Favorite.user_id == user.id, Favorite.product_id == product.id)
    )
    if exists.scalar_one_or_none() is None:
        db.add(Favorite(user_id=user.id, product_id=product.id))
        await db.commit()
    return product


@router.delete("/favorites/{product_id}", status_code=204)
async def remove_favorite(
    product_id: UUID,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.product_id == product_id)
    )
    row = result.scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    return Response(status_code=204)


@router.get("/views", response_model=list[ProductOut])
async def list_views(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> list[Product]:
    result = await db.execute(
        select(Product)
        .join(ProductView, ProductView.product_id == Product.id)
        .where(ProductView.user_id == user.id, Product.is_published.is_(True))
        .order_by(ProductView.viewed_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


@router.post("/views", response_model=ProductOut)
async def record_view(
    payload: ViewIn,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Product:
    product = await db.get(Product, payload.product_id)
    if product is None or not product.is_published:
        raise HTTPException(status_code=404, detail="Товар не найден")
    result = await db.execute(
        select(ProductView).where(ProductView.user_id == user.id, ProductView.product_id == product.id)
    )
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row:
        row.viewed_at = now
    else:
        db.add(ProductView(user_id=user.id, product_id=product.id, viewed_at=now))
    await db.commit()
    return product


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserNotification]:
    result = await db.execute(
        select(UserNotification)
        .where(UserNotification.user_id == user.id)
        .order_by(UserNotification.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


@router.get("/notifications/unread-count", response_model=UnreadNotificationsOut)
async def unread_notification_count(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadNotificationsOut:
    total = await db.execute(
        select(func.count())
        .select_from(UserNotification)
        .where(UserNotification.user_id == user.id, UserNotification.read_at.is_(None))
    )
    return UnreadNotificationsOut(unread=int(total.scalar_one()))


@router.post("/notifications/{note_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    note_id: UUID,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> UserNotification:
    result = await db.execute(
        select(UserNotification).where(
            UserNotification.id == note_id, UserNotification.user_id == user.id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(row)
    return row


def _orders_without_access(orders: list[Order]) -> list[OrderOut]:
    return [OrderOut.model_validate(order).model_copy(update={"access_token": None}) for order in orders]


@router.get("/export", response_model=DataExportOut)
async def export_me(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> DataExportOut:
    orders = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(200)
    )
    favs = await db.execute(select(Favorite.product_id).where(Favorite.user_id == user.id))
    views = await db.execute(select(ProductView.product_id).where(ProductView.user_id == user.id))
    notes = await db.execute(
        select(UserNotification)
        .where(UserNotification.user_id == user.id)
        .order_by(UserNotification.created_at.desc())
        .limit(200)
    )
    bonuses = await db.execute(
        select(BonusLedger).where(BonusLedger.user_id == user.id).order_by(BonusLedger.created_at.desc())
    )
    return DataExportOut(
        exported_at=datetime.now(timezone.utc),
        privacy_policy_version=user.privacy_policy_version or PRIVACY_POLICY_VERSION,
        profile=_me(user),
        orders=_orders_without_access(list(orders.scalars().all())),
        favorite_product_ids=list(favs.scalars().all()),
        viewed_product_ids=list(views.scalars().all()),
        notifications=[NotificationOut.model_validate(row) for row in notes.scalars().all()],
        bonuses=[BonusExportOut.model_validate(row) for row in bonuses.scalars().all()],
    )


@router.post("/delete", status_code=204)
async def delete_me(
    payload: DeleteAccountIn,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    if user.password_hash:
        if not payload.password:
            dummy_verify("missing-password")
            raise HTTPException(status_code=400, detail="Нужен текущий пароль")
        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Неверный пароль")
    await erase_account_personal_data(db, user)
    await db.execute(sa_delete(Favorite).where(Favorite.user_id == user.id))
    await db.execute(sa_delete(ProductView).where(ProductView.user_id == user.id))
    await db.execute(sa_delete(UserNotification).where(UserNotification.user_id == user.id))
    user.email = None
    user.telegram_id = None
    user.name = None
    user.phone = None
    user.password_hash = None
    user.is_active = False
    user.privacy_consented_at = None
    user.privacy_policy_version = None
    await revoke_all_sessions(db, user)
    await db.commit()
    return Response(status_code=204)

