from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from apps.api.models.order import AdminOrderStatus, DeliveryType


class OrderItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1, default=1)


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=255)
    customer_phone: str = Field(min_length=10, max_length=32)
    customer_telegram: str | None = Field(default=None, max_length=128)
    delivery_type: DeliveryType
    delivery_address: str | None = None
    comment: str | None = None
    items: list[OrderItemIn] = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID | None
    title: str
    unit_price: Decimal
    quantity: int


class OrderOut(BaseModel):
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
    admin_status: AdminOrderStatus


class AdminOrderAction(BaseModel):
    """issue | cancel"""

    action: str = Field(pattern="^(issue|cancel)$")
