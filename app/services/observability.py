"""Optional Sentry error tracking.

``init_sentry`` is a safe no-op unless ``SENTRY_DSN`` is configured AND the
``sentry-sdk`` package is installed, so the app runs identically in dev/CI
(where the SDK isn't installed) and gains crash + slow-task visibility in
production once the DSN is set. Called from both the web app (``main.py``) and
the Celery process (``celery_app.py``) so silent task failures surface too.

Returns True if Sentry was actually initialized, else False (handy for tests).
"""

import logging

from app.config import settings

logger = logging.getLogger("gatekeepify.observability")


def init_sentry() -> bool:
    if not settings.sentry_dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
    except ImportError:
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed; "
            "run `pip install sentry-sdk[fastapi]` to enable error tracking."
        )
        return False

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
    logger.info("Sentry error tracking initialized")
    return True
