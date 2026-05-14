import logging
from datetime import datetime, timezone

from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError
from sqlalchemy import func, select

from app.celery_app import celery_app
from app.config import settings
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


MAX_USERS_PER_CYCLE = 500
INTER_USER_DELAY = 1.0


@celery_app.task(name="app.tasks.poll_recent_listens", bind=True)
def poll_recent_listens(self):
    import time

    lock_key = "lock:poll_recent_listens"
    lock = None
    try:
        from redis import Redis
        redis = Redis.from_url(settings.redis_url)
        lock = redis.lock(lock_key, timeout=settings.poll_interval_seconds - 10)
        if not lock.acquire(blocking=False):
            logger.warning("poll_recent_listens skipped: previous cycle still running")
            return
    except Exception as e:
        logger.warning(f"Could not acquire Redis lock, running without lock: {e}")

    db = SessionLocal()
    started_at = datetime.now(timezone.utc)
    try:
        service = SpotifyService()
        all_users = get_active_users(db)
        total_users = len(all_users)

        all_users.sort(key=lambda u: u.last_poll_at or datetime.min)
        batch = all_users[:MAX_USERS_PER_CYCLE]

        logger.info(
            f"Polling recent listens: {len(batch)}/{total_users} users "
            f"(oldest poll: {batch[0].last_poll_at if batch else 'N/A'})"
        )

        polled = 0
        errors = 0
        for user in batch:
            try:
                _poll_single_user(db, service, user)
                polled += 1
            except Exception as e:
                db.rollback()
                errors += 1
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

            if INTER_USER_DELAY > 0 and len(batch) > 10:
                time.sleep(INTER_USER_DELAY)

        pending = total_users - len(batch)
        logger.info(
            f"Poll cycle complete: {polled} polled, {errors} errors, "
            f"{pending} pending for next cycle"
        )
        log_job_run(
            db, "poll_recent_listens", None, started_at,
            datetime.now(timezone.utc), "success", polled,
        )
    except Exception as e:
        logger.error(f"Poll cycle failed: {e}")
        log_job_run(db, "poll_recent_listens", None, started_at,
                    datetime.now(timezone.utc), "error")
    finally:
        db.close()
        if lock:
            try:
                lock.release()
            except Exception:
                pass


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


@celery_app.task(name="app.tasks.compute_award_snapshots")
def compute_award_snapshots():
    from app.models import AwardSnapshot
    from app.services.awards import (
        ALL_COMPUTE_FUNCTIONS,
        get_friend_group_hash,
    )

    db = SessionLocal()
    started_at = datetime.now(timezone.utc)
    try:
        get_active_users(db)
        all_users = db.query(User).all()
        processed_groups = set()
        total_snapshots = 0

        for u in all_users:
            friend_ids = [
                r[0] for r in db.execute(
                    __import__("sqlalchemy", fromlist=["select"]).select(
                        __import__("app.models", fromlist=["Friendship"]).Friendship.user_id_2
                    ).where(
                        __import__("app.models", fromlist=["Friendship"]).Friendship.user_id_1 == u.user_id
                    )
                ).all()
            ]
            if not friend_ids:
                continue

            group_ids = sorted([u.user_id] + friend_ids)
            group_hash = get_friend_group_hash(group_ids)

            if group_hash in processed_groups:
                continue
            processed_groups.add(group_hash)

            cached_awards = {"archaeologist", "patient_zero", "completionist", "genre_snob", "time_traveler", "streak", "hypebeast"}
            for award_id in cached_awards:
                fn = ALL_COMPUTE_FUNCTIONS.get(award_id)
                if not fn:
                    continue
                try:
                    results = fn(db, group_ids)
                    for entry in results:
                        db.merge(AwardSnapshot(
                            user_id=entry["user_id"],
                            friend_group_hash=group_hash,
                            award_id=award_id,
                            rank=entry["rank"],
                            stat_value=entry.get("stat_value"),
                            stat_detail=entry.get("stat_detail"),
                            entity_id=entry.get("entity_id"),
                            entity_name=entry.get("entity_name"),
                            computed_at=datetime.now(timezone.utc),
                        ))
                        total_snapshots += 1
                except Exception as e:
                    logger.warning(f"Failed to compute {award_id}: {e}")
                    db.rollback()

            db.commit()

        log_job_run(db, "compute_award_snapshots", None, started_at, datetime.now(timezone.utc), "success", total_snapshots)
        logger.info(f"Computed {total_snapshots} award snapshots across {len(processed_groups)} groups")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to compute award snapshots: {e}")
        log_job_run(db, "compute_award_snapshots", None, started_at, datetime.now(timezone.utc), "error")
    finally:
        db.close()


