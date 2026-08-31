from alembic.script import ScriptDirectory

from apps.api.migrate import alembic_config


def test_alembic_head_is_account() -> None:
    script = ScriptDirectory.from_config(alembic_config())
    assert script.get_current_head() == "0007_price_hygiene"


def test_alembic_linear_history() -> None:
    script = ScriptDirectory.from_config(alembic_config())
    revisions = list(script.walk_revisions())
    assert [item.revision for item in revisions] == [
        "0007_price_hygiene",
        "0006_order_bonus_spent",
        "0005_markup_rules",
        "0004_admin_users",
        "0003_auth_hardening",
        "0002_account",
        "0001_baseline",
    ]
    assert revisions[-1].down_revision is None
