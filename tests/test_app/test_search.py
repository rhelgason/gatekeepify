class TestSearchArtists:
    def test_search_by_name(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artists", params={"q": "Radiohead"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["artist_id"] == "artist_1"
        assert data[0]["artist_name"] == "Radiohead"

    def test_search_case_insensitive(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artists", params={"q": "radiohead"}, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_partial_match(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artists", params={"q": "radio"}, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["artist_name"] == "Radiohead"

    def test_search_includes_genres(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artists", params={"q": "Radiohead"}, headers=auth_headers)
        data = resp.json()
        assert "alternative rock" in data[0]["genres"]

    def test_search_includes_listen_count(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artists", params={"q": "Radiohead"}, headers=auth_headers)
        data = resp.json()
        assert data[0]["your_listen_count"] > 0

    def test_search_no_results(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artists", params={"q": "Nonexistent"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_respects_limit(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artists", params={"q": "o", "limit": 1}, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 1

    def test_search_requires_query(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artists", headers=auth_headers)
        assert resp.status_code == 422

    def test_search_requires_auth(self, client, seeded_db):
        resp = client.get("/search/artists", params={"q": "test"})
        assert resp.status_code in (401, 403)


class TestSearchTracks:
    def test_search_by_name(self, client, seeded_db, auth_headers):
        resp = client.get("/search/tracks", params={"q": "Paranoid"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["track_id"] == "track_1"
        assert data[0]["track_name"] == "Paranoid Android"

    def test_search_includes_album(self, client, seeded_db, auth_headers):
        resp = client.get("/search/tracks", params={"q": "Paranoid"}, headers=auth_headers)
        data = resp.json()
        assert data[0]["album_name"] == "OK Computer"

    def test_search_includes_artist_names(self, client, seeded_db, auth_headers):
        resp = client.get("/search/tracks", params={"q": "Everything"}, headers=auth_headers)
        data = resp.json()
        assert len(data) == 1
        assert "Radiohead" in data[0]["artist_names"]
        assert "Thom Yorke" in data[0]["artist_names"]

    def test_search_includes_listen_count(self, client, seeded_db, auth_headers):
        resp = client.get("/search/tracks", params={"q": "Paranoid"}, headers=auth_headers)
        data = resp.json()
        assert data[0]["your_listen_count"] > 0

    def test_search_case_insensitive(self, client, seeded_db, auth_headers):
        resp = client.get("/search/tracks", params={"q": "paranoid"}, headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_no_results(self, client, seeded_db, auth_headers):
        resp = client.get("/search/tracks", params={"q": "Nonexistent"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_orders_by_listen_count(self, client, seeded_db, auth_headers):
        resp = client.get("/search/tracks", params={"q": "a"}, headers=auth_headers)
        data = resp.json()
        if len(data) >= 2:
            assert data[0]["your_listen_count"] >= data[1]["your_listen_count"]


class TestArtistDetail:
    def test_get_artist_detail(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artist/artist_1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["artist_id"] == "artist_1"
        assert data["artist_name"] == "Radiohead"
        assert data["total_listens"] > 0
        assert "alternative rock" in data["genres"]

    def test_artist_not_found(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artist/nonexistent", headers=auth_headers)
        assert resp.status_code == 404


class TestTrackDetail:
    def test_get_track_detail(self, client, seeded_db, auth_headers):
        resp = client.get("/search/track/track_1", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["track_id"] == "track_1"
        assert data["track_name"] == "Paranoid Android"
        assert data["total_listens"] > 0

    def test_track_not_found(self, client, seeded_db, auth_headers):
        resp = client.get("/search/track/nonexistent", headers=auth_headers)
        assert resp.status_code == 404


class TestResolveArtist:
    def test_resolve_from_db(self, client, seeded_db, auth_headers):
        resp = client.get("/search/resolve-artist", params={"name": "Radiohead"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["artist_id"] == "artist_1"
        assert data["resolved"] == "db"

    def test_resolve_case_insensitive(self, client, seeded_db, auth_headers):
        resp = client.get("/search/resolve-artist", params={"name": "radiohead"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["resolved"] == "db"
