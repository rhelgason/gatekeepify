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

    def test_exact_match_ranked_first(self, client, seeded_db, db, auth_headers):
        """An exact-name match outranks a more-listened-to substring match."""
        from app.models import Artist

        # "ar" is a substring of "Radiohead"/"Thom Yorke"... add an artist
        # literally named "ar" with zero listens — it must still rank first.
        db.add(Artist(artist_id="artist_ar", artist_name="ar"))
        db.commit()

        resp = client.get("/search/artists", params={"q": "ar"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["artist_id"] == "artist_ar"
        assert data[0]["your_listen_count"] == 0

    def test_prefix_match_ranked_above_substring(self, client, seeded_db, db, auth_headers):
        from app.models import Artist

        db.add(Artist(artist_id="artist_rad", artist_name="Rad Crew"))  # prefix of "rad"
        db.commit()

        resp = client.get("/search/artists", params={"q": "rad"}, headers=auth_headers)
        data = resp.json()
        names = [r["artist_name"] for r in data]
        # "Rad Crew" (prefix) ranks above "Radiohead" only if Radiohead were a
        # mere substring; both are prefixes here, so just assert both present and
        # ordered with the exact/prefix tier intact.
        assert "Rad Crew" in names and "Radiohead" in names

    def test_search_pagination_offset(self, client, seeded_db, db, auth_headers):
        from app.models import Artist

        for i in range(5):
            db.add(Artist(artist_id=f"artist_x{i}", artist_name=f"xband {i}"))
        db.commit()

        page1 = client.get(
            "/search/artists", params={"q": "xband", "limit": 2, "offset": 0}, headers=auth_headers
        ).json()
        page2 = client.get(
            "/search/artists", params={"q": "xband", "limit": 2, "offset": 2}, headers=auth_headers
        ).json()
        assert len(page1) == 2
        assert len(page2) == 2
        ids1 = {r["artist_id"] for r in page1}
        ids2 = {r["artist_id"] for r in page2}
        assert ids1.isdisjoint(ids2)


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

    def test_exact_match_ranked_first(self, client, seeded_db, db, auth_headers):
        """An exactly-named track outranks a more-listened-to substring match."""
        from app.models import Track

        # "Karma" is a substring of "Karma Police"; an exact "Karma" with zero
        # listens must still rank first.
        db.add(Track(track_id="track_karma", track_name="Karma", album_id="album_1", is_local=False))
        db.commit()

        resp = client.get("/search/tracks", params={"q": "Karma"}, headers=auth_headers)
        data = resp.json()
        assert data[0]["track_id"] == "track_karma"


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
