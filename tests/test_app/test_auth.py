from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from jose import jwt

from app.config import settings
from app.models import AuditLog, User


class TestAuthMe:
    def test_get_me(self, client, seeded_db, auth_headers):
        resp = client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "test_user_1"
        assert data["user_name"] == "Test User"

    def test_get_me_invalid_token(self, client, seeded_db):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401

    def test_get_me_expired_token(self, client, seeded_db):
        payload = {
            "sub": "test_user_1",
            "exp": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "iat": datetime(2019, 1, 1, tzinfo=timezone.utc),
        }
        token = jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_get_me_nonexistent_user(self, client, db):
        payload = {
            "sub": "nonexistent_user",
            "exp": datetime(2099, 1, 1, tzinfo=timezone.utc),
            "iat": datetime(2024, 1, 1, tzinfo=timezone.utc),
        }
        token = jwt.encode(
            payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
        )
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_get_me_no_auth_header(self, client, seeded_db):
        resp = client.get("/auth/me")
        assert resp.status_code in (401, 403)


class TestAuthLogin:
    def test_login_returns_auth_url(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.config.settings.spotify_client_id", "test_client_id"
        )
        monkeypatch.setattr(
            "app.config.settings.spotify_client_secret", "test_client_secret"
        )
        resp = client.get("/auth/login")
        assert resp.status_code == 200
        data = resp.json()
        assert "auth_url" in data
        assert "accounts.spotify.com" in data["auth_url"]


class TestAuthCallback:
    @patch("app.routers.auth.SpotifyService")
    def test_callback_creates_new_user(self, MockService, client, db):
        mock = MockService.return_value
        mock.exchange_code.return_value = {
            "access_token": "sp_access_tok",
            "refresh_token": "sp_refresh_tok",
        }
        mock.get_current_user.return_value = {
            "id": "spotify_user_42",
            "display_name": "New User",
            "email": "new@example.com",
        }

        resp = client.get("/auth/callback", params={"code": "auth_code_123"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["token_type"] == "bearer"
        assert data["access_token"] is not None
        assert data["user"]["user_id"] == "spotify_user_42"
        assert data["user"]["user_name"] == "New User"
        assert data["user"]["email"] == "new@example.com"

        user = db.query(User).filter(User.user_id == "spotify_user_42").first()
        assert user is not None
        assert user.user_name == "New User"
        assert user.spotify_refresh_token is not None
        assert user.created_at is not None

        mock.exchange_code.assert_called_once_with("auth_code_123")
        mock.get_current_user.assert_called_once_with("sp_access_tok")

    @patch("app.routers.auth.SpotifyService")
    def test_callback_updates_existing_user(self, MockService, client, db):
        db.add(User(
            user_id="existing_user",
            user_name="Old Name",
            email="old@example.com",
            spotify_refresh_token="old_token",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        db.commit()

        mock = MockService.return_value
        mock.exchange_code.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
        }
        mock.get_current_user.return_value = {
            "id": "existing_user",
            "display_name": "Updated Name",
            "email": "updated@example.com",
        }

        resp = client.get("/auth/callback", params={"code": "code_456"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user"]["user_name"] == "Updated Name"
        assert data["user"]["email"] == "updated@example.com"

        user = db.query(User).filter(User.user_id == "existing_user").first()
        assert user.user_name == "Updated Name"
        assert user.spotify_refresh_token == "new_refresh"
        assert db.query(User).count() == 1

    @patch("app.routers.auth.SpotifyService")
    def test_callback_returns_valid_jwt(self, MockService, client, db):
        mock = MockService.return_value
        mock.exchange_code.return_value = {
            "access_token": "acc",
            "refresh_token": "ref",
        }
        mock.get_current_user.return_value = {
            "id": "jwt_test_user",
            "display_name": "JWT User",
        }

        resp = client.get("/auth/callback", params={"code": "code"})
        token = resp.json()["access_token"]

        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == "jwt_test_user"
        assert "exp" in payload

        resp2 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp2.status_code == 200
        assert resp2.json()["user_id"] == "jwt_test_user"

    @patch("app.routers.auth.SpotifyService")
    def test_callback_logs_to_audit(self, MockService, client, db):
        mock = MockService.return_value
        mock.exchange_code.return_value = {
            "access_token": "acc",
            "refresh_token": "ref",
        }
        mock.get_current_user.return_value = {
            "id": "audit_user",
            "display_name": "Audit Test",
        }

        client.get("/auth/callback", params={"code": "code"})

        entry = db.query(AuditLog).filter(AuditLog.action == "auth.callback").first()
        assert entry is not None
        assert entry.user_id == "audit_user"
        assert entry.status == "success"

    @patch("app.routers.auth.SpotifyService")
    def test_callback_code_exchange_failure(self, MockService, client, db):
        mock = MockService.return_value
        mock.exchange_code.side_effect = Exception("invalid code")

        resp = client.get("/auth/callback", params={"code": "bad_code"})
        assert resp.status_code == 400

        entry = db.query(AuditLog).filter(
            AuditLog.action == "auth.callback",
            AuditLog.status == "error",
        ).first()
        assert entry is not None

    @patch("app.routers.auth.SpotifyService")
    def test_callback_missing_code_param(self, MockService, client, db):
        resp = client.get("/auth/callback")
        assert resp.status_code == 422


class TestHealthCheck:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
