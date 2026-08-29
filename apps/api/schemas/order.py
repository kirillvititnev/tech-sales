from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from apps.api.models.order import AdminOrderStatus, DeliveryType


class OrderItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    quantity: int = Field(ge=1, le=100, default=1)


class OrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_name: str = Field(min_length=2, max_length=255)
    customer_phone: str = Field(min_length=10, max_length=32)
    customer_telegram: str | None = Field(default=None, max_length=128)
    delivery_type: DeliveryType
    delivery_address: str | None = Field(default=None, max_length=2000)
    comment: str | None = Field(default=None, max_length=2000)
    telegram_init_data: str | None = Field(default=None, max_length=4096)
    privacy_consent: bool
    items: list[OrderItemIn] = Field(min_length=1, max_length=50)

    @field_validator("privacy_consent")
    @classmethod
    def require_privacy_consent(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Нужно согласие на обработку персональных данных")
        return value


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID | None
    title: str
    unit_price: Decimal
    quantity: int


class OrderOut(BaseModel):
    """Customer-facing order. access_token is set only on create."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str
    customer_name: str
    customer_phone: str
    customer_telegram: str | None = None
    customer_status: str
    delivery_type: str
    delivery_address: str | None = None
    comment: str | None = None
    total_amount: Decimal
    items: list[OrderItemOut] = []
    access_token: str | None = None


class AdminOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str
    customer_name: str
    customer_phone: str
    customer_telegram: str | None = None
    customer_status: str
    admin_status: str
    delivery_type: str
    delivery_address: str | None = None
    comment: str | None = None
    total_amount: Decimal
    items: list[OrderItemOut] = []


class AdminOrderStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admin_status: AdminOrderStatus


class AdminOrderAction(BaseModel):
    """issue | cancel"""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(pattern="^(issue|cancel)$")
