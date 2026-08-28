"""Run Alembic to head. Used at API startup instead of create_all."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

INI_PATH = Path(__file__).resolve().parent / "alembic.ini"


def alembic_config() -> Config:
    return Config(str(INI_PATH))


def run_migrations() -> None:
    command.upgrade(alembic_config(), "head")
