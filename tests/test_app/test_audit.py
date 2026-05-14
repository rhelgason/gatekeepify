import json

from app.models import AuditLog
from app.services.audit import log_action


class TestAuditLogService:
    def test_log_action_writes_to_db(self, db, test_user):
        log_action(db, "test.action", user_id=test_user.user_id)

        entry = db.query(AuditLog).first()
        assert entry is not None
        assert entry.action == "test.action"
        assert entry.user_id == test_user.user_id
        assert entry.status == "success"
        assert entry.ts is not None

    def test_log_action_with_entity(self, db, test_user):
        log_action(
            db, "test.entity",
            user_id=test_user.user_id,
            entity_type="artist",
            entity_id="art_123",
        )

        entry = db.query(AuditLog).first()
        assert entry.entity_type == "artist"
        assert entry.entity_id == "art_123"

    def test_log_action_with_details(self, db, test_user):
        log_action(
            db, "test.details",
            user_id=test_user.user_id,
            details={"count": 42, "items": ["a", "b"]},
        )

        entry = db.query(AuditLog).first()
        parsed = json.loads(entry.details)
        assert parsed["count"] == 42
        assert parsed["items"] == ["a", "b"]

    def test_log_action_error_status(self, db, test_user):
        log_action(
            db, "test.fail",
            user_id=test_user.user_id,
            status="error",
            details={"error": "something broke"},
        )

        entry = db.query(AuditLog).first()
        assert entry.status == "error"

    def test_log_action_without_user(self, db):
        log_action(db, "system.startup")

        entry = db.query(AuditLog).first()
        assert entry.user_id is None
        assert entry.action == "system.startup"


class TestAuditFromEndpoints:
    def test_backfill_upload_creates_audit_entry(self, client, seeded_db, auth_headers):
        import io
        import zipfile
        from unittest.mock import patch, MagicMock

        listens = [
            {
                "ts": "2024-01-01T10:00:00Z",
                "ms_played": 60000,
                "master_metadata_track_name": "Test",
                "spotify_track_uri": "spotify:track:audit_trk",
            }
        ]
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("Streaming_History_Audio_0.json", json.dumps(listens))
        buf.seek(0)

        with patch("app.celery_app.celery_app.send_task"):
            client.post(
                "/backfill/upload",
                headers=auth_headers,
                files={"file": ("data.zip", buf, "application/zip")},
            )

        entry = seeded_db.query(AuditLog).filter(
            AuditLog.action == "backfill.upload_started"
        ).first()
        assert entry is not None
        assert entry.user_id == "test_user_1"
        assert entry.status == "success"
        details = json.loads(entry.details)
        assert "job_id" in details

    def test_friend_invite_creates_audit_entry(self, client, seeded_db, auth_headers):
        client.post("/friends/invite", headers=auth_headers)

        entry = seeded_db.query(AuditLog).filter(
            AuditLog.action == "friends.invite_created"
        ).first()
        assert entry is not None
        assert entry.user_id == "test_user_1"
        assert entry.entity_type == "invite"

    def test_gatekeep_artist_creates_audit_entry(self, client, seeded_db, auth_headers):
        client.get("/gatekeep/artist/artist_1", headers=auth_headers)

        entry = seeded_db.query(AuditLog).filter(
            AuditLog.action == "gatekeep.artist_viewed"
        ).first()
        assert entry is not None
        assert entry.user_id == "test_user_1"
        assert entry.entity_type == "artist"
        assert entry.entity_id == "artist_1"

    def test_stats_creates_audit_entry(self, client, seeded_db, auth_headers):
        client.get("/stats/top-tracks", params={"period": "all"}, headers=auth_headers)

        entry = seeded_db.query(AuditLog).filter(
            AuditLog.action == "stats.top_tracks_viewed"
        ).first()
        assert entry is not None
        assert entry.user_id == "test_user_1"

    def test_denied_invite_creates_audit_entry(self, client, seeded_db, auth_headers):
        client.post("/friends/accept/nonexistent_code", headers=auth_headers)

        entry = seeded_db.query(AuditLog).filter(
            AuditLog.action == "friends.invite_accepted",
            AuditLog.status == "error",
        ).first()
        assert entry is not None
        details = json.loads(entry.details)
        assert details["reason"] == "not_found"
