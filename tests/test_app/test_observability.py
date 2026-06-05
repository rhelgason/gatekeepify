"""Tests for the optional Sentry integration (app/services/observability.py)."""

from app.config import settings
from app.services.observability import init_sentry


def test_no_dsn_is_noop(monkeypatch):
    monkeypatch.setattr(settings, "sentry_dsn", "")
    assert init_sentry() is False


def test_dsn_set_but_sdk_missing_logs_and_returns_false(monkeypatch, caplog):
    """With a DSN but sentry-sdk not installed (the CI/test environment),
    init_sentry must warn and return False rather than crash."""
    monkeypatch.setattr(settings, "sentry_dsn", "https://example@sentry.invalid/1")
    import builtins

    real_import = builtins.__import__

    def _fail_sentry_import(name, *args, **kwargs):
        if name.startswith("sentry_sdk"):
            raise ImportError("sentry-sdk not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fail_sentry_import)
    with caplog.at_level("WARNING"):
        result = init_sentry()
    assert result is False
    assert any("sentry-sdk" in r.message for r in caplog.records)
