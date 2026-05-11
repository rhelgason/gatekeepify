from datetime import datetime, timezone

from jose import jwt

from app.config import settings
from app.models import User


class TestAuthMe:
    def test_get_me(self, client, seeded_db, test_user_token):
        resp = client.get("/auth/me", params={"token": test_user_token})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "test_user_1"
        assert data["user_name"] == "Test User"

    def test_get_me_invalid_token(self, client, seeded_db):
        resp = client.get("/auth/me", params={"token": "garbage"})
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
        resp = client.get("/auth/me", params={"token": token})
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
        resp = client.get("/auth/me", params={"token": token})
        assert resp.status_code == 401


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


class TestHealthCheck:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
