from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from pydantic import ValidationError

from apps.api.schemas.account import UnreadNotificationsOut
from apps.api.services.customer_notify import (
    CustomerTelegram,
    deliver_customer_telegrams,
    format_customer_telegram,
    telegrams_for_notices,
)


def test_format_customer_telegram_escapes_html() -> None:
    text = format_customer_telegram("Цена <hot>", "было 10 & 20 > 5")
    assert text.startswith("<b>Цена &lt;hot&gt;</b>")
    assert "&amp;" in text
    assert "&gt;" in text
    assert "<hot>" not in text


def test_format_customer_telegram_title_only() -> None:
    assert format_customer_telegram("White Shop", "  ") == "<b>White Shop</b>"


def test_telegrams_skip_missing_chat_and_empty_copy() -> None:
    linked = uuid4()
    guest = uuid4()
    notices = [
        SimpleNamespace(user_id=linked, title="Заказ WS-1", body="Статус: Оплачен"),
        SimpleNamespace(user_id=guest, title="Заказ WS-2", body="Статус: Оплачен"),
        SimpleNamespace(user_id=linked, title="  ", body="  "),
    ]
    jobs = telegrams_for_notices(notices, {linked: "1001"})
    assert jobs == [CustomerTelegram(chat_id="1001", title="Заказ WS-1", body="Статус: Оплачен")]


def test_unread_count_rejects_negative() -> None:
    UnreadNotificationsOut(unread=0)
    UnreadNotificationsOut(unread=3)
    try:
        UnreadNotificationsOut(unread=-1)
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass


async def test_deliver_skips_when_bot_token_missing() -> None:
    with (
        patch("apps.api.services.customer_notify.get_settings") as settings,
        patch("apps.api.services.customer_notify.send_telegram_text", new=AsyncMock()) as send,
    ):
        settings.return_value.telegram_bot_token = None
        await deliver_customer_telegrams(
            [CustomerTelegram(chat_id="1", title="Hi", body="Body")]
        )
        send.assert_not_called()


async def test_deliver_skips_forbidden_chat() -> None:
    request = httpx.Request("POST", "https://api.telegram.org/botx/sendMessage")
    response = httpx.Response(403, request=request)
    err = httpx.HTTPStatusError("forbidden", request=request, response=response)
    with (
        patch("apps.api.services.customer_notify.get_settings") as settings,
        patch(
            "apps.api.services.customer_notify.send_telegram_text",
            new=AsyncMock(side_effect=err),
        ) as send,
    ):
        settings.return_value.telegram_bot_token = "token"
        await deliver_customer_telegrams(
            [CustomerTelegram(chat_id="1", title="Hi", body="Body")]
        )
        send.assert_awaited_once()
