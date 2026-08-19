from apps.api.models.order import AdminOrderStatus, CustomerOrderStatus, DeliveryType
from apps.api.services.orders import (
    apply_admin_status,
    cancel_order,
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
