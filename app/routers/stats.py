import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Album,
    Artist,
    ArtistGenre,
    Listen,
    Track,
    TrackArtist,
    User,
)
from app.models import User as UserModel
from app.routers.auth import get_current_user
from app.services.audit import log_action
from app.schemas import (
    TimePeriod,
    TopArtistEntry,
    TopGenreEntry,
    TopTrackEntry,
    WrappedResponse,
)

router = APIRouter(prefix="/stats", tags=["stats"])

DEFAULT_LIMIT = 10
MAX_LIMIT = 100
WRAPPED_LIMIT = 5


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def _period_to_since(period: TimePeriod) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    if period == TimePeriod.today:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == TimePeriod.month:
        return now - timedelta(days=30)
    elif period == TimePeriod.year:
        return now - timedelta(days=365)
    return None


def _ms_to_minutes(ms: Optional[int]) -> int:
    if not ms or ms < 0:
        return 0
    return math.floor(ms / 1000 / 60)


def _get_top_tracks(
    db: Session, user_id: str, since: Optional[datetime], limit: int, offset: int = 0
) -> List[TopTrackEntry]:
    stmt = (
        select(
            Track.track_id,
            Track.track_name,
            Album.album_name,
            Track.duration_ms,
            func.count().label("listen_count"),
        )
        .select_from(Listen)
        .join(Track, Listen.track_id == Track.track_id)
        .outerjoin(Album, Track.album_id == Album.album_id)
        .where(Listen.user_id == user_id)
        .group_by(
            Track.track_id,
            Track.track_name,
            Album.album_name,
            Track.duration_ms,
        )
        .order_by(func.count().desc())
        .limit(limit)
        .offset(offset)
    )
    if since:
        stmt = stmt.where(Listen.ts >= since)
    rows = db.execute(stmt).all()
    return [
        TopTrackEntry(
            rank=offset + i + 1,
            track_id=row.track_id,
            track_name=row.track_name,
            album_name=row.album_name,
            listen_count=row.listen_count,
            total_minutes=_ms_to_minutes(
                (row.duration_ms or 0) * row.listen_count
            ),
        )
        for i, row in enumerate(rows)
    ]


