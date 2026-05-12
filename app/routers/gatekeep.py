import math
import secrets
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Artist,
    FriendInvite,
    Listen,
    ListenSource,
    Track,
    TrackArtist,
    User,
)
from app.models import User as UserModel
from app.routers.auth import get_current_user
from app.routers.friends import get_friend_ids
from app.services.audit import log_action
from app.schemas import (
    ChallengeResponse,
    GatekeepArtistResponse,
    GatekeepEntry,
    GatekeepTrackResponse,
    LeaderboardEntry,
    LeaderboardResponse,
)

router = APIRouter(prefix="/gatekeep", tags=["gatekeep"])


def _ms_to_minutes(ms: Optional[int]) -> int:
    if ms is None or ms < 0:
        return 0
    return math.floor(ms / 1000 / 60)


def _get_first_listen_source(
    db: Session, user_id: str, entity_type: str, entity_id: str
) -> str:
    if entity_type == "artist":
        stmt = (
            select(Listen.source)
            .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
            .where(TrackArtist.artist_id == entity_id, Listen.user_id == user_id)
            .order_by(Listen.ts.asc())
            .limit(1)
        )
    else:
        stmt = (
            select(Listen.source)
            .where(Listen.track_id == entity_id, Listen.user_id == user_id)
            .order_by(Listen.ts.asc())
            .limit(1)
        )
    return db.execute(stmt).scalar() or "export"


def _build_gatekeep_entries(
    db: Session,
    rows: list,
    entity_type: str,
    entity_id: str,
) -> List[GatekeepEntry]:
    entries = []
    for i, row in enumerate(rows):
        source = _get_first_listen_source(db, row.user_id, entity_type, entity_id)
        entries.append(
            GatekeepEntry(
                user_id=row.user_id,
                user_name=row.user_name,
                first_listen=row.first_listen,
                first_listen_source=source,
                total_listens=row.total_listens,
                verified_listens=row.verified_listens or 0,
                total_minutes=_ms_to_minutes(row.total_ms),
                is_winner=(i == 0),
            )
        )
    return entries


