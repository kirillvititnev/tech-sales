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
    is_private: bool
    status: str
    last_parsed_at: datetime | None
    last_error: str | None
