from __future__ import annotations

from decimal import Decimal

from apps.api.services.order_notify import deliver_admin_order_text, format_rub


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

PRICE_JUMP_RATIO = Decimal("0.20")
PRICE_JUMP_MIN_RUB = Decimal("2000")
MAX_JUMP_LINES = 12
MAX_ERROR_LINES = 8


def is_price_jump(old: Decimal | None, new: Decimal | None) -> bool:
    if old is None or new is None:
        return False
    if old <= 0 or new <= 0:
        return False
    delta = abs(new - old)
    return delta >= PRICE_JUMP_MIN_RUB and (delta / old) >= PRICE_JUMP_RATIO


def format_ops_alert(
    *,
    folder: str,
    errors: list[tuple[str, str]],
    jumps: list[tuple[str, Decimal, Decimal]],
) -> str | None:
    if not errors and not jumps:
        return None
    lines = [f"<b>Парсинг: {_esc(folder)}</b>", ""]
    if errors:
        lines.append("<b>Ошибки каналов</b>")
        for title, err in errors[:MAX_ERROR_LINES]:
            snippet = _esc(err.replace("\n", " ").strip()[:180])
            lines.append(f"• {_esc(title)}: {snippet}")
        extra = len(errors) - MAX_ERROR_LINES
        if extra > 0:
            lines.append(f"… ещё {extra}")
        lines.append("")
    if jumps:
        lines.append("<b>Скачок витринной цены</b>")
        for title, old, new in jumps[:MAX_JUMP_LINES]:
            direction = "↑" if new > old else "↓"
            lines.append(f"• {_esc(title)}: {format_rub(old)} → {format_rub(new)} {direction}")
        extra = len(jumps) - MAX_JUMP_LINES
        if extra > 0:
            lines.append(f"… ещё {extra}")
    return "\n".join(lines).strip()


async def notify_admin_ops(
    folder: str,
    errors: list[tuple[str, str]],
    jumps: list[tuple[str, Decimal, Decimal]],
) -> None:
    text = format_ops_alert(folder=folder, errors=errors, jumps=jumps)
    if not text:
        return
    await deliver_admin_order_text(text)
