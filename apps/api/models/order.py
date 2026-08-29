import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.db import Base
from apps.api.security import new_order_access_token


class CustomerOrderStatus(str, enum.Enum):
    placed = "placed"  # оформлен
    paid = "paid"  # оплачен
    cancelled = "cancelled"  # отменён
    ready = "ready"  # готов к выдаче
    issued = "issued"  # выдан


class AdminOrderStatus(str, enum.Enum):
    accepted = "accepted"  # принят
    paid = "paid"  # оплачен
    processing = "processing"  # обработан
    assembled = "assembled"  # собран
    shipped = "shipped"  # отгружен


class DeliveryType(str, enum.Enum):
    pickup_moscow = "pickup_moscow"
    cdek = "cdek"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_telegram: Mapped[str | None] = mapped_column(String(128), nullable=True)
    customer_status: Mapped[CustomerOrderStatus] = mapped_column(
        Enum(CustomerOrderStatus), default=CustomerOrderStatus.placed, nullable=False
    )
    admin_status: Mapped[AdminOrderStatus] = mapped_column(
        Enum(AdminOrderStatus), default=AdminOrderStatus.accepted, nullable=False
    )
    delivery_type: Mapped[DeliveryType] = mapped_column(Enum(DeliveryType), nullable=False)
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    bonus_spent: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    access_token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, default=new_order_access_token
    )
    privacy_consented_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
