"""Sync alembic history with model drift handled at startup

Brings `alembic upgrade head` in line with app/models.py by adding the columns
that had only ever been applied at runtime via main._run_schema_migrations()
(idempotent ALTER TABLE). Each add is guarded by an inspector check so this
migration is safe to run on:
  - a fresh DB built by 001..005 (columns added here), and
  - an existing production DB already carrying these columns (no-ops).

Revision ID: 006
Revises: 005
Create Date: 2026-06-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column, SQLAlchemy type, kwargs) — mirrors the startup helper's set.
_COLUMNS = [
    ("dim_all_tracks", "enrich_attempts", sa.Integer, {"server_default": "0"}),
    ("dim_all_users", "image_url", sa.String(512), {"nullable": True}),
    ("dim_all_users", "token_invalidated_at", sa.DateTime, {"nullable": True}),
    ("dim_all_users", "is_admin", sa.Boolean, {"server_default": sa.false()}),
    ("dim_all_listens", "ms_played", sa.Integer, {"nullable": True}),
    ("friend_invites", "to_user_id", sa.String(255), {"nullable": True}),
    ("job_runs", "details", sa.Text, {"nullable": True}),
]


def _existing_columns(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    for table, column, col_type, kwargs in _COLUMNS:
        if column not in _existing_columns(bind, table):
            op.add_column(table, sa.Column(column, col_type, **kwargs))


def downgrade() -> None:
    bind = op.get_bind()
    for table, column, _col_type, _kwargs in reversed(_COLUMNS):
        if column in _existing_columns(bind, table):
            op.drop_column(table, column)
