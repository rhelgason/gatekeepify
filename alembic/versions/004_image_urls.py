"""Add image_url to albums, tracks, artists

Revision ID: 004
Revises: 003
Create Date: 2025-05-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("dim_all_albums", sa.Column("image_url", sa.String(512), nullable=True))
    op.add_column("dim_all_tracks", sa.Column("image_url", sa.String(512), nullable=True))
    op.add_column("dim_all_artists", sa.Column("image_url", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("dim_all_artists", "image_url")
    op.drop_column("dim_all_tracks", "image_url")
    op.drop_column("dim_all_albums", "image_url")
