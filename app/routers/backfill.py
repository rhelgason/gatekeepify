import io
import json
import zipfile
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Album, Listen, ListenSource, Track, User
from app.models import User as UserModel
from app.routers.auth import get_current_user
from app.schemas import BackfillStatusResponse, BackfillUploadResponse
from app.services.audit import log_action

router = APIRouter(prefix="/backfill", tags=["backfill"])

BACKFILL_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
FILE_PREFIX = "Streaming_History_Audio"
FILE_SUFFIX = ".json"
MIN_PLAY_TIME_MS = 30000
TRACK_URI_PREFIX = "spotify:track:"

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


def _extract_json_from_zip(upload: UploadFile) -> list[dict]:
    content = upload.file.read()
    all_listens = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")

    for name in zf.namelist():
        basename = name.split("/")[-1]
        if basename.startswith(FILE_PREFIX) and basename.endswith(FILE_SUFFIX):
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


@router.post("/upload", response_model=BackfillUploadResponse)
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

    raw_listens = _extract_json_from_zip(file)
    if not raw_listens:
        log_action(
            db, "backfill.upload",
            user_id=user.user_id,
            status="error",
            details={"reason": "no_streaming_history_files"},
        )
        raise HTTPException(
            status_code=400,
            detail="No streaming history files found in the ZIP",
        )

    accepted, rejection_reasons = _validate_and_process_listens(
        raw_listens, user, db
    )

    user_obj = db.query(User).filter(User.user_id == user.user_id).first()
    if user_obj:
        db.merge(user_obj)

    inserted = 0
    for listen, track_name in accepted:
        existing = db.execute(
            select(Listen).where(
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

    log_action(
        db, "backfill.upload",
        user_id=user.user_id,
        details={
            "total_processed": len(raw_listens),
            "total_accepted": inserted,
            "total_rejected": len(raw_listens) - len(accepted),
            "rejection_reasons": rejection_reasons,
        },
    )

    return BackfillUploadResponse(
        total_listens_processed=len(raw_listens),
        total_listens_accepted=inserted,
        total_listens_rejected=len(raw_listens) - len(accepted),
        rejection_reasons=rejection_reasons,
    )


@router.get("/status", response_model=BackfillStatusResponse)
def backfill_status(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    missing_meta = db.execute(
        select(func.count(func.distinct(Listen.track_id)))
        .select_from(Listen)
        .outerjoin(Track, Listen.track_id == Track.track_id)
        .where(Listen.user_id == user.user_id, Track.track_name.is_(None))
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

    return BackfillStatusResponse(
        tracks_missing_metadata=missing_meta,
        total_listens=total_listens,
        total_tracks=total_tracks,
    )
