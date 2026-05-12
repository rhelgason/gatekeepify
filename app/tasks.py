import logging
from datetime import datetime, timezone

from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError
from sqlalchemy import func, select

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Listen, User
from app.services.ingestion import (
    get_active_users,
    get_tracks_missing_metadata,
    log_job_run,
    retroactively_validate_export_listens,
    upsert_from_recent_listens,
    upsert_track_metadata,
)
from app.services.spotify import SpotifyService, decrypt_token, encrypt_token

logger = logging.getLogger(__name__)


def _is_token_revoked(exc: Exception) -> bool:
    if isinstance(exc, SpotifyOauthError):
        return True
    if isinstance(exc, SpotifyException) and exc.http_status in (401, 403):
        return True
    return False


def _deactivate_user(db, user: User, reason: str) -> None:
    user.spotify_refresh_token = None
    db.commit()
    logger.warning(
        f"Deactivated user {user.user_id}: {reason}. "
        f"User must re-authenticate via /auth/login to resume polling."
    )


@celery_app.task(name="app.tasks.poll_recent_listens")
def poll_recent_listens():
    db = SessionLocal()
    try:
        service = SpotifyService()
        users = get_active_users(db)
        logger.info(f"Polling recent listens for {len(users)} users")
        for user in users:
            try:
                _poll_single_user(db, service, user)
            except Exception as e:
                if _is_token_revoked(e):
                    _deactivate_user(db, user, f"token revoked ({e})")
                    log_job_run(
                        db,
                        "poll_recent_listens",
                        user.user_id,
                        datetime.now(timezone.utc),
                        datetime.now(timezone.utc),
                        "token_revoked",
                    )
                else:
                    logger.error(f"Failed to poll user {user.user_id}: {e}")
                    log_job_run(
                        db,
                        "poll_recent_listens",
                        user.user_id,
                        datetime.now(timezone.utc),
                        datetime.now(timezone.utc),
                        "error",
                    )
    finally:
        db.close()


def _poll_single_user(
    db, service: SpotifyService, user: User
) -> None:
    started_at = datetime.now(timezone.utc)

    refresh_token = decrypt_token(user.spotify_refresh_token)
    token_info = service.refresh_access_token(refresh_token)
    access_token = token_info["access_token"]

    new_refresh = token_info.get("refresh_token")
    if new_refresh and new_refresh != refresh_token:
        user.spotify_refresh_token = encrypt_token(new_refresh)

    last_ts = db.execute(
        select(func.max(Listen.ts)).where(Listen.user_id == user.user_id)
    ).scalar()

    items = service.get_recent_listens(access_token, after=last_ts)
    count = 0
    if items:
        count = upsert_from_recent_listens(db, items, user.user_id)

    user.last_poll_at = datetime.now(timezone.utc)
    db.commit()

    log_job_run(
        db,
        "poll_recent_listens",
        user.user_id,
        started_at,
        datetime.now(timezone.utc),
        "success",
        count,
    )
    logger.info(f"Polled {count} new listens for user {user.user_id}")


@celery_app.task(name="app.tasks.backfill_track_metadata")
def backfill_track_metadata():
    db = SessionLocal()
    started_at = datetime.now(timezone.utc)
    try:
        missing = get_tracks_missing_metadata(db)
        if not missing:
            return

        service = SpotifyService()
        users = get_active_users(db)
        if not users:
            logger.warning("No active users available to backfill track metadata")
            return

        access_token = _get_working_access_token(db, service, users)
        if not access_token:
            logger.error("All active users have revoked tokens, cannot backfill")
            return

        items = service.get_tracks(access_token, list(missing))
        count = 0
        if items:
            count = upsert_track_metadata(db, items)

        removed = retroactively_validate_export_listens(db, missing)
        if removed:
            logger.info(
                f"Removed {removed} export listens that predate track release dates"
            )

        log_job_run(
            db,
            "backfill_track_metadata",
            None,
            started_at,
            datetime.now(timezone.utc),
            "success",
            count,
        )
        logger.info(f"Backfilled metadata for {count} tracks")
    except Exception as e:
        logger.error(f"Failed to backfill track metadata: {e}")
        log_job_run(
            db,
            "backfill_track_metadata",
            None,
            started_at,
            datetime.now(timezone.utc),
            "error",
        )
    finally:
        db.close()


def _get_working_access_token(db, service: SpotifyService, users: list) -> str | None:
    for user in users:
        try:
            refresh_token = decrypt_token(user.spotify_refresh_token)
            token_info = service.refresh_access_token(refresh_token)
            return token_info["access_token"]
        except Exception as e:
            if _is_token_revoked(e):
                _deactivate_user(db, user, f"token revoked ({e})")
            else:
                logger.warning(f"Failed to refresh token for {user.user_id}: {e}")
    return None
