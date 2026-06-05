import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog

logger = logging.getLogger("gatekeepify.audit")


def log_action(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
    status: str = "success",
) -> None:
    entry = AuditLog(
        ts=datetime.now(timezone.utc),
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details) if details else None,
        status=status,
    )
    db.add(entry)
    try:
        db.flush()
    except Exception as e:
        # Audit logging is best-effort and must never break the request, but a
        # failure here means we're losing the audit trail — surface it (and let
        # Sentry capture it) instead of swallowing silently.
        logger.error(f"Failed to persist audit entry for action '{action}': {e!r}")

    log_msg = f"[{status}] {action}"
    if user_id:
        log_msg += f" user={user_id}"
    if entity_type and entity_id:
        log_msg += f" {entity_type}={entity_id}"
    if details:
        log_msg += f" {details}"

    if status == "error":
        logger.error(log_msg)
    elif status == "denied":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)
