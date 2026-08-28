"""Idempotent baseline matching current SQLAlchemy models.

Safe on a blank database and on volumes that were created with metadata.create_all.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

from apps.api.db import Base
from apps.api import models as _models  # noqa: F401
from apps.api.security import new_order_access_token

revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def _has_unique_on(inspector: sa.Inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    for index in inspector.get_indexes(table):
        if index.get("unique") and list(index.get("column_names") or []) == [column]:
            return True
    for constraint in inspector.get_unique_constraints(table):
        if list(constraint.get("column_names") or []) == [column]:
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    inspector = inspect(bind)
    columns = _column_names(inspector, "orders")
    if "access_token" not in columns:
        op.add_column("orders", sa.Column("access_token", sa.String(length=64), nullable=True))
    if "privacy_consented_at" not in columns:
        op.add_column(
            "orders",
            sa.Column("privacy_consented_at", sa.DateTime(timezone=True), nullable=True),
        )

    missing = bind.execute(text("SELECT id FROM orders WHERE access_token IS NULL")).fetchall()
    for (order_id,) in missing:
        bind.execute(
            text("UPDATE orders SET access_token = :tok WHERE id = :id"),
            {"tok": new_order_access_token(), "id": order_id},
        )
    op.alter_column("orders", "access_token", existing_type=sa.String(length=64), nullable=False)

    inspector = inspect(bind)
    if not _has_unique_on(inspector, "orders", "access_token"):
        op.create_index("ix_orders_access_token", "orders", ["access_token"], unique=True)


def downgrade() -> None:
    raise NotImplementedError("Baseline schema is not rolled back")
