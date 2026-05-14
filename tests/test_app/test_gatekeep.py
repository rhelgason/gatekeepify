from datetime import datetime, timezone

import pytest
from jose import jwt

from app.config import settings
from app.models import (
    Album,
    Artist,
    ArtistGenre,
    Friendship,
    Listen,
    ListenSource,
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
def social_db(db):
    """Three users, two friendships, listening data across multiple artists."""
    users = [
        User(user_id="alice", user_name="Alice", created_at=datetime(2024, 1, 1)),
        User(user_id="bob", user_name="Bob", created_at=datetime(2024, 1, 1)),
        User(user_id="charlie", user_name="Charlie", created_at=datetime(2024, 1, 1)),
    ]
    for u in users:
        db.add(u)

    now = datetime(2024, 6, 1)
    friendships = [
        Friendship(user_id_1="alice", user_id_2="bob", created_at=now),
        Friendship(user_id_1="bob", user_id_2="alice", created_at=now),
        Friendship(user_id_1="alice", user_id_2="charlie", created_at=now),
        Friendship(user_id_1="charlie", user_id_2="alice", created_at=now),
    ]
    for f in friendships:
        db.add(f)

    albums = [
        Album(album_id="alb_rh", album_name="OK Computer"),
        Album(album_id="alb_bf", album_name="For Emma"),
    ]
    for a in albums:
        db.add(a)

    artists = [
        Artist(artist_id="art_rh", artist_name="Radiohead"),
        Artist(artist_id="art_bf", artist_name="Bon Iver"),
    ]
    for a in artists:
        db.add(a)

    db.add(ArtistGenre(artist_id="art_rh", genre="alternative rock"))
    db.add(ArtistGenre(artist_id="art_bf", genre="indie folk"))

    tracks = [
        Track(track_id="trk_pa", track_name="Paranoid Android", album_id="alb_rh", duration_ms=384000),
        Track(track_id="trk_kp", track_name="Karma Police", album_id="alb_rh", duration_ms=264000),
        Track(track_id="trk_sk", track_name="Skinny Love", album_id="alb_bf", duration_ms=232000),
    ]
    for t in tracks:
        db.add(t)

    track_artists = [
        TrackArtist(track_id="trk_pa", artist_id="art_rh"),
        TrackArtist(track_id="trk_kp", artist_id="art_rh"),
        TrackArtist(track_id="trk_sk", artist_id="art_bf"),
    ]
    for ta in track_artists:
        db.add(ta)

    listens = [
        Listen(ts=datetime(2017, 3, 1, 10, 0), user_id="alice", track_id="trk_pa", source=ListenSource.api.value),
        Listen(ts=datetime(2017, 3, 2, 10, 0), user_id="alice", track_id="trk_pa", source=ListenSource.api.value),
        Listen(ts=datetime(2017, 6, 1, 10, 0), user_id="alice", track_id="trk_kp", source=ListenSource.api.value),
        Listen(ts=datetime(2021, 1, 15, 10, 0), user_id="bob", track_id="trk_pa", source=ListenSource.export.value),
        Listen(ts=datetime(2021, 2, 1, 10, 0), user_id="bob", track_id="trk_kp", source=ListenSource.api.value),
        Listen(ts=datetime(2023, 8, 1, 10, 0), user_id="charlie", track_id="trk_pa", source=ListenSource.api.value),
        Listen(ts=datetime(2019, 5, 1, 10, 0), user_id="bob", track_id="trk_sk", source=ListenSource.api.value),
        Listen(ts=datetime(2019, 5, 2, 10, 0), user_id="bob", track_id="trk_sk", source=ListenSource.api.value),
        Listen(ts=datetime(2022, 11, 1, 10, 0), user_id="alice", track_id="trk_sk", source=ListenSource.export.value),
    ]
    for listen in listens:
        db.add(listen)

    db.commit()
    return db


class TestGatekeepArtist:
    def test_returns_entries_sorted_by_first_listen(self, client, social_db):
        resp = client.get("/gatekeep/artist/art_rh", headers=_auth("alice"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["artist_id"] == "art_rh"
        assert data["artist_name"] == "Radiohead"
        assert len(data["entries"]) == 3
        assert data["entries"][0]["user_id"] == "alice"
        assert data["entries"][1]["user_id"] == "bob"
        assert data["entries"][2]["user_id"] == "charlie"

    def test_first_entry_is_winner(self, client, social_db):
        resp = client.get("/gatekeep/artist/art_rh", headers=_auth("alice"))
        entries = resp.json()["entries"]
        assert entries[0]["is_winner"] is True
        assert entries[1]["is_winner"] is False
        assert entries[2]["is_winner"] is False

    def test_first_listen_source_is_correct(self, client, social_db):
        resp = client.get("/gatekeep/artist/art_rh", headers=_auth("alice"))
        entries = resp.json()["entries"]
        assert entries[0]["first_listen_source"] == "api"
        assert entries[1]["first_listen_source"] == "export"
        assert entries[2]["first_listen_source"] == "api"

    def test_verified_listens_count(self, client, social_db):
        resp = client.get("/gatekeep/artist/art_rh", headers=_auth("alice"))
        entries = resp.json()["entries"]
        assert entries[0]["total_listens"] == 3
        assert entries[0]["verified_listens"] == 3
        assert entries[1]["total_listens"] == 2
        assert entries[1]["verified_listens"] == 1

    def test_only_includes_friends(self, client, social_db):
        resp = client.get("/gatekeep/artist/art_rh", headers=_auth("bob"))
        entries = resp.json()["entries"]
        user_ids = {e["user_id"] for e in entries}
        assert user_ids == {"alice", "bob"}
        assert "charlie" not in user_ids

    def test_artist_not_found(self, client, social_db):
        resp = client.get("/gatekeep/artist/nonexistent", headers=_auth("alice"))
        assert resp.status_code == 404

    def test_no_listens_returns_empty_entries(self, client, social_db):
        resp = client.get("/gatekeep/artist/art_bf", headers=_auth("charlie"))
        entries = resp.json()["entries"]
        user_ids = {e["user_id"] for e in entries}
        assert "charlie" not in user_ids
        assert "alice" in user_ids


class TestGatekeepTrack:
    def test_returns_track_comparison(self, client, social_db):
        resp = client.get("/gatekeep/track/trk_pa", headers=_auth("alice"))
        assert resp.status_code == 200
        data = resp.json()
        assert data["track_id"] == "trk_pa"
        assert data["track_name"] == "Paranoid Android"
        assert len(data["entries"]) == 3
        assert data["entries"][0]["user_id"] == "alice"
        assert data["entries"][0]["is_winner"] is True

    def test_track_not_found(self, client, social_db):
        resp = client.get("/gatekeep/track/nonexistent", headers=_auth("alice"))
        assert resp.status_code == 404


class TestLeaderboard:
    def test_leaderboard_counts_crowns(self, client, social_db):
        resp = client.get("/gatekeep/leaderboard", headers=_auth("alice"))
        assert resp.status_code == 200
        data = resp.json()
        entries = data["entries"]
        assert len(entries) >= 1
        assert data["total_artists_contested"] >= 1
        crown_map = {e["user_id"]: e["crown_count"] for e in entries}
        assert crown_map.get("alice", 0) >= 1

    def test_leaderboard_entries_have_ranks(self, client, social_db):
        resp = client.get("/gatekeep/leaderboard", headers=_auth("alice"))
        entries = resp.json()["entries"]
        for i, entry in enumerate(entries):
            assert entry["rank"] == i + 1

    def test_leaderboard_no_friends(self, client, social_db):
        social_db.add(User(user_id="loner", user_name="Loner"))
        social_db.commit()
        resp = client.get("/gatekeep/leaderboard", headers=_auth("loner"))
        data = resp.json()
        assert data["entries"] == []
        assert data["total_artists_contested"] == 0


class TestChallenge:
    def test_creates_challenge(self, client, social_db):
        resp = client.post(
            "/gatekeep/challenge",
            params={"artist_id": "art_rh"},
            headers=_auth("alice"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Radiohead" in data["challenge_text"]
        assert "3 times" in data["challenge_text"]
        assert data["artist_name"] == "Radiohead"
        assert data["your_total_listens"] == 3
        assert data["invite_code"] is not None
        assert len(data["invite_code"]) > 10

    def test_challenge_creates_invite(self, client, social_db):
        resp = client.post(
            "/gatekeep/challenge",
            params={"artist_id": "art_rh"},
            headers=_auth("alice"),
        )
        code = resp.json()["invite_code"]
        invite = social_db.query(
            __import__("app.models", fromlist=["FriendInvite"]).FriendInvite
        ).filter_by(invite_code=code).first()
        assert invite is not None
        assert invite.from_user_id == "alice"

    def test_challenge_no_listens(self, client, social_db):
        resp = client.post(
            "/gatekeep/challenge",
            params={"artist_id": "art_bf"},
            headers=_auth("charlie"),
        )
        assert resp.status_code == 400
        assert "no listening data" in resp.json()["detail"].lower()

    def test_challenge_artist_not_found(self, client, social_db):
        resp = client.post(
            "/gatekeep/challenge",
            params={"artist_id": "nonexistent"},
            headers=_auth("alice"),
        )
        assert resp.status_code == 404
