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
    Friendship,
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


def _clamp_offset(offset: int) -> int:
    return max(0, offset)


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
    if ms is None or ms < 0:
        return 0
    return math.floor(ms / 1000 / 60)


def _get_top_tracks(
    db: Session, user_id: str, since: Optional[datetime], limit: int, offset: int = 0, until: Optional[datetime] = None
) -> List[TopTrackEntry]:
    stmt = (
        select(
            Track.track_id,
            Track.track_name,
            Album.album_name,
            Track.image_url,
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
            Track.image_url,
            Track.duration_ms,
        )
        .order_by(func.count().desc())
        .limit(limit)
        .offset(offset)
    )
    if since:
        stmt = stmt.where(Listen.ts >= since)
    if until:
        stmt = stmt.where(Listen.ts < until)
    rows = db.execute(stmt).all()
    return [
        TopTrackEntry(
            rank=offset + i + 1,
            track_id=row.track_id,
            track_name=row.track_name,
            album_name=row.album_name,
            image_url=row.image_url,
            listen_count=row.listen_count,
            total_minutes=_ms_to_minutes(
                (row.duration_ms or 0) * row.listen_count
            ),
        )
        for i, row in enumerate(rows)
    ]


def _get_top_artists(
    db: Session, user_id: str, since: Optional[datetime], limit: int, offset: int = 0, until: Optional[datetime] = None
) -> List[TopArtistEntry]:
    stmt = (
        select(
            Artist.artist_id,
            Artist.artist_name,
            Artist.image_url,
            func.count().label("listen_count"),
            func.sum(Track.duration_ms).label("total_ms"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .join(Track, Listen.track_id == Track.track_id)
        .where(Listen.user_id == user_id)
        .group_by(Artist.artist_id, Artist.artist_name, Artist.image_url)
        .order_by(func.count().desc())
        .limit(limit)
        .offset(offset)
    )
    if since:
        stmt = stmt.where(Listen.ts >= since)
    if until:
        stmt = stmt.where(Listen.ts < until)
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
            image_url=row.image_url,
            genres=genres_by_artist.get(row.artist_id, []),
            listen_count=row.listen_count,
            total_minutes=_ms_to_minutes(row.total_ms),
        )
        for i, row in enumerate(rows)
    ]


def _get_top_genres(
    db: Session, user_id: str, since: Optional[datetime], limit: int, offset: int = 0, until: Optional[datetime] = None
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
    if until:
        inner = inner.where(Listen.ts < until)
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
    db: Session, user_id: str, since: Optional[datetime], until: Optional[datetime] = None
) -> int:
    stmt = (
        select(func.sum(Track.duration_ms))
        .select_from(Listen)
        .join(Track, Listen.track_id == Track.track_id)
        .where(Listen.user_id == user_id)
    )
    if since:
        stmt = stmt.where(Listen.ts >= since)
    if until:
        stmt = stmt.where(Listen.ts < until)
    result = db.execute(stmt).scalar()
    return _ms_to_minutes(result)


def _get_total_listens(
    db: Session, user_id: str, since: Optional[datetime]
) -> int:
    stmt = select(func.count()).select_from(Listen).where(Listen.user_id == user_id)
    if since:
        stmt = stmt.where(Listen.ts >= since)
    return db.execute(stmt).scalar() or 0


def _resolve_target_user(
    db: Session, requester: User, target_user_id: Optional[str]
) -> str:
    if not target_user_id or target_user_id == requester.user_id:
        return requester.user_id
    friend_ids = [
        r[0] for r in db.execute(
            select(Friendship.user_id_2).where(Friendship.user_id_1 == requester.user_id)
        ).all()
    ]
    if target_user_id not in friend_ids:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="You can only view friends' stats")
    return target_user_id


