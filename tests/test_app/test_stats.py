class TestTopTracks:
    def test_top_tracks_all_time(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/top-tracks", params={"period": "all"}, headers=auth_headers
        )
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
        resp = client.get(
            "/stats/top-tracks", params={"period": "year"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_top_tracks_no_auth(self, client, seeded_db):
        resp = client.get("/stats/top-tracks", params={"period": "all"})
        assert resp.status_code in (401, 403)


class TestTopArtists:
    def test_top_artists_all_time(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/top-artists", params={"period": "all"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["artist_name"] == "Radiohead"
        assert data[0]["listen_count"] == 6
        assert "alternative rock" in data[0]["genres"]
        assert "art rock" in data[0]["genres"]

    def test_top_artists_includes_genres(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/top-artists", params={"period": "all"}, headers=auth_headers
        )
        data = resp.json()
        thom = next(a for a in data if a["artist_name"] == "Thom Yorke")
        assert thom["genres"] == ["electronic"]


class TestTopGenres:
    def test_top_genres_all_time(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/top-genres", params={"period": "all"}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        genre_names = [g["genre"] for g in data]
        assert "alternative rock" in genre_names

    def test_top_genres_deduplicates(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/top-genres", params={"period": "all"}, headers=auth_headers
        )
        data = resp.json()
        alt_rock = next(g for g in data if g["genre"] == "alternative rock")
        assert alt_rock["listen_count"] == 6


class TestWrapped:
    def test_wrapped(self, client, seeded_db, auth_headers):
        resp = client.get(
            "/stats/wrapped", params={"year": 2024}, headers=auth_headers
        )
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
