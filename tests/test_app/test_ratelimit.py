"""Tests for the dependency-free rate limiter (app/services/ratelimit.py)."""

import pytest

from app.services import ratelimit
from app.services.ratelimit import _FixedWindowLimiter, reset_limiter


class TestFixedWindowLimiter:
    def test_allows_under_limit(self):
        lim = _FixedWindowLimiter()
        for _ in range(3):
            allowed, retry = lim.check("k", max_requests=3, window_seconds=60)
            assert allowed
            assert retry == 0

    def test_blocks_over_limit(self):
        lim = _FixedWindowLimiter()
        for _ in range(3):
            assert lim.check("k", 3, 60)[0] is True
        allowed, retry = lim.check("k", 3, 60)
        assert allowed is False
        assert retry >= 1

    def test_keys_are_independent(self):
        lim = _FixedWindowLimiter()
        assert lim.check("a", 1, 60)[0] is True
        assert lim.check("a", 1, 60)[0] is False
        # Different key still has its own budget.
        assert lim.check("b", 1, 60)[0] is True

    def test_reset_clears_state(self):
        lim = _FixedWindowLimiter()
        assert lim.check("k", 1, 60)[0] is True
        assert lim.check("k", 1, 60)[0] is False
        lim.reset()
        assert lim.check("k", 1, 60)[0] is True

    def test_window_expiry_allows_again(self):
        lim = _FixedWindowLimiter()
        assert lim.check("k", 1, window_seconds=0)[0] is True
        # With a zero-length window every prior hit is already expired.
        assert lim.check("k", 1, window_seconds=0)[0] is True


@pytest.fixture()
def low_search_limit():
    original = ratelimit.LIMITS["search"]
    ratelimit.LIMITS["search"] = (2, 60)
    reset_limiter()
    yield
    ratelimit.LIMITS["search"] = original
    reset_limiter()


class TestRateLimitedEndpoint:
    def test_search_returns_429_after_limit(self, client, seeded_db, auth_headers, low_search_limit):
        # First two requests pass.
        for _ in range(2):
            r = client.get("/search/artists", params={"q": "Radiohead"}, headers=auth_headers)
            assert r.status_code == 200
        # Third trips the limit.
        r = client.get("/search/artists", params={"q": "Radiohead"}, headers=auth_headers)
        assert r.status_code == 429
        assert "Retry-After" in r.headers

    def test_rate_limit_records_denied_audit(self, client, seeded_db, auth_headers, db, low_search_limit):
        from app.models import AuditLog

        for _ in range(3):
            client.get("/search/artists", params={"q": "Radiohead"}, headers=auth_headers)
        denied = db.query(AuditLog).filter(AuditLog.action == "search.rate_limited").all()
        assert len(denied) >= 1
        assert denied[0].status == "denied"

    def test_disabled_when_setting_off(self, client, seeded_db, auth_headers, low_search_limit, monkeypatch):
        from app.config import settings

        monkeypatch.setattr(settings, "rate_limit_enabled", False)
        # Far exceed the limit; all should pass with limiting disabled.
        for _ in range(5):
            r = client.get("/search/artists", params={"q": "Radiohead"}, headers=auth_headers)
            assert r.status_code == 200
