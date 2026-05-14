import io
import json
import zipfile
from unittest.mock import patch, MagicMock
from datetime import date

from app.models import Album, Listen, ListenSource, Track
from app.routers.backfill import _extract_json_from_zip, _validate_and_process_listens


def _make_zip(files: dict[str, list[dict]]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, json.dumps(data))
    buf.seek(0)
    return buf


def _make_zip_bytes(files: dict[str, list[dict]]) -> bytes:
    buf = _make_zip(files)
    return buf.read()


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


class TestUploadEndpoint:
    @patch("app.celery_app.celery_app.send_task")
    def test_upload_returns_job_id(self, mock_send, client, seeded_db, auth_headers):
        listens = [_make_listen_json()]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "processing"
        mock_send.assert_called_once()

    def test_upload_rejects_non_zip(self, client, seeded_db, auth_headers):
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.txt", b"not a zip", "text/plain")},
        )
        assert resp.status_code == 400


class TestExtractJson:
    def test_extracts_audio_files(self):
        content = _make_zip_bytes({
            "Streaming_History_Audio_0.json": [_make_listen_json()],
            "other.json": [{"nope": True}],
        })
        result = _extract_json_from_zip(content)
        assert len(result) == 1

    def test_ignores_non_audio_files(self):
        content = _make_zip_bytes({"random_file.json": [{"a": 1}]})
        result = _extract_json_from_zip(content)
        assert len(result) == 0

    def test_handles_nested_paths(self):
        content = _make_zip_bytes({
            "my_spotify_data/Streaming_History_Audio_0.json": [_make_listen_json()],
        })
        result = _extract_json_from_zip(content)
        assert len(result) == 1


class TestValidateListens:
    def test_accepts_valid_listen(self, seeded_db, test_user):
        listens = [_make_listen_json("new_trk", "New", "2024-01-01T10:00:00Z")]
        accepted, reasons = _validate_and_process_listens(listens, test_user, seeded_db)
        assert len(accepted) == 1
        assert len(reasons) == 0

    def test_rejects_short_plays(self, seeded_db, test_user):
        listens = [_make_listen_json(ms_played=5000)]
        accepted, reasons = _validate_and_process_listens(listens, test_user, seeded_db)
        assert len(accepted) == 0
        assert reasons["too_short"] == 1

    def test_rejects_null_uri(self, seeded_db, test_user):
        listens = [{
            "ts": "2024-01-01T10:00:00Z",
            "ms_played": 60000,
            "master_metadata_track_name": "Test",
            "spotify_track_uri": None,
        }]
        accepted, reasons = _validate_and_process_listens(listens, test_user, seeded_db)
        assert reasons["no_track_uri"] == 1

    def test_rejects_invalid_uri_format(self, seeded_db, test_user):
        listens = [{
            "ts": "2024-01-01T10:00:00Z",
            "ms_played": 60000,
            "master_metadata_track_name": "Test",
            "spotify_track_uri": "not:a:spotify:uri",
        }]
        accepted, reasons = _validate_and_process_listens(listens, test_user, seeded_db)
        assert reasons["invalid_uri_format"] == 1

    def test_rejects_before_release_date(self, seeded_db, test_user):
        album = seeded_db.query(Album).filter(Album.album_id == "album_1").first()
        album.release_date = date(2024, 6, 1)
        seeded_db.commit()

        listens = [_make_listen_json("track_1", "Paranoid Android", "2024-01-01T10:00:00Z")]
        accepted, reasons = _validate_and_process_listens(listens, test_user, seeded_db)
        assert reasons.get("before_release_date", 0) == 1

    def test_accepts_after_release_date(self, seeded_db, test_user):
        album = seeded_db.query(Album).filter(Album.album_id == "album_1").first()
        album.release_date = date(2024, 1, 1)
        seeded_db.commit()

        listens = [_make_listen_json("track_1", "Paranoid Android", "2024-06-15T10:00:00Z")]
        accepted, reasons = _validate_and_process_listens(listens, test_user, seeded_db)
        assert reasons.get("before_release_date", 0) == 0

    def test_stores_extra_metadata(self, seeded_db, test_user):
        listens = [_make_listen_json(
            "meta_trk", "Meta", extra_fields={"platform": "iOS", "shuffle": True}
        )]
        accepted, _ = _validate_and_process_listens(listens, test_user, seeded_db)
        assert len(accepted) == 1
        listen, _ = accepted[0]
        meta = json.loads(listen.export_metadata)
        assert meta["platform"] == "iOS"

    def test_tags_source_as_export(self, seeded_db, test_user):
        listens = [_make_listen_json("src_trk", "Source")]
        accepted, _ = _validate_and_process_listens(listens, test_user, seeded_db)
        listen, _ = accepted[0]
        assert listen.source == ListenSource.export.value


class TestUploadStatus:
    @patch("app.celery_app.celery_app.send_task")
    def test_upload_status_after_upload(self, mock_send, client, seeded_db, auth_headers):
        listens = [_make_listen_json()]
        zip_buf = _make_zip({"Streaming_History_Audio_0.json": listens})
        client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.zip", zip_buf, "application/zip")},
        )
        resp = client.get("/backfill/upload-status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["phase"] == "queued"

    def test_upload_status_no_job(self, client, seeded_db, auth_headers):
        resp = client.get("/backfill/upload-status", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "none"


class TestBackfillStatus:
    def test_status(self, client, seeded_db, auth_headers):
        resp = client.get("/backfill/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_listens"] == 6
        assert data["total_tracks"] == 3
        assert data["tracks_missing_metadata"] >= 0
