from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from apps.api.services.passwords import password_error
from apps.api.schemas.order import OrderOut

PRIVACY_POLICY_VERSION = "2026-08-28"
_STRICT = ConfigDict(extra="forbid")


class RegisterIn(BaseModel):
    model_config = _STRICT

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    referral_code: str | None = Field(default=None, max_length=32)
    privacy_consent: bool

    @field_validator("privacy_consent")
    @classmethod
    def require_privacy(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Нужно согласие на обработку персональных данных")
        return value

    @model_validator(mode="after")
    def strong_enough(self) -> "RegisterIn":
        err = password_error(self.password, email=str(self.email))
        if err:
            raise ValueError(err)
        return self


class LoginIn(BaseModel):
    model_config = _STRICT

    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class TelegramInitIn(BaseModel):
    model_config = _STRICT

    init_data: str = Field(min_length=10, max_length=4096)
    referral_code: str | None = Field(default=None, max_length=32)
    privacy_consent: bool = False


class TelegramLoginIn(BaseModel):
    model_config = _STRICT

    id: str = Field(min_length=1, max_length=32)
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: str
    hash: str
    referral_code: str | None = Field(default=None, max_length=32)
    privacy_consent: bool = False

    @field_validator("id", "auth_date", "first_name", "last_name", "username", "photo_url", mode="before")
    @classmethod
    def stringify(cls, value: object) -> str | None:
        if value is None:
            return None
        return str(value)


class RefreshIn(BaseModel):
    model_config = _STRICT

    refresh_token: str | None = Field(default=None, min_length=20, max_length=4096)


class LogoutIn(BaseModel):
    model_config = _STRICT

    refresh_token: str | None = Field(default=None, min_length=20, max_length=4096)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ProfilePatch(BaseModel):
    model_config = _STRICT

    name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)


class DeleteAccountIn(BaseModel):
    model_config = _STRICT

    confirm: Literal[True]
    password: str | None = Field(default=None, max_length=72)


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    name: str | None
    phone: str | None
    telegram_id: str | None
    referral_code: str
    bonus_balance: Decimal
    referred_by_id: UUID | None = None
    privacy_consented_at: datetime | None = None


class FavoriteIn(BaseModel):
    model_config = _STRICT

    product_id: UUID


class ViewIn(BaseModel):
    model_config = _STRICT

    product_id: UUID


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime


class UnreadNotificationsOut(BaseModel):
    unread: int = Field(ge=0)


class BonusExportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID | None
    level: int
    amount: Decimal
    created_at: datetime
    note: str | None = None


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None
    name: str | None
    phone: str | None
    telegram_id: str | None
    referral_code: str
    bonus_balance: Decimal
    is_active: bool
    created_at: datetime
    referred_by_id: UUID | None = None


class AdminUserPatch(BaseModel):
    model_config = _STRICT

    is_active: bool


class AdminBonusAdjust(BaseModel):
    model_config = _STRICT

    delta: Decimal
    note: str | None = Field(default=None, max_length=255)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class DataExportOut(BaseModel):
    exported_at: datetime
    privacy_policy_version: str | None
    profile: MeOut
    orders: list[OrderOut]
    favorite_product_ids: list[UUID]
    viewed_product_ids: list[UUID]
    notifications: list[NotificationOut]
    bonuses: list[BonusExportOut]
