import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Artist, AuditLog, Friendship, Listen, ListenSource, Track, TrackArtist, User


def generate_activity_feed(
    db: Session, user_ids: List[str], limit: int = 20, days: int = 7
) -> List[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    events = []

    upload_user_ids = set()
    for uid in user_ids:
        upload_events = _detect_uploads(db, uid, since)
        if upload_events:
            upload_user_ids.add(uid)
        events.extend(upload_events)
        events.extend(_detect_binges(db, uid, since))
        events.extend(_detect_new_obsessions(db, uid, since))
        events.extend(_detect_milestones(db, uid))
        events.extend(_detect_late_to_party(db, uid, user_ids, since))
        events.extend(_detect_broken_streaks(db, uid))
        events.extend(_detect_track_repeats(db, uid, since))

    crown_events = _detect_crown_steals(db, user_ids, since)
    for uid in upload_user_ids:
        user_crowns = [e for e in crown_events if e["user_id"] == uid]
        if len(user_crowns) > 3:
            kept = user_crowns[:3]
            rest_count = len(user_crowns) - 3
            user_name = kept[0]["user_name"]
            kept.append({
                "type": "crown_stolen",
                "ts": user_crowns[3]["ts"],
                "user_id": uid,
                "user_name": user_name,
                "artist_id": None,
                "artist_name": None,
                "message": f"...and {rest_count} more crowns stolen by {user_name}'s data upload.",
                "stat": f"+{rest_count} more",
                "emoji": "👑",
            })
            crown_events = [e for e in crown_events if e["user_id"] != uid] + kept

    events.extend(crown_events)
    events.extend(_detect_new_users(db, user_ids, since))
    events.extend(_detect_new_friendships(db, user_ids, since))

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
    user_obj = db.query(User).filter(User.user_id == user_id).first()
    if user_obj and user_obj.created_at:
        created = user_obj.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if created >= since:
            return []

    rows = db.execute(
        select(Listen.ts, TrackArtist.artist_id, Artist.artist_name)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id == user_id, Listen.ts >= since, Listen.source == ListenSource.api.value)
        .order_by(Listen.ts)
    ).all()

    if not rows:
        return []

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
        if len(listens) >= 20:
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
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
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
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
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


def _detect_track_repeats(db: Session, user_id: str, since: datetime) -> List[dict]:
    rows = db.execute(
        select(
            Listen.track_id,
            Track.track_name,
            TrackArtist.artist_id,
            Artist.artist_name,
            func.count().label("play_count"),
            func.max(Listen.ts).label("last_ts"),
        )
        .join(Track, Listen.track_id == Track.track_id)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(Artist, TrackArtist.artist_id == Artist.artist_id)
        .where(Listen.user_id == user_id, Listen.ts >= since, Listen.source == ListenSource.api.value)
        .group_by(Listen.track_id, Track.track_name, TrackArtist.artist_id, Artist.artist_name)
        .having(func.count() >= 10)
    ).all()

    if not rows:
        return []

    user_name = _get_user_name(db, user_id)
    events = []
    for row in rows:
        ts = row.last_ts if isinstance(row.last_ts, datetime) else datetime.fromisoformat(str(row.last_ts))
        quip = _track_repeat_quip(user_name, row.track_name, row.artist_name, row.play_count)
        events.append({
            "type": "track_repeat",
            "ts": ts.isoformat(),
            "user_id": user_id,
            "user_name": user_name,
            "artist_id": row.artist_id,
            "artist_name": row.artist_name,
            "message": quip,
            "stat": f"{row.track_name} — {row.play_count} plays",
            "emoji": "🔂",
        })
    return events


def _detect_uploads(db: Session, user_id: str, since: datetime) -> List[dict]:
    rows = db.execute(
        select(AuditLog.ts, AuditLog.details)
        .where(
            AuditLog.user_id == user_id,
            AuditLog.action == "backfill.upload",
            AuditLog.ts >= since,
            AuditLog.status == "success",
        )
        .order_by(AuditLog.ts.desc())
    ).all()

    if not rows:
        return []

    user_name = _get_user_name(db, user_id)
    events = []
    for row in rows:
        details = json.loads(row.details) if row.details else {}
        accepted = details.get("total_listens_accepted", 0)
        if accepted == 0:
            continue
        ts = row.ts if isinstance(row.ts, datetime) else datetime.fromisoformat(str(row.ts))
        quip = _upload_quip(user_name, accepted)
        events.append({
            "type": "data_uploaded",
            "ts": ts.isoformat(),
            "user_id": user_id,
            "user_name": user_name,
            "artist_id": None,
            "artist_name": None,
            "message": quip,
            "stat": f"{accepted:,} listens uploaded",
            "emoji": "📦",
        })

    return events


def _detect_new_users(db: Session, user_ids: List[str], since: datetime) -> List[dict]:
    rows = db.execute(
        select(User.user_id, User.user_name, User.created_at)
        .where(User.created_at >= since)
        .order_by(User.created_at.desc())
    ).all()

    viewer_set = set(user_ids)
    viewer_friends = set()
    for uid in user_ids:
        friend_rows = db.execute(
            select(Friendship.user_id_2).where(Friendship.user_id_1 == uid)
        ).all()
        for r in friend_rows:
            viewer_friends.add(r[0])

    events = []
    for row in rows:
        if row.user_id in viewer_set:
            continue
        new_user_friends = set(
            r[0] for r in db.execute(
                select(Friendship.user_id_2).where(Friendship.user_id_1 == row.user_id)
            ).all()
        )
        has_mutual = bool(new_user_friends & viewer_friends) or bool(new_user_friends & viewer_set)
        if not has_mutual:
            continue
        ts = row.created_at if isinstance(row.created_at, datetime) else datetime.fromisoformat(str(row.created_at))
        name = row.user_name or row.user_id
        quip = _new_user_quip(name)
        events.append({
            "type": "user_joined",
            "ts": ts.isoformat(),
            "user_id": row.user_id,
            "user_name": name,
            "artist_id": None,
            "artist_name": None,
            "message": quip,
            "stat": None,
            "emoji": "👋",
        })
    return events


