import io
import json
import zipfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Album, JobRun, Listen, ListenSource, Track, User
import logging

from app.models import User as UserModel
from app.routers.auth import get_current_user
from app.schemas import BackfillStatusResponse, BackfillUploadResponse
from app.services.audit import log_action
from app.services.ingestion import upsert_track_metadata
from app.services.spotify import SpotifyService, decrypt_token

logger = logging.getLogger("gatekeepify.backfill")

router = APIRouter(prefix="/backfill", tags=["backfill"])

BACKFILL_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
FILE_PREFIX = "Streaming_History_Audio"
FILE_SUFFIX = ".json"
MIN_PLAY_TIME_MS = 30000
TRACK_URI_PREFIX = "spotify:track:"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100 MB
MAX_DECOMPRESSED_BYTES = 500 * 1024 * 1024  # 500 MB

EXPECTED_EXPORT_FIELDS = {
    "ts",
    "ms_played",
    "master_metadata_track_name",
    "spotify_track_uri",
}
EXTRA_EXPORT_FIELDS = {
    "reason_start",
    "reason_end",
    "platform",
    "shuffle",
    "skipped",
    "offline",
    "offline_timestamp",
    "incognito_mode",
    "ip_addr_decrypted",
    "conn_country",
    "master_metadata_album_artist_name",
    "master_metadata_album_album_name",
    "episode_name",
    "episode_show_name",
    "spotify_episode_uri",
}


def _extract_json_from_zip(content: bytes) -> list[dict]:
    all_listens = []
    total_decompressed = 0
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    for name in zf.namelist():
        basename = name.split("/")[-1]
        if basename.startswith(FILE_PREFIX) and basename.endswith(FILE_SUFFIX):
            info = zf.getinfo(name)
            total_decompressed += info.file_size
            if total_decompressed > MAX_DECOMPRESSED_BYTES:
                raise HTTPException(status_code=400, detail="Decompressed data too large (max 500 MB)")
            with zf.open(name) as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_listens.extend(data)
                except json.JSONDecodeError:
                    continue
    return all_listens


def _validate_and_process_listens(
    raw_listens: list[dict],
    user: User,
    db: Session,
) -> tuple[list[tuple[Listen, Optional[str]]], dict]:
    rejection_reasons: dict[str, int] = {}
    accepted: list[tuple[Listen, Optional[str]]] = []

    album_release_dates: dict[str, Optional[datetime]] = {}
    albums = db.execute(
        select(Album.album_id, Album.release_date).where(
            Album.release_date.isnot(None)
        )
    ).all()
    for a in albums:
        album_release_dates[a.album_id] = datetime(
            a.release_date.year, a.release_date.month, a.release_date.day
        )

    track_albums: dict[str, str] = {}
    track_rows = db.execute(select(Track.track_id, Track.album_id)).all()
    for tr in track_rows:
        if tr.album_id:
            track_albums[tr.track_id] = tr.album_id

    user_api_listen_range = _get_api_listen_range(db, user.user_id)

    for listen_json in raw_listens:
        if not isinstance(listen_json, dict):
            rejection_reasons["invalid_format"] = (
                rejection_reasons.get("invalid_format", 0) + 1
            )
            continue

        ms_played = listen_json.get("ms_played", 0)
        if ms_played < MIN_PLAY_TIME_MS:
            rejection_reasons["too_short"] = (
                rejection_reasons.get("too_short", 0) + 1
            )
            continue

        track_uri = listen_json.get("spotify_track_uri")
        if not track_uri or not isinstance(track_uri, str):
            rejection_reasons["no_track_uri"] = (
                rejection_reasons.get("no_track_uri", 0) + 1
            )
            continue

        if not track_uri.startswith(TRACK_URI_PREFIX):
            rejection_reasons["invalid_uri_format"] = (
                rejection_reasons.get("invalid_uri_format", 0) + 1
            )
            continue

        track_id = track_uri.removeprefix(TRACK_URI_PREFIX)
        if not track_id:
            rejection_reasons["empty_track_id"] = (
                rejection_reasons.get("empty_track_id", 0) + 1
            )
            continue

        ts_str = listen_json.get("ts")
        if not ts_str:
            rejection_reasons["no_timestamp"] = (
                rejection_reasons.get("no_timestamp", 0) + 1
            )
            continue
        try:
            ts = datetime.strptime(ts_str, BACKFILL_DATETIME_FORMAT)
        except ValueError:
            rejection_reasons["invalid_timestamp"] = (
                rejection_reasons.get("invalid_timestamp", 0) + 1
            )
            continue

        album_id = track_albums.get(track_id)
        if album_id and album_id in album_release_dates:
            release_dt = album_release_dates[album_id]
            if ts < release_dt:
                rejection_reasons["before_release_date"] = (
                    rejection_reasons.get("before_release_date", 0) + 1
                )
                continue

        if user_api_listen_range:
            api_min, api_max = user_api_listen_range
            if api_min <= ts <= api_max:
                existing = db.execute(
                    select(Listen).where(
                        Listen.user_id == user.user_id,
                        Listen.track_id == track_id,
                        Listen.ts == ts,
                        Listen.source == ListenSource.api.value,
                    )
                ).first()
                if existing:
                    continue

        extra_meta = {
            k: listen_json[k] for k in EXTRA_EXPORT_FIELDS if k in listen_json
        }

        listen = Listen(
            ts=ts,
            user_id=user.user_id,
            track_id=track_id,
            source=ListenSource.export.value,
            export_metadata=json.dumps(extra_meta) if extra_meta else None,
        )
        track_name = listen_json.get("master_metadata_track_name")
        accepted.append((listen, track_name))

    return accepted, rejection_reasons


