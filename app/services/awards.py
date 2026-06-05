import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

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

AWARD_DEFINITIONS = {
    "crown": {
        "name": "The Crown",
        "description": "You heard them first. That's all that matters.",
        "tier": "discovery",
    },
    "archaeologist": {
        "name": "The Archaeologist",
        "description": "Dug up an artist months before anyone else noticed.",
        "tier": "discovery",
    },
    "trendsetter": {
        "name": "The Trendsetter",
        "description": "Found the most artists before any of your friends.",
        "tier": "discovery",
    },
    "patient_zero": {
        "name": "Patient Zero",
        "description": "Your taste spread like a disease.",
        "tier": "discovery",
    },
    "obsessive": {
        "name": "The Obsessive",
        "description": "Listened to one artist more than anyone should.",
        "tier": "devotion",
    },
    "completionist": {
        "name": "The Completionist",
        "description": "Heard every track. Yes, the B-sides.",
        "tier": "devotion",
    },
    "genre_snob": {
        "name": "The Genre Snob",
        "description": "Listens to genres nobody else has heard of.",
        "tier": "taste",
    },
    "time_traveler": {
        "name": "The Time Traveler",
        "description": "Still listening to albums from before you were born.",
        "tier": "taste",
    },
    "basic": {
        "name": "The Basic",
        "description": "Congratulations, you listen to exactly what everyone else listens to.",
        "tier": "taste",
    },
    "streak": {
        "name": "The Streak",
        "description": "Listened every single day for X days straight.",
        "tier": "dynamic",
    },
    "hypebeast": {
        "name": "The Hypebeast",
        "description": "Biggest listening spike this month.",
        "tier": "dynamic",
    },
}


def get_friend_group_hash(group_ids: List[str]) -> str:
    return hashlib.sha256(",".join(sorted(group_ids)).encode()).hexdigest()[:16]


def compute_crown(db: Session, group_ids: List[str]) -> List[dict]:
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
    ).cte("auf")

    artist_min = (
        select(
            artist_user_first.c.artist_id,
            func.min(artist_user_first.c.first_listen).label("min_first"),
        )
        .group_by(artist_user_first.c.artist_id)
        .having(func.count(artist_user_first.c.user_id) > 1)
    ).cte("am")

    stmt = (
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
    )
    rows = db.execute(stmt).all()

    return [
        {
            "user_id": row.user_id,
            "rank": i + 1,
            "stat_value": float(row.crown_count),
            "stat_detail": f"{row.crown_count} crowns",
        }
        for i, row in enumerate(rows)
    ]


