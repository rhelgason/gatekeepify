"""Add friendships and friend_invites tables

Revision ID: 002
Revises: 001
Create Date: 2025-05-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "friendships",
        sa.Column(
            "user_id_1",
            sa.String(255),
            sa.ForeignKey("dim_all_users.user_id"),
            primary_key=True,
        ),
        sa.Column(
            "user_id_2",
            sa.String(255),
            sa.ForeignKey("dim_all_users.user_id"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "friend_invites",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "from_user_id",
            sa.String(255),
            sa.ForeignKey("dim_all_users.user_id"),
            nullable=False,
        ),
        sa.Column("invite_code", sa.String(64), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column(
            "accepted_by_user_id",
            sa.String(255),
            sa.ForeignKey("dim_all_users.user_id"),
            nullable=True,
        ),
        sa.Column("accepted_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_invite_code", "friend_invites", ["invite_code"])


def downgrade() -> None:
    op.drop_index("ix_invite_code", table_name="friend_invites")
    op.drop_table("friend_invites")
    op.drop_table("friendships")