@router.get("/top-tracks", response_model=List[TopTrackEntry])
def top_tracks(
    user: UserModel = Depends(get_current_user),
    period: TimePeriod = TimePeriod.all,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    target_user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    uid = _resolve_target_user(db, user, target_user_id)
    since = _period_to_since(period)
    results = _get_top_tracks(db, uid, since, _clamp_limit(limit), _clamp_offset(offset))
    log_action(db, "stats.top_tracks_viewed", user_id=user.user_id,
               details={"period": period.value, "target": uid, "results": len(results)})
    return results


@router.get("/top-artists", response_model=List[TopArtistEntry])
def top_artists(
    user: UserModel = Depends(get_current_user),
    period: TimePeriod = TimePeriod.all,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    target_user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    uid = _resolve_target_user(db, user, target_user_id)
    since = _period_to_since(period)
    results = _get_top_artists(db, uid, since, _clamp_limit(limit), _clamp_offset(offset))
    log_action(db, "stats.top_artists_viewed", user_id=user.user_id,
               details={"period": period.value, "target": uid, "results": len(results)})
    return results


@router.get("/top-genres", response_model=List[TopGenreEntry])
def top_genres(
    user: UserModel = Depends(get_current_user),
    period: TimePeriod = TimePeriod.all,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    target_user_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    uid = _resolve_target_user(db, user, target_user_id)
    since = _period_to_since(period)
    results = _get_top_genres(db, uid, since, _clamp_limit(limit), _clamp_offset(offset))
    log_action(db, "stats.top_genres_viewed", user_id=user.user_id,
               details={"period": period.value, "target": uid, "results": len(results)})
    return results


@router.get("/wrapped", response_model=WrappedResponse)
def wrapped(
    user: UserModel = Depends(get_current_user),
    year: Optional[int] = None,
    db: Session = Depends(get_db),
):

    current_year = datetime.now(timezone.utc).year
    if year:
        if year < 2000 or year > current_year + 1:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Year must be between 2000 and {current_year + 1}")
        since = datetime(year, 1, 1, tzinfo=timezone.utc)
    else:
        year = current_year
        since = datetime(year, 1, 1, tzinfo=timezone.utc)

    # Spotify Wrapped typically covers Jan 1 - Oct 31.
    # For past years, scope to full year. For current year, use Oct 31 cutoff
    # if we're past November, otherwise use today.
    if year < current_year:
        until = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        period_label = f"Jan 1 - Dec 31, {year}"
    else:
        now = datetime.now(timezone.utc)
        if now.month >= 11:
            until = datetime(year, 11, 1, tzinfo=timezone.utc)
            period_label = f"Jan 1 - Oct 31, {year}"
        else:
            until = None
            period_label = f"Jan 1 - {now.strftime('%b %d')}, {year}"

    top_tracks = _get_top_tracks(db, user.user_id, since, WRAPPED_LIMIT, until=until)
    top_artists = _get_top_artists(db, user.user_id, since, WRAPPED_LIMIT, until=until)
    top_genres = _get_top_genres(db, user.user_id, since, 5, until=until)
    total_minutes = _get_total_minutes(db, user.user_id, since, until=until)
    total_listens = _get_total_listens(db, user.user_id, since)

    unique_artists = db.execute(
        select(func.count(func.distinct(TrackArtist.artist_id)))
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .where(Listen.user_id == user.user_id, Listen.ts >= since,
               *([Listen.ts < until] if until else []))
    ).scalar() or 0

    unique_tracks = db.execute(
        select(func.count(func.distinct(Listen.track_id)))
        .select_from(Listen)
        .where(Listen.user_id == user.user_id, Listen.ts >= since,
               *([Listen.ts < until] if until else []))
    ).scalar() or 0

    log_action(db, "stats.wrapped_viewed", user_id=user.user_id,
               details={"year": year, "total_minutes": total_minutes})

    return WrappedResponse(
        top_artists=top_artists,
        top_tracks=top_tracks,
        top_genre=top_genres[0].genre if top_genres else None,
        top_genres=top_genres,
        total_minutes=total_minutes,
        total_listens=total_listens,
        unique_artists=unique_artists,
        unique_tracks=unique_tracks,
        year=year,
        data_period=period_label,
    )


@router.get("/timeline")
def timeline(
    artist_id: str = Query(None),
    track_id: str = Query(None),
    mode: str = Query("personal"),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not artist_id and not track_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Provide artist_id or track_id")

    if mode == "global":
        user_ids = None
    elif mode == "friends":
        friend_rows = db.execute(
            select(Friendship.user_id_2).where(Friendship.user_id_1 == user.user_id)
        ).all()
        user_ids = [user.user_id] + [r[0] for r in friend_rows]
    else:
        user_ids = [user.user_id]

    stmt = (
        select(
            Listen.user_id,
            User.user_name,
            Listen.ts,
        )
        .join(User, Listen.user_id == User.user_id)
    )
    if user_ids is not None:
        stmt = stmt.where(Listen.user_id.in_(user_ids))
    if artist_id:
        stmt = stmt.join(TrackArtist, Listen.track_id == TrackArtist.track_id).where(
            TrackArtist.artist_id == artist_id
        )
    elif track_id:
        stmt = stmt.where(Listen.track_id == track_id)

    stmt = stmt.order_by(Listen.ts)

    rows = db.execute(stmt).all()

    from collections import defaultdict

    if mode == "global":
        global_months: dict[str, int] = defaultdict(int)
        for row in rows:
            ts = row.ts if isinstance(row.ts, datetime) else datetime.fromisoformat(str(row.ts))
            global_months[ts.strftime("%Y-%m")] += 1
        data = {
            "_global": {
                "user_id": "_global",
                "user_name": "All Users",
                "months": [
                    {"month": m, "listen_count": c}
                    for m, c in sorted(global_months.items())
                ],
            }
        }
    else:
        counts: dict = {}
        for row in rows:
            uid = row.user_id
            if uid not in counts:
                counts[uid] = {"user_name": row.user_name, "months": defaultdict(int)}
            ts = row.ts if isinstance(row.ts, datetime) else datetime.fromisoformat(str(row.ts))
            month_key = ts.strftime("%Y-%m")
            counts[uid]["months"][month_key] += 1

        data = {}
        for uid, info in counts.items():
            data[uid] = {
                "user_id": uid,
                "user_name": info["user_name"],
                "months": [
                    {"month": m, "listen_count": c}
                    for m, c in sorted(info["months"].items())
                ],
            }

    log_action(
        db, "stats.timeline_viewed",
        user_id=user.user_id,
        details={"artist_id": artist_id, "track_id": track_id, "mode": mode},
    )

    return {"users": list(data.values())}


@router.get("/lastfm-timeline")
def lastfm_timeline(
    artist_name: str = Query(...),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.lastfm import get_artist_global_stats

    result = get_artist_global_stats(artist_name)

    log_action(
        db, "stats.lastfm_timeline_viewed",
        user_id=user.user_id,
        details={"artist_name": artist_name, "has_data": result is not None},
    )

    if result is None:
        return {"source": "lastfm", "data": None, "message": "Last.fm data unavailable"}

    return {
        "source": "lastfm",
        "type": "summary",
        "data": result,
    }
