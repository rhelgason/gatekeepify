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
from app.schemas import ArtistSearchResult, TrackSearchResult
from app.services.audit import log_action

router = APIRouter(prefix="/search", tags=["search"])

MAX_RESULTS = 20


@router.get("/artists", response_model=List[ArtistSearchResult])
def search_artists(
    q: str = Query(..., min_length=1),
    user: UserModel = Depends(get_current_user),
    limit: int = 10,
    db: Session = Depends(get_db),
):
    clamped = max(1, min(limit, MAX_RESULTS))
    pattern = f"%{q}%"

    stmt = (
        select(
            Artist.artist_id,
            Artist.artist_name,
            func.count(Listen.track_id).label("your_listen_count"),
        )
        .outerjoin(TrackArtist, Artist.artist_id == TrackArtist.artist_id)
        .outerjoin(
            Listen,
            (TrackArtist.track_id == Listen.track_id)
            & (Listen.user_id == user.user_id),
        )
        .where(Artist.artist_name.ilike(pattern))
        .group_by(Artist.artist_id, Artist.artist_name)
        .order_by(func.count(Listen.track_id).desc(), Artist.artist_name.asc())
        .limit(clamped)
    )
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

    log_action(
        db, "search.artists",
        user_id=user.user_id,
        details={"query": q, "results": len(rows)},
    )

    return [
        ArtistSearchResult(
            artist_id=row.artist_id,
            artist_name=row.artist_name,
            genres=genres_by_artist.get(row.artist_id, []),
            your_listen_count=row.your_listen_count,
        )
        for row in rows
    ]


@router.get("/tracks", response_model=List[TrackSearchResult])
def search_tracks(
    q: str = Query(..., min_length=1),
    user: UserModel = Depends(get_current_user),
    limit: int = 10,
    db: Session = Depends(get_db),
):
    clamped = max(1, min(limit, MAX_RESULTS))
    pattern = f"%{q}%"

    stmt = (
        select(
            Track.track_id,
            Track.track_name,
            Album.album_name,
            Track.duration_ms,
            func.count(Listen.track_id).label("your_listen_count"),
        )
        .outerjoin(Album, Track.album_id == Album.album_id)
        .outerjoin(
            Listen,
            (Track.track_id == Listen.track_id)
            & (Listen.user_id == user.user_id),
        )
        .where(Track.track_name.ilike(pattern))
        .group_by(
            Track.track_id,
            Track.track_name,
            Album.album_name,
            Track.duration_ms,
        )
        .order_by(func.count(Listen.track_id).desc(), Track.track_name.asc())
        .limit(clamped)
    )
    rows = db.execute(stmt).all()

    track_ids = [row.track_id for row in rows]
    artists_by_track: dict[str, list[str]] = {}
    if track_ids:
        ta_rows = db.execute(
            select(TrackArtist.track_id, Artist.artist_name)
            .join(Artist, TrackArtist.artist_id == Artist.artist_id)
            .where(TrackArtist.track_id.in_(track_ids))
        ).all()
        for ta in ta_rows:
            artists_by_track.setdefault(ta.track_id, []).append(ta.artist_name)

    log_action(
        db, "search.tracks",
        user_id=user.user_id,
        details={"query": q, "results": len(rows)},
    )

    return [
        TrackSearchResult(
            track_id=row.track_id,
            track_name=row.track_name,
            album_name=row.album_name,
            artist_names=artists_by_track.get(row.track_id, []),
            your_listen_count=row.your_listen_count,
        )
        for row in rows
    ]
