from datetime import datetime, timezone

import pytest

from app.models import (
    Artist,
    ArtistGenre,
    Listen,
    ListenSource,
    Track,
    TrackArtist,
    User,
)
from app.services.compatibility import (
    compute_quick_score,
    get_user_artists,
    get_user_genres,
)


@pytest.fixture()
def two_users(db):
    user1 = User(user_id="compat_u1", user_name="User 1", created_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    user2 = User(user_id="compat_u2", user_name="User 2", created_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
    db.add_all([user1, user2])

    for i in range(3):
        db.add(Artist(artist_id=f"compat_a{i}", artist_name=f"Compat Artist {i}"))
        db.add(Track(track_id=f"compat_t{i}", track_name=f"Compat Track {i}", duration_ms=200000))
        db.flush()
        db.add(TrackArtist(track_id=f"compat_t{i}", artist_id=f"compat_a{i}"))
        db.add(ArtistGenre(artist_id=f"compat_a{i}", genre=f"genre_{i}"))

    db.add(Listen(ts=datetime(2024, 3, 1), user_id="compat_u1", track_id="compat_t0", source=ListenSource.api.value))
    db.add(Listen(ts=datetime(2024, 3, 2), user_id="compat_u1", track_id="compat_t1", source=ListenSource.api.value))
    db.add(Listen(ts=datetime(2024, 3, 1), user_id="compat_u2", track_id="compat_t0", source=ListenSource.api.value))
    db.add(Listen(ts=datetime(2024, 3, 2), user_id="compat_u2", track_id="compat_t2", source=ListenSource.api.value))
    db.commit()
    return user1, user2


class TestGetUserArtists:
    def test_returns_artist_data(self, db, two_users):
        artists = get_user_artists(db, "compat_u1", limit=50)
        artist_ids = [a["artist_id"] for a in artists]
        assert "compat_a0" in artist_ids
        assert "compat_a1" in artist_ids

    def test_empty_for_unknown_user(self, db, two_users):
        artists = get_user_artists(db, "nonexistent", limit=50)
        assert len(artists) == 0


class TestGetUserGenres:
    def test_returns_genres(self, db, two_users):
        genres = get_user_genres(db, "compat_u1")
        assert "genre_0" in genres
        assert "genre_1" in genres


class TestComputeQuickScore:
    def test_partial_overlap(self, db, two_users):
        score = compute_quick_score(db, "compat_u1", "compat_u2")
        assert 0 < score < 100

    def test_no_overlap(self, db):
        u1 = User(user_id="no_ov_1", user_name="No Ov 1", created_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
        u2 = User(user_id="no_ov_2", user_name="No Ov 2", created_at=datetime(2024, 1, 1, tzinfo=timezone.utc))
        db.add_all([u1, u2])

        for uid, idx in [("no_ov_1", 10), ("no_ov_2", 20)]:
            db.add(Artist(artist_id=f"nov_a{idx}", artist_name=f"Nov Artist {idx}"))
            db.add(Track(track_id=f"nov_t{idx}", track_name=f"Nov Track {idx}", duration_ms=200000))
            db.flush()
            db.add(TrackArtist(track_id=f"nov_t{idx}", artist_id=f"nov_a{idx}"))
            db.add(Listen(ts=datetime(2024, 3, 1), user_id=uid, track_id=f"nov_t{idx}", source=ListenSource.api.value))
        db.commit()

        score = compute_quick_score(db, "no_ov_1", "no_ov_2")
        assert score == 0
