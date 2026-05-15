import logging
import time
import traceback

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError

from sqlalchemy import text
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, validate_settings
from app.database import Base, SessionLocal, engine, get_db
from app.routers import auth, awards, backfill, discover, friends, gatekeep, search, stats
from app.models import User
from app.routers.auth import get_admin_user, get_current_user
from app.services.audit import log_action

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("gatekeepify.http")

validate_settings()
Base.metadata.create_all(bind=engine)

def _add_column_if_missing(engine, table, column, col_type):
    from sqlalchemy import inspect as sa_inspect, text as sa_text
    insp = sa_inspect(engine)
    existing = [c["name"] for c in insp.get_columns(table)]
    if column not in existing:
        with engine.begin() as conn:
            conn.execute(sa_text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        logger.info(f"Added column {table}.{column}")

try:
    _add_column_if_missing(engine, "dim_all_albums", "image_url", "VARCHAR(512)")
    _add_column_if_missing(engine, "dim_all_tracks", "image_url", "VARCHAR(512)")
    _add_column_if_missing(engine, "dim_all_artists", "image_url", "VARCHAR(512)")
    _add_column_if_missing(engine, "friend_invites", "to_user_id", "VARCHAR(255)")
    _add_column_if_missing(engine, "dim_all_users", "token_invalidated_at", "TIMESTAMP")
    _add_column_if_missing(engine, "dim_all_users", "image_url", "VARCHAR(512)")
    _add_column_if_missing(engine, "dim_all_users", "is_admin", "BOOLEAN DEFAULT FALSE")
    _add_column_if_missing(engine, "job_runs", "details", "TEXT")
except Exception as e:
    logger.warning(f"Column migration skipped: {e}")

try:
    from app.models import JobRun
    from datetime import datetime, timezone
    _startup_db = SessionLocal()
    orphaned = _startup_db.query(JobRun).filter(
        JobRun.job_name == "backfill_upload",
        JobRun.status.in_(["pending", "running"]),
    ).all()
    for j in orphaned:
        j.status = "error"
        j.completed_at = datetime.now(timezone.utc)
        import json as _json
        details = _json.loads(j.details) if j.details else {}
        details.pop("listen_data", None)
        details.update({"phase": "error", "error": "Server restarted during processing"})
        j.details = _json.dumps(details)
    if orphaned:
        _startup_db.commit()
        logger.info(f"Marked {len(orphaned)} orphaned upload jobs as failed")
    _startup_db.close()
except Exception as e:
    logger.warning(f"Orphaned job cleanup skipped: {e}")

app = FastAPI(
    title="Gatekeepify",
    description="Prove you listened first.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(stats.router)
app.include_router(backfill.router)
app.include_router(friends.router)
app.include_router(gatekeep.router)
app.include_router(search.router)
app.include_router(awards.router)
app.include_router(discover.router)


def _error_response(status_code: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": error, "detail": detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append(f"{field}: {err.get('msg', 'invalid')}")
    detail = "; ".join(errors)
    logger.warning(f"Validation error on {request.method} {request.url.path}: {detail}")
    return _error_response(422, "validation_error", detail)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return _error_response(exc.status_code, "http_error", str(exc.detail))


@app.exception_handler(OperationalError)
async def database_exception_handler(request: Request, exc: OperationalError):
    logger.error(f"Database error on {request.method} {request.url.path}: {exc}")
    return _error_response(503, "database_error", "Database is temporarily unavailable")


@app.exception_handler(SpotifyOauthError)
async def spotify_oauth_exception_handler(request: Request, exc: SpotifyOauthError):
    logger.error(f"Spotify OAuth error on {request.method} {request.url.path}: {exc}")
    return _error_response(502, "spotify_auth_error", "Spotify authentication failed")


@app.exception_handler(SpotifyException)
async def spotify_api_exception_handler(request: Request, exc: SpotifyException):
    logger.error(f"Spotify API error on {request.method} {request.url.path}: {exc}")
    return _error_response(502, "spotify_api_error", "Spotify API request failed")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}\n"
        f"{traceback.format_exc()}"
    )
    db = None
    try:
        db = SessionLocal()
        log_action(
            db, "system.unhandled_error",
            status="error",
            details={
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
    except Exception:
        pass
    finally:
        if db:
            db.close()
    return _error_response(500, "internal_error", "Internal server error")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception:
        duration = time.time() - start
        logger.error(
            f"{request.method} {request.url.path} -> 500 ({duration:.3f}s)"
        )
        raise
    duration = time.time() - start
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration:.3f}s)"
    )
    return response


@app.get("/health")
def health():
    checks = {"database": "ok"}
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        checks["database"] = "unavailable"
        logger.error(f"Health check database failure: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "checks": checks},
        )
    finally:
        db.close()
    return {"status": "ok", "checks": checks}


@app.post("/admin/trigger-poll")
def trigger_poll(user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    from app.tasks import poll_recent_listens
    poll_recent_listens.delay()
    log_action(db, "admin.trigger_poll", user_id=user.user_id)
    return {"status": "triggered", "task": "poll_recent_listens"}


@app.post("/admin/trigger-backfill")
def trigger_backfill(user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    from app.tasks import backfill_track_metadata
    backfill_track_metadata.delay()
    log_action(db, "admin.trigger_backfill", user_id=user.user_id)
    return {"status": "triggered", "task": "backfill_track_metadata"}


@app.post("/admin/trigger-awards")
def trigger_awards(user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    from app.tasks import compute_award_snapshots
    compute_award_snapshots.delay()
    log_action(db, "admin.trigger_awards", user_id=user.user_id)
    return {"status": "triggered", "task": "compute_award_snapshots"}


@app.post("/track-event")
def track_event(
    event: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.audit import log_action
    action = event.get("action", "frontend.unknown")
    log_action(
        db,
        f"frontend.{action}",
        user_id=user.user_id,
        entity_type=event.get("entity_type"),
        entity_id=event.get("entity_id"),
        details=event.get("details"),
    )
    return {"status": "ok"}


@app.get("/admin/trust-score")
def trust_score(
    target_user_id: str = None,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from app.services.anomaly import analyze_user_export
    uid = target_user_id or user.user_id
    log_action(db, "admin.trust_score", user_id=user.user_id,
               details={"target_user_id": uid})
    return analyze_user_export(db, uid)


@app.post("/admin/force-logout-all")
def force_logout_all(
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
    from app.models import User as UserModel
    now = datetime.now(timezone.utc)
    db.query(UserModel).update({"token_invalidated_at": now})
    db.commit()
    log_action(db, "admin.force_logout_all", user_id=user.user_id)
    return {"status": "all_tokens_invalidated", "invalidated_at": now.isoformat()}


@app.post("/admin/force-logout/{target_user_id}")
def force_logout_user(
    target_user_id: str,
    user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    from datetime import datetime, timezone
    from app.models import User as UserModel
    now = datetime.now(timezone.utc)
    target = db.query(UserModel).filter(UserModel.user_id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.token_invalidated_at = now
    db.commit()
    log_action(db, "admin.force_logout_user", user_id=user.user_id,
               details={"target_user_id": target_user_id})
    return {"status": "token_invalidated", "target_user_id": target_user_id, "invalidated_at": now.isoformat()}


