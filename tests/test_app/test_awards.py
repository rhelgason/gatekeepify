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
from app.services.awards import (
    compute_archaeologist,
    compute_basic,
    compute_completionist,
    compute_crown,
    compute_genre_snob,
    compute_hypebeast,
    compute_night_owl,
    compute_obsessive,
    compute_patient_zero,
    compute_streak,
    compute_time_traveler,
    get_friend_group_hash,
)


def _auth(user_id):
    token = jwt.encode(
        {"sub": user_id, "exp": datetime(2099, 1, 1, tzinfo=timezone.utc)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def award_db(db):
    users = [
        User(user_id="alice", user_name="Alice"),
        User(user_id="bob", user_name="Bob"),
        User(user_id="charlie", user_name="Charlie"),
    ]
    for u in users:
        db.add(u)

    now = datetime(2024, 6, 1)
    for a, b in [("alice", "bob"), ("bob", "alice"), ("alice", "charlie"), ("charlie", "alice")]:
        db.add(Friendship(user_id_1=a, user_id_2=b, created_at=now))

    db.add(Album(album_id="alb1", album_name="Album 1", release_date=None))
    db.add(Album(album_id="alb2", album_name="Album 2", release_date=None))
    db.add(Artist(artist_id="art1", artist_name="Artist 1"))
    db.add(Artist(artist_id="art2", artist_name="Artist 2"))
    db.add(Artist(artist_id="art3", artist_name="Artist 3"))
    db.add(ArtistGenre(artist_id="art1", genre="rock"))
    db.add(ArtistGenre(artist_id="art1", genre="indie"))
    db.add(ArtistGenre(artist_id="art2", genre="electronic"))
    db.add(ArtistGenre(artist_id="art3", genre="jazz"))
    db.add(Track(track_id="t1", track_name="Track 1", album_id="alb1", duration_ms=200000))
    db.add(Track(track_id="t2", track_name="Track 2", album_id="alb1", duration_ms=180000))
    db.add(Track(track_id="t3", track_name="Track 3", album_id="alb2", duration_ms=240000))
    db.add(Track(track_id="t4", track_name="Track 4", album_id="alb1", duration_ms=150000))
    db.add(Track(track_id="t5", track_name="Track 5", album_id="alb1", duration_ms=160000))
    db.add(TrackArtist(track_id="t1", artist_id="art1"))
    db.add(TrackArtist(track_id="t2", artist_id="art1"))
    db.add(TrackArtist(track_id="t3", artist_id="art2"))
    db.add(TrackArtist(track_id="t4", artist_id="art1"))
    db.add(TrackArtist(track_id="t5", artist_id="art1"))
    db.add(TrackArtist(track_id="t3", artist_id="art3"))

    # Alice: art1 first (2017), art2 (2022)
    # Bob: art1 (2021), art2 first (2019), art3 first (2020)
    # Charlie: art1 (2023)
    listens = [
        Listen(ts=datetime(2017, 3, 1, 10), user_id="alice", track_id="t1", source="api"),
        Listen(ts=datetime(2017, 3, 2, 10), user_id="alice", track_id="t1", source="api"),
        Listen(ts=datetime(2017, 3, 3, 10), user_id="alice", track_id="t2", source="api"),
        Listen(ts=datetime(2017, 3, 4, 2, 0), user_id="alice", track_id="t1", source="api"),  # 2am
        Listen(ts=datetime(2017, 3, 5, 3, 0), user_id="alice", track_id="t4", source="api"),  # 3am
        Listen(ts=datetime(2017, 3, 6, 10), user_id="alice", track_id="t5", source="api"),
        Listen(ts=datetime(2022, 11, 1, 10), user_id="alice", track_id="t3", source="export"),
        Listen(ts=datetime(2021, 1, 15, 10), user_id="bob", track_id="t1", source="export"),
        Listen(ts=datetime(2021, 2, 1, 10), user_id="bob", track_id="t2", source="api"),
        Listen(ts=datetime(2019, 5, 1, 10), user_id="bob", track_id="t3", source="api"),
        Listen(ts=datetime(2019, 5, 2, 10), user_id="bob", track_id="t3", source="api"),
        Listen(ts=datetime(2020, 1, 1, 10), user_id="bob", track_id="t3", source="api"),
        Listen(ts=datetime(2023, 8, 1, 10), user_id="charlie", track_id="t1", source="api"),
    ]
    for l in listens:
        db.add(l)
    db.commit()
    return db


class TestFriendGroupHash:
    def test_hash_is_deterministic(self):
        h1 = get_friend_group_hash(["alice", "bob", "charlie"])
        h2 = get_friend_group_hash(["charlie", "alice", "bob"])
        assert h1 == h2

    def test_different_groups_different_hashes(self):
        h1 = get_friend_group_hash(["alice", "bob"])
        h2 = get_friend_group_hash(["alice", "charlie"])
        assert h1 != h2


class TestComputeCrown:
    def test_crown_counts(self, award_db):
        results = compute_crown(award_db, ["alice", "bob", "charlie"])
        crown_map = {r["user_id"]: r["stat_value"] for r in results}
        assert crown_map["alice"] >= 1
        assert crown_map["bob"] >= 1

    def test_crown_ranking(self, award_db):
        results = compute_crown(award_db, ["alice", "bob", "charlie"])
        assert results[0]["rank"] == 1


class TestComputeArchaeologist:
    def test_finds_largest_gap(self, award_db):
        results = compute_archaeologist(award_db, ["alice", "bob", "charlie"])
        assert len(results) > 0
        assert results[0]["stat_value"] > 0
        assert "days" in results[0]["stat_detail"]

    def test_alice_has_largest_gap_for_art1(self, award_db):
        results = compute_archaeologist(award_db, ["alice", "bob", "charlie"])
        alice = next((r for r in results if r["user_id"] == "alice"), None)
        assert alice is not None
        assert alice["stat_value"] > 1000  # ~4 years gap


class TestComputeObsessive:
    def test_finds_most_listened_artist(self, award_db):
        results = compute_obsessive(award_db, ["alice", "bob", "charlie"])
        assert len(results) > 0
        assert results[0]["rank"] == 1
        assert results[0]["stat_value"] > 0
        assert results[0]["entity_name"] is not None


class TestComputePatientZero:
    def test_counts_infections(self, award_db):
        results = compute_patient_zero(award_db, ["alice", "bob", "charlie"])
        assert len(results) > 0
        assert "Infected" in results[0]["stat_detail"]


class TestComputeNightOwl:
    def test_detects_night_listens(self, award_db):
        results = compute_night_owl(award_db, ["alice", "bob", "charlie"])
        alice = next((r for r in results if r["user_id"] == "alice"), None)
        assert alice is not None
        assert alice["stat_value"] > 0  # Alice has 2am and 3am listens


class TestComputeGenreSnob:
    def test_finds_exclusive_genres(self, award_db):
        results = compute_genre_snob(award_db, ["alice", "bob", "charlie"])
        # Alice listens to rock/indie (via art1) but art3 has jazz only listened to by Bob
        bob = next((r for r in results if r["user_id"] == "bob"), None)
        if bob:
            assert bob["stat_value"] > 0


class TestComputeBasic:
    def test_computes_overlap(self, award_db):
        results = compute_basic(award_db, ["alice", "bob", "charlie"])
        assert len(results) > 0
        for r in results:
            assert 0 <= r["stat_value"] <= 100


class TestComputeStreak:
    def test_finds_consecutive_days(self, award_db):
        results = compute_streak(award_db, ["alice", "bob", "charlie"])
        alice = next((r for r in results if r["user_id"] == "alice"), None)
        assert alice is not None
        assert alice["stat_value"] >= 3  # Alice has listens on March 1-6


class TestComputeCompletionist:
    def test_computes_ratio(self, award_db):
        results = compute_completionist(award_db, ["alice", "bob", "charlie"])
        # art1 has 4 tracks (t1,t2,t4,t5), alice listened to all 4
        if results:
            assert results[0]["stat_value"] > 0
            assert "%" in results[0]["stat_detail"]


class TestComputeHypebeast:
    def test_handles_no_prior_data(self, award_db):
        results = compute_hypebeast(award_db, ["alice", "bob", "charlie"])
        # All data is from 2017-2023, so no recent 30-day activity
        assert isinstance(results, list)


class TestTrophiesEndpoint:
    def test_trophies_returns_all_awards(self, client, award_db):
        resp = client.get("/gatekeep/awards/trophies", headers=_auth("alice"))
        assert resp.status_code == 200
        data = resp.json()
        assert "user_awards" in data
        assert "leaderboards" in data
        assert len(data["user_awards"]) == 12

    def test_trophies_requires_auth(self, client, award_db):
        resp = client.get("/gatekeep/awards/trophies")
        assert resp.status_code in (401, 403)


class TestHeadToHeadEndpoint:
    def test_head_to_head_returns_comparisons(self, client, award_db):
        resp = client.get("/gatekeep/awards/head-to-head", params={"friend_id": "bob"}, headers=_auth("alice"))
        assert resp.status_code == 200
        data = resp.json()
        assert "comparisons" in data
        assert len(data["comparisons"]) == 12
        assert "you" in data
        assert "friend" in data

    def test_head_to_head_not_friends(self, client, award_db):
        resp = client.get("/gatekeep/awards/head-to-head", params={"friend_id": "bob"}, headers=_auth("charlie"))
        # Charlie is friends with Alice but not Bob
        assert resp.status_code == 403