def _detect_new_friendships(db: Session, user_ids: List[str], since: datetime) -> List[dict]:
    rows = db.execute(
        select(Friendship.user_id_1, Friendship.user_id_2, Friendship.created_at)
        .where(
            Friendship.created_at >= since,
            Friendship.user_id_1 < Friendship.user_id_2,
        )
        .order_by(Friendship.created_at.desc())
    ).all()

    events = []
    user_id_set = set(user_ids)
    for row in rows:
        if row.user_id_1 not in user_id_set and row.user_id_2 not in user_id_set:
            continue
        ts = row.created_at if isinstance(row.created_at, datetime) else datetime.fromisoformat(str(row.created_at))
        name1 = _get_user_name(db, row.user_id_1)
        name2 = _get_user_name(db, row.user_id_2)
        quip = _friendship_quip(name1, name2)
        events.append({
            "type": "new_friendship",
            "ts": ts.isoformat(),
            "user_id": row.user_id_1,
            "user_name": name1,
            "artist_id": None,
            "artist_name": None,
            "message": quip,
            "stat": None,
            "emoji": "🤝",
        })
    return events


def _get_user_name(db: Session, user_id: str) -> str:
    user = db.query(User).filter(User.user_id == user_id).first()
    return user.user_name if user else user_id


# --- Quip generators ---

def _pick(quips: list, *seed_parts: str) -> str:
    seed = hashlib.md5("|".join(str(s) for s in seed_parts).encode()).hexdigest()
    idx = int(seed, 16) % len(quips)
    return quips[idx]


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
    return _pick(quips, "binge", user, artist)


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
    return _pick(quips, "obsession", user, artist)


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
    return _pick(quips, "milestone", user, artist, str(milestone))


def _late_quip(user: str, artist: str, friend_count: int) -> str:
    quips = [
        f"{user} finally listened to {artist}. Only {friend_count} friends were ahead of them.",
        f"Welcome to {artist}, {user}. Everyone else has been here for a while.",
        f"{user} showed up late to the {artist} party. {friend_count} friends are already inside.",
        f"Better late than never: {user} discovered {artist}. {friend_count} friends are rolling their eyes.",
        f"{user} just found out about {artist}. {friend_count} of their friends: 'we been knew.'",
        f"Fashionably late: {user} finally listened to {artist}. Only about a year behind {friend_count} friends.",
    ]
    return _pick(quips, "late", user, artist)


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
    return _pick(quips, "crown", thief, victim, artist)


def _upload_quip(user: str, accepted: int) -> str:
    quips = [
        f"{user} just uploaded {accepted:,} listens. The receipts are in.",
        f"{user} dropped {accepted:,} listens worth of proof. Crowns are about to change hands.",
        f"Data dump incoming: {user} just uploaded {accepted:,} listens. Check your crowns.",
        f"{user} pulled up with {accepted:,} listens of listening history. This changes everything.",
        f"{user} just submitted {accepted:,} listens to the record. Your move.",
        f"Breaking: {user} has entered the chat with {accepted:,} listens. Thrones are shaking.",
        f"{user} uploaded their Spotify data. {accepted:,} listens. The leaderboard will never be the same.",
    ]
    return _pick(quips, "upload", user, str(accepted))


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
    return _pick(quips, "streak", user, str(streak_days))


def _track_repeat_quip(user: str, track: str, artist: str, count: int) -> str:
    quips = [
        f"{user} played \"{track}\" by {artist} {count} times. Someone intervene.",
        f"\"{track}\" by {artist}, {count} times. {user} is stuck in a loop.",
        f"{user} has listened to \"{track}\" {count} times this week. This is not healthy.",
        f"Repeat offender: {user} can't stop playing \"{track}\" by {artist}. {count} plays.",
        f"{user} put \"{track}\" on repeat and forgot about it. {count} plays and counting.",
        f"{count} plays of \"{track}\" by {artist}. {user} has memorized every millisecond.",
        f"{user} and \"{track}\" by {artist} are in a committed relationship. {count} plays.",
    ]
    return _pick(quips, "track_repeat", user, track, artist)


def _new_user_quip(user: str) -> str:
    quips = [
        f"{user} just joined Gatekeepify. The competition just got stiffer.",
        f"New challenger approaching: {user} has entered the arena.",
        f"{user} just signed up. Time to prove your taste is better than theirs.",
        f"Welcome {user} to the platform. Add them before they gatekeep you.",
        f"{user} is here. Another person to argue about music with.",
        f"Fresh blood: {user} just joined. Send that friend request.",
        f"{user} just showed up. The leaderboard is about to change.",
    ]
    return _pick(quips, "joined", user)


def _friendship_quip(user1: str, user2: str) -> str:
    quips = [
        f"{user1} and {user2} are now friends. The gatekeeping begins.",
        f"{user1} and {user2} linked up. Crowns are about to be contested.",
        f"New rivalry unlocked: {user1} vs {user2}.",
        f"{user1} and {user2} are now comparing listening histories. This should be fun.",
        f"{user1} added {user2}. Let the judgment commence.",
        f"{user1} and {user2} are friends now. Someone's about to find out they're basic.",
    ]
    return _pick(quips, "friendship", user1, user2)
