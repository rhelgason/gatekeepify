"""Add award_snapshots table

Revision ID: 005
Revises: 004
Create Date: 2025-05-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "award_snapshots",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("dim_all_users.user_id"),
            nullable=False,
        ),
        sa.Column("friend_group_hash", sa.String(64), nullable=False),
        sa.Column("award_id", sa.String(50), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("stat_value", sa.Float, nullable=True),
        sa.Column("stat_detail", sa.Text, nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("entity_name", sa.String(255), nullable=True),
        sa.Column("computed_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "friend_group_hash", "award_id"),
    )
    op.create_index(
        "ix_award_user_group", "award_snapshots", ["user_id", "friend_group_hash"]
    )
    op.create_index(
        "ix_award_group_award", "award_snapshots", ["friend_group_hash", "award_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_award_group_award", table_name="award_snapshots")
    op.drop_index("ix_award_user_group", table_name="award_snapshots")
    op.drop_table("award_snapshots")