@celery_app.task(name="app.tasks.process_backfill_upload")
def process_backfill_upload(job_id: int, user_id: str, encoded_content: str):
    import base64
    import json

    from app.models import JobRun, Track
    from app.routers.backfill import (
        _extract_json_from_zip,
        _validate_and_process_listens,
    )
    from app.services.audit import log_action

    db = SessionLocal()
    try:
        job = db.query(JobRun).filter(JobRun.id == job_id).first()
        if not job:
            logger.error(f"Backfill job {job_id} not found")
            return

        def _update_job(phase: str, progress: int, **extra):
            details = json.loads(job.details) if job.details else {}
            details.update({"phase": phase, "progress": progress, **extra})
            job.details = json.dumps(details)
            db.commit()

        job.status = "running"
        _update_job("extracting", 5)

        content = base64.b64decode(encoded_content)
        raw_listens = _extract_json_from_zip(content)

        if not raw_listens:
            job.status = "error"
            job.completed_at = datetime.now(timezone.utc)
            _update_job("error", 100, error="No streaming history files found in the ZIP")
            log_action(db, "backfill.upload", user_id=user_id, status="error",
                       details={"reason": "no_streaming_history_files"})
            return

        _update_job("validating", 15, total_listens=len(raw_listens))

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            job.status = "error"
            job.completed_at = datetime.now(timezone.utc)
            _update_job("error", 100, error="User not found")
            return

        accepted, rejection_reasons = _validate_and_process_listens(
            raw_listens, user, db
        )

        _update_job("inserting", 40, total_listens=len(raw_listens),
                     accepted_count=len(accepted))

        inserted = 0
        batch_size = 500
        for i in range(0, len(accepted), batch_size):
            batch = accepted[i:i + batch_size]
            for listen, track_name in batch:
                from sqlalchemy import select as sa_select
                existing = db.execute(
                    sa_select(Listen).where(
                        Listen.user_id == listen.user_id,
                        Listen.track_id == listen.track_id,
                        Listen.ts == listen.ts,
                    )
                ).first()
                if existing:
                    continue

                existing_track = (
                    db.query(Track).filter(Track.track_id == listen.track_id).first()
                )
                if not existing_track:
                    db.merge(Track(track_id=listen.track_id, track_name=track_name))

                db.add(listen)
                inserted += 1
            db.commit()

            progress = 40 + int(35 * (i + len(batch)) / max(len(accepted), 1))
            _update_job("inserting", min(progress, 75), inserted=inserted)

        _update_job("enriching", 80, inserted=inserted)

        MAX_IMMEDIATE_ENRICHMENT = 500
        new_track_ids = list({
            listen.track_id for listen, _ in accepted
            if db.query(Track).filter(
                Track.track_id == listen.track_id, Track.album_id.is_(None)
            ).first()
        })[:MAX_IMMEDIATE_ENRICHMENT]

        enriched = 0
        if new_track_ids:
            try:
                from spotipy.exceptions import SpotifyException as SpotifyExc
                user_obj = db.query(User).filter(User.user_id == user_id).first()
                if user_obj and user_obj.spotify_refresh_token:
                    service = SpotifyService()
                    refresh_token = decrypt_token(user_obj.spotify_refresh_token)
                    token_info = service.refresh_access_token(refresh_token)
                    access_token = token_info["access_token"]
                    items = service.get_tracks(access_token, new_track_ids)
                    if items:
                        enriched = upsert_track_metadata(db, items)
            except Exception as e:
                logger.warning(f"Enrichment during backfill upload: {e}")

        _update_job("analyzing", 95, enriched=enriched)

        from app.services.anomaly import analyze_user_export
        anomaly_result = analyze_user_export(db, user_id)
        if anomaly_result["flags"]:
            log_action(db, "backfill.anomaly_detected", user_id=user_id,
                       status="warning", details=anomaly_result)

        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.record_count = inserted
        _update_job("done", 100,
                    inserted=inserted,
                    accepted=len(accepted),
                    rejected=len(raw_listens) - len(accepted),
                    rejection_reasons=rejection_reasons,
                    enriched=enriched,
                    trust_score=anomaly_result["score"])

        log_action(db, "backfill.upload", user_id=user_id,
                   details={
                       "total_processed": len(raw_listens),
                       "total_accepted": inserted,
                       "total_rejected": len(raw_listens) - len(accepted),
                       "rejection_reasons": rejection_reasons,
                       "tracks_enriched_immediately": enriched,
                       "trust_score": anomaly_result["score"],
                   })
        logger.info(f"Backfill upload complete for {user_id}: {inserted} inserted, {enriched} enriched")

    except Exception as e:
        logger.error(f"Backfill upload task failed for job {job_id}: {e}")
        try:
            job = db.query(JobRun).filter(JobRun.id == job_id).first()
            if job:
                job.status = "error"
                job.completed_at = datetime.now(timezone.utc)
                details = json.loads(job.details) if job.details else {}
                details.update({"phase": "error", "progress": 0, "error": str(e)})
                job.details = json.dumps(details)
                db.commit()
        except Exception:
            pass
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
