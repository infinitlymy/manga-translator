import logging
from typing import Any
from sqlmodel import Session
from app.models.base import AuditLog

logger = logging.getLogger(__name__)


def record_change(
    session: Session,
    table_name: str,
    record_id: str,
    action: str,
    user_id: str | None,
    old_data: dict[str, Any] | None,
    new_data: dict[str, Any] | None,
) -> AuditLog:
    """Persist an audit log entry for a CRUD change. Call before session.commit()."""
    log = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        user_id=user_id,
        old_data=old_data,
        new_data=new_data,
    )
    session.add(log)
    logger.debug(f"Audit: {action} on {table_name}/{record_id} by {user_id}")
    return log


def revert_change(session: Session, log_id: str, user_id: str | None) -> dict:
    """Revert a change by restoring old_data into the target table."""
    from sqlmodel import SQLModel
    from app.models.base import (
        Collection, Dictionary, Setting, Job, Asset, User,
    )
    from datetime import datetime, timezone

    log = session.get(AuditLog, log_id)
    if not log:
        raise ValueError("Audit log entry not found")
    if log.reverted_at:
        raise ValueError("This change has already been reverted")
    if log.action == "delete":
        raise ValueError("Cannot revert a delete via this endpoint")
    if not log.old_data:
        raise ValueError("No old data to revert to")

    # Map table_name to model class
    TABLE_MAP = {
        "collections": Collection,
        "dictionaries": Dictionary,
        "settings": Setting,
        "jobs": Job,
        "assets": Asset,
        "users": User,
    }
    model_cls = TABLE_MAP.get(log.table_name)
    if not model_cls:
        raise ValueError(f"Reversion not supported for table {log.table_name}")

    record = session.get(model_cls, log.record_id)
    if not record:
        raise ValueError("Record no longer exists")

    # Apply old_data fields (skip id, timestamps, and read-only fields)
    skip_fields = {"id", "created_at", "updated_at"}
    for key, value in log.old_data.items():
        if key in skip_fields:
            continue
        if hasattr(record, key):
            setattr(record, key, value)

    # Update record and mark log as reverted
    session.add(record)
    log.reverted_at = datetime.now(timezone.utc)
    log.reverted_by = user_id
    session.add(log)
    session.commit()
    session.refresh(record)
    return {"message": "Change reverted", "record": record}
