import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Album, Listen, ListenSource, Track, TrackArtist

logger = logging.getLogger("gatekeepify.anomaly")


def analyze_user_export(db: Session, user_id: str) -> dict:
    export_listens = db.execute(
        select(Listen.ts, Listen.track_id)
        .where(Listen.user_id == user_id, Listen.source == ListenSource.export.value)
        .order_by(Listen.ts)
    ).all()

    if not export_listens:
        return {"score": 100, "flags": [], "export_count": 0}

    flags = []
    timestamps = [
        r.ts if isinstance(r.ts, datetime) else datetime.fromisoformat(str(r.ts))
        for r in export_listens
    ]

    # 1. Rapid-fire listens (more than 1 per 30 seconds)
    rapid_count = 0
    for i in range(1, len(timestamps)):
        gap = (timestamps[i] - timestamps[i - 1]).total_seconds()
        if 0 < gap < 30:
            rapid_count += 1
    if rapid_count > 0:
        rapid_pct = round(rapid_count / len(timestamps) * 100, 1)
        if rapid_pct > 5:
            flags.append({
                "type": "rapid_fire",
                "severity": "high" if rapid_pct > 20 else "medium",
                "detail": f"{rapid_count} listens ({rapid_pct}%) within 30s of each other",
            })

    # 2. Perfectly even spacing (bot-like)
    if len(timestamps) >= 20:
        gaps = [(timestamps[i] - timestamps[i - 1]).total_seconds() for i in range(1, len(timestamps))]
        gaps = [g for g in gaps if g > 0]
        if gaps:
            gap_counts = Counter(int(g) for g in gaps)
            most_common_gap, most_common_count = gap_counts.most_common(1)[0]
            if most_common_count > len(gaps) * 0.5 and most_common_gap < 600:
                flags.append({
                    "type": "even_spacing",
                    "severity": "high",
                    "detail": f"{most_common_count} listens with identical {most_common_gap}s gaps ({round(most_common_count / len(gaps) * 100)}%)",
                })

    # 3. Single-day dump (many listens on one date suggesting bulk fabrication)
    date_counts = Counter(ts.date() for ts in timestamps)
    for date, count in date_counts.most_common(5):
        if count > 200:
            flags.append({
                "type": "single_day_dump",
                "severity": "medium",
                "detail": f"{count} export listens on {date}",
            })

    # 4. Backdated clusters (many different artists all first-listened on the same date)
    track_first: dict = {}
    for ts, track_id in zip(timestamps, [r.track_id for r in export_listens]):
        if track_id not in track_first:
            track_first[track_id] = ts

    first_listen_dates = Counter(ts.date() for ts in track_first.values())
    for date, count in first_listen_dates.most_common(3):
        if count > 50:
            flags.append({
                "type": "backdated_cluster",
                "severity": "medium",
                "detail": f"First listen for {count} different tracks on {date}",
            })

    # 5. Pre-release listens (already caught during upload, but flag retroactively)
    pre_release = db.execute(
        select(func.count())
        .select_from(Listen)
        .join(Track, Listen.track_id == Track.track_id)
        .join(Album, Track.album_id == Album.album_id)
        .where(
            Listen.user_id == user_id,
            Listen.source == ListenSource.export.value,
            Album.release_date.isnot(None),
            Listen.ts < func.date(Album.release_date),
        )
    ).scalar() or 0
    if pre_release > 0:
        flags.append({
            "type": "pre_release",
            "severity": "high",
            "detail": f"{pre_release} listens before track release date",
        })

    # 6. Export-to-API ratio (high export ratio with very few API listens is suspicious)
    api_count = db.execute(
        select(func.count())
        .select_from(Listen)
        .where(Listen.user_id == user_id, Listen.source == ListenSource.api.value)
    ).scalar() or 0

    export_count = len(export_listens)
    total = api_count + export_count
    if total > 100 and api_count < total * 0.02:
        flags.append({
            "type": "low_api_ratio",
            "severity": "low",
            "detail": f"Only {api_count} API-verified listens out of {total} total ({round(api_count / total * 100, 1)}%)",
        })

    # Calculate trust score (100 = fully trusted, 0 = highly suspicious)
    penalty = 0
    for flag in flags:
        if flag["severity"] == "high":
            penalty += 25
        elif flag["severity"] == "medium":
            penalty += 10
        elif flag["severity"] == "low":
            penalty += 5
    score = max(0, 100 - penalty)

    return {
        "score": score,
        "flags": flags,
        "export_count": export_count,
        "api_count": api_count,
    }
