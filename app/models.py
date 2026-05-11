import enum
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
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

    album: Mapped[Optional["Album"]] = relationship(back_populates="tracks")
    artists: Mapped[List["Artist"]] = relationship(
        secondary="track_to_artist", back_populates="tracks", viewonly=True
    )


class Artist(Base):
    __tablename__ = "dim_all_artists"

    artist_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    artist_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

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
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_poll_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


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
    export_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship()
    track: Mapped["Track"] = relationship()

    __table_args__ = (
        Index("ix_listens_user_track", "user_id", "track_id"),
        Index("ix_listens_track_ts", "track_id", "ts"),
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
