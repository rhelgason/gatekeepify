from datetime import date, datetime
from typing import List, Optional, Set

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Album,
    Artist,
    ArtistGenre,
    JobRun,
    Listen,
    ListenSource,
    Track,
    TrackArtist,
    User,
)

CLIENT_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def parse_release_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def upsert_from_recent_listens(
    db: Session, items: List[dict], user_id: str
) -> int:
    inserted = 0
    for item in items:
        track_data = item.get("track", {})
        if not track_data.get("id"):
            continue

        _upsert_track_and_relations(db, track_data)

        played_at_str = item.get("played_at", "")
        try:
            ts = datetime.strptime(played_at_str, CLIENT_DATETIME_FORMAT)
        except ValueError:
            continue

        existing = db.execute(
            select(Listen).where(
                Listen.ts == ts,
                Listen.user_id == user_id,
                Listen.track_id == track_data["id"],
            )
        ).first()

        if not existing:
            db.add(
                Listen(
                    ts=ts,
                    user_id=user_id,
                    track_id=track_data["id"],
                    source=ListenSource.api.value,
                )
            )
            inserted += 1

    db.commit()
    return inserted


def upsert_track_metadata(db: Session, track_items: List[dict]) -> int:
    updated = 0
    for item in track_items:
        track_data = item.get("track", {})
        if not track_data or not track_data.get("id"):
            continue
        _upsert_track_and_relations(db, track_data)
        updated += 1
    db.commit()
    return updated


def _upsert_track_and_relations(db: Session, track_data: dict) -> None:
    album_data = track_data.get("album") or {}

    if album_data.get("id"):
        db.merge(
            Album(
                album_id=album_data["id"],
                album_name=album_data.get("name"),
                release_date=parse_release_date(album_data.get("release_date")),
            )
        )

    db.merge(
        Track(
            track_id=track_data["id"],
            track_name=track_data.get("name"),
            album_id=album_data.get("id"),
            duration_ms=track_data.get("duration_ms"),
            is_local=track_data.get("is_local", False),
        )
    )

    for artist_data in track_data.get("artists", []):
        if not artist_data.get("id"):
            continue
        db.merge(
            Artist(
                artist_id=artist_data["id"],
                artist_name=artist_data.get("name"),
            )
        )

    # Entities must exist before relations that reference them
    db.flush()

    for artist_data in track_data.get("artists", []):
        if not artist_data.get("id"):
            continue
        db.merge(
            TrackArtist(
                track_id=track_data["id"],
                artist_id=artist_data["id"],
            )
        )
        for genre in artist_data.get("genres", []):
            if genre:
                db.merge(
                    ArtistGenre(
                        artist_id=artist_data["id"],
                        genre=genre,
                    )
                )

    db.flush()


def retroactively_validate_export_listens(
    db: Session, track_ids: Set[str]
) -> int:
    if not track_ids:
        return 0

    stmt = (
        select(Track.track_id, Album.release_date)
        .join(Album, Track.album_id == Album.album_id)
        .where(
            Track.track_id.in_(list(track_ids)),
            Album.release_date.isnot(None),
        )
    )
    track_release_dates: dict[str, datetime] = {}
    for row in db.execute(stmt).all():
        track_release_dates[row.track_id] = datetime(
            row.release_date.year, row.release_date.month, row.release_date.day
        )

    if not track_release_dates:
        return 0

    removed = 0
    for track_id, release_dt in track_release_dates.items():
        invalid = (
            db.execute(
                select(Listen).where(
                    Listen.track_id == track_id,
                    Listen.source == ListenSource.export.value,
                    Listen.ts < release_dt,
                )
            )
            .scalars()
            .all()
        )
        for listen in invalid:
            db.delete(listen)
            removed += 1

    if removed:
        db.commit()
    return removed


def get_tracks_missing_metadata(db: Session, limit: int = 50) -> Set[str]:
    stmt = (
        select(Listen.track_id, func.count().label("cnt"))
        .outerjoin(Track, Listen.track_id == Track.track_id)
        .where(
            (Track.track_name.is_(None)) | (Track.track_id.is_(None))
        )
        .group_by(Listen.track_id)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return {row.track_id for row in rows}


def get_active_users(db: Session) -> List[User]:
    return (
        db.query(User)
        .filter(
            User.spotify_refresh_token.isnot(None),
            User.spotify_refresh_token != "",
        )
        .all()
    )


def log_job_run(
    db: Session,
    job_name: str,
    user_id: Optional[str],
    started_at: datetime,
    completed_at: datetime,
    status: str,
    record_count: int = 0,
) -> None:
    db.add(
        JobRun(
            job_name=job_name,
            user_id=user_id,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            record_count=record_count,
        )
    )
    db.commit()
