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
import logging

from app.models import User as UserModel
from app.routers.auth import get_current_user
from app.schemas import ArtistDetailResponse, ArtistSearchResult, TrackDetailResponse, TrackSearchResult
from app.services.audit import log_action
from app.services.ingestion import _get_best_image
from app.services.spotify import SpotifyService, decrypt_token

logger = logging.getLogger("gatekeepify.search")

router = APIRouter(prefix="/search", tags=["search"])

MAX_RESULTS = 20


def _escape_like(q: str) -> str:
    return q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/artists", response_model=List[ArtistSearchResult])
def search_artists(
    q: str = Query(..., min_length=1),
    user: UserModel = Depends(get_current_user),
    limit: int = 10,
    db: Session = Depends(get_db),
):
    clamped = max(1, min(limit, MAX_RESULTS))
    pattern = f"%{_escape_like(q)}%"

    stmt = (
        select(
            Artist.artist_id,
            Artist.artist_name,
            Artist.image_url,
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
            image_url=row.image_url,
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
    pattern = f"%{_escape_like(q)}%"

    stmt = (
        select(
            Track.track_id,
            Track.track_name,
            Album.album_name,
            Track.image_url,
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
            image_url=row.image_url,
            artist_names=artists_by_track.get(row.track_id, []),
            your_listen_count=row.your_listen_count,
        )
        for row in rows
    ]


@router.get("/artist/{artist_id}", response_model=ArtistDetailResponse)
def get_artist_detail(
    artist_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    import math

    artist = db.query(Artist).filter(Artist.artist_id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    genre_names = [g.genre for g in artist.genres]

    stats_stmt = (
        select(
            func.count().label("total_listens"),
            func.sum(Track.duration_ms).label("total_ms"),
            func.min(Listen.ts).label("first_listen"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Track, Listen.track_id == Track.track_id)
        .where(TrackArtist.artist_id == artist_id, Listen.user_id == user.user_id)
    )
    row = db.execute(stats_stmt).first()

    return ArtistDetailResponse(
        artist_id=artist.artist_id,
        artist_name=artist.artist_name,
        image_url=artist.image_url,
        genres=genre_names,
        total_listens=row.total_listens or 0,
        total_minutes=math.floor((row.total_ms or 0) / 1000 / 60),
        first_listen=row.first_listen,
    )


@router.get("/track/{track_id}", response_model=TrackDetailResponse)
def get_track_detail(
    track_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    import math

    track = db.query(Track).filter(Track.track_id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    artist_names = [a.artist_name for a in track.artists if a.artist_name]
    album_name = track.album.album_name if track.album else None

    stats_stmt = (
        select(
            func.count().label("total_listens"),
            func.min(Listen.ts).label("first_listen"),
        )
        .where(Listen.track_id == track_id, Listen.user_id == user.user_id)
    )
    row = db.execute(stats_stmt).first()

    return TrackDetailResponse(
        track_id=track.track_id,
        track_name=track.track_name,
        album_name=album_name,
        image_url=track.image_url,
        artist_names=artist_names,
        duration_ms=track.duration_ms,
        total_listens=row.total_listens or 0,
        total_minutes=math.floor((row.total_listens or 0) * (track.duration_ms or 0) / 1000 / 60),
        first_listen=row.first_listen,
    )


@router.get("/resolve-artist")
def resolve_artist(
    name: str = Query(..., min_length=1),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    existing = db.query(Artist).filter(
        func.lower(Artist.artist_name) == name.lower()
    ).first()
    if existing:
        return {"artist_id": existing.artist_id, "artist_name": existing.artist_name, "resolved": "db"}

    user_obj = db.query(User).filter(User.user_id == user.user_id).first()
    if not user_obj or not user_obj.spotify_refresh_token:
        raise HTTPException(status_code=404, detail="Artist not found")

    try:
        service = SpotifyService()
        refresh_token = decrypt_token(user_obj.spotify_refresh_token)
        token_info = service.refresh_access_token(refresh_token)
        client = service.get_client(token_info["access_token"])

        results = client.search(q=f'artist:"{name}"', type="artist", limit=5)
        artists = results.get("artists", {}).get("items", [])

        match = None
        for a in artists:
            if a.get("name", "").lower() == name.lower():
                match = a
                break
        if not match and artists:
            match = artists[0]

        if not match:
            raise HTTPException(status_code=404, detail="Artist not found on Spotify")

        db.merge(Artist(
            artist_id=match["id"],
            artist_name=match.get("name"),
            image_url=_get_best_image(match.get("images", [])),
        ))
        for genre in match.get("genres", []):
            if genre:
                db.merge(ArtistGenre(artist_id=match["id"], genre=genre))
        db.commit()

        log_action(db, "search.artist_resolved", user_id=user.user_id,
                   entity_type="artist", entity_id=match["id"],
                   details={"name": name, "spotify_name": match.get("name")})

        return {"artist_id": match["id"], "artist_name": match.get("name"), "resolved": "spotify"}

    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Failed to resolve artist '{name}': {e}")
        raise HTTPException(status_code=404, detail="Could not resolve artist")
