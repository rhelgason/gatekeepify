"""Guards that `alembic upgrade head` produces a schema matching app/models.py.

The deploy builds the schema via Base.metadata.create_all + the startup
incremental-column helper, while Alembic is kept in sync as the version-controlled
source of truth. This test fails if the two ever drift apart again.
"""

import os
import tempfile

import sqlalchemy as sa

from app.database import Base


def _alembic_schema(db_url: str) -> dict[str, set[str]]:
    from alembic import command
    from alembic.config import Config

    from app.config import settings

    original = settings.database_url
    settings.database_url = db_url  # env.py reads settings.database_url at runtime
    try:
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")
    finally:
        settings.database_url = original

    insp = sa.inspect(sa.create_engine(db_url))
    return {t: {c["name"] for c in insp.get_columns(t)} for t in insp.get_table_names()}


def _model_schema() -> dict[str, set[str]]:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    insp = sa.inspect(engine)
    return {t: {c["name"] for c in insp.get_columns(t)} for t in insp.get_table_names()}


def test_add_index_if_missing_is_idempotent_and_validates():
    import pytest

    from app.main import _add_index_if_missing

    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE t (user_id TEXT, ts TEXT)"))

    def _indexes() -> set[str]:
        return {ix["name"] for ix in sa.inspect(engine).get_indexes("t")}

    assert "ix_t_user_ts" not in _indexes()
    _add_index_if_missing(engine, "ix_t_user_ts", "t", ["user_id", "ts"])
    assert "ix_t_user_ts" in _indexes()
    # Second call must be a no-op, not an error.
    _add_index_if_missing(engine, "ix_t_user_ts", "t", ["user_id", "ts"])
    assert "ix_t_user_ts" in _indexes()

    # Identifier validation guards against injection.
    with pytest.raises(ValueError):
        _add_index_if_missing(engine, "bad name", "t", ["user_id"])
    with pytest.raises(ValueError):
        _add_index_if_missing(engine, "ix_ok", "t", ["user_id; DROP TABLE t"])


def test_alembic_head_matches_model():
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "alembic_check.db")
        alembic = _alembic_schema(f"sqlite:///{db_path}")

    model = _model_schema()

    # Every model table must exist in the alembic-built schema with the same columns.
    # (alembic_version is alembic's own bookkeeping table; ignore it.)
    alembic.pop("alembic_version", None)
    assert set(model) == set(alembic), (
        f"table drift: model-only={set(model) - set(alembic)}, "
        f"alembic-only={set(alembic) - set(model)}"
    )
    for table in model:
        assert model[table] == alembic[table], (
            f"column drift in {table}: model-only={model[table] - alembic[table]}, "
            f"alembic-only={alembic[table] - model[table]}"
        )
