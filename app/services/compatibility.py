from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ArtistGenre, Listen, TrackArtist


def compute_compatibility(db: Session, user_id_1: str, user_id_2: str) -> dict:
    artists_1 = get_user_artists(db, user_id_1, 50)
    artists_2 = get_user_artists(db, user_id_2, 50)

    if not artists_1 or not artists_2:
        return {
            "score": 0,
            "artist_overlap": 0,
            "genre_overlap": 0,
            "top5_agreement": 0,
            "shared_artists": [],
            "only_you": [],
            "only_them": [],
            "shared_genres": [],
            "disagreement_genres": [],
        }

    artist_ids_1 = set(a["artist_id"] for a in artists_1)
    artist_ids_2 = set(a["artist_id"] for a in artists_2)

    shared_artist_ids = artist_ids_1 & artist_ids_2
    all_artist_ids = artist_ids_1 | artist_ids_2
    artist_jaccard = len(shared_artist_ids) / len(all_artist_ids) * 100 if all_artist_ids else 0

    genres_1 = get_user_genres(db, user_id_1)
    genres_2 = get_user_genres(db, user_id_2)
    shared_genres = genres_1 & genres_2
    all_genres = genres_1 | genres_2
    genre_jaccard = len(shared_genres) / len(all_genres) * 100 if all_genres else 0

    top5_1 = set(a["artist_id"] for a in artists_1[:5])
    top5_2 = set(a["artist_id"] for a in artists_2[:5])
    top5_overlap = len(top5_1 & top5_2) / 5 * 100

    score = round(artist_jaccard * 0.5 + genre_jaccard * 0.3 + top5_overlap * 0.2)

    artist_name_map = {a["artist_id"]: a["artist_name"] for a in artists_1 + artists_2}

    shared_artists = sorted(
        [artist_name_map[aid] for aid in shared_artist_ids if aid in artist_name_map],
        key=lambda n: n.lower(),
    )[:10]

    only_you = [artist_name_map[aid] for aid in (artist_ids_1 - artist_ids_2) if aid in artist_name_map][:5]
    only_them = [artist_name_map[aid] for aid in (artist_ids_2 - artist_ids_1) if aid in artist_name_map][:5]

    disagreement_genres = sorted(list((genres_1 - genres_2) | (genres_2 - genres_1)))[:5]

    return {
        "score": min(score, 100),
        "artist_overlap": round(artist_jaccard, 1),
        "genre_overlap": round(genre_jaccard, 1),
        "top5_agreement": round(top5_overlap, 1),
        "shared_artists": shared_artists,
        "only_you": only_you,
        "only_them": only_them,
        "shared_genres": sorted(list(shared_genres))[:10],
        "disagreement_genres": disagreement_genres,
    }


def compute_quick_score(db: Session, user_id_1: str, user_id_2: str) -> float:
    a1 = set(a["artist_id"] for a in get_user_artists(db, user_id_1, 50))
    a2 = set(a["artist_id"] for a in get_user_artists(db, user_id_2, 50))
    if not a1 or not a2:
        return 0.0
    return len(a1 & a2) / len(a1 | a2) * 100


def get_user_artists(db: Session, user_id: str, limit: int) -> list[dict]:
    stmt = (
        select(TrackArtist.artist_id, func.count().label("cnt"))
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .where(Listen.user_id == user_id)
        .group_by(TrackArtist.artist_id)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()

    if not rows:
        return []

    from app.models import Artist
    artist_ids = [r.artist_id for r in rows]
    names = {
        a.artist_id: a.artist_name
        for a in db.query(Artist).filter(Artist.artist_id.in_(artist_ids)).all()
    }

    return [
        {"artist_id": r.artist_id, "artist_name": names.get(r.artist_id, "Unknown"), "count": r.cnt}
        for r in rows
    ]


def get_user_genres(db: Session, user_id: str) -> set:
    stmt = (
        select(ArtistGenre.genre)
        .select_from(Listen)
        .join(TrackArtist, Listen.track_id == TrackArtist.track_id)
        .join(ArtistGenre, TrackArtist.artist_id == ArtistGenre.artist_id)
        .where(Listen.user_id == user_id)
        .group_by(ArtistGenre.genre)
    )
    return set(r[0] for r in db.execute(stmt).all())
