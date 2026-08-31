from datetime import datetime
from decimal import Decimal
from uuid import UUID

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from apps.api.security import public_product_attributes
from apps.api.services.pricing import PRICE_RECEIPT_KEY
from apps.api.services.product_images import is_storefront_image_url


def _storefront_image(value: Any) -> str | None:
    if value is None or value == "":
        return None
    text = str(value)
    return text if is_storefront_image_url(text) else None


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

    @field_validator("image_url", mode="before")
    @classmethod
    def only_local_image(cls, value: Any) -> str | None:
        return _storefront_image(value)

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
    model_config = ConfigDict(extra="forbid")
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
    counts_toward_price: bool = True


class ChannelStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^(active|paused|error)$")
    counts_toward_price: bool | None = None


class PriceReceiptOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    accepted_n: int = Field(ge=0)
    quarantined_n: int = Field(ge=0)
    accepted: list[str] = Field(default_factory=list, max_length=40)
    quarantined: list[str] = Field(default_factory=list, max_length=40)
    markup_percent: float | None = None
    round_to: int | None = None


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
    price_receipt: PriceReceiptOut | None = None

    @field_validator("image_url", mode="before")
    @classmethod
    def only_local_image(cls, value: Any) -> str | None:
        return _storefront_image(value)


def admin_product_out(product: Any) -> AdminProductOut:
    out = AdminProductOut.model_validate(product)
    raw = getattr(product, "attributes", None)
    receipt = raw.get(PRICE_RECEIPT_KEY) if isinstance(raw, dict) else None
    parsed: PriceReceiptOut | None = None
    if receipt is not None:
        try:
            parsed = PriceReceiptOut.model_validate(receipt)
        except ValidationError:
            parsed = None
    return out.model_copy(update={"price_receipt": parsed})


class AdminProductListOut(BaseModel):
    items: list[AdminProductOut]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class AdminProductPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_hot: bool | None = None
    is_published: bool | None = None
    title: str | None = None
    price: Decimal | None = None


class ManualProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
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


class MarkupRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match: Literal["brand", "category", "kind"]
    value: str = Field(min_length=1, max_length=128)
    percent: Decimal = Field(ge=0, le=100)

    @field_validator("value")
    @classmethod
    def strip_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Нужно значение")
        return cleaned


class StoreSettingsOut(BaseModel):
    default_markup_percent: Decimal
    price_round_to: int
    referral_percent_l1: Decimal
    referral_percent_l2: Decimal
    referral_percent_l3: Decimal
    markup_rules: list[MarkupRule] = Field(default_factory=list)
    last_sync_stats: dict[str, Any] = Field(default_factory=dict)


class StoreSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_markup_percent: Decimal | None = Field(default=None, ge=0, le=100)
    price_round_to: int | None = Field(default=None, ge=1, le=10000)
    referral_percent_l1: Decimal | None = Field(default=None, ge=0, le=50)
    referral_percent_l2: Decimal | None = Field(default=None, ge=0, le=50)
    referral_percent_l3: Decimal | None = Field(default=None, ge=0, le=50)
    markup_rules: list[MarkupRule] | None = Field(default=None, max_length=50)


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
