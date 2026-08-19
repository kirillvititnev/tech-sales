"""Order creation rules and admin/customer status transitions."""

from __future__ import annotations

from apps.api.models.order import AdminOrderStatus, CustomerOrderStatus, DeliveryType

_ADMIN_ORDER = [
    AdminOrderStatus.accepted,
    AdminOrderStatus.paid,
    AdminOrderStatus.processing,
    AdminOrderStatus.assembled,
    AdminOrderStatus.shipped,
]


def validate_delivery(delivery_type: DeliveryType, delivery_address: str | None) -> str | None:
    """Return error message or None if OK."""
    address = (delivery_address or "").strip()
    if delivery_type == DeliveryType.cdek:
        if len(address) < 8:
            return "Для СДЭК укажите город и адрес пункта выдачи / доставки"
        return None
    if delivery_type == DeliveryType.pickup_moscow:
        return None
    return "Неизвестный тип доставки"


def validate_contacts(name: str, phone: str) -> str | None:
    if len(name.strip()) < 2:
        return "Укажите имя"
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 10:
        return "Укажите корректный телефон"
    return None


def apply_admin_status(
    *,
    delivery_type: DeliveryType,
    current_admin: AdminOrderStatus,
    current_customer: CustomerOrderStatus,
    new_admin: AdminOrderStatus,
) -> tuple[AdminOrderStatus, CustomerOrderStatus]:
    """Advance admin status by one step and mirror customer-facing status."""
    if current_customer == CustomerOrderStatus.cancelled:
        raise ValueError("Заказ уже отменён")

    if new_admin == current_admin:
        return current_admin, current_customer

    try:
        ci = _ADMIN_ORDER.index(current_admin)
        ni = _ADMIN_ORDER.index(new_admin)
    except ValueError as exc:
        raise ValueError("Неизвестный админ-статус") from exc

    if ni != ci + 1:
        raise ValueError(
            f"Нельзя сменить админ-статус с {current_admin.value} на {new_admin.value}"
        )

    customer = current_customer
    if new_admin == AdminOrderStatus.paid:
        customer = CustomerOrderStatus.paid
    elif new_admin == AdminOrderStatus.assembled and delivery_type == DeliveryType.pickup_moscow:
        customer = CustomerOrderStatus.ready
    elif new_admin == AdminOrderStatus.shipped:
        if delivery_type == DeliveryType.cdek:
            customer = CustomerOrderStatus.ready
        else:
            customer = CustomerOrderStatus.issued

    return new_admin, customer


def mark_issued(current_customer: CustomerOrderStatus) -> CustomerOrderStatus:
    if current_customer == CustomerOrderStatus.cancelled:
        raise ValueError("Заказ отменён")
    if current_customer not in {CustomerOrderStatus.paid, CustomerOrderStatus.ready}:
        raise ValueError("Нельзя отметить выданным в текущем статусе")
    return CustomerOrderStatus.issued


def cancel_order(current_customer: CustomerOrderStatus) -> CustomerOrderStatus:
    if current_customer in {CustomerOrderStatus.issued, CustomerOrderStatus.cancelled}:
        raise ValueError("Этот заказ нельзя отменить")
    return CustomerOrderStatus.cancelled
