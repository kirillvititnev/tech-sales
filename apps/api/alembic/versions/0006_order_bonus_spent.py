"""Store bonus amount spent on an order."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0006_order_bonus_spent"
down_revision: Union[str, Sequence[str], None] = "0005_markup_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "orders" not in inspector.get_table_names():
        return
    if "bonus_spent" in _column_names(inspector, "orders"):
        return
    op.add_column(
        "orders",
        sa.Column(
            "bonus_spent",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    raise NotImplementedError("Order bonus spend schema is not rolled back")
