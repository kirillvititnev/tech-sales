from types import SimpleNamespace

from apps.api.schemas.account import TokenOut
from apps.api.services.auth_cookies import COOKIE_PATH, REFRESH_COOKIE, cookie_secure
from apps.api.services.privacy import REDACTED_NAME, REDACTED_PHONE, redact_order


def test_refresh_cookie_is_host_only_auth_path() -> None:
    assert REFRESH_COOKIE == "whiteshop_refresh"
    assert COOKIE_PATH == "/api/v1/auth"


def test_cookie_secure_follows_forwarded_proto() -> None:
    from starlette.requests import Request

    def req(headers: list[tuple[bytes, bytes]], scheme: str = "http") -> Request:
        return Request(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": scheme,
                "path": "/api/v1/auth/login",
                "raw_path": b"/api/v1/auth/login",
                "query_string": b"",
                "headers": headers,
                "client": ("127.0.0.1", 1),
                "server": ("127.0.0.1", 8000),
            }
        )

    assert cookie_secure(req([])) is False
    assert cookie_secure(req([(b"x-forwarded-proto", b"https")])) is True
    assert cookie_secure(req([(b"host", b"whiteshop.tech")])) is True


def test_erasure_placeholders_are_not_real_contacts() -> None:
    assert REDACTED_NAME
    assert REDACTED_PHONE == "00000000000"
    assert "+" not in REDACTED_PHONE


def test_redact_order_clears_pii_and_rotates_access() -> None:
    order = SimpleNamespace(
        customer_name="Анна",
        customer_phone="+79001112233",
        customer_telegram="@anna",
        delivery_address="Москва, Ленина 1",
        comment="позвонить",
        access_token="old-access-token-value-32chars!",
    )
    redact_order(order)
    assert order.customer_name == REDACTED_NAME
    assert order.customer_phone == REDACTED_PHONE
    assert order.customer_telegram is None
    assert order.delivery_address is None
    assert order.comment is None
    assert order.access_token != "old-access-token-value-32chars!"
    assert len(order.access_token) >= 32


def test_token_json_omits_refresh() -> None:
    payload = TokenOut(access_token="a" * 40, refresh_token="r" * 40, expires_in=900).model_dump(
        exclude={"refresh_token"}
    )
    assert "access_token" in payload
    assert "refresh_token" not in payload
