from uuid import uuid4

from pydantic import ValidationError

from apps.api.models.order import AdminOrderStatus, CustomerOrderStatus, DeliveryType
from apps.api.schemas.order import OrderCreate
from apps.api.services.orders import (
    apply_admin_status,
    cancel_order,
    customer_status_notice,
    mark_issued,
    validate_contacts,
    validate_delivery,
)


def test_cdek_requires_address() -> None:
    assert validate_delivery(DeliveryType.cdek, None) is not None
    assert validate_delivery(DeliveryType.cdek, "Москва") is not None
    assert validate_delivery(DeliveryType.cdek, "Москва, ПВЗ СДЭК на Ленина 10") is None


def test_pickup_ok_without_address() -> None:
    assert validate_delivery(DeliveryType.pickup_moscow, None) is None


def test_contacts() -> None:
    assert validate_contacts("A", "79001112233") is not None
    assert validate_contacts("Иван", "123") is not None
    assert validate_contacts("Иван", "+7 (900) 111-22-33") is None


def test_admin_paid_mirrors_customer() -> None:
    admin, customer = apply_admin_status(
        delivery_type=DeliveryType.pickup_moscow,
        current_admin=AdminOrderStatus.accepted,
        current_customer=CustomerOrderStatus.placed,
        new_admin=AdminOrderStatus.paid,
    )
    assert admin == AdminOrderStatus.paid
    assert customer == CustomerOrderStatus.paid


def test_pickup_assembled_ready() -> None:
    # advance to assembled
    admin, customer = AdminOrderStatus.accepted, CustomerOrderStatus.placed
    for nxt in (
        AdminOrderStatus.paid,
        AdminOrderStatus.processing,
        AdminOrderStatus.assembled,
    ):
        admin, customer = apply_admin_status(
            delivery_type=DeliveryType.pickup_moscow,
            current_admin=admin,
            current_customer=customer,
            new_admin=nxt,
        )
    assert admin == AdminOrderStatus.assembled
    assert customer == CustomerOrderStatus.ready


def test_cdek_shipped_ready() -> None:
    admin, customer = AdminOrderStatus.accepted, CustomerOrderStatus.placed
    for nxt in (
        AdminOrderStatus.paid,
        AdminOrderStatus.processing,
        AdminOrderStatus.assembled,
        AdminOrderStatus.shipped,
    ):
        admin, customer = apply_admin_status(
            delivery_type=DeliveryType.cdek,
            current_admin=admin,
            current_customer=customer,
            new_admin=nxt,
        )
    assert customer == CustomerOrderStatus.ready


def test_cannot_skip_admin_status() -> None:
    try:
        apply_admin_status(
            delivery_type=DeliveryType.cdek,
            current_admin=AdminOrderStatus.accepted,
            current_customer=CustomerOrderStatus.placed,
            new_admin=AdminOrderStatus.processing,
        )
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_cancel_and_issue() -> None:
    assert cancel_order(CustomerOrderStatus.placed) == CustomerOrderStatus.cancelled
    assert mark_issued(CustomerOrderStatus.ready) == CustomerOrderStatus.issued


def test_customer_status_notice_skips_guest_and_noop() -> None:
    assert (
        customer_status_notice(
            user_id=None,
            number="WS-1",
            previous=CustomerOrderStatus.placed,
            new_status=CustomerOrderStatus.paid,
        )
        is None
    )
    notice = customer_status_notice(
        user_id=uuid4(),
        number="WS-1",
        previous=CustomerOrderStatus.placed,
        new_status=CustomerOrderStatus.paid,
    )
    assert notice is not None
    assert "Оплачен" in notice.body


def _order_payload(**overrides: object) -> dict:
    data: dict = {
        "customer_name": "Иван Иванов",
        "customer_phone": "+79001112233",
        "delivery_type": "pickup_moscow",
        "privacy_consent": True,
        "items": [{"product_id": str(uuid4()), "quantity": 1}],
    }
    data.update(overrides)
    return data


def test_order_requires_privacy_consent() -> None:
    OrderCreate.model_validate(_order_payload())
    try:
        OrderCreate.model_validate(_order_payload(privacy_consent=False))
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
    payload = _order_payload()
    del payload["privacy_consent"]
    try:
        OrderCreate.model_validate(payload)
        raise AssertionError("expected ValidationError")
    except ValidationError:
        pass
