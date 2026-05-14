from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from jose import jwt
from app.config import settings


@pytest.fixture()
def admin_user(db, test_user):
    test_user.is_admin = True
    db.commit()
    return test_user


@pytest.fixture()
def admin_headers(admin_user):
    payload = {
        "sub": admin_user.user_id,
        "exp": datetime(2099, 1, 1, tzinfo=timezone.utc),
        "iat": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestTrackEvent:
    def test_logs_frontend_event(self, client, auth_headers, test_user):
        resp = client.post(
            "/track-event",
            json={"action": "page_view", "details": {"page": "/dashboard"}},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_requires_auth(self, client):
        resp = client.post("/track-event", json={"action": "test"})
        assert resp.status_code in (401, 403)


class TestAdminTriggerPoll:
    @patch("app.tasks.poll_recent_listens")
    def test_triggers_task(self, mock_task, client, admin_headers, admin_user):
        mock_task.delay = MagicMock()
        resp = client.post("/admin/trigger-poll", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["task"] == "poll_recent_listens"

    def test_rejects_non_admin(self, client, auth_headers, test_user):
        resp = client.post("/admin/trigger-poll", headers=auth_headers)
        assert resp.status_code == 403

    def test_requires_auth(self, client):
        resp = client.post("/admin/trigger-poll")
        assert resp.status_code in (401, 403)


class TestAdminTriggerBackfill:
    @patch("app.tasks.backfill_track_metadata")
    def test_triggers_task(self, mock_task, client, admin_headers, admin_user):
        mock_task.delay = MagicMock()
        resp = client.post("/admin/trigger-backfill", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["task"] == "backfill_track_metadata"


class TestAdminTriggerAwards:
    @patch("app.tasks.compute_award_snapshots")
    def test_triggers_task(self, mock_task, client, admin_headers, admin_user):
        mock_task.delay = MagicMock()
        resp = client.post("/admin/trigger-awards", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["task"] == "compute_award_snapshots"


class TestAdminTrustScore:
    def test_returns_trust_data(self, client, admin_headers, admin_user, seeded_db):
        resp = client.get("/admin/trust-score", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data

    def test_rejects_non_admin(self, client, auth_headers, test_user, seeded_db):
        resp = client.get("/admin/trust-score", headers=auth_headers)
        assert resp.status_code == 403

    def test_requires_auth(self, client):
        resp = client.get("/admin/trust-score")
        assert resp.status_code in (401, 403)


class TestForceLogout:
    def test_force_logout_all_invalidates_tokens(self, client, admin_headers, admin_user, db):
        resp = client.post("/admin/force-logout-all", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "all_tokens_invalidated"

        resp2 = client.get("/auth/me", headers=admin_headers)
        assert resp2.status_code == 401

    def test_force_logout_user(self, client, admin_headers, admin_user, db):
        resp = client.post(f"/admin/force-logout/{admin_user.user_id}", headers=admin_headers)
        assert resp.status_code == 200

        resp2 = client.get("/auth/me", headers=admin_headers)
        assert resp2.status_code == 401

    def test_new_token_works_after_logout(self, client, admin_user, db):
        old_token = jwt.encode(
            {"sub": admin_user.user_id, "exp": datetime(2099, 1, 1, tzinfo=timezone.utc), "iat": datetime(2024, 1, 1, tzinfo=timezone.utc)},
            settings.jwt_secret, algorithm=settings.jwt_algorithm,
        )
        client.post("/admin/force-logout-all", headers={"Authorization": f"Bearer {old_token}"})

        new_token = jwt.encode(
            {"sub": admin_user.user_id, "exp": datetime(2099, 1, 1, tzinfo=timezone.utc), "iat": datetime(2099, 1, 1, tzinfo=timezone.utc)},
            settings.jwt_secret, algorithm=settings.jwt_algorithm,
        )
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        assert resp.status_code == 200

    def test_rejects_non_admin(self, client, auth_headers, test_user):
        resp = client.post("/admin/force-logout-all", headers=auth_headers)
        assert resp.status_code == 403

    def test_requires_auth(self, client):
        resp = client.post("/admin/force-logout-all")
        assert resp.status_code in (401, 403)
