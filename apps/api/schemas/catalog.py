from datetime import datetime
from decimal import Decimal
from uuid import UUID

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.api.security import public_product_attributes


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
    attributes: dict[str, Any] = Field(default_factory=dict)

    @field_validator("attributes", mode="before")
    @classmethod
    def strip_internal_attributes(cls, value: Any) -> dict[str, Any]:
        return public_product_attributes(value if isinstance(value, dict) else {})


class ProductDetailOut(ProductOut):
    description: str | None
    category_id: UUID | None
    is_manual: bool
    updated_at: datetime


class ChannelCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    telegram_id: str = Field(min_length=1, max_length=128)
    username: str | None = Field(default=None, max_length=128)
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


class SuggestItemOut(BaseModel):
    slug: str
    title: str
    brand: str | None = None
    price: Decimal | None = None
    device_category: str | None = None
    device_name: str | None = None

    @field_validator("device_category", "device_name", mode="before")
    @classmethod
    def nonempty_str(cls, value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value
        return None


class FacetValueOut(BaseModel):
    value: str
    count: int


class CatalogFacetsOut(BaseModel):
    brands: list[FacetValueOut]
    device_categories: list[FacetValueOut]
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    total: int = 0
