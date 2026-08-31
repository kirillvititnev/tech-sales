"""Deliver the same cabinet notices to the customer Telegram bot chat."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Protocol
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import get_settings
from apps.api.models.account import UserNotification
from apps.api.models.user import User
from apps.api.services.order_notify import send_telegram_text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CustomerTelegram:
    chat_id: str
    title: str
    body: str


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def format_customer_telegram(title: str, body: str) -> str:
    heading = _esc((title or "").strip() or "White Shop")
    detail = _esc((body or "").strip())
    if detail:
        return f"<b>{heading}</b>\n{detail}"
    return f"<b>{heading}</b>"


class NotificationCopy(Protocol):
    user_id: UUID
    title: str
    body: str


def telegrams_for_notices(
    notices: Iterable[NotificationCopy],
    chats: dict[UUID, str],
) -> list[CustomerTelegram]:
    """Match cabinet notices to Telegram chats. Skip empty copy and missing chats."""
    out: list[CustomerTelegram] = []
    for notice in notices:
        chat_id = chats.get(notice.user_id)
        if not chat_id:
            continue
        title = (notice.title or "").strip()
        body = (notice.body or "").strip()
        if not title and not body:
            continue
        out.append(CustomerTelegram(chat_id=chat_id, title=title, body=body))
    return out


async def customer_telegrams_for(
    db: AsyncSession,
    notices: list[UserNotification],
) -> list[CustomerTelegram]:
    """Resolve chat ids. Only active users who already linked Telegram."""
    user_ids = {notice.user_id for notice in notices if notice.user_id}
    if not user_ids:
        return []
    rows = await db.execute(
        select(User.id, User.telegram_id).where(User.id.in_(user_ids), User.is_active.is_(True))
    )
    chats: dict[UUID, str] = {}
    for user_id, telegram_id in rows.all():
        chat = str(telegram_id or "").strip()
        if chat:
            chats[user_id] = chat
    return telegrams_for_notices(notices, chats)


async def deliver_customer_telegrams(messages: list[CustomerTelegram]) -> None:
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token or not messages:
        return
    for message in messages:
        text = format_customer_telegram(message.title, message.body)
        try:
            await send_telegram_text(token, message.chat_id, text)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status in {400, 403, 404}:
                logger.info("Customer telegram skipped chat=%s status=%s", message.chat_id, status)
                continue
            logger.exception("Customer telegram failed chat=%s", message.chat_id)
        except Exception:
            logger.exception("Customer telegram failed chat=%s", message.chat_id)
