"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-05-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dim_all_albums",
        sa.Column("album_id", sa.String(255), primary_key=True),
        sa.Column("album_name", sa.String(255), nullable=True),
        sa.Column("release_date", sa.Date, nullable=True),
    )

    op.create_table(
        "dim_all_tracks",
        sa.Column("track_id", sa.String(255), primary_key=True),
        sa.Column("track_name", sa.String(255), nullable=True),
        sa.Column(
            "album_id",
            sa.String(255),
            sa.ForeignKey("dim_all_albums.album_id"),
            nullable=True,
        ),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("is_local", sa.Boolean, nullable=True),
    )

    op.create_table(
        "dim_all_artists",
        sa.Column("artist_id", sa.String(255), primary_key=True),
        sa.Column("artist_name", sa.String(255), nullable=True),
    )

    op.create_table(
        "track_to_artist",
        sa.Column(
            "track_id",
            sa.String(255),
            sa.ForeignKey("dim_all_tracks.track_id"),
            primary_key=True,
        ),
        sa.Column(
            "artist_id",
            sa.String(255),
            sa.ForeignKey("dim_all_artists.artist_id"),
            primary_key=True,
        ),
    )

    op.create_table(
        "artist_to_genre",
        sa.Column(
            "artist_id",
            sa.String(255),
            sa.ForeignKey("dim_all_artists.artist_id"),
            primary_key=True,
        ),
        sa.Column("genre", sa.String(255), primary_key=True),
    )

    op.create_table(
        "dim_all_users",
        sa.Column("user_id", sa.String(255), primary_key=True),
        sa.Column("user_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("spotify_refresh_token", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("last_poll_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "dim_all_listens",
        sa.Column("ts", sa.DateTime, primary_key=True),
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("dim_all_users.user_id"),
            primary_key=True,
        ),
        sa.Column(
            "track_id",
            sa.String(255),
            sa.ForeignKey("dim_all_tracks.track_id"),
            primary_key=True,
        ),
        sa.Column("source", sa.String(10), server_default="api"),
        sa.Column("export_metadata", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_listens_user_track", "dim_all_listens", ["user_id", "track_id"]
    )
    op.create_index(
        "ix_listens_track_ts", "dim_all_listens", ["track_id", "ts"]
    )

    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("job_name", sa.String(255), nullable=False),
        sa.Column(
            "user_id",
            sa.String(255),
            sa.ForeignKey("dim_all_users.user_id"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("record_count", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("job_runs")
    op.drop_index("ix_listens_track_ts", table_name="dim_all_listens")
    op.drop_index("ix_listens_user_track", table_name="dim_all_listens")
    op.drop_table("dim_all_listens")
    op.drop_table("dim_all_users")
    op.drop_table("artist_to_genre")
    op.drop_table("track_to_artist")
    op.drop_table("dim_all_artists")
    op.drop_table("dim_all_tracks")
    op.drop_table("dim_all_albums")
