"""Admin Telegram notification for a new storefront order."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.config import get_settings
from apps.api.models.catalog import ChannelStatus, ProductOffer, SupplierChannel
from apps.api.models.order import DeliveryType, Order

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LEN = 4096


@dataclass(frozen=True)
class SupplierQuote:
    channel_id: UUID
    title: str
    username: str | None
    price: Decimal


def format_rub(amount: Decimal | int | float) -> str:
    value = int(Decimal(str(amount)))
    return f"{value:,} ₽".replace(",", " ")


def cheapest_quotes(quotes: list[SupplierQuote], limit: int = 3) -> list[SupplierQuote]:
    """One quote per channel (min price), then the N cheapest."""
    by_channel: dict[UUID, SupplierQuote] = {}
    for quote in quotes:
        current = by_channel.get(quote.channel_id)
        if current is None or quote.price < current.price:
            by_channel[quote.channel_id] = quote
    ranked = sorted(by_channel.values(), key=lambda q: (q.price, q.title.lower()))
    return ranked[:limit]


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _delivery_label(order: Order) -> str:
    if order.delivery_type == DeliveryType.pickup_moscow:
        return "Самовывоз, Москва"
    if order.delivery_type == DeliveryType.cdek:
        return "СДЭК"
    return order.delivery_type.value


def _channel_label(quote: SupplierQuote) -> str:
    if quote.username:
        return f"{quote.title} (@{quote.username})"
    return quote.title


def format_admin_order_message(
    order: Order,
    quotes_by_product: dict[UUID, list[SupplierQuote]],
) -> str:
    lines: list[str] = [
        f"<b>Новый заказ { _esc(order.number) }</b>",
        "",
        "<b>Клиент</b>",
        f"Имя: {_esc(order.customer_name)}",
        f"Телефон: {_esc(order.customer_phone)}",
    ]
    if order.customer_telegram:
        lines.append(f"Telegram: {_esc(order.customer_telegram)}")
    lines.append(f"Доставка: {_esc(_delivery_label(order))}")
    if order.delivery_address:
        lines.append(f"Адрес: {_esc(order.delivery_address)}")
    if order.comment:
        lines.append(f"Комментарий: {_esc(order.comment)}")

    lines.extend(["", "<b>Состав</b>"])
    for index, item in enumerate(order.items, start=1):
        lines.append(
            f"{index}. {_esc(item.title)} × {item.quantity} — {format_rub(item.unit_price)}"
        )
        product_id = item.product_id
        quotes = cheapest_quotes(quotes_by_product.get(product_id, []) if product_id else [])
        if not quotes:
            lines.append("   Поставщики: нет активных офферов")
            continue
        lines.append("   Взять дешевле:")
        for rank, quote in enumerate(quotes, start=1):
            mark = " ← взять" if rank == 1 else ""
            lines.append(
                f"   {rank}. {_esc(_channel_label(quote))} — {format_rub(quote.price)}{mark}"
            )

    lines.extend(["", f"<b>Итого витрина: {format_rub(order.total_amount)}</b>"])
    return "\n".join(lines)


def split_telegram_chunks(text: str, limit: int = TELEGRAM_MAX_LEN) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    rest = text
    while rest:
        if len(rest) <= limit:
            chunks.append(rest)
            break
        cut = rest.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip("\n")
    return chunks


async def load_quotes_by_product(
    db: AsyncSession,
    product_ids: list[UUID],
) -> dict[UUID, list[SupplierQuote]]:
    ids = [pid for pid in product_ids if pid]
    if not ids:
        return {}
    min_price = func.min(ProductOffer.raw_price).label("price")
    result = await db.execute(
        select(
            ProductOffer.product_id,
            SupplierChannel.id,
            SupplierChannel.title,
            SupplierChannel.username,
            min_price,
        )
        .join(SupplierChannel, ProductOffer.channel_id == SupplierChannel.id)
        .where(
            ProductOffer.product_id.in_(ids),
            ProductOffer.is_active.is_(True),
            SupplierChannel.status != ChannelStatus.paused,
        )
        .group_by(
            ProductOffer.product_id,
            SupplierChannel.id,
            SupplierChannel.title,
            SupplierChannel.username,
        )
    )
    by_product: dict[UUID, list[SupplierQuote]] = defaultdict(list)
    for product_id, channel_id, title, username, price in result.all():
        if product_id is None:
            continue
        by_product[product_id].append(
            SupplierQuote(
                channel_id=channel_id,
                title=title,
                username=username,
                price=Decimal(price),
            )
        )
    return dict(by_product)


def telegram_http_client() -> httpx.AsyncClient:
    # anyio/httpx may pick IPv6 first; Telegram IPv6 often fails behind consumer VPNs.
    transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
    return httpx.AsyncClient(timeout=12.0, transport=transport)


async def send_telegram_text(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with telegram_http_client() as client:
        for chunk in split_telegram_chunks(text):
            response = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            if response.status_code >= 400:
                logger.error(
                    "Telegram notify failed chat=%s status=%s body=%s",
                    chat_id,
                    response.status_code,
                    response.text[:500],
                )
                response.raise_for_status()


async def deliver_admin_order_text(text: str) -> None:
    settings = get_settings()
    token = settings.telegram_bot_token
    chat_ids = settings.admin_telegram_chat_ids
    if not token or not chat_ids:
        logger.warning("Admin order notify skipped: TELEGRAM_BOT_TOKEN or ADMIN_TELEGRAM_CHAT_ID missing")
        return
    for chat_id in chat_ids:
        try:
            await send_telegram_text(token, chat_id, text)
        except Exception:
            logger.exception("Admin order notify failed for chat %s", chat_id)


async def build_admin_order_message(db: AsyncSession, order: Order) -> str:
    product_ids = [item.product_id for item in order.items if item.product_id]
    quotes = await load_quotes_by_product(db, product_ids)
    return format_admin_order_message(order, quotes)
