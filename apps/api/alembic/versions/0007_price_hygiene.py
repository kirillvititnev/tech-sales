"""Price hygiene: last sync stats and per-channel median eligibility."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0007_price_hygiene"
down_revision: Union[str, Sequence[str], None] = "0006_order_bonus_spent"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    names = inspector.get_table_names()
    if "store_settings" in names and "last_sync_stats" not in _column_names(inspector, "store_settings"):
        op.add_column(
            "store_settings",
            sa.Column(
                "last_sync_stats",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
    inspector = inspect(bind)
    if "supplier_channels" in names and "counts_toward_price" not in _column_names(
        inspector, "supplier_channels"
    ):
        op.add_column(
            "supplier_channels",
            sa.Column(
                "counts_toward_price",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )


def downgrade() -> None:
    raise NotImplementedError("Price hygiene schema is not rolled back")
