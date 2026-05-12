"""Add audit_log table

Revision ID: 003
Revises: 002
Create Date: 2025-05-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime, nullable=False),
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("dim_all_users.user_id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("details", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="success"),
    )
    op.create_index("ix_audit_action", "audit_log", ["action"])
    op.create_index("ix_audit_user_ts", "audit_log", ["user_id", "ts"])
    op.create_index("ix_audit_action_ts", "audit_log", ["action", "ts"])


def downgrade() -> None:
    op.drop_index("ix_audit_action_ts", table_name="audit_log")
    op.drop_index("ix_audit_user_ts", table_name="audit_log")
    op.drop_index("ix_audit_action", table_name="audit_log")
    op.drop_table("audit_log")
