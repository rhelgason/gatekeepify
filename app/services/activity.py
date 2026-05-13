import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Artist, Listen, ListenSource, Track, TrackArtist


def generate_activity_feed(
    db: Session, user_ids: List[str], limit: int = 20, days: int = 7
) -> List[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    events = []

    for uid in user_ids:
        events.extend(_detect_binges(db, uid, since))
        events.extend(_detect_new_obsessions(db, uid, since))
        events.extend(_detect_milestones(db, uid))
        events.extend(_detect_late_to_party(db, uid, user_ids, since))
        events.extend(_detect_broken_streaks(db, uid))

    events.extend(_detect_crown_steals(db, user_ids, since))

    events.sort(key=lambda e: e["ts"], reverse=True)
    return events[:limit]


def _detect_binges(db: Session, user_id: str, since: datetime) -> List[dict]:
    rows = db.execute(
        select(Listen.ts, Listen.track_id, TrackArtist.artist_id, Artist.artist_name, Track.duration_ms)
        .join(Track, Listen.track_id == Track.track_id)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id == user_id, Listen.ts >= since, Listen.source == ListenSource.api.value)
        .order_by(Listen.ts)
    ).all()

    if len(rows) < 3:
        return []

    user_name = _get_user_name(db, user_id)
    events = []
    i = 0
    while i < len(rows):
        artist_id = rows[i].artist_id
        artist_name = rows[i].artist_name
        streak_start = i
        total_ms = 0

        while i < len(rows) and rows[i].artist_id == artist_id:
            total_ms += rows[i].duration_ms or 0
            i += 1

        streak_len = i - streak_start
        minutes = total_ms // 60000

        if minutes >= 60:
            hours = round(minutes / 60, 1)
            quip = _binge_quip(user_name, artist_name, hours, minutes)
            events.append({
                "type": "binge",
                "ts": rows[streak_start].ts.isoformat() if isinstance(rows[streak_start].ts, datetime) else str(rows[streak_start].ts),
                "user_id": user_id,
                "user_name": user_name,
                "artist_id": artist_id,
                "artist_name": artist_name,
                "message": quip,
                "stat": f"{minutes} min ({streak_len} tracks)",
                "emoji": "🔥",
            })

    return events


def _detect_new_obsessions(db: Session, user_id: str, since: datetime) -> List[dict]:
    rows = db.execute(
        select(Listen.ts, TrackArtist.artist_id, Artist.artist_name)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id == user_id, Listen.ts >= since, Listen.source == ListenSource.api.value)
        .order_by(Listen.ts)
    ).all()

    if not rows:
        return []

    # Check against ALL prior listens (both api and export) so we don't
    # re-trigger for artists the user has historical data for
    prior_artists = set(
        r[0] for r in db.execute(
            select(TrackArtist.artist_id)
            .select_from(Listen)
            .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
            .where(Listen.user_id == user_id, Listen.ts < since)
            .group_by(TrackArtist.artist_id)
        ).all()
    )

    user_name = _get_user_name(db, user_id)
    new_artist_listens: dict = defaultdict(list)
    for row in rows:
        if row.artist_id not in prior_artists:
            new_artist_listens[row.artist_id].append(row)

    events = []
    for artist_id, listens in new_artist_listens.items():
        if len(listens) >= 10:
            artist_name = listens[0].artist_name
            quip = _new_obsession_quip(user_name, artist_name, len(listens))
            events.append({
                "type": "new_obsession",
                "ts": listens[0].ts.isoformat() if isinstance(listens[0].ts, datetime) else str(listens[0].ts),
                "user_id": user_id,
                "user_name": user_name,
                "artist_id": artist_id,
                "artist_name": artist_name,
                "message": quip,
                "stat": f"{len(listens)} listens in first week",
                "emoji": "🆕",
            })

    return events


def _detect_milestones(db: Session, user_id: str) -> List[dict]:
    milestones = [1000, 500, 100]

    rows = db.execute(
        select(TrackArtist.artist_id, Artist.artist_name, func.count().label("cnt"))
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id == user_id)
        .group_by(TrackArtist.artist_id, Artist.artist_name)
        .order_by(func.count().desc())
    ).all()

    user_name = _get_user_name(db, user_id)
    events = []
    for row in rows:
        for m in milestones:
            if row.cnt >= m:
                last_listen = db.execute(
                    select(func.max(Listen.ts))
                    .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
                    .where(Listen.user_id == user_id, TrackArtist.artist_id == row.artist_id,
                           Listen.source == ListenSource.api.value)
                ).scalar()

                if last_listen:
                    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                    ts = last_listen if isinstance(last_listen, datetime) else datetime.fromisoformat(str(last_listen))
                    if ts < week_ago:
                        break

                quip = _milestone_quip(user_name, row.artist_name, m)
                events.append({
                    "type": "milestone",
                    "ts": last_listen.isoformat() if isinstance(last_listen, datetime) else str(last_listen),
                    "user_id": user_id,
                    "user_name": user_name,
                    "artist_id": row.artist_id,
                    "artist_name": row.artist_name,
                    "message": quip,
                    "stat": f"{row.cnt} listens",
                    "emoji": "🏆",
                })
                break

    return events


