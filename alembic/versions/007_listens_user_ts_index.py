"""Add ix_listens_user_ts index for per-user time-window queries

Revision ID: 007
Revises: 006
Create Date: 2026-06-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEX = "ix_listens_user_ts"
_TABLE = "dim_all_listens"


def _index_exists(bind) -> bool:
    return _INDEX in {ix["name"] for ix in sa.inspect(bind).get_indexes(_TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _index_exists(bind):
        op.create_index(_INDEX, _TABLE, ["user_id", "ts"])


def downgrade() -> None:
    bind = op.get_bind()
    if _index_exists(bind):
        op.drop_index(_INDEX, table_name=_TABLE)
