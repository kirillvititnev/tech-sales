from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from apps.api.models.order import (
    AdminOrderStatus,
    CustomerOrderStatus,
    DeliveryType,
    Order,
    OrderItem,
)
from apps.api.services.order_notify import (
    SupplierQuote,
    cheapest_quotes,
    deliver_admin_order_text,
    format_admin_order_message,
    format_rub,
    send_telegram_text,
    split_telegram_chunks,
)


def test_format_rub_groups_thousands() -> None:
    assert format_rub(Decimal("99900")) == "99 900 ₽"


def test_cheapest_one_per_channel_then_three() -> None:
    top_id, global_id, bests_id, extra_id = uuid4(), uuid4(), uuid4(), uuid4()
    quotes = [
        SupplierQuote(top_id, "Top re:sale", None, Decimal("100000")),
        SupplierQuote(top_id, "Top re:sale", None, Decimal("98000")),
        SupplierQuote(global_id, "Global Market Channel", "globalmarket_opt", Decimal("99500")),
        SupplierQuote(bests_id, "Bests re:sale", None, Decimal("110000")),
        SupplierQuote(extra_id, "Unisale", None, Decimal("200000")),
    ]
    ranked = cheapest_quotes(quotes, limit=3)
    assert [q.title for q in ranked] == ["Top re:sale", "Global Market Channel", "Bests re:sale"]
    assert ranked[0].price == Decimal("98000")
    assert ranked[1].username == "globalmarket_opt"


def test_admin_message_has_contacts_lines_and_cheapest_mark() -> None:
    product_id = uuid4()
    item = OrderItem(
        product_id=product_id,
        title="iPhone 17 Pro · 256GB · Deep Blue · eSIM",
        unit_price=Decimal("99900"),
        quantity=2,
    )
    order = Order(
        number="WS-TEST01",
        customer_name="Иван <test>",
        customer_phone="+7 (900) 111-22-33",
        customer_telegram="@ivan",
        customer_status=CustomerOrderStatus.placed,
        admin_status=AdminOrderStatus.accepted,
        delivery_type=DeliveryType.cdek,
        delivery_address="Москва, ПВЗ СДЭК на Ленина 10",
        comment="после 18",
        total_amount=Decimal("199800"),
        items=[item],
    )
    cheap = uuid4()
    mid = uuid4()
    quotes = {
        product_id: [
            SupplierQuote(mid, "Bests re:sale", None, Decimal("102000")),
            SupplierQuote(cheap, "Top re:sale", None, Decimal("98000")),
        ]
    }
    text = format_admin_order_message(order, quotes)
    assert "WS-TEST01" in text
    assert "Иван &lt;test&gt;" in text
    assert "+7 (900) 111-22-33" in text
    assert "@ivan" in text
    assert "СДЭК" in text
    assert "Ленина 10" in text
    assert "после 18" in text
    assert "× 2 — 99 900 ₽" in text
    assert "Top re:sale — 98 000 ₽ ← взять" in text
    assert "Bests re:sale — 102 000 ₽" in text
    assert "199 800 ₽" in text


def test_no_offers_line() -> None:
    product_id = uuid4()
    item = OrderItem(product_id=product_id, title="Ручной товар", unit_price=Decimal("10000"), quantity=1)
    order = Order(
        number="WS-X",
        customer_name="Анна",
        customer_phone="79001112233",
        customer_status=CustomerOrderStatus.placed,
        admin_status=AdminOrderStatus.accepted,
        delivery_type=DeliveryType.pickup_moscow,
        total_amount=Decimal("10000"),
        items=[item],
    )
    text = format_admin_order_message(order, {})
    assert "нет активных офферов" in text
    assert "Самовывоз" in text


def test_split_long_telegram_text() -> None:
    body = "\n".join(f"line {i}" for i in range(500))
    chunks = split_telegram_chunks(body, limit=200)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    assert "line 0" in chunks[0]


async def test_deliver_skips_without_credentials() -> None:
    with (
        patch("apps.api.services.order_notify.get_settings") as settings_mock,
        patch("apps.api.services.order_notify.send_telegram_text", new_callable=AsyncMock) as send,
    ):
        settings_mock.return_value.telegram_bot_token = None
        settings_mock.return_value.admin_telegram_chat_ids = ["1"]
        await deliver_admin_order_text("hello")
        send.assert_not_called()


async def test_send_telegram_binds_ipv4() -> None:
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    with (
        patch("apps.api.services.order_notify.httpx.AsyncHTTPTransport") as transport_cls,
        patch("apps.api.services.order_notify.httpx.AsyncClient", return_value=mock_client) as client_cls,
    ):
        await send_telegram_text("token", "1", "hello")
    transport_cls.assert_called_once_with(local_address="0.0.0.0")
    assert client_cls.call_args.kwargs["transport"] is transport_cls.return_value
    mock_client.post.assert_awaited()