def _detect_late_to_party(
    db: Session, user_id: str, group_ids: List[str], since: datetime
) -> List[dict]:
    new_listens = db.execute(
        select(TrackArtist.artist_id, Artist.artist_name, func.min(Listen.ts).label("first"))
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id == user_id, Listen.ts >= since, Listen.source == ListenSource.api.value)
        .group_by(TrackArtist.artist_id, Artist.artist_name)
    ).all()

    prior_artists = set(
        r[0] for r in db.execute(
            select(TrackArtist.artist_id)
            .select_from(Listen)
            .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
            .where(Listen.user_id == user_id, Listen.ts < since)
            .group_by(TrackArtist.artist_id)
        ).all()
    )

    other_ids = [uid for uid in group_ids if uid != user_id]
    if not other_ids:
        return []

    user_name = _get_user_name(db, user_id)
    events = []
    for row in new_listens:
        if row.artist_id in prior_artists:
            continue

        friends_who_listen = db.execute(
            select(func.count(func.distinct(Listen.user_id)))
            .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
            .where(
                Listen.user_id.in_(other_ids),
                TrackArtist.artist_id == row.artist_id,
            )
        ).scalar() or 0

        if friends_who_listen >= 2:
            quip = _late_quip(user_name, row.artist_name, friends_who_listen)
            ts = row.first if isinstance(row.first, datetime) else datetime.fromisoformat(str(row.first))
            events.append({
                "type": "late_to_party",
                "ts": ts.isoformat(),
                "user_id": user_id,
                "user_name": user_name,
                "artist_id": row.artist_id,
                "artist_name": row.artist_name,
                "message": quip,
                "stat": f"{friends_who_listen} friends already listen",
                "emoji": "🐌",
            })

    return events


def _detect_crown_steals(db: Session, group_ids: List[str], since: datetime) -> List[dict]:
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

    artist_entries: dict = defaultdict(list)
    for row in rows:
        ts = row.first_listen if isinstance(row.first_listen, datetime) else datetime.fromisoformat(str(row.first_listen))
        artist_entries[row.artist_id].append({
            "user_id": row.user_id,
            "ts": ts,
            "artist_name": row.artist_name,
        })

    events = []
    for artist_id, entries in artist_entries.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda e: e["ts"])

        # Check if the current winner uploaded data recently (crown steal)
        winner = entries[0]
        runner_up = entries[1]
        if winner["ts"] >= since and runner_up["ts"] < since:
            # Winner's first listen is recent but runner_up's is old = winner just uploaded backdated data
            winner_name = _get_user_name(db, winner["user_id"])
            loser_name = _get_user_name(db, runner_up["user_id"])
            quip = _crown_steal_quip(winner_name, loser_name, winner["artist_name"])
            events.append({
                "type": "crown_stolen",
                "ts": winner["ts"].isoformat(),
                "user_id": winner["user_id"],
                "user_name": winner_name,
                "artist_id": artist_id,
                "artist_name": winner["artist_name"],
                "message": quip,
                "stat": f"Took crown from {loser_name}",
                "emoji": "👑",
            })

    return events


def _detect_broken_streaks(db: Session, user_id: str) -> List[dict]:
    rows = db.execute(
        select(Listen.ts).where(
            Listen.user_id == user_id, Listen.source == ListenSource.api.value
        ).order_by(Listen.ts)
    ).all()

    if not rows:
        return []

    days = sorted(set(
        (r[0] if isinstance(r[0], datetime) else datetime.fromisoformat(str(r[0]))).date()
        for r in rows
    ))

    if len(days) < 5:
        return []

    # Find the most recent streak
    streaks = []
    current_start = 0
    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days != 1:
            streak_len = i - current_start
            if streak_len >= 5:
                streaks.append((current_start, i - 1, streak_len))
            current_start = i
    # Final streak
    final_len = len(days) - current_start
    if final_len >= 5:
        streaks.append((current_start, len(days) - 1, final_len))

    if not streaks:
        return []

    # Check if the most recent streak ended in the last 7 days
    today = datetime.now(timezone.utc).date()
    last_streak = streaks[-1]
    streak_end = days[last_streak[1]]
    days_since_end = (today - streak_end).days

    if 1 <= days_since_end <= 7 and last_streak[2] >= 5:
        # Streak is broken (gap between streak end and today)
        # Make sure the streak isn't still active
        if days[-1] < today - timedelta(days=1):
            user_name = _get_user_name(db, user_id)
            quip = _streak_broken_quip(user_name, last_streak[2])
            return [{
                "type": "streak_broken",
                "ts": datetime.combine(streak_end, datetime.min.time()).isoformat(),
                "user_id": user_id,
                "user_name": user_name,
                "artist_id": None,
                "artist_name": None,
                "message": quip,
                "stat": f"{last_streak[2]}-day streak ended",
                "emoji": "💀",
            }]

    return []


