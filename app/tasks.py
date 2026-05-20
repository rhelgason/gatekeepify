import logging
from datetime import datetime, timezone

from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError
from sqlalchemy import func, select

from app.celery_app import celery_app
from app.config import settings
from app.database import SessionLocal
from app.models import Listen, User
from app.models import Friendship
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
        f"Deactivated user {user.user_id}: {reason}. User must re-authenticate via /auth/login to resume polling."
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
        logger.info(f"Poll cycle complete: {polled} polled, {errors} errors, {pending} pending for next cycle")
        log_job_run(
            db,
            "poll_recent_listens",
            None,
            started_at,
            datetime.now(timezone.utc),
            "success",
            polled,
        )
    except Exception as e:
        logger.error(f"Poll cycle failed: {e}")
        log_job_run(db, "poll_recent_listens", None, started_at, datetime.now(timezone.utc), "error")
    finally:
        db.close()
        if lock:
            try:
                lock.release()
            except Exception:
                pass


def _poll_single_user(db, service: SpotifyService, user: User) -> None:
    started_at = datetime.now(timezone.utc)

    refresh_token = decrypt_token(user.spotify_refresh_token)
    token_info = service.refresh_access_token(refresh_token)
    access_token = token_info["access_token"]

    new_refresh = token_info.get("refresh_token")
    if new_refresh and new_refresh != refresh_token:
        user.spotify_refresh_token = encrypt_token(new_refresh)

    last_ts = db.execute(select(func.max(Listen.ts)).where(Listen.user_id == user.user_id)).scalar()

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
        enriched_ids = set()
        if items:
            count = upsert_track_metadata(db, items)
            enriched_ids = {item["track"]["id"] for item in items if item.get("track", {}).get("id")}
        failed_ids = missing - enriched_ids
        if failed_ids:
            from app.models import Track

            db.execute(
                Track.__table__.update()
                .where(Track.__table__.c.track_id.in_(failed_ids))
                .values(enrich_attempts=func.coalesce(Track.__table__.c.enrich_attempts, 0) + 1)
            )
            db.commit()

        removed = retroactively_validate_export_listens(db, missing)
        if removed:
            logger.info(f"Removed {removed} export listens that predate track release dates")

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
        db.rollback()
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
                r[0] for r in db.execute(select(Friendship.user_id_2).where(Friendship.user_id_1 == u.user_id)).all()
            ]
            if not friend_ids:
                continue

            group_ids = sorted([u.user_id] + friend_ids)
            group_hash = get_friend_group_hash(group_ids)

            if group_hash in processed_groups:
                continue
            processed_groups.add(group_hash)

            cached_awards = {
                "archaeologist",
                "patient_zero",
                "completionist",
                "genre_snob",
                "time_traveler",
                "streak",
                "hypebeast",
            }
            for award_id in cached_awards:
                fn = ALL_COMPUTE_FUNCTIONS.get(award_id)
                if not fn:
                    continue
                try:
                    results = fn(db, group_ids)
                    for entry in results:
                        db.merge(
                            AwardSnapshot(
                                user_id=entry["user_id"],
                                friend_group_hash=group_hash,
                                award_id=award_id,
                                rank=entry["rank"],
                                stat_value=entry.get("stat_value"),
                                stat_detail=entry.get("stat_detail"),
                                entity_id=entry.get("entity_id"),
                                entity_name=entry.get("entity_name"),
                                computed_at=datetime.now(timezone.utc),
                            )
                        )
                        total_snapshots += 1
                except Exception as e:
                    logger.warning(f"Failed to compute {award_id}: {e}")
                    db.rollback()

            db.commit()

        log_job_run(
            db, "compute_award_snapshots", None, started_at, datetime.now(timezone.utc), "success", total_snapshots
        )
        logger.info(f"Computed {total_snapshots} award snapshots across {len(processed_groups)} groups")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to compute award snapshots: {e}")
        log_job_run(db, "compute_award_snapshots", None, started_at, datetime.now(timezone.utc), "error")
    finally:
        db.close()


