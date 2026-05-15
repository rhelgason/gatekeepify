import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ListenSource(str, enum.Enum):
    api = "api"
    export = "export"


class Album(Base):
    __tablename__ = "dim_all_albums"

    album_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    album_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    release_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    tracks: Mapped[List["Track"]] = relationship(back_populates="album")


class Track(Base):
    __tablename__ = "dim_all_tracks"

    track_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    track_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    album_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("dim_all_albums.album_id"), nullable=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_local: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    album: Mapped[Optional["Album"]] = relationship(back_populates="tracks")
    artists: Mapped[List["Artist"]] = relationship(
        secondary="track_to_artist", back_populates="tracks", viewonly=True
    )


class Artist(Base):
    __tablename__ = "dim_all_artists"

    artist_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    artist_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    tracks: Mapped[List["Track"]] = relationship(
        secondary="track_to_artist", back_populates="artists", viewonly=True
    )
    genres: Mapped[List["ArtistGenre"]] = relationship(back_populates="artist")


class TrackArtist(Base):
    __tablename__ = "track_to_artist"

    track_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("dim_all_tracks.track_id"), primary_key=True
    )
    artist_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("dim_all_artists.artist_id"), primary_key=True
    )


class ArtistGenre(Base):
    __tablename__ = "artist_to_genre"

    artist_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("dim_all_artists.artist_id"), primary_key=True
    )
    genre: Mapped[str] = mapped_column(String(255), primary_key=True)

    artist: Mapped["Artist"] = relationship(back_populates="genres")


class User(Base):
    __tablename__ = "dim_all_users"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    spotify_refresh_token: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True
    )
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_poll_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    token_invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_admin: Mapped[bool] = mapped_column(default=False)


class Listen(Base):
    __tablename__ = "dim_all_listens"

    ts: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("dim_all_users.user_id"), primary_key=True
    )
    track_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("dim_all_tracks.track_id"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(10), default=ListenSource.api.value)
    ms_played: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    export_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship()
    track: Mapped["Track"] = relationship()

    __table_args__ = (
        Index("ix_listens_user_track", "user_id", "track_id"),
        Index("ix_listens_track_ts", "track_id", "ts"),
    )


class Friendship(Base):
    __tablename__ = "friendships"

    user_id_1: Mapped[str] = mapped_column(
        String(255), ForeignKey("dim_all_users.user_id"), primary_key=True
    )
    user_id_2: Mapped[str] = mapped_column(
        String(255), ForeignKey("dim_all_users.user_id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime)


class FriendInvite(Base):
    __tablename__ = "friend_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("dim_all_users.user_id")
    )
    to_user_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("dim_all_users.user_id"), nullable=True
    )
    invite_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    accepted_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("dim_all_users.user_id"), nullable=True
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("dim_all_users.user_id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(255), index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="success")

    __table_args__ = (
        Index("ix_audit_user_ts", "user_id", "ts"),
        Index("ix_audit_action_ts", "action", "ts"),
    )


class AwardSnapshot(Base):
    __tablename__ = "award_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("dim_all_users.user_id")
    )
    friend_group_hash: Mapped[str] = mapped_column(String(64))
    award_id: Mapped[str] = mapped_column(String(50))
    rank: Mapped[int] = mapped_column(Integer)
    stat_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    stat_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    entity_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        Index("ix_award_user_group", "user_id", "friend_group_hash"),
        Index("ix_award_group_award", "friend_group_hash", "award_id"),
    )


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_name: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("dim_all_users.user_id"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    record_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
