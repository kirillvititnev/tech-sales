"""Nullable bonus ledger rows for admin adjustments."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0004_admin_users"
down_revision: Union[str, Sequence[str], None] = "0003_auth_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "bonus_ledger" not in inspector.get_table_names():
        return
    columns = _column_names(inspector, "bonus_ledger")
    if "note" not in columns:
        op.add_column("bonus_ledger", sa.Column("note", sa.String(length=255), nullable=True))
    op.alter_column("bonus_ledger", "order_id", existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    raise NotImplementedError("Admin users schema is not rolled back")