def _get_top_artists(
    db: Session, user_id: str, since: Optional[datetime], limit: int, offset: int = 0
) -> List[TopArtistEntry]:
    stmt = (
        select(
            Artist.artist_id,
            Artist.artist_name,
            func.count().label("listen_count"),
            func.sum(Track.duration_ms).label("total_ms"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .join(Track, Listen.track_id == Track.track_id)
        .where(Listen.user_id == user_id)
        .group_by(Artist.artist_id, Artist.artist_name)
        .order_by(func.count().desc())
        .limit(limit)
        .offset(offset)
    )
    if since:
        stmt = stmt.where(Listen.ts >= since)
    rows = db.execute(stmt).all()

    artist_ids = [row.artist_id for row in rows]
    genres_by_artist: dict[str, list[str]] = {}
    if artist_ids:
        genre_rows = db.execute(
            select(ArtistGenre.artist_id, ArtistGenre.genre).where(
                ArtistGenre.artist_id.in_(artist_ids)
            )
        ).all()
        for gr in genre_rows:
            genres_by_artist.setdefault(gr.artist_id, []).append(gr.genre)

    return [
        TopArtistEntry(
            rank=offset + i + 1,
            artist_id=row.artist_id,
            artist_name=row.artist_name,
            genres=genres_by_artist.get(row.artist_id, []),
            listen_count=row.listen_count,
            total_minutes=_ms_to_minutes(row.total_ms),
        )
        for i, row in enumerate(rows)
    ]


def _get_top_genres(
    db: Session, user_id: str, since: Optional[datetime], limit: int, offset: int = 0
) -> List[TopGenreEntry]:
    inner = (
        select(
            Listen.ts,
            Listen.user_id,
            Listen.track_id,
            ArtistGenre.genre,
            Track.duration_ms,
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(ArtistGenre, TrackArtist.artist_id == ArtistGenre.artist_id)
        .join(Track, Listen.track_id == Track.track_id)
        .where(Listen.user_id == user_id)
        .distinct()
    )
    if since:
        inner = inner.where(Listen.ts >= since)
    sub = inner.subquery()

    stmt = (
        select(
            sub.c.genre,
            func.count().label("listen_count"),
            func.sum(sub.c.duration_ms).label("total_ms"),
        )
        .group_by(sub.c.genre)
        .order_by(func.count().desc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(stmt).all()
    return [
        TopGenreEntry(
            rank=offset + i + 1,
            genre=row.genre,
            listen_count=row.listen_count,
            total_minutes=_ms_to_minutes(row.total_ms),
        )
        for i, row in enumerate(rows)
    ]


def _get_total_minutes(
    db: Session, user_id: str, since: Optional[datetime]
) -> int:
    stmt = (
        select(func.sum(Track.duration_ms))
        .select_from(Listen)
        .join(Track, Listen.track_id == Track.track_id)
        .where(Listen.user_id == user_id)
    )
    if since:
        stmt = stmt.where(Listen.ts >= since)
    result = db.execute(stmt).scalar()
    return _ms_to_minutes(result)


def _get_total_listens(
    db: Session, user_id: str, since: Optional[datetime]
) -> int:
    stmt = select(func.count()).select_from(Listen).where(Listen.user_id == user_id)
    if since:
        stmt = stmt.where(Listen.ts >= since)
    return db.execute(stmt).scalar() or 0


@router.get("/top-tracks", response_model=List[TopTrackEntry])
def top_tracks(
    user: UserModel = Depends(get_current_user),
    period: TimePeriod = TimePeriod.all,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    since = _period_to_since(period)
    results = _get_top_tracks(db, user.user_id, since, _clamp_limit(limit), offset)
    log_action(db, "stats.top_tracks_viewed", user_id=user.user_id,
               details={"period": period.value, "limit": limit, "offset": offset, "results": len(results)})
    return results


@router.get("/top-artists", response_model=List[TopArtistEntry])
def top_artists(
    user: UserModel = Depends(get_current_user),
    period: TimePeriod = TimePeriod.all,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    since = _period_to_since(period)
    results = _get_top_artists(db, user.user_id, since, _clamp_limit(limit), offset)
    log_action(db, "stats.top_artists_viewed", user_id=user.user_id,
               details={"period": period.value, "limit": limit, "offset": offset, "results": len(results)})
    return results


@router.get("/top-genres", response_model=List[TopGenreEntry])
def top_genres(
    user: UserModel = Depends(get_current_user),
    period: TimePeriod = TimePeriod.all,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    since = _period_to_since(period)
    results = _get_top_genres(db, user.user_id, since, _clamp_limit(limit), offset)
    log_action(db, "stats.top_genres_viewed", user_id=user.user_id,
               details={"period": period.value, "limit": limit, "offset": offset, "results": len(results)})
    return results


@router.get("/wrapped", response_model=WrappedResponse)
def wrapped(
    user: UserModel = Depends(get_current_user),
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):

    if year:
        since = datetime(year, 1, 1, tzinfo=timezone.utc)
    else:
        year = datetime.now(timezone.utc).year
        since = datetime(year, 1, 1, tzinfo=timezone.utc)

    top_tracks = _get_top_tracks(db, user.user_id, since, WRAPPED_LIMIT)
    top_artists = _get_top_artists(db, user.user_id, since, WRAPPED_LIMIT)
    top_genres = _get_top_genres(db, user.user_id, since, 1)
    total_minutes = _get_total_minutes(db, user.user_id, since)

    log_action(db, "stats.wrapped_viewed", user_id=user.user_id,
               details={"year": year, "total_minutes": total_minutes})

    return WrappedResponse(
        top_artists=top_artists,
        top_tracks=top_tracks,
        top_genre=top_genres[0].genre if top_genres else None,
        total_minutes=total_minutes,
        year=year,
    )
