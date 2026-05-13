from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Artist,
    ArtistGenre,
    Listen,
    Track,
    TrackArtist,
    User,
)
from app.models import User as UserModel
from app.routers.auth import get_current_user
from app.routers.friends import get_friend_ids
from app.services.audit import log_action

router = APIRouter(prefix="/discover", tags=["discover"])


@router.get("/friends-fresh-finds")
def friends_fresh_finds(
    days: int = 7,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend_ids = get_friend_ids(db, user.user_id)
    if not friend_ids:
        return []

    since = datetime.now(timezone.utc) - timedelta(days=days)

    my_artists = set(
        r[0] for r in db.execute(
            select(TrackArtist.artist_id)
            .select_from(Listen)
            .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
            .where(Listen.user_id == user.user_id)
            .group_by(TrackArtist.artist_id)
        ).all()
    )

    stmt = (
        select(
            TrackArtist.artist_id,
            Artist.artist_name,
            Artist.image_url,
            func.count(func.distinct(Listen.user_id)).label("friend_count"),
            func.count().label("listen_count"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(
            Listen.user_id.in_(friend_ids),
            Listen.ts >= since,
        )
        .group_by(TrackArtist.artist_id, Artist.artist_name, Artist.image_url)
        .order_by(func.count(func.distinct(Listen.user_id)).desc(), func.count().desc())
        .limit(20)
    )
    rows = db.execute(stmt).all()

    results = [
        {
            "artist_id": r.artist_id,
            "artist_name": r.artist_name,
            "image_url": r.image_url,
            "friend_count": r.friend_count,
            "listen_count": r.listen_count,
            "you_listen": r.artist_id in my_artists,
        }
        for r in rows
        if r.artist_id not in my_artists
    ]

    log_action(db, "discover.friends_fresh_finds", user_id=user.user_id,
               details={"days": days, "results": len(results)})
    return results


@router.get("/youre-late-on")
def youre_late_on(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend_ids = get_friend_ids(db, user.user_id)
    if not friend_ids:
        return []

    my_artists = set(
        r[0] for r in db.execute(
            select(TrackArtist.artist_id)
            .select_from(Listen)
            .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
            .where(Listen.user_id == user.user_id)
            .group_by(TrackArtist.artist_id)
        ).all()
    )

    stmt = (
        select(
            TrackArtist.artist_id,
            Artist.artist_name,
            Artist.image_url,
            func.count(func.distinct(Listen.user_id)).label("friend_count"),
            func.sum(
                func.count().over(partition_by=[Listen.user_id, TrackArtist.artist_id])
            ).label("total_listens") if False else func.count().label("total_listens"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id.in_(friend_ids))
        .group_by(TrackArtist.artist_id, Artist.artist_name, Artist.image_url)
        .having(func.count(func.distinct(Listen.user_id)) >= 2)
        .order_by(func.count(func.distinct(Listen.user_id)).desc(), func.count().desc())
        .limit(20)
    )
    rows = db.execute(stmt).all()

    genre_map: dict = {}
    artist_ids = [r.artist_id for r in rows if r.artist_id not in my_artists]
    if artist_ids:
        genre_rows = db.execute(
            select(ArtistGenre.artist_id, ArtistGenre.genre)
            .where(ArtistGenre.artist_id.in_(artist_ids))
        ).all()
        for gr in genre_rows:
            genre_map.setdefault(gr.artist_id, []).append(gr.genre)

    results = [
        {
            "artist_id": r.artist_id,
            "artist_name": r.artist_name,
            "image_url": r.image_url,
            "friend_count": r.friend_count,
            "total_listens": r.total_listens,
            "genres": genre_map.get(r.artist_id, [])[:3],
            "urgency": f"{r.friend_count} of your friends already listen to this artist",
        }
        for r in rows
        if r.artist_id not in my_artists
    ]

    log_action(db, "discover.youre_late_on", user_id=user.user_id,
               details={"results": len(results)})
    return results


@router.get("/rising")
def rising_artists(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=30)
    prior_start = now - timedelta(days=60)

    recent_stmt = (
        select(
            TrackArtist.artist_id,
            func.count(func.distinct(Listen.user_id)).label("recent_listeners"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .where(Listen.ts >= recent_start)
        .group_by(TrackArtist.artist_id)
    )
    recent = {r[0]: r[1] for r in db.execute(recent_stmt).all()}

    prior_stmt = (
        select(
            TrackArtist.artist_id,
            func.count(func.distinct(Listen.user_id)).label("prior_listeners"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .where(Listen.ts >= prior_start, Listen.ts < recent_start)
        .group_by(TrackArtist.artist_id)
    )
    prior = {r[0]: r[1] for r in db.execute(prior_stmt).all()}

    growth = []
    for artist_id, recent_count in recent.items():
        prior_count = prior.get(artist_id, 0)
        new_listeners = recent_count - prior_count
        if new_listeners > 0:
            growth.append((artist_id, new_listeners, recent_count))

    growth.sort(key=lambda x: -x[1])
    top_ids = [g[0] for g in growth[:15]]

    if not top_ids:
        return []

    artists = {
        a.artist_id: a
        for a in db.query(Artist).filter(Artist.artist_id.in_(top_ids)).all()
    }

    my_artists = set(
        r[0] for r in db.execute(
            select(TrackArtist.artist_id)
            .select_from(Listen)
            .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
            .where(Listen.user_id == user.user_id)
            .group_by(TrackArtist.artist_id)
        ).all()
    )

    results = []
    for artist_id, new_listeners, total_listeners in growth[:15]:
        a = artists.get(artist_id)
        if not a:
            continue
        results.append({
            "artist_id": artist_id,
            "artist_name": a.artist_name,
            "image_url": a.image_url,
            "new_listeners": new_listeners,
            "total_listeners": total_listeners,
            "you_listen": artist_id in my_artists,
        })

    log_action(db, "discover.rising_viewed", user_id=user.user_id,
               details={"results": len(results)})
    return results
