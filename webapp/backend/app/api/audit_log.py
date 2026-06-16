from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from app.api.deps import require_admin
from app.core.db import get_session
from app.models.base import AuditLog, User
from app.services.audit_log_service import record_change, revert_change

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("/")
def list_audit_log(
    table_name: str | None = None,
    record_id: str | None = None,
    action: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if table_name:
        stmt = stmt.where(AuditLog.table_name == table_name)
    if record_id:
        stmt = stmt.where(AuditLog.record_id == record_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    stmt = stmt.offset(offset).limit(limit)
    return session.exec(stmt).all()


@router.get("/{log_id}")
def get_audit_log(
    log_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    log = session.get(AuditLog, log_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log entry not found")
    return log


@router.post("/{log_id}/revert")
def revert_audit_log(
    log_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    try:
        result = revert_change(session, log_id, user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
