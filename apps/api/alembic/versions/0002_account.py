"""Account tables and referral percents on store_settings.

Idempotent: create_all for new tables; add missing columns on existing volumes.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

from apps.api.db import Base
from apps.api import models as _models  # noqa: F401

revision: str = "0002_account"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REFERRAL_COLUMNS = (
    ("referral_percent_l1", "5"),
    ("referral_percent_l2", "2"),
    ("referral_percent_l3", "1"),
)


def _column_names(inspector: sa.Inspector, table: str) -> set[str]:
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    inspector = inspect(bind)
    columns = _column_names(inspector, "store_settings")
    for name, default in _REFERRAL_COLUMNS:
        if name in columns:
            continue
        op.add_column(
            "store_settings",
            sa.Column(
                name,
                sa.Numeric(6, 2),
                nullable=False,
                server_default=default,
            ),
        )


def downgrade() -> None:
    raise NotImplementedError("Account schema is not rolled back")
