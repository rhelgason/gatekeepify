from app.models import User


class TestTopTracks:
    def test_top_tracks_all_time(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/top-tracks", params={"period": "all"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["track_name"] == "Paranoid Android"
        assert data[0]["listen_count"] == 3
        assert data[0]["rank"] == 1

    def test_top_tracks_with_limit(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/top-tracks",
            params={"period": "all", "limit": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["track_name"] == "Paranoid Android"

    def test_top_tracks_year_period(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/top-tracks", params={"period": "year"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_top_tracks_with_offset(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/top-tracks",
            params={"period": "all", "limit": 1, "offset": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["rank"] == 2
        assert data[0]["track_name"] != "Paranoid Android"

    def test_top_tracks_limit_clamped(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/top-tracks",
            params={"period": "all", "limit": 9999},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) <= 100

    def test_top_tracks_no_auth(self, client, seeded_db):
        resp = client.get("/stats/top-tracks", params={"period": "all"})
        assert resp.status_code in (401, 403)


class TestTopArtists:
    def test_top_artists_all_time(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/top-artists", params={"period": "all"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["artist_name"] == "Radiohead"
        assert data[0]["listen_count"] == 6
        assert "alternative rock" in data[0]["genres"]
        assert "art rock" in data[0]["genres"]

    def test_top_artists_includes_genres(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/top-artists", params={"period": "all"}, headers=auth_headers)
        data = resp.json()
        thom = next(a for a in data if a["artist_name"] == "Thom Yorke")
        assert thom["genres"] == ["electronic"]


class TestTopGenres:
    def test_top_genres_all_time(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/top-genres", params={"period": "all"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        genre_names = [g["genre"] for g in data]
        assert "alternative rock" in genre_names

    def test_top_genres_deduplicates(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/top-genres", params={"period": "all"}, headers=auth_headers)
        data = resp.json()
        alt_rock = next(g for g in data if g["genre"] == "alternative rock")
        assert alt_rock["listen_count"] == 6


class TestWrapped:
    def test_wrapped(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/wrapped", params={"year": 2024}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2024
        assert len(data["top_artists"]) <= 5
        assert len(data["top_tracks"]) <= 5
        assert data["total_minutes"] > 0
        assert data["top_genre"] is not None

    def test_wrapped_default_year(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/wrapped", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] is not None

    def test_wrapped_invalid_year(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/wrapped", params={"year": 1999}, headers=auth_headers)
        assert resp.status_code == 400


class TestTimeline:
    def test_timeline_personal(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/timeline",
            params={"artist_id": "artist_1", "mode": "personal"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert len(data["users"]) >= 1

    def test_timeline_requires_artist_or_track(self, client, seeded_db, auth_headers):
        resp = client.get("/stats/timeline", headers=auth_headers)
        assert resp.status_code == 400

    def test_timeline_friends_mode(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/timeline",
            params={"artist_id": "artist_1", "mode": "friends"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_timeline_global_mode(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/timeline",
            params={"artist_id": "artist_1", "mode": "global"},
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestTargetUserStats:
    def test_cannot_view_stranger_stats(self, client, seeded_db, auth_headers):
        seeded_db.add(User(user_id="stranger", user_name="Stranger"))
        seeded_db.commit()
        resp = client.get(
            "/stats/top-tracks",
            params={"period": "all", "target_user_id": "stranger"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_can_view_friend_stats(self, client, seeded_db, auth_headers):
        from app.models import Friendship
        from datetime import datetime, timezone

        seeded_db.add(User(user_id="friend_user", user_name="Friend"))
        seeded_db.add(
            Friendship(user_id_1="test_user_1", user_id_2="friend_user", created_at=datetime.now(timezone.utc))
        )
        seeded_db.commit()
        resp = client.get(
            "/stats/top-tracks",
            params={"period": "all", "target_user_id": "friend_user"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_can_view_own_stats_with_target(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/top-tracks",
            params={"period": "all", "target_user_id": "test_user_1"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
