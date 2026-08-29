"""Per-brand/category/kind markup rules on store settings."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0005_markup_rules"
down_revision: Union[str, Sequence[str], None] = "0004_admin_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "store_settings" not in inspector.get_table_names():
        return
    if "markup_rules" in _column_names(inspector, "store_settings"):
        return
    op.add_column(
        "store_settings",
        sa.Column(
            "markup_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    raise NotImplementedError("Markup rules schema is not rolled back")
