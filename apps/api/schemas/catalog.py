from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    parent_id: UUID | None
    sort_order: int


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    brand: str | None
    price: Decimal | None
    is_hot: bool
    image_url: str | None
    attributes: dict = Field(default_factory=dict)


class ProductDetailOut(ProductOut):
    description: str | None
    category_id: UUID | None
    is_manual: bool
    updated_at: datetime


class ChannelCreate(BaseModel):
    title: str
    telegram_id: str
    username: str | None = None
    is_private: bool = False


class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    telegram_id: str
    username: str | None
    folder_label: str | None = None
    is_private: bool
    status: str
    last_parsed_at: datetime | None
    last_error: str | None


class ChannelStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|paused|error)$")


class AdminProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    brand: str | None
    price: Decimal | None
    cost_median: Decimal | None = None
    markup_percent: Decimal | None = None
    is_hot: bool
    is_published: bool
    is_manual: bool
    image_url: str | None = None
    updated_at: datetime


class AdminProductPatch(BaseModel):
    is_hot: bool | None = None
    is_published: bool | None = None
    title: str | None = None
    price: Decimal | None = None


class ManualProductCreate(BaseModel):
    title: str = Field(min_length=2, max_length=512)
    price: Decimal = Field(gt=0)
    brand: str | None = None
    is_hot: bool = False
    is_published: bool = True
    description: str | None = None


class OfferLogOut(BaseModel):
    id: UUID
    raw_title: str
    raw_price: Decimal
    currency: str
    parsed_at: datetime
    source_message_id: str | None
    is_active: bool
    channel_id: UUID
    channel_title: str
    folder_label: str | None = None


class StoreSettingsOut(BaseModel):
    default_markup_percent: Decimal
    price_round_to: int


class StoreSettingsUpdate(BaseModel):
    default_markup_percent: Decimal | None = Field(default=None, ge=0, le=100)
    price_round_to: int | None = Field(default=None, ge=1, le=10000)