@router.get("/artist/{artist_id}", response_model=GatekeepArtistResponse)
def gatekeep_artist(
    artist_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    artist = db.query(Artist).filter(Artist.artist_id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    friend_ids = get_friend_ids(db, user.user_id)
    group_ids = [user.user_id] + friend_ids

    stmt = (
        select(
            Listen.user_id,
            User.user_name,
            func.min(Listen.ts).label("first_listen"),
            func.count().label("total_listens"),
            func.sum(
                case((Listen.source == ListenSource.api.value, 1), else_=0)
            ).label("verified_listens"),
            func.sum(Track.duration_ms).label("total_ms"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Track, Listen.track_id == Track.track_id)
        .join(User, Listen.user_id == User.user_id)
        .where(TrackArtist.artist_id == artist_id)
        .where(Listen.user_id.in_(group_ids))
        .group_by(Listen.user_id, User.user_name)
        .order_by(func.min(Listen.ts).asc())
    )
    rows = db.execute(stmt).all()

    entries = _build_gatekeep_entries(db, rows, "artist", artist_id)

    winner_id = entries[0].user_id if entries else None
    log_action(
        db, "gatekeep.artist_viewed",
        user_id=user.user_id,
        entity_type="artist",
        entity_id=artist_id,
        details={
            "artist_name": artist.artist_name,
            "num_participants": len(entries),
            "winner": winner_id,
        },
    )

    return GatekeepArtistResponse(
        artist_id=artist_id,
        artist_name=artist.artist_name,
        entries=entries,
    )


@router.get("/track/{track_id}", response_model=GatekeepTrackResponse)
def gatekeep_track(
    track_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    track = db.query(Track).filter(Track.track_id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    friend_ids = get_friend_ids(db, user.user_id)
    group_ids = [user.user_id] + friend_ids

    stmt = (
        select(
            Listen.user_id,
            User.user_name,
            func.min(Listen.ts).label("first_listen"),
            func.count().label("total_listens"),
            func.sum(
                case((Listen.source == ListenSource.api.value, 1), else_=0)
            ).label("verified_listens"),
            (func.count() * func.coalesce(Track.duration_ms, 0)).label("total_ms"),
        )
        .select_from(Listen)
        .join(Track, Listen.track_id == Track.track_id)
        .join(User, Listen.user_id == User.user_id)
        .where(Listen.track_id == track_id)
        .where(Listen.user_id.in_(group_ids))
        .group_by(Listen.user_id, User.user_name)
        .order_by(func.min(Listen.ts).asc())
    )
    rows = db.execute(stmt).all()

    entries = _build_gatekeep_entries(db, rows, "track", track_id)

    winner_id = entries[0].user_id if entries else None
    log_action(
        db, "gatekeep.track_viewed",
        user_id=user.user_id,
        entity_type="track",
        entity_id=track_id,
        details={
            "track_name": track.track_name,
            "num_participants": len(entries),
            "winner": winner_id,
        },
    )

    return GatekeepTrackResponse(
        track_id=track_id,
        track_name=track.track_name,
        entries=entries,
    )


@router.get("/leaderboard", response_model=LeaderboardResponse)
def leaderboard(
    user: UserModel = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    friend_ids = get_friend_ids(db, user.user_id)
    group_ids = [user.user_id] + friend_ids

    if len(group_ids) < 2:
        return LeaderboardResponse(entries=[], total_artists_contested=0)

    artist_user_first = (
        select(
            TrackArtist.artist_id,
            Listen.user_id,
            func.min(Listen.ts).label("first_listen"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .where(Listen.user_id.in_(group_ids))
        .group_by(TrackArtist.artist_id, Listen.user_id)
    ).cte("artist_user_first")

    artist_min = (
        select(
            artist_user_first.c.artist_id,
            func.min(artist_user_first.c.first_listen).label("min_first"),
        )
        .group_by(artist_user_first.c.artist_id)
        .having(func.count(artist_user_first.c.user_id) > 1)
    ).cte("artist_min")

    contested_count = db.execute(
        select(func.count()).select_from(artist_min)
    ).scalar() or 0

    crown_stmt = (
        select(
            artist_user_first.c.user_id,
            func.count().label("crown_count"),
        )
        .join(
            artist_min,
            (artist_user_first.c.artist_id == artist_min.c.artist_id)
            & (artist_user_first.c.first_listen == artist_min.c.min_first),
        )
        .group_by(artist_user_first.c.user_id)
        .order_by(func.count().desc())
        .limit(max(1, min(limit, 100)))
        .offset(max(0, offset))
    )
    rows = db.execute(crown_stmt).all()

    user_names = {
        u.user_id: u.user_name
        for u in db.query(User).filter(User.user_id.in_(group_ids)).all()
    }

    entries = [
        LeaderboardEntry(
            rank=offset + i + 1,
            user_id=row.user_id,
            user_name=user_names.get(row.user_id),
            crown_count=row.crown_count,
        )
        for i, row in enumerate(rows)
    ]

    log_action(
        db, "gatekeep.leaderboard_viewed",
        user_id=user.user_id,
        details={
            "total_artists_contested": contested_count,
            "num_entries": len(entries),
        },
    )

    return LeaderboardResponse(
        entries=entries,
        total_artists_contested=contested_count,
    )


@router.post("/challenge", response_model=ChallengeResponse)
def create_challenge(
    artist_id: str = Query(...),
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    artist = db.query(Artist).filter(Artist.artist_id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    stmt = (
        select(
            func.min(Listen.ts).label("first_listen"),
            func.count().label("total_listens"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .where(TrackArtist.artist_id == artist_id, Listen.user_id == user.user_id)
    )
    result = db.execute(stmt).first()

    if not result or not result.first_listen:
        log_action(
            db, "gatekeep.challenge_created",
            user_id=user.user_id,
            entity_type="artist",
            entity_id=artist_id,
            status="error",
            details={"reason": "no_listening_data"},
        )
        raise HTTPException(
            status_code=400,
            detail="You have no listening data for this artist",
        )

    code = secrets.token_urlsafe(16)
    db.add(
        FriendInvite(
            from_user_id=user.user_id,
            invite_code=code,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    log_action(
        db, "gatekeep.challenge_created",
        user_id=user.user_id,
        entity_type="artist",
        entity_id=artist_id,
        details={
            "artist_name": artist.artist_name,
            "total_listens": result.total_listens,
            "invite_code": code,
        },
    )

    artist_name = artist.artist_name or "this artist"
    challenge_text = (
        f"I've listened to {artist_name} {result.total_listens} times "
        f"since {result.first_listen.strftime('%B %Y')}. "
        f"Think you beat me? Prove it."
    )

    return ChallengeResponse(
        challenge_text=challenge_text,
        invite_code=code,
        artist_id=artist_id,
        artist_name=artist.artist_name,
        your_first_listen=result.first_listen,
        your_total_listens=result.total_listens,
    )