def _get_user_name(db: Session, user_id: str) -> str:
    from app.models import User
    user = db.query(User).filter(User.user_id == user_id).first()
    return user.user_name if user else user_id


# --- Quip generators ---

def _binge_quip(user: str, artist: str, hours: float, minutes: int) -> str:
    quips = [
        f"{user} just spent {hours} hours on {artist}. Someone check on them.",
        f"{user} has been locked in with {artist} for {minutes} minutes. This is not normal behavior.",
        f"Breaking: {user} discovered the repeat button. {artist} on loop for {hours} hours.",
        f"{user} and {artist} need to get a room. {hours} hours straight.",
        f"Is {user} okay? That's {minutes} minutes of {artist} without stopping.",
        f"{user} just marathoned {artist} for {hours} hours. Touch grass.",
        f"Noise complaint filed. {user} has been playing {artist} for {hours} hours.",
        f"{user} apparently thinks {artist} will stop making music if they stop listening. {hours} hours.",
    ]
    return random.choice(quips)


def _new_obsession_quip(user: str, artist: str, count: int) -> str:
    quips = [
        f"{user} discovered {artist} and immediately went feral. {count} listens already.",
        f"New personality trait unlocked: {user} now listens to {artist}.",
        f"{user} found {artist} this week and has already played them {count} times. We've lost them.",
        f"Someone introduced {user} to {artist}. They've listened {count} times since. This is your fault.",
        f"{user} just discovered {artist}. Don't worry, they'll tell everyone about it.",
        f"Day 1 of {user} knowing {artist} exists: {count} plays. This will only get worse.",
        f"{user} stumbled into {artist} and decided to make it their whole week. {count} plays.",
    ]
    return random.choice(quips)


def _milestone_quip(user: str, artist: str, milestone: int) -> str:
    if milestone >= 1000:
        quips = [
            f"{user} hit {milestone} listens on {artist}. At this point it's a legal dependency.",
            f"BREAKING: {user} has listened to {artist} {milestone} times. Scientists are concerned.",
            f"{milestone} plays of {artist}. {user} should be receiving royalties at this point.",
            f"{user} just hit {milestone} on {artist}. This is no longer a hobby, it's a lifestyle.",
        ]
    elif milestone >= 500:
        quips = [
            f"{user} crossed 500 listens on {artist}. Halfway to needing an intervention.",
            f"500 plays. {user} and {artist} are in a committed relationship now.",
            f"{user} has officially played {artist} 500 times. The neighbors know every lyric.",
        ]
    else:
        quips = [
            f"{user} hit 100 listens on {artist}. The obsession is taking shape.",
            f"Century club: {user} has played {artist} 100 times.",
            f"{user} cracked 100 plays on {artist}. That's... a lot of commitment.",
        ]
    return random.choice(quips)


def _late_quip(user: str, artist: str, friend_count: int) -> str:
    quips = [
        f"{user} finally listened to {artist}. Only {friend_count} friends were ahead of them.",
        f"Welcome to {artist}, {user}. Everyone else has been here for a while.",
        f"{user} showed up late to the {artist} party. {friend_count} friends are already inside.",
        f"Better late than never: {user} discovered {artist}. {friend_count} friends are rolling their eyes.",
        f"{user} just found out about {artist}. {friend_count} of their friends: 'we been knew.'",
        f"Fashionably late: {user} finally listened to {artist}. Only about a year behind {friend_count} friends.",
    ]
    return random.choice(quips)


def _crown_steal_quip(thief: str, victim: str, artist: str) -> str:
    quips = [
        f"{thief} just snatched the {artist} crown from {victim}. Cold blooded.",
        f"Crown heist: {thief} uploaded proof they heard {artist} before {victim}. Drama.",
        f"{victim} thought they discovered {artist} first. {thief} just proved otherwise.",
        f"Plot twist: {thief} had {artist} on repeat before {victim} even knew they existed.",
        f"{thief} pulled receipts on {artist}. {victim}'s crown has been revoked.",
        f"The {artist} crown just changed hands. {thief} dethroned {victim}. Brutal.",
        f"{victim} held the {artist} crown for a while. {thief} just ended that era.",
    ]
    return random.choice(quips)


def _streak_broken_quip(user: str, streak_days: int) -> str:
    quips = [
        f"{user}'s {streak_days}-day listening streak just died. Rest in peace.",
        f"Moment of silence: {user} broke their {streak_days}-day streak. Life got in the way.",
        f"{user} went {streak_days} days without missing a day of music. That's over now.",
        f"RIP to {user}'s {streak_days}-day streak. Gone but not forgotten.",
        f"{user} forgot to listen to music yesterday. {streak_days}-day streak: destroyed.",
        f"After {streak_days} days, {user} finally touched grass. Streak broken.",
        f"{user}'s {streak_days}-day streak just flatlined. The silence is deafening.",
    ]
    return random.choice(quips)
