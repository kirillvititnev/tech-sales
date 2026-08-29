"""Token revocation, consent columns, refresh-token table.

Idempotent: create_all for new tables; add missing columns on existing volumes.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from apps.api.db import Base
from apps.api import models as _models  # noqa: F401

revision: str = "0003_auth_hardening"
down_revision: Union[str, Sequence[str], None] = "0002_account"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_USER_COLUMNS = (
    ("token_version", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0")),
    ("privacy_consented_at", sa.Column("privacy_consented_at", sa.DateTime(timezone=True), nullable=True)),
    (
        "privacy_policy_version",
        sa.Column("privacy_policy_version", sa.String(length=32), nullable=True),
    ),
)


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    inspector = inspect(bind)
    columns = _column_names(inspector, "users")
    for name, column in _USER_COLUMNS:
        if name in columns:
            continue
        op.add_column("users", column)


def downgrade() -> None:
    raise NotImplementedError("Auth hardening schema is not rolled back")
