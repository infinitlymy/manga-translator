from typing import Any
from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.api.deps import get_current_user, require_admin
from app.core.db import get_session
from app.services.settings_service import SettingsService
from app.services.audit_log_service import record_change
from app.models.base import User, Setting
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])

class SettingsUpdate(BaseModel):
    key: str
    value: Any
    category: str = "general"

@router.get("/")
def get_settings(
    category: str | None = None,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    svc = SettingsService(session)
    return svc.get_all(category)

@router.put("/")
def update_settings(
    data: SettingsUpdate,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    old_setting = session.query(Setting).filter(Setting.key == data.key).first()
    old_value = old_setting.value if old_setting else None
    record_change(
        session, "settings", data.key, "update" if old_value else "create", user.id,
        {"value": old_value, "category": data.category} if old_value else None,
        {"value": data.value, "category": data.category}
    )
    svc = SettingsService(session)
    svc.set(data.key, data.value, data.category)
    return {"message": "Setting updated"}

@router.put("/bulk")
def update_settings_bulk(
    data: dict[str, Any],
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    old_settings = {s.key: s.value for s in session.query(Setting).filter(Setting.key.in_(list(data.keys()))).all()}
    for key, value in data.items():
        record_change(
            session, "settings", key, "update" if key in old_settings else "create", user.id,
            {"value": old_settings.get(key)} if key in old_settings else None,
            {"value": value}
        )
    svc = SettingsService(session)
    for key, value in data.items():
        svc.set(key, value)
    return {"message": "Settings updated"}