def compute_obsessive(db: Session, group_ids: List[str]) -> List[dict]:
    stmt = (
        select(
            Listen.user_id,
            TrackArtist.artist_id,
            Artist.artist_name,
            func.count().label("cnt"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id.in_(group_ids))
        .group_by(Listen.user_id, TrackArtist.artist_id, Artist.artist_name)
        .order_by(func.count().desc())
    )
    rows = db.execute(stmt).all()

    best_per_user: dict = {}
    for row in rows:
        if row.user_id not in best_per_user:
            best_per_user[row.user_id] = row

    sorted_users = sorted(best_per_user.values(), key=lambda r: -r.cnt)
    return [
        {
            "user_id": r.user_id,
            "rank": i + 1,
            "stat_value": float(r.cnt),
            "stat_detail": f"Listened to {r.artist_name} {r.cnt} times",
            "entity_id": r.artist_id,
            "entity_name": r.artist_name,
        }
        for i, r in enumerate(sorted_users)
    ]


def compute_basic(db: Session, group_ids: List[str]) -> List[dict]:
    # Single query for every (user, artist, play_count) pair in the group; both
    # each user's top-20 and their full artist set are derived in-memory. This
    # replaces the previous O(N^2) pattern (a full per-friend query inside a
    # per-user loop) with one query total.
    rows = db.execute(
        select(
            Listen.user_id,
            TrackArtist.artist_id,
            func.count().label("cnt"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .where(Listen.user_id.in_(group_ids))
        .group_by(Listen.user_id, TrackArtist.artist_id)
    ).all()

    counts_by_user: dict = defaultdict(list)
    user_all: dict = defaultdict(set)
    for r in rows:
        counts_by_user[r.user_id].append((r.artist_id, r.cnt))
        user_all[r.user_id].add(r.artist_id)

    user_top: dict = {}
    for uid in group_ids:
        ranked = sorted(counts_by_user.get(uid, []), key=lambda x: (-x[1], x[0]))
        user_top[uid] = set(a for a, _ in ranked[:20])

    results = []
    for uid in group_ids:
        if not user_top[uid]:
            continue
        overlaps = []
        for fid in group_ids:
            if fid == uid or not user_top[fid]:
                continue
            overlap = len(user_top[uid] & user_all[fid]) / len(user_top[uid]) * 100
            overlaps.append(overlap)

        if overlaps:
            avg_overlap = round(sum(overlaps) / len(overlaps), 1)
            results.append(
                {
                    "user_id": uid,
                    "stat_value": avg_overlap,
                    "stat_detail": f"{avg_overlap}% of top artists shared with friends",
                }
            )

    results.sort(key=lambda r: -r["stat_value"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


def compute_archaeologist(db: Session, group_ids: List[str]) -> List[dict]:
    artist_user_first = (
        select(
            TrackArtist.artist_id,
            Artist.artist_name,
            Listen.user_id,
            func.min(Listen.ts).label("first_listen"),
        )
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id.in_(group_ids))
        .group_by(TrackArtist.artist_id, Artist.artist_name, Listen.user_id)
    )
    rows = db.execute(artist_user_first).all()

    artist_listens: dict = defaultdict(list)
    for row in rows:
        ts = (
            row.first_listen
            if isinstance(row.first_listen, datetime)
            else datetime.fromisoformat(str(row.first_listen))
        )
        artist_listens[row.artist_id].append((row.user_id, ts, row.artist_name))

    best_per_user: dict = {}
    for artist_id, entries in artist_listens.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda x: x[1])
        winner_uid, winner_ts, artist_name = entries[0]
        second_ts = entries[1][1]
        gap_days = (second_ts - winner_ts).days

        if winner_uid not in best_per_user or gap_days > best_per_user[winner_uid]["stat_value"]:
            best_per_user[winner_uid] = {
                "user_id": winner_uid,
                "stat_value": float(gap_days),
                "stat_detail": f"Found {artist_name} {gap_days} days before anyone else",
                "entity_id": artist_id,
                "entity_name": artist_name,
            }

    results = sorted(best_per_user.values(), key=lambda r: -r["stat_value"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


def compute_patient_zero(db: Session, group_ids: List[str]) -> List[dict]:
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
    )
    rows = db.execute(artist_user_first).all()

    artist_entries: dict = defaultdict(list)
    for row in rows:
        ts = (
            row.first_listen
            if isinstance(row.first_listen, datetime)
            else datetime.fromisoformat(str(row.first_listen))
        )
        artist_entries[row.artist_id].append((row.user_id, ts))

    artist_names = {}
    artist_ids_needed = set(artist_entries.keys())
    if artist_ids_needed:
        for a in db.execute(
            select(Artist.artist_id, Artist.artist_name).where(Artist.artist_id.in_(artist_ids_needed))
        ).all():
            artist_names[a.artist_id] = a.artist_name

    infections: dict = defaultdict(lambda: {"artists": 0, "friends": set(), "detail": []})
    for artist_id, entries in artist_entries.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda x: x[1])
        winner = entries[0][0]
        infected_count = len(entries) - 1
        for uid, _ in entries[1:]:
            infections[winner]["friends"].add(uid)
        infections[winner]["artists"] += 1
        infections[winner]["detail"].append(
            {
                "artist_name": artist_names.get(artist_id, artist_id),
                "artist_id": artist_id,
                "friend_count": infected_count,
            }
        )

    results = []
    for uid, data in infections.items():
        friend_count = len(data["friends"])
        detail = sorted(data["detail"], key=lambda d: -d["friend_count"])[:10]
        results.append(
            {
                "user_id": uid,
                "stat_value": float(friend_count),
                "stat_detail": f"Infected {friend_count} friends across {data['artists']} artists",
                "infections_detail": detail,
            }
        )

    results.sort(key=lambda r: -r["stat_value"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


def compute_completionist(db: Session, group_ids: List[str]) -> List[dict]:
    best_per_user: dict = {}
    for uid in group_ids:
        user_tracks_stmt = (
            select(
                TrackArtist.artist_id,
                Artist.artist_name,
                func.count(func.distinct(Listen.track_id)).label("unique_tracks"),
            )
            .select_from(Listen)
            .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
            .join(Artist, TrackArtist.artist_id == Artist.artist_id)
            .where(Listen.user_id == uid)
            .group_by(TrackArtist.artist_id, Artist.artist_name)
        )
        for row in db.execute(user_tracks_stmt).all():
            if uid not in best_per_user or row.unique_tracks > best_per_user[uid]["stat_value"]:
                best_per_user[uid] = {
                    "user_id": uid,
                    "stat_value": float(row.unique_tracks),
                    "stat_detail": f"{row.unique_tracks} tracks by {row.artist_name}",
                    "entity_id": row.artist_id,
                    "entity_name": row.artist_name,
                }

    results = sorted(best_per_user.values(), key=lambda r: -r["stat_value"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


def compute_genre_snob(db: Session, group_ids: List[str]) -> List[dict]:
    # One query for every (user, genre) pair in the group instead of one query
    # per user.
    rows = db.execute(
        select(Listen.user_id, ArtistGenre.genre)
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(ArtistGenre, TrackArtist.artist_id == ArtistGenre.artist_id)
        .where(Listen.user_id.in_(group_ids))
        .group_by(Listen.user_id, ArtistGenre.genre)
    ).all()
    user_genres: dict = defaultdict(set)
    for r in rows:
        user_genres[r.user_id].add(r.genre)

    results = []
    for uid in group_ids:
        if not user_genres.get(uid):
            continue
        all_friend_genres = set()
        for fid in group_ids:
            if fid != uid:
                all_friend_genres.update(user_genres.get(fid, set()))
        exclusive = user_genres[uid] - all_friend_genres
        if exclusive:
            results.append(
                {
                    "user_id": uid,
                    "stat_value": float(len(exclusive)),
                    "stat_detail": f"Listens to {len(exclusive)} genres none of your friends touch",
                }
            )

    results.sort(key=lambda r: -r["stat_value"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


def compute_time_traveler(db: Session, group_ids: List[str]) -> List[dict]:
    results = []
    for uid in group_ids:
        stmt = (
            select(Album.release_date)
            .select_from(Listen)
            .join(Track, Listen.track_id == Track.track_id)
            .join(Album, Track.album_id == Album.album_id)
            .where(Listen.user_id == uid, Album.release_date.isnot(None))
        )
        dates = [r[0] for r in db.execute(stmt).all() if r[0]]
        if not dates:
            continue
        years = sorted([d.year for d in dates])
        median_year = years[len(years) // 2]
        results.append(
            {
                "user_id": uid,
                "stat_value": float(median_year),
                "stat_detail": f"Median album from {median_year}",
            }
        )

    results.sort(key=lambda r: r["stat_value"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


def compute_streak(db: Session, group_ids: List[str]) -> List[dict]:
    results = []
    for uid in group_ids:
        stmt = select(Listen.ts).where(Listen.user_id == uid).order_by(Listen.ts)
        rows = db.execute(stmt).all()
        if not rows:
            continue

        days = sorted(
            set((r[0] if isinstance(r[0], datetime) else datetime.fromisoformat(str(r[0]))).date() for r in rows)
        )

        if not days:
            continue

        max_streak = 1
        current = 1
        for i in range(1, len(days)):
            if (days[i] - days[i - 1]).days == 1:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 1

        today = datetime.now(timezone.utc).date()
        last_day = days[-1]
        if last_day >= today - timedelta(days=1):
            current_streak = current
        else:
            current_streak = 0

        results.append(
            {
                "user_id": uid,
                "stat_value": float(max_streak),
                "stat_detail": f"Longest streak: {max_streak} days",
                "current_streak": current_streak,
            }
        )

    results.sort(key=lambda r: -r["stat_value"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


def compute_hypebeast(db: Session, group_ids: List[str]) -> List[dict]:
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=30)
    prior_start = now - timedelta(days=60)

    results = []
    for uid in group_ids:
        recent = (
            db.execute(
                select(func.count()).select_from(Listen).where(Listen.user_id == uid, Listen.ts >= recent_start)
            ).scalar()
            or 0
        )

        prior = (
            db.execute(
                select(func.count())
                .select_from(Listen)
                .where(Listen.user_id == uid, Listen.ts >= prior_start, Listen.ts < recent_start)
            ).scalar()
            or 0
        )

        if prior >= 10:
            change = round((recent - prior) / prior * 100, 1)
            results.append(
                {
                    "user_id": uid,
                    "stat_value": change,
                    "stat_detail": f"Listening {'up' if change >= 0 else 'down'} {abs(change)}% this month",
                }
            )

    results.sort(key=lambda r: -r["stat_value"])
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


ALL_COMPUTE_FUNCTIONS = {
    "crown": compute_crown,
    "obsessive": compute_obsessive,
    "basic": compute_basic,
    "archaeologist": compute_archaeologist,
    "patient_zero": compute_patient_zero,
    "completionist": compute_completionist,
    "genre_snob": compute_genre_snob,
    "time_traveler": compute_time_traveler,
    "streak": compute_streak,
    "hypebeast": compute_hypebeast,
}
