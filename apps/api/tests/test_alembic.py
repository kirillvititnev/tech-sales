from alembic.script import ScriptDirectory

from apps.api.migrate import alembic_config


def test_alembic_head_is_baseline() -> None:
    script = ScriptDirectory.from_config(alembic_config())
    assert script.get_current_head() == "0001_baseline"


def test_alembic_linear_history() -> None:
    script = ScriptDirectory.from_config(alembic_config())
    revisions = list(script.walk_revisions())
    assert revisions[0].revision == "0001_baseline"
    assert revisions[0].down_revision is None