def _get_api_listen_range(
    db: Session, user_id: str
) -> Optional[tuple[datetime, datetime]]:
    stmt = (
        select(func.min(Listen.ts), func.max(Listen.ts))
        .where(Listen.user_id == user_id, Listen.source == ListenSource.api.value)
    )
    result = db.execute(stmt).first()
    if result and result[0] and result[1]:
        return (result[0], result[1])
    return None


@router.post("/upload")
def upload_data_export(
    file: UploadFile,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".zip"):
        log_action(
            db, "backfill.upload",
            user_id=user.user_id,
            status="error",
            details={"reason": "invalid_file_type", "filename": file.filename},
        )
        raise HTTPException(
            status_code=400, detail="Please upload a ZIP file"
        )

    active_job = db.execute(
        select(JobRun)
        .where(
            JobRun.user_id == user.user_id,
            JobRun.job_name == "backfill_upload",
            JobRun.status.in_(["pending", "running"]),
        )
    ).scalar_one_or_none()
    if active_job:
        raise HTTPException(status_code=409, detail="An upload is already being processed")

    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 100 MB)")

    raw_listens = _extract_json_from_zip(content)
    if not raw_listens:
        log_action(db, "backfill.upload", user_id=user.user_id, status="error",
                   details={"reason": "no_streaming_history_files"})
        raise HTTPException(status_code=400, detail="No streaming history files found in the ZIP")

    job = JobRun(
        job_name="backfill_upload",
        user_id=user.user_id,
        started_at=datetime.now(timezone.utc),
        status="pending",
        details=json.dumps({
            "phase": "queued",
            "progress": 0,
            "filename": file.filename,
            "total_listens": len(raw_listens),
            "listen_data": raw_listens,
        }),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.celery_app import celery_app
    celery_app.send_task("app.tasks.process_backfill_upload", args=[job.id, user.user_id])

    log_action(db, "backfill.upload_started", user_id=user.user_id,
               details={"job_id": job.id, "filename": file.filename, "size_bytes": len(content)})

    return {"job_id": job.id, "status": "processing"}


@router.get("/upload-status")
def upload_job_status(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.execute(
        select(JobRun)
        .where(JobRun.user_id == user.user_id, JobRun.job_name == "backfill_upload")
        .order_by(JobRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not job:
        return {"status": "none"}

    JOB_TIMEOUT_MINUTES = 120
    if job.status in ("pending", "running") and job.started_at:
        started = job.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - started).total_seconds() > JOB_TIMEOUT_MINUTES * 60:
            job.status = "error"
            job.completed_at = datetime.now(timezone.utc)
            details = json.loads(job.details) if job.details else {}
            details.update({"phase": "error", "error": "Job timed out after 30 minutes"})
            job.details = json.dumps(details)
            db.commit()

    details = json.loads(job.details) if job.details else {}
    return {
        "job_id": job.id,
        "status": job.status,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "phase": details.get("phase", "unknown"),
        "progress": details.get("progress", 0),
        "total_listens": details.get("total_listens"),
        "accepted": details.get("accepted"),
        "rejected": details.get("rejected"),
        "rejection_reasons": details.get("rejection_reasons"),
        "enriched": details.get("enriched"),
        "error": details.get("error"),
    }


@router.post("/cancel-upload")
def cancel_upload(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.execute(
        select(JobRun)
        .where(
            JobRun.user_id == user.user_id,
            JobRun.job_name == "backfill_upload",
            JobRun.status.in_(["pending", "running"]),
        )
        .order_by(JobRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="No active upload to cancel")

    job.status = "error"
    job.completed_at = datetime.now(timezone.utc)
    details = json.loads(job.details) if job.details else {}
    details.update({"phase": "error", "error": "Cancelled by user"})
    job.details = json.dumps(details)
    db.commit()

    log_action(db, "backfill.upload_cancelled", user_id=user.user_id,
               details={"job_id": job.id})

    return {"status": "cancelled", "job_id": job.id}


@router.get("/status", response_model=BackfillStatusResponse)
def backfill_status(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    missing_meta = db.execute(
        select(func.count(func.distinct(Listen.track_id)))
        .select_from(Listen)
        .join(Track, Listen.track_id == Track.track_id)
        .where(
            Listen.user_id == user.user_id,
            (Track.duration_ms.is_(None)) | (Track.album_id.is_(None)),
        )
    ).scalar() or 0

    total_listens = db.execute(
        select(func.count())
        .select_from(Listen)
        .where(Listen.user_id == user.user_id)
    ).scalar() or 0

    total_tracks = db.execute(
        select(func.count(func.distinct(Listen.track_id)))
        .select_from(Listen)
        .where(Listen.user_id == user.user_id)
    ).scalar() or 0

    has_export = db.execute(
        select(func.count())
        .select_from(Listen)
        .where(Listen.user_id == user.user_id, Listen.source == ListenSource.export.value)
    ).scalar() or 0

    log_action(db, "backfill.status_viewed", user_id=user.user_id,
               details={"missing_metadata": missing_meta, "has_export": has_export > 0})

    return BackfillStatusResponse(
        tracks_missing_metadata=missing_meta,
        total_listens=total_listens,
        total_tracks=total_tracks,
        has_export_data=has_export > 0,
    )
