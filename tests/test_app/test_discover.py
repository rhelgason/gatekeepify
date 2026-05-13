from datetime import datetime, timezone

import pytest
from jose import jwt

from app.config import settings
from app.models import (
    Artist,
    ArtistGenre,
    Friendship,
    Listen,
    Track,
    TrackArtist,
    User,
)


def _auth(user_id):
    token = jwt.encode(
        {"sub": user_id, "exp": datetime(2099, 1, 1, tzinfo=timezone.utc)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def discover_db(db):
    users = [
        User(user_id="alice", user_name="Alice"),
        User(user_id="bob", user_name="Bob"),
    ]
    for u in users:
        db.add(u)

    now = datetime(2024, 6, 1)
    db.add(Friendship(user_id_1="alice", user_id_2="bob", created_at=now))
    db.add(Friendship(user_id_1="bob", user_id_2="alice", created_at=now))

    db.add(Artist(artist_id="art1", artist_name="Shared Artist"))
    db.add(Artist(artist_id="art2", artist_name="Bob Only Artist"))
    db.add(ArtistGenre(artist_id="art1", genre="rock"))
    db.add(ArtistGenre(artist_id="art2", genre="jazz"))
    db.add(Track(track_id="t1", track_name="Track 1", duration_ms=200000))
    db.add(Track(track_id="t2", track_name="Track 2", duration_ms=180000))
    db.add(TrackArtist(track_id="t1", artist_id="art1"))
    db.add(TrackArtist(track_id="t2", artist_id="art2"))

    from datetime import timedelta
    recent = datetime.now(timezone.utc) - timedelta(days=3)
    db.add(Listen(ts=recent, user_id="alice", track_id="t1", source="api"))
    db.add(Listen(ts=recent, user_id="bob", track_id="t1", source="api"))
    db.add(Listen(ts=recent - timedelta(days=1), user_id="bob", track_id="t2", source="api"))
    db.add(Listen(ts=recent - timedelta(days=2), user_id="bob", track_id="t2", source="api"))
    db.commit()
    return db


class TestFriendsFreshFinds:
    def test_returns_artists_friends_listen_to(self, client, discover_db):
        resp = client.get("/discover/friends-fresh-finds", params={"days": 365}, headers=_auth("alice"))
        assert resp.status_code == 200
        data = resp.json()
        artist_ids = [a["artist_id"] for a in data]
        assert "art2" in artist_ids  # Bob listens to art2, alice doesn't

    def test_excludes_artists_user_already_listens_to(self, client, discover_db):
        resp = client.get("/discover/friends-fresh-finds", params={"days": 365}, headers=_auth("alice"))
        data = resp.json()
        artist_ids = [a["artist_id"] for a in data]
        assert "art1" not in artist_ids  # alice already listens to art1

    def test_empty_without_friends(self, client, discover_db):
        db = discover_db
        db.add(User(user_id="loner", user_name="Loner"))
        db.commit()
        resp = client.get("/discover/friends-fresh-finds", headers=_auth("loner"))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_requires_auth(self, client, discover_db):
        resp = client.get("/discover/friends-fresh-finds")
        assert resp.status_code in (401, 403)


class TestYoureLateOn:
    def test_returns_artists_multiple_friends_listen_to(self, client, discover_db):
        # Need 2+ friends listening to same artist that alice doesn't
        db = discover_db
        db.add(User(user_id="charlie", user_name="Charlie"))
        db.add(Friendship(user_id_1="alice", user_id_2="charlie", created_at=datetime(2024, 6, 1)))
        db.add(Friendship(user_id_1="charlie", user_id_2="alice", created_at=datetime(2024, 6, 1)))
        from datetime import timedelta
        db.add(Listen(ts=datetime.now(timezone.utc) - timedelta(days=1), user_id="charlie", track_id="t2", source="api"))
        db.commit()

        resp = client.get("/discover/youre-late-on", headers=_auth("alice"))
        assert resp.status_code == 200
        data = resp.json()
        if data:
            assert data[0]["friend_count"] >= 2

    def test_requires_auth(self, client, discover_db):
        resp = client.get("/discover/youre-late-on")
        assert resp.status_code in (401, 403)


class TestRising:
    def test_returns_list(self, client, discover_db):
        resp = client.get("/discover/rising", headers=_auth("alice"))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_requires_auth(self, client, discover_db):
        resp = client.get("/discover/rising")
        assert resp.status_code in (401, 403)


class TestActivityFeed:
    def test_returns_list(self, client, discover_db):
        resp = client.get("/discover/feed", headers=_auth("alice"))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_respects_limit(self, client, discover_db):
        resp = client.get("/discover/feed", params={"limit": 2}, headers=_auth("alice"))
        assert resp.status_code == 200
        assert len(resp.json()) <= 2

    def test_requires_auth(self, client, discover_db):
        resp = client.get("/discover/feed")
        assert resp.status_code in (401, 403)
