"""
One-time migration script: reads data from the legacy SQLite database
(db/database.db) and inserts it into the new database configured via
DATABASE_URL. Run once after setting up the new schema.

Usage:
    python -m scripts.migrate_sqlite
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    Album,
    Artist,
    ArtistGenre,
    Listen,
    ListenSource,
    Track,
    TrackArtist,
    User,
)

LEGACY_DB_PATH = Path("db/database.db")
LEGACY_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


def migrate():
    if not LEGACY_DB_PATH.exists():
        print(f"Legacy database not found at {LEGACY_DB_PATH}")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)

    legacy = sqlite3.connect(str(LEGACY_DB_PATH))
    legacy.row_factory = sqlite3.Row

    db = SessionLocal()
    try:
        _migrate_albums(legacy, db)
        _migrate_tracks(legacy, db)
        _migrate_artists(legacy, db)
        _migrate_track_to_artist(legacy, db)
        _migrate_artist_to_genre(legacy, db)
        _migrate_users(legacy, db)
        _migrate_listens(legacy, db)
        db.commit()
        print("Migration complete.")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        db.close()
        legacy.close()


def _migrate_albums(legacy: sqlite3.Connection, db: Session):
    rows = legacy.execute("SELECT album_id, album_name FROM dim_all_albums").fetchall()
    for row in rows:
        db.merge(Album(album_id=row["album_id"], album_name=row["album_name"]))
    print(f"  Migrated {len(rows)} albums")


def _migrate_tracks(legacy: sqlite3.Connection, db: Session):
    rows = legacy.execute(
        "SELECT track_id, track_name, album_id, duration_ms, is_local FROM dim_all_tracks"
    ).fetchall()
    for row in rows:
        db.merge(
            Track(
                track_id=row["track_id"],
                track_name=row["track_name"],
                album_id=row["album_id"],
                duration_ms=row["duration_ms"],
                is_local=bool(row["is_local"]) if row["is_local"] is not None else None,
            )
        )
    print(f"  Migrated {len(rows)} tracks")


def _migrate_artists(legacy: sqlite3.Connection, db: Session):
    rows = legacy.execute(
        "SELECT artist_id, artist_name FROM dim_all_artists"
    ).fetchall()
    for row in rows:
        db.merge(Artist(artist_id=row["artist_id"], artist_name=row["artist_name"]))
    print(f"  Migrated {len(rows)} artists")


def _migrate_track_to_artist(legacy: sqlite3.Connection, db: Session):
    rows = legacy.execute(
        "SELECT track_id, artist_id FROM track_to_artist"
    ).fetchall()
    for row in rows:
        db.merge(TrackArtist(track_id=row["track_id"], artist_id=row["artist_id"]))
    print(f"  Migrated {len(rows)} track-artist mappings")


def _migrate_artist_to_genre(legacy: sqlite3.Connection, db: Session):
    rows = legacy.execute(
        "SELECT artist_id, genre FROM artist_to_genre"
    ).fetchall()
    for row in rows:
        db.merge(ArtistGenre(artist_id=row["artist_id"], genre=row["genre"]))
    print(f"  Migrated {len(rows)} artist-genre mappings")


def _migrate_users(legacy: sqlite3.Connection, db: Session):
    rows = legacy.execute("SELECT user_id, user_name FROM dim_all_users").fetchall()
    for row in rows:
        existing = db.query(User).filter(User.user_id == row["user_id"]).first()
        if not existing:
            db.add(
                User(
                    user_id=row["user_id"],
                    user_name=row["user_name"],
                    created_at=datetime.utcnow(),
                )
            )
        else:
            existing.user_name = row["user_name"]
    print(f"  Migrated {len(rows)} users")


def _migrate_listens(legacy: sqlite3.Connection, db: Session):
    rows = legacy.execute(
        "SELECT ts, user_id, track_id FROM dim_all_listens"
    ).fetchall()
    count = 0
    for row in rows:
        ts_str = row["ts"]
        try:
            if len(ts_str) == 19:
                ts = datetime.strptime(ts_str, LEGACY_DATETIME_FORMAT[:-3])
            else:
                ts = datetime.strptime(ts_str, LEGACY_DATETIME_FORMAT)
        except (ValueError, TypeError):
            continue
        db.merge(
            Listen(
                ts=ts,
                user_id=row["user_id"],
                track_id=row["track_id"],
                source=ListenSource.api.value,
            )
        )
        count += 1
    print(f"  Migrated {count} listens")


if __name__ == "__main__":
    migrate()
