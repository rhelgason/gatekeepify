import io
import json
import zipfile

from app.models import Listen, ListenSource, Track


def _make_zip(files: dict[str, list[dict]]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, json.dumps(data))
    buf.seek(0)
    return buf


def _make_listen_json(
    track_id="track_100",
    track_name="Test Track",
    ts="2024-06-15T10:30:00Z",
    ms_played=60000,
    extra_fields=None,
):
    entry = {
        "ts": ts,
        "ms_played": ms_played,
        "master_metadata_track_name": track_name,
        "spotify_track_uri": f"spotify:track:{track_id}",
    }
    if extra_fields:
        entry.update(extra_fields)
    return entry


class TestBackfillUpload:
    def test_upload_valid_zip(self, client, seeded_db, auth_headers):
        listens = [
            _make_listen_json("new_track_1", "New Track 1", "2024-01-01T10:00:00Z"),
            _make_listen_json("new_track_2", "New Track 2", "2024-01-02T10:00:00Z"),
        ]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_listens_processed"] == 2
        assert data["total_listens_accepted"] == 2
        assert data["total_listens_rejected"] == 0

    def test_upload_filters_short_listens(self, client, seeded_db, auth_headers):
        listens = [
            _make_listen_json(ms_played=5000),
            _make_listen_json(track_id="valid", ms_played=60000),
        ]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        data = resp.json()
        assert data["total_listens_accepted"] == 1
        assert data["rejection_reasons"]["too_short"] == 1

    def test_upload_filters_null_uri(self, client, seeded_db, auth_headers):
        listens = [
            {
                "ts": "2024-01-01T10:00:00Z",
                "ms_played": 60000,
                "master_metadata_track_name": "Test",
                "spotify_track_uri": None,
            }
        ]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        data = resp.json()
        assert data["total_listens_accepted"] == 0
        assert data["rejection_reasons"]["no_track_uri"] == 1

    def test_upload_ignores_non_audio_files(self, client, seeded_db, auth_headers):
        audio_listens = [_make_listen_json()]
        other_data = [{"some": "data"}]
        zip_buf = _make_zip(
            {
                "Streaming_History_Audio_0.json": audio_listens,
                "other_file.json": other_data,
            }
        )
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        data = resp.json()
        assert data["total_listens_processed"] == 1

    def test_upload_tags_source_as_export(self, client, seeded_db, auth_headers):
        listens = [_make_listen_json("export_track", "Export Track")]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        result = (
            seeded_db.query(Listen)
            .filter(Listen.track_id == "export_track")
            .first()
        )
        assert result is not None
        assert result.source == ListenSource.export.value

    def test_upload_stores_extra_metadata(self, client, seeded_db, auth_headers):
        listens = [
            _make_listen_json(
                "meta_track",
                "Meta Track",
                extra_fields={"platform": "iOS", "shuffle": True, "skipped": False},
            )
        ]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        result = (
            seeded_db.query(Listen)
            .filter(Listen.track_id == "meta_track")
            .first()
        )
        assert result is not None
        meta = json.loads(result.export_metadata)
        assert meta["platform"] == "iOS"
        assert meta["shuffle"] is True

    def test_upload_creates_skeleton_tracks(self, client, seeded_db, auth_headers):
        listens = [_make_listen_json("brand_new_track", "Brand New")]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        track = (
            seeded_db.query(Track)
            .filter(Track.track_id == "brand_new_track")
            .first()
        )
        assert track is not None
        assert track.track_name == "Brand New"
        assert track.album_id is None
        assert track.duration_ms is None

    def test_upload_rejects_non_zip(self, client, seeded_db, auth_headers):
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.txt", b"not a zip", "text/plain")},
        )
        assert resp.status_code == 400

    def test_upload_deduplicates(self, client, seeded_db, auth_headers):
        listens = [
            _make_listen_json("dedup_track", "Dedup", "2024-01-01T10:00:00Z")
        ]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})

        resp1 = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        assert resp1.json()["total_listens_accepted"] == 1

        zip_buf.seek(0)
        resp2 = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        assert resp2.json()["total_listens_accepted"] == 0


class TestBackfillReleaseDate:
    def test_rejects_listen_before_release_date(
        self, client, seeded_db, auth_headers
    ):
        from datetime import date

        from app.models import Album

        album = seeded_db.query(Album).filter(Album.album_id == "album_1").first()
        album.release_date = date(2024, 6, 1)
        seeded_db.commit()

        listens = [_make_listen_json("track_1", "Paranoid Android", "2024-01-01T10:00:00Z")]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        data = resp.json()
        assert data["rejection_reasons"].get("before_release_date", 0) == 1

    def test_accepts_listen_after_release_date(
        self, client, seeded_db, auth_headers
    ):
        from datetime import date

        from app.models import Album

        album = seeded_db.query(Album).filter(Album.album_id == "album_1").first()
        album.release_date = date(2024, 1, 1)
        seeded_db.commit()

        listens = [_make_listen_json("track_1", "Paranoid Android", "2024-06-15T10:00:00Z")]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        data = resp.json()
        assert data["rejection_reasons"].get("before_release_date", 0) == 0


class TestBackfillStatus:
    def test_status(self, client, seeded_db, auth_headers):
        resp = client.get("/backfill/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_listens"] == 6
        assert data["total_tracks"] == 3
        assert data["tracks_missing_metadata"] >= 0
