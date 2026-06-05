"""Lightweight, dependency-free rate limiting.

An in-memory fixed-window limiter. This is correct for the current deployment,
which runs a single uvicorn web process (see ``supervisord.conf``). If the web
tier is ever scaled to multiple processes/replicas, swap ``_FixedWindowLimiter``
for a Redis-backed counter (the app already depends on Redis for Celery) — the
public ``enforce_rate_limit`` API stays the same.

Limits are enforced by calling ``enforce_rate_limit`` at the top of an endpoint
body rather than via a FastAPI dependency, which keeps this module free of any
import cycle with ``app.routers.auth``.
"""

import threading
import time
from collections import defaultdict
from typing import Tuple

from fastapi import HTTPException, Request

from app.config import settings
from app.services.audit import log_action

# scope -> (max_requests, window_seconds). Tunable; tests monkeypatch entries.
LIMITS: dict[str, Tuple[int, int]] = {
    "auth.login": (20, 60),
    "auth.callback": (20, 60),
    "friends.accept": (20, 60),  # invite-code brute force is the real risk
    "friends.search": (40, 60),
    "backfill.upload": (5, 3600),  # large ZIPs + expensive enrichment
    "search": (80, 60),  # live debounced search legitimately bursts
}


class _FixedWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int]:
        """Record a hit. Returns ``(allowed, retry_after_seconds)``."""
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            hits = self._hits[key]
            # Drop timestamps that have aged out of the window.
            fresh = [t for t in hits if t > cutoff]
            if len(fresh) >= max_requests:
                retry_after = int(window_seconds - (now - fresh[0])) + 1
                self._hits[key] = fresh
                return False, max(retry_after, 1)
            fresh.append(now)
            self._hits[key] = fresh
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiter = _FixedWindowLimiter()


def reset_limiter() -> None:
    """Test helper: clear all rate-limit state."""
    _limiter.reset()


def client_ip(request: Request) -> str:
    """Best-effort client IP. Honors X-Forwarded-For (we sit behind Railway's proxy)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(db, scope: str, key: str) -> None:
    """Raise HTTP 429 if ``key`` has exceeded the limit configured for ``scope``.

    ``db`` is used to record a ``{scope}.rate_limited`` audit entry on denial.
    """
    if not settings.rate_limit_enabled:
        return
    max_requests, window_seconds = LIMITS[scope]
    allowed, retry_after = _limiter.check(f"{scope}:{key}", max_requests, window_seconds)
    if allowed:
        return
    try:
        log_action(
            db,
            f"{scope}.rate_limited",
            status="denied",
            details={"limit": max_requests, "window_s": window_seconds},
        )
    except Exception:
        pass
    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please slow down and try again shortly.",
        headers={"Retry-After": str(retry_after)},
    )
