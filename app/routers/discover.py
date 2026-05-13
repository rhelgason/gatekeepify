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
from app.services.activity import generate_activity_feed
from app.services.compatibility import compute_quick_score, get_user_artists

router = APIRouter(prefix="/discover", tags=["discover"])


def _get_my_artist_ids(db: Session, user_id: str) -> set:
    return set(
        r[0] for r in db.execute(
            select(TrackArtist.artist_id)
            .select_from(Listen)
            .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
            .where(Listen.user_id == user_id)
            .group_by(TrackArtist.artist_id)
        ).all()
    )


def _get_friend_compat_scores(db: Session, user_id: str, friend_ids: list) -> dict:
    scores = {}
    for fid in friend_ids:
        scores[fid] = compute_quick_score(db, user_id, fid)
    return scores


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
    my_artists = _get_my_artist_ids(db, user.user_id)
    compat_scores = _get_friend_compat_scores(db, user.user_id, friend_ids)

    # Get per-friend-per-artist recent listens
    stmt = (
        select(
            TrackArtist.artist_id,
            Artist.artist_name,
            Artist.image_url,
            Listen.user_id,
            func.count().label("listen_count"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id.in_(friend_ids), Listen.ts >= since)
        .group_by(TrackArtist.artist_id, Artist.artist_name, Artist.image_url, Listen.user_id)
    )
    rows = db.execute(stmt).all()

    # Aggregate per artist, weighting by friend compatibility
    artist_data: dict = {}
    for r in rows:
        if r.artist_id in my_artists:
            continue
        if r.artist_id not in artist_data:
            artist_data[r.artist_id] = {
                "artist_id": r.artist_id,
                "artist_name": r.artist_name,
                "image_url": r.image_url,
                "friend_count": 0,
                "listen_count": 0,
                "relevance_score": 0.0,
            }
        d = artist_data[r.artist_id]
        d["friend_count"] += 1
        d["listen_count"] += r.listen_count
        d["relevance_score"] += compat_scores.get(r.user_id, 50) * r.listen_count

    results = sorted(artist_data.values(), key=lambda x: -x["relevance_score"])[:20]

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

    my_artists = _get_my_artist_ids(db, user.user_id)
    compat_scores = _get_friend_compat_scores(db, user.user_id, friend_ids)

    # Get per-friend-per-artist listens (all time)
    stmt = (
        select(
            TrackArtist.artist_id,
            Artist.artist_name,
            Artist.image_url,
            Listen.user_id,
            func.count().label("listen_count"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id.in_(friend_ids))
        .group_by(TrackArtist.artist_id, Artist.artist_name, Artist.image_url, Listen.user_id)
    )
    rows = db.execute(stmt).all()

    artist_data: dict = {}
    for r in rows:
        if r.artist_id in my_artists:
            continue
        if r.artist_id not in artist_data:
            artist_data[r.artist_id] = {
                "artist_id": r.artist_id,
                "artist_name": r.artist_name,
                "image_url": r.image_url,
                "friend_count": 0,
                "total_listens": 0,
                "relevance_score": 0.0,
            }
        d = artist_data[r.artist_id]
        d["friend_count"] += 1
        d["total_listens"] += r.listen_count
        d["relevance_score"] += compat_scores.get(r.user_id, 50) * r.listen_count

    # Only include artists that 2+ friends listen to
    candidates = [d for d in artist_data.values() if d["friend_count"] >= 2]
    candidates.sort(key=lambda x: -x["relevance_score"])
    rows_filtered = candidates[:20]

    genre_map: dict = {}
    artist_ids = [d["artist_id"] for d in rows_filtered]
    if artist_ids:
        genre_rows = db.execute(
            select(ArtistGenre.artist_id, ArtistGenre.genre)
            .where(ArtistGenre.artist_id.in_(artist_ids))
        ).all()
        for gr in genre_rows:
            genre_map.setdefault(gr.artist_id, []).append(gr.genre)

    results = [
        {
            **d,
            "genres": genre_map.get(d["artist_id"], [])[:3],
            "urgency": f"{d['friend_count']} of your friends already listen to this artist",
        }
        for d in rows_filtered
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

    my_artists = _get_my_artist_ids(db, user.user_id)

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


@router.get("/feed")
def activity_feed(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    friend_ids = get_friend_ids(db, user.user_id)
    group_ids = [user.user_id] + friend_ids

    events = generate_activity_feed(db, group_ids)

    log_action(db, "discover.feed_viewed", user_id=user.user_id,
               details={"events": len(events)})
    return events