@celery_app.task(name="app.tasks.process_backfill_upload", acks_late=True, reject_on_worker_lost=True)
def process_backfill_upload(job_id: int, user_id: str):
    import json
    import time

    from app.models import JobRun, Track
    from app.routers.backfill import _validate_and_process_listens
    from app.services.audit import log_action
    from app.services.ingestion import get_tracks_missing_metadata, retroactively_validate_export_listens
    from sqlalchemy.dialects import sqlite as sqlite_dialect
    from sqlalchemy.dialects import postgresql as pg_dialect
    from spotipy.exceptions import SpotifyException as SpotifyExc

    db = SessionLocal()
    try:
        job = db.query(JobRun).filter(JobRun.id == job_id).first()
        if not job:
            logger.error(f"Backfill job {job_id} not found")
            return

        def _update_job(phase, progress, **extra):
            det = json.loads(job.details) if job.details else {}
            det.pop("listen_data", None)
            det.update({"phase": phase, "progress": progress, **extra})
            job.details = json.dumps(det)
            db.commit()

        job.status = "running"
        details = json.loads(job.details) if job.details else {}
        raw_listens = details.get("listen_data", [])
        prev_phase = details.get("phase", "")
        resuming = not raw_listens and prev_phase in ("resuming", "enriching", "analyzing", "inserting")

        if not raw_listens and not resuming:
            job.status = "error"
            job.completed_at = datetime.now(timezone.utc)
            _update_job("error", 100, error="No listen data found in job")
            return

        user_obj = db.query(User).filter(User.user_id == user_id).first()
        if not user_obj:
            job.status = "error"
            job.completed_at = datetime.now(timezone.utc)
            _update_job("error", 100, error="User not found")
            return

        inserted = details.get("inserted", 0)
        rejection_reasons = details.get("rejection_reasons", {})
        total_processed = details.get("total_listens", 0)
        total_accepted = inserted

        # --- Phase 1: Validate and insert listens ---
        if not resuming:
            _update_job("validating", 15, total_listens=len(raw_listens))
            accepted, rejection_reasons = _validate_and_process_listens(raw_listens, user_obj, db)
            total_processed = len(raw_listens)
            total_accepted = len(accepted)
            _update_job("inserting", 40, total_listens=total_processed, accepted_count=total_accepted)

            inserted = 0
            batch_size = 500
            for bi in range(0, len(accepted), batch_size):
                db.refresh(job)
                if job.status == "error":
                    logger.info(f"Backfill job {job_id} was cancelled, stopping")
                    return
                batch = accepted[bi : bi + batch_size]
                seen_tracks = set()
                for listen, track_name in batch:
                    if listen.track_id not in seen_tracks:
                        seen_tracks.add(listen.track_id)
                        if not db.query(Track).filter(Track.track_id == listen.track_id).first():
                            db.merge(Track(track_id=listen.track_id, track_name=track_name))
                db.flush()

                seen_listens = set()
                listen_rows = []
                for listen, track_name in batch:
                    lk = (listen.user_id, listen.track_id, str(listen.ts))
                    if lk in seen_listens:
                        continue
                    seen_listens.add(lk)
                    listen_rows.append(
                        {
                            "ts": listen.ts,
                            "user_id": listen.user_id,
                            "track_id": listen.track_id,
                            "source": listen.source,
                            "ms_played": listen.ms_played,
                            "export_metadata": listen.export_metadata,
                        }
                    )
                if listen_rows:
                    dialect = db.bind.dialect.name if db.bind else "sqlite"
                    tbl = Listen.__table__
                    if dialect == "postgresql":
                        stmt = pg_dialect.insert(tbl).values(listen_rows)
                    else:
                        stmt = sqlite_dialect.insert(tbl).values(listen_rows)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["ts", "user_id", "track_id"],
                        set_={"ms_played": stmt.excluded.ms_played},
                        where=tbl.c.ms_played.is_(None),
                    )
                    result = db.execute(stmt)
                    inserted += result.rowcount
                db.commit()
                progress = 40 + int(35 * (bi + len(batch)) / max(total_accepted, 1))
                _update_job("inserting", min(progress, 75), inserted=inserted)

        # --- Phase 2: Enrich track metadata ---
        all_unenriched = list(get_tracks_missing_metadata(db, limit=100000))
        total_to_enrich = len(all_unenriched)
        _update_job("enriching", 80, inserted=inserted, enrich_total=total_to_enrich, enrich_done=0)

        enriched = 0
        enrich_idx = 0
        rate_limit_strikes = 0
        if total_to_enrich > 0 and user_obj.spotify_refresh_token:
            try:
                service = SpotifyService()
                refresh_token = decrypt_token(user_obj.spotify_refresh_token)
                token_info = service.refresh_access_token(refresh_token)
                client = service.get_client(token_info["access_token"])

                while enrich_idx < total_to_enrich:
                    db.refresh(job)
                    if job.status == "error":
                        logger.info(f"Backfill job {job_id} cancelled during enrichment")
                        return
                    batch = all_unenriched[enrich_idx : enrich_idx + 50]
                    try:
                        res = client.tracks(batch)
                        if res and res.get("tracks"):
                            items = [{"track": t} for t in res["tracks"] if t]
                            service._enrich_with_genres(client, items)
                            enriched += upsert_track_metadata(db, items)
                        rate_limit_strikes = 0
                        enrich_idx += 50
                    except SpotifyExc as e:
                        if e.http_status == 429:
                            retry_after = (
                                int(e.headers.get("Retry-After", 5)) if hasattr(e, "headers") and e.headers else 5
                            )
                            rate_limit_strikes += 1
                            if rate_limit_strikes >= 5:
                                logger.warning(f"Too many rate limits, stopping at {enriched}/{total_to_enrich}")
                                break
                            time.sleep(retry_after)
                        elif e.http_status in (401, 403):
                            try:
                                token_info = service.refresh_access_token(refresh_token)
                                client = service.get_client(token_info["access_token"])
                            except Exception:
                                logger.warning("Token refresh failed, stopping enrichment")
                                break
                        else:
                            enrich_idx += 50
                    except Exception as e:
                        logger.warning(f"Error during enrichment batch: {e}")
                        db.rollback()
                        enrich_idx += 50
                    progress = 80 + int(15 * min(enrich_idx, total_to_enrich) / total_to_enrich)
                    _update_job("enriching", min(progress, 95), enrich_total=total_to_enrich, enrich_done=enriched)
            except Exception as e:
                logger.warning(f"Enrichment setup failed: {e}")

        # --- Phase 3: Retroactive validation ---
        if enriched > 0:
            enriched_ids = set(all_unenriched[: min(enrich_idx, total_to_enrich)])
            removed = retroactively_validate_export_listens(db, enriched_ids)
            if removed:
                logger.info(f"Removed {removed} pre-release listens after enrichment")

        # --- Phase 4: Anomaly detection ---
        _update_job("analyzing", 95, enriched=enriched, enrich_total=total_to_enrich, enrich_done=enriched)
        from app.services.anomaly import analyze_user_export

        anomaly_result = analyze_user_export(db, user_id)
        if anomaly_result["flags"]:
            log_action(db, "backfill.anomaly_detected", user_id=user_id, status="warning", details=anomaly_result)

        # --- Done ---
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.record_count = inserted
        rejected = total_processed - total_accepted if total_processed else 0
        _update_job(
            "done",
            100,
            inserted=inserted,
            accepted=total_accepted,
            rejected=rejected,
            rejection_reasons=rejection_reasons,
            enriched=enriched,
            trust_score=anomaly_result["score"],
        )

        log_action(
            db,
            "backfill.upload",
            user_id=user_id,
            details={
                "total_processed": total_processed,
                "total_accepted": inserted,
                "total_rejected": rejected,
                "rejection_reasons": rejection_reasons,
                "tracks_enriched": enriched,
                "trust_score": anomaly_result["score"],
            },
        )
        logger.info(f"Backfill upload complete for {user_id}: {inserted} inserted, {enriched} enriched")

    except Exception as e:
        logger.error(f"Backfill upload task failed for job {job_id}: {e}")
        try:
            db.rollback()
            job = db.query(JobRun).filter(JobRun.id == job_id).first()
            if job:
                job.status = "error"
                job.completed_at = datetime.now(timezone.utc)
                det = json.loads(job.details) if job.details else {}
                det.update({"phase": "error", "progress": 0, "error": str(e)})
                job.details = json.dumps(det)
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
