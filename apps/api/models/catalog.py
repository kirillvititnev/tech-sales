import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.db import Base


class ChannelStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    error = "error"


class SupplierChannel(Base):
    __tablename__ = "supplier_channels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    folder_label: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ChannelStatus] = mapped_column(Enum(ChannelStatus), default=ChannelStatus.active)
    last_parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    counts_toward_price: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    offers: Mapped[list["ProductOffer"]] = relationship(back_populates="channel")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    # Median of supplier prices (before markup)
    cost_median: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Storefront price after markup + rounding
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, index=True)
    markup_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_hot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped[Category | None] = relationship(back_populates="products")
    offers: Mapped[list["ProductOffer"]] = relationship(back_populates="product")


class ProductOffer(Base):
    """Raw supplier price offer with provenance for admin audit."""

    __tablename__ = "product_offers"
    __table_args__ = (UniqueConstraint("channel_id", "external_key", name="uq_offer_channel_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True, index=True
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_channels.id"), nullable=False, index=True
    )
    external_key: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_title: Mapped[str] = mapped_column(String(1024), nullable=False)
    raw_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="RUB", nullable=False)
    source_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    parsed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    product: Mapped[Product | None] = relationship(back_populates="offers")
    channel: Mapped[SupplierChannel] = relationship(back_populates="offers")


class StoreSettings(Base):
    """Singleton store pricing defaults (row id=1)."""

    __tablename__ = "store_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    default_markup_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("0"))
    price_round_to: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    referral_percent_l1: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("5"))
    referral_percent_l2: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("2"))
    referral_percent_l3: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=Decimal("1"))
    markup_rules: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    last_sync_stats: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
